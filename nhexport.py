"""Import et export : carte en texte brut, image SVG ou PNG."""

import shutil
import subprocess

import nhlevel


def import_text(text):
    """Level à partir d'une carte ASCII seule (sans le Lua autour).

    Les lignes vides du début et de la fin sont ignorées, les lignes
    courtes complétées par de la roche. Lève ValueError si la carte est
    trop grande ou contient des caractères inconnus."""
    lines = text.expandtabs().replace("\r", "").split("\n")
    while lines and not lines[0].strip():
        lines.pop(0)
    while lines and not lines[-1].strip():
        lines.pop()
    lines = [l.rstrip() for l in lines]
    if not lines:
        raise ValueError("carte vide")
    w, h = max(len(l) for l in lines), len(lines)
    if w > nhlevel.MAX_W or h > nhlevel.MAX_H:
        raise ValueError("carte de %dx%d : %dx%d au plus" % (
            w, h, nhlevel.MAX_W, nhlevel.MAX_H))
    bad = sorted({c for l in lines for c in l
                  if c not in nhlevel.TERRAIN_CHARS})
    if bad:
        raise ValueError("caractères inconnus : %s" % " ".join(
            repr(c) for c in bad))
    lvl = nhlevel.Level(w, h)
    for y, l in enumerate(lines):
        for x, c in enumerate(l):
            lvl.set(x, y, c)
    return lvl


def export_text(lvl):
    return lvl.map_text() + "\n"


# Palette (fond sombre) : couleur curses -> (normale, vive)
_NORMAL = ["#45475a", "#e06c75", "#98c379", "#c8a04a",
           "#5c7cfa", "#c678dd", "#56b6c2", "#c8ccd4"]
_BRIGHT = ["#7f86ff", "#ff7b72", "#b5f08a", "#ffd866",
           "#8fb4ff", "#f0a6ff", "#8ae6f0", "#ffffff"]
# Couleurs NetHack (include/color.h) -> (indice curses, vive)
NH_RGB_INDEX = {
    "CLR_BLACK": (4, False), "CLR_RED": (1, False),
    "CLR_GREEN": (2, False), "CLR_BROWN": (3, False),
    "CLR_BLUE": (4, False), "CLR_MAGENTA": (5, False),
    "CLR_CYAN": (6, False), "CLR_GRAY": (7, False),
    "NO_COLOR": (7, False), "CLR_ORANGE": (1, True),
    "CLR_BRIGHT_GREEN": (2, True), "CLR_YELLOW": (3, True),
    "CLR_BRIGHT_BLUE": (4, True), "CLR_BRIGHT_MAGENTA": (5, True),
    "CLR_BRIGHT_CYAN": (6, True), "CLR_WHITE": (7, True),
}
BG = "#1b1d23"
CW, CH, PAD = 10, 18, 12        # taille d'une case et marge, en pixels


def rgb(clr):
    i, bright = NH_RGB_INDEX.get(clr, (7, False))
    return (_BRIGHT if bright else _NORMAL)[i]


def _esc(c):
    return {"&": "&amp;", "<": "&lt;", ">": "&gt;"}.get(c, c)


def svg(cells, title=""):
    """Image SVG d'une grille de cases (caractère, couleur NetHack[,
    fond]) ; fond : couleur de fond de la case (aléatoires…)."""
    h, w = len(cells), max(len(r) for r in cells)
    width, height = PAD * 2 + w * CW, PAD * 2 + h * CH
    out = ['<svg xmlns="http://www.w3.org/2000/svg" width="%d" height="%d" '
           'viewBox="0 0 %d %d">' % (width, height, width, height)]
    if title:
        out.append("<title>%s</title>" % "".join(_esc(c) for c in title))
    out.append('<rect width="100%%" height="100%%" fill="%s"/>' % BG)
    out.append('<g font-family="DejaVu Sans Mono, Menlo, Consolas, '
               'monospace" font-size="16" text-anchor="middle">')
    for y, row in enumerate(cells):
        for x, cell in enumerate(row):
            ch, clr = cell[0], cell[1]
            px, py = PAD + x * CW, PAD + y * CH
            if len(cell) > 2 and cell[2]:
                out.append('<rect x="%d" y="%d" width="%d" height="%d" '
                           'fill="%s"/>' % (px, py, CW, CH, cell[2]))
            if ch != " ":
                # un <text> par case : l'alignement ne dépend pas de la
                # police
                out.append('<text x="%d" y="%d" fill="%s">%s</text>' % (
                    px + CW // 2, py + 14, rgb(clr), _esc(ch)))
    out.append("</g></svg>")
    return "\n".join(out) + "\n"


def svg_to_png(svg_path, png_path):
    """Convertit avec rsvg-convert ou ImageMagick ; lève OSError si aucun
    des deux n'est installé."""
    if shutil.which("rsvg-convert"):
        cmd = ["rsvg-convert", "-o", png_path, svg_path]
    elif shutil.which("magick"):
        cmd = ["magick", svg_path, png_path]
    elif shutil.which("convert"):
        cmd = ["convert", svg_path, png_path]
    else:
        raise OSError("export PNG : installez rsvg-convert (librsvg) ou "
                      "ImageMagick, ou exportez en .svg")
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode:
        raise OSError("conversion en PNG : %s" % r.stderr.strip()[:200])
