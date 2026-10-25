#!/usr/bin/env python3
"""Extrait de l'arbre source de NetHack les listes de monstres, d'objets et
de pièges utilisées par l'éditeur, et les écrit dans nhdata.json.

Usage : python3 gen_data.py [CHEMIN_SOURCES_NETHACK]
"""

import json
import os
import re
import sys

DEFAULT_SRC = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                           "..", "NetHack-5.0.0")

# Macro de objects.h -> symbole de la classe d'objet
OBJ_MACRO_CLASS = {
    "WEAPON": ")", "PROJECTILE": ")", "BOW": ")",
    "ARMOR": "[", "HELM": "[", "CLOAK": "[", "SHIELD": "[",
    "GLOVES": "[", "BOOTS": "[",
    "RING": "=", "AMULET": '"',
    "TOOL": "(", "CONTAINER": "(", "WEPTOOL": "(", "EYEWEAR": "(",
    "FOOD": "%", "POTION": "!", "SCROLL": "?", "SPELL": "+",
    "WAND": "/", "COIN": "$", "GEM": "*", "ROCK": "`",
}
CLASS_CONST = {
    "ILLOBJ": "]", "WEAPON": ")", "ARMOR": "[", "RING": "=", "AMULET": '"',
    "TOOL": "(", "FOOD": "%", "POTION": "!", "SCROLL": "?", "SPBOOK": "+",
    "WAND": "/", "COIN": "$", "GEM": "*", "ROCK": "`", "BALL": "0",
    "CHAIN": "_", "VENOM": ".",
}


def read(src, *path):
    with open(os.path.join(src, *path), encoding="utf-8",
              errors="replace") as f:
        return f.read()


def monsters(src):
    defsym = read(src, "include", "defsym.h")
    symchar = {}
    for m in re.finditer(r"MONSYM\(\s*\d+,\s*'(\\.|.)',\s*\w+,\s*(S_\w+)",
                         defsym):
        ch = m.group(1)
        symchar[m.group(2)] = ch[1] if ch.startswith("\\") else ch
    text = read(src, "include", "monsters.h")
    starts = [m for m in re.finditer(
        r'^\s*MON\(\s*NAMS?\(\s*"([^"]+)"([^)]*)\)\s*,\s*(S_\w+)', text,
        re.M)]
    result = []
    for i, m in enumerate(starts):
        end = starts[i + 1].start() if i + 1 < len(starts) else len(text)
        body = text[m.start():end]
        col = re.findall(r"\b(CLR_\w+|HI_\w+)\b", body)
        entry = {"name": m.group(1),
                 "sym": symchar.get(m.group(3), "?"),
                 "color": col[-1] if col else "CLR_GRAY"}
        # LVL(niveau, vitesse, CA, RM, alignement) et la difficulté,
        # avant-dernier nombre devant la couleur : MON(..., 4, CLR_BROWN, X)
        lvl = re.search(r"LVL\(\s*(-?\d+)", body)
        dif = re.search(r",\s*(\d+)\s*,\s*(?:CLR_\w+|HI_\w+|DRAGON_\w+)\s*,\s*\w+\s*\)",
                        body)
        if lvl:
            entry["level"] = int(lvl.group(1))
        if dif:
            entry["difficulty"] = int(dif.group(1))
        # NAMS("priest", "priestess", "aligned cleric") : formes féminine
        # et neutre, acceptées aussi par des.monster()
        aliases = re.findall(r'"([^"]+)"', m.group(2))
        if aliases:
            entry["aliases"] = aliases
        result.append(entry)
    return result


def objects(src):
    text = read(src, "include", "objects.h")
    macros = "|".join(list(OBJ_MACRO_CLASS) + ["OBJECT"])
    starts = list(re.finditer(
        r'^\s*(%s)\(\s*(?:OBJ\(\s*)?"([^"]+)"' % macros, text, re.M))
    result, seen = [], set()
    for i, m in enumerate(starts):
        name = m.group(2)
        if (name in seen or name == "strange object"
                or name.startswith("generic ")):
            continue
        end = starts[i + 1].start() if i + 1 < len(starts) else len(text)
        body = text[m.start():end]
        sym = OBJ_MACRO_CLASS.get(m.group(1))
        if sym is None:
            c = re.search(r"\b(\w+)_CLASS\b", body)
            sym = CLASS_CONST.get(c.group(1), "?") if c else "?"
        bare = name
        desc = re.match(r'\s*\w+\(\s*(?:OBJ\(\s*)?"[^"]+"\s*,\s*"([^"]+)"',
                        body)
        if m.group(1) == "SPELL":
            name = "spellbook of " + name
        elif m.group(1) == "WAND":
            name = "wand of " + name
        elif m.group(1) == "RING":
            name = "ring of " + name
        elif m.group(1) == "POTION":
            name = "potion of " + name
        elif m.group(1) == "SCROLL":
            name = "scroll of " + name
        seen.add(name)
        entry = {"name": name, "sym": sym}
        # des.object() accepte aussi le nom sans préfixe (« wishing ») et
        # la description (« walking shoes »), sans tenir compte de la casse
        aliases = [a for a in (bare if bare != name else None,
                               desc.group(1) if desc else None) if a]
        if aliases:
            entry["aliases"] = aliases
        result.append(entry)
    return result


def traps(src):
    text = read(src, "src", "sp_lev.c")
    block = re.search(r"trap_types\[\]\s*=\s*\{(.*?)\};", text, re.S)
    return [n for n in re.findall(r'\{\s*"([^"]+)"', block.group(1))]


def trap_names(src, field=1):
    """Nom de des.trap() -> nom du piège dans le jeu (« arrow » -> « arrow
    trap »), traduit par le catalogue du jeu (msgctxt « trap ») ; avec
    field=0, son symbole (S_arrow_trap, des options glyph:). Le piège
    n° k de include/trap.h est le k-ième symbole de piège de
    include/defsym.h."""
    text = read(src, "src", "sp_lev.c")
    block = re.search(r"trap_types\[\]\s*=\s*\{(.*?)\};", text, re.S)
    des = re.findall(r'\{\s*"([^"]+)"\s*,\s*(\w+)\s*\}', block.group(1))
    num = {m.group(1): int(m.group(2)) for m in re.finditer(
        r"^\s*(\w+)\s*=\s*(\d+)\s*,", read(src, "include", "trap.h"),
        re.M)}
    # PCHAR2(n, c, S_x, "nom", "explication", couleur) : l'explication
    # est le nom affiché
    syms = [(m.group(1), m.group(3) or m.group(2)) for m in re.finditer(
        r'PCHAR2?\(\s*\d+,\s*\'[^\']*\',\s*(S_\w+),\s*"([^"]+)"'
        r'(?:\s*,\s*"([^"]+)")?', read(src, "include", "defsym.h"))]
    first = [s for _sym, s in syms].index("arrow trap")
    return {name: syms[first + num[const] - 1][field] for name, const in des
            if num.get(const, 0) > 0}


def main():
    src = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_SRC
    if not os.path.isdir(os.path.join(src, "include")):
        sys.exit("Sources NetHack introuvables : %s" % src)
    data = {"monsters": monsters(src), "objects": objects(src),
            "traps": traps(src), "trap_names": trap_names(src),
            "trap_syms": trap_names(src, 0)}
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       "nhdata.json")
    with open(out, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)
    print("%d monstres, %d objets, %d pièges -> %s" % (
        len(data["monsters"]), len(data["objects"]), len(data["traps"]), out))


if __name__ == "__main__":
    main()
