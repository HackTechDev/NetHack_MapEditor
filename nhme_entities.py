"""Entités : placement, formulaires d'options, contenus, liste."""

import collections
import copy

import nhlevel
from nhi18n import _
from nhlevel import Entity
from nhme_common import (
    Cancel, MON_FORM, OBJ_FORM, REGION_FORMS, REGION_MARK)


class EntitiesMixin:
    """Méthodes de l'éditeur (voir nhmapedit.Editor)."""

    def ask_extra(self, current=None):
        txt = ""
        if current:
            txt = ", ".join("%s = %s" % (k, nhlevel.lua_value(v))
                            for k, v in current.items())
        while True:
            s = self.prompt(_("Options Lua (ex: peaceful=1, asleep=1) : "),
                            txt)
            if not s.strip():
                return {}
            try:
                t = nhlevel.parse_lua_value("{" + s + "}")
                d = nhlevel._to_py(t)
                if isinstance(d, dict):
                    return d
            except (nhlevel.NotLiteral, ValueError):
                pass
            txt = s
            self.msg = _("Syntaxe invalide : clé = valeur, séparées par des "
                         "virgules.")

    def edit_options(self, kind, extra):
        """Formulaire des options courantes d'un monstre ou d'un objet."""
        return self.form(_("Options du monstre") if kind == "monster"
                         else _("Options de l'objet"),
                         MON_FORM if kind == "monster" else OBJ_FORM, extra)

    def edit_contents(self, cont, title):
        """Liste des objets d'un contenu ou d'un inventaire.

        Renvoie un nouveau Contents, ou None pour retirer l'option."""
        existed = cont is not None
        cont = copy.deepcopy(cont) if existed else nhlevel.Contents()
        sel = 0
        while True:
            items = [("%s %s" % (self.entity_glyph(it)[0], it.describe()), i)
                     for i, it in enumerate(cont.items)]
            items.append((_("+ ajouter un objet"), "add"))
            if existed:
                items.append((_("- retirer l'option"), "remove"))
            hint = _("Entrée/e: modifier  d: supprimer  Échap: terminer")
            try:
                i, action = self.pick_action(title, items, sel, hint)
            except Cancel:
                return cont if cont.items or existed else None
            if i == "remove":
                return None
            try:
                if i == "add":
                    value, extra = self.edit_entity_fields("object")
                    cont.items.append(Entity("object", None, None, value,
                                             extra))
                    sel = len(cont.items) - 1
                elif action == "delete":
                    del cont.items[i]
                    sel = max(0, i - 1)
                else:
                    it = cont.items[i]
                    it.value, it.extra = self.edit_entity_fields(
                        "object", it.value, it.extra)
                    sel = i
            except Cancel:
                pass

    def pick_value(self, kind, value=None):
        """Valeur principale d'une entité (monstre, type de piège,
        direction…), demandée selon son genre."""
        if kind in ("stair", "ladder"):
            return self.pick(_("Direction"), [(_("montant (up)"), "up"),
                                              (_("descendant (down)"),
                                               "down")], value)
        if kind == "altar":
            return self.pick(_("Alignement de l'autel"),
                             [(a, a) for a in nhlevel.ALTAR_ALIGNS], value)
        if kind == "monster":
            items = [(_("(aléatoire)"), None)] + [
                ("%s  %s" % (m["sym"], m["name"]), m["name"])
                for m in self.data["monsters"]]
            return self.pick(_("Monstre (tapez pour filtrer ; une lettre "
                               "seule = classe)"), items, value, custom=True)
        if kind == "object":
            items = [(_("(aléatoire)"), None)] + [
                ("%s  %s" % (o["sym"], o["name"]), o["name"])
                for o in self.data["objects"]]
            return self.pick(_("Objet (tapez pour filtrer ; un symbole "
                               "seul = classe)"), items, value, custom=True)
        if kind == "trap":
            return self.pick(_("Type de piège"),
                             [(t, t) for t in self.data["traps"]], value)
        if kind == "door":
            return self.pick(_("État de la porte"),
                             [(s, s) for s in nhlevel.DOOR_STATES], value)
        if kind == "engraving":
            return self.prompt(_("Texte gravé : "), value or "Elbereth")
        if kind == "gold":
            s = self.prompt(_("Montant (vide : aléatoire) : "),
                            "" if value is None else str(value)).strip()
            try:
                return int(s) if s else None
            except ValueError:
                return None
        if kind == "grave":
            return self.prompt(_("Épitaphe (vide : aléatoire) : "),
                               value or "").strip() or None
        if kind == "drawbridge":
            return self.pick(_("Côté du mur où le pont s'abaisse"),
                             [(d, d) for d in nhlevel.DRAWBRIDGE_DIRS],
                             value or "random")
        if kind == "feature":
            return self.pick(_("Élément de décor"),
                             [("%s  %s" % (c, f), f)
                              for f, c in nhlevel.FEATURES.items()], value)
        if kind == "terrain":
            return self.pick(_("Terrain de la case"),
                             [("%s  %s" % ("e" if c == " " else c, d), c)
                              for c, d in nhlevel.TERRAIN if c != "x"],
                             value)
        return value

    def edit_entity_fields(self, kind, value=None, extra=None):
        """Demande les paramètres d'une entité. Renvoie (value, extra)."""
        extra = dict(extra or {})
        if kind == "engraving":
            etype = self.pick(_("Type de gravure"),
                              [(t, t) for t in nhlevel.ENGRAVING_TYPES],
                              extra.get("type", "engrave"))
        value = self.pick_value(kind, value)
        if kind == "altar":
            extra["type"] = self.pick(
                _("Type d'autel"), [(t, t) for t in nhlevel.ALTAR_TYPES],
                extra.get("type", "altar"))
        elif kind in ("monster", "object"):
            extra = self.edit_options(kind, extra)
        elif kind == "engraving":
            extra.pop("type", None)
            extra = dict(type=etype, **extra)
        elif kind == "drawbridge":
            extra["state"] = self.pick(
                _("État du pont-levis"),
                [(s, s) for s in nhlevel.DRAWBRIDGE_STATES],
                extra.get("state", "random"))
        return value, extra

    def find_replace(self, ents=None):
        """Rechercher et remplacer (touche /) : choisit un genre et une
        valeur parmi les entités (toutes, ou ents : une sélection), puis
        remplace la valeur, pose ou retire une option, ou supprime."""
        pool = self.lvl.entities if ents is None else ents
        if not pool:
            self.msg = _("Aucune entité.")
            return
        count = collections.Counter(e.kind for e in pool)
        kind = self.pick(_("Rechercher : genre d'entité"), [
            ("%s (%d)" % (nhlevel.ENTITY_LABEL[k], count[k]), k)
            for k in nhlevel.ENTITY_KINDS if count[k]])
        same = [e for e in pool if e.kind == kind]
        vals = collections.Counter(repr(e.value) for e in same)
        shown = {repr(e.value): e.value for e in same}
        any_ = "\0"
        key = self.pick(_("Rechercher : valeur"), [
            (_("(toutes les valeurs) (%d)") % len(same), any_)] + [
            ("%s (%d)" % (_("(aléatoire)") if shown[k] is None
                          else shown[k], n), k)
            for k, n in sorted(vals.items(), key=lambda kv: -kv[1])])
        found = [e for e in same if key == any_ or repr(e.value) == key]
        what = (nhlevel.ENTITY_LABEL[kind] if key == any_ else
                "%s %s" % (nhlevel.ENTITY_LABEL[kind],
                           _("aléatoire") if shown[key] is None
                           else shown[key]))
        action = self.pick(_("%d × %s : que faire ?") % (len(found), what), [
            (_("remplacer la valeur par…"), "value"),
            (_("poser ou modifier des options (ex. asleep=1)…"), "set"),
            (_("retirer une option…"), "unset"),
            (_("supprimer ces entités"), "delete")])
        if action == "value":
            new = self.pick_value(kind, None if key == any_ else shown[key])
            self.checkpoint(_("Remplacer : %s → %s (%d)") % (
                what, new, len(found)))
            for e in found:
                e.value = new
        elif action == "set":
            opts = self.ask_extra()
            if not opts:
                return
            self.checkpoint(_("Options : %s (%d)") % (what, len(found)))
            for e in found:
                e.extra.update(copy.deepcopy(opts))
        elif action == "unset":
            keys = sorted({k for e in found for k in e.extra})
            if not keys:
                self.msg = _("Ces entités n'ont aucune option.")
                return
            opt = self.pick(_("Option à retirer"), [(k, k) for k in keys])
            self.checkpoint(_("Retrait de %s : %s (%d)") % (opt, what,
                                                            len(found)))
            for e in found:
                e.extra.pop(opt, None)
        else:
            self.checkpoint(_("Suppression : %s (%d)") % (what, len(found)))
            for e in found:
                self.lvl.entities.remove(e)
                if ents is not None:
                    ents.remove(e)
        self.msg = _("%d entité(s) modifiée(s) : %s.") % (len(found), what)

    def place_entity(self):
        if self.no_entities():
            return
        kinds = [("%s" % nhlevel.ENTITY_LABEL[k].capitalize(), k)
                 for k in nhlevel.ENTITY_KINDS]
        kinds += [("[%s] %s (des.%s)" % (REGION_MARK[k],
                                         nhlevel.REGION_LABEL[k].capitalize(),
                                         k), k)
                  for k in nhlevel.REGION_KINDS]
        kind = self.pick(_("Placer une entité en (%d,%d)")
                         % (self.cx, self.cy), kinds)
        if kind in nhlevel.REGION_KINDS:
            self.start_region(kind)
            return
        value, extra = self.edit_entity_fields(kind)
        self.add_entity(Entity(kind, self.cx, self.cy, value, extra))

    def no_entities(self):
        """Une salle à thème n'enregistre que sa carte."""
        if self.lvl.theme:
            self.msg = (_("Salle à thème : seule la carte est enregistrée, "
                          "pas les entités."))
            return True
        return False

    def add_entity(self, e):
        e.x, e.y = self.cx, self.cy
        self.checkpoint(_("Ajout : %s") % e.describe())
        if e.kind in ("stair", "ladder", "altar", "door"):
            # une seule de ces entités par case
            self.lvl.entities = [o for o in self.lvl.entities if not (
                o.x == e.x and o.y == e.y and o.kind in
                ("stair", "ladder", "altar", "door"))]
        if e.kind == "door" and self.lvl.grid[e.y][e.x] not in "+S":
            self.lvl.set(e.x, e.y, "+")
        self.lvl.entities.append(e)
        self.template = e.copy()
        self.template.origin = None
        self.msg = _("Ajouté : %s (r pour répéter).") % e.describe()

    def delete_entities(self):
        ents = self.lvl.entities_at(self.cx, self.cy)
        if not ents:
            self.msg = _("Aucune entité ici.")
            return
        self.checkpoint(_("Suppression : %s")
                        % " ; ".join(e.describe() for e in ents))
        self.lvl.entities = [e for e in self.lvl.entities if e not in ents]
        self.msg = _("%d entité(s) supprimée(s).") % len(ents)

    def annotate(self):
        """Touche \" : annotation de la case ou d'une de ses entités,
        enregistrée en commentaire Lua (texte vide : la retire)."""
        x, y = self.cx, self.cy
        ents = self.lvl.entities_at(x, y)
        target = None
        if ents:
            items = [(_("la case (%d,%d)") % (x, y)
                      + (" — « %s »" % self.lvl.notes[(x, y)]
                         if (x, y) in self.lvl.notes else ""), None)]
            items += [(e.describe(), i) for i, e in enumerate(ents)]
            i = self.pick(_("Annoter quoi ?"), items, 0)
            target = ents[i] if i is not None else None
        old = target.note if target else self.lvl.notes.get((x, y))
        text = nhlevel.note_text(self.prompt(
            _("Annotation (vide : la retirer) : "), old or ""))
        if text == old:
            return
        self.checkpoint(_("Annotation"))
        if target:
            target.note = text
        elif text:
            self.lvl.notes[(x, y)] = text
        else:
            self.lvl.notes.pop((x, y), None)
        self.msg = (_("Annotation : %s") % text if text
                    else _("Annotation retirée."))

    def entity_list(self):
        """Liste des entités, des régions puis des placements aléatoires
        du niveau."""
        sel = None
        while True:
            ents, regs = self.lvl.entities, self.lvl.regions
            rnds = self.lvl.randoms
            if not ents and not regs and not rnds:
                self.msg = _("Aucune entité.")
                return
            ents.sort(key=lambda e: (e.y, e.x))
            items = [("(%2d,%2d) %s %s" % (e.x, e.y, self.entity_glyph(e)[0],
                                          e.describe()), ("e", i))
                     for i, e in enumerate(ents)]
            items += [("[%s] %s" % (REGION_MARK[r.kind], r.describe()),
                       ("r", i)) for i, r in enumerate(regs)]
            items += [("[?] %s" % rp.describe(), ("a", i))
                      for i, rp in enumerate(rnds)]
            if sel is None:
                here = [i for i, e in enumerate(ents)
                        if (e.x, e.y) == (self.cx, self.cy)]
                sel = here[0] if here else 0
            hint = _("Entrée: aller  e: modifier  d: supprimer  Échap: fermer")
            try:
                (what, i), action = self.pick_action(
                    _("Entités (%d), régions (%d), au hasard (%d)") % (
                        len(ents), len(regs), len(rnds)),
                    items, sel, hint)
            except Cancel:
                return
            sel = [v for _l, v in items].index((what, i))
            if what == "a":
                cells = rnds[i].cells(self.lvl)
                if action == "goto" and cells:
                    self.cx, self.cy = min(cells, key=lambda p: (p[1], p[0]))
                    return
                self.msg = _("Placement aléatoire écrit dans le script : "
                             "modifiez-le dans le fichier.")
                continue
            if what == "r":
                if self.region_action(regs[i], action):
                    return
                sel = min(sel, len(ents) + len(regs) - 2)
                continue
            e = ents[i]
            if action == "goto":
                self.cx, self.cy = e.x, e.y
                return
            if action == "delete":
                self.checkpoint(_("Suppression : %s") % e.describe())
                ents.remove(e)
                self.msg = _("Supprimé : %s") % e.describe()
                sel = max(0, sel - 1)
            elif action == "edit":
                try:
                    value, extra = self.edit_entity_fields(e.kind, e.value,
                                                           e.extra)
                except Cancel:
                    continue
                self.checkpoint(_("Modification : %s") % e.describe())
                e.value, e.extra = value, extra
                self.msg = _("Modifié : %s") % e.describe()

    # --- sélection multiple ---------------------------------------------
    def start_entity_selection(self):
        if self.tool not in ("entsel", "entpaste"):
            self.sel_prev_tool = self.tool
        self.tool = "entsel"
        self.anchor = (self.cx, self.cy)
        self.msg = _("Sélection : allez au coin opposé puis Espace (Échap "
                     "annule).")

    def entity_selection(self, a, b):
        """Actions sur les entités du rectangle a-b."""
        lx, hx = sorted((a[0], b[0]))
        ly, hy = sorted((a[1], b[1]))
        sel = [e for e in self.lvl.entities
               if lx <= e.x <= hx and ly <= e.y <= hy]
        if not sel:
            self.msg = _("Aucune entité dans la sélection.")
            return
        action = self.pick(_("%d entité(s) sélectionnée(s)") % len(sel), [
            (_("déplacer (Espace pour poser)"), "move"),
            (_("copier (Espace pour poser, autant de fois que voulu)"),
             "copy"),
            (_("supprimer"), "delete"),
            (_("rechercher et remplacer dans la sélection…"), "find")])
        if action == "delete":
            self.checkpoint(_("Suppression de %d entité(s)") % len(sel))
            for e in sel:
                self.lvl.entities.remove(e)
            self.msg = _("%d entité(s) supprimée(s).") % len(sel)
        elif action == "find":
            self.find_replace(sel)
        else:
            self.ent_clip = []
            for e in sel:
                c = e.copy()
                c.origin, c.x, c.y = None, e.x - lx, e.y - ly
                self.ent_clip.append(c)
            self.ent_moved = sel if action == "move" else []
            self.cx, self.cy = lx, ly
            self.tool = "entpaste"
            self.msg = _("Déplacez les entités puis Espace (Échap annule).")

    def place_entities(self):
        moved = self.ent_moved
        self.checkpoint((_("Déplacement de %d entité(s)") if moved
                         else _("Copie de %d entité(s)")) % len(self.ent_clip))
        for e in moved:
            if e in self.lvl.entities:
                self.lvl.entities.remove(e)
        n = 0
        for e in self.ent_clip:
            c = e.copy()
            c.x += self.cx
            c.y += self.cy
            if c.x < self.lvl.w and c.y < self.lvl.h:
                self.lvl.entities.append(c)
                n += 1
        self.msg = _("%d entité(s) posée(s).") % n
        if n < len(self.ent_clip):
            self.msg += _(" %d hors de la carte, abandonnée(s).") % (
                len(self.ent_clip) - n)
        if moved:
            self.ent_moved = []
            self.tool = self.sel_prev_tool

    # --- régions --------------------------------------------------------
    def region_action(self, r, action):
        """Action de la liste sur une région ; True pour fermer la liste."""
        if action == "goto":
            cells = r.cells(self.lvl)
            if cells:
                self.cx, self.cy = min(cells, key=lambda p: (p[1], p[0]))
            return True
        if r.readonly:
            self.msg = _("Région écrite avec du code Lua : modifiez-la dans "
                         "le fichier.")
            return False
        if action == "delete":
            self.checkpoint(_("Suppression : %s") % r.describe())
            self.lvl.regions.remove(r)
            self.msg = _("Supprimé : %s") % r.describe()
            return False
        what = self.pick(_("Modifier : %s") % r.describe(), [
            (_("options"), "options"),
            (_("redessiner la zone (à partir du curseur)"), "rect")])
        if what == "rect":
            self.start_region(r.kind, r)
            return True
        extra = self.edit_region_fields(r.kind, r.extra, r.style)
        self.checkpoint(_("Modification : %s") % r.describe())
        r.extra = extra
        self.msg = _("Modifié : %s") % r.describe()
        return False

    def edit_region_fields(self, kind, extra, style="table"):
        """Formulaire des options d'une région. Renvoie extra."""
        extra = dict(extra)
        if style == "sel":
            if kind == "region":
                extra["lit"] = self.pick(
                    _("Éclairage de la zone"),
                    [(_("éclairée (lit)"), "lit"),
                     (_("sombre (unlit)"), "unlit")],
                    extra.get("lit", "lit"))
            return extra
        form = REGION_FORMS.get(kind)
        if not form:
            return extra
        return self.form(_("Options : %s") % nhlevel.REGION_LABEL[kind],
                         form, extra)

    def start_region(self, kind, old=None):
        """Commence le tracé d'une région : le curseur est le premier
        coin, Espace sur le coin opposé la crée (ou redessine old)."""
        if old is None:
            style = "table"
            if kind in ("non_diggable", "non_passwall"):
                style = "sel"
                if self.pick(_("Étendue"), [
                        (_("une zone (à tracer)"), "zone"),
                        (_("tout le niveau"), "all")]) == "all":
                    r = nhlevel.Region(kind, None)
                    self.checkpoint(_("Ajout : %s") % r.describe())
                    self.lvl.regions.append(r)
                    self.msg = _("Ajouté : %s") % r.describe()
                    return
            elif kind == "region" and self.pick(_("Forme de l'appel"), [
                    (_("salle ou zone typée : { region = {...}, type = ... }"),
                     "table"),
                    (_("éclairage seul : selection.area(...), \"lit\""),
                     "sel")]) == "sel":
                style = "sel"
            extra = self.edit_region_fields(kind, {}, style)
            self.pending_region = nhlevel.Region(kind, None, extra, style)
        else:
            self.pending_region = old
        if self.tool != "region":
            self.region_prev_tool = self.tool
        self.tool = "region"
        self.anchor = (self.cx, self.cy)
        self.msg = _("Zone : allez au coin opposé puis Espace (Échap "
                     "annule).")

    def finish_region(self, a, b):
        r = self.pending_region
        rect = (min(a[0], b[0]), min(a[1], b[1]),
                max(a[0], b[0]), max(a[1], b[1]))
        if r.islev() and self.lvl.origin():
            o = self.lvl.origin()       # coordonnées absolues du niveau
            rect = (rect[0] + o[0], rect[1] + o[1], rect[2] + o[0],
                    rect[3] + o[1])
        if r in self.lvl.regions:
            self.checkpoint(_("Modification : %s") % r.describe())
            r.rect = rect
            self.msg = _("Modifié : %s") % r.describe()
        else:
            r.rect = rect
            self.checkpoint(_("Ajout : %s") % r.describe())
            self.lvl.regions.append(r)
            self.msg = _("Ajouté : %s") % r.describe()
        self.end_region()

    def end_region(self):
        self.pending_region = None
        self.tool = getattr(self, "region_prev_tool", "pen")
