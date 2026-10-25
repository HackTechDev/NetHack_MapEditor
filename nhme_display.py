"""Affichage : couleurs, carte, règles, panneau et barre d'état."""

import curses
import os
import tempfile

import nhexport
import nhlevel
from nhi18n import _
from nhme_common import (
    ASCII_GLYPH, FLIP_NAME, HI_COLORS, NH_COLORS, OBJ_CLASS_COLOR, RANDOM,
    REGION_BG, SELECT, SHORT, SYM_NAME, TERRAIN_COLOR, TOOLS, TOOL_NAME,
    TWO_POINT, game_view, region_family)


class DisplayMixin:
    """Méthodes de l'éditeur (voir nhmapedit.Editor)."""

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
        # calque des régions : une couleur de fond par famille, paires
        # (texte, fond) créées à la demande à partir de 10
        self.next_pair = 10

    def attr(self, clr, family=None):
        """Attribut curses d'une couleur NetHack ; family : fond du
        calque des régions (REGION_BG)."""
        if clr == RANDOM:
            return self.pairs.get(RANDOM, curses.A_DIM) | curses.A_BOLD
        clr = HI_COLORS.get(clr, clr)
        c, bold = NH_COLORS.get(clr, (curses.COLOR_WHITE, False))
        a = self.pairs.get(c, 0)
        if family and self.pairs:
            bg = REGION_BG[family]
            if c == bg:             # texte invisible sur ce fond
                c, bold = curses.COLOR_WHITE, True
            key = (c, bg)
            if (key not in self.pairs
                    and getattr(self, "next_pair", 99999) < curses.COLOR_PAIRS):
                curses.init_pair(self.next_pair, c, bg)
                self.pairs[key] = curses.color_pair(self.next_pair)
                self.next_pair += 1
            a = self.pairs.get(key, curses.A_REVERSE)
        return a | (curses.A_BOLD if bold else 0)

    def region_overlay(self):
        """Case -> famille de la région affichée dessus (calque)."""
        out = {}
        order = {"lit": 0, "dig": 1, "tele": 2, "room": 3}  # salles dessus
        for r in sorted(self.lvl.regions,
                        key=lambda r: order[region_family(r)]):
            fam = region_family(r)
            if fam in self.show_regions:
                for p in r.cells(self.lvl):
                    out[p] = fam
        return out

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
        if k == "gold":
            return "$", "CLR_YELLOW"
        if k == "grave":
            return "|", "CLR_WHITE"
        if k == "drawbridge":
            return "#", "CLR_BROWN"
        if k in ("feature", "terrain"):
            # le terrain qu'ils posent, dans sa couleur
            ch = nhlevel.FEATURES.get(v, "?") if k == "feature" else (v or "?")
            return ch, TERRAIN_COLOR.get(ch, "CLR_GRAY")
        return "?", "CLR_WHITE"

    def top_entity(self, x, y, index=None):
        ents = (index.get((x, y)) if index is not None
                else self.lvl.entities_at(x, y))
        if not ents:
            return None
        prio = ["monster", "object", "gold", "trap", "stair", "ladder",
                "altar", "grave", "engraving", "drawbridge", "feature",
                "terrain", "door"]
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

    def draw(self):
        scr = self.scr
        scr.erase()
        maxy, maxx, vw, vh, side, top, left = self.layout()
        if maxy < 12 or maxx < 40:
            self.put(0, 0, _("Terminal trop petit (min. 40x12)"))
            scr.refresh()
            return
        self.scroll_into_view(vw, vh)
        lvl = self.lvl
        # en-tête
        name = os.path.basename(self.path) if self.path else _("(sans nom)")
        if lvl.theme:
            name += _(" : salle « %s »") % lvl.theme["name"]
        head = " nhmapedit — %s%s   %dx%d" % (
            name, _(" [modifié]") if self.modified else "", lvl.w, lvl.h)
        if len(lvl.maps) > 1:
            head += _("   carte %d/%d ([ ] N)") % (lvl.map_index + 1,
                                                  len(lvl.maps))
        if lvl.w > nhlevel.MAP_X_LIM:
            head += "  (largeur > %d !)" % nhlevel.MAP_X_LIM
        if lvl.allowed_flips() and not lvl.theme:
            head += _("  (retournable : %s, f pour voir)") % FLIP_NAME[
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
        overlay = self.region_overlay()
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
                else:
                    ch = lvl.grid[y][x]
                    clr = TERRAIN_COLOR.get(ch, "CLR_GRAY")
                fam = overlay.get((x, y))
                a = self.attr(clr, fam)
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
                        a = self.attr(clr, None if clr == RANDOM else fam)
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
        self.put(y, x, _("Outils"), curses.A_BOLD)
        rows = (len(TOOLS) + 1) // 2
        for i, (t, _name, short, key) in enumerate(TOOLS):
            a = curses.A_REVERSE if t == self.tool else 0
            self.put(y + 1 + i % rows, x + i // rows * 13,
                     "%s %s" % (key, short), a)
        y += rows + 2
        self.put(y, x, _("Terrain"), curses.A_BOLD)
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
        info = _("(%2d,%2d) niveau %s  '%s' %s") % (
            x, y, "(%2d,%2d)" % (o[0] + x, o[1] + y) if o else "(?)",
            c, nhlevel.TERRAIN_DESC.get(c, "?"))
        ents = lvl.entities_at(x, y)
        if ents:
            info += "  | " + " ; ".join(e.describe() for e in ents)
        regs = lvl.regions_at(x, y)
        if regs:
            info += "  | " + " ; ".join(r.describe() for r in regs)
        self.put(maxy - 4, 0, info[:maxx - 1])
        bname = _("roche") if self.brush == " " else self.brush
        st = _("Outil: %s   Pinceau: %s (%s)") % (
            TOOL_NAME[self.tool], bname,
            nhlevel.TERRAIN_DESC[self.brush].split(" (")[0])
        if self.pen_down:
            st += _("   [crayon baissé]")
        if self.advance:
            st += _("   [avance auto]")
        if self.anchor:
            st += _("   ancre (%d,%d) -> %dx%d") % (
                self.anchor + (abs(self.cx - self.anchor[0]) + 1,
                               abs(self.cy - self.anchor[1]) + 1))
        if not self.show_ents:
            st += _("   [entités masquées]")
        if self.game:
            st += _("   [rendu jeu]")
        if self.flip:
            st += _("   [aperçu retourné : %s]") % FLIP_NAME[self.flip]
        if self.sym:
            st += _("   [symétrie : %s]") % SYM_NAME[self.sym]
        self.put(maxy - 3, 0, st[:maxx - 1], curses.A_BOLD)
        self.put(maxy - 2, 0, self.msg[:maxx - 1], self.attr("CLR_YELLOW"))
        self.put(maxy - 1, 0, self.context_hint()[:maxx - 1].ljust(
            maxx - 1), curses.A_REVERSE)

    def context_hint(self):
        """Barre du bas : les touches utiles dans la situation actuelle."""
        if self.tool == "region":
            return _(" Zone de la région : Espace/Entrée sur le coin "
                     "opposé  Échap: annuler")
        if self.anchor:
            return _(" Espace/Entrée: tracer jusqu'au curseur  "
                     "flèches/souris: 2e point  Échap: annuler l'ancre")
        if self.tool == "paste":
            if not self.clip:
                return (_(" Presse-papiers vide :  7: copier  D: couper  "
                          "b: modèle  Échap: Pinceau"))
            h, w = len(self.clip[0]), len(self.clip[0][0])
            return (_(" Espace: coller (%dx%d, coin haut-gauche au curseur)  "
                      "X/Y: miroir  O: rotation  b: modèles  Échap: Pinceau")
                    % (w, h))
        if self.pen_down:
            return (_(" Crayon baissé : flèches = peindre  caractère = "
                      "pinceau  d: lever  u: annuler le trait"))
        if self.tool in TWO_POINT:
            extra = {"scatter": _("  (densité %d %%)") % self.density,
                     "copy": "  puis 8 colle", "cut": "  puis 8 colle",
                     "replace": _("  (R : autre remplacement)")}
            return (_(" Espace: poser l'ancre (1er coin)  caractère: pinceau  "
                      "M: symétrie  u: annuler") + extra.get(self.tool, ""))
        if self.tool == "fill":
            return (_(" Espace: remplir la zone sous le curseur avec le "
                      "pinceau  y: pipette  u: annuler"))
        if self.show_ents and self.lvl.entities_at(self.cx, self.cy):
            return (_(" m: ajouter  z: supprimer  i: liste (e: modifier)  "
                      "r: répéter  Tab: masquer les entités"))
        if self.game:
            return (_(" Rendu jeu :  J: revenir aux caractères de carte  "
                      "f: retournement  ?: aide"))
        return _(" ?:aide  1-0 D G R:outils  m:entité  i:liste  "
                 "p:propriétés  t:tester  s:enregistrer  q:quitter")

    def put(self, y, x, s, a=0):
        try:
            self.scr.addstr(y, x, s, a)
        except curses.error:
            pass

    def export_image(self, path):
        """Exporte la carte seule en SVG (ou PNG), telle qu'elle est
        affichée : rendu d'édition ou « comme dans le jeu », entités
        visibles ou non."""
        lvl = self.lvl
        view = game_view(lvl.grid, lvl.init.get("fg", " ")) \
            if self.game else None
        index = lvl.entity_index()
        cells = []
        for y in range(lvl.h):
            row = []
            for x in range(lvl.w):
                if view:
                    ch, clr = view[y][x]
                else:
                    ch = lvl.grid[y][x]
                    clr = TERRAIN_COLOR.get(ch, "CLR_GRAY")
                    if ch == "x":
                        ch = " "
                bg = None
                e = self.top_entity(x, y, index) if self.show_ents else None
                if e:
                    ch, clr = self.entity_glyph(e)
                    if clr == RANDOM:
                        clr, bg = "CLR_WHITE", "#7a3e8a"
                row.append((ch, clr, bg))
            cells.append(row)
        title = os.path.basename(self.path or "nhmapedit")
        text = nhexport.svg(cells, title)
        if path.lower().endswith(".png"):
            with tempfile.TemporaryDirectory() as d:
                tmp = os.path.join(d, "carte.svg")
                with open(tmp, "w", encoding="utf-8") as f:
                    f.write(text)
                nhexport.svg_to_png(tmp, path)
        else:
            with open(path, "w", encoding="utf-8") as f:
                f.write(text)

