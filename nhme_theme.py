"""Thèmes de l'interface, repris du lanceur NetHack (Nethack_Launcher).

Les menus de l'éditeur ont le même aspect que le menu du lanceur : un
bloc de titre entre deux lignes « ==== », des titres de groupe
« ── Groupe ──── », des lignes numérotées avec leur touche entre
crochets, une barre de sélection, la description de la ligne choisie et
une ligne d'aide « ↑/↓ naviguer · Entrée choisir · … ». Les couleurs
suivent le thème : « cyber » (néon de Night City) quand le jeu est dans
sa version cyberpunk, « classique » sinon, ou « sobre » (sans couleur).
"""

import curses
import re

# Couleurs du terminal, dans l'ordre de curses (comme le lanceur)
COLORS = ["noir", "rouge", "vert", "jaune", "bleu", "magenta", "cyan",
          "blanc"]

# Mise en forme de chaque élément : (couleur ou None, attributs...).
# Un thème peut redéfinir n'importe lequel de ces éléments.
COMMON = {
    "titre": (None, "gras"),
    "texte": (None,),
    "discret": (None, "pale"),
    "aide": (None, "pale"),
    "indisponible": (None, "pale"),
    "etat": (None, "gras"),
}
THEMES = {
    "classique": {
        "entete": ("jaune", "gras", "inverse"),
        "separateur": ("bleu",),
        "groupe": ("bleu", "gras"),
        "numero": ("cyan",),
        "touche": ("jaune", "gras"),
        "erreur": ("rouge", "gras"),
        "message": ("jaune",),
        "description": ("cyan",),
    },
    "cyber": {
        "entete": ("magenta", "gras", "inverse"),
        "titre": ("cyan", "gras"),
        "separateur": ("cyan",),
        "groupe": ("magenta", "gras"),
        "numero": ("vert",),
        "touche": ("cyan", "gras"),
        "erreur": ("rouge", "gras"),
        "message": ("vert",),
        "description": ("magenta",),
    },
    "sobre": {
        "entete": (None, "inverse"),
        "separateur": (None,),
        "groupe": (None, "gras"),
        "numero": (None,),
        "touche": (None, "gras"),
        "erreur": (None, "gras"),
        "message": (None,),
        "description": (None,),
    },
}
NAMES = list(THEMES)

# Nom de l'éditeur dans la barre de titre, selon l'univers
HEADER = {"cyber": "nhmapedit // NIGHT CITY"}


def theme_name(choice, game_theme):
    """Thème utilisé : choice (auto, classique, cyber, sobre) ; auto
    prend « cyber » pour la version cyberpunk du jeu, comme le lanceur."""
    if choice in THEMES:
        return choice
    return "cyber" if game_theme == "cyber" else "classique"


def curses_styles(name, pairs):
    """{élément: attribut curses} du thème ; pairs : {couleur curses:
    paire} déjà créées (vide sans couleurs : attributs seuls)."""
    attrs = {"gras": curses.A_BOLD, "pale": curses.A_DIM,
             "inverse": curses.A_REVERSE}
    out = {"selection": curses.A_REVERSE | curses.A_BOLD}
    for elem, (color, *flags) in {**COMMON, **THEMES[name]}.items():
        a = 0
        for f in flags:
            a |= attrs[f]
        if color and pairs:
            a |= pairs.get(COLORS.index(color), 0)
        out[elem] = a
    return out


def group_line(title, width, unicode=True):
    """« ── Groupe ──────── » sur width colonnes."""
    bar = "─" if unicode else "-"
    head = "%s %s " % (bar * 2, title)
    return head + bar * max(0, width - len(head))


def dotted(hint):
    """Aide au format du lanceur : « Entrée: choisir  Échap: annuler »
    devient « Entrée: choisir · Échap: annuler »."""
    return re.sub(r"\s{2,}", " · ", hint.strip())
