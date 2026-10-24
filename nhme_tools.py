"""Outils d'édition du terrain : dessin, presse-papiers, annulation."""

import random

import nhlevel
from nhme_common import Cancel, SELECT, TOOL_NAME, bresenham, ellipse_cells


class ToolsMixin:
    """Méthodes de l'éditeur (voir nhmapedit.Editor)."""

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
