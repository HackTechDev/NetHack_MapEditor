#!/usr/bin/env python3
"""nhmapedit — petit éditeur de cartes NetHack en mode terminal.

Usage : python3 nhmapedit.py [fichier.lua] [--new LARGEURxHAUTEUR]

Appuyez sur « ? » dans l'éditeur pour l'aide.
"""

import curses
import glob
import json
import locale
import os
import re
import sys

import nhlevel
from nhlevel import Entity, Level

HERE = os.path.dirname(os.path.abspath(__file__))

# Répertoires de données du jeu essayés pour la touche « t » (tester)
HACKDIRS = [
    os.environ.get("NHMAPEDIT_HACKDIR", ""),
    os.path.expanduser("~/nh/install/games/lib/nethackdir"),
    os.path.join(HERE, "..", "NetHack-5.0.0", "playground"),
]
# Préfixe des copies de test, pour ne jamais masquer un niveau de nhdat
TEST_PREFIX = "nhme-"

TOOLS = [
    ("pen", "Pinceau"),
    ("line", "Ligne"),
    ("rect", "Rectangle"),
    ("fillrect", "Rectangle plein"),
    ("room", "Salle"),
    ("fill", "Remplissage"),
    ("copy", "Copier zone"),
    ("paste", "Coller"),
]
TOOL_NAME = dict(TOOLS)
TWO_POINT = {"line", "rect", "fillrect", "room", "copy"}

# Retournements (bits de flip_level() : 1 = haut/bas, 2 = gauche/droite)
FLIP_NAME = {0: "aucun", 1: "vertical", 2: "horizontal",
             3: "horizontal et vertical"}
FLIP_CYCLE = {0: 2, 2: 1, 1: 3, 3: 0}

# Couleurs NetHack (CLR_*) -> (couleur curses, gras)
NH_COLORS = {
    "CLR_BLACK": (curses.COLOR_BLUE, True),
    "CLR_RED": (curses.COLOR_RED, False),
    "CLR_GREEN": (curses.COLOR_GREEN, False),
    "CLR_BROWN": (curses.COLOR_YELLOW, False),
    "CLR_BLUE": (curses.COLOR_BLUE, False),
    "CLR_MAGENTA": (curses.COLOR_MAGENTA, False),
    "CLR_CYAN": (curses.COLOR_CYAN, False),
    "CLR_GRAY": (curses.COLOR_WHITE, False),
    "NO_COLOR": (curses.COLOR_WHITE, False),
    "CLR_ORANGE": (curses.COLOR_RED, True),
    "CLR_BRIGHT_GREEN": (curses.COLOR_GREEN, True),
    "CLR_YELLOW": (curses.COLOR_YELLOW, True),
    "CLR_BRIGHT_BLUE": (curses.COLOR_BLUE, True),
    "CLR_BRIGHT_MAGENTA": (curses.COLOR_MAGENTA, True),
    "CLR_BRIGHT_CYAN": (curses.COLOR_CYAN, True),
    "CLR_WHITE": (curses.COLOR_WHITE, True),
}
HI_COLORS = {
    "HI_DOMESTIC": "CLR_WHITE", "HI_LORD": "CLR_MAGENTA",
    "HI_OBJ": "CLR_MAGENTA", "HI_METAL": "CLR_CYAN",
    "HI_COPPER": "CLR_YELLOW", "HI_SILVER": "CLR_GRAY",
    "HI_GOLD": "CLR_YELLOW", "HI_LEATHER": "CLR_BROWN",
    "HI_CLOTH": "CLR_BROWN", "HI_ORGANIC": "CLR_BROWN",
    "HI_WOOD": "CLR_BROWN", "HI_PAPER": "CLR_WHITE",
    "HI_GLASS": "CLR_BRIGHT_CYAN", "HI_MINERAL": "CLR_GRAY",
    "HI_ZAP": "CLR_BRIGHT_BLUE",
}

TERRAIN_COLOR = {
    " ": "CLR_GRAY", ".": "CLR_GRAY", "#": "CLR_GRAY", "-": "CLR_GRAY",
    "|": "CLR_GRAY", "+": "CLR_BROWN", "S": "CLR_BRIGHT_MAGENTA",
    "H": "CLR_BRIGHT_MAGENTA", "{": "CLR_BLUE", "\\": "CLR_YELLOW",
    "K": "CLR_GRAY", "}": "CLR_BLUE", "P": "CLR_BLUE", "W": "CLR_BLUE",
    "L": "CLR_RED", "Z": "CLR_ORANGE", "I": "CLR_CYAN", "T": "CLR_GREEN",
    "F": "CLR_CYAN", "A": "CLR_BRIGHT_CYAN", "C": "CLR_GRAY",
    "B": "CLR_MAGENTA", "x": "CLR_BLACK",
}

OBJ_CLASS_COLOR = {
    ")": "CLR_CYAN", "[": "CLR_BROWN", "=": "CLR_YELLOW", '"': "CLR_CYAN",
    "(": "CLR_BROWN", "%": "CLR_RED", "!": "CLR_MAGENTA", "?": "CLR_WHITE",
    "+": "CLR_BRIGHT_BLUE", "/": "CLR_BRIGHT_BLUE", "$": "CLR_YELLOW",
    "*": "CLR_GRAY", "`": "CLR_GRAY", "0": "CLR_CYAN", "_": "CLR_CYAN",
}

# Libellés courts pour la palette latérale
SHORT = {
    " ": "roche", ".": "sol", "#": "couloir", "-": "mur -", "|": "mur |",
    "+": "porte", "S": "porte sec.", "H": "coul. sec.", "{": "fontaine",
    "\\": "trône", "K": "évier", "}": "douves", "P": "bassin", "W": "eau",
    "L": "lave", "Z": "mur lave", "I": "glace", "T": "arbre",
    "F": "barreaux", "A": "air", "C": "nuage", "B": "limite",
    "x": "transp.",
}

# Rendu « comme dans le jeu » : symbole et couleur de chaque terrain
# (include/defsym.h) ; les murs sont calculés à part
GAME_GLYPH = {
    " ": (" ", "CLR_GRAY"), ".": ("·", "CLR_GRAY"),
    "#": ("#", "CLR_GRAY"), "+": ("+", "CLR_BROWN"),
    "H": (" ", "CLR_GRAY"),             # couloir secret : roche
    "B": ("·", "CLR_GRAY"),             # limite : devient du sol
    "{": ("{", "CLR_BRIGHT_BLUE"), "\\": ("\\", "CLR_YELLOW"),
    "K": ("{", "CLR_WHITE"), "}": ("}", "CLR_BLUE"), "P": ("}", "CLR_BLUE"),
    "W": ("}", "CLR_BRIGHT_BLUE"), "L": ("}", "CLR_RED"),
    "Z": ("}", "CLR_ORANGE"), "I": ("·", "CLR_CYAN"),
    "T": ("#", "CLR_GREEN"), "F": ("#", "CLR_CYAN"),
    "A": (" ", "CLR_CYAN"), "C": ("#", "CLR_GRAY"),
}
# Murs selon les murs voisins (haut, bas, gauche, droite)
WALL_GLYPH = {
    (0, 0, 0, 0): None, (1, 0, 0, 0): "│", (0, 1, 0, 0): "│",
    (1, 1, 0, 0): "│", (0, 0, 1, 0): "─", (0, 0, 0, 1): "─",
    (0, 0, 1, 1): "─", (0, 1, 0, 1): "┌", (0, 1, 1, 0): "┐",
    (1, 0, 0, 1): "└", (1, 0, 1, 0): "┘", (1, 1, 0, 1): "├",
    (1, 1, 1, 0): "┤", (0, 1, 1, 1): "┬", (1, 0, 1, 1): "┴",
    (1, 1, 1, 1): "┼",
}
# Repli quand le terminal n'est pas en UTF-8
ASCII_GLYPH = {"·": ".", "│": "|", "─": "-"}
ASCII_GLYPH.update({c: "-" for c in "┌┐└┘├┤┬┴┼"})


def game_view(grid, fill=" "):
    """Grille de (caractère, couleur) proche de l'affichage du jeu.

    Les portes secrètes sont dessinées comme le mur qui les entoure, les
    couloirs secrets comme de la roche ; « x » montre le terrain de
    remplissage de level_init."""
    h, w = len(grid), len(grid[0])

    def at(x, y):
        if 0 <= x < w and 0 <= y < h:
            c = grid[y][x]
            return fill if c == "x" else c
        return " "

    def orient(x, y):
        """'-' ou '|' : orientation d'un mur (une porte secrète prend
        celle des murs qui l'encadrent)."""
        c = at(x, y)
        if c != "S":
            return c
        return "-" if at(x - 1, y) == "-" or at(x + 1, y) == "-" else "|"

    out = []
    for y in range(h):
        row = []
        for x in range(w):
            c = at(x, y)
            if c not in "-|S":
                row.append(GAME_GLYPH.get(c, (c, "CLR_GRAY")))
                continue
            o = orient(x, y)
            vert = set("|+S") | ({"-"} if o == "|" else set())
            horiz = set("-+S") | ({"|"} if o == "-" else set())
            key = (int(at(x, y - 1) in vert), int(at(x, y + 1) in vert),
                   int(at(x - 1, y) in horiz), int(at(x + 1, y) in horiz))
            row.append((WALL_GLYPH[key] or ("─" if o == "-" else "│"),
                        "CLR_GRAY"))
        out.append(row)
    return out


# Terrain sur lequel une entité (autre qu'une porte) n'a pas sa place
SOLID = set(" -|STZFB")

HELP = """\
nhmapedit — éditeur de cartes NetHack (fichiers .lua de dat/)

DÉPLACEMENT
  Flèches / h j k l      déplacer le curseur
  Maj+flèches, PgPréc/PgSuiv, Début/Fin   déplacement rapide
  g                      aller à une position (x y)
  c                      afficher / masquer les règles de coordonnées
  f                      aperçu du retournement aléatoire de NetHack :
                         aucun, horizontal, vertical, les deux
  Souris                 clic = déplacer + appliquer l'outil, glisser = peindre,
                         clic droit = pipette

TERRAIN (le caractère tapé devient le pinceau, et peint en mode Pinceau)
  .  sol        #  couloir      -  mur horiz.   |  mur vert.   +  porte
  S  porte secrète   H  couloir secret   {  fontaine   \\  trône   K  évier
  }  douves     P  bassin       W  eau          L  lave        Z  mur de lave
  I  glace      T  arbre        F  barreaux     A  air         C  nuage
  B  limite     x  transparent  e  roche (espace)
  y  pipette : prend comme pinceau le terrain sous le curseur

OUTILS (Espace ou Entrée pour appliquer)
  1 Pinceau   2 Ligne   3 Rectangle   4 Rectangle plein   5 Salle (murs+sol)
  6 Remplissage   7 Copier une zone   8 Coller
  Les outils à deux points : 1er appui = ancre, 2e appui = tracé. Échap annule.
  d  crayon baissé (peint en se déplaçant)    a  avance automatique

ENTITÉS (coordonnées relatives à la carte)
  m  placer une entité (escalier, échelle, autel, monstre, objet, piège,
     porte, gravure)        r  répéter la dernière entité au curseur
  Suppr / Retour arrière / z   supprimer les entités sous le curseur
  i  liste des entités (Entrée: aller, e: modifier, d: supprimer)
  Tab  afficher / masquer les entités
  J  rendu « comme dans le jeu » (murs en traits, sol en points, portes
     et couloirs secrets cachés) ; l'édition reste possible

NIVEAU ET FICHIERS
  p  propriétés (taille, drapeaux, level_init, alignement, éclairage)
  v  vérifier la carte
  t  tester : copie la carte dans le répertoire du jeu, à charger avec
     #wizloaddes en mode wizard (nethack -D)
  u  annuler      U / Ctrl-R  rétablir
  n  nouveau      o  ouvrir      s  enregistrer      w  enregistrer sous
  q  quitter      ?  cette aide

Pour un fichier existant, seuls la première carte des.map et les éléments
à position fixe qui la suivent sont édités ; le reste du script Lua est
conservé tel quel à l'enregistrement.
"""


def load_data():
    path = os.path.join(HERE, "nhdata.json")
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {"monsters": [], "objects": [],
                "traps": [t for t in ("arrow", "dart", "falling rock",
                                      "board", "bear", "land mine",
                                      "rolling boulder", "sleep gas",
                                      "rust", "fire", "pit", "spiked pit",
                                      "hole", "trap door", "teleport",
                                      "level teleport", "magic portal",
                                      "web", "statue", "magic",
                                      "anti magic", "polymorph",
                                      "vibrating square", "random")]}


def bresenham(x0, y0, x1, y1):
    dx, dy = abs(x1 - x0), -abs(y1 - y0)
    sx, sy = (1 if x0 < x1 else -1), (1 if y0 < y1 else -1)
    err = dx + dy
    while True:
        yield x0, y0
        if x0 == x1 and y0 == y1:
            return
        e2 = 2 * err
        if e2 >= dy:
            err += dy
            x0 += sx
        if e2 <= dx:
            err += dx
            y0 += sy


class Cancel(Exception):
    pass


class Editor:
    def __init__(self, scr, path=None, size=None):
        self.scr = scr
        self.data = load_data()
        self.mon = {m["name"]: m for m in self.data["monsters"]}
        self.obj = {o["name"]: o for o in self.data["objects"]}
        self.lvl = Level(*(size or (75, 19)))
        self.path = None
        self.modified = False
        self.cx = self.cy = 0
        self.ox = self.oy = 0       # décalage de la vue
        self.brush = "."
        self.tool = "pen"
        self.anchor = None
        self.pen_down = False
        self.advance = False
        self.show_ents = True
        self.rulers = True          # règles de coordonnées autour de la carte
        self.game = False           # rendu « comme dans le jeu »
        self.flip = 0               # aperçu retourné (bits de FLIP_NAME)
        enc = locale.getpreferredencoding(False).lower().replace("-", "")
        self.unicode = enc == "utf8"
        self.clip = None
        self.template = None        # dernière entité placée
        self.hackdir = next((d for d in HACKDIRS if self.is_hackdir(d)),
                            None)
        self.undo_stack, self.redo_stack = [], []
        self.msg = "Bienvenue ! « ? » pour l'aide."
        self.mouse_down = False
        self.init_colors()
        if path:
            if os.path.exists(path):
                self.open_file(path)
            else:
                self.path = path
                self.msg = "Nouveau fichier : %s" % path

    # ------------------------------------------------------------------
    # Couleurs
    # ------------------------------------------------------------------
    def init_colors(self):
        self.pairs = {}
        if not curses.has_colors():
            return
        curses.start_color()
        try:
            curses.use_default_colors()
            bg = -1
        except curses.error:
            bg = curses.COLOR_BLACK
        for i, c in enumerate(range(8)):
            curses.init_pair(i + 1, c, bg)
            self.pairs[c] = curses.color_pair(i + 1)

    def attr(self, clr):
        clr = HI_COLORS.get(clr, clr)
        c, bold = NH_COLORS.get(clr, (curses.COLOR_WHITE, False))
        a = self.pairs.get(c, 0)
        return a | (curses.A_BOLD if bold else 0)

    # ------------------------------------------------------------------
    # Affichage
    # ------------------------------------------------------------------
    def entity_glyph(self, e):
        k, v = e.kind, e.value
        if k == "stair":
            return ("<" if v == "up" else ">"), "CLR_YELLOW"
        if k == "ladder":
            return ("<" if v == "up" else ">"), "CLR_BROWN"
        if k == "altar":
            return "_", "CLR_GRAY"
        if k == "monster":
            if v in self.mon:
                return self.mon[v]["sym"], self.mon[v]["color"]
            if v and len(v) == 1:
                return v, "CLR_RED"
            return "M", "CLR_BRIGHT_MAGENTA"
        if k == "object":
            sym = None
            if v in self.obj:
                sym = self.obj[v]["sym"]
            elif v and len(v) == 1:
                sym = v
            if sym:
                return sym, OBJ_CLASS_COLOR.get(sym, "CLR_GRAY")
            return "]", "CLR_BRIGHT_MAGENTA"
        if k == "trap":
            return "^", ("CLR_MAGENTA" if v in ("magic portal",
                                               "vibrating square")
                         else "CLR_CYAN")
        if k == "door":
            ch = {"open": "'", "nodoor": ".", "broken": ".",
                  "secret": "S"}.get(v, "+")
            return ch, "CLR_BROWN"
        if k == "engraving":
            return "~", "CLR_BROWN"
        return "?", "CLR_WHITE"

    def top_entity(self, x, y, index=None):
        ents = (index.get((x, y)) if index is not None
                else self.lvl.entities_at(x, y))
        if not ents:
            return None
        prio = ["monster", "object", "trap", "stair", "ladder", "altar",
                "engraving", "door"]
        return min(ents, key=lambda e: prio.index(e.kind))

    def layout(self):
        """Taille de la vue et position du cadre de la carte à l'écran.

        Renvoie (maxy, maxx, vw, vh, side, top, left) : top et left sont
        la ligne et la colonne du coin du cadre ; la case (ox, oy) de la
        carte est affichée en (top + 1, left + 1)."""
        maxy, maxx = self.scr.getmaxyx()
        # règles : 2 lignes au-dessus (dizaines, unités), 3 colonnes à gauche
        rt, rl = (2, 3) if self.rulers else (0, 0)
        side = 26 if maxx >= self.lvl.w + 2 + rl + 27 else 0
        vw = max(1, min(self.lvl.w, maxx - 2 - rl - side))
        vh = max(1, min(self.lvl.h, maxy - 2 - 5 - rt))
        return maxy, maxx, vw, vh, side, 1 + rt, rl

    def fl(self, x, y):
        """Case de la carte <-> case affichée, selon l'aperçu retourné.

        La transformation est sa propre inverse ; ox et oy (décalage de
        la vue) sont exprimés dans les coordonnées affichées."""
        if self.flip & 2:
            x = self.lvl.w - 1 - x
        if self.flip & 1:
            y = self.lvl.h - 1 - y
        return x, y

    def scroll_into_view(self, vw, vh):
        cx, cy = self.fl(self.cx, self.cy)
        if cx < self.ox:
            self.ox = cx
        elif cx >= self.ox + vw:
            self.ox = cx - vw + 1
        if cy < self.oy:
            self.oy = cy
        elif cy >= self.oy + vh:
            self.oy = cy - vh + 1
        self.ox = max(0, min(self.ox, self.lvl.w - vw))
        self.oy = max(0, min(self.oy, self.lvl.h - vh))

    def preview_cells(self):
        """Cases qui seront modifiées par l'outil courant (aperçu)."""
        if self.tool == "paste" and self.clip:
            g = self.clip[0]
            return {(self.cx + x, self.cy + y): g[y][x]
                    for y in range(len(g)) for x in range(len(g[0]))}
        if self.anchor is None:
            return {}
        cells = self.shape_cells(self.anchor, (self.cx, self.cy))
        return cells

    def shape_cells(self, a, b):
        (x0, y0), (x1, y1) = a, b
        lx, hx = sorted((x0, x1))
        ly, hy = sorted((y0, y1))
        t, br = self.tool, self.brush
        cells = {}
        if t == "line":
            for x, y in bresenham(x0, y0, x1, y1):
                cells[(x, y)] = br
        elif t in ("rect", "copy"):
            for x in range(lx, hx + 1):
                cells[(x, ly)] = cells[(x, hy)] = br
            for y in range(ly, hy + 1):
                cells[(lx, y)] = cells[(hx, y)] = br
        elif t == "fillrect":
            for y in range(ly, hy + 1):
                for x in range(lx, hx + 1):
                    cells[(x, y)] = br
        elif t == "room":
            for y in range(ly, hy + 1):
                for x in range(lx, hx + 1):
                    if y in (ly, hy):
                        cells[(x, y)] = "-"
                    elif x in (lx, hx):
                        cells[(x, y)] = "|"
                    else:
                        cells[(x, y)] = "."
        return cells

    def draw(self):
        scr = self.scr
        scr.erase()
        maxy, maxx, vw, vh, side, top, left = self.layout()
        if maxy < 12 or maxx < 40:
            self.put(0, 0, "Terminal trop petit (min. 40x12)")
            scr.refresh()
            return
        self.scroll_into_view(vw, vh)
        lvl = self.lvl
        # en-tête
        name = os.path.basename(self.path) if self.path else "(sans nom)"
        head = " nhmapedit — %s%s   %dx%d" % (
            name, " [modifié]" if self.modified else "", lvl.w, lvl.h)
        if lvl.w > nhlevel.MAP_X_LIM:
            head += "  (largeur > %d !)" % nhlevel.MAP_X_LIM
        if lvl.allowed_flips():
            head += "  (retournable : %s, f pour voir)" % FLIP_NAME[
                lvl.allowed_flips()]
        self.put(0, 0, head.ljust(maxx), curses.A_REVERSE)
        # cadre
        frame = self.attr("CLR_BLACK")
        if self.rulers:
            self.draw_rulers(top, left, vw, vh, frame)
        lch = "<" if self.ox > 0 else "+"
        rch = ">" if self.ox + vw < lvl.w else "+"
        self.put(top, left, lch + "-" * vw + rch, frame)
        self.put(top + vh + 1, left, lch + "-" * vw + rch, frame)
        for y in range(vh):
            self.put(top + 1 + y, left, "^" if self.oy > 0 and y == 0 else
                     "v" if self.oy + vh < lvl.h and y == vh - 1 else "|",
                     frame)
            self.put(top + 1 + y, left + vw + 1, "|", frame)
        # carte
        prev = self.preview_cells()
        index = lvl.entity_index()
        if self.game:
            grid = [row[:] for row in lvl.grid]
            if self.tool != "copy":
                for (x, y), c in prev.items():
                    if 0 <= x < lvl.w and 0 <= y < lvl.h:
                        grid[y][x] = c
            # le rendu se calcule sur la carte telle qu'affichée, pour
            # que les coins de murs soient eux aussi retournés
            shown = [[grid[y][x] for x, y in
                      (self.fl(dx, dy) for dx in range(lvl.w))]
                     for dy in range(lvl.h)]
            view = game_view(shown, lvl.init.get("fg", " "))
        for sy in range(vh):
            for sx in range(vw):
                dx, dy = self.ox + sx, self.oy + sy
                x, y = self.fl(dx, dy)
                if self.game:
                    ch, clr = view[dy][dx]
                    if not self.unicode:
                        ch = ASCII_GLYPH.get(ch, ch)
                    a = self.attr(clr)
                else:
                    ch = lvl.grid[y][x]
                    a = self.attr(TERRAIN_COLOR.get(ch, "CLR_GRAY"))
                if (x, y) in prev:
                    if self.tool != "copy" and not self.game:
                        ch = prev[(x, y)]
                        a = self.attr(TERRAIN_COLOR.get(ch, "CLR_GRAY"))
                    a |= curses.A_REVERSE
                elif self.show_ents:
                    e = self.top_entity(x, y, index)
                    if e:
                        ch, clr = self.entity_glyph(e)
                        a = self.attr(clr)
                self.put(top + 1 + sy, left + 1 + sx, ch, a)
        if side:
            self.draw_side(top, left + vw + 3, maxy)
        self.draw_status(maxy, maxx)
        dx, dy = self.fl(self.cx, self.cy)
        cy = top + 1 + dy - self.oy
        cx = left + 1 + dx - self.ox
        try:
            scr.move(cy, cx)
        except curses.error:
            pass
        scr.refresh()

    def draw_rulers(self, top, left, vw, vh, a):
        """Numéros de colonnes (dizaines puis unités) et de lignes."""
        hi = self.attr("CLR_YELLOW") | curses.A_REVERSE
        # les règles donnent les vraies coordonnées, même retournées
        for sx in range(vw):
            x = self.fl(self.ox + sx, 0)[0]
            ca = hi if x == self.cx else a
            tens = str(x // 10 % 10) if x % 10 == 0 or x == self.cx else " "
            self.put(top - 2, left + 1 + sx, tens, ca)
            self.put(top - 1, left + 1 + sx, str(x % 10), ca)
        for sy in range(vh):
            y = self.fl(0, self.oy + sy)[1]
            self.put(top + 1 + sy, 0, "%2d" % y,
                     hi if y == self.cy else a)

    def draw_side(self, y, x, maxy):
        self.put(y, x, "Outils", curses.A_BOLD)
        for i, (t, label) in enumerate(TOOLS):
            a = curses.A_REVERSE if t == self.tool else 0
            self.put(y + 1 + i, x, " %d %s " % (i + 1, label), a)
        y += len(TOOLS) + 2
        self.put(y, x, "Terrain", curses.A_BOLD)
        y += 1
        cols = 2
        rows = (len(nhlevel.TERRAIN) + cols - 1) // cols
        for i, (c, desc) in enumerate(nhlevel.TERRAIN):
            r, col = i % rows, i // rows
            if y + r >= maxy - 5:
                continue
            short = SHORT.get(c, desc)[:10]
            a = curses.A_REVERSE if c == self.brush else 0
            shown = "e" if c == " " else c
            self.put(y + r, x + col * 13, shown,
                     self.attr(TERRAIN_COLOR.get(c, "CLR_GRAY")) | a)
            self.put(y + r, x + col * 13 + 1, " " + short, a)

    def draw_status(self, maxy, maxx):
        lvl = self.lvl
        x, y = self.cx, self.cy
        c = lvl.grid[y][x]
        o = lvl.origin()
        # coordonnées relatives à la carte (celles des scripts), puis
        # position réelle dans le niveau de 80x21
        info = "(%2d,%2d) niveau %s  '%s' %s" % (
            x, y, "(%2d,%2d)" % (o[0] + x, o[1] + y) if o else "(?)",
            c, nhlevel.TERRAIN_DESC.get(c, "?"))
        ents = lvl.entities_at(x, y)
        if ents:
            info += "  | " + " ; ".join(e.describe() for e in ents)
        self.put(maxy - 4, 0, info[:maxx - 1])
        bname = "roche" if self.brush == " " else self.brush
        st = "Outil: %s   Pinceau: %s (%s)" % (
            TOOL_NAME[self.tool], bname,
            nhlevel.TERRAIN_DESC[self.brush].split(" (")[0])
        if self.pen_down:
            st += "   [crayon baissé]"
        if self.advance:
            st += "   [avance auto]"
        if self.anchor:
            st += "   ancre (%d,%d) -> %dx%d" % (
                self.anchor + (abs(self.cx - self.anchor[0]) + 1,
                               abs(self.cy - self.anchor[1]) + 1))
        if not self.show_ents:
            st += "   [entités masquées]"
        if self.game:
            st += "   [rendu jeu]"
        if self.flip:
            st += "   [aperçu retourné : %s]" % FLIP_NAME[self.flip]
        self.put(maxy - 3, 0, st[:maxx - 1], curses.A_BOLD)
        self.put(maxy - 2, 0, self.msg[:maxx - 1], self.attr("CLR_YELLOW"))
        hint = (" ?:aide  1-8:outils  m:entité  i:liste  p:propriétés  "
                "t:tester  s:enregistrer  q:quitter")
        self.put(maxy - 1, 0, hint[:maxx - 1].ljust(maxx - 1),
                 curses.A_REVERSE)

    def put(self, y, x, s, a=0):
        try:
            self.scr.addstr(y, x, s, a)
        except curses.error:
            pass

    # ------------------------------------------------------------------
    # Fenêtres de saisie
    # ------------------------------------------------------------------
    def prompt(self, label, default="", completer=None):
        """Saisie d'une ligne en bas de l'écran. Échap -> Cancel."""
        buf, pos = list(default), len(default)
        curses.curs_set(1)
        while True:
            maxy, maxx = self.scr.getmaxyx()
            line = label + "".join(buf)
            off = max(0, len(line) - maxx + 2)
            self.put(maxy - 2, 0, " " * (maxx - 1))
            self.put(maxy - 2, 0, line[off:], curses.A_BOLD)
            self.scr.move(maxy - 2, min(maxx - 1, len(label) + pos - off))
            self.scr.refresh()
            k = self.scr.get_wch()
            if k in ("\n", "\r", curses.KEY_ENTER):
                return "".join(buf)
            if k == "\x1b":
                raise Cancel()
            if k in (curses.KEY_BACKSPACE, "\x7f", "\x08"):
                if pos:
                    del buf[pos - 1]
                    pos -= 1
            elif k == curses.KEY_DC:
                if pos < len(buf):
                    del buf[pos]
            elif k == curses.KEY_LEFT:
                pos = max(0, pos - 1)
            elif k == curses.KEY_RIGHT:
                pos = min(len(buf), pos + 1)
            elif k in (curses.KEY_HOME, "\x01"):
                pos = 0
            elif k in (curses.KEY_END, "\x05"):
                pos = len(buf)
            elif k == "\x15":
                buf, pos = [], 0
            elif k == "\t" and completer:
                new = completer("".join(buf))
                if new is not None:
                    buf, pos = list(new), len(new)
            elif isinstance(k, str) and k.isprintable():
                buf.insert(pos, k)
                pos += 1

    def path_completer(self, text):
        matches = glob.glob(os.path.expanduser(text) + "*")
        if not matches:
            return None
        common = os.path.commonprefix(matches)
        if len(matches) == 1 and os.path.isdir(common):
            common += "/"
        if len(matches) > 1:
            self.msg = "  ".join(os.path.basename(m) for m in matches[:12])
        return common

    def window(self, h, w):
        maxy, maxx = self.scr.getmaxyx()
        h, w = min(h, maxy - 2), min(w, maxx - 2)
        win = curses.newwin(h, w, (maxy - h) // 2, (maxx - w) // 2)
        win.keypad(True)
        return win, h, w

    def pick(self, title, items, initial=None, custom=False, hint=""):
        """Liste filtrable. items : [(libellé, valeur)]. Échap -> Cancel.

        On tape pour filtrer ; avec custom=True, Entrée sur un filtre sans
        correspondance renvoie le texte saisi."""
        filt, sel, top = "", 0, 0
        if initial is not None:
            for i, (_, v) in enumerate(items):
                if v == initial:
                    sel = i
        curses.curs_set(0)
        while True:
            shown = [it for it in items
                     if filt.lower() in it[0].lower()] if filt else items
            maxy, maxx = self.scr.getmaxyx()
            width = max([len(title) + 4, len(hint) + 4, 40] +
                        [len(l) + 6 for l, _ in shown[:200]])
            win, h, w = self.window(min(len(items), maxy - 8) + 5, width)
            n = h - 5
            sel = max(0, min(sel, len(shown) - 1))
            if sel < top:
                top = sel
            elif sel >= top + n:
                top = sel - n + 1
            win.erase()
            win.box()
            win.addnstr(0, 2, " %s " % title, w - 4, curses.A_BOLD)
            for i in range(n):
                j = top + i
                if j >= len(shown):
                    break
                a = curses.A_REVERSE if j == sel else 0
                win.addnstr(1 + i, 2, shown[j][0].ljust(w - 4), w - 4, a)
            more = "%d/%d" % (len(shown), len(items))
            win.addnstr(h - 3, 2, "Filtre : " + filt, w - 4 - len(more) - 1,
                        curses.A_BOLD)
            win.addnstr(h - 3, w - 2 - len(more), more, len(more))
            win.addnstr(h - 2, 2, hint or "Entrée: choisir  Échap: annuler",
                        w - 4)
            win.refresh()
            k = win.get_wch()
            if k in ("\n", "\r", curses.KEY_ENTER):
                if shown:
                    curses.curs_set(1)
                    return shown[sel][1]
                if custom and filt:
                    curses.curs_set(1)
                    return filt
            elif k == "\x1b":
                curses.curs_set(1)
                raise Cancel()
            elif k == curses.KEY_UP:
                sel -= 1
            elif k == curses.KEY_DOWN:
                sel += 1
            elif k == curses.KEY_PPAGE:
                sel -= n
            elif k == curses.KEY_NPAGE:
                sel += n
            elif k == curses.KEY_HOME:
                sel = 0
            elif k == curses.KEY_END:
                sel = len(shown) - 1
            elif k in (curses.KEY_BACKSPACE, "\x7f", "\x08"):
                filt = filt[:-1]
                sel = 0
            elif k == curses.KEY_RESIZE:
                self.draw()
            elif isinstance(k, str) and k.isprintable():
                filt += k
                sel = 0

    def message_box(self, title, text):
        lines = text.split("\n")
        top = 0
        curses.curs_set(0)
        while True:
            maxy, maxx = self.scr.getmaxyx()
            win, h, w = self.window(len(lines) + 3,
                                    max(len(l) for l in lines + [title]) + 4)
            n = h - 3
            win.erase()
            win.box()
            win.addnstr(0, 2, " %s " % title, w - 4, curses.A_BOLD)
            for i in range(n):
                if top + i < len(lines):
                    win.addnstr(1 + i, 2, lines[top + i], w - 4)
            foot = " Échap/q: fermer "
            if len(lines) > n:
                foot = " ↑↓ défiler" + foot
            win.addnstr(h - 1, max(1, w - len(foot) - 2), foot, w - 3)
            win.refresh()
            k = win.getch()
            if k in (curses.KEY_DOWN, ord("j"), curses.KEY_NPAGE, ord(" ")):
                step = n if k in (curses.KEY_NPAGE, ord(" ")) else 1
                top = min(max(0, len(lines) - n), top + step)
            elif k in (curses.KEY_UP, ord("k"), curses.KEY_PPAGE):
                step = n if k == curses.KEY_PPAGE else 1
                top = max(0, top - step)
            elif k == curses.KEY_RESIZE:
                self.draw()
            else:
                break
        curses.curs_set(1)

    def confirm(self, question):
        try:
            r = self.prompt(question + " (o/n) ")
        except Cancel:
            return False
        return r.strip().lower() in ("o", "oui", "y", "yes")

    # ------------------------------------------------------------------
    # Modifications
    # ------------------------------------------------------------------
    def checkpoint(self):
        self.undo_stack.append(self.lvl.snapshot())
        if len(self.undo_stack) > 300:
            del self.undo_stack[0]
        self.redo_stack.clear()
        self.modified = True

    def undo(self):
        if not self.undo_stack:
            self.msg = "Rien à annuler."
            return
        self.redo_stack.append(self.lvl.snapshot())
        self.lvl.restore(self.undo_stack.pop())
        self.clamp_cursor()
        self.modified = True
        self.msg = "Annulé."

    def redo(self):
        if not self.redo_stack:
            self.msg = "Rien à rétablir."
            return
        self.undo_stack.append(self.lvl.snapshot())
        self.lvl.restore(self.redo_stack.pop())
        self.clamp_cursor()
        self.modified = True
        self.msg = "Rétabli."

    def clamp_cursor(self):
        self.cx = max(0, min(self.cx, self.lvl.w - 1))
        self.cy = max(0, min(self.cy, self.lvl.h - 1))

    def paint(self, cells):
        if any(self.lvl.grid[y][x] != c for (x, y), c in cells.items()
               if 0 <= x < self.lvl.w and 0 <= y < self.lvl.h):
            self.checkpoint()
            for (x, y), c in cells.items():
                self.lvl.set(x, y, c)

    def apply(self):
        t = self.tool
        if t == "pen":
            self.paint({(self.cx, self.cy): self.brush})
        elif t == "fill":
            self.flood_fill(self.cx, self.cy, self.brush)
        elif t == "paste":
            self.paste()
        elif self.anchor is None:
            self.anchor = (self.cx, self.cy)
            self.msg = "Ancre posée ; déplacez-vous puis Espace (Échap annule)."
        else:
            a, b = self.anchor, (self.cx, self.cy)
            self.anchor = None
            if t == "copy":
                self.copy(a, b)
            else:
                self.paint(self.shape_cells(a, b))
                self.msg = "%s tracé." % TOOL_NAME[t]

    def flood_fill(self, x, y, c):
        old = self.lvl.grid[y][x]
        if old == c:
            return
        self.checkpoint()
        stack, n = [(x, y)], 0
        while stack:
            x, y = stack.pop()
            if (0 <= x < self.lvl.w and 0 <= y < self.lvl.h
                    and self.lvl.grid[y][x] == old):
                self.lvl.grid[y][x] = c
                n += 1
                stack += [(x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)]
        self.msg = "%d cases remplies." % n

    def copy(self, a, b):
        lx, hx = sorted((a[0], b[0]))
        ly, hy = sorted((a[1], b[1]))
        g = [self.lvl.grid[y][lx:hx + 1] for y in range(ly, hy + 1)]
        ents = []
        for e in self.lvl.entities:
            if lx <= e.x <= hx and ly <= e.y <= hy:
                c = e.copy()
                c.origin = None
                c.x -= lx
                c.y -= ly
                ents.append(c)
        self.clip = ([r[:] for r in g], ents)
        self.tool = "paste"
        self.msg = ("Zone %dx%d copiée (%d entités). Outil Coller actif."
                    % (hx - lx + 1, hy - ly + 1, len(ents)))

    def paste(self):
        if not self.clip:
            self.msg = "Presse-papiers vide (outil 7 pour copier)."
            return
        g, ents = self.clip
        self.checkpoint()
        for y, row in enumerate(g):
            for x, c in enumerate(row):
                self.lvl.set(self.cx + x, self.cy + y, c)
        for e in ents:
            c = e.copy()
            c.x += self.cx
            c.y += self.cy
            if c.x < self.lvl.w and c.y < self.lvl.h:
                self.lvl.entities.append(c)
        self.msg = "Collé."

    def eyedropper(self):
        """Pipette : le terrain sous le curseur devient le pinceau."""
        self.brush = self.lvl.grid[self.cy][self.cx]
        self.msg = "Pipette : pinceau %s." % nhlevel.TERRAIN_DESC.get(
            self.brush, repr(self.brush))

    def move(self, dx, dy):
        """Déplace le curseur de (dx, dy) cases à l'écran."""
        if self.flip & 2:
            dx = -dx
        if self.flip & 1:
            dy = -dy
        nx = max(0, min(self.lvl.w - 1, self.cx + dx))
        ny = max(0, min(self.lvl.h - 1, self.cy + dy))
        if self.pen_down and self.tool == "pen":
            cells = {p: self.brush for p in bresenham(self.cx, self.cy,
                                                      nx, ny)}
            self.paint(cells)
        self.cx, self.cy = nx, ny

    # ------------------------------------------------------------------
    # Entités
    # ------------------------------------------------------------------
    def ask_extra(self, current=None):
        txt = ""
        if current:
            txt = ", ".join("%s = %s" % (k, nhlevel.lua_value(v))
                            for k, v in current.items())
        while True:
            s = self.prompt("Options Lua (ex: peaceful=1, asleep=1) : ", txt)
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
            self.msg = "Syntaxe invalide : clé = valeur, séparées par des virgules."

    def edit_entity_fields(self, kind, value=None, extra=None):
        """Demande les paramètres d'une entité. Renvoie (value, extra)."""
        extra = dict(extra or {})
        if kind in ("stair", "ladder"):
            value = self.pick("Direction", [("montant (up)", "up"),
                                            ("descendant (down)", "down")],
                              value)
        elif kind == "altar":
            value = self.pick("Alignement de l'autel",
                              [(a, a) for a in nhlevel.ALTAR_ALIGNS], value)
            extra["type"] = self.pick(
                "Type d'autel", [(t, t) for t in nhlevel.ALTAR_TYPES],
                extra.get("type", "altar"))
        elif kind == "monster":
            items = [("(aléatoire)", None)] + [
                ("%s  %s" % (m["sym"], m["name"]), m["name"])
                for m in self.data["monsters"]]
            value = self.pick("Monstre (tapez pour filtrer ; une lettre "
                              "seule = classe)", items, value, custom=True)
            extra = self.ask_extra(extra)
        elif kind == "object":
            items = [("(aléatoire)", None)] + [
                ("%s  %s" % (o["sym"], o["name"]), o["name"])
                for o in self.data["objects"]]
            value = self.pick("Objet (tapez pour filtrer ; un symbole "
                              "seul = classe)", items, value, custom=True)
            extra = self.ask_extra(extra)
        elif kind == "trap":
            value = self.pick("Type de piège",
                              [(t, t) for t in self.data["traps"]], value)
        elif kind == "door":
            value = self.pick("État de la porte",
                              [(s, s) for s in nhlevel.DOOR_STATES], value)
        elif kind == "engraving":
            etype = self.pick("Type de gravure",
                              [(t, t) for t in nhlevel.ENGRAVING_TYPES],
                              extra.get("type", "engrave"))
            value = self.prompt("Texte gravé : ", value or "Elbereth")
            extra.pop("type", None)
            extra = dict(type=etype, **extra)
        return value, extra

    def place_entity(self):
        kinds = [("%s" % nhlevel.ENTITY_LABEL[k].capitalize(), k)
                 for k in nhlevel.ENTITY_KINDS]
        kind = self.pick("Placer une entité en (%d,%d)" % (self.cx, self.cy),
                         kinds)
        value, extra = self.edit_entity_fields(kind)
        self.add_entity(Entity(kind, self.cx, self.cy, value, extra))

    def add_entity(self, e):
        e.x, e.y = self.cx, self.cy
        self.checkpoint()
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
        self.msg = "Ajouté : %s (r pour répéter)." % e.describe()

    def delete_entities(self):
        ents = self.lvl.entities_at(self.cx, self.cy)
        if not ents:
            self.msg = "Aucune entité ici."
            return
        self.checkpoint()
        self.lvl.entities = [e for e in self.lvl.entities if e not in ents]
        self.msg = "%d entité(s) supprimée(s)." % len(ents)

    def entity_list(self):
        sel = None
        while True:
            ents = self.lvl.entities
            if not ents:
                self.msg = "Aucune entité."
                return
            ents.sort(key=lambda e: (e.y, e.x))
            items = [("(%2d,%2d) %s %s" % (e.x, e.y, self.entity_glyph(e)[0],
                                          e.describe()), i)
                     for i, e in enumerate(ents)]
            if sel is None:
                here = [i for i, e in enumerate(ents)
                        if (e.x, e.y) == (self.cx, self.cy)]
                sel = here[0] if here else 0
            hint = "Entrée: aller  e: modifier  d: supprimer  Échap: fermer"
            try:
                i, action = self.pick_action("Entités (%d)" % len(ents),
                                             items, sel, hint)
            except Cancel:
                return
            e = ents[i]
            sel = i
            if action == "goto":
                self.cx, self.cy = e.x, e.y
                return
            if action == "delete":
                self.checkpoint()
                ents.remove(e)
                self.msg = "Supprimé : %s" % e.describe()
                sel = max(0, i - 1)
            elif action == "edit":
                try:
                    value, extra = self.edit_entity_fields(e.kind, e.value,
                                                           e.extra)
                except Cancel:
                    continue
                self.checkpoint()
                e.value, e.extra = value, extra
                self.msg = "Modifié : %s" % e.describe()

    def pick_action(self, title, items, sel, hint):
        """Comme pick() sans filtre, avec les touches e et d."""
        top = 0
        curses.curs_set(0)
        try:
            while True:
                maxy, maxx = self.scr.getmaxyx()
                width = max([len(hint) + 4] + [len(l) + 4 for l, _ in items])
                win, h, w = self.window(len(items) + 4, width)
                n = h - 4
                sel = max(0, min(sel, len(items) - 1))
                if sel < top:
                    top = sel
                elif sel >= top + n:
                    top = sel - n + 1
                win.erase()
                win.box()
                win.addnstr(0, 2, " %s " % title, w - 4, curses.A_BOLD)
                for i in range(n):
                    j = top + i
                    if j < len(items):
                        a = curses.A_REVERSE if j == sel else 0
                        win.addnstr(1 + i, 2, items[j][0].ljust(w - 4),
                                    w - 4, a)
                win.addnstr(h - 2, 2, hint, w - 4)
                win.refresh()
                k = win.getch()
                if k in (10, 13, curses.KEY_ENTER):
                    return items[sel][1], "goto"
                if k == ord("e"):
                    return items[sel][1], "edit"
                if k in (ord("d"), curses.KEY_DC):
                    return items[sel][1], "delete"
                if k in (27, ord("q")):
                    raise Cancel()
                if k == curses.KEY_UP:
                    sel -= 1
                elif k == curses.KEY_DOWN:
                    sel += 1
                elif k == curses.KEY_PPAGE:
                    sel -= n
                elif k == curses.KEY_NPAGE:
                    sel += n
        finally:
            curses.curs_set(1)

    # ------------------------------------------------------------------
    # Propriétés du niveau
    # ------------------------------------------------------------------
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

    # ------------------------------------------------------------------
    # Vérification
    # ------------------------------------------------------------------
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
        if not out:
            out = ["Aucun problème détecté."]
        self.message_box("Vérification", "\n".join(out))

    # ------------------------------------------------------------------
    # Fichiers
    # ------------------------------------------------------------------
    def open_file(self, path):
        try:
            with open(path, encoding="utf-8") as f:
                text = f.read()
            lvl, _ = nhlevel.parse_level(text)
        except (OSError, ValueError, UnicodeDecodeError) as e:
            self.msg = "Erreur à l'ouverture : %s" % e
            return False
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
        self.modified = False
        self.msg = "Enregistré : %s" % path
        return True

    @staticmethod
    def is_hackdir(d):
        return bool(d) and any(os.path.isfile(os.path.join(d, f))
                               for f in ("nhdat", "sysconf"))

    def test_in_game(self):
        """Copie l'état courant de la carte dans le répertoire du jeu."""
        if not self.hackdir:
            d = self.prompt("Répertoire de données de NetHack (nethackdir) : ",
                            HACKDIRS[1], self.path_completer)
            d = os.path.expanduser(d.strip())
            if not self.is_hackdir(d):
                self.msg = "%s : ni nhdat ni sysconf, répertoire refusé." % d
                return
            self.hackdir = d
        base = os.path.splitext(os.path.basename(self.path or "sans-nom"))[0]
        name = TEST_PREFIX + re.sub(r"[^A-Za-z0-9_-]", "_", base)
        dest = os.path.join(self.hackdir, name + ".lua")
        # NetHack retourne au hasard les niveaux sans « noflip » : on
        # l'ajoute à la copie de test pour retrouver la carte telle quelle
        flags = self.lvl.flags
        if not {"noflip", "noflipx", "noflipy"} & set(flags):
            self.lvl.flags = flags + ["noflip"]
        try:
            with open(dest, "w", encoding="utf-8") as f:
                f.write(self.lvl.to_lua(base))
        except OSError as e:
            self.msg = "Erreur d'écriture : %s" % e
            return
        finally:
            self.lvl.flags = flags
        self.msg = "Copié pour test : %s" % dest
        self.message_box("Tester dans NetHack", "\n".join([
            "Carte copiée (état actuel, même non enregistré) dans :",
            "  " + dest,
            "",
            "Dans un autre terminal :",
            "  1. lancez le jeu en mode wizard :  nethack -D",
            "  2. tapez  #wizloaddes  puis Entrée",
            "  3. répondez :  " + name,
            "",
            "Après une modification, appuyez de nouveau sur t puis",
            "refaites #wizloaddes : inutile de relancer le jeu.",
            "Ctrl-F révèle toute la carte, Ctrl-T téléporte.",
            "(La copie de test a le drapeau noflip : sinon NetHack",
            "retourne la carte au hasard à chaque chargement.)",
        ]))

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

    # ------------------------------------------------------------------
    # Boucle principale
    # ------------------------------------------------------------------
    def run(self):
        curses.raw()
        curses.mousemask(curses.ALL_MOUSE_EVENTS
                         | curses.REPORT_MOUSE_POSITION)
        curses.mouseinterval(0)
        # suivi du glissement de la souris (xterm 1002)
        sys.stdout.write("\033[?1002h")
        sys.stdout.flush()
        try:
            while True:
                self.draw()
                try:
                    k = self.scr.get_wch()
                except curses.error:
                    continue
                try:
                    if self.handle(k) is False:
                        break
                except Cancel:
                    self.msg = "Annulé."
        finally:
            sys.stdout.write("\033[?1002l")
            sys.stdout.flush()

    def handle(self, k):
        lvl = self.lvl
        lay = self.layout()
        vh = lay[3]
        moves = {curses.KEY_LEFT: (-1, 0), curses.KEY_RIGHT: (1, 0),
                 curses.KEY_UP: (0, -1), curses.KEY_DOWN: (0, 1),
                 "h": (-1, 0), "l": (1, 0), "k": (0, -1), "j": (0, 1),
                 curses.KEY_SLEFT: (-8, 0), curses.KEY_SRIGHT: (8, 0),
                 curses.KEY_SR: (0, -4), curses.KEY_SF: (0, 4),
                 curses.KEY_PPAGE: (0, -vh), curses.KEY_NPAGE: (0, vh)}
        if k in moves:
            self.move(*moves[k])
        elif k == curses.KEY_HOME:
            self.move(-self.fl(self.cx, 0)[0], 0)
        elif k == curses.KEY_END:
            self.move(lvl.w - 1 - self.fl(self.cx, 0)[0], 0)
        elif k == curses.KEY_MOUSE:
            self.mouse(lay)
        elif k == curses.KEY_RESIZE:
            pass
        elif k in (" ", "\n", "\r", curses.KEY_ENTER):
            self.apply()
        elif k == "\x1b":
            if self.anchor:
                self.anchor = None
                self.msg = "Tracé annulé."
            elif self.tool == "paste":
                self.tool = "pen"
                self.msg = "Outil Pinceau."
        elif isinstance(k, str) and k in "12345678":
            self.tool = TOOLS[int(k) - 1][0]
            self.anchor = None
            self.msg = "Outil : %s." % TOOL_NAME[self.tool]
            if self.tool == "paste" and not self.clip:
                self.msg += " (presse-papiers vide)"
        elif isinstance(k, str) and (k in nhlevel.TERRAIN_CHARS
                                     and k != " " or k == "e"):
            self.brush = " " if k == "e" else k
            if self.tool == "pen":
                self.paint({(self.cx, self.cy): self.brush})
                if self.advance:
                    self.move(1, 0)
            self.msg = "Pinceau : %s." % nhlevel.TERRAIN_DESC[self.brush]
        elif k == "d":
            self.pen_down = not self.pen_down
            if self.pen_down and self.tool == "pen":
                self.paint({(self.cx, self.cy): self.brush})
            self.msg = "Crayon %s." % ("baissé" if self.pen_down else "levé")
        elif k == "y":
            self.eyedropper()
        elif k == "a":
            self.advance = not self.advance
            self.msg = "Avance automatique %s." % (
                "activée" if self.advance else "désactivée")
        elif k == "m":
            self.place_entity()
        elif k == "r":
            if self.template:
                self.add_entity(self.template.copy())
            else:
                self.msg = "Aucune entité à répéter (m pour en placer une)."
        elif k in (curses.KEY_DC, curses.KEY_BACKSPACE, "\x7f", "\x08", "z"):
            self.delete_entities()
        elif k == "i":
            self.entity_list()
        elif k == "\t":
            self.show_ents = not self.show_ents
        elif k == "J":
            self.game = not self.game
            self.msg = ("Rendu « comme dans le jeu »." if self.game
                        else "Rendu des caractères de carte (des.map).")
        elif k == "f":
            self.flip = FLIP_CYCLE[self.flip]
            if not self.flip:
                self.msg = "Carte affichée dans son sens d'origine."
            else:
                self.msg = "Aperçu retourné : %s. %s" % (
                    FLIP_NAME[self.flip],
                    "NetHack peut le faire au chargement."
                    if self.flip & lvl.allowed_flips() == self.flip else
                    "Empêché par les drapeaux du niveau (noflip...).")
        elif k == "c":
            self.rulers = not self.rulers
            self.msg = "Règles de coordonnées %s." % (
                "affichées" if self.rulers else "masquées")
        elif k == "p":
            self.properties()
        elif k == "v":
            self.check()
        elif k == "t":
            self.test_in_game()
        elif k == "g":
            s = self.prompt("Aller à « x y » : ", "%d %d" % (self.cx, self.cy))
            try:
                x, y = (int(v) for v in s.split())
                self.cx, self.cy = x, y
                self.clamp_cursor()
            except ValueError:
                self.msg = "Position invalide."
        elif k == "u":
            self.undo()
        elif k in ("U", "\x12"):
            self.redo()
        elif k == "n":
            self.new_level()
        elif k == "o":
            self.check_unsaved()
            path = self.prompt("Ouvrir : ", os.getcwd() + "/",
                               self.path_completer)
            self.open_file(os.path.expanduser(path.strip()))
        elif k in ("s", "\x13"):
            self.save()
        elif k == "w":
            self.save(as_new=True)
        elif k == "?":
            self.message_box("Aide", HELP.rstrip())
        elif k in ("q", "\x11"):
            if self.check_unsaved():
                return False
        elif k == "\x03":
            if not self.modified or self.confirm("Quitter sans enregistrer ?"):
                return False
        return True

    def mouse(self, lay):
        _, _, vw, vh, _, top, left = lay
        try:
            _, mx, my, _, bstate = curses.getmouse()
        except curses.error:
            return
        sx, sy = mx - left - 1, my - top - 1
        x, y = self.fl(sx + self.ox, sy + self.oy)
        inside = 0 <= sx < vw and 0 <= sy < vh
        if bstate & (curses.BUTTON3_PRESSED | curses.BUTTON3_CLICKED):
            if inside:
                self.cx, self.cy = x, y
                self.eyedropper()
        elif bstate & curses.BUTTON1_PRESSED and inside:
            self.mouse_down = True
            self.cx, self.cy = x, y
            self.apply()
        elif bstate & curses.BUTTON1_CLICKED and inside:
            self.cx, self.cy = x, y
            self.apply()
        elif bstate & curses.BUTTON1_RELEASED:
            # fin d'un glisser avec un outil à deux points
            if (self.mouse_down and inside and self.tool in TWO_POINT
                    and self.anchor and (x, y) != self.anchor):
                self.cx, self.cy = x, y
                self.apply()
            self.mouse_down = False
        elif bstate & curses.REPORT_MOUSE_POSITION and inside:
            if self.mouse_down and self.tool == "pen":
                self.paint({p: self.brush
                            for p in bresenham(self.cx, self.cy, x, y)})
            self.cx, self.cy = x, y
        elif bstate & curses.BUTTON4_PRESSED:
            self.move(0, -1)
        elif bstate & getattr(curses, "BUTTON5_PRESSED", 0):
            self.move(0, 1)


def main():
    args = sys.argv[1:]
    size, path = None, None
    while args:
        a = args.pop(0)
        if a in ("-h", "--help"):
            print(__doc__.strip())
            print()
            print(HELP)
            return
        if a == "--new" and args:
            try:
                w, h = (int(v) for v in args.pop(0).lower().split("x"))
                size = (min(w, nhlevel.MAX_W), min(h, nhlevel.MAX_H))
            except ValueError:
                sys.exit("--new attend LARGEURxHAUTEUR, ex: --new 40x12")
        else:
            path = a
    locale.setlocale(locale.LC_ALL, "")
    os.environ.setdefault("ESCDELAY", "25")

    def run(scr):
        scr.keypad(True)
        Editor(scr, path, size).run()

    curses.wrapper(run)


if __name__ == "__main__":
    main()
