"""Modèle de niveau NetHack et lecture/écriture des fichiers Lua (des.*).

Un fichier importé est découpé en appels « des.xxx(...) » de premier niveau.
Ceux que l'éditeur sait gérer (level_init, level_flags, la première des.map
et les entités à coordonnées fixes qui la suivent) sont remplacés par le
contenu de l'éditeur à l'enregistrement ; tout le reste du script est
conservé tel quel.
"""

import re

MAX_W, MAX_H = 79, 21
MAP_X_LIM = 76          # limite indiquée par include/sp_lev.h
COLNO, ROWNO = 80, 21   # taille d'un niveau (include/global.h)
# gx.x_maze_max et gy.y_maze_max par défaut (src/decl.c)
X_MAZE_MAX, Y_MAZE_MAX = (COLNO - 1) & ~1, (ROWNO - 1) & ~1

# Caractères de carte acceptés par des.map (src/nhlua.c, char2typ[])
TERRAIN = [
    (" ", "roche (pierre pleine)"),
    (".", "sol de salle"),
    ("#", "couloir"),
    ("-", "mur horizontal / coin"),
    ("|", "mur vertical"),
    ("+", "porte"),
    ("S", "porte secrète"),
    ("H", "couloir secret"),
    ("{", "fontaine"),
    ("\\", "trône"),
    ("K", "évier"),
    ("}", "douves"),
    ("P", "bassin d'eau"),
    ("W", "eau (plan de l'Eau)"),
    ("L", "lave"),
    ("Z", "mur de lave"),
    ("I", "glace"),
    ("T", "arbre"),
    ("F", "barreaux de fer"),
    ("A", "air"),
    ("C", "nuage"),
    ("B", "limite (crosswall)"),
    ("x", "transparent (garde l'existant)"),
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
                "door", "engraving"]
ENTITY_LABEL = {
    "stair": "escalier", "ladder": "échelle", "altar": "autel",
    "monster": "monstre", "object": "objet", "trap": "piège",
    "door": "porte", "engraving": "gravure",
}
# Nom du paramètre principal de chaque entité dans la table Lua
MAIN_KEY = {
    "stair": "dir", "ladder": "dir", "altar": "align", "monster": "id",
    "object": "id", "trap": "type", "door": "state", "engraving": "text",
}
DOOR_STATES = ["random", "open", "closed", "locked", "nodoor", "broken",
               "secret"]
ALTAR_ALIGNS = ["random", "law", "neutral", "chaos", "noalign",
                "coaligned", "noncoaligned"]
ALTAR_TYPES = ["altar", "shrine", "sanctum"]
HALIGNS = ["center", "left", "half-left", "half-right", "right", "none"]
VALIGNS = ["center", "top", "bottom", "none"]
ENGRAVING_TYPES = ["dust", "engrave", "burn", "mark", "blood"]


class Entity:
    def __init__(self, kind, x, y, value=None, extra=None, origin=None):
        self.kind = kind
        self.origin = origin        # n° de l'appel d'origine (import)
        self.x, self.y = x, y
        self.value = value          # dir / id / type / state / text
        self.extra = dict(extra or {})   # autres clés de la table Lua

    def copy(self):
        return Entity(self.kind, self.x, self.y, self.value,
                      dict(self.extra), self.origin)

    def describe(self):
        s = ENTITY_LABEL[self.kind]
        if self.value is not None:
            s += " " + str(self.value)
        if self.extra:
            s += " {" + ", ".join("%s=%s" % (k, lua_value(v))
                                  for k, v in self.extra.items()) + "}"
        return s

    def to_lua(self):
        x, y, v, e = self.x, self.y, self.value, self.extra
        k = self.kind
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
        t = {"x": x, "y": y}
        if v is not None:
            key = MAIN_KEY[k]
            if k in ("monster", "object") and len(v) == 1:
                key = "class"
            t[key] = v
        t.update(e)
        return "des.%s(%s);" % (k, lua_value(t))


class Level:
    def __init__(self, w=75, h=19):
        self.w, self.h = w, h
        self.grid = [[" "] * w for _ in range(h)]
        self.entities = []
        self.init = {"style": "solidfill", "fg": " "}
        self.flags = ["mazelevel"]
        self.halign, self.valign = "center", "center"
        self.pos = None             # (x, y) si la carte a une position fixe
        self.lit = False
        # Texte Lua d'origine découpé (None pour un niveau neuf)
        self.source = None
        self.map_partial = False    # des.map non littérale (contents=...)

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

    def insert_row(self, y, fill=" "):
        """Insère une ligne avant la ligne y ; les entités suivent."""
        if self.h >= MAX_H:
            return False
        self.grid.insert(y, [fill] * self.w)
        self.h += 1
        for e in self.entities:
            if e.y >= y:
                e.y += 1
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
        return True

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
        return ([row[:] for row in self.grid],
                [e.copy() for e in self.entities], self.w, self.h)

    def restore(self, snap):
        g, ents, self.w, self.h = snap
        self.grid = [row[:] for row in g]
        self.entities = [e.copy() for e in ents]

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
        return "\n".join(e.to_lua() for e in ents)

    def to_lua(self, name="niveau"):
        if self.source is not None:
            return self._merge_source()
        parts = ["-- NetHack %s.lua (créé avec nhmapedit)" % name, "",
                 self.init_lua()]
        if self.flags:
            parts.append(self.flags_lua())
        parts += ["", self.map_lua(), ""]
        ents = self.entities_lua()
        if ents:
            parts += [ents, ""]
        return "\n".join(parts)

    def _merge_source(self):
        text, calls = self.source
        out, pos = [], 0
        have_init = any(c["role"] == "init" for c in calls)
        have_flags = any(c["role"] == "flags" for c in calls)
        ent_calls = [i for i, c in enumerate(calls) if c["role"] == "entity"]
        last_ent = ent_calls[-1] if ent_calls else None
        by_origin = {e.origin: e for e in self.entities
                     if e.origin is not None}
        new = self.entities_lua(new_only=True)
        def same(c, gen):
            # texte d'origine si l'élément n'a pas été modifié
            return text[c["start"]:c["end"]] if gen == c.get("gen") else gen

        for idx, c in enumerate(calls):
            out.append(text[pos:c["start"]])
            role = c["role"]
            if role == "init":
                out.append(same(c, self.init_lua()))
            elif role == "flags":
                out.append(same(c, self.flags_lua()))
            elif role == "map":
                pre = []
                if not have_init:
                    pre.append(self.init_lua())
                if not have_flags and self.flags:
                    pre.append(self.flags_lua())
                if self.map_partial:
                    s, e = c["str_span"]
                    m = text[c["start"]:c["end"]]
                    m = (m[:s - c["start"]] + "[[\n" + self.map_text()
                         + "\n]]" + m[e - c["start"]:])
                else:
                    m = same(c, self.map_lua())
                block = "\n".join(pre + [m])
                if new and last_ent is None:
                    block += "\n\n" + new
                out.append(block)
            elif role == "entity":
                e = by_origin.get(c["origin"])
                block = same(c, e.to_lua()) if e else ""
                if new and idx == last_ent:
                    block += ("\n" if block else "") + new
                out.append(block)
            pos = c["end"]
            if (role == "entity" and not out[-1]) or (
                    role == "flags" and not self.flags):
                # avale la fin de ligne laissée vide
                m = re.match(r"[ \t]*\n", text[pos:])
                if m and (not out[-1] or out[-1].endswith("\n")):
                    pos += m.end()
        out.append(text[pos:])
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
    if isinstance(v, dict):
        return lua_value(LuaTable([], v))
    if isinstance(v, (list, tuple)):
        return lua_value(LuaTable(list(v), {}))
    raise ValueError("valeur non convertible : %r" % (v,))


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


def parse_level(text):
    """Construit un Level à partir d'un script Lua de niveau."""
    lvl = Level(1, 1)
    calls = scan_des_calls(text)
    kept, warnings = [], []
    map_seen = map_done = False
    for c in calls:
        name, args = c["name"], c["args"]
        try:
            if name == "level_init" and not map_seen:
                vals = _parse_args(args, 0, len(args))[0]
                if len(vals) != 1 or not isinstance(_to_py(vals[0]), dict):
                    raise NotLiteral()
                lvl.init = _to_py(vals[0])
                c["role"] = "init"
            elif name == "level_flags" and not map_seen:
                vals = _parse_args(args, 0, len(args))[0]
                if not all(isinstance(v, str) for v in vals):
                    raise NotLiteral()
                lvl.flags = list(vals)
                c["role"] = "flags"
            elif name == "map" and not map_seen:
                _read_map(lvl, c, args)
                map_seen = True
                c["role"] = "map"
            elif name == "map" and map_seen:
                map_done = True
                raise NotLiteral()
            elif map_seen and not map_done and name in ENTITY_KINDS:
                vals = _parse_args(args, 0, len(args))[0]
                e = _entity_from_call(name, vals)
                e.origin = c["origin"] = len(kept)
                lvl.entities.append(e)
                c["role"] = "entity"
            else:
                raise NotLiteral()
            kept.append(c)
        except NotLiteral:
            pass
    if not map_seen:
        raise ValueError("aucun appel des.map() trouvé dans ce fichier")
    has_init = any(c["role"] == "init" for c in kept)
    if not has_init:
        lvl.init = {"style": "solidfill", "fg": " "}
    has_flags = any(c["role"] == "flags" for c in kept)
    if not has_flags:
        lvl.flags = []
    lvl.source = (text, kept)
    by_origin = {e.origin: e for e in lvl.entities}
    for c in kept:
        c["gen"] = {"init": lvl.init_lua, "flags": lvl.flags_lua,
                    "map": lvl.map_lua,
                    "entity": lambda: by_origin[c["origin"]].to_lua()
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
