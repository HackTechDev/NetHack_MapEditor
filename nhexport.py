"""Import et export : carte en texte brut, image SVG ou PNG."""

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
