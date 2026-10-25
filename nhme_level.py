"""Propriétés du niveau, vérification, fichiers et salles à thème."""

import collections
import os
import random
import re
import shutil
import time

import nhcheck
import nhexport
import nhgen
import nhlevel
from nhi18n import _
import nhtheme
from nhlevel import Entity, Level
from nhme_common import (
    AUTOSAVE_SUFFIX, CACHE_DIR, Cancel, EXPORTS)


class LevelMixin:
    """Méthodes de l'éditeur (voir nhmapedit.Editor)."""

    # --- statistiques ---------------------------------------------------
    def stats_text(self):
        """Texte des statistiques du niveau (touche %)."""
        lvl = self.lvl
        lines = [_("Carte %dx%d") % (lvl.w, lvl.h)
                 + (_(" (carte %d sur %d)") % (lvl.map_index + 1,
                                               len(lvl.maps))
                    if len(lvl.maps) > 1 else ""), ""]
        cells = collections.Counter(c for row in lvl.grid for c in row)
        total = lvl.w * lvl.h
        lines.append(_("Terrain :"))
        for c, n in cells.most_common():
            lines.append("  %s  %-28s %5d  %3d %%" % (
                "e" if c == " " else c,
                nhlevel.TERRAIN_DESC.get(c, "?").split(" (")[0][:28], n,
                round(100 * n / total)))
        fixed = collections.Counter(e.kind for e in lvl.entities)
        lines += ["", _("Entités à position fixe : %d") % len(lvl.entities)]
        for k in nhlevel.ENTITY_KINDS:
            if fixed[k]:
                lines.append("  %-28s %5d" % (nhlevel.ENTITY_LABEL[k],
                                              fixed[k]))
        sym = {"monster": {m["name"]: m["sym"] for m in
                           self.data["monsters"]},
               "object": {o["name"]: o["sym"] for o in self.data["objects"]}}
        titles = {"monster": _("Monstres par classe :"),
                  "object": _("Objets par classe :")}
        for kind in ("monster", "object"):
            groups = collections.defaultdict(collections.Counter)
            for e in lvl.entities:
                if e.kind != kind:
                    continue
                if e.value is None:
                    groups["?"][_("aléatoire")] += 1
                elif len(e.value) == 1:
                    groups[e.value][_("classe aléatoire")] += 1
                else:
                    groups[sym[kind].get(e.value, "?")][e.value] += 1
            if not groups:
                continue
            lines += ["", titles[kind]]
            for s, names in sorted(groups.items(),
                                   key=lambda kv: -sum(kv[1].values())):
                detail = ", ".join(
                    "%s ×%d" % (nm, n) if n > 1 else nm
                    for nm, n in names.most_common(4))
                if len(names) > 4:
                    detail += ", …"
                lines.append("  %s %4d  %s" % (s, sum(names.values()),
                                               detail))
        traps = collections.Counter(
            _("aléatoire") if e.value is None else e.value
            for e in lvl.entities if e.kind == "trap")
        if traps:
            lines += ["", _("Pièges :")]
            lines += ["  %-28s %5d" % (t, n) for t, n in traps.most_common()]
        if lvl.regions:
            regs = collections.Counter(nhlevel.REGION_LABEL[r.kind]
                                       for r in lvl.regions)
            lines += ["", _("Régions : %d") % len(lvl.regions)]
            lines += ["  %-28s %5d" % (k, n) for k, n in regs.most_common()]
            types = collections.Counter(
                r.extra["type"] for r in lvl.regions
                if isinstance(r.extra.get("type"), str)
                and r.kind == "region")
            if types:
                lines.append(_("  salles typées : %s") % ", ".join(
                    "%s ×%d" % kv if kv[1] > 1 else kv[0]
                    for kv in types.most_common()))
        if lvl.randoms:
            lines += ["", _("Placements aléatoires du script : %d")
                      % len(lvl.randoms)]
            rnd = collections.Counter(
                (nhlevel.ENTITY_LABEL[r.kind], r.zone[0] == "map")
                for r in lvl.randoms)
            for (k, anywhere), n in rnd.most_common():
                lines.append("  %-28s %5d  %s" % (
                    k, n, _("n'importe où dans la carte") if anywhere
                    else _("dans une zone ou une liste de cases")))
        lines += self.difficulty_lines()
        return "\n".join(lines)

    def difficulty(self):
        """Difficulté estimée d'après les monstres placés (positions fixes
        et appels aléatoires du script qui nomment le monstre). NetHack ne
        tire au hasard un monstre de difficulté D que si (profondeur +
        niveau du héros) / 2 >= D : pour un héros de niveau voisin de la
        profondeur, D est la profondeur où il apparaît naturellement.
        Renvoie None sans monstre."""
        named, classes, unknown = [], [], 0
        values = [e.value for e in self.lvl.entities if e.kind == "monster"]
        for r in self.lvl.randoms:
            if r.kind == "monster":
                m = re.search(r'"([^"]+)"', r.text)
                values.append(m.group(1) if m else None)
        for v in values:
            if v is None or v not in self.mon and len(v) != 1:
                unknown += 1
            elif len(v) == 1:
                diffs = sorted(m["difficulty"] for m in self.data["monsters"]
                               if m["sym"] == v and "difficulty" in m)
                if diffs:                       # médiane de la classe
                    classes.append((diffs[len(diffs) // 2], 0,
                                    _("classe %s") % v))
                else:
                    unknown += 1
            elif "difficulty" in self.mon[v]:
                m = self.mon[v]
                named.append((m["difficulty"], m.get("level", 0), v))
            else:
                unknown += 1
        if not values:
            return None
        diffs = [d for d, _l, _n in named + classes]
        hardest = max(named + classes, default=None)
        return {"count": len(values), "named": len(named),
                "classes": len(classes), "unknown": unknown,
                "max": hardest[0] if hardest else None,
                "hardest": hardest[2] if hardest else None,
                "mean": sum(diffs) / len(diffs) if diffs else None,
                "levels": sum(lv for _d, lv, _n in named),
                "depth": max(1, hardest[0]) if hardest else None}

    def difficulty_lines(self):
        d = self.difficulty()
        if d is None:
            return []
        lines = ["", _("Difficulté estimée :"),
                 _("  monstres comptés : %d (nommés %d, par classe %d, "
                   "aléatoires %d)") % (
                     d["count"], d["named"], d["classes"], d["unknown"])]
        if d["max"] is None:
            lines.append(_("  monstres tous aléatoires : ils suivront la "
                           "profondeur du niveau"))
            return lines
        lines.append(_("  le plus dur : %s (difficulté %d)") % (
            d["hardest"], d["max"]))
        lines.append(_("  difficulté moyenne : %.1f") % d["mean"])
        if d["named"]:
            lines.append(_("  somme des niveaux des monstres nommés : %d")
                         % d["levels"])
        lines.append(_("  profondeur conseillée : %d ou plus (là où NetHack "
                       "les ferait apparaître)") % d["depth"])
        return lines

    def show_stats(self):
        self.message_box(_("Statistiques du niveau"), self.stats_text())

    # --- fichiers à plusieurs cartes ------------------------------------
    def map_label(self, i, info):
        if info is None:
            return _("carte %d : texte calculé par le script") % (i + 1)
        place = (_("position x=%d y=%d") % tuple(info["pos"]) if info["pos"]
                 else "%s/%s" % (info["halign"], info["valign"]))
        return _("carte %d : %dx%d, %s") % (i + 1, info["w"], info["h"],
                                            place)

    def switch_map(self, i):
        """Passe à la carte n° i du fichier. Les modifications de la carte
        quittée sont reportées dans le texte ; l'historique continue (une
        annulation peut ramener à l'autre carte)."""
        if self.theme_guard():
            return False
        lvl = self.lvl
        if not 0 <= i < len(lvl.maps) or i == lvl.map_index:
            return False
        try:
            new = nhlevel.parse_level(lvl.to_lua(), i)[0]
        except ValueError as e:
            self.msg = str(e)
            return False
        self.lvl = new
        self.anchor = None
        if self.tool == "region":
            self.end_region()
        self.cx = self.cy = self.ox = self.oy = 0
        self.msg = _("Carte %d / %d (%dx%d).") % (i + 1, len(new.maps),
                                                   new.w, new.h)
        return True

    def theme_guard(self):
        if self.lvl.theme:
            self.msg = _("Une salle à thème n'a qu'une carte.")
            return True
        return False

    def maps_menu(self):
        """Liste des cartes du fichier : aller à une carte, en ajouter
        une, voir leur place dans le niveau."""
        lvl = self.lvl
        if self.theme_guard():
            return
        items = [(("● " if i == lvl.map_index else "  ")
                  + self.map_label(i, info), i)
                 for i, info in enumerate(lvl.maps)]
        if not lvl.maps:            # niveau neuf
            items = [("● " + _("carte 1 : %dx%d") % (lvl.w, lvl.h), 0)]
        items += [(_("+ ajouter une carte à la fin du fichier"), "add"),
                  (_("  place des cartes dans le niveau (80x21)"), "view")]
        try:
            what = self.pick(_("Cartes du fichier"), items, lvl.map_index)
        except Cancel:
            return
        if what == "add":
            self.add_map()
        elif what == "view":
            self.message_box(_("Place des cartes dans le niveau"),
                             self.maps_overview())
        else:
            self.switch_map(what)

    def add_map(self):
        if self.theme_guard():
            return
        s = self.prompt(_("Taille de la nouvelle carte (largeur x "
                          "hauteur) : "), "21x7")
        try:
            w, h = (int(v) for v in s.lower().replace(" ", "").split("x"))
            if not (1 <= w <= nhlevel.MAX_W and 1 <= h <= nhlevel.MAX_H):
                raise ValueError
        except ValueError:
            self.msg = _("Taille invalide.")
            return
        halign = self.pick(_("Placement horizontal"), [
            (v, v) for v in ("center", "left", "half-left", "half-right",
                             "right")])
        valign = self.pick(_("Placement vertical"), [
            (v, v) for v in ("center", "top", "bottom")])
        text = self.lvl.to_lua().rstrip("\n")
        text += ('\n\ndes.map({ halign = "%s", valign = "%s", map = [[\n%s\n'
                 ']] });\n' % (halign, valign,
                               "\n".join(["." * w] * h)))
        old = self.lvl
        try:
            # un niveau neuf n'a pas encore de liste de cartes
            new = nhlevel.parse_level(text, max(1, len(old.maps)))[0]
        except ValueError as e:
            self.msg = str(e)
            return
        self.checkpoint(_("Ajout de la carte %d") % len(new.maps))
        self.lvl = new
        self.anchor = None
        self.cx = self.cy = self.ox = self.oy = 0
        self.msg = _("Carte %d / %d ajoutée (%dx%d).") % (
            len(new.maps), len(new.maps), w, h)

    def maps_overview(self):
        """Dessin du niveau de 80x21 avec le cadre de chaque carte, marqué
        de son numéro (la carte éditée en #)."""
        grid = [["."] * nhlevel.COLNO for _r in range(nhlevel.ROWNO)]
        notes = []
        for i, info in enumerate(self.lvl.maps):
            tmp = Level(1, 1)
            if info:
                tmp.w, tmp.h = info["w"], info["h"]
                tmp.halign, tmp.valign = info["halign"], info["valign"]
                tmp.pos = info["pos"]
            o = tmp.origin() if info else None
            if o is None:
                notes.append(_("carte %d : position aléatoire ou inconnue")
                             % (i + 1))
                continue
            mark = "#" if i == self.lvl.map_index else str((i + 1) % 10)
            for y in range(o[1], o[1] + tmp.h):
                for x in range(o[0], o[0] + tmp.w):
                    if 0 <= x < nhlevel.COLNO and 0 <= y < nhlevel.ROWNO:
                        grid[y][x] = mark
        text = "\n".join("".join(r) for r in grid)
        return text + ("\n\n" + "\n".join(notes) if notes else "")

    def properties(self):
        sel = 0
        while True:
            lvl = self.lvl
            if lvl.pos:
                place = _("position fixe x=%d y=%d") % lvl.pos
            else:
                place = "halign=%s valign=%s" % (lvl.halign, lvl.valign)
                o = lvl.origin()
                place += (_(" -> coin en (%d,%d) du niveau") % o if o
                          else _(" -> position aléatoire"))
            if lvl.map_partial:
                place += _(" (fixé par le script)")
            items = [
                (_("Taille de la carte : %dx%d") % (lvl.w, lvl.h), "size"),
                (_("level_init : %s") % nhlevel.lua_value(lvl.init), "init"),
                (_("Drapeaux : %s") % (", ".join(lvl.flags) or _("(aucun)")),
                 "flags"),
                (_("Placement : %s") % place, "place"),
                (_("Carte éclairée (lit) : %s")
                 % (_("oui") if lvl.lit else _("non")), "lit"),
                (_("Donjon : placer le niveau dans dungeon.lua…"), "dungeon"),
            ]
            try:
                what = self.pick(_("Propriétés du niveau"), items,
                                 items[sel][1])
            except Cancel:
                return
            sel = [v for _, v in items].index(what)
            try:
                if what == "size":
                    self.ask_size()
                elif what == "init":
                    self.edit_init()
                elif what == "flags":
                    self.edit_flags()
                elif what == "place" and not lvl.map_partial:
                    self.edit_place()
                elif what == "lit":
                    self.checkpoint(_("Carte éclairée (lit) : %s") % (
                        _("non") if lvl.lit else _("oui")))
                    lvl.lit = not lvl.lit
                elif what == "dungeon":
                    self.edit_dungeon()
            except Cancel:
                pass

    def ask_size(self):
        s = self.prompt(_("Nouvelle taille « largeur hauteur » (max %dx%d) : ")
                        % (nhlevel.MAX_W, nhlevel.MAX_H),
                        "%d %d" % (self.lvl.w, self.lvl.h))
        try:
            w, h = (int(v) for v in s.replace("x", " ").split())
        except ValueError:
            self.msg = _("Taille invalide.")
            return
        self.checkpoint(_("Taille de la carte : %dx%d") % (w, h))
        self.lvl.resize(w, h)
        self.clamp_cursor()
        self.msg = _("Carte redimensionnée en %dx%d.") % (self.lvl.w,
                                                          self.lvl.h)

    def edit_init(self):
        styles = ["solidfill", "mazegrid", "maze", "rogue", "mines", "swamp"]
        cur = self.lvl.init
        style = self.pick(_("Style de level_init"), [(s, s) for s in styles],
                          cur.get("style", "solidfill"))
        init = {"style": style}
        if style in ("solidfill", "mazegrid"):
            fg = self.pick(_("Terrain de remplissage (fg)"),
                           [("%s  %s" % ("e" if c == " " else c, d), c)
                            for c, d in nhlevel.TERRAIN if c != "x"],
                           cur.get("fg", " "))
            init["fg"] = fg
        rest = {k: v for k, v in cur.items() if k not in ("style", "fg")}
        txt = ", ".join("%s = %s" % (k, nhlevel.lua_value(v))
                        for k, v in rest.items())
        s = self.prompt(_("Autres options de level_init (ex: lit=0) : "), txt)
        if s.strip():
            try:
                d = nhlevel._to_py(nhlevel.parse_lua_value("{" + s + "}"))
                if isinstance(d, dict):
                    init.update(d)
            except (nhlevel.NotLiteral, ValueError):
                self.msg = _("Options ignorées (syntaxe invalide).")
        self.checkpoint(_("level_init : %s") % nhlevel.lua_value(init))
        self.lvl.init = init

    def edit_flags(self):
        flags = list(self.lvl.flags)
        sel = 0
        while True:
            items = [("[%s] %s" % ("x" if f in flags else " ", f), f)
                     for f in nhlevel.LEVEL_FLAGS]
            items += [("[x] %s" % f, f) for f in flags
                      if f not in nhlevel.LEVEL_FLAGS]
            try:
                f = self.pick(_("Drapeaux (Entrée: cocher/décocher, "
                                "Échap: terminer)"), items, items[sel][1])
            except Cancel:
                break
            sel = [v for _, v in items].index(f)
            if f in flags:
                flags.remove(f)
            else:
                flags.append(f)
        if flags != self.lvl.flags:
            self.checkpoint(_("Drapeaux : %s") % (", ".join(flags)
                                                  or _("(aucun)")))
            self.lvl.flags = flags

    def edit_place(self):
        lvl = self.lvl
        mode = self.pick(_("Placement de la carte"),
                         [(_("alignement (halign/valign)"), "align"),
                          (_("position fixe (x, y)"), "pos")],
                         "pos" if lvl.pos else "align")
        if mode == "pos":
            s = self.prompt(_("Position « x y » : "),
                            "%d %d" % (lvl.pos or (1, 1)))
            try:
                x, y = (int(v) for v in s.split())
            except ValueError:
                self.msg = _("Position invalide.")
                return
            self.checkpoint(_("Placement : %s") % (
                _("position fixe x=%d y=%d") % (x, y)))
            lvl.pos = (x, y)
        else:
            h = self.pick(_("Alignement horizontal"),
                          [(a, a) for a in nhlevel.HALIGNS], lvl.halign)
            v = self.pick(_("Alignement vertical"),
                          [(a, a) for a in nhlevel.VALIGNS], lvl.valign)
            self.checkpoint(_("Placement : %s")
                            % ("halign=%s valign=%s" % (h, v)))
            lvl.pos, lvl.halign, lvl.valign = None, h, v

    def check(self):
        out = nhcheck.check(self.lvl, self.mon, self.obj)
        lua = self.lua_for_check()
        if lua:
            name = os.path.splitext(os.path.basename(
                self.path or "niveau"))[0]
            found = nhcheck.lua_check(self.lvl.to_lua(name), lua, self.data)
            out = [m for m in out if m != _("Aucun problème détecté.")] + (
                found or [_("- Lua : le script s'exécute sans erreur.")])
        else:
            out.append(_("- Vérification Lua indisponible : installez lua5.4 "
                         "ou indiquez l'interpréteur dans NHMAPEDIT_LUA."))
        self.message_box(_("Vérification"), "\n".join(out))

    def lua_for_check(self):
        """Interpréteur Lua ; propose (une fois) de compiler celui des
        sources de NetHack s'il n'y en a pas."""
        lua = nhcheck.find_lua()
        if lua or self.lua_refused or not nhcheck.lua_sources() \
                or not shutil.which("make"):
            return lua
        if not self.confirm(_("Pas d'interpréteur Lua : compiler celui des "
                              "sources de NetHack (quelques secondes) ?")):
            self.lua_refused = True
            return None
        self.msg = _("Compilation de Lua…")
        self.draw()
        try:
            lua = nhcheck.build_lua()
        except OSError as e:
            self.lua_refused = True
            self.message_box(_("Compilation de Lua"), _("Échec :\n%s") % e)
            return None
        self.msg = _("Lua compilé : %s") % lua
        return lua

    def open_file(self, path):
        if path.lower().endswith(".txt"):
            return self.import_text(path)
        try:
            with open(path, encoding="utf-8") as f:
                text = f.read()
            lvl = nhlevel.parse_level(text)[0]
        except ValueError as e:
            # pas de des.map au premier niveau : peut-être themerms.lua
            try:
                tf = nhtheme.ThemeFile(text)
            except ValueError:
                self.msg = _("Erreur à l'ouverture : %s") % e
                return False
            return self.open_theme(path, tf)
        except (OSError, UnicodeDecodeError) as e:
            self.msg = _("Erreur à l'ouverture : %s") % e
            return False
        self.set_level(lvl, path)
        self.offer_autosave()
        return True

    def import_text(self, path):
        """Ouvre une carte ASCII seule comme un nouveau niveau ; « s »
        l'enregistrera en .lua à côté du fichier texte."""
        try:
            with open(path, encoding="utf-8") as f:
                lvl = nhexport.import_text(f.read())
        except (OSError, ValueError, UnicodeDecodeError) as e:
            self.msg = _("Erreur à l'import : %s") % e
            return False
        lua = os.path.splitext(path)[0] + ".lua"
        self.set_level(lvl, None if os.path.exists(lua) else lua)
        self.mark_saved(False)
        self.msg = _("Carte importée de %s (%dx%d) ; s l'enregistre en "
                     "%s.") % (
            path, lvl.w, lvl.h, os.path.basename(self.path or "Lua"))
        return True

    def open_theme(self, path, tf):
        """Choisit une salle à thème (dessinée par des.map) à éditer, ou
        en crée une nouvelle."""
        items = tf.editable() + [(_("+ nouvelle salle à thème"), None)]
        try:
            what = self.pick(_("Salles à thème de %s (dessinées par des.map)")
                             % os.path.basename(path), items)
            if what is None:
                name = self.prompt(_("Nom de la nouvelle salle : ")).strip()
                if not name:
                    raise Cancel()
                if tf.find(name):
                    self.msg = _("La salle « %s » existe déjà.") % name
                    return False
                s = self.prompt(_("Taille « largeur hauteur » : "), "9 7")
                w, h = (max(3, int(v)) for v in s.replace("x", " ").split())
                rows = (["-" * w] + ["|" + "." * (w - 2) + "|"] * (h - 2)
                        + ["-" * w])
                theme = {"path": path, "name": name, "k": 0, "new": True}
                text = "\n".join(rows)
            else:
                name, k = what
                theme = {"path": path, "name": name, "k": k, "new": False}
                text = tf.map_text(name, k)
        except Cancel:
            return False
        except ValueError:
            self.msg = _("Taille invalide.")
            return False
        lvl = nhlevel.parse_level("des.map([[\n%s\n]]);" % text)[0]
        lvl.source, lvl.theme = None, theme
        self.set_level(lvl, path)
        self.mark_saved(not theme["new"])   # nouvelle : pas dans le fichier
        self.msg = (_("Salle à thème « %s » : seule la carte est éditée ; son "
                      "contenu (filler_region…) est conservé.") % name)
        return True

    def set_level(self, lvl, path):
        self.lvl, self.path = lvl, path
        self.undo_stack.clear()
        self.redo_stack.clear()
        self.mark_saved()
        self.cx = self.cy = self.ox = self.oy = 0
        self.anchor = None
        n = len(lvl.entities)
        self.msg = _("Ouvert : %s (%dx%d, %d entités%s).") % (
            path, lvl.w, lvl.h, n,
            _(", carte avec contenu : placement non modifiable")
            if lvl.map_partial else "")
        if len(lvl.maps) > 1:
            self.msg += _(" %d cartes : [ ] ou N pour changer.") % len(
                lvl.maps)
        return True

    def save(self, as_new=False):
        path = self.path
        if as_new or not path:
            path = self.prompt(_("Enregistrer sous : "), path or "",
                               self.path_completer)
            if not path.strip():
                raise Cancel()
            path = os.path.expanduser(path.strip())
            if os.path.splitext(path)[1].lower() not in EXPORTS:
                path += ".lua"
            if path != self.path and os.path.exists(path):
                if not self.confirm(_("%s existe. Écraser ?") % path):
                    raise Cancel()
            if not path.endswith(".lua"):
                return self.export(path)
        if self.lvl.theme and not as_new:
            return self.save_theme()
        name = os.path.splitext(os.path.basename(path))[0]
        try:
            text = self.lvl.to_lua(name)
            if os.path.exists(path) and not os.path.exists(path + "~"):
                os.replace(path, path + "~")    # sauvegarde de l'original
            with open(path, "w", encoding="utf-8") as f:
                f.write(text)
        except OSError as e:
            self.msg = _("Erreur d'écriture : %s") % e
            return False
        self.drop_autosave()        # celle de l'ancien nom
        self.path = path
        self.lvl.theme = None       # « enregistrer sous » : niveau à part
        self.mark_saved()
        self.drop_autosave()
        self.msg = _("Enregistré : %s") % path
        return True

    def export(self, path):
        """Exporte la carte seule (texte brut, image) sans changer le
        fichier en cours."""
        ext = os.path.splitext(path)[1].lower()
        try:
            if ext == ".txt":
                with open(path, "w", encoding="utf-8") as f:
                    f.write(nhexport.export_text(self.lvl))
            else:
                self.export_image(path)
        except (OSError, ValueError) as e:
            self.msg = _("Erreur d'export : %s") % e
            return False
        self.msg = _("Carte exportée : %s") % path
        return True

    # -- sauvegarde de secours ------------------------------------------
    def autosave_path(self):
        if self.path:
            return self.path + AUTOSAVE_SUFFIX
        return os.path.join(CACHE_DIR, "sans-nom" + AUTOSAVE_SUFFIX)

    def autosave(self, force=False):
        """Écrit la sauvegarde de secours si la carte est modifiée depuis
        plus de AUTOSAVE_DELAY secondes (les salles à thème exceptées)."""
        now = time.time()
        if not self.modified or self.lvl.theme or self.autosave_delay <= 0:
            return
        if not force and now - self.autosave_time < self.autosave_delay:
            return
        self.autosave_time = now
        path = self.autosave_path()
        try:
            os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                f.write(self.lvl.to_lua(os.path.splitext(
                    os.path.basename(self.path or "sans-nom"))[0]))
        except OSError:
            pass                    # une sauvegarde de secours ratée
            #                         ne doit pas gêner l'édition

    def drop_autosave(self):
        try:
            os.remove(self.autosave_path())
        except OSError:
            pass

    def offer_autosave(self):
        """Après une ouverture : propose de récupérer une sauvegarde de
        secours plus récente que le fichier (session interrompue)."""
        auto = self.autosave_path()
        if self.scr is None or not os.path.exists(auto):
            return
        if self.path and os.path.exists(self.path) and \
                os.path.getmtime(auto) <= os.path.getmtime(self.path):
            self.drop_autosave()        # périmée : le fichier est plus récent
            return
        when = time.strftime("%d/%m/%Y %H:%M",
                             time.localtime(os.path.getmtime(auto)))
        if not self.confirm(_("Sauvegarde de secours du %s trouvée (session "
                              "interrompue). La récupérer ?") % when):
            self.drop_autosave()
            return
        try:
            with open(auto, encoding="utf-8") as f:
                lvl = nhlevel.parse_level(f.read())[0]
        except (OSError, ValueError) as e:
            self.msg = _("Sauvegarde de secours illisible : %s") % e
            return
        path = self.path
        self.set_level(lvl, path)
        self.mark_saved(False)
        self.msg = (_("Sauvegarde de secours récupérée ; s pour l'enregistrer "
                      "dans %s.") % (path or _("un fichier")))

    def save_theme(self):
        """Remplace la carte de la salle dans themerms.lua (ou ajoute la
        salle) ; le reste du fichier ne change pas."""
        th, path = self.lvl.theme, self.lvl.theme["path"]
        try:
            with open(path, encoding="utf-8") as f:
                tf = nhtheme.ThemeFile(f.read())
            new = self.lvl.map_text()
            if th["new"] and not tf.find(th["name"]):
                text = tf.add_room(th["name"], new)
            elif tf.find(th["name"]) and th["k"] < len(
                    tf.find(th["name"])["maps"]):
                text = tf.replace_map(th["name"], th["k"], new)
            else:
                self.msg = _("Salle « %s » introuvable dans %s.") % (
                    th["name"], path)
                return False
            if not os.path.exists(path + "~"):
                shutil.copy2(path, path + "~")
            with open(path, "w", encoding="utf-8") as f:
                f.write(text)
        except (OSError, ValueError) as e:
            self.msg = _("Erreur d'enregistrement : %s") % e
            return False
        th["new"] = False
        self.mark_saved()
        self.msg = _("Enregistré : salle « %s » dans %s") % (th["name"], path)
        if self.lvl.entities:
            self.msg += _(" (sans les entités)")
        return True

    def check_unsaved(self):
        if not self.modified:
            return True
        r = self.prompt(_("Modifications non enregistrées. Enregistrer ? "
                          "(o/n, Échap annule) "))
        r = r.strip().lower()
        if r in ("o", "oui", "y", "yes"):
            return self.save()
        if r in ("n", "non", "no"):
            return True
        raise Cancel()

    def ask_int(self, label, default, lo, hi):
        s = self.prompt("%s (%d-%d) : " % (label, lo, hi), str(default))
        try:
            return max(lo, min(hi, int(s)))
        except ValueError:
            return default

    def level_wizard(self, w, h, rng=None):
        """Assistant : un niveau complet en quelques questions, construit
        par nhgen ; None si la carte est trop petite."""
        if w < 12 or h < 6:
            self.msg = _("Assistant : 12x6 au moins.")
            return None
        rng = rng or random.Random()
        kind = self.pick(_("Assistant : genre de niveau"), [
            (_("salles reliées par des couloirs"), "rooms"),
            (_("labyrinthe (comme Géhenne)"), "maze"),
            (_("caverne (comme les Mines)"), "cave"),
            (_("grande salle (piliers, fontaines, arbres…)"), "big")])
        area = w * h
        if kind == "rooms":
            n = self.ask_int(_("Nombre de salles"), max(2, area // 180), 2, 12)
            grid, rooms = nhgen.rooms_and_corridors(w, h, n, rng)
            what = _("%d salles") % len(rooms)
        elif kind == "maze":
            loops = self.ask_int(_("Boucles en % (0 : labyrinthe parfait)"),
                                 10, 0, 100)
            grid = nhgen.maze(w, h, rng, "-", loops)
            what = _("labyrinthe")
        elif kind == "cave":
            fill = self.ask_int(_("Roche au départ en % (plus : caverne plus "
                                  "étroite)"), 45, 30, 60)
            grid = nhgen.cave(w, h, rng, fill)
            what = _("caverne")
        else:
            n = self.ask_int(_("Éléments de décor"), max(4, area // 120),
                             0, 60)
            grid = nhgen.big_room(w, h, rng, n)
            what = _("grande salle")
        floor = sum(row.count(".") for row in grid)
        mons = self.ask_int(_("Monstres (aléatoires)"),
                            max(2, floor // 60), 0, 60)
        objs = self.ask_int(_("Objets (aléatoires)"), max(2, floor // 80),
                            0, 60)
        traps = self.ask_int(_("Pièges (aléatoires)"), max(1, floor // 150),
                             0, 30)
        lit = self.pick(_("Éclairage"), [(_("éclairé"), True),
                                         (_("sombre"), False)],
                        kind in ("rooms", "big"))
        lvl = Level(w, h)
        lvl.grid = grid
        lvl.lit = lit
        lvl.flags = ["mazelevel"] if kind == "maze" else []
        for k, x, y, v in nhgen.populate(grid, rng, mons, objs, traps):
            lvl.entities.append(Entity(k, x, y, v))
        self.wizard_summary = _("Assistant : %s, %d monstre(s), %d objet(s), "
                                "%d piège(s), escaliers aux deux bouts.") % (
            what, mons, objs, traps)
        return lvl

    def new_level(self):
        self.check_unsaved()
        s = self.prompt(_("Nouvelle carte « largeur hauteur » : "), "75 19")
        try:
            w, h = (int(v) for v in s.replace("x", " ").split())
        except ValueError:
            self.msg = _("Taille invalide.")
            return
        fill = self.pick(_("Remplir avec"), [
            (_("roche (espace)"), " "), (_("sol de salle (.)"), "."),
            (_("salle entourée de murs"), "room"),
            (_("assistant : niveau complet prêt à essayer…"), "wizard")])
        w, h = max(1, min(w, nhlevel.MAX_W)), max(1, min(h, nhlevel.MAX_H))
        if fill == "wizard":
            lvl = self.level_wizard(w, h)
            if lvl is None:
                return
        self.lvl = lvl if fill == "wizard" else Level(w, h)
        if fill == ".":
            self.lvl.grid = [["."] * self.lvl.w for _ in range(self.lvl.h)]
        elif fill == "room":
            t, self.tool = self.tool, "room"
            for (x, y), c in self.shape_cells(
                    (0, 0), (self.lvl.w - 1, self.lvl.h - 1)).items():
                self.lvl.set(x, y, c)
            self.tool = t
        self.path = None
        self.undo_stack.clear()
        self.redo_stack.clear()
        self.mark_saved()
        self.cx = self.cy = self.ox = self.oy = 0
        self.msg = _("Nouvelle carte %dx%d.") % (self.lvl.w, self.lvl.h)
        if fill == "wizard":
            self.msg = self.wizard_summary + _(" t pour l'essayer.")
