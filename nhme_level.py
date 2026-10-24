"""Propriétés du niveau, vérification, fichiers et salles à thème."""

import os
import shutil
import time

import nhcheck
import nhexport
import nhlevel
import nhtheme
from nhlevel import Level
from nhme_common import (
    AUTOSAVE_SUFFIX, CACHE_DIR, Cancel, EXPORTS)


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
        out = nhcheck.check(self.lvl, self.mon, self.obj)
        lua = self.lua_for_check()
        if lua:
            name = os.path.splitext(os.path.basename(
                self.path or "niveau"))[0]
            found = nhcheck.lua_check(self.lvl.to_lua(name), lua, self.data)
            out = [m for m in out if m != "Aucun problème détecté."] + (
                found or ["- Lua : le script s'exécute sans erreur."])
        else:
            out.append("- Vérification Lua indisponible : installez lua5.4 "
                       "ou indiquez l'interpréteur dans NHMAPEDIT_LUA.")
        self.message_box("Vérification", "\n".join(out))

    def lua_for_check(self):
        """Interpréteur Lua ; propose (une fois) de compiler celui des
        sources de NetHack s'il n'y en a pas."""
        lua = nhcheck.find_lua()
        if lua or self.lua_refused or not nhcheck.lua_sources() \
                or not shutil.which("make"):
            return lua
        if not self.confirm("Pas d'interpréteur Lua : compiler celui des "
                            "sources de NetHack (quelques secondes) ?"):
            self.lua_refused = True
            return None
        self.msg = "Compilation de Lua…"
        self.draw()
        try:
            lua = nhcheck.build_lua()
        except OSError as e:
            self.lua_refused = True
            self.message_box("Compilation de Lua", "Échec :\n%s" % e)
            return None
        self.msg = "Lua compilé : %s" % lua
        return lua

    def open_file(self, path):
        if path.lower().endswith(".txt"):
            return self.import_text(path)
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
            self.msg = "Erreur à l'import : %s" % e
            return False
        lua = os.path.splitext(path)[0] + ".lua"
        self.set_level(lvl, None if os.path.exists(lua) else lua)
        self.modified = True
        self.msg = "Carte importée de %s (%dx%d) ; s l'enregistre en %s." % (
            path, lvl.w, lvl.h, os.path.basename(self.path or "Lua"))
        return True

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
            if os.path.splitext(path)[1].lower() not in EXPORTS:
                path += ".lua"
            if path != self.path and os.path.exists(path):
                if not self.confirm("%s existe. Écraser ?" % path):
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
            self.msg = "Erreur d'écriture : %s" % e
            return False
        self.drop_autosave()        # celle de l'ancien nom
        self.path = path
        self.lvl.theme = None       # « enregistrer sous » : niveau à part
        self.modified = False
        self.drop_autosave()
        self.msg = "Enregistré : %s" % path
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
            self.msg = "Erreur d'export : %s" % e
            return False
        self.msg = "Carte exportée : %s" % path
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
        if not self.confirm("Sauvegarde de secours du %s trouvée (session "
                            "interrompue). La récupérer ?" % when):
            self.drop_autosave()
            return
        try:
            with open(auto, encoding="utf-8") as f:
                lvl = nhlevel.parse_level(f.read())[0]
        except (OSError, ValueError) as e:
            self.msg = "Sauvegarde de secours illisible : %s" % e
            return
        path = self.path
        self.set_level(lvl, path)
        self.modified = True
        self.msg = ("Sauvegarde de secours récupérée ; s pour l'enregistrer "
                    "dans %s." % (path or "un fichier"))

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
