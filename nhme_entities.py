"""Entités : placement, formulaires d'options, contenus, liste."""

import copy

import nhlevel
from nhi18n import _
from nhlevel import Entity
from nhme_common import Cancel, MON_FORM, OBJ_FORM


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

    def edit_entity_fields(self, kind, value=None, extra=None):
        """Demande les paramètres d'une entité. Renvoie (value, extra)."""
        extra = dict(extra or {})
        if kind in ("stair", "ladder"):
            value = self.pick(_("Direction"), [(_("montant (up)"), "up"),
                                               (_("descendant (down)"),
                                                "down")],
                              value)
        elif kind == "altar":
            value = self.pick(_("Alignement de l'autel"),
                              [(a, a) for a in nhlevel.ALTAR_ALIGNS], value)
            extra["type"] = self.pick(
                _("Type d'autel"), [(t, t) for t in nhlevel.ALTAR_TYPES],
                extra.get("type", "altar"))
        elif kind == "monster":
            items = [(_("(aléatoire)"), None)] + [
                ("%s  %s" % (m["sym"], m["name"]), m["name"])
                for m in self.data["monsters"]]
            value = self.pick(_("Monstre (tapez pour filtrer ; une lettre "
                                "seule = classe)"), items, value, custom=True)
            extra = self.edit_options(kind, extra)
        elif kind == "object":
            items = [(_("(aléatoire)"), None)] + [
                ("%s  %s" % (o["sym"], o["name"]), o["name"])
                for o in self.data["objects"]]
            value = self.pick(_("Objet (tapez pour filtrer ; un symbole "
                                "seul = classe)"), items, value, custom=True)
            extra = self.edit_options(kind, extra)
        elif kind == "trap":
            value = self.pick(_("Type de piège"),
                              [(t, t) for t in self.data["traps"]], value)
        elif kind == "door":
            value = self.pick(_("État de la porte"),
                              [(s, s) for s in nhlevel.DOOR_STATES], value)
        elif kind == "engraving":
            etype = self.pick(_("Type de gravure"),
                              [(t, t) for t in nhlevel.ENGRAVING_TYPES],
                              extra.get("type", "engrave"))
            value = self.prompt(_("Texte gravé : "), value or "Elbereth")
            extra.pop("type", None)
            extra = dict(type=etype, **extra)
        return value, extra

    def place_entity(self):
        if self.no_entities():
            return
        kinds = [("%s" % nhlevel.ENTITY_LABEL[k].capitalize(), k)
                 for k in nhlevel.ENTITY_KINDS]
        kind = self.pick(_("Placer une entité en (%d,%d)")
                         % (self.cx, self.cy), kinds)
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

    def entity_list(self):
        sel = None
        while True:
            ents = self.lvl.entities
            if not ents:
                self.msg = _("Aucune entité.")
                return
            ents.sort(key=lambda e: (e.y, e.x))
            items = [("(%2d,%2d) %s %s" % (e.x, e.y, self.entity_glyph(e)[0],
                                          e.describe()), i)
                     for i, e in enumerate(ents)]
            if sel is None:
                here = [i for i, e in enumerate(ents)
                        if (e.x, e.y) == (self.cx, self.cy)]
                sel = here[0] if here else 0
            hint = _("Entrée: aller  e: modifier  d: supprimer  Échap: fermer")
            try:
                i, action = self.pick_action(_("Entités (%d)") % len(ents),
                                             items, sel, hint)
            except Cancel:
                return
            e = ents[i]
            sel = i
            if action == "goto":
                self.cx, self.cy = e.x, e.y
                return
            if action == "delete":
                self.checkpoint(_("Suppression : %s") % e.describe())
                ents.remove(e)
                self.msg = _("Supprimé : %s") % e.describe()
                sel = max(0, i - 1)
            elif action == "edit":
                try:
                    value, extra = self.edit_entity_fields(e.kind, e.value,
                                                           e.extra)
                except Cancel:
                    continue
                self.checkpoint(_("Modification : %s") % e.describe())
                e.value, e.extra = value, extra
                self.msg = _("Modifié : %s") % e.describe()
