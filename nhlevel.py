"""Modèle de niveau NetHack et lecture/écriture des fichiers Lua (des.*).

Un fichier importé est découpé en appels « des.xxx(...) » de premier niveau.
Ceux que l'éditeur sait gérer (level_init, level_flags, la première des.map
et les entités à coordonnées fixes qui la suivent) sont remplacés par le
contenu de l'éditeur à l'enregistrement ; tout le reste du script est
conservé tel quel.
"""

import copy
import re

from nhi18n import _

MAX_W, MAX_H = 79, 21
MAP_X_LIM = 76          # limite indiquée par include/sp_lev.h
COLNO, ROWNO = 80, 21   # taille d'un niveau (include/global.h)
# gx.x_maze_max et gy.y_maze_max par défaut (src/decl.c)
X_MAZE_MAX, Y_MAZE_MAX = (COLNO - 1) & ~1, (ROWNO - 1) & ~1

# Caractères de carte acceptés par des.map (src/nhlua.c, char2typ[])
TERRAIN = [
    (" ", _("roche (pierre pleine)")),
    (".", _("sol de salle")),
    ("#", _("couloir")),
    ("-", _("mur horizontal / coin")),
    ("|", _("mur vertical")),
    ("+", _("porte")),
    ("S", _("porte secrète")),
    ("H", _("couloir secret")),
    ("{", _("fontaine")),
    ("\\", _("trône")),
    ("K", _("évier")),
    ("}", _("douves")),
    ("P", _("bassin d'eau")),
    ("W", _("eau (plan de l'Eau)")),
    ("L", _("lave")),
    ("Z", _("mur de lave")),
    ("I", _("glace")),
    ("T", _("arbre")),
    ("F", _("barreaux de fer")),
    ("A", _("air")),
    ("C", _("nuage")),
    ("B", _("limite (crosswall)")),
    ("x", _("transparent (garde l'existant)")),
]
TERRAIN_CHARS = "".join(c for c, _ in TERRAIN)
TERRAIN_DESC = dict(TERRAIN)

LEVEL_FLAGS = [
    "noteleport", "hardfloor", "nommap", "shortsighted", "arboreal",
    "mazelevel", "shroud", "graveyard", "icedpools", "corrmaze",
    "premapped", "sokoban", "solidify", "inaccessibles", "noflip",
    "noflipx", "noflipy", "hot", "cold", "temperate", "nomongen",
    "nodeathdrops", "fumaroles", "stormy",
]

ENTITY_KINDS = ["stair", "ladder", "altar", "monster", "object", "trap",
                "door", "engraving", "gold", "grave", "drawbridge",
                "feature", "terrain"]
ENTITY_LABEL = {
    "stair": _("escalier"), "ladder": _("échelle"), "altar": _("autel"),
    "monster": _("monstre"), "object": _("objet"), "trap": _("piège"),
    "door": _("porte"), "engraving": _("gravure"), "gold": _("or"),
    "grave": _("tombe"), "drawbridge": _("pont-levis"),
    "feature": _("élément de décor"), "terrain": _("terrain (une case)"),
}
# Nom du paramètre principal de chaque entité dans la table Lua
MAIN_KEY = {
    "stair": "dir", "ladder": "dir", "altar": "align", "monster": "id",
    "object": "id", "trap": "type", "door": "state", "engraving": "text",
    "gold": "amount", "grave": "text", "drawbridge": "dir",
    "feature": "type", "terrain": "typ",
}
DOOR_STATES = ["random", "open", "closed", "locked", "nodoor", "broken",
               "secret"]
ALTAR_ALIGNS = ["random", "law", "neutral", "chaos", "noalign",
                "coaligned", "noncoaligned"]
ALTAR_TYPES = ["altar", "shrine", "sanctum"]
HALIGNS = ["center", "left", "half-left", "half-right", "right", "none"]
VALIGNS = ["center", "top", "bottom", "none"]
ENGRAVING_TYPES = ["dust", "engrave", "burn", "mark", "blood"]
DRAWBRIDGE_DIRS = ["north", "south", "east", "west", "random"]
DRAWBRIDGE_STATES = ["open", "closed", "random"]
# des.feature() : type -> caractère de carte équivalent (affichage)
FEATURES = {"fountain": "{", "sink": "K", "pool": "P", "throne": "\\",
            "tree": "T"}


class Entity:
    def __init__(self, kind, x, y, value=None, extra=None, origin=None):
        self.kind = kind
        self.origin = origin        # n° de l'appel d'origine (import)
        self.x, self.y = x, y
        self.value = value          # dir / id / type / state / text
        self.extra = dict(extra or {})   # autres clés de la table Lua
        self.note = None            # annotation : commentaire de fin de ligne

    def copy(self):
        # copie profonde : les extras peuvent contenir des Contents
        c = Entity(self.kind, self.x, self.y, self.value,
                   copy.deepcopy(self.extra), self.origin)
        c.note = self.note
        return c

    def lua_line(self):
        """Appel Lua suivi de l'annotation en commentaire."""
        return self.to_lua() + (" -- " + self.note if self.note else "")

    def describe(self):
        s = ENTITY_LABEL[self.kind]
        if self.value is not None:
            s += " " + str(self.value)
            if self.kind in ("monster", "object") and len(self.value) == 1:
                s += _(" (classe, aléatoire)")
        elif self.kind in ("monster", "object"):
            s += _(" aléatoire")
        if self.extra:
            s += " {" + ", ".join(
                "%s=%s" % (k, v.summary() if isinstance(v, Contents)
                           else lua_value(v))
                for k, v in self.extra.items()) + "}"
        if self.note:
            s += " -- " + self.note
        return s

    def to_lua(self):
        x, y, v, e = self.x, self.y, self.value, self.extra
        k = self.kind
        if x is None:
            # objet sans position : élément d'un contenu ou d'un inventaire
            if not e and v and len(v) > 1:
                return "des.%s(%s);" % (k, lua_value(v))
            if not e and not v:
                return "des.%s();" % k
            t = {}
            if v is not None:
                t["class" if len(v) == 1 else MAIN_KEY[k]] = v
            t.update(e)
            return "des.%s(%s);" % (k, lua_value(t))
        if k in ("stair", "ladder") and not e:
            return 'des.%s("%s", %d, %d);' % (k, v, x, y)
        if k in ("monster", "object") and not e and v:
            if len(v) == 1:
                return "des.%s({ class = %s, x = %d, y = %d });" % (
                    k, lua_value(v), x, y)
            return "des.%s(%s, %d, %d);" % (k, lua_value(v), x, y)
        if k == "trap" and not e and v:
            return "des.trap(%s, %d, %d);" % (lua_value(v), x, y)
        if k == "door" and not e and v:
            return "des.door(%s, %d, %d);" % (lua_value(v), x, y)
        if k == "gold" and not e and isinstance(v, int):
            return "des.gold(%d, %d, %d);" % (v, x, y)
        if k in ("grave", "terrain") and not e and isinstance(v, str):
            return "des.%s(%d, %d, %s);" % (k, x, y, lua_value(v))
        if k == "feature" and not e and v:
            return "des.feature(%s, %d, %d);" % (lua_value(v), x, y)
        t = {"x": x, "y": y}
        if v is not None:
            key = MAIN_KEY[k]
            if k in ("monster", "object") and len(v) == 1:
                key = "class"
            t[key] = v
        t.update(e)
        return "des.%s(%s);" % (k, lua_value(t))


# Annotations des cases : une ligne de commentaire par case, juste avant
# la des.map() de la carte (« -- nhme-note 3 4 : trésor caché ici »)
NOTE_LINE = re.compile(r"^[ \t]*-- nhme-note (\d+) (\d+) : ?(.*)\n?", re.M)
# annotation d'une entité : commentaire sur la même ligne que l'appel
TRAILING_NOTE = re.compile(r"[ \t]*--(?!\[=*\[)[ \t]*([^\n]*)")


def note_text(s):
    """Annotation sur une seule ligne, sans espaces superflus."""
    return " ".join((s or "").split()) or None


def notes_lua(notes):
    return "".join("-- nhme-note %d %d : %s\n" % (x, y, t)
                   for (x, y), t in sorted(notes.items(),
                                           key=lambda kv: kv[0][::-1]))


# Régions : des.region(), des.non_diggable(), des.non_passwall(),
# des.teleport_region(), des.levregion()
REGION_KINDS = ["region", "non_diggable", "non_passwall", "teleport_region",
                "levregion"]
REGION_LABEL = {
    "region": _("région"), "non_diggable": _("zone non creusable"),
    "non_passwall": _("zone sans passe-muraille"),
    "teleport_region": _("zone de téléportation"),
    "levregion": _("zone d'arrivée"),
}
# types de salle de des.region() (room_types[] de src/sp_lev.c)
ROOM_TYPES = ["ordinary", "themed", "throne", "swamp", "vault", "beehive",
              "morgue", "barracks", "zoo", "delphi", "temple", "anthole",
              "cocknest", "leprehall", "shop", "armor shop", "scroll shop",
              "potion shop", "weapon shop", "food shop", "ring shop",
              "wand shop", "tool shop", "book shop", "health food shop",
              "candle shop"]
TELE_DIRS = ["both", "down", "up"]
LEVREGION_TYPES = ["stair-down", "stair-up", "portal", "branch", "teleport",
                   "teleport-up", "teleport-down"]


class RandomPlacement:
    """Appel des.monster/object/trap/gold que l'éditeur ne peut pas
    modifier, mais dont on sait où il tombera : zone ("map",) toute la
    carte, ("rect", (x1, y1, x2, y2)) une région, ("points", [...]) une
    case tirée dans une liste, ("point", (x, y)) une case fixe dont le
    contenu est calculé par le script."""

    def __init__(self, kind, zone, text):
        self.kind, self.zone, self.text = kind, zone, text

    def cells(self, lvl):
        z = self.zone
        if z[0] == "map":
            return {(x, y) for y in range(lvl.h) for x in range(lvl.w)}
        if z[0] == "rect":
            x1, y1, x2, y2 = z[1]
            return {(x, y) for y in range(max(0, y1), min(lvl.h, y2 + 1))
                    for x in range(max(0, x1), min(lvl.w, x2 + 1))}
        pts = z[1] if z[0] == "points" else [z[1]]
        return {tuple(p) for p in pts
                if 0 <= p[0] < lvl.w and 0 <= p[1] < lvl.h}

    def where(self):
        z = self.zone
        if z[0] == "map":
            return _("n'importe où dans la carte")
        if z[0] == "rect":
            return _("au hasard dans (%d,%d)-(%d,%d)") % z[1]
        if z[0] == "points":
            return _("une case parmi %d") % len(z[1])
        return _("en (%d,%d), contenu calculé") % tuple(z[1])

    def describe(self):
        return "%s : %s" % (self.text, self.where())


RANDOM_KINDS = ("monster", "object", "trap", "gold")


def _split_args(args):
    """Arguments d'un appel séparés aux virgules de premier niveau."""
    out, cur, depth = [], [], 0
    for t in args:
        if t[0] == "op" and t[1] in "({[":
            depth += 1
        elif t[0] == "op" and t[1] in ")}]":
            depth -= 1
        if depth == 0 and t[:2] == ("op", ","):
            out.append(cur)
            cur = []
        else:
            cur.append(t)
    if cur:
        out.append(cur)
    return out


def _point_sets(text):
    """Listes de cases nommées du script : « local p = { {x,y}, ... } »,
    « local p = selection.new() » suivi de « p:set(x,y) », et
    « local c = p:rndcoord(...) ». Renvoie {nom: (cases, aléatoire)} ;
    aléatoire : la case est tirée au sort dans la liste."""
    sets = {}
    for m in re.finditer(r"local\s+(\w+)\s*=\s*(\{\s*\{[-\d\s,{}]*\})",
                         text):
        pts = [(int(a), int(b)) for a, b in re.findall(
            r"\{\s*(-?\d+)\s*,\s*(-?\d+)\s*\}", m.group(2))]
        shuffled = re.search(r"shuffle\(\s*%s\s*\)" % m.group(1), text)
        sets[m.group(1)] = (pts, bool(shuffled))
    for m in re.finditer(r"local\s+(\w+)\s*=\s*selection\.new\(\)", text):
        name = m.group(1)
        pts = [(int(a), int(b)) for a, b in re.findall(
            r"\b%s:set\(\s*(\d+)\s*,\s*(\d+)\s*\)" % name, text)]
        if pts:
            sets[name] = (pts, True)
    for m in re.finditer(r"local\s+(\w+)\s*=\s*(\w+):rndcoord\(", text):
        if m.group(2) in sets:
            sets[m.group(1)] = (sets[m.group(2)][0], True)
    return sets


def _coord_zone(toks, sets):
    """Zone désignée par les jetons d'une coordonnée ; None si inconnue."""
    if (len(toks) >= 1 and toks[0][0] == "name" and toks[0][1] in sets):
        pts, rnd = sets[toks[0][1]]
        if (len(toks) == 4 and toks[1][1] == "[" and toks[2][0] == "num"
                and toks[3][1] == "]" and not rnd):
            k = int(toks[2][1]) - 1         # indice Lua à partir de 1
            return ("point", pts[k]) if 0 <= k < len(pts) else None
        return ("points", pts)
    try:
        v = _to_py(_parse_args(toks, 0, len(toks))[0][0])
    except (NotLiteral, IndexError):
        return None
    if (isinstance(v, list) and len(v) == 2
            and all(isinstance(n, int) for n in v)):
        return ("point", tuple(v))
    return None


def _random_from_call(name, args, sets, text, where=("map",)):
    """RandomPlacement d'un appel non modifiable ; None si l'on ne sait
    pas où il tombera. where : zone d'un appel sans coordonnées."""
    if name not in RANDOM_KINDS:
        return None
    label = re.sub(r"\s+", " ", text)
    if len(label) > 60:
        label = label[:57] + "..."
    parts = _split_args(args)
    if len(parts) == 1 and parts[0][0][:2] == ("op", "{"):
        t = parts[0]
        fields, depth = {}, 0
        for k, tok in enumerate(t):
            if tok[0] == "op" and tok[1] in "({[":
                depth += 1
            elif tok[0] == "op" and tok[1] in ")}]":
                depth -= 1
            elif (depth == 1 and tok[0] == "name" and k + 1 < len(t)
                  and t[k + 1][:2] == ("op", "=")):
                end, d = k + 2, 0
                while end < len(t):
                    if t[end][0] == "op" and t[end][1] in "({[":
                        d += 1
                    elif t[end][0] == "op" and t[end][1] in ")}]":
                        if d == 0:
                            break
                        d -= 1
                    elif d == 0 and t[end][:2] == ("op", ","):
                        break
                    end += 1
                fields[tok[1]] = t[k + 2:end]
        if "coord" in fields:
            zone = _coord_zone(fields["coord"], sets)
        elif "x" in fields or "y" in fields:
            try:
                zone = ("point", (int(_to_py(_parse_value(
                    fields["x"], 0, len(fields["x"]))[0])), int(_to_py(
                        _parse_value(fields["y"], 0, len(fields["y"]))[0]))))
            except (NotLiteral, KeyError, TypeError, ValueError):
                zone = None
        else:
            zone = where
    elif len(parts) <= 1:
        zone = where
    elif len(parts) == 3:
        zone = _coord_zone([("op", "{", 0, 0)] + parts[1] + [("op", ",", 0, 0)]
                           + parts[2] + [("op", "}", 0, 0)], sets)
    elif len(parts) == 2:
        zone = _coord_zone(parts[1], sets)
    else:
        zone = None
    return RandomPlacement(name, zone, label) if zone else None


class SelArea(tuple):
    """selection.area(x1, y1, x2, y2) lu dans un appel."""


class Region:
    """Zone rectangulaire d'un appel des.region() ou apparenté.

    rect : (x1, y1, x2, y2) inclus, relatif à la carte (absolu dans le
    niveau si region_islev), ou None pour tout le niveau (non_diggable()).
    style « sel » : écrit avec selection.area() (des.region(sel, "lit"),
    non_diggable, non_passwall) ; « table » : { region = {...}, ... }.
    readonly : région lue dans un appel qui contient du code ; affichée
    mais conservée telle quelle."""

    def __init__(self, kind, rect, extra=None, style=None, origin=None,
                 readonly=False):
        self.kind, self.rect = kind, tuple(rect) if rect else None
        self.extra = dict(extra or {})
        self.style = style or ("sel" if kind in ("non_diggable",
                                                 "non_passwall") else "table")
        self.origin, self.readonly = origin, readonly

    def copy(self):
        return Region(self.kind, self.rect, copy.deepcopy(self.extra),
                      self.style, self.origin, self.readonly)

    def islev(self):
        return bool(self.extra.get("region_islev"))

    def cells(self, lvl):
        """Cases de la carte couvertes (coordonnées de la carte)."""
        if self.rect is None:
            return {(x, y) for y in range(lvl.h) for x in range(lvl.w)}
        x1, y1, x2, y2 = self.rect
        if self.islev():
            o = lvl.origin()
            if not o:
                return set()
            x1, x2, y1, y2 = x1 - o[0], x2 - o[0], y1 - o[1], y2 - o[1]
        return {(x, y) for y in range(max(0, y1), min(lvl.h, y2 + 1))
                for x in range(max(0, x1), min(lvl.w, x2 + 1))}

    def describe(self):
        s = REGION_LABEL[self.kind]
        if self.rect:
            s += " (%d,%d)-(%d,%d)" % self.rect
        else:
            s += " " + _("(tout le niveau)")
        if self.style == "sel" and "lit" in self.extra:
            s += " " + self.extra["lit"]
        else:
            ex = {k: v for k, v in self.extra.items()}
            if ex:
                s += " {" + ", ".join("%s=%s" % (k, lua_value(v))
                                      for k, v in ex.items()) + "}"
        if self.readonly:
            s += " " + _("[code Lua, non modifiable]")
        return s

    def to_lua(self):
        k, r = self.kind, self.rect
        area = "selection.area(%d,%d,%d,%d)" % r if r else ""
        if self.style == "sel":
            if k == "region":
                return "des.region(%s, %s);" % (
                    area, lua_value(self.extra.get("lit", "lit")))
            return "des.%s(%s);" % (k, area)
        t = {"region": list(r)} if r else {}
        t.update(self.extra)
        return "des.%s(%s);" % (k, lua_value(t))


class Level:
    def __init__(self, w=75, h=19):
        self.w, self.h = w, h
        self.grid = [[" "] * w for _ in range(h)]
        self.entities = []
        self.regions = []
        self.init = {"style": "solidfill", "fg": " "}
        self.flags = ["mazelevel"]
        self.halign, self.valign = "center", "center"
        self.pos = None             # (x, y) si la carte a une position fixe
        self.lit = False
        # Texte Lua d'origine découpé (None pour un niveau neuf)
        self.source = None
        self.map_partial = False    # des.map non littérale (contents=...)
        # fichier à plusieurs des.map() : n° de la carte éditée et, pour
        # chaque carte, {"w", "h", "halign", "valign", "pos"} (None si elle
        # n'est pas lisible)
        self.map_index = 0
        self.maps = []
        # placements aléatoires lus dans le script (RandomPlacement)
        self.randoms = []
        # salle à thème de themerms.lua : {"path", "name", "k", "new"}
        self.theme = None
        # annotations des cases : (x, y) -> texte
        self.notes = {}
        # calque de travail (brouillon), jamais enregistré : (x, y) -> car.
        self.draft = {}

    # --- grille ---------------------------------------------------------
    def get(self, x, y):
        return self.grid[y][x]

    def set(self, x, y, c):
        if 0 <= x < self.w and 0 <= y < self.h:
            self.grid[y][x] = c

    def resize(self, w, h, fill=" "):
        w = max(1, min(MAX_W, w))
        h = max(1, min(MAX_H, h))
        g = [[fill] * w for _ in range(h)]
        for y in range(min(h, self.h)):
            for x in range(min(w, self.w)):
                g[y][x] = self.grid[y][x]
        self.grid, self.w, self.h = g, w, h
        self.entities = [e for e in self.entities if e.x < w and e.y < h]
        self.notes = {p: t for p, t in self.notes.items()
                      if p[0] < w and p[1] < h}
        self.draft = {p: t for p, t in self.draft.items()
                      if p[0] < w and p[1] < h}

    def insert_row(self, y, fill=" "):
        """Insère une ligne avant la ligne y ; les entités suivent."""
        if self.h >= MAX_H:
            return False
        self.grid.insert(y, [fill] * self.w)
        self.h += 1
        for e in self.entities:
            if e.y >= y:
                e.y += 1
        self._shift_regions(1, y, 1)
        self._shift_points(1, y, 1)
        return True

    def delete_row(self, y):
        """Supprime la ligne y et ses entités ; les suivantes remontent."""
        if self.h <= 1:
            return False
        del self.grid[y]
        self.h -= 1
        self.entities = [e for e in self.entities if e.y != y]
        for e in self.entities:
            if e.y > y:
                e.y -= 1
        self._shift_regions(1, y, -1)
        self._shift_points(1, y, -1)
        return True

    def insert_col(self, x, fill=" "):
        """Insère une colonne avant la colonne x ; les entités suivent."""
        if self.w >= MAX_W:
            return False
        for row in self.grid:
            row.insert(x, fill)
        self.w += 1
        for e in self.entities:
            if e.x >= x:
                e.x += 1
        self._shift_regions(0, x, 1)
        self._shift_points(0, x, 1)
        return True

    def delete_col(self, x):
        """Supprime la colonne x et ses entités ; les suivantes reculent."""
        if self.w <= 1:
            return False
        for row in self.grid:
            del row[x]
        self.w -= 1
        self.entities = [e for e in self.entities if e.x != x]
        for e in self.entities:
            if e.x > x:
                e.x -= 1
        self._shift_regions(0, x, -1)
        self._shift_points(0, x, -1)
        return True

    def _shift_points(self, axis, at, delta):
        """Décale les annotations et le brouillon (voir _shift_regions)."""
        for name in ("notes", "draft"):
            out = {}
            for p, t in getattr(self, name).items():
                if p[axis] == at and delta < 0:
                    continue        # ligne ou colonne supprimée
                if p[axis] >= at:
                    p = tuple(v + delta if i == axis else v
                              for i, v in enumerate(p))
                out[p] = t
            setattr(self, name, out)

    def _shift_regions(self, axis, at, delta):
        """Décale les régions après une insertion (delta 1) ou une
        suppression (delta -1) de la ligne ou colonne at (axis 1 : y)."""
        keep = []
        for r in self.regions:
            if r.rect is None or r.islev() or r.readonly:
                keep.append(r)
                continue
            c = list(r.rect)
            for i in (axis, axis + 2):
                if c[i] > at or (c[i] == at and delta > 0):
                    c[i] += delta
                elif c[i] == at and delta < 0 and i == axis + 2:
                    c[i] -= 1       # bord supprimé : la zone rétrécit
            if c[axis] <= c[axis + 2]:
                r.rect = tuple(c)
                keep.append(r)
        self.regions = keep

    def regions_at(self, x, y):
        return [r for r in self.regions if (x, y) in r.cells(self)]

    def entities_at(self, x, y):
        return [e for e in self.entities if e.x == x and e.y == y]

    def entity_index(self):
        """Dictionnaire (x, y) -> [entités], pour afficher toute la carte
        sans parcourir la liste des entités case par case."""
        index = {}
        for e in self.entities:
            index.setdefault((e.x, e.y), []).append(e)
        return index

    def snapshot(self):
        """État complet de ce que l'éditeur modifie (annulation)."""
        return ([row[:] for row in self.grid],
                [e.copy() for e in self.entities], self.w, self.h,
                copy.deepcopy(self.init), list(self.flags), self.lit,
                self.pos, self.halign, self.valign,
                [r.copy() for r in self.regions], dict(self.notes),
                dict(self.draft))

    def restore(self, snap):
        (g, ents, self.w, self.h, init, flags, self.lit, self.pos,
         self.halign, self.valign, regions, notes, draft) = snap
        self.notes, self.draft = dict(notes), dict(draft)
        self.grid = [row[:] for row in g]
        self.entities = [e.copy() for e in ents]
        self.regions = [r.copy() for r in regions]
        self.init, self.flags = copy.deepcopy(init), list(flags)

    def map_text(self):
        return "\n".join("".join(row) for row in self.grid)

    # --- génération Lua -------------------------------------------------
    def init_lua(self):
        return "des.level_init(%s);" % lua_value(self.init)

    def flags_lua(self):
        if not self.flags:
            return ""
        return "des.level_flags(%s);" % ", ".join(
            lua_value(f) for f in self.flags)

    def allowed_flips(self):
        """Retournements que NetHack peut appliquer au chargement : bit 1
        haut/bas, bit 2 gauche/droite (allow_flips de src/sp_lev.c)."""
        allowed = 3
        for f in self.flags:
            if f == "noflip":
                allowed = 0
            elif f == "noflipx":
                allowed &= ~2
            elif f == "noflipy":
                allowed &= ~1
        return allowed

    def origin(self):
        """Position (x, y) dans le niveau de la case (0, 0) de la carte.

        Reprend le calcul de lspo_map() (src/sp_lev.c). Renvoie None si
        la carte est placée au hasard (halign ou valign « none »)."""
        if self.pos:
            return tuple(self.pos)
        if "none" in (self.halign, self.valign):
            return None
        w, h = self.w, self.h
        x = {
            # 1 si des.level_init() précède la carte, ce que l'éditeur
            # garantit à l'enregistrement (3 sinon)
            "left": 1,
            "half-left": 2 + _cdiv(X_MAZE_MAX - 2 - w, 4),
            "center": 2 + _cdiv(X_MAZE_MAX - 2 - w, 2),
            "half-right": 2 + _cdiv((X_MAZE_MAX - 2 - w) * 3, 4),
            "right": X_MAZE_MAX - w - 1,
        }.get(self.halign)
        y = {
            "top": 3,
            "center": 2 + _cdiv(Y_MAZE_MAX - 2 - h, 2),
            "bottom": Y_MAZE_MAX - h - 1,
        }.get(self.valign)
        if x is None or y is None:
            return None
        x += x % 2 == 0         # NetHack force des coordonnées impaires
        y += y % 2 == 0
        if y < 0 or y + h > ROWNO:
            y += -2 if y > 0 else 2
            if h == ROWNO or y < 0 or y + h > ROWNO:
                y = 0
        return x, y

    def map_lua(self):
        if (not self.pos and not self.lit and self.halign == "center"
                and self.valign == "center"):
            return "des.map([[\n%s\n]]);" % self.map_text()
        t = {}
        if self.pos:
            t["x"], t["y"] = self.pos
        else:
            if self.halign != "none":
                t["halign"] = self.halign
            if self.valign != "none":
                t["valign"] = self.valign
        if self.lit:
            t["lit"] = 1
        head = "".join("%s = %s, " % (k, lua_value(v)) for k, v in t.items())
        return "des.map({ %smap = [[\n%s\n]] });" % (head, self.map_text())

    def entities_lua(self, new_only=False):
        order = {k: i for i, k in enumerate(ENTITY_KINDS)}
        ents = [e for e in self.entities
                if not new_only or e.origin is None]
        ents.sort(key=lambda e: (order[e.kind], e.y, e.x))
        # puis les régions, dans leur ordre (une région peut en recouvrir
        # une autre)
        regs = [r for r in self.regions if not r.readonly
                and (not new_only or r.origin is None)]
        return "\n".join([e.lua_line() for e in ents]
                         + [r.to_lua() for r in regs])

    def to_lua(self, name="niveau"):
        if self.source is not None:
            return self._merge_source()
        parts = ["-- NetHack %s.lua (créé avec nhmapedit)" % name, "",
                 self.init_lua()]
        if self.flags:
            parts.append(self.flags_lua())
        parts += ["", notes_lua(self.notes) + self.map_lua(), ""]
        ents = self.entities_lua()
        if ents:
            parts += [ents, ""]
        return "\n".join(parts)

    def _merge_source(self):
        text, calls = self.source
        out, pos = [], 0
        have_init = any(c["role"] == "init" for c in calls)
        have_flags = any(c["role"] == "flags" for c in calls)
        have_first = any(c["role"] == "first" for c in calls)
        ent_calls = [i for i, c in enumerate(calls)
                     if c["role"] in ("entity", "region")]
        last_ent = ent_calls[-1] if ent_calls else None
        by_origin = {e.origin: e for e in self.entities + self.regions
                     if e.origin is not None and not getattr(e, "readonly",
                                                             False)}
        new = self.entities_lua(new_only=True)
        def same(c, gen):
            # texte d'origine si l'élément n'a pas été modifié
            return text[c["start"]:c["end"]] if gen == c.get("gen") else gen

        for idx, c in enumerate(calls):
            before = text[pos:c["start"]]
            role = c["role"]
            if role == "map" and self.notes != c.get("notes", {}):
                # annotations des cases réécrites juste avant la carte
                before = NOTE_LINE.sub("", before)
                if before and not before.endswith("\n"):
                    before += "\n"
                before += notes_lua(self.notes)
            out.append(before)
            if role == "init":
                out.append(same(c, self.init_lua()))
            elif role == "flags":
                out.append(same(c, self.flags_lua()))
            elif role == "first":
                pre = []
                if not have_init:
                    pre.append(self.init_lua())
                if not have_flags and self.flags:
                    pre.append(self.flags_lua())
                out.append("\n".join(pre + [text[c["start"]:c["end"]]]))
            elif role == "map":
                pre = []
                if not have_init and not have_first:
                    pre.append(self.init_lua())
                if not have_flags and self.flags and not have_first:
                    pre.append(self.flags_lua())
                if self.map_partial:
                    m = self._merge_map_call(text, c, by_origin, same)
                else:
                    m = same(c, self.map_lua())
                block = "\n".join(pre + [m])
                if new and last_ent is None:
                    block += "\n\n" + new
                out.append(block)
            elif role in ("entity", "region"):
                e = by_origin.get(c["origin"])
                block = same(c, e.to_lua()) if e else ""
                end, note = self._note_change(c, e)
                if note is not None:
                    block += note
                if new and idx == last_ent:
                    block += ("\n" if block else "") + new
                out.append(block)
            pos = c["end"] if role not in ("entity", "region") else end
            if (role in ("entity", "region") and not out[-1]) or (
                    role == "flags" and not self.flags):
                # avale la fin de ligne laissée vide
                m = re.match(r"[ \t]*\n", text[pos:])
                if m and (not out[-1] or out[-1].endswith("\n")):
                    pos += m.end()
        out.append(text[pos:])
        return "".join(out)

    @staticmethod
    def _note_change(c, e):
        """Annotation d'une entité à l'enregistrement : (fin du texte
        d'origine remplacé, nouveau commentaire) ; commentaire None si
        celui d'origine reste tel quel."""
        old = c.get("note")
        if e is None:                   # supprimée, avec son commentaire
            return (old[1] if old else c["end"]), None
        note = getattr(e, "note", None)
        if (old[2] if old else None) == note:
            return c["end"], None
        return (old[1] if old else c["end"]), (" -- " + note if note else "")

    def _merge_map_call(self, text, c, by_origin, same):
        """Texte de l'appel des.map() gardé tel quel, sauf la carte et les
        éléments modifiés de sa fonction contents."""
        subs = [c["str_span"] + ("[[\n" + self.map_text() + "\n]]",)]
        for ic in c.get("inner", ()):
            e = by_origin.get(ic["origin"])
            end, note = self._note_change(ic, e)
            if e:
                subs.append((ic["start"], ic["end"], same(ic, e.to_lua())))
                if note is not None:
                    subs.append((ic["end"], end, note))
            else:
                # élément supprimé : la ligne entière disparaît si l'appel
                # était seul dessus
                s, t = ic["start"], end
                m1 = re.search(r"\n[ \t]*$", text[c["start"]:s])
                m2 = re.match(r"[ \t]*\n", text[t:])
                if m1 and m2:
                    s, t = s - len(m1.group()) + 1, t + m2.end()
                subs.append((s, t, ""))
        out, pos = [], c["start"]
        for s, t, new in sorted(subs):
            out += [text[pos:s], new]
            pos = t
        out.append(text[pos:c["end"]])
        return "".join(out)


def _cdiv(a, b):
    """Division entière du C (tronquée vers zéro)."""
    q = abs(a) // b
    return q if a >= 0 else -q


# ----------------------------------------------------------------------
# Valeurs Lua
# ----------------------------------------------------------------------
_IDENT = re.compile(r"^[A-Za-z_]\w*$")


def lua_value(v):
    if isinstance(v, bool):
        return "true" if v else "false"
    if v is None:
        return "nil"
    if isinstance(v, (int, float)):
        return repr(v)
    if isinstance(v, str):
        return '"' + (v.replace("\\", "\\\\").replace('"', '\\"')
                      .replace("\n", "\\n")) + '"'
    if isinstance(v, LuaTable):
        items = [lua_value(x) for x in v.array]
        items += ["%s = %s" % (k if _IDENT.match(k) else
                               "[%s]" % lua_value(k), lua_value(x))
                  for k, x in v.hash.items()]
        return "{ " + ", ".join(items) + " }" if items else "{}"
    if isinstance(v, Contents):
        return v.lua()
    if isinstance(v, dict):
        return lua_value(LuaTable([], v))
    if isinstance(v, (list, tuple)):
        return lua_value(LuaTable(list(v), {}))
    raise ValueError("valeur non convertible : %r" % (v,))


class Contents:
    """Fonction Lua `function() des.object(...); ... end` des options
    `contents` (conteneurs, statues) et `inventory` (monstres) : une
    liste d'Entity sans position."""

    def __init__(self, items=None, param=None):
        self.items = items or []
        self.param = param          # nom du paramètre, ex. function(obj)

    def summary(self):
        n = len(self.items)
        return (_("(%d objets)") if n > 1 else _("(%d objet)")) % n

    def lua(self):
        head = "function(%s)" % (self.param or "")
        if not self.items:
            return head + " end"
        # chaque ligne d'un élément est décalée, contenus imbriqués compris
        body = ["   " + line for it in self.items
                for line in it.to_lua().split("\n")]
        return "\n".join([head] + body + ["end"])


class LuaTable:
    def __init__(self, array=None, hash=None):
        self.array = array or []
        self.hash = hash or {}


class NotLiteral(Exception):
    pass


def parse_lua_value(s):
    """Analyse une valeur Lua littérale saisie par l'utilisateur."""
    toks = [t for t in tokenize(s) if t[0] != "space"]
    vals, i = _parse_args(toks, 0, len(toks))
    if len(vals) != 1:
        raise NotLiteral(s)
    return vals[0]


# ----------------------------------------------------------------------
# Analyse lexicale Lua (suffisante pour repérer et lire les appels des.*)
# ----------------------------------------------------------------------
_LONG_OPEN = re.compile(r"\[(=*)\[")
_NAME = re.compile(r"[A-Za-z_]\w*")
_NUM = re.compile(r"0[xX][0-9a-fA-F]+|\d+\.?\d*(?:[eE][+-]?\d+)?|\.\d+")
_ESC = {"n": "\n", "t": "\t", "r": "\r", "\\": "\\", '"': '"', "'": "'",
        "a": "\a", "b": "\b", "f": "\f", "v": "\v", "\n": "\n"}


def tokenize(text):
    """Renvoie une liste de (genre, valeur, début, fin)."""
    toks, i, n = [], 0, len(text)
    while i < n:
        c = text[i]
        if c.isspace():
            j = i
            while j < n and text[j].isspace():
                j += 1
            toks.append(("space", None, i, j))
            i = j
        elif text.startswith("--", i):
            m = _LONG_OPEN.match(text, i + 2)
            if m:
                end = text.find("]" + m.group(1) + "]", m.end())
                j = n if end < 0 else end + len(m.group(1)) + 2
            else:
                end = text.find("\n", i)
                j = n if end < 0 else end
            toks.append(("space", None, i, j))
            i = j
        elif c in "\"'":
            j, buf = i + 1, []
            while j < n and text[j] != c:
                if text[j] == "\\" and j + 1 < n:
                    e = text[j + 1]
                    if e.isdigit():
                        m = re.match(r"\d{1,3}", text[j + 1:])
                        buf.append(chr(int(m.group())))
                        j += 1 + len(m.group())
                        continue
                    buf.append(_ESC.get(e, e))
                    j += 2
                else:
                    buf.append(text[j])
                    j += 1
            toks.append(("str", "".join(buf), i, min(j + 1, n)))
            i = j + 1
        elif c == "[" and _LONG_OPEN.match(text, i):
            m = _LONG_OPEN.match(text, i)
            close = "]" + m.group(1) + "]"
            end = text.find(close, m.end())
            end = n if end < 0 else end
            s = text[m.end():end]
            if s.startswith("\r\n"):
                s = s[2:]
            elif s.startswith("\n"):
                s = s[1:]
            j = min(n, end + len(close))
            toks.append(("str", s, i, j))
            i = j
        elif c.isalpha() or c == "_":
            m = _NAME.match(text, i)
            toks.append(("name", m.group(), i, m.end()))
            i = m.end()
        elif c.isdigit() or (c == "." and i + 1 < n and text[i + 1].isdigit()):
            m = _NUM.match(text, i)
            v = m.group()
            num = int(v, 16) if v[:2] in ("0x", "0X") else (
                float(v) if any(ch in v for ch in ".eE") else int(v))
            toks.append(("num", num, i, m.end()))
            i = m.end()
        else:
            for op in ("...", "..", "==", "~=", "<=", ">=", "::", "//"):
                if text.startswith(op, i):
                    break
            else:
                op = c
            toks.append(("op", op, i, i + len(op)))
            i += len(op)
    return toks


_BLOCK_OPEN = {"function", "if", "do", "repeat"}
_BLOCK_CLOSE = {"end", "until"}


def scan_des_calls(text):
    """Liste des appels des.xxx(...) au niveau supérieur du script."""
    toks = [t for t in tokenize(text) if t[0] != "space"]
    calls, block, paren, i = [], 0, 0, 0
    while i < len(toks):
        kind, val, start, end = toks[i]
        if kind == "name":
            if val in _BLOCK_OPEN:
                block += 1
            elif val in _BLOCK_CLOSE:
                block -= 1
            elif (val == "des" and block == 0 and paren == 0
                  and i + 3 < len(toks) and toks[i + 1][1] == "."
                  and toks[i + 2][0] == "name" and toks[i + 3][1] == "("):
                # trouve la parenthèse fermante
                depth, j = 0, i + 3
                while j < len(toks):
                    v = toks[j][1] if toks[j][0] == "op" else None
                    if v in ("(", "{", "["):
                        depth += 1
                    elif v in (")", "}", "]"):
                        depth -= 1
                        if depth == 0:
                            break
                    j += 1
                if j >= len(toks):
                    break
                cend = toks[j][3]
                k = j + 1
                if k < len(toks) and toks[k][1] == ";":
                    cend = toks[k][3]
                    k += 1
                calls.append({"name": toks[i + 2][1], "start": start,
                              "end": cend, "args": toks[i + 4:j]})
                i = k
                continue
        elif kind == "op":
            if val in ("(", "{", "["):
                paren += 1
            elif val in (")", "}", "]"):
                paren -= 1
        i += 1
    return calls


def _parse_args(toks, i, n):
    vals = []
    while i < n:
        v, i = _parse_value(toks, i, n)
        vals.append(v)
        if i < n:
            if toks[i][1] != ",":
                raise NotLiteral()
            i += 1
    return vals, i


def _parse_value(toks, i, n):
    if i >= n:
        raise NotLiteral()
    kind, val = toks[i][0], toks[i][1]
    if kind in ("str", "num"):
        return val, i + 1
    if kind == "op" and val == "-" and i + 1 < n and toks[i + 1][0] == "num":
        return -toks[i + 1][1], i + 2
    if kind == "name" and val in ("true", "false", "nil"):
        return {"true": True, "false": False, "nil": None}[val], i + 1
    if kind == "op" and val == "{":
        t = LuaTable()
        i += 1
        while i < n and toks[i][1] != "}":
            if (toks[i][0] == "name" and i + 1 < n
                    and toks[i + 1][1] == "="):
                key = toks[i][1]
                v, i = _parse_value(toks, i + 2, n)
                t.hash[key] = v
            elif toks[i][1] == "[":
                key, i = _parse_value(toks, i + 1, n)
                if i + 1 >= n or toks[i][1] != "]" or toks[i + 1][1] != "=":
                    raise NotLiteral()
                v, i = _parse_value(toks, i + 2, n)
                t.hash[key] = v
            else:
                v, i = _parse_value(toks, i, n)
                t.array.append(v)
            if i < n and toks[i][1] in (",", ";"):
                i += 1
            elif i < n and toks[i][1] != "}":
                raise NotLiteral()
        if i >= n:
            raise NotLiteral()
        return t, i + 1
    if kind == "name" and val == "function":
        return _parse_function(toks, i + 1, n)
    if (kind == "name" and val == "selection" and i + 3 < n
            and toks[i + 1][1] == "." and toks[i + 2][1] == "area"
            and toks[i + 3][1] == "("):
        depth, j = 0, i + 3
        while j < n:
            v = toks[j][1] if toks[j][0] == "op" else None
            depth += v in ("(", "{", "[")
            depth -= v in (")", "}", "]")
            if depth == 0:
                break
            j += 1
        vals = _parse_args(toks, i + 4, j)[0]
        if len(vals) != 4 or not all(isinstance(v, int) for v in vals):
            raise NotLiteral()
        return SelArea(vals), j + 1
    raise NotLiteral()


def _parse_function(toks, i, n):
    """Lit `(param) des.object(...); ... end` : uniquement des appels
    des.object littéraux, sans position (contenu, inventaire)."""
    if i >= n or toks[i][1] != "(":
        raise NotLiteral()
    param = None
    if i + 1 < n and toks[i + 1][0] == "name":
        param = toks[i + 1][1]
        i += 1
    if i + 1 >= n or toks[i + 1][1] != ")":
        raise NotLiteral()
    i += 2
    items = []
    while i < n and not (toks[i][0] == "name" and toks[i][1] == "end"):
        if not (i + 3 < n and toks[i][1] == "des" and toks[i + 1][1] == "."
                and toks[i + 2][1] == "object" and toks[i + 3][1] == "("):
            raise NotLiteral()
        depth, j = 0, i + 3
        while j < n:
            v = toks[j][1] if toks[j][0] == "op" else None
            if v in ("(", "{", "["):
                depth += 1
            elif v in (")", "}", "]"):
                depth -= 1
                if depth == 0:
                    break
            j += 1
        if j >= n:
            raise NotLiteral()
        vals = [_to_py(a) for a in _parse_args(toks, i + 4, j)[0]]
        items.append(_item_from_args(vals))
        i = j + 1
        if i < n and toks[i][1] == ";":
            i += 1
    if i >= n:
        raise NotLiteral()
    return Contents(items, param), i + 1


def _item_from_args(vals):
    """Objet sans position, à partir des arguments de des.object()."""
    if not vals:
        return Entity("object", None, None)
    if len(vals) == 1 and isinstance(vals[0], str):
        return Entity("object", None, None, vals[0])
    if len(vals) == 1 and isinstance(vals[0], dict):
        t = dict(vals[0])
        if any(k in t for k in ("x", "y", "coord")):
            raise NotLiteral()
        value = t.pop("id", None)
        if value is None and "class" in t:
            value = t.pop("class")
        return Entity("object", None, None, value, t)
    raise NotLiteral()


def _to_py(v):
    if isinstance(v, LuaTable):
        if v.hash and not v.array:
            return {k: _to_py(x) for k, x in v.hash.items()}
        if v.array and not v.hash:
            return [_to_py(x) for x in v.array]
        if not v.array and not v.hash:
            return {}
        raise NotLiteral()
    return v


# ----------------------------------------------------------------------
# Import
# ----------------------------------------------------------------------
def _xy_from(table):
    """Extrait (x, y) d'une table {x=,y=} ou {coord={x,y}}; les retire."""
    if "coord" in table:
        c = table.pop("coord")
        if isinstance(c, list) and len(c) == 2:
            return c
        if isinstance(c, dict) and "x" in c and "y" in c:
            return [c["x"], c["y"]]
        raise NotLiteral()
    if "x" in table and "y" in table:
        return [table.pop("x"), table.pop("y")]
    raise NotLiteral()


def _entity_from_call(name, args):
    vals = [_to_py(a) for a in args]
    if name not in ENTITY_KINDS:
        raise NotLiteral()
    main = MAIN_KEY[name]
    value, xy, extra = None, None, {}
    if vals and isinstance(vals[0], dict):
        t = dict(vals[0])
        xy = _xy_from(t)
        if name in ("monster", "object") and "class" in t and main not in t:
            value = t.pop("class")
        else:
            value = t.pop(main, None)
        if name == "engraving" and len(vals) == 1:
            pass
        elif len(vals) != 1:
            raise NotLiteral()
        extra = t
    elif (name == "engraving" and len(vals) == 3
          and isinstance(vals[0], list)):
        xy = vals[0]
        extra = {"type": vals[1]}
        value = vals[2]
    elif (name in ("grave", "terrain") and len(vals) == 3
          and isinstance(vals[2], str)):
        xy, value = vals[:2], vals[2]       # des.grave(x, y, "texte")
    elif (name == "terrain" and len(vals) == 2 and isinstance(vals[0], list)
          and isinstance(vals[1], str)):
        xy, value = vals[0], vals[1]        # des.terrain({x, y}, "L")
    elif name == "gold" and vals and isinstance(vals[0], int):
        value, rest = vals[0], vals[1:]     # des.gold(montant, x, y)
        xy = rest if len(rest) == 2 else (
            rest[0] if len(rest) == 1 else None)
    elif vals and isinstance(vals[0], str):
        value = vals[0]
        rest = vals[1:]
        if len(rest) == 2:
            xy = rest
        elif len(rest) == 1 and isinstance(rest[0], list):
            xy = rest[0]
        else:
            raise NotLiteral()
    else:
        raise NotLiteral()
    if not (isinstance(xy, list) and len(xy) == 2
            and all(isinstance(c, int) for c in xy)):
        raise NotLiteral()
    if name == "engraving" and "type" in extra:
        extra = dict(type=extra.pop("type"), **extra)
    return Entity(name, xy[0], xy[1], value, extra)


def _rect(v):
    if isinstance(v, list) and len(v) == 4 and all(
            isinstance(c, int) for c in v):
        return tuple(v)
    raise NotLiteral()


def _region_from_call(name, args):
    vals = [_to_py(a) for a in args]
    if name in ("non_diggable", "non_passwall"):
        if not vals:
            return Region(name, None)
        if len(vals) == 1 and isinstance(vals[0], SelArea):
            return Region(name, vals[0])
        raise NotLiteral()
    if (name == "region" and len(vals) == 2 and isinstance(vals[0], SelArea)
            and vals[1] in ("lit", "unlit")):
        return Region(name, vals[0], {"lit": vals[1]}, "sel")
    if len(vals) == 1 and isinstance(vals[0], dict) and "region" in vals[0]:
        t = dict(vals[0])
        rect = _rect(t.pop("region"))
        if "contents" in t:
            raise NotLiteral()
        return Region(name, rect, t, "table")
    raise NotLiteral()


def _readonly_region(name, args):
    """Région d'un appel non littéral (avec du code) dont la zone est
    quand même lisible ; None sinon."""
    if name in ("non_diggable", "non_passwall", "region") and args:
        try:
            v, j = _parse_value(args, 0, len(args))
            if isinstance(v, SelArea):
                return Region(name, v, {}, "sel", readonly=True)
        except NotLiteral:
            pass
    try:
        rect = _rect(_to_py(_literal_fields(args).get("region")))
    except NotLiteral:
        return None
    extra = {k: v for k, v in _literal_fields(args).items()
             if k != "region" and not isinstance(v, (dict, list))}
    return Region(name, rect, extra, "table", readonly=True)


def map_info(args):
    """Taille et placement d'un appel des.map() ; None s'il n'est pas
    lisible."""
    tmp = Level(1, 1)
    try:
        _read_map(tmp, {}, args)
    except NotLiteral:
        return None
    return {"w": tmp.w, "h": tmp.h, "halign": tmp.halign,
            "valign": tmp.valign, "pos": tmp.pos}


def parse_level(text, index=0):
    """Construit un Level à partir d'un script Lua de niveau ; index :
    n° de la carte des.map() à éditer quand il y en a plusieurs."""
    lvl = Level(1, 1)
    calls = scan_des_calls(text)
    kept, warnings = [], []
    map_seen = map_done = False
    serial = iter(range(10 ** 9))       # n° d'origine des éléments lus
    sets = _point_sets(text)

    def note_random(c, name, args, where=("map",)):
        rp = _random_from_call(name, args, sets, text[c["start"]:c["end"]],
                               where)
        if rp and (where[0] == "map" or rp.zone == where):
            lvl.randoms.append(rp)

    def region_contents(r, args):
        """Appels sans coordonnées de la fonction contents d'une région :
        ils tombent dans la région."""
        body = _function_body(args, "contents")
        if body and r.rect and r.kind == "region" and not r.islev():
            for ic in scan_des_calls(text[body[0]:body[1]]):
                ic["start"] += body[0]
                ic["end"] += body[0]
                note_random(ic, ic["name"], ic["args"], ("rect", r.rect))

    def take(c, name, args):
        """Entité ou région à coordonnées fixes ; False si l'appel n'est
        pas modifiable (NotLiteral)."""
        try:
            if name in REGION_KINDS:
                try:
                    vals = _parse_args(args, 0, len(args))[0]
                    r = _region_from_call(name, vals)
                except NotLiteral:
                    r = _readonly_region(name, args)
                    if r:
                        lvl.regions.append(r)
                        region_contents(r, args)
                    raise
                r.origin = c["origin"] = next(serial)
                lvl.regions.append(r)
                c["role"] = "region"
            elif name in ENTITY_KINDS:
                vals = _parse_args(args, 0, len(args))[0]
                e = _entity_from_call(name, vals)
                e.origin = c["origin"] = next(serial)
                m = TRAILING_NOTE.match(text, c["end"])
                if m and note_text(m.group(1)):
                    e.note = note_text(m.group(1))
                    c["note"] = (c["end"], m.end(), e.note)
                lvl.entities.append(e)
                c["role"] = "entity"
            else:
                return False
        except NotLiteral:
            return False
        return True

    nmap = 0                            # cartes déjà rencontrées
    for c in calls:
        name, args = c["name"], c["args"]
        try:
            if name == "map":
                lvl.maps.append(map_info(args))
                nmap += 1
                if nmap - 1 < index:
                    if nmap == 1:
                        # première carte : level_init et level_flags
                        # manquants s'écriront juste avant
                        c["role"] = "first"
                        kept.append(c)
                    continue
                if nmap - 1 > index:
                    map_done = True
                    continue
            if name == "level_init" and nmap == 0:
                vals = _parse_args(args, 0, len(args))[0]
                if len(vals) != 1 or not isinstance(_to_py(vals[0]), dict):
                    raise NotLiteral()
                lvl.init = _to_py(vals[0])
                c["role"] = "init"
            elif name == "level_flags" and nmap == 0:
                vals = _parse_args(args, 0, len(args))[0]
                if not all(isinstance(v, str) for v in vals):
                    raise NotLiteral()
                lvl.flags = list(vals)
                c["role"] = "flags"
            elif name == "map" and not map_seen:
                lvl.map_index = index
                _read_map(lvl, c, args)
                # annotations des cases : lignes juste avant la carte
                prev = max((k["end"] for k in calls
                            if k["end"] <= c["start"]), default=0)
                lvl.notes = {(int(m.group(1)), int(m.group(2))):
                             note_text(m.group(3))
                             for m in NOTE_LINE.finditer(
                                 text, prev, c["start"])
                             if note_text(m.group(3))}
                c["notes"] = dict(lvl.notes)
                map_seen = True
                c["role"] = "map"
                # appels de « contents = function() ... end » : mêmes
                # coordonnées (relatives à la carte) qu'après la carte
                c["inner"] = []
                if c.get("body"):
                    bs, be = c["body"]
                    for ic in scan_des_calls(text[bs:be]):
                        ic["start"] += bs
                        ic["end"] += bs
                        ic["args"] = [(k, v, s + bs, e + bs)
                                      for k, v, s, e in ic["args"]]
                        if take(ic, ic["name"], ic["args"]):
                            c["inner"].append(ic)
                        else:
                            note_random(ic, ic["name"], ic["args"])
            elif map_seen and not map_done and take(c, name, args):
                pass
            elif map_seen and not map_done:
                note_random(c, name, args)
                raise NotLiteral()
            else:
                raise NotLiteral()
            kept.append(c)
        except NotLiteral:
            pass
    if not map_seen and index and index < nmap:
        raise ValueError(_("la carte n° %d n'est pas lisible (texte calculé "
                           "par le script)") % (index + 1))
    if not map_seen:
        raise ValueError(_("aucun appel des.map() trouvé dans ce fichier"))
    has_init = any(c["role"] == "init" for c in kept)
    if not has_init:
        lvl.init = {"style": "solidfill", "fg": " "}
    has_flags = any(c["role"] == "flags" for c in kept)
    if not has_flags:
        lvl.flags = []
    lvl.source = (text, kept)
    by_origin = {e.origin: e for e in lvl.entities + lvl.regions
                 if not getattr(e, "readonly", False)}
    for c in kept + [ic for c in kept for ic in c.get("inner", ())]:
        c["gen"] = {"init": lvl.init_lua, "flags": lvl.flags_lua,
                    "map": lvl.map_lua, "first": lambda: None,
                    "entity": lambda: by_origin[c["origin"]].to_lua(),
                    "region": lambda: by_origin[c["origin"]].to_lua(),
                    }[c["role"]]()
    return lvl, warnings


def _read_map(lvl, call, args):
    s, span, table = None, None, None
    if len(args) == 1 and args[0][0] == "str":
        s, span = args[0][1], (args[0][2], args[0][3])
    else:
        # cherche « map = <chaîne> » au premier niveau de la table
        depth = 0
        for k, t in enumerate(args):
            if t[0] == "op" and t[1] in "({[":
                depth += 1
            elif t[0] == "op" and t[1] in ")}]":
                depth -= 1
            elif (depth == 1 and t == args[k] and t[0] == "name"
                  and t[1] == "map" and k + 2 < len(args)
                  and args[k + 1][1] == "=" and args[k + 2][0] == "str"):
                s = args[k + 2][1]
                span = (args[k + 2][2], args[k + 2][3])
                break
        if s is None:
            raise NotLiteral()
        call["body"] = _function_body(args, "contents")
        try:
            vals = _parse_args(args, 0, len(args))[0]
            table = _to_py(vals[0]) if len(vals) == 1 else None
            if not isinstance(table, dict):
                table = None
        except NotLiteral:
            # table avec du code (contents = function...) : on lit au
            # moins les options littérales pour connaître le placement
            table = _literal_fields(args)
            lvl.map_partial = True
    lvl.halign = lvl.valign = "center"
    lines = s.split("\n")
    if lines and lines[-1] == "":
        lines.pop()
    lines = [re.sub(r"\d", "", ln.rstrip("\r")) for ln in lines] or [" "]
    w = max(1, min(MAX_W, max(len(ln) for ln in lines)))
    h = max(1, min(MAX_H, len(lines)))
    lvl.w, lvl.h = w, h
    lvl.grid = [list(ln[:w].ljust(w)) for ln in lines[:h]]
    call["str_span"] = span
    if table:
        if "coord" in table:
            table["x"], table["y"] = (list(table.pop("coord")) + [None])[:2]
        if isinstance(table.get("x"), int) and isinstance(table.get("y"),
                                                           int):
            lvl.pos = (table["x"], table["y"])
        lvl.halign = table.get("halign", "none")
        lvl.valign = table.get("valign", "none")
        lvl.lit = bool(table.get("lit", 0))
        unknown = set(table) - {"x", "y", "coord", "halign", "valign",
                                "lit", "map"}
        if unknown:
            lvl.map_partial = True


def _function_body(args, field):
    """(début, fin) du corps de « field = function(...) ... end » au
    premier niveau de la table args ; None s'il n'y en a pas."""
    depth = 0
    for k, t in enumerate(args):
        if t[0] == "op" and t[1] in "({[":
            depth += 1
        elif t[0] == "op" and t[1] in ")}]":
            depth -= 1
        elif (depth == 1 and t[0] == "name" and t[1] == field
              and k + 2 < len(args) and args[k + 1][1] == "="
              and args[k + 2][:2] == ("name", "function")):
            j = k + 3
            while j < len(args) and args[j][1] != ")":
                j += 1
            if j >= len(args):
                return None
            start, block = args[j][3], 1
            for t2 in args[j + 1:]:
                if t2[0] == "name" and t2[1] in _BLOCK_OPEN:
                    block += 1
                elif t2[0] == "name" and t2[1] in _BLOCK_CLOSE:
                    block -= 1
                    if block == 0:
                        return start, t2[2]
            return None
    return None


def _literal_fields(args):
    """Champs « nom = valeur littérale » au premier niveau d'une table."""
    fields, depth, i, n = {}, 0, 0, len(args)
    while i < n:
        kind, val = args[i][0], args[i][1]
        if kind == "op" and val in ("(", "{", "["):
            depth += 1
        elif kind == "op" and val in (")", "}", "]"):
            depth -= 1
        elif (depth == 1 and kind == "name" and i + 1 < n
              and args[i + 1][1] == "="):
            try:
                v, j = _parse_value(args, i + 2, n)
                if j < n and args[j][1] in (",", ";", "}"):
                    fields[val] = _to_py(v)
                    i = j
                    continue
            except NotLiteral:
                pass
        i += 1
    return fields
