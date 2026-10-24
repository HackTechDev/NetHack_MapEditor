"""Lecture et modification de dat/dungeon.lua (structure du donjon).

Le fichier est une seule table Lua littérale `dungeon = { ... }`. Pour
garder sa mise en forme et ses commentaires, on ne le réécrit pas : on
repère la position de chaque élément dans le texte, et on insère,
remplace ou supprime seulement l'entrée d'un niveau spécial.
"""

from nhi18n import _
from nhlevel import NotLiteral, lua_value, tokenize

# Limites de NetHack (include/dgn_file.h, include/dungeon.h)
LEV_LIMIT = 50          # niveaux spéciaux, tous donjons confondus
NAME_MAX = 14           # char proto[15]
ALIGNMENTS = ["unaligned", "noalign", "lawful", "neutral", "chaotic"]
LEVEL_FLAGS = ["town", "hellish", "mazelike", "roguelike"]
# Ordre des clés d'une entrée de niveau, comme dans dungeon.lua
LEVEL_KEYS = ["name", "bonetag", "chainlevel", "base", "range", "chance",
              "nlevels", "alignment", "flags"]


class Node:
    """Valeur lue avec sa position [start, end[ dans le texte."""

    def __init__(self, start, end, value=None):
        self.start, self.end = start, end
        self.value = value          # valeur Python (feuilles)
        self.array = []             # éléments d'une table : Node
        self.hash = {}              # clé -> Node
        self.table = False

    def py(self):
        if not self.table:
            return self.value
        if self.hash:
            return {k: v.py() for k, v in self.hash.items()}
        return [v.py() for v in self.array]


def _parse(toks, i):
    kind, val, start, end = toks[i]
    if kind in ("str", "num"):
        return Node(start, end, val), i + 1
    if kind == "op" and val == "-" and toks[i + 1][0] == "num":
        return Node(start, toks[i + 1][3], -toks[i + 1][1]), i + 2
    if kind == "name" and val in ("true", "false"):
        return Node(start, end, val == "true"), i + 1
    if kind == "op" and val == "{":
        node = Node(start, None)
        node.table = True
        i += 1
        while toks[i][1] != "}":
            if toks[i][0] == "name" and toks[i + 1][1] == "=":
                key = toks[i][1]
                node.hash[key], i = _parse(toks, i + 2)
            else:
                v, i = _parse(toks, i)
                node.array.append(v)
            if toks[i][1] in (",", ";"):
                i += 1
            elif toks[i][1] != "}":
                raise NotLiteral()
        node.end = toks[i][3]
        return node, i + 1
    raise NotLiteral()


class DungeonFile:
    def __init__(self, text):
        self.text = text
        toks = [t for t in tokenize(text) if t[0] != "space"]
        self.toks = toks
        for i in range(len(toks) - 2):
            if (toks[i][:2] == ("name", "dungeon") and toks[i + 1][1] == "="
                    and toks[i + 2][1] == "{"):
                try:
                    self.root = _parse(toks, i + 2)[0]
                except (NotLiteral, IndexError):
                    break
                return
        raise ValueError(_("table « dungeon = { ... } » introuvable ou trop "
                           "complexe"))

    # -- lecture ---------------------------------------------------------
    def dungeons(self):
        return [d for d in self.root.array if d.table]

    @staticmethod
    def dungeon_name(d):
        n = d.hash.get("name")
        return n.value if n else "?"

    @staticmethod
    def levels(d):
        lv = d.hash.get("levels")
        return [l for l in lv.array if l.table] if lv else []

    def all_level_names(self):
        return [l.py().get("name") for d in self.dungeons()
                for l in self.levels(d)]

    def names_before(self, di, li=None):
        """Noms des niveaux définis avant l'entrée li du donjon di (avant
        la fin du donjon si li vaut None) : seuls niveaux possibles pour
        chainlevel, que NetHack cherche parmi les niveaux déjà lus."""
        out = []
        for i, d in enumerate(self.dungeons()):
            lv = self.levels(d)
            if i == di:
                lv = lv if li is None else lv[:li]
            out += [l.py().get("name") for l in lv]
            if i == di:
                break
        return out

    # -- écriture --------------------------------------------------------
    def _col(self, pos):
        return pos - (self.text.rfind("\n", 0, pos) + 1)

    def _next_tok(self, pos):
        for t in self.toks:
            if t[2] >= pos:
                return t
        return None

    @staticmethod
    def entry_text(fields, col):
        ind = " " * (col + 3)
        lines = []
        for k in LEVEL_KEYS + [k for k in fields if k not in LEVEL_KEYS]:
            if k in fields and fields[k] is not None:
                v = fields[k]
                if k == "flags" and isinstance(v, list) and len(v) == 1:
                    v = v[0]
                lines.append("%s%s = %s" % (ind, k, lua_value(v)))
        return "{\n" + ",\n".join(lines) + "\n" + " " * col + "}"

    def _edit(self, start, end, new):
        return DungeonFile(self.text[:start] + new + self.text[end:])

    def add_level(self, di, fields):
        """Nouveau DungeonFile avec le niveau ajouté au donjon di."""
        d = self.dungeons()[di]
        lv = d.hash.get("levels")
        if lv is None:
            # pas de table levels : on l'ajoute après la dernière clé
            last = max(list(d.hash.values()) + d.array, key=lambda n: n.end)
            col = self._col(d.hash["name"].start) if "name" in d.hash \
                else self._col(d.start) + 3
            ins = ",\n%slevels = {\n%s%s\n%s}" % (
                " " * col, " " * (col + 3),
                self.entry_text(fields, col + 3), " " * col)
            return self._edit(last.end, last.end, ins)
        if lv.array:
            last = lv.array[-1]
            col = self._col(last.start)
            entry = self.entry_text(fields, col)
            t = self._next_tok(last.end)
            if t and t[1] == ",":
                return self._edit(t[3], t[3], "\n" + " " * col + entry + ",")
            return self._edit(last.end, last.end,
                              ",\n" + " " * col + entry)
        col = self._col(lv.start) + 3
        return self._edit(lv.start, lv.end, "{\n%s%s\n%s}" % (
            " " * col, self.entry_text(fields, col), " " * (col - 3)))

    def replace_level(self, di, li, fields):
        node = self.levels(self.dungeons()[di])[li]
        return self._edit(node.start, node.end,
                          self.entry_text(fields, self._col(node.start)))

    def delete_level(self, di, li):
        lv = self.levels(self.dungeons()[di])
        node = lv[li]
        end = node.end
        t = self._next_tok(end)
        if t and t[1] == ",":
            end = t[3]
        if li + 1 < len(lv):
            return self._edit(node.start, lv[li + 1].start, "")
        if li > 0:
            return self._edit(lv[li - 1].end, end, "")
        return self._edit(node.start, end, "")


def check_level(df, fields, di, li=None):
    """Liste des problèmes d'une entrée de niveau (li : entrée modifiée,
    None pour un ajout)."""
    errs = []
    name = fields.get("name") or ""
    n = fields.get("nlevels")
    longest = name + ("-%d" % n if n else "")
    if not name:
        errs.append(_("nom manquant"))
    elif len(longest) > NAME_MAX:
        errs.append(_("nom trop long : %s (%d caractères au plus)")
                    % (longest, NAME_MAX))
    names = df.all_level_names()
    if li is not None:
        cur = df.levels(df.dungeons()[di])[li].py().get("name")
        names.remove(cur)
    if name in names:
        errs.append(_("le niveau %s existe déjà") % name)
    if not isinstance(fields.get("base"), int):
        errs.append(_("base manquante"))
    chain = fields.get("chainlevel")
    if chain and chain not in df.names_before(di, li):
        errs.append(_("chainlevel %s : niveau inconnu ou défini plus loin")
                    % chain)
    bt = fields.get("bonetag")
    if bt is not None and len(bt) != 1:
        errs.append(_("bonetag : un seul caractère"))
    if li is None and len(df.all_level_names()) + 1 > LEV_LIMIT:
        errs.append(_("plus de %d niveaux spéciaux") % LEV_LIMIT)
    return errs
