"""Fenêtres de saisie : invite, listes, messages, formulaires."""

import curses
import glob
import os
import textwrap

import nhlevel
from nhi18n import _
from nhme_common import BUC, Cancel, Group
from nhme_theme import dotted, group_line


class DialogsMixin:
    """Méthodes de l'éditeur (voir nhmapedit.Editor)."""

    def prompt(self, label, default="", completer=None):
        """Saisie d'une ligne en bas de l'écran. Échap -> Cancel."""
        buf, pos = list(default), len(default)
        curses.curs_set(1)
        while True:
            maxy, maxx = self.scr.getmaxyx()
            line = label + "".join(buf)
            off = max(0, len(line) - maxx + 2)
            self.put(maxy - 2, 0, " " * (maxx - 1))
            self.put(maxy - 2, 0, line[off:], curses.A_BOLD)
            self.scr.move(maxy - 2, min(maxx - 1, len(label) + pos - off))
            self.scr.refresh()
            k = self.scr.get_wch()
            if k in ("\n", "\r", curses.KEY_ENTER):
                return "".join(buf)
            if k == "\x1b":
                raise Cancel()
            if k in (curses.KEY_BACKSPACE, "\x7f", "\x08"):
                if pos:
                    del buf[pos - 1]
                    pos -= 1
            elif k == curses.KEY_DC:
                if pos < len(buf):
                    del buf[pos]
            elif k == curses.KEY_LEFT:
                pos = max(0, pos - 1)
            elif k == curses.KEY_RIGHT:
                pos = min(len(buf), pos + 1)
            elif k in (curses.KEY_HOME, "\x01"):
                pos = 0
            elif k in (curses.KEY_END, "\x05"):
                pos = len(buf)
            elif k == "\x15":
                buf, pos = [], 0
            elif k == "\t" and completer:
                new = completer("".join(buf))
                if new is not None:
                    buf, pos = list(new), len(new)
            elif isinstance(k, str) and k.isprintable():
                buf.insert(pos, k)
                pos += 1

    def path_completer(self, text):
        matches = glob.glob(os.path.expanduser(text) + "*")
        if not matches:
            return None
        common = os.path.commonprefix(matches)
        if len(matches) == 1 and os.path.isdir(common):
            common += "/"
        if len(matches) > 1:
            self.msg = "  ".join(os.path.basename(m) for m in matches[:12])
        return common

    def window(self, h, w):
        maxy, maxx = self.scr.getmaxyx()
        h, w = min(h, maxy - 2), min(w, maxx - 2)
        geom = (h, w, (maxy - h) // 2, (maxx - w) // 2)
        if geom != getattr(self, "last_window", None) and self.lvl:
            # autre fenêtre (ou autre taille) : on efface les restes de
            # la précédente en redessinant l'écran dessous
            self.draw()
        self.last_window = geom
        win = curses.newwin(*geom)
        win.keypad(True)
        return win, h, w

    @staticmethod
    def menu_mouse(win):
        """Événement souris d'un menu : ("row", y) clic gauche sur la
        ligne y de la fenêtre (double : ("row2", y)), ("up",)/("down",)
        molette, ("cancel",) clic droit, None sinon."""
        try:
            _id, mx, my, _z, b = curses.getmouse()
        except curses.error:
            return None
        if b & curses.BUTTON4_PRESSED:
            return ("up",)
        if b & getattr(curses, "BUTTON5_PRESSED", 0):
            return ("down",)
        if b & (curses.BUTTON3_PRESSED | curses.BUTTON3_CLICKED):
            return ("cancel",)
        by, bx = win.getbegyx()
        h, w = win.getmaxyx()
        if not (by <= my < by + h and bx <= mx < bx + w):
            return None
        if b & curses.BUTTON1_DOUBLE_CLICKED:
            return ("row2", my - by)
        if b & (curses.BUTTON1_PRESSED | curses.BUTTON1_CLICKED):
            return ("row", my - by)
        return None

    def wput(self, win, y, x, s, a=0):
        """Écrit dans une fenêtre en coupant au bord (sans erreur dans le
        coin bas-droit)."""
        h, w = win.getmaxyx()
        if 0 <= y < h and x < w:
            try:
                win.addnstr(y, x, s, w - x, a)
            except curses.error:
                pass

    def menu_head(self, win, title):
        """Bloc de titre du lanceur : « ==== », titre centré, « ==== »."""
        h, w = win.getmaxyx()
        sep = "=" * w
        self.wput(win, 0, 0, sep, self.style("separateur"))
        self.wput(win, 1, 0, title[:w - 2].center(w).rstrip(),
                  self.style("titre"))
        self.wput(win, 2, 0, sep, self.style("separateur"))

    def menu_foot(self, win, y, lines):
        """Pied d'un menu à partir de la ligne y : « ==== », puis les
        lignes (texte, élément du thème), puis « ==== » en bas."""
        h, w = win.getmaxyx()
        sep = "=" * w
        self.wput(win, y, 0, sep, self.style("separateur"))
        for i, (text, elem) in enumerate(lines):
            self.wput(win, y + 1 + i, 1, text, self.style(elem))
        self.wput(win, h - 1, 0, sep, self.style("separateur"))

    def menu(self, title, items, initial=None, custom=False, hint="",
             actions=None, filterable=True):
        """Menu dans le style du lanceur NetHack. items : [(libellé,
        valeur)] ou [(libellé, valeur, {"key": touche, "desc": texte})],
        et des Group("titre") pour les titres de groupe. Renvoie la valeur
        choisie, ou (valeur, action) avec actions ({touche: action}).
        Échap -> Cancel.

        Une touche entre crochets choisit sa ligne ; un numéro aussi
        (tout de suite s'il y a au plus 9 lignes, sinon Entrée) ; les
        autres lettres filtrent la liste (filterable) ; avec custom,
        Entrée sur un filtre sans correspondance renvoie le texte saisi."""
        entries = []
        for it in items:
            if isinstance(it, Group):
                entries.append(it)
            else:
                opts = it[2] if len(it) > 2 else {}
                entries.append((it[0], it[1], opts.get("key"),
                                opts.get("desc") or ""))
        choices = [e for e in entries if not isinstance(e, Group)]
        number = {id(e): i + 1 for i, e in enumerate(choices)}
        keys = {e[2]: e for e in choices if e[2]}
        numw = len(str(len(choices)))
        keyw = 4 if keys else 0
        filt = ""
        sel = 0
        if initial is not None:
            for i, e in enumerate(choices):
                if e[1] == initial:
                    sel = i
                    break
        cur = choices[sel] if choices else None
        top = 0
        if not hint:
            parts = [_("↑/↓ naviguer"), _("Entrée choisir")]
            parts.append(_("touche ou numéro") if keys else _("numéro"))
            parts.append(_("Échap annuler"))
            hint = " · ".join(parts)
        hint = dotted(hint)

        def done(e, action=None):
            curses.curs_set(1)
            return (e[1], action) if actions is not None else e[1]

        curses.curs_set(0)
        while True:
            if filt and not filt.isdigit():
                low = filt.lower()
                shown = [e for e in choices if low in e[0].lower()]
            else:
                shown = entries
            rows = [e for e in shown]
            selectable = [e for e in rows if not isinstance(e, Group)]
            if cur not in selectable:
                cur = selectable[0] if selectable else None
            maxy, maxx = self.scr.getmaxyx()
            label_w = max([len(e[0]) for e in choices[:300]] + [10])
            width = max(len(title) + 4, len(hint) + 3, 44,
                        label_w + numw + keyw + 6)
            wrap_w = min(width, maxx - 2) - 2
            descs = [textwrap.wrap(e[3], max(10, wrap_w)) for e in choices
                     if e[3]]
            desc_h = min(4, max([len(d) for d in descs] + [0]))
            # ligne du filtre : listes longues, ou dès que l'on tape
            show_filt = filt or (filterable and len(choices) > 9)
            foot = (1 if show_filt else 0) + desc_h + 1
            win, h, w = self.window(min(len(entries), maxy - 8 - foot)
                                    + foot + 5, width)
            n = max(1, h - foot - 5)
            ri = rows.index(cur) if cur in rows else 0
            if ri < top:
                top = ri
            elif ri >= top + n:
                top = ri - n + 1
            top = max(0, min(top, max(0, len(rows) - n)))
            win.erase()
            self.menu_head(win, title)
            zones = {}
            for i in range(n):
                j = top + i
                if j >= len(rows):
                    break
                e, y = rows[j], 3 + i
                if isinstance(e, Group):
                    self.wput(win, y, 1, group_line(e, w - 2, self.unicode),
                              self.style("groupe"))
                    continue
                zones[y] = e
                num = "%*d" % (numw, number[id(e)])
                key = ("[%s]" % e[2] if e[2] else "   ") if keys else ""
                if e is cur:
                    text = " %s %s%s %s" % (num, key, " " if key else "",
                                           e[0])
                    self.wput(win, y, 0, text.ljust(w), self.style(
                        "selection"))
                else:
                    self.wput(win, y, 1, num, self.style("numero"))
                    x = 2 + numw
                    if key:
                        self.wput(win, y, x, key, self.style("touche"))
                        x += 4
                    self.wput(win, y, x + 1, e[0], self.style("texte"))
            lines = []
            if show_filt:
                if filt.isdigit():
                    left = _("Numéro : ") + filt
                elif filt:
                    left = _("Filtre : ") + filt
                else:
                    left = _("Filtre : (tapez des lettres)")
                more = "%d/%d" % (len(selectable), len(choices))
                lines.append((left.ljust(w - 3 - len(more)) + more,
                              "discret"))
            d = textwrap.wrap(cur[3], max(10, w - 2)) if cur else []
            lines += [(t, "description") for t in (d + [""] * desc_h)[
                :desc_h]]
            lines.append((hint, "aide"))
            self.menu_foot(win, h - 2 - len(lines), lines)
            if len(rows) > n:
                mark = "%d-%d/%d" % (top + 1, min(len(rows), top + n),
                                     len(rows))
                self.wput(win, 2, w - len(mark) - 2, " %s " % mark,
                          self.style("discret"))
            win.refresh()
            k = win.get_wch()
            idx = selectable.index(cur) if cur in selectable else 0
            if k in ("\n", "\r", curses.KEY_ENTER):
                if filt.isdigit() and custom and not (
                        1 <= int(filt) <= len(choices)):
                    curses.curs_set(1)
                    return filt
                if cur is not None:
                    return done(cur, "goto")
                if custom and filt:
                    curses.curs_set(1)
                    return filt
            elif k == "\x1b" or (actions is not None and k == "q"):
                curses.curs_set(1)
                raise Cancel()
            elif actions is not None and k in actions and cur is not None:
                return done(cur, actions[k])
            elif k == curses.KEY_UP and selectable:
                cur = selectable[(idx - 1) % len(selectable)]
            elif k == curses.KEY_DOWN and selectable:
                cur = selectable[(idx + 1) % len(selectable)]
            elif k == curses.KEY_PPAGE and selectable:
                cur = selectable[max(0, idx - n)]
            elif k == curses.KEY_NPAGE and selectable:
                cur = selectable[min(len(selectable) - 1, idx + n)]
            elif k == curses.KEY_HOME and selectable:
                cur = selectable[0]
            elif k == curses.KEY_END and selectable:
                cur = selectable[-1]
            elif k in (curses.KEY_BACKSPACE, "\x7f", "\x08"):
                filt = filt[:-1]
            elif k == curses.KEY_RESIZE:
                self.draw()
            elif k == curses.KEY_MOUSE:
                # clic : choisit la ligne, un second clic (ou un double
                # clic) la valide ; molette : défile ; clic droit : annule
                m = self.menu_mouse(win)
                if m == ("cancel",):
                    curses.curs_set(1)
                    raise Cancel()
                if m in (("up",), ("down",)) and selectable:
                    step = 3 if m == ("down",) else -3
                    cur = selectable[max(0, min(len(selectable) - 1,
                                                idx + step))]
                elif m and m[1] in zones:
                    if zones[m[1]] is cur or m[0] == "row2":
                        return done(zones[m[1]], "goto")
                    cur = zones[m[1]]
            elif isinstance(k, str) and k.isprintable():
                if not filt and k in keys:
                    return done(keys[k], "goto")
                if k.isdigit() and (not filt or filt.isdigit()):
                    filt += k
                    v = int(filt)
                    if len(choices) <= 9 and 1 <= v <= len(choices):
                        return done(choices[v - 1], "goto")
                    if 1 <= v <= len(choices):
                        cur = choices[v - 1]
                elif filterable or custom:
                    filt += k

    def pick(self, title, items, initial=None, custom=False, hint=""):
        """Liste filtrable (voir menu()). Échap -> Cancel."""
        return self.menu(title, items, initial, custom, hint)

    def message_box(self, title, text):
        lines = text.split("\n")
        top = 0
        curses.curs_set(0)
        while True:
            maxy, maxx = self.scr.getmaxyx()
            foot = _("↑/↓ défiler · Échap/q fermer")
            win, h, w = self.window(len(lines) + 6, max(
                [len(l) for l in lines] + [len(title) + 4, len(foot) + 3])
                + 2)
            n = h - 6
            win.erase()
            self.menu_head(win, title)
            for i in range(n):
                if top + i < len(lines):
                    line = lines[top + i]
                    word = line.split(" ")[0]
                    if line[:1].isalpha() and len(word) > 1 and \
                            word == word.upper():
                        # titre de section de l'aide : « ── OUTILS ── »
                        self.wput(win, 3 + i, 1, group_line(
                            line, w - 2, self.unicode), self.style("groupe"))
                    else:
                        self.wput(win, 3 + i, 1, line)
            if len(lines) > n:
                mark = "%d-%d/%d" % (top + 1, min(len(lines), top + n),
                                     len(lines))
                self.wput(win, 2, w - len(mark) - 2, " %s " % mark,
                          self.style("discret"))
            self.menu_foot(win, h - 3, [(foot, "aide")])
            win.refresh()
            k = win.getch()
            if k == curses.KEY_MOUSE:
                m = self.menu_mouse(win)
                if m in (("up",), ("down",)):
                    top += 3 if m == ("down",) else -3
                    top = max(0, min(max(0, len(lines) - n), top))
                    continue
                if m is None:
                    continue        # mouvement : la fenêtre reste
                break               # clic : fermer
            if k in (curses.KEY_DOWN, ord("j"), curses.KEY_NPAGE, ord(" ")):
                step = n if k in (curses.KEY_NPAGE, ord(" ")) else 1
                top = min(max(0, len(lines) - n), top + step)
            elif k in (curses.KEY_UP, ord("k"), curses.KEY_PPAGE):
                step = n if k == curses.KEY_PPAGE else 1
                top = max(0, top - step)
            elif k == curses.KEY_RESIZE:
                self.draw()
            else:
                break
        curses.curs_set(1)

    def confirm(self, question):
        try:
            r = self.prompt(question + _(" (o/n) "))
        except Cancel:
            return False
        return r.strip().lower() in ("o", "oui", "y", "yes")

    def form(self, title, form, extra, free=True):
        """Formulaire : form = [(clé, type, libellé)], extra = valeurs.

        Entrée modifie la ligne choisie (les booléens passent de « défaut »
        à oui, non, puis défaut) ; Échap ou « Terminer » valide. Avec
        free, les autres options se saisissent librement sur la dernière
        ligne. Types : voir MON_FORM, plus ("choice", valeurs) et
        ("flags", valeurs) pour une liste à cocher."""
        keys = [k for k, _, _ in form]
        extra = dict(extra)
        sel = "_done"
        while True:
            items = [(_("Terminer"), "_done")]
            for key, typ, label in form:
                if key not in extra:
                    shown = _("(défaut)")
                elif typ == "bool":
                    shown = _("oui") if extra[key] else _("non")
                elif typ == "contents":
                    c = extra[key]
                    shown = c.summary() + " " + ", ".join(
                        it.value or _("aléatoire") for it in c.items)
                elif isinstance(extra[key], list):
                    shown = ", ".join(map(str, extra[key]))
                else:
                    shown = nhlevel.lua_value(extra[key])
                items.append(("%-34s %s" % ("%s (%s)" % (label, key), shown),
                              key))
            rest = {k: v for k, v in extra.items() if k not in keys}
            if free:
                items.append((_("Autres options : %s") % (", ".join(
                    "%s=%s" % (k, nhlevel.lua_value(v))
                    for k, v in rest.items()) or _("(aucune)")), "_other"))
            try:
                sel = self.pick(title, items, sel,
                                hint=_("↑/↓ naviguer · Entrée modifier · "
                                       "numéro · Échap terminer"))
            except Cancel:
                return extra
            if sel == "_done":
                return extra
            try:
                if sel == "_other":
                    new = self.ask_extra(rest)
                    extra = {k: v for k, v in extra.items() if k in keys}
                    extra.update(new)
                    continue
                typ = dict((k, t) for k, t, _ in form)[sel]
                if typ == "bool":
                    # défaut -> oui -> non -> défaut
                    if sel not in extra:
                        extra[sel] = 1
                    elif extra[sel]:
                        extra[sel] = 0
                    else:
                        del extra[sel]
                elif typ == "buc" or typ[0] == "choice":
                    values = BUC if typ == "buc" else typ[1]
                    v = self.pick(sel, [(_("(défaut)"), None)] +
                                  [(b, b) for b in values], extra.get(sel))
                    self.set_option(extra, sel, v)
                elif typ[0] == "flags":
                    v = self.check_list(sel, typ[1], extra.get(sel) or [])
                    self.set_option(extra, sel, v or None)
                elif typ == "contents":
                    v = self.edit_contents(extra.get(sel), "%s (%s)" % (
                        dict((k, l) for k, _, l in form)[sel].capitalize(),
                        sel))
                    self.set_option(extra, sel, v)
                elif typ == "mon":
                    items = [(_("(défaut)"), None)] + [
                        self.pick_label("monster", m)
                        for m in self.data["monsters"]]
                    v = self.pick(_("Monstre (tapez pour filtrer ; une lettre "
                                    "seule = classe)"), items, extra.get(sel),
                                  custom=True)
                    self.set_option(extra, sel, v)
                else:
                    self.ask_option(extra, sel, typ)
            except Cancel:
                pass

    def check_list(self, title, values, checked):
        """Liste à cocher (Entrée coche ou décoche, Échap termine)."""
        checked = list(checked)
        sel = values[0]
        while True:
            items = [("[%s] %s" % ("x" if v in checked else " ", v), v)
                     for v in values]
            try:
                sel = self.pick(title, items, sel,
                                hint=_("↑/↓ naviguer · Entrée cocher/décocher"
                                       " · numéro · Échap terminer"))
            except Cancel:
                return [v for v in values if v in checked]
            if sel in checked:
                checked.remove(sel)
            else:
                checked.append(sel)

    @staticmethod
    def set_option(extra, key, v):
        if v is None:
            extra.pop(key, None)
        else:
            extra[key] = v

    def ask_option(self, extra, key, typ):
        """Saisie d'une option texte ou entière ; vide = valeur par défaut."""
        cur = extra.get(key)
        txt = "" if cur is None else str(cur)
        hint = {"str": _("texte"), "int": _("entier"),
                "intr": _("entier ou random")}[typ]
        while True:
            s = self.prompt(_("%s (%s, vide = défaut) : ") % (key, hint),
                            txt).strip()
            if not s:
                extra.pop(key, None)
                return
            if typ == "str":
                extra[key] = s
                return
            if typ == "intr" and s == "random":
                extra[key] = s
                return
            try:
                extra[key] = int(s)
                return
            except ValueError:
                txt = s
                self.msg = _("Valeur invalide : %s attendu.") % hint

    def pick_action(self, title, items, sel, hint):
        """Comme pick() sans filtre, avec les touches e (modifier) et d
        (supprimer) ; renvoie (valeur, action)."""
        initial = items[min(sel, len(items) - 1)][1] if items else None
        return self.menu(title, items, initial, hint=hint, filterable=False,
                         actions={"e": "edit", "d": "delete",
                                  curses.KEY_DC: "delete"})
