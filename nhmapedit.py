#!/usr/bin/env python3
"""nhmapedit — petit éditeur de cartes NetHack en mode terminal.

Usage : python3 nhmapedit.py [fichier.lua] [--new LARGEURxHAUTEUR]

Appuyez sur « ? » dans l'éditeur pour l'aide.
"""

import copy
import curses
import glob
import json
import locale
import os
import random
import re
import shlex
import shutil
import subprocess
import sys
import time

import nhdungeon
import nhlevel
import nhtheme
from nhlevel import Entity, Level

HERE = os.path.dirname(os.path.abspath(__file__))

# Répertoires de données du jeu essayés pour la touche « t » (tester)
HACKDIRS = [
    os.environ.get("NHMAPEDIT_HACKDIR", ""),
    os.path.expanduser("~/nh/install/games/lib/nethackdir"),
    os.path.join(HERE, "..", "NetHack-5.0.0", "playground"),
]
# Fichiers dungeon.lua essayés pour « placer le niveau dans le donjon »
DUNGEON_FILES = [
    os.environ.get("NHMAPEDIT_DUNGEON", ""),
    os.path.join(HERE, "..", "NetHack-5.0.0", "dat", "dungeon.lua"),
]
# Préfixe des copies de test, pour ne jamais masquer un niveau de nhdat
TEST_PREFIX = "nhme-"
# Session tmux du jeu lancé par l'éditeur (hors de tmux)
GAME_SESSION = "nhmapedit-jeu"
# Options ajoutées au .nethackrc : ni introduction ni question du
# tutoriel, pour que #wizloaddes arrive au jeu
GAME_OPTIONS = "!legacy,!tutorial"

# Outils : identifiant, nom, nom court (palette), touche
TOOLS = [
    ("pen", "Pinceau", "Pinceau", "1"),
    ("line", "Ligne", "Ligne", "2"),
    ("rect", "Rectangle", "Rectangle", "3"),
    ("fillrect", "Rectangle plein", "Rect plein", "4"),
    ("room", "Salle", "Salle", "5"),
    ("fill", "Remplissage", "Remplir", "6"),
    ("copy", "Copier zone", "Copier", "7"),
    ("paste", "Coller", "Coller", "8"),
    ("ellipse", "Ellipse", "Ellipse", "9"),
    ("fillellipse", "Ellipse pleine", "Ell. pleine", "0"),
    ("cut", "Couper (déplacer) zone", "Couper", "D"),
    ("scatter", "Semis aléatoire", "Semis", "G"),
    ("replace", "Remplacer du terrain", "Remplacer", "R"),
]
TOOL_NAME = {t: name for t, name, _, _ in TOOLS}
TOOL_KEY = {key: t for t, _, _, key in TOOLS}
TWO_POINT = {"line", "rect", "fillrect", "room", "copy", "cut", "ellipse",
             "fillellipse", "scatter", "replace"}
# outils dont l'aperçu montre la zone sans y dessiner le pinceau
SELECT = {"copy", "cut", "scatter", "replace"}

# Retournements (bits de flip_level() : 1 = haut/bas, 2 = gauche/droite)
FLIP_NAME = {0: "aucun", 1: "vertical", 2: "horizontal",
             3: "horizontal et vertical"}
FLIP_CYCLE = {0: 2, 2: 1, 1: 3, 3: 0}
SYM_NAME = {1: "haut/bas", 2: "gauche/droite", 3: "les deux axes"}

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


# Formulaires d'options des monstres et des objets : (clé Lua, type,
# libellé). Types : bool (1/0), str, int, intr (entier ou "random"),
# buc (liste), mon (nom de monstre ou classe), contents (liste d'objets).
MON_FORM = [
    ("peaceful", "bool", "pacifique"),
    ("asleep", "bool", "endormi"),
    ("female", "bool", "femelle"),
    ("invisible", "bool", "invisible"),
    ("cancelled", "bool", "annulé"),
    ("waiting", "bool", "attend le héros"),
    ("name", "str", "nom"),
    ("appear_as", "str", "apparence (obj:…, mon:…, ter:…)"),
    ("m_lev_adj", "int", "ajustement du niveau"),
    ("inventory", "contents", "inventaire"),
    ("keep_default_invent", "bool", "garde l'inventaire par défaut"),
]
OBJ_FORM = [
    ("buc", "buc", "béni / maudit"),
    ("spe", "intr", "enchantement, charges"),
    ("quantity", "intr", "quantité"),
    ("name", "str", "nom"),
    ("achievement", "bool", "succès (achievement)"),
    ("montype", "mon", "monstre (statue, cadavre…)"),
    ("contents", "contents", "contenu (conteneur, statue)"),
    ("buried", "bool", "enterré"),
    ("locked", "bool", "verrouillé"),
    ("trapped", "bool", "piégé"),
    ("eroded", "int", "érosion"),
    ("greased", "bool", "graissé"),
    ("lit", "bool", "allumé"),
]
BUC = ["random", "blessed", "uncursed", "cursed", "not-cursed",
       "not-uncursed", "not-blessed"]

# Pseudo-couleur des monstres et objets aléatoires
RANDOM = "RANDOM"

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
  D Couper une zone (pour la déplacer : la zone est vidée, entités comprises,
    puis l'outil Coller la repose où l'on veut)
  9 Ellipse   0 Ellipse pleine (un cercle est une ellipse dans un carré)
  G Semis aléatoire : peint au hasard une partie des cases d'une zone,
    selon une densité en % demandée au choix de l'outil
  R Remplacer un terrain par un autre, sur toute la carte ou dans une zone,
    avec une proportion en % (comme des.replace_terrain)
  M  symétrie : aucune, gauche/droite, haut/bas, les deux ; tout ce qui
     peint (pinceau, formes, remplissage, semis, remplacement) est reproduit
     en miroir autour du centre de la carte (axes marqués « * » sur le cadre)
  E  insérer ou supprimer une ligne ou une colonne au curseur (la carte et
     les entités sont décalées)
  Presse-papiers : X miroir gauche/droite   Y miroir haut/bas
                   O rotation d'un quart de tour (sens horaire)
  Les outils à deux points : 1er appui = ancre, 2e appui = tracé. Échap annule.
  d  crayon baissé (peint en se déplaçant)    a  avance automatique
  Un trait (crayon baissé ou glisser à la souris) s'annule en une fois.

ENTITÉS (coordonnées relatives à la carte)
  m  placer une entité (escalier, échelle, autel, monstre, objet, piège,
     porte, gravure)        r  répéter la dernière entité au curseur
     Monstres et objets : un formulaire présente leurs options courantes
     (Entrée modifie : défaut -> oui -> non -> défaut ; Échap termine) ;
     « inventaire » (monstre) et « contenu » (coffre, statue…) ouvrent la
     liste de leurs objets (Entrée/e : modifier, d : supprimer)
  Suppr / Retour arrière / z   supprimer les entités sous le curseur
  i  liste des entités (Entrée: aller, e: modifier, d: supprimer)
  Tab  afficher / masquer les entités
  Monstres et objets aléatoires : sur fond magenta, avec le symbole de leur
  classe (d, !…) ou « ? » quand tout est aléatoire
  Un symbole souligné signale plusieurs entités sur la case (seule la plus
  importante est dessinée ; la barre d'état les liste toutes)
  J  rendu « comme dans le jeu » (murs en traits, sol en points, portes
     et couloirs secrets cachés) ; l'édition reste possible

NIVEAU ET FICHIERS
  p  propriétés (taille, drapeaux, level_init, alignement, éclairage) ;
     « Donjon » y ajoute le niveau à dat/dungeon.lua (profondeur,
     probabilité…), ou modifie et retire les niveaux spéciaux du donjon
  v  vérifier la carte
  t  tester : copie la carte dans le répertoire du jeu, à charger avec
     #wizloaddes en mode wizard (nethack -D) ; avec tmux, l'éditeur
     lance le jeu (panneau, fenêtre ou session tmux) et y charge la carte
     lui-même, puis la recharge à chaque nouvel appui sur t
  u  annuler      U / Ctrl-R  rétablir
  n  nouveau      o  ouvrir      s  enregistrer      w  enregistrer sous
  q  quitter      ?  cette aide

Salles à thème : ouvrir themerms.lua (o) propose ses salles dessinées par
des.map, ou une nouvelle salle ; s n'y réécrit que la carte (ou ajoute la
salle), t explique comment la voir en jeu avec THEMERM.

Pour un fichier existant, seuls la première carte des.map et les éléments
à position fixe qui la suivent (avec leur inventaire ou contenu, s'il ne
contient que des des.object simples) sont édités ; le reste du script Lua
est conservé tel quel à l'enregistrement.
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


def ellipse_cells(lx, ly, hx, hy, filled):
    """Cases de l'ellipse inscrite dans le rectangle (lx, ly)-(hx, hy).

    Le contour garde toute case qui touche l'extérieur, diagonales
    comprises : il n'a pas de trou en diagonale par où se faufiler."""
    cx, cy = (lx + hx) / 2, (ly + hy) / 2
    rx, ry = (hx - lx) / 2 + 0.5, (hy - ly) / 2 + 0.5
    inside = {(x, y) for y in range(ly, hy + 1) for x in range(lx, hx + 1)
              if ((x - cx) / rx) ** 2 + ((y - cy) / ry) ** 2 <= 1}
    if filled:
        return inside
    return {(x, y) for x, y in inside
            if any((x + dx, y + dy) not in inside
                   for dx in (-1, 0, 1) for dy in (-1, 0, 1))}


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
        self.sym = 0                # symétrie de dessin (mêmes bits)
        enc = locale.getpreferredencoding(False).lower().replace("-", "")
        self.unicode = enc == "utf8"
        self.clip = None
        self.density = 30           # densité de l'outil Semis, en %
        self.replace = None         # (ancien, nouveau, %) de l'outil Remplacer
        self.template = None        # dernière entité placée
        self.hackdir = next((d for d in HACKDIRS if self.is_hackdir(d)),
                            None)
        self.game_pane = None       # panneau tmux du jeu lancé par « t »
        self.dungeon_path = next((f for f in DUNGEON_FILES
                                  if f and os.path.isfile(f)), "")
        self.game_where = ""
        self.launch = None          # réponse à « lancer le jeu ? »
        self.undo_stack, self.redo_stack = [], []
        # trait en cours (crayon baissé ou glisser à la souris) : un seul
        # point d'annulation pour tout le trait
        self.stroke = self.stroke_saved = False
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
        # style commun des monstres et objets aléatoires : fond magenta
        curses.init_pair(9, curses.COLOR_WHITE, curses.COLOR_MAGENTA)
        self.pairs[RANDOM] = curses.color_pair(9)

    def attr(self, clr):
        if clr == RANDOM:
            return self.pairs.get(RANDOM, curses.A_DIM) | curses.A_BOLD
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
        if k in ("monster", "object"):
            data = self.mon if k == "monster" else self.obj
            if v in data:
                sym = data[v]["sym"]
                return sym, (data[v]["color"] if k == "monster"
                             else OBJ_CLASS_COLOR.get(sym, "CLR_GRAY"))
            # aléatoire : symbole de la classe, ou « ? » si tout est
            # aléatoire, sur fond magenta
            if not v or len(v) == 1:
                return v or "?", RANDOM
            return "?", "CLR_WHITE"     # nom absent de nhdata.json
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
        if self.tool in ("copy", "cut"):
            return cells
        return self.mirrored(cells)

    def shape_cells(self, a, b):
        (x0, y0), (x1, y1) = a, b
        lx, hx = sorted((x0, x1))
        ly, hy = sorted((y0, y1))
        t, br = self.tool, self.brush
        cells = {}
        if t == "line":
            for x, y in bresenham(x0, y0, x1, y1):
                cells[(x, y)] = br
        elif t in ("rect", "copy", "cut"):
            for x in range(lx, hx + 1):
                cells[(x, ly)] = cells[(x, hy)] = br
            for y in range(ly, hy + 1):
                cells[(lx, y)] = cells[(hx, y)] = br
        elif t == "fillrect":
            for y in range(ly, hy + 1):
                for x in range(lx, hx + 1):
                    cells[(x, y)] = br
        elif t in ("ellipse", "fillellipse"):
            for p in ellipse_cells(lx, ly, hx, hy, t == "fillellipse"):
                cells[p] = br
        elif t == "scatter":
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
        if lvl.theme:
            name += " : salle « %s »" % lvl.theme["name"]
        head = " nhmapedit — %s%s   %dx%d" % (
            name, " [modifié]" if self.modified else "", lvl.w, lvl.h)
        if lvl.w > nhlevel.MAP_X_LIM:
            head += "  (largeur > %d !)" % nhlevel.MAP_X_LIM
        if lvl.allowed_flips() and not lvl.theme:
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
        # axes de symétrie (au centre de la carte, donc au même endroit
        # dans l'aperçu retourné)
        axis = self.attr("CLR_YELLOW")
        if self.sym & 2:
            for x in {(lvl.w - 1) // 2, lvl.w // 2}:
                if 0 <= x - self.ox < vw:
                    for yy in (top, top + vh + 1):
                        self.put(yy, left + 1 + x - self.ox, "*", axis)
        if self.sym & 1:
            for y in {(lvl.h - 1) // 2, lvl.h // 2}:
                if 0 <= y - self.oy < vh:
                    for xx in (left, left + vw + 1):
                        self.put(top + 1 + y - self.oy, xx, "*", axis)
        # carte
        prev = self.preview_cells()
        index = lvl.entity_index()
        # entités du presse-papiers montrées dans l'aperçu de Coller
        prev_ents = {}
        if self.tool == "paste" and self.clip:
            for e in self.clip[1]:
                prev_ents[(self.cx + e.x, self.cy + e.y)] = e
        if self.game:
            grid = [row[:] for row in lvl.grid]
            if self.tool not in SELECT:
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
                    if self.tool not in SELECT and not self.game:
                        ch = prev[(x, y)]
                        a = self.attr(TERRAIN_COLOR.get(ch, "CLR_GRAY"))
                    if (x, y) in prev_ents and self.show_ents:
                        ch, clr = self.entity_glyph(prev_ents[(x, y)])
                        a = self.attr(clr)
                    a |= curses.A_REVERSE
                elif self.show_ents:
                    e = self.top_entity(x, y, index)
                    if e:
                        ch, clr = self.entity_glyph(e)
                        a = self.attr(clr)
                        # plusieurs entités sur la case : symbole souligné
                        if len(index[(x, y)]) > 1:
                            a |= curses.A_UNDERLINE
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
        rows = (len(TOOLS) + 1) // 2
        for i, (t, _, short, key) in enumerate(TOOLS):
            a = curses.A_REVERSE if t == self.tool else 0
            self.put(y + 1 + i % rows, x + i // rows * 13,
                     "%s %s" % (key, short), a)
        y += rows + 2
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
        if self.sym:
            st += "   [symétrie : %s]" % SYM_NAME[self.sym]
        self.put(maxy - 3, 0, st[:maxx - 1], curses.A_BOLD)
        self.put(maxy - 2, 0, self.msg[:maxx - 1], self.attr("CLR_YELLOW"))
        hint = (" ?:aide  1-0 D G R:outils  m:entité  i:liste  p:propriétés  "
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
    def checkpoint(self, snap=None):
        """Point d'annulation ; snap : état pris avant la modification."""
        self.undo_stack.append(snap or self.lvl.snapshot())
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

    def begin_stroke(self):
        self.stroke, self.stroke_saved = True, False

    def end_stroke(self):
        self.stroke = False

    def mirror_points(self, x, y):
        """La case et ses reflets selon le mode symétrie."""
        pts = {(x, y)}
        if self.sym & 2:
            pts |= {(self.lvl.w - 1 - px, py) for px, py in pts}
        if self.sym & 1:
            pts |= {(px, self.lvl.h - 1 - py) for px, py in pts}
        return pts

    def mirrored(self, cells):
        """Ajoute aux cases à peindre leurs reflets (mode symétrie)."""
        if not self.sym:
            return cells
        out = {}
        for (x, y), c in cells.items():
            for p in self.mirror_points(x, y):
                out[p] = c
        return out

    def paint(self, cells, sym=True):
        if sym:
            cells = self.mirrored(cells)
        if any(self.lvl.grid[y][x] != c for (x, y), c in cells.items()
               if 0 <= x < self.lvl.w and 0 <= y < self.lvl.h):
            if not (self.stroke and self.stroke_saved):
                self.checkpoint()
                self.stroke_saved = self.stroke
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
            if t == "scatter":
                cells = self.shape_cells(a, b)
                pick = {p: c for p, c in cells.items()
                        if random.random() * 100 < self.density}
                self.paint(pick)
                self.msg = "Semis : %d cases sur %d (%d %%)." % (
                    len(pick), len(cells), self.density)
            elif t == "replace":
                self.replace_terrain(a, b)
            elif t in SELECT:
                self.copy(a, b, cut=t == "cut")
            else:
                self.paint(self.shape_cells(a, b))
                self.msg = "%s tracé." % TOOL_NAME[t]

    def flood_fill(self, x, y, c):
        old = self.lvl.grid[y][x]
        if old == c:
            return
        self.checkpoint()
        # en symétrie, on remplit aussi depuis les reflets du point de départ
        stack = [p for p in self.mirror_points(x, y)
                 if self.lvl.grid[p[1]][p[0]] == old]
        n = 0
        while stack:
            x, y = stack.pop()
            if (0 <= x < self.lvl.w and 0 <= y < self.lvl.h
                    and self.lvl.grid[y][x] == old):
                self.lvl.grid[y][x] = c
                n += 1
                stack += [(x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)]
        self.msg = "%d cases remplies." % n

    def ask_replace(self):
        """Demande les paramètres du remplacement. Renvoie True s'il faut
        tracer une zone, False s'il a été fait sur toute la carte."""
        items = [("%s  %s" % ("e" if c == " " else c, d), c)
                 for c, d in nhlevel.TERRAIN if c != "x"]
        old = self.pick("Remplacer quel terrain ?", items,
                        self.lvl.grid[self.cy][self.cx])
        new = self.pick("Remplacer « %s » par :" % nhlevel.TERRAIN_DESC[old],
                        items, self.brush)
        s = self.prompt("Proportion des cases à remplacer en %% (1-100) : ",
                        "100")
        try:
            pct = max(1, min(100, int(s)))
        except ValueError:
            raise Cancel()
        self.replace = (old, new, pct)
        where = self.pick("Où remplacer ?", [
            ("sur toute la carte", "map"),
            ("dans une zone (à tracer avec l'ancre)", "zone")])
        if where == "map":
            self.replace_terrain((0, 0), (self.lvl.w - 1, self.lvl.h - 1))
            return False
        return True

    def replace_terrain(self, a, b):
        old, new, pct = self.replace
        lx, hx = sorted((a[0], b[0]))
        ly, hy = sorted((a[1], b[1]))
        zone = set()
        for y in range(ly, hy + 1):
            for x in range(lx, hx + 1):
                zone |= self.mirror_points(x, y)
        # les reflets ne sont modifiés que s'ils contiennent l'ancien
        # terrain : pas de symétrie automatique dans paint()
        cells = {(x, y): new for x, y in zone
                 if self.lvl.grid[y][x] == old
                 and random.random() * 100 < pct}
        self.paint(cells, sym=False)
        self.msg = "%d case(s) « %s » remplacée(s) par « %s »." % (
            len(cells), nhlevel.TERRAIN_DESC[old], nhlevel.TERRAIN_DESC[new])

    def edit_rows_cols(self):
        """Menu : insérer ou supprimer une ligne ou une colonne."""
        lvl = self.lvl
        what = self.pick("Lignes et colonnes (curseur en %d,%d)"
                         % (self.cx, self.cy), [
                             ("insérer une ligne au-dessus", "row-above"),
                             ("insérer une ligne en dessous", "row-below"),
                             ("supprimer la ligne", "row-del"),
                             ("insérer une colonne à gauche", "col-left"),
                             ("insérer une colonne à droite", "col-right"),
                             ("supprimer la colonne", "col-del")])
        # « au-dessus » et « à gauche » s'entendent à l'écran, même dans
        # l'aperçu retourné
        if self.flip & 1:
            what = {"row-above": "row-below",
                    "row-below": "row-above"}.get(what, what)
        if self.flip & 2:
            what = {"col-left": "col-right",
                    "col-right": "col-left"}.get(what, what)
        fill = lvl.init.get("fg", " ")
        if fill not in nhlevel.TERRAIN_CHARS or fill == "x":
            fill = " "
        snap = lvl.snapshot()
        n = len(lvl.entities)
        if what == "row-above":
            ok = lvl.insert_row(self.cy, fill)
        elif what == "row-below":
            ok = lvl.insert_row(self.cy + 1, fill)
            self.cy += ok
        elif what == "row-del":
            ok = lvl.delete_row(self.cy)
        elif what == "col-left":
            ok = lvl.insert_col(self.cx, fill)
        elif what == "col-right":
            ok = lvl.insert_col(self.cx + 1, fill)
            self.cx += ok
        else:
            ok = lvl.delete_col(self.cx)
        if not ok:
            self.msg = ("Taille maximale atteinte (%dx%d)."
                        % (nhlevel.MAX_W, nhlevel.MAX_H)
                        if "del" not in what else
                        "Impossible : la carte n'a plus qu'une ligne "
                        "ou colonne.")
            return
        self.checkpoint(snap)
        self.clamp_cursor()
        self.msg = "Carte maintenant en %dx%d%s." % (
            lvl.w, lvl.h, "" if len(lvl.entities) == n else
            " (%d entité(s) supprimée(s))" % (n - len(lvl.entities)))

    def copy(self, a, b, cut=False):
        """Copie la zone (terrain et entités) dans le presse-papiers.

        Avec cut=True, la zone est vidée : son terrain devient celui de
        remplissage du niveau et ses entités sont retirées."""
        lx, hx = sorted((a[0], b[0]))
        ly, hy = sorted((a[1], b[1]))
        g = [self.lvl.grid[y][lx:hx + 1] for y in range(ly, hy + 1)]
        inside = [e for e in self.lvl.entities
                  if lx <= e.x <= hx and ly <= e.y <= hy]
        ents = []
        for e in inside:
            c = e.copy()
            c.origin = None
            c.x -= lx
            c.y -= ly
            ents.append(c)
        self.clip = ([r[:] for r in g], ents)
        if cut:
            self.checkpoint()
            fill = self.lvl.init.get("fg", " ")
            if fill not in nhlevel.TERRAIN_CHARS or fill == "x":
                fill = " "
            for y in range(ly, hy + 1):
                for x in range(lx, hx + 1):
                    self.lvl.set(x, y, fill)
            self.lvl.entities = [e for e in self.lvl.entities
                                 if e not in inside]
        self.tool = "paste"
        self.msg = ("Zone %dx%d %s (%d entités). Outil Coller actif."
                    % (hx - lx + 1, hy - ly + 1,
                       "coupée" if cut else "copiée", len(ents)))

    def transform_clip(self, how):
        """Miroir (« x » : gauche/droite, « y » : haut/bas) ou rotation
        d'un quart de tour dans le sens horaire (« rot ») du
        presse-papiers, entités comprises."""
        if not self.clip:
            self.msg = "Presse-papiers vide (outil 7 ou D pour en remplir un)."
            return
        g, ents = self.clip
        h, w = len(g), len(g[0])
        if how == "x":
            g = [row[::-1] for row in g]
            pos = lambda x, y: (w - 1 - x, y)
        elif how == "y":
            g = g[::-1]
            pos = lambda x, y: (x, h - 1 - y)
        else:
            swap = {"-": "|", "|": "-"}
            g = [[swap.get(g[h - 1 - y][x], g[h - 1 - y][x])
                  for y in range(h)] for x in range(w)]
            # les coins et jonctions des cartes NetHack s'écrivent « - »
            for row in g:
                for x, c in enumerate(row):
                    side = (row[x - 1] if x else " ") + (
                        row[x + 1] if x + 1 < h else " ")
                    if c == "|" and any(n in side for n in "-+S"):
                        row[x] = "-"
            pos = lambda x, y: (h - 1 - y, x)
        for e in ents:
            e.x, e.y = pos(e.x, e.y)
        self.clip = (g, ents)
        self.tool = "paste"
        self.msg = "Presse-papiers %s (%dx%d). Outil Coller actif." % (
            {"x": "retourné gauche/droite", "y": "retourné haut/bas",
             "rot": "tourné d'un quart de tour"}[how], len(g[0]), len(g))

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
            if not self.stroke:
                self.begin_stroke()
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

    def edit_options(self, kind, extra):
        """Formulaire des options courantes d'un monstre ou d'un objet."""
        return self.form("Options %s" % ("du monstre" if kind == "monster"
                                         else "de l'objet"),
                         MON_FORM if kind == "monster" else OBJ_FORM, extra)

    def form(self, title, form, extra, free=True):
        """Formulaire : form = [(clé, type, libellé)], extra = valeurs.

        Entrée modifie la ligne choisie (les booléens passent de « défaut »
        à oui, non, puis défaut) ; Échap ou « Terminer » valide. Avec
        free, les autres options se saisissent librement sur la dernière
        ligne. Types : voir MON_FORM, plus ("choice", valeurs) et
        ("flags", valeurs) pour une liste à cocher."""
        keys = [k for k, _, _ in form]
        extra = dict(extra)
        sel = "_done"
        while True:
            items = [("Terminer", "_done")]
            for key, typ, label in form:
                if key not in extra:
                    shown = "(défaut)"
                elif typ == "bool":
                    shown = "oui" if extra[key] else "non"
                elif typ == "contents":
                    c = extra[key]
                    shown = c.summary() + " " + ", ".join(
                        it.value or "aléatoire" for it in c.items)
                elif isinstance(extra[key], list):
                    shown = ", ".join(map(str, extra[key]))
                else:
                    shown = nhlevel.lua_value(extra[key])
                items.append(("%-34s %s" % ("%s (%s)" % (label, key), shown),
                              key))
            rest = {k: v for k, v in extra.items() if k not in keys}
            if free:
                items.append(("Autres options : %s" % (", ".join(
                    "%s=%s" % (k, nhlevel.lua_value(v))
                    for k, v in rest.items()) or "(aucune)"), "_other"))
            try:
                sel = self.pick("%s (Entrée: modifier, Échap: terminer)"
                                % title, items, sel)
            except Cancel:
                return extra
            if sel == "_done":
                return extra
            try:
                if sel == "_other":
                    new = self.ask_extra(rest)
                    extra = {k: v for k, v in extra.items() if k in keys}
                    extra.update(new)
                    continue
                typ = dict((k, t) for k, t, _ in form)[sel]
                if typ == "bool":
                    # défaut -> oui -> non -> défaut
                    if sel not in extra:
                        extra[sel] = 1
                    elif extra[sel]:
                        extra[sel] = 0
                    else:
                        del extra[sel]
                elif typ == "buc" or typ[0] == "choice":
                    values = BUC if typ == "buc" else typ[1]
                    v = self.pick(sel, [("(défaut)", None)] +
                                  [(b, b) for b in values], extra.get(sel))
                    self.set_option(extra, sel, v)
                elif typ[0] == "flags":
                    v = self.check_list(sel, typ[1], extra.get(sel) or [])
                    self.set_option(extra, sel, v or None)
                elif typ == "contents":
                    v = self.edit_contents(extra.get(sel), "%s (%s)" % (
                        dict((k, l) for k, _, l in form)[sel].capitalize(),
                        sel))
                    self.set_option(extra, sel, v)
                elif typ == "mon":
                    items = [("(défaut)", None)] + [
                        ("%s  %s" % (m["sym"], m["name"]), m["name"])
                        for m in self.data["monsters"]]
                    v = self.pick("Monstre (tapez pour filtrer ; une lettre "
                                  "seule = classe)", items, extra.get(sel),
                                  custom=True)
                    self.set_option(extra, sel, v)
                else:
                    self.ask_option(extra, sel, typ)
            except Cancel:
                pass

    def check_list(self, title, values, checked):
        """Liste à cocher (Entrée coche ou décoche, Échap termine)."""
        checked = list(checked)
        sel = values[0]
        while True:
            items = [("[%s] %s" % ("x" if v in checked else " ", v), v)
                     for v in values]
            try:
                sel = self.pick("%s (Entrée: cocher/décocher, Échap: "
                                "terminer)" % title, items, sel)
            except Cancel:
                return [v for v in values if v in checked]
            if sel in checked:
                checked.remove(sel)
            else:
                checked.append(sel)

    def edit_contents(self, cont, title):
        """Liste des objets d'un contenu ou d'un inventaire.

        Renvoie un nouveau Contents, ou None pour retirer l'option."""
        existed = cont is not None
        cont = copy.deepcopy(cont) if existed else nhlevel.Contents()
        sel = 0
        while True:
            items = [("%s %s" % (self.entity_glyph(it)[0], it.describe()), i)
                     for i, it in enumerate(cont.items)]
            items.append(("+ ajouter un objet", "add"))
            if existed:
                items.append(("- retirer l'option", "remove"))
            hint = "Entrée/e: modifier  d: supprimer  Échap: terminer"
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

    @staticmethod
    def set_option(extra, key, v):
        if v is None:
            extra.pop(key, None)
        else:
            extra[key] = v

    def ask_option(self, extra, key, typ):
        """Saisie d'une option texte ou entière ; vide = valeur par défaut."""
        cur = extra.get(key)
        txt = "" if cur is None else str(cur)
        hint = {"str": "texte", "int": "entier",
                "intr": "entier ou random"}[typ]
        while True:
            s = self.prompt("%s (%s, vide = défaut) : " % (key, hint),
                            txt).strip()
            if not s:
                extra.pop(key, None)
                return
            if typ == "str":
                extra[key] = s
                return
            if typ == "intr" and s == "random":
                extra[key] = s
                return
            try:
                extra[key] = int(s)
                return
            except ValueError:
                txt = s
                self.msg = "Valeur invalide : %s attendu." % hint

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
            extra = self.edit_options(kind, extra)
        elif kind == "object":
            items = [("(aléatoire)", None)] + [
                ("%s  %s" % (o["sym"], o["name"]), o["name"])
                for o in self.data["objects"]]
            value = self.pick("Objet (tapez pour filtrer ; un symbole "
                              "seul = classe)", items, value, custom=True)
            extra = self.edit_options(kind, extra)
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
        if self.no_entities():
            return
        kinds = [("%s" % nhlevel.ENTITY_LABEL[k].capitalize(), k)
                 for k in nhlevel.ENTITY_KINDS]
        kind = self.pick("Placer une entité en (%d,%d)" % (self.cx, self.cy),
                         kinds)
        value, extra = self.edit_entity_fields(kind)
        self.add_entity(Entity(kind, self.cx, self.cy, value, extra))

    def no_entities(self):
        """Une salle à thème n'enregistre que sa carte."""
        if self.lvl.theme:
            self.msg = ("Salle à thème : seule la carte est enregistrée, "
                        "pas les entités.")
            return True
        return False

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

    # ------------------------------------------------------------------
    # Donjon (dungeon.lua)
    # ------------------------------------------------------------------
    def edit_dungeon(self):
        """Ajoute, modifie ou supprime un niveau spécial de dungeon.lua."""
        path = self.prompt("Fichier dungeon.lua (dans dat/ des sources) : ",
                           self.dungeon_path, self.path_completer)
        path = os.path.expanduser(path.strip())
        try:
            with open(path, encoding="utf-8") as f:
                df = nhdungeon.DungeonFile(f.read())
        except (OSError, ValueError) as e:
            self.msg = "%s : %s" % (path, e)
            return
        self.dungeon_path = path
        di = 0
        while True:
            items = [("%-24s %d niveau(x) spécial(aux)" % (
                df.dungeon_name(d), len(df.levels(d))), i)
                for i, d in enumerate(df.dungeons())]
            try:
                di = self.pick("Donjons de %s (%d niveaux spéciaux sur %d)"
                               % (os.path.basename(path),
                                  len(df.all_level_names()),
                                  nhdungeon.LEV_LIMIT), items, di)
            except Cancel:
                return
            df = self.dungeon_levels(df, di)

    def dungeon_levels(self, df, di):
        """Liste des niveaux spéciaux d'un donjon. Renvoie le fichier
        tel qu'il est après les modifications (déjà enregistrées)."""
        sel = 0
        while True:
            d = df.dungeons()[di]
            levels = [l.py() for l in df.levels(d)]
            items = [("%-10s %s" % (l.get("name"), " ".join(
                "%s=%s" % (k, v if not isinstance(v, (list, str)) or
                           k == "name" else nhlevel.lua_value(v))
                for k, v in l.items() if k != "name")), i)
                for i, l in enumerate(levels)]
            items.append(("+ ajouter ce niveau", "add"))
            hint = "Entrée/e: modifier  d: supprimer  Échap: retour"
            try:
                i, action = self.pick_action(df.dungeon_name(d), items, sel,
                                             hint)
            except Cancel:
                return df
            try:
                if i == "add":
                    base = os.path.splitext(os.path.basename(
                        self.path or "niveau"))[0]
                    fields = self.dungeon_form(df, di, None, {"name": base})
                    if fields:
                        df = self.write_dungeon(df.add_level(di, fields))
                        sel = len(levels)
                        if df:
                            self.after_dungeon_add(df, di, fields)
                elif action == "delete":
                    if self.confirm("Retirer %s du donjon ?"
                                    % levels[i].get("name")):
                        df = self.write_dungeon(df.delete_level(di, i))
                        sel = max(0, i - 1)
                else:
                    fields = self.dungeon_form(df, di, i, levels[i])
                    if fields:
                        df = self.write_dungeon(df.replace_level(di, i,
                                                                 fields))
                        sel = i
            except Cancel:
                pass
            if df is None:          # erreur d'écriture
                return self.reload_dungeon()

    def reload_dungeon(self):
        with open(self.dungeon_path, encoding="utf-8") as f:
            return nhdungeon.DungeonFile(f.read())

    def dungeon_form(self, df, di, li, fields):
        """Formulaire d'un niveau du donjon ; None si abandon."""
        fields = dict(fields)
        if isinstance(fields.get("flags"), str):
            fields["flags"] = [fields["flags"]]
        form = [
            ("name", "str", "nom du fichier, sans .lua"),
            ("base", "int", "profondeur (négatif : depuis le bas)"),
            ("range", "int", "profondeur : tirage en plus"),
            ("chance", "int", "probabilité de présence, en %"),
            ("nlevels", "int", "variantes (nom-1.lua … nom-N.lua)"),
            ("alignment", ("choice", nhdungeon.ALIGNMENTS), "alignement"),
            ("flags", ("flags", nhdungeon.LEVEL_FLAGS), "drapeaux"),
            ("bonetag", "str", "lettre des fichiers bones"),
            ("chainlevel", ("choice", df.names_before(di, li)),
             "base comptée depuis ce niveau"),
        ]
        while True:
            fields = self.form("Niveau du donjon", form, fields, free=False)
            errs = nhdungeon.check_level(df, fields, di, li)
            if not errs:
                return fields
            if not self.confirm("%s. Corriger ?" % " ; ".join(errs)
                                .capitalize()):
                return None

    def write_dungeon(self, df):
        """Enregistre dungeon.lua (l'original est gardé sous ~)."""
        path = self.dungeon_path
        try:
            if not os.path.exists(path + "~"):
                shutil.copy2(path, path + "~")
            with open(path, "w", encoding="utf-8") as f:
                f.write(df.text)
        except OSError as e:
            self.msg = "Erreur d'écriture : %s" % e
            return None
        self.msg = "Enregistré : %s" % path
        return df

    def after_dungeon_add(self, df, di, fields):
        """Propose de copier la carte dans le répertoire du jeu, puis
        rappelle les étapes pour jouer le niveau."""
        name = fields["name"]
        if fields.get("nlevels"):
            name += "-1"
        dest = None
        if self.hackdir and self.confirm(
                "Copier la carte dans %s/%s.lua ?" % (self.hackdir, name)):
            dest = os.path.join(self.hackdir, name + ".lua")
            try:
                if not os.path.exists(dest) or self.confirm(
                        "%s existe. Écraser ?" % dest):
                    with open(dest, "w", encoding="utf-8") as f:
                        f.write(self.lvl.to_lua(name))
                else:
                    dest = None
            except OSError as e:
                self.msg = "Erreur d'écriture : %s" % e
                dest = None
        self.message_box("Niveau ajouté au donjon", "\n".join([
            "%s ajouté à « %s » dans :" % (fields["name"],
                                           df.dungeon_name(
                                               df.dungeons()[di])),
            "  " + self.dungeon_path,
            "",
            "Pour le jouer :",
            ("  1. la carte est copiée dans " + dest) if dest else
            "  1. copiez la carte sous %s.lua dans le répertoire du jeu"
            % name,
            "     (le jeu la lit là, puisqu'elle n'est pas dans nhdat) ;",
            "  2. dans les sources, « make install » range le nouveau",
            "     dungeon.lua dans nhdat ;",
            "  3. commencez une nouvelle partie (les parties en cours",
            "     gardent l'ancien donjon). En mode wizard, #wizwhere",
            "     donne la profondeur des niveaux spéciaux et Ctrl-V",
            "     téléporte de niveau.",
        ] + (["", "Avec nlevels, il faut un fichier par variante :",
              "%s-1.lua … %s-%d.lua." % (fields["name"], fields["name"],
                                          fields["nlevels"])]
             if fields.get("nlevels") else [])))

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
        return self.set_level(lvl, path)

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
            if not path.endswith(".lua"):
                path += ".lua"
            if path != self.path and os.path.exists(path):
                if not self.confirm("%s existe. Écraser ?" % path):
                    raise Cancel()
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
        self.path = path
        self.lvl.theme = None       # « enregistrer sous » : niveau à part
        self.modified = False
        self.msg = "Enregistré : %s" % path
        return True

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

    @staticmethod
    def is_hackdir(d):
        return bool(d) and any(os.path.isfile(os.path.join(d, f))
                               for f in ("nhdat", "sysconf"))

    def test_in_game(self):
        """Copie l'état courant de la carte dans le répertoire du jeu."""
        if self.lvl.theme:
            return self.test_theme()
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
        if self.game_alive():
            self.load_in_game(name)
            return
        if shutil.which("tmux") and self.launch is None:
            self.launch = self.confirm(
                "Lancer NetHack (mode wizard) et y charger la carte ?")
        if self.launch and shutil.which("tmux"):
            if self.start_game():
                self.load_in_game(name)
                return
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
            "",
            "Avec tmux installé, l'éditeur peut lancer le jeu et",
            "charger la carte lui-même.",
        ]))

    # ------------------------------------------------------------------
    # Jeu lancé dans tmux
    # ------------------------------------------------------------------
    @staticmethod
    def tmux(*args):
        try:
            r = subprocess.run(["tmux"] + list(args), capture_output=True,
                               text=True, timeout=5)
        except (OSError, subprocess.SubprocessError):
            return None
        return r.stdout.strip() if r.returncode == 0 else None

    def game_alive(self):
        """Le panneau du jeu existe-t-il encore ? (il se ferme avec le jeu)"""
        if not self.game_pane:
            return False
        cmd = self.tmux("display-message", "-p", "-t", self.game_pane,
                        "#{pane_current_command}")
        if cmd is None:
            self.game_pane = None
        return bool(cmd)

    def test_theme(self):
        """Une salle à thème se teste avec THEMERM, une fois themerms.lua
        rangé dans nhdat (le jeu lit nhdat avant les fichiers à part)."""
        name = self.lvl.theme["name"]
        self.message_box("Tester une salle à thème", "\n".join([
            "themerms.lua est rangé dans nhdat : le jeu ne lit pas une",
            "copie posée à côté. Pour voir la salle « %s » :" % name,
            "",
            "  1. enregistrez (s) : la carte est écrite dans",
            "     " + self.lvl.theme["path"] + " ;",
            "  2. dans les sources, lancez « make install » ;",
            "  3. lancez le jeu en mode wizard avec la variable THEMERM :",
            "     THEMERM=%s nethack -D" % shlex.quote(name),
            "",
            "Chaque salle des niveaux ordinaires est alors cette salle,",
            "quand elle y tient. Ctrl-F révèle la carte, Ctrl-V change de",
            "niveau pour en générer d'autres.",
        ]))
        if not (self.hackdir and shutil.which("tmux")):
            return
        if self.game_alive():
            self.msg = ("Une partie lancée par l'éditeur est en cours : "
                        "quittez-la pour relancer avec THEMERM.")
            return
        if self.confirm("Lancer NetHack avec THEMERM=%s (après make "
                        "install) ?" % name):
            if self.start_game({"THEMERM": name}):
                self.msg = "NetHack lancé avec THEMERM=%s (%s)." % (
                    name, self.game_where)

    def game_command(self, env=None):
        d = self.hackdir
        opts = os.environ.get("NETHACKOPTIONS", "")
        # une valeur qui désigne un fichier remplace le .nethackrc : on
        # n'y touche pas
        if not opts.startswith(("/", "@")):
            opts = opts + "," + GAME_OPTIONS if opts else GAME_OPTIONS
        # -D : mode wizard ; -@ : personnage tiré au hasard, sans question
        extra = "".join("%s=%s " % (k, shlex.quote(v))
                        for k, v in (env or {}).items())
        return "cd %s && %sHACKDIR=%s NETHACKOPTIONS=%s %s -D -@" % (
            shlex.quote(d), extra, shlex.quote(d), shlex.quote(opts),
            shlex.quote(os.path.join(d, "nethack")))

    def start_game(self, env=None):
        """Lance NetHack dans tmux : un panneau ou une fenêtre de la
        session courante, sinon une session à part ouverte dans un
        nouveau terminal. Renvoie True si le jeu est prêt."""
        if not os.access(os.path.join(self.hackdir, "nethack"), os.X_OK):
            self.msg = "Pas d'exécutable nethack dans %s." % self.hackdir
            return False
        try:
            busy = subprocess.run(["pgrep", "-x", "nethack"],
                                  capture_output=True).returncode == 0
        except OSError:
            busy = False
        if busy:
            # même verrou de partie : un second jeu ne démarrerait pas
            self.msg = "Une partie de NetHack est déjà en cours."
            return False
        cmd = self.game_command(env)
        attach = None
        if os.environ.get("TMUX"):
            here = os.environ.get("TMUX_PANE", "")
            width = int(self.tmux("display-message", "-p", "-t", here,
                                  "#{window_width}") or 0)
            # assez large : panneau à droite (80 colonnes pour le jeu),
            # sinon une fenêtre tmux à part
            if width >= 170:
                pane = self.tmux("split-window", "-h", "-d", "-t", here,
                                 "-P", "-F", "#{pane_id}", cmd)
                where = "panneau tmux à droite"
            else:
                pane = self.tmux("new-window", "-d", "-n", "nethack", "-P",
                                 "-F", "#{pane_id}", cmd)
                where = "fenêtre tmux « nethack »"
        else:
            self.tmux("kill-session", "-t", GAME_SESSION)
            pane = self.tmux("new-session", "-d", "-s", GAME_SESSION,
                             "-x", "100", "-y", "32", "-P", "-F",
                             "#{pane_id}", cmd)
            attach = "tmux attach -t " + GAME_SESSION
            where = "session tmux « %s »" % GAME_SESSION
            term = (os.environ.get("TERMINAL")
                    or shutil.which("x-terminal-emulator"))
            if pane and os.environ.get("DISPLAY") and term:
                try:
                    subprocess.Popen([term, "-e", "tmux", "attach", "-t",
                                      GAME_SESSION],
                                     stdin=subprocess.DEVNULL,
                                     stdout=subprocess.DEVNULL,
                                     stderr=subprocess.DEVNULL,
                                     start_new_session=True)
                    attach = None
                except OSError:
                    pass
        if not pane:
            self.msg = "Impossible de lancer le jeu dans tmux."
            return False
        self.game_pane = pane
        self.game_where = where
        self.msg = "Lancement de NetHack…"
        self.draw()
        # attend que l'écran du jeu ne bouge plus
        last, stable, end = None, 0, time.time() + 15
        while time.time() < end and stable < 3:
            time.sleep(0.4)
            screen = self.tmux("capture-pane", "-p", "-t", pane)
            if screen is None:
                self.game_pane = None
                self.msg = "Le jeu s'est arrêté au démarrage."
                return False
            stable = stable + 1 if screen.strip() and screen == last else 0
            last = screen
        if attach:
            self.message_box("NetHack lancé", "\n".join([
                "Le jeu tourne dans la session tmux « %s »." % GAME_SESSION,
                "Pour le voir, dans un autre terminal :",
                "  " + attach,
            ]))
        return True

    def load_in_game(self, name):
        """Envoie #wizloaddes au jeu ; Échap ferme d'abord un éventuel
        message ou menu en attente."""
        p = self.game_pane
        self.tmux("send-keys", "-t", p, "Escape")
        time.sleep(0.3)
        self.tmux("send-keys", "-t", p, "-l", "#")
        time.sleep(0.2)
        self.tmux("send-keys", "-t", p, "-l", "wizloaddes")
        self.tmux("send-keys", "-t", p, "Enter")
        time.sleep(0.3)
        self.tmux("send-keys", "-t", p, "-l", name)
        self.tmux("send-keys", "-t", p, "Enter")
        self.msg = ("Carte chargée dans NetHack (%s, %s) ; t la recharge "
                    "après une modification." % (name, self.game_where))

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
        if k not in moves and k not in (curses.KEY_HOME, curses.KEY_END,
                                         curses.KEY_MOUSE,
                                         curses.KEY_RESIZE):
            self.end_stroke()       # toute autre touche termine le trait
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
        elif k in TOOL_KEY:
            if TOOL_KEY[k] == "scatter":
                s = self.prompt("Densité du semis en %% (1-100) : ",
                                str(self.density))
                try:
                    self.density = max(1, min(100, int(s)))
                except ValueError:
                    self.msg = "Densité invalide."
                    return True
            elif TOOL_KEY[k] == "replace" and not self.ask_replace():
                return True         # déjà fait sur toute la carte
            self.tool = TOOL_KEY[k]
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
                self.begin_stroke()
                self.paint({(self.cx, self.cy): self.brush})
            self.msg = "Crayon %s." % ("baissé" if self.pen_down else "levé")
        elif k == "y":
            self.eyedropper()
        elif k == "M":
            self.sym = FLIP_CYCLE[self.sym]
            self.msg = ("Symétrie : %s." % SYM_NAME[self.sym] if self.sym
                        else "Symétrie désactivée.")
        elif k == "E":
            self.edit_rows_cols()
        elif k in ("X", "Y", "O"):
            self.transform_clip({"X": "x", "Y": "y", "O": "rot"}[k])
        elif k == "a":
            self.advance = not self.advance
            self.msg = "Avance automatique %s." % (
                "activée" if self.advance else "désactivée")
        elif k == "m":
            self.place_entity()
        elif k == "r":
            if self.template and not self.no_entities():
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
            if self.tool == "pen":
                self.begin_stroke()
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
            self.end_stroke()
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
