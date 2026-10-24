"""Salles à thème de dat/themerms.lua.

Chaque entrée de la table `themerooms = { ... }` décrit une salle par une
fonction Lua. Les salles dessinées par `des.map()` ont une carte que
l'on peut éditer : on repère la chaîne de la carte dans le texte et on ne
remplace qu'elle, le reste du fichier (code, commentaires) ne change pas.
"""

import re

from nhlevel import tokenize

_BRACKETS = {"(": 1, "{": 1, "[": 1, ")": -1, "}": -1, "]": -1}


class ThemeFile:
    def __init__(self, text):
        self.text = text
        toks = [t for t in tokenize(text) if t[0] != "space"]
        self.rooms = []             # [{"name", "start", "end", "maps"}]
        self.table_end = None       # position du « } » de themerooms
        start = None
        for i in range(len(toks) - 2):
            if (toks[i][:2] == ("name", "themerooms")
                    and toks[i + 1][1] == "=" and toks[i + 2][1] == "{"):
                start = i + 2
                break
        if start is None:
            raise ValueError("pas de table « themerooms = { ... } »")
        depth, entry = 0, None
        for j in range(start, len(toks)):
            kind, val, s, e = toks[j]
            if kind != "op" or val not in _BRACKETS:
                continue
            depth += _BRACKETS[val]
            if depth == 2 and val == "{":
                entry = j
            elif depth == 1 and val == "}" and entry is not None:
                self.rooms.append(self._room(toks, entry, j))
                entry = None
            elif depth == 0:
                self.table_end = s
                break
        if self.table_end is None:
            raise ValueError("table themerooms non terminée")
        self.toks = toks

    @staticmethod
    def _room(toks, i, j):
        """Nom et cartes (positions des chaînes) de l'entrée toks[i..j]."""
        name, maps, depth = None, [], 0
        for k in range(i, j):
            kind, val = toks[k][0], toks[k][1]
            if kind == "op" and val in _BRACKETS:
                depth += _BRACKETS[val]
            elif (depth == 1 and kind == "name" and val == "name"
                  and toks[k + 1][1] == "=" and toks[k + 2][0] == "str"):
                name = toks[k + 2][1]
            elif (kind == "name" and val == "des" and toks[k + 1][1] == "."
                  and toks[k + 2][1] == "map" and toks[k + 3][1] == "("):
                m = ThemeFile._map_arg(toks, k + 4)
                if m:
                    maps.append(m)
        return {"name": name, "start": toks[i][2], "end": toks[j][3],
                "maps": maps}

    @staticmethod
    def _map_arg(toks, k):
        """Chaîne de la carte : des.map([[...]]) ou des.map({ map = ... })."""
        if toks[k][0] == "str":
            return toks[k][2], toks[k][3], toks[k][1]
        if toks[k][1] != "{":
            return None
        depth = 0
        while k < len(toks):
            kind, val = toks[k][0], toks[k][1]
            if kind == "op" and val in _BRACKETS:
                depth += _BRACKETS[val]
                if depth == 0:
                    return None
            elif (depth == 1 and kind == "name" and val == "map"
                  and toks[k + 1][1] == "=" and toks[k + 2][0] == "str"):
                t = toks[k + 2]
                return t[2], t[3], t[1]
            k += 1
        return None

    # -- lecture ---------------------------------------------------------
    def editable(self):
        """[(libellé, (nom, n° de carte))] des salles qui ont une carte."""
        out = []
        for r in self.rooms:
            if not r["name"]:
                continue
            for k, _ in enumerate(r["maps"]):
                label = r["name"] + ("  (carte %d)" % (k + 1)
                                     if len(r["maps"]) > 1 else "")
                out.append((label, (r["name"], k)))
        return out

    def find(self, name):
        for r in self.rooms:
            if r["name"] == name:
                return r
        return None

    def map_text(self, name, k):
        return self.find(name)["maps"][k][2].rstrip("\n")

    # -- écriture --------------------------------------------------------
    def replace_map(self, name, k, new):
        """Texte du fichier avec la carte k de la salle remplacée ; garde
        le style de la chaîne (sauts de ligne autour de la carte)."""
        s, e, _ = self.find(name)["maps"][k]
        raw = self.text[s:e]
        m = re.match(r"\[(=*)\[", raw)
        if not m:               # chaîne entre guillemets : rare, on la
            lit = '"%s"' % new.replace("\\", "\\\\").replace(
                "\n", "\\n").replace('"', '\\"')
            return self.text[:s] + lit + self.text[e:]
        close = "]" + m.group(1) + "]"
        lead = "\n" if raw[m.end():].startswith("\n") else ""
        trail = "\n" if raw[:-len(close)].endswith("\n") else ""
        return (self.text[:s] + m.group() + lead + new + trail + close
                + self.text[e:])

    def add_room(self, name, new):
        """Texte du fichier avec une nouvelle salle à la fin de la table.

        Le contenu de la salle est rempli par filler_region() (défini dans
        themerms.lua) à partir de la première case de sol trouvée."""
        lines = new.split("\n")
        filler = ""
        for y, row in enumerate(lines):
            x = row.find(".")
            if x >= 0:
                filler = (", contents = function(m) filler_region(%d,%d); "
                          "end" % (x, y))
                break
        entry = ("   {\n      name = %s,\n      contents = function()\n"
                 "         des.map({ map = [[\n%s]]%s });\n      end,\n   },\n"
                 % (_lua_str(name), new, filler))
        # après la dernière entrée, en ajoutant sa virgule si besoin
        last = self.rooms[-1]["end"] if self.rooms else None
        if last is None:
            return (self.text[:self.table_end] + "\n" + entry
                    + self.text[self.table_end:])
        after = self.text[last:self.table_end]
        comma = "" if after.lstrip().startswith(",") else ","
        pos = last + (after.index(",") + 1 if not comma else 0)
        return (self.text[:pos] + comma + "\n\n" + entry.rstrip("\n")
                + self.text[pos:])


def _lua_str(s):
    return '"%s"' % s.replace("\\", "\\\\").replace('"', '\\"')
