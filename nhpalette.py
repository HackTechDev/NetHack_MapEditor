"""Symboles et couleurs du jeu pour le rendu « comme dans le jeu » (J).

Les options « glyph:S_<symbole>:<caractère>[/R-G-B] » d'un .nethackrc
changent le caractère et la couleur d'un symbole de la carte. La branche
cybernethack fournit une palette néon dans doc/cyberpunk.nethackrc (murs
cyan, sol violet, portes rose vif...) ; le .nethackrc du joueur passe
par-dessus. L'éditeur en tire le même aspect que le jeu.
"""

import os
import re

# Terrain des cartes des.map -> symbole du jeu
TERRAIN_SYM = {
    ".": "S_room", "#": "S_corr", "+": "S_vcdoor", "{": "S_fountain",
    "\\": "S_throne", "K": "S_sink", "}": "S_pool", "P": "S_pool",
    "W": "S_water", "L": "S_lava", "Z": "S_lavawall", "I": "S_ice",
    "T": "S_tree", "F": "S_bars", "A": "S_air", "C": "S_cloud",
    "B": "S_room",
}
# Murs du rendu jeu (caractères de WALL_GLYPH) -> symbole du jeu
WALL_SYM = {
    "│": "S_vwall", "─": "S_hwall", "┌": "S_tlcorn", "┐": "S_trcorn",
    "└": "S_blcorn", "┘": "S_brcorn", "┼": "S_crwall", "┴": "S_tuwall",
    "┬": "S_tdwall", "┤": "S_tlwall", "├": "S_trwall",
}
# Classe d'objet -> symbole du jeu
CLASS_SYM = {
    ")": "S_weapon", "[": "S_armor", "=": "S_ring", '"': "S_amulet",
    "(": "S_tool", "%": "S_food", "!": "S_potion", "?": "S_scroll",
    "+": "S_book", "/": "S_wand", "$": "S_coin", "*": "S_gem",
    "`": "S_rock", "0": "S_ball", "_": "S_chain", ".": "S_venom",
}
GLYPH = re.compile(r"glyph\s*:\s*(S_\w+)\s*:\s*([^/,\s]+)?"
                   r"(?:/(\d+)-(\d+)-(\d+))?")


def parse_rc(path):
    """{S_nom: (caractère ou None, (r, g, b) ou None)} des options glyph
    d'un .nethackrc (les suivantes l'emportent)."""
    out = {}
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            lines = f.read().splitlines()
    except OSError:
        return out
    for line in lines:
        line = line.strip()
        if line.startswith("#") or not line.upper().startswith("OPTIONS="):
            continue
        for m in GLYPH.finditer(line):
            sym, ch = m.group(1), m.group(2)
            if ch and ch.upper().startswith("U+"):
                try:
                    ch = chr(int(ch[2:], 16))
                except ValueError:
                    ch = None
            elif ch and len(ch) != 1:
                ch = None
            rgb = (tuple(min(255, int(m.group(i))) for i in (3, 4, 5))
                   if m.group(3) else None)
            old = out.get(sym, (None, None))
            out[sym] = (ch or old[0], rgb or old[1])
    return out


class Palette:
    """Fusion de plusieurs .nethackrc, dans l'ordre (le dernier gagne)."""

    def __init__(self, paths=(), unicode=True):
        self.glyphs = {}
        self.sources = []
        for p in paths:
            g = parse_rc(p) if p else {}
            if g:
                self.sources.append(p)
            for sym, (ch, rgb) in g.items():
                old = self.glyphs.get(sym, (None, None))
                self.glyphs[sym] = (ch or old[0], rgb or old[1])
        if not unicode:                 # terminal sans UTF-8
            self.glyphs = {s: (ch if ch and ord(ch) < 128 else None, rgb)
                           for s, (ch, rgb) in self.glyphs.items()}

    def __bool__(self):
        return bool(self.glyphs)

    def apply(self, sym, ch, clr):
        """(caractère, couleur) du symbole sym, à défaut ceux donnés ; la
        couleur est un nom CLR_* ou un triplet (r, g, b)."""
        g = self.glyphs.get(sym)
        if not g:
            return ch, clr
        return g[0] or ch, g[1] or clr

    def terrain(self, c, ch, clr):
        sym = WALL_SYM.get(ch) if c in "-|S" else TERRAIN_SYM.get(c)
        return self.apply(sym, ch, clr) if sym else (ch, clr)


def default_paths(source_dirs, lang):
    """La palette néon du thème cyberpunk (si le jeu est en @cyber), puis
    le .nethackrc du joueur."""
    paths = []
    if "@cyber" in (lang or ""):
        paths += [p for p in (os.path.join(d, "doc", "cyberpunk.nethackrc")
                              for d in source_dirs) if os.path.isfile(p)][:1]
    rc = os.environ.get("NETHACKRC") or os.path.expanduser("~/.nethackrc")
    paths.append(rc)
    return paths


def xterm256(rgb):
    """Indice de la couleur la plus proche dans la palette de 256
    couleurs de xterm (cube 6x6x6 et gris)."""
    steps = [0, 95, 135, 175, 215, 255]

    def near(v):
        return min(range(6), key=lambda i: abs(steps[i] - v))
    r, g, b = (near(v) for v in rgb)
    cube = (16 + 36 * r + 6 * g + b,
            (steps[r], steps[g], steps[b]))
    gray = min(range(24), key=lambda i: abs(8 + 10 * i - sum(rgb) / 3))
    grayc = (232 + gray, (8 + 10 * gray,) * 3)

    def dist(c):
        return sum((a - b) ** 2 for a, b in zip(c[1], rgb))
    return min((cube, grayc), key=dist)[0]


# Couleurs NetHack de base et leur valeur approchée, pour un terminal
# sans 256 couleurs
BASIC_RGB = {
    "CLR_RED": (170, 0, 0), "CLR_GREEN": (0, 170, 0),
    "CLR_BROWN": (170, 85, 0), "CLR_BLUE": (0, 0, 170),
    "CLR_MAGENTA": (170, 0, 170), "CLR_CYAN": (0, 170, 170),
    "CLR_GRAY": (170, 170, 170), "CLR_ORANGE": (255, 85, 85),
    "CLR_BRIGHT_GREEN": (85, 255, 85), "CLR_YELLOW": (255, 255, 85),
    "CLR_BRIGHT_BLUE": (85, 85, 255), "CLR_BRIGHT_MAGENTA": (255, 85, 255),
    "CLR_BRIGHT_CYAN": (85, 255, 255), "CLR_WHITE": (255, 255, 255),
}


def nearest_basic(rgb):
    return min(BASIC_RGB, key=lambda n: sum(
        (a - b) ** 2 for a, b in zip(BASIC_RGB[n], rgb)))
