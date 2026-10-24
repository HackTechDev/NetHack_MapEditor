"""Propriétés du niveau, vérification, fichiers et salles à thème."""

import os
import shutil

import nhcheck
import nhlevel
import nhtheme
from nhlevel import Level
from nhme_common import Cancel, FLIP_NAME, SOLID


class LevelMixin:
    """Méthodes de l'éditeur (voir nhmapedit.Editor)."""

    def properties(self):
        sel = 0
        while True:
            lvl = self.lvl
            if lvl.pos:
                place = "position fixe x=%d y=%d" % lvl.pos
            else:
                place = "halign=%s valign=%s" % (lvl.halign, lvl.valign)
                o = lvl.origin()
                place += (" -> coin en (%d,%d) du niveau" % o if o
                          else " -> position aléatoire")
            if lvl.map_partial:
                place += " (fixé par le script)"
            items = [
                ("Taille de la carte : %dx%d" % (lvl.w, lvl.h), "size"),
                ("level_init : %s" % nhlevel.lua_value(lvl.init), "init"),
                ("Drapeaux : %s" % (", ".join(lvl.flags) or "(aucun)"),
                 "flags"),
                ("Placement : %s" % place, "place"),
                ("Carte éclairée (lit) : %s" % ("oui" if lvl.lit else "non"),
                 "lit"),
                ("Donjon : placer le niveau dans dungeon.lua…", "dungeon"),
            ]
            try:
                what = self.pick("Propriétés du niveau", items,
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
                    self.checkpoint()
                    lvl.lit = not lvl.lit
                elif what == "dungeon":
                    self.edit_dungeon()
            except Cancel:
                pass

    def ask_size(self):
        s = self.prompt("Nouvelle taille « largeur hauteur » (max %dx%d) : "
                        % (nhlevel.MAX_W, nhlevel.MAX_H),
                        "%d %d" % (self.lvl.w, self.lvl.h))
        try:
            w, h = (int(v) for v in s.replace("x", " ").split())
        except ValueError:
            self.msg = "Taille invalide."
            return
        self.checkpoint()
        self.lvl.resize(w, h)
        self.clamp_cursor()
        self.msg = "Carte redimensionnée en %dx%d." % (self.lvl.w, self.lvl.h)

    def edit_init(self):
        styles = ["solidfill", "mazegrid", "maze", "rogue", "mines", "swamp"]
        cur = self.lvl.init
        style = self.pick("Style de level_init", [(s, s) for s in styles],
                          cur.get("style", "solidfill"))
        init = {"style": style}
        if style in ("solidfill", "mazegrid"):
            fg = self.pick("Terrain de remplissage (fg)",
                           [("%s  %s" % ("e" if c == " " else c, d), c)
                            for c, d in nhlevel.TERRAIN if c != "x"],
                           cur.get("fg", " "))
            init["fg"] = fg
        rest = {k: v for k, v in cur.items() if k not in ("style", "fg")}
        txt = ", ".join("%s = %s" % (k, nhlevel.lua_value(v))
                        for k, v in rest.items())
        s = self.prompt("Autres options de level_init (ex: lit=0) : ", txt)
        if s.strip():
            try:
                d = nhlevel._to_py(nhlevel.parse_lua_value("{" + s + "}"))
                if isinstance(d, dict):
                    init.update(d)
            except (nhlevel.NotLiteral, ValueError):
                self.msg = "Options ignorées (syntaxe invalide)."
        self.checkpoint()
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
                f = self.pick("Drapeaux (Entrée: cocher/décocher, "
                              "Échap: terminer)", items, items[sel][1])
            except Cancel:
                break
            sel = [v for _, v in items].index(f)
            if f in flags:
                flags.remove(f)
            else:
                flags.append(f)
        if flags != self.lvl.flags:
            self.checkpoint()
            self.lvl.flags = flags

    def edit_place(self):
        lvl = self.lvl
        mode = self.pick("Placement de la carte",
                         [("alignement (halign/valign)", "align"),
                          ("position fixe (x, y)", "pos")],
                         "pos" if lvl.pos else "align")
        if mode == "pos":
            s = self.prompt("Position « x y » : ",
                            "%d %d" % (lvl.pos or (1, 1)))
            try:
                x, y = (int(v) for v in s.split())
            except ValueError:
                self.msg = "Position invalide."
                return
            self.checkpoint()
            lvl.pos = (x, y)
        else:
            h = self.pick("Alignement horizontal",
                          [(a, a) for a in nhlevel.HALIGNS], lvl.halign)
            v = self.pick("Alignement vertical",
                          [(a, a) for a in nhlevel.VALIGNS], lvl.valign)
            self.checkpoint()
            lvl.pos, lvl.halign, lvl.valign = None, h, v

    def check(self):
        lvl, out = self.lvl, []
        if lvl.w > nhlevel.MAP_X_LIM:
            out.append("! Largeur %d > %d (MAP_X_LIM) : risque de refus "
                       "par NetHack." % (lvl.w, nhlevel.MAP_X_LIM))
        o = lvl.origin()
        if o:
            x, y = o
            if x < 1 or x + lvl.w > nhlevel.COLNO or y < 0 \
                    or y + lvl.h > nhlevel.ROWNO:
                out.append("! La carte placée en (%d,%d) déborde du niveau "
                           "(80x21)." % (x, y))
        if lvl.allowed_flips():
            out.append("- NetHack peut retourner ce niveau au chargement (%s) "
                       ": f pour un aperçu, drapeau noflip pour l'empêcher."
                       % FLIP_NAME[lvl.allowed_flips()])
        kinds = [(e.kind, e.value) for e in lvl.entities]
        for d, lab in (("up", "montant"), ("down", "descendant")):
            if ("stair", d) not in kinds and ("ladder", d) not in kinds:
                out.append("- Pas d'escalier/échelle %s à position fixe "
                           "(peut être placé ailleurs dans le script)." % lab)
        for e in lvl.entities:
            t = lvl.grid[e.y][e.x]
            if e.kind == "door":
                if t not in "+S":
                    out.append("! Porte en (%d,%d) sur '%s'." % (e.x, e.y, t))
            elif t in SOLID:
                out.append("! %s en (%d,%d) sur du terrain solide '%s'." % (
                    e.describe(), e.x, e.y, t))
            if e.kind == "monster" and e.value and len(e.value) > 1 \
                    and self.mon and e.value not in self.mon:
                out.append("? Monstre inconnu : %s" % e.value)
            if e.kind == "object" and e.value and len(e.value) > 1 \
                    and self.obj and e.value not in self.obj:
                out.append("? Objet inconnu (vérifiez le nom) : %s"
                           % e.value)
        seen = {}
        for e in lvl.entities:
            if e.kind in ("stair", "ladder"):
                seen.setdefault((e.kind, e.value), []).append(e)
        for (k, v), lst in seen.items():
            if len(lst) > 1:
                out.append("! %d %ss %s : un seul est permis par niveau."
                           % (len(lst), nhlevel.ENTITY_LABEL[k], v))
        for y in range(lvl.h):
            for x in range(lvl.w):
                if lvl.grid[y][x] == "+":
                    h = (x > 0 and lvl.grid[y][x - 1] in "-|"
                         and x < lvl.w - 1 and lvl.grid[y][x + 1] in "-|")
                    v = (y > 0 and lvl.grid[y - 1][x] in "-|"
                         and y < lvl.h - 1 and lvl.grid[y + 1][x] in "-|")
                    if not (h or v):
                        out.append("? Porte en (%d,%d) qui n'est pas "
                                   "encadrée par des murs." % (x, y))
        out += nhcheck.connectivity(lvl)
        if not out:
            out = ["Aucun problème détecté."]
        self.message_box("Vérification", "\n".join(out))

    def open_file(self, path):
        try:
            with open(path, encoding="utf-8") as f:
                text = f.read()
            lvl, _ = nhlevel.parse_level(text)
        except ValueError as e:
            # pas de des.map au premier niveau : peut-être themerms.lua
            try:
                tf = nhtheme.ThemeFile(text)
            except ValueError:
                self.msg = "Erreur à l'ouverture : %s" % e
                return False
            return self.open_theme(path, tf)
        except (OSError, UnicodeDecodeError) as e:
            self.msg = "Erreur à l'ouverture : %s" % e
            return False
        return self.set_level(lvl, path)

    def open_theme(self, path, tf):
        """Choisit une salle à thème (dessinée par des.map) à éditer, ou
        en crée une nouvelle."""
        items = tf.editable() + [("+ nouvelle salle à thème", None)]
        try:
            what = self.pick("Salles à thème de %s (dessinées par des.map)"
                             % os.path.basename(path), items)
            if what is None:
                name = self.prompt("Nom de la nouvelle salle : ").strip()
                if not name:
                    raise Cancel()
                if tf.find(name):
                    self.msg = "La salle « %s » existe déjà." % name
                    return False
                s = self.prompt("Taille « largeur hauteur » : ", "9 7")
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
            self.msg = "Taille invalide."
            return False
        lvl = nhlevel.parse_level("des.map([[\n%s\n]]);" % text)[0]
        lvl.source, lvl.theme = None, theme
        self.set_level(lvl, path)
        self.modified = theme["new"]    # pas encore dans le fichier
        self.msg = ("Salle à thème « %s » : seule la carte est éditée ; son "
                    "contenu (filler_region…) est conservé." % name)
        return True

    def set_level(self, lvl, path):
        self.lvl, self.path = lvl, path
        self.modified = False
        self.undo_stack.clear()
        self.redo_stack.clear()
        self.cx = self.cy = self.ox = self.oy = 0
        self.anchor = None
        n = len(lvl.entities)
        self.msg = "Ouvert : %s (%dx%d, %d entités%s)." % (
            path, lvl.w, lvl.h, n,
            ", carte avec contenu : placement non modifiable"
            if lvl.map_partial else "")
        return True

    def save(self, as_new=False):
        path = self.path
        if as_new or not path:
            path = self.prompt("Enregistrer sous : ", path or "",
                               self.path_completer)
            if not path.strip():
                raise Cancel()
            path = os.path.expanduser(path.strip())
            if not path.endswith(".lua"):
                path += ".lua"
            if path != self.path and os.path.exists(path):
                if not self.confirm("%s existe. Écraser ?" % path):
                    raise Cancel()
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
            self.msg = "Erreur d'écriture : %s" % e
            return False
        self.path = path
        self.lvl.theme = None       # « enregistrer sous » : niveau à part
        self.modified = False
        self.msg = "Enregistré : %s" % path
        return True

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
                self.msg = "Salle « %s » introuvable dans %s." % (
                    th["name"], path)
                return False
            if not os.path.exists(path + "~"):
                shutil.copy2(path, path + "~")
            with open(path, "w", encoding="utf-8") as f:
                f.write(text)
        except (OSError, ValueError) as e:
            self.msg = "Erreur d'enregistrement : %s" % e
            return False
        th["new"] = False
        self.modified = False
        self.msg = "Enregistré : salle « %s » dans %s" % (th["name"], path)
        if self.lvl.entities:
            self.msg += " (sans les entités)"
        return True

    def check_unsaved(self):
        if not self.modified:
            return True
        r = self.prompt("Modifications non enregistrées. Enregistrer ? "
                        "(o/n, Échap annule) ")
        r = r.strip().lower()
        if r in ("o", "oui", "y", "yes"):
            return self.save()
        if r in ("n", "non", "no"):
            return True
        raise Cancel()

    def new_level(self):
        self.check_unsaved()
        s = self.prompt("Nouvelle carte « largeur hauteur » : ", "75 19")
        try:
            w, h = (int(v) for v in s.replace("x", " ").split())
        except ValueError:
            self.msg = "Taille invalide."
            return
        fill = self.pick("Remplir avec", [
            ("roche (espace)", " "), ("sol de salle (.)", "."),
            ("salle entourée de murs", "room")])
        self.lvl = Level(min(w, nhlevel.MAX_W), min(h, nhlevel.MAX_H))
        if fill == ".":
            self.lvl.grid = [["."] * self.lvl.w for _ in range(self.lvl.h)]
        elif fill == "room":
            t, self.tool = self.tool, "room"
            for (x, y), c in self.shape_cells(
                    (0, 0), (self.lvl.w - 1, self.lvl.h - 1)).items():
                self.lvl.set(x, y, c)
            self.tool = t
        self.path = None
        self.modified = False
        self.undo_stack.clear()
        self.redo_stack.clear()
        self.cx = self.cy = self.ox = self.oy = 0
        self.msg = "Nouvelle carte %dx%d." % (self.lvl.w, self.lvl.h)
