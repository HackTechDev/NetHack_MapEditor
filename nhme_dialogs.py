"""Fenêtres de saisie : invite, listes, messages, formulaires."""

import curses
import glob
import os

import nhlevel
from nhi18n import _
from nhme_common import BUC, Cancel


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
        win = curses.newwin(h, w, (maxy - h) // 2, (maxx - w) // 2)
        win.keypad(True)
        return win, h, w

    @staticmethod
    def dialog_mouse(win, h, w):
        """Événement souris dans une fenêtre de dialogue : ("line", i) clic
        gauche sur la ligne intérieure i (0 : celle sous le cadre),
        ("up",) / ("down",) molette, ("cancel",) clic droit ; None pour le
        reste (mouvements, clic hors de la fenêtre)."""
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
        if (b & (curses.BUTTON1_PRESSED | curses.BUTTON1_CLICKED)
                and by < my < by + h - 1 and bx < mx < bx + w - 1):
            return ("line", my - by - 1)
        return None

    def pick(self, title, items, initial=None, custom=False, hint=""):
        """Liste filtrable. items : [(libellé, valeur)]. Échap -> Cancel.

        On tape pour filtrer ; avec custom=True, Entrée sur un filtre sans
        correspondance renvoie le texte saisi."""
        filt, sel, top = "", 0, 0
        if initial is not None:
            for i, (_label, v) in enumerate(items):
                if v == initial:
                    sel = i
        curses.curs_set(0)
        while True:
            shown = [it for it in items
                     if filt.lower() in it[0].lower()] if filt else items
            maxy, maxx = self.scr.getmaxyx()
            width = max([len(title) + 4, len(hint) + 4, 40] +
                        [len(l) + 6 for l, _ in shown[:200]])
            win, h, w = self.window(min(len(items), maxy - 8) + 5, width)
            n = h - 5
            sel = max(0, min(sel, len(shown) - 1))
            if sel < top:
                top = sel
            elif sel >= top + n:
                top = sel - n + 1
            win.erase()
            win.box()
            win.addnstr(0, 2, " %s " % title, w - 4, curses.A_BOLD)
            for i in range(n):
                j = top + i
                if j >= len(shown):
                    break
                a = curses.A_REVERSE if j == sel else 0
                win.addnstr(1 + i, 2, shown[j][0].ljust(w - 4), w - 4, a)
            more = "%d/%d" % (len(shown), len(items))
            win.addnstr(h - 3, 2, _("Filtre : ") + filt, w - 4 - len(more) - 1,
                        curses.A_BOLD)
            win.addnstr(h - 3, w - 2 - len(more), more, len(more))
            win.addnstr(h - 2, 2, hint or _("Entrée: choisir  Échap: annuler"),
                        w - 4)
            win.refresh()
            k = win.get_wch()
            if k in ("\n", "\r", curses.KEY_ENTER):
                if shown:
                    curses.curs_set(1)
                    return shown[sel][1]
                if custom and filt:
                    curses.curs_set(1)
                    return filt
            elif k == "\x1b":
                curses.curs_set(1)
                raise Cancel()
            elif k == curses.KEY_UP:
                sel -= 1
            elif k == curses.KEY_DOWN:
                sel += 1
            elif k == curses.KEY_PPAGE:
                sel -= n
            elif k == curses.KEY_NPAGE:
                sel += n
            elif k == curses.KEY_HOME:
                sel = 0
            elif k == curses.KEY_END:
                sel = len(shown) - 1
            elif k in (curses.KEY_BACKSPACE, "\x7f", "\x08"):
                filt = filt[:-1]
                sel = 0
            elif k == curses.KEY_RESIZE:
                self.draw()
            elif k == curses.KEY_MOUSE:
                # clic : choisit la ligne, un second clic la valide ;
                # molette : défile ; clic droit : annule
                m = self.dialog_mouse(win, h, w)
                if m == ("cancel",):
                    curses.curs_set(1)
                    raise Cancel()
                if m in (("up",), ("down",)):
                    sel += 3 if m == ("down",) else -3
                elif m and m[1] < n and top + m[1] < len(shown):
                    if top + m[1] == sel:
                        curses.curs_set(1)
                        return shown[sel][1]
                    sel = top + m[1]
            elif isinstance(k, str) and k.isprintable():
                filt += k
                sel = 0

    def message_box(self, title, text):
        lines = text.split("\n")
        top = 0
        curses.curs_set(0)
        while True:
            maxy, maxx = self.scr.getmaxyx()
            win, h, w = self.window(len(lines) + 3,
                                    max(len(l) for l in lines + [title]) + 4)
            n = h - 3
            win.erase()
            win.box()
            win.addnstr(0, 2, " %s " % title, w - 4, curses.A_BOLD)
            for i in range(n):
                if top + i < len(lines):
                    win.addnstr(1 + i, 2, lines[top + i], w - 4)
            foot = _(" Échap/q: fermer ")
            if len(lines) > n:
                foot = _(" ↑↓ défiler") + foot
            win.addnstr(h - 1, max(1, w - len(foot) - 2), foot, w - 3)
            win.refresh()
            k = win.getch()
            if k == curses.KEY_MOUSE:
                m = self.dialog_mouse(win, h, w)
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
                sel = self.pick(_("%s (Entrée: modifier, Échap: terminer)")
                                % title, items, sel)
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
                sel = self.pick(_("%s (Entrée: cocher/décocher, Échap: "
                                  "terminer)") % title, items, sel)
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
        """Comme pick() sans filtre, avec les touches e et d."""
        top = 0
        curses.curs_set(0)
        try:
            while True:
                maxy, maxx = self.scr.getmaxyx()
                width = max([len(hint) + 4] + [len(l) + 4 for l, _ in items])
                win, h, w = self.window(len(items) + 4, width)
                n = h - 4
                sel = max(0, min(sel, len(items) - 1))
                if sel < top:
                    top = sel
                elif sel >= top + n:
                    top = sel - n + 1
                win.erase()
                win.box()
                win.addnstr(0, 2, " %s " % title, w - 4, curses.A_BOLD)
                for i in range(n):
                    j = top + i
                    if j < len(items):
                        a = curses.A_REVERSE if j == sel else 0
                        win.addnstr(1 + i, 2, items[j][0].ljust(w - 4),
                                    w - 4, a)
                win.addnstr(h - 2, 2, hint, w - 4)
                win.refresh()
                k = win.getch()
                if k in (10, 13, curses.KEY_ENTER):
                    return items[sel][1], "goto"
                if k == ord("e"):
                    return items[sel][1], "edit"
                if k in (ord("d"), curses.KEY_DC):
                    return items[sel][1], "delete"
                if k in (27, ord("q")):
                    raise Cancel()
                if k == curses.KEY_MOUSE:
                    m = self.dialog_mouse(win, h, w)
                    if m == ("cancel",):
                        raise Cancel()
                    if m in (("up",), ("down",)):
                        sel += 3 if m == ("down",) else -3
                    elif m and m[1] < n and top + m[1] < len(items):
                        if top + m[1] == sel:
                            return items[sel][1], "goto"
                        sel = top + m[1]
                    continue
                if k == curses.KEY_UP:
                    sel -= 1
                elif k == curses.KEY_DOWN:
                    sel += 1
                elif k == curses.KEY_PPAGE:
                    sel -= n
                elif k == curses.KEY_NPAGE:
                    sel += n
        finally:
            curses.curs_set(1)
