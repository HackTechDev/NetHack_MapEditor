"""Constantes et fonctions communes aux modules de l'éditeur."""

import curses
import json
import os

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
# Extensions de « enregistrer sous » qui exportent la carte seule
EXPORTS = (".txt", ".svg", ".png")
# Dossiers de la bibliothèque de modèles (touche b) : ceux livrés avec
# l'éditeur, puis ceux de l'utilisateur, où l'on enregistre les siens
CONFIG_DIR = os.path.join(os.environ.get("XDG_CONFIG_HOME")
                          or os.path.expanduser("~/.config"), "nhmapedit")
TEMPLATE_DIRS = [os.path.join(HERE, "modeles"),
                 os.path.join(CONFIG_DIR, "modeles")]
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
  b  bibliothèque de modèles (temple, boutique, fontaine…) : le modèle
     choisi va dans le presse-papiers ; la dernière ligne enregistre le
     presse-papiers comme modèle (~/.config/nhmapedit/modeles)
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
  v  vérifier la carte, dont la connexité : escalier descendant accessible
     depuis le montant (portes sans diagonale, passages secrets, eau et
     lave signalés) et zones fermées ; règles de NetHack (porte dans un
     coin, escalier dans l'eau, autel hors d'un temple, carte qui déborde…) ;
     avec un interpréteur Lua, exécution du script complet avec une
     bibliothèque des factice (noms, paramètres, erreurs de syntaxe)
  t  tester : copie la carte dans le répertoire du jeu, à charger avec
     #wizloaddes en mode wizard (nethack -D) ; avec tmux, l'éditeur
     lance le jeu (panneau, fenêtre ou session tmux) et y charge la carte
     lui-même, puis la recharge à chaque nouvel appui sur t
  u  annuler      U / Ctrl-R  rétablir
  n  nouveau      o  ouvrir      s  enregistrer      w  enregistrer sous
     o sur un .txt : importe une carte en texte brut ;
     w vers un .txt : exporte la carte seule ; vers un .svg ou un .png :
     l'exporte en image, telle qu'elle est affichée (J, Tab)
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
