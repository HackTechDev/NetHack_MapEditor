"""Outils communs aux tests."""

import glob
import os
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
# messages vérifiés en français, quelle que soit la locale
os.environ["NHMAPEDIT_LANG"] = "fr"
# noms du script seuls, sans le catalogue du jeu installé sur la machine
os.environ["NHMAPEDIT_GAME_LANG"] = "en"
os.environ["NHMAPEDIT_PALETTE"] = "aucune"

# Niveaux de NetHack : $NHMAPEDIT_DAT, sinon les sources à côté du dépôt
DAT = os.environ.get("NHMAPEDIT_DAT",
                     os.path.join(ROOT, "..", "NetHack-5.0.0", "dat"))


def dat_files():
    return sorted(glob.glob(os.path.join(DAT, "*.lua")))


def luac():
    """Compilateur Lua pour vérifier la syntaxe : $NHMAPEDIT_LUAC, luac
    ou luac5.4 dans le PATH ; None si absent."""
    for c in (os.environ.get("NHMAPEDIT_LUAC"), "luac5.4", "luac"):
        if c and shutil.which(c):
            return shutil.which(c)
    return None


def level(rows, **kw):
    """Level à partir d'une liste de lignes de carte."""
    import nhlevel
    lvl = nhlevel.Level(len(rows[0]), len(rows))
    for y, r in enumerate(rows):
        for x, c in enumerate(r):
            lvl.set(x, y, c)
    for k, v in kw.items():
        setattr(lvl, k, v)
    return lvl


def grid(lvl):
    return ["".join(r) for r in lvl.grid]
