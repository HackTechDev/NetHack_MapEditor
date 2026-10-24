#!/usr/bin/env python3
"""Génère la capture d'écran du README (docs/capture.svg).

L'éditeur est lancé dans un pseudo-terminal, piloté par une suite de
touches, puis le contenu réel de l'écran curses (caractères, couleurs,
gras, inversion) est converti en image SVG.

Usage : python3 docs/capture.py [--level NIVEAU.lua] [--out FICHIER.svg]
                                [--size LARGEURxHAUTEUR]
"""

import argparse
import fcntl
import json
import os
import pty
import select
import shutil
import struct
import sys
import tempfile
import termios
import time
from xml.sax.saxutils import escape

DOCS = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(DOCS)
DEFAULT_LEVEL = os.path.join(ROOT, "..", "NetHack-5.0.0", "dat",
                             "medusa-1.lua")

# Touches envoyées à l'éditeur : outil Salle, ancre posée, puis curseur
# déplacé pour montrer l'aperçu du tracé
RIGHT, DOWN = "\x1bOC", "\x1bOB"
KEYS = [RIGHT * 55, DOWN * 3, "5", " ", RIGHT * 9, DOWN * 4]

# Palette du terminal : couleurs curses 0-7, normales et en gras
NORMAL = ["#45475a", "#e06c75", "#98c379", "#c8a04a",
          "#5c7cfa", "#c678dd", "#56b6c2", "#c8ccd4"]
BRIGHT = ["#7f86ff", "#ff7b72", "#b5f08a", "#ffd866",
          "#8fb4ff", "#f0a6ff", "#8ae6f0", "#ffffff"]
BG, FG = "#1b1d23", "#c8ccd4"
CW, CH, PAD, TOP = 9, 18, 14, 30    # case, marges, barre de titre (px)


def child(dump, level):
    """Lance l'éditeur en écrivant l'écran dans dump à chaque affichage."""
    import curses
    sys.path.insert(0, ROOT)
    import nhmapedit

    draw = nhmapedit.Editor.draw

    def draw_and_dump(self):
        draw(self)
        maxy, maxx = self.scr.getmaxyx()
        cursor = self.scr.getyx()   # avant instr()/inch(), qui le déplacent
        rows = []
        for y in range(maxy):
            text = self.scr.instr(y, 0, maxx).decode("utf-8", "replace")
            cells = []
            for x in range(min(len(text), maxx)):
                a = self.scr.inch(y, x)
                cells.append([text[x],
                              curses.pair_number(a & curses.A_COLOR),
                              bool(a & curses.A_BOLD),
                              bool(a & curses.A_REVERSE)])
            rows.append(cells)
        with open(dump, "w", encoding="utf-8") as f:
            json.dump({"rows": rows, "cursor": cursor}, f)

    nhmapedit.Editor.draw = draw_and_dump
    sys.argv = ["nhmapedit", level]
    nhmapedit.main()


def capture(level, cols, rows):
    """Pilote l'éditeur dans un pseudo-terminal ; renvoie l'écran final."""
    tmp = tempfile.mkdtemp(prefix="nhme-capture-")
    try:
        # copie du niveau : l'éditeur ne touche jamais au fichier d'origine
        copy = os.path.join(tmp, os.path.basename(level))
        shutil.copy(level, copy)
        dump = os.path.join(tmp, "screen.json")
        pid, fd = pty.fork()
        if pid == 0:
            os.environ["TERM"] = "xterm-256color"
            # capture du README en français, sauf NHMAPEDIT_LANG=en
            os.environ.setdefault("NHMAPEDIT_LANG", "fr")
            os.environ["NHMAPEDIT_CONFIG"] = os.devnull
            os.execv(sys.executable, [sys.executable, __file__,
                                      "--child", dump, copy])
        fcntl.ioctl(fd, termios.TIOCSWINSZ,
                    struct.pack("HHHH", rows, cols, 0, 0))

        def drain(delay):
            end = time.time() + delay
            while time.time() < end:
                if select.select([fd], [], [], 0.05)[0]:
                    try:
                        os.read(fd, 65536)
                    except OSError:
                        return

        drain(1.0)
        for k in KEYS:
            os.write(fd, k.encode())
            drain(0.3)
        os.kill(pid, 9)
        os.waitpid(pid, 0)
        with open(dump, encoding="utf-8") as f:
            return json.load(f)
    finally:
        shutil.rmtree(tmp)


def to_svg(screen, title):
    rows, (cy, cx) = screen["rows"], screen["cursor"]
    while rows and not "".join(c[0] for c in rows[-1]).strip():
        rows.pop()
    # inch() ne sait pas lire les attributs des caractères non ASCII :
    # on reprend ceux de la case précédente
    for r in rows:
        for i, c in enumerate(r):
            if i and (c[1] > 8 or ord(c[0]) > 127):
                c[1:] = r[i - 1][1:]
    w = max(len(r) for r in rows)
    width, height = PAD * 2 + w * CW, TOP + PAD + len(rows) * CH
    bar = (TOP - 8) // 2
    out = [
        '<svg xmlns="http://www.w3.org/2000/svg" width="%d" height="%d" '
        'viewBox="0 0 %d %d">' % (width, height, width, height),
        '<rect width="100%%" height="100%%" rx="8" fill="%s"/>' % BG,
        '<rect width="100%%" height="%d" rx="8" fill="#2b2e36"/>'
        '<rect y="%d" width="100%%" height="8" fill="#2b2e36"/>'
        % (TOP - 8, TOP - 16),
        "".join('<circle cx="%d" cy="%d" r="6" fill="%s"/>'
                % (18 + i * 20, bar, c)
                for i, c in enumerate(["#ff5f57", "#febc2e", "#28c840"])),
        '<text x="50%%" y="%d" text-anchor="middle" fill="#9aa0aa" '
        'font-family="sans-serif" font-size="12">%s</text>'
        % (bar + 4, escape(title)),
        '<g font-family="DejaVu Sans Mono, Menlo, Consolas, monospace" '
        'font-size="15" text-anchor="middle">',
    ]
    for y, r in enumerate(rows):
        x = 0
        while x < len(r):
            _, pair, bold, rev = r[x]
            j = x
            while j < len(r) and r[j][1:] == r[x][1:]:
                j += 1
            if pair == 0:
                fg = "#ffffff" if bold else FG
            else:
                fg = (BRIGHT if bold else NORMAL)[pair - 1]
            px, py = PAD + x * CW, TOP + y * CH
            if rev:
                out.append('<rect x="%d" y="%d" width="%d" height="%d" '
                           'fill="%s"/>' % (px, py, (j - x) * CW, CH, fg))
                fg = BG
            # un <text> par caractère : l'alignement ne dépend pas de la
            # police ni du moteur de rendu SVG
            for k, c in enumerate(r[x:j]):
                if c[0] != " ":
                    out.append('<text x="%d" y="%d" fill="%s"%s>%s</text>' % (
                        px + k * CW + CW // 2, py + 14, fg,
                        ' font-weight="bold"' if bold else "",
                        escape(c[0])))
            x = j
    out.append("</g>")
    out.append('<rect x="%d" y="%d" width="%d" height="%d" fill="none" '
               'stroke="#ffffff" stroke-width="1.5"/>'
               % (PAD + cx * CW, TOP + cy * CH, CW, CH))
    out.append("</svg>")
    return "\n".join(out) + "\n"


def main():
    if len(sys.argv) == 4 and sys.argv[1] == "--child":
        child(sys.argv[2], sys.argv[3])
        return
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--level", default=DEFAULT_LEVEL,
                    help="niveau à afficher (défaut : medusa-1.lua des "
                         "sources de NetHack)")
    ap.add_argument("--out", default=os.path.join(DOCS, "capture.svg"),
                    help="fichier SVG produit (défaut : docs/capture.svg)")
    ap.add_argument("--size", default="108x30",
                    help="taille du terminal simulé (défaut : 108x30)")
    args = ap.parse_args()
    if not os.path.isfile(args.level):
        sys.exit("Niveau introuvable : %s (utilisez --level)" % args.level)
    try:
        cols, rows = (int(v) for v in args.size.lower().split("x"))
    except ValueError:
        sys.exit("--size attend LARGEURxHAUTEUR, ex: --size 108x28")
    screen = capture(args.level, cols, rows)
    title = "nhmapedit — " + os.path.basename(args.level)
    with open(args.out, "w", encoding="utf-8") as f:
        f.write(to_svg(screen, title))
    print("Capture écrite : %s" % args.out)


if __name__ == "__main__":
    main()
