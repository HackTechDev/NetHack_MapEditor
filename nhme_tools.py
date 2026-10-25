"""Outils d'édition du terrain : dessin, presse-papiers, annulation."""

import os
import random
import re

import nhexport
import nhgen
import nhlevel
from nhi18n import _
from nhme_common import (
    GENERATOR_NAME, GENERATORS, HISTORY_MAX, PATTERNS, Cancel, HistoryEntry,
    SELECT, STAMPS,
    TEMPLATE_DIRS, TOOL_NAME, pattern_second,
    bresenham, ellipse_cells, maze_cells, wall_fixes)


def transform_grid(g, how):
    """Miroir (« x » : gauche/droite, « y » : haut/bas) ou rotation d'un
    quart de tour dans le sens horaire (« rot ») d'une grille ; renvoie
    la grille et la fonction qui déplace une position."""
    h, w = len(g), len(g[0])
    if how == "x":
        return [row[::-1] for row in g], lambda x, y: (w - 1 - x, y)
    if how == "y":
        return g[::-1], lambda x, y: (x, h - 1 - y)
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
    return g, lambda x, y: (h - 1 - y, x)


class ToolsMixin:
    """Méthodes de l'éditeur (voir nhmapedit.Editor)."""

    def preview_cells(self):
        """Cases qui seront modifiées par l'outil courant (aperçu)."""
        if self.tool == "paste" and self.clip:
            g = self.clip[0]
            return {(self.cx + x, self.cy + y): g[y][x]
                    for y in range(len(g)) for x in range(len(g[0]))}
        if self.tool == "entpaste":
            return {(self.cx + e.x, self.cy + e.y): " "
                    for e in self.ent_clip}
        if self.tool == "stamp":
            return self.mirrored(self.stamp_cells())
        if self.anchor is None:
            return {}
        cells = self.shape_cells(self.anchor, (self.cx, self.cy))
        if self.tool in ("copy", "cut", "region", "walls", "entsel"):
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
        elif t in ("rect", "copy", "cut", "maze", "walls", "entsel"):
            for x in range(lx, hx + 1):
                cells[(x, ly)] = cells[(x, hy)] = br
            for y in range(ly, hy + 1):
                cells[(lx, y)] = cells[(hx, y)] = br
        elif t in ("fillrect", "region"):
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
        elif t == "pattern":
            cells = self.pattern_cells((x, y) for y in range(ly, hy + 1)
                                       for x in range(lx, hx + 1))
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

    # Historique des commandes : undo_stack et redo_stack contiennent des
    # HistoryEntry. Une entrée de undo_stack garde l'état d'avant sa
    # commande ; annuler l'échange avec l'état courant et la passe dans
    # redo_stack (et inversement pour rétablir). L'état est un couple
    # (Level, snapshot) : dans un fichier à plusieurs cartes, chaque carte
    # éditée est un Level distinct, et annuler peut ramener à une autre.

    def checkpoint(self, label=None, snap=None):
        """Point d'annulation nommé label ; snap : état pris avant la
        modification (sinon, l'état actuel)."""
        self.serial += 1
        self.undo_stack.append(HistoryEntry(
            label or _("Modification"),
            (self.lvl, snap or self.lvl.snapshot()),
            self.serial, (self.cx, self.cy)))
        if len(self.undo_stack) > HISTORY_MAX:
            del self.undo_stack[0]
        self.redo_stack.clear()
        self.modified = True

    def history_state(self):
        """Numéro de l'état courant (0 : état d'ouverture)."""
        return self.undo_stack[-1].serial if self.undo_stack else 0

    def mark_saved(self, saved=True):
        """L'état courant est celui du fichier (saved), ou n'y est pas
        encore (carte importée, récupérée…)."""
        self.saved_state = self.history_state() if saved else -1
        self.modified = not saved

    def _swap(self, src, dst):
        e = src.pop()
        dst.append(e._replace(snap=(self.lvl, self.lvl.snapshot())))
        self.lvl, snap = e.snap
        self.lvl.restore(snap)
        self.cx, self.cy = e.pos
        self.clamp_cursor()
        self.modified = self.history_state() != self.saved_state
        return e

    def undo(self, quiet=False):
        if not self.undo_stack:
            self.msg = _("Rien à annuler.")
            return False
        e = self._swap(self.undo_stack, self.redo_stack)
        if not quiet:
            self.msg = _("Annulé : %s.") % e.label
        return True

    def redo(self, quiet=False):
        if not self.redo_stack:
            self.msg = _("Rien à rétablir.")
            return False
        e = self._swap(self.redo_stack, self.undo_stack)
        if not quiet:
            self.msg = _("Rétabli : %s.") % e.label
        return True

    def history(self):
        """Fenêtre de l'historique : choisir une commande y ramène la
        carte (annulations ou rétablissements successifs)."""
        done, undone = self.undo_stack, self.redo_stack[::-1]
        if not done and not undone:
            self.msg = _("Historique vide.")
            return
        items = [(_("   0. (ouverture de la carte)"), 0)]
        for i, e in enumerate(done, 1):
            items.append(("%s%4d. %s" % ("●" if i == len(done) else " ", i,
                                          e.label), i))
        for i, e in enumerate(undone, len(done) + 1):
            items.append(("%4d. %s %s" % (i, e.label, _("(annulé)")), i))
        if not done:
            items[0] = ("●" + items[0][0][1:], 0)
        target = self.pick(
            _("Historique : %d commande(s), %d annulée(s) (● état actuel)")
            % (len(done) + len(undone), len(undone)), items, len(done),
            hint=_("Entrée: revenir à cet état  Échap: fermer"))
        steps = target - len(done)
        for _i in range(abs(steps)):
            (self.redo if steps > 0 else self.undo)(quiet=True)
        if steps < 0:
            self.msg = _("%d commande(s) annulée(s).") % -steps
        elif steps > 0:
            self.msg = _("%d commande(s) rétablie(s).") % steps

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

    def paint_label(self):
        """Nom dans l'historique d'une commande qui peint au pinceau."""
        what = nhlevel.TERRAIN_DESC[self.brush].split(" (")[0]
        if self.stroke:
            return _("Trait au crayon : %s") % what
        return "%s : %s" % (TOOL_NAME[self.tool], what)

    def paint(self, cells, sym=True, label=None):
        if sym:
            cells = self.mirrored(cells)
        if self.draft_mode:
            return self.paint_draft(cells, label)
        if any(self.lvl.grid[y][x] != c for (x, y), c in cells.items()
               if 0 <= x < self.lvl.w and 0 <= y < self.lvl.h):
            if not (self.stroke and self.stroke_saved):
                self.checkpoint(label or self.paint_label())
                self.stroke_saved = self.stroke
            for (x, y), c in cells.items():
                self.lvl.set(x, y, c)
            if self.auto_walls:
                near = {(x + dx, y + dy) for x, y in cells
                        for dx in (-1, 0, 1) for dy in (-1, 0, 1)}
                for (x, y), c in wall_fixes(self.lvl.grid, near).items():
                    self.lvl.set(x, y, c)

    def paint_draft(self, cells, label=None):
        """Mode brouillon : les outils de dessin écrivent sur le calque de
        travail (la roche l'efface) ; annulable comme le reste."""
        draft = self.lvl.draft
        cells = {p: c for p, c in cells.items()
                 if 0 <= p[0] < self.lvl.w and 0 <= p[1] < self.lvl.h
                 and draft.get(p, " ") != c}
        if not cells:
            return
        if not (self.stroke and self.stroke_saved):
            self.checkpoint(_("Brouillon : %s") % (label
                                                  or self.paint_label()))
            self.stroke_saved = self.stroke
        for p, c in cells.items():
            if c == " ":
                draft.pop(p, None)
            else:
                draft[p] = c

    def draft_menu(self):
        """Touche & : calque de travail (brouillon) jamais enregistré."""
        lvl = self.lvl
        shown = "draft" in self.show_regions
        what = self.pick(_("Brouillon (%d case(s), jamais enregistré)")
                         % len(lvl.draft), [
            (_("dessiner sur la carte") if self.draft_mode
             else _("dessiner sur le brouillon"), "mode"),
            (_("masquer le brouillon") if shown
             else _("afficher le brouillon"), "show"),
            (_("reporter le brouillon sur la carte"), "apply"),
            (_("effacer le brouillon"), "clear")])
        if what == "mode":
            self.draft_mode = not self.draft_mode
            self.show_regions.add("draft")
            self.msg = (_("Les outils de dessin écrivent sur le brouillon "
                          "(e efface).") if self.draft_mode
                        else _("Les outils de dessin écrivent sur la carte."))
        elif what == "show":
            self.show_regions ^= {"draft"}
        elif not lvl.draft:
            self.msg = _("Brouillon vide.")
        elif what == "apply":
            self.checkpoint(_("Brouillon reporté sur la carte"))
            for (x, y), c in lvl.draft.items():
                if c in nhlevel.TERRAIN_DESC:
                    lvl.set(x, y, c)
            lvl.draft = {}
            self.msg = _("Brouillon reporté sur la carte.")
        else:
            self.checkpoint(_("Brouillon effacé"))
            lvl.draft = {}
            self.msg = _("Brouillon effacé.")

    def apply(self):
        t = self.tool
        if t == "pen":
            self.paint({(self.cx, self.cy): self.brush})
        elif t == "fill":
            self.flood_fill(self.cx, self.cy, self.brush)
        elif t == "paste":
            self.paste()
        elif t == "entpaste":
            self.place_entities()
        elif t == "stamp":
            self.paint(self.stamp_cells(),
                       label=_("Tampon : %s") % self.stamp[0])
        elif self.anchor is None:
            self.anchor = (self.cx, self.cy)
            self.msg = _("Ancre posée ; déplacez-vous puis Espace (Échap "
                         "annule).")
        else:
            a, b = self.anchor, (self.cx, self.cy)
            self.anchor = None
            if t == "scatter":
                cells = self.shape_cells(a, b)
                pick = {p: c for p, c in cells.items()
                        if random.random() * 100 < self.density}
                self.paint(pick)
                self.msg = _("Semis : %d cases sur %d (%d %%).") % (
                    len(pick), len(cells), self.density)
            elif t == "replace":
                self.replace_terrain(a, b)
            elif t == "region":
                self.finish_region(a, b)
            elif t == "walls":
                self.tool = self.walls_prev_tool
                self.fix_walls(a, b)
            elif t == "entsel":
                self.tool = self.sel_prev_tool
                self.entity_selection(a, b)
            elif t == "pattern" and a == b:
                # deux appuis sur la même case : la zone de même terrain
                self.paint(self.pattern_cells(self.same_terrain(*a)),
                           sym=False, label=self.pattern_label())
                self.msg = _("Zone remplie par le motif.")
            elif t == "pattern":
                self.paint(self.shape_cells(a, b), label=self.pattern_label())
                self.msg = _("Rectangle rempli par le motif.")
            elif t == "maze":
                self.generate(a, b, random.Random())
            elif t in SELECT:
                self.copy(a, b, cut=t == "cut")
            else:
                self.paint(self.shape_cells(a, b))
                self.msg = _("%s tracé.") % TOOL_NAME[t]

    def same_terrain(self, x, y):
        """Cases reliées à (x, y) (4 directions) de même terrain, et
        celles de ses reflets en mode symétrie."""
        old = self.lvl.grid[y][x]
        zone, stack = set(), list(self.mirror_points(x, y))
        while stack:
            p = stack.pop()
            if (p not in zone and 0 <= p[0] < self.lvl.w
                    and 0 <= p[1] < self.lvl.h
                    and self.lvl.grid[p[1]][p[0]] == old):
                zone.add(p)
                stack += [(p[0] + 1, p[1]), (p[0] - 1, p[1]),
                          (p[0], p[1] + 1), (p[0], p[1] - 1)]
        return zone

    def pattern_cells(self, cells):
        kind, first, second, w = self.pattern
        return {(x, y): second if pattern_second(kind, x, y, w) else first
                for x, y in cells}

    def pattern_label(self):
        kind, first, second, _w = self.pattern
        return _("Motif %s : « %s » et « %s »") % (
            dict(PATTERNS)[kind], first, second)

    def ask_pattern(self):
        """Options de l'outil Remplissage par motif."""
        kind, first, second, w = self.pattern
        kind = self.pick(_("Motif"), [(n, k) for k, n in PATTERNS], kind)
        items = [("%s  %s" % ("e" if c == " " else c, d), c)
                 for c, d in nhlevel.TERRAIN if c != "x"]
        first = self.pick(_("Premier terrain (fond)"), items, self.brush)
        second = self.pick(_("Second terrain"), items, second)
        label = (_("Écart entre deux diagonales ou deux points")
                 if kind in ("diagonal", "dots")
                 else _("Largeur des cases ou des bandes"))
        w = self.ask_int(label, w, 1, 9)
        self.pattern = (kind, first, second, w)

    def flood_fill(self, x, y, c):
        old = self.lvl.grid[y][x]
        if self.draft_mode:
            # brouillon : la zone de même terrain de la carte
            self.paint({p: c for p in self.same_terrain(x, y)}, sym=False,
                       label=_("Remplissage"))
            return
        if old == c:
            return
        self.checkpoint(_("Remplissage : %s")
                        % nhlevel.TERRAIN_DESC[c].split(" (")[0])
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
        self.msg = _("%d cases remplies.") % n

    def walls_menu(self):
        """Touche = : pinceau mur automatique, correction des murs."""
        what = self.pick(_("Murs automatiques"), [
            (_("désactiver le pinceau mur automatique") if self.auto_walls
             else _("activer le pinceau mur automatique"), "toggle"),
            (_("corriger les murs de toute la carte"), "map"),
            (_("corriger les murs d'une zone (à tracer)"), "zone")])
        if what == "toggle":
            self.auto_walls = not self.auto_walls
            self.msg = (_("Murs automatiques : - et | prennent la forme qui "
                          "convient.") if self.auto_walls
                        else _("Murs automatiques désactivés."))
        elif what == "map":
            self.fix_walls((0, 0), (self.lvl.w - 1, self.lvl.h - 1))
        else:
            if self.tool != "walls":
                self.walls_prev_tool = self.tool
            self.tool = "walls"
            self.anchor = (self.cx, self.cy)
            self.msg = _("Zone : allez au coin opposé puis Espace (Échap "
                         "annule).")

    def fix_walls(self, a, b):
        lx, hx = sorted((a[0], b[0]))
        ly, hy = sorted((a[1], b[1]))
        changes = wall_fixes(self.lvl.grid, [
            (x, y) for y in range(ly, hy + 1) for x in range(lx, hx + 1)])
        if not changes:
            self.msg = _("Murs déjà corrects.")
            return
        self.paint(changes, sym=False, label=_("Murs corrigés"))
        self.msg = _("%d mur(s) corrigé(s).") % len(changes)

    def generate(self, a, b, rng):
        """Outil Q : le générateur choisi remplit la zone tracée."""
        lx, hx = sorted((a[0], b[0]))
        ly, hy = sorted((a[1], b[1]))
        w, h = hx - lx + 1, hy - ly + 1
        kind = self.gen_kind
        if kind == "maze":
            wall, floor, loops = self.maze_opts
            cells = maze_cells(lx, ly, hx, hy, rng, wall, floor, loops)
            ok, small = any(c == floor for c in cells.values()), "3x3"
        else:
            if kind == "cave":
                fill, walls = self.cave_opts
                g = nhgen.cave_zone(w, h, rng, fill, walls)
                ok, small = True, "5x4"
            else:
                ok, small = w >= 12 and h >= 6, "12x6"
                g, rooms = (nhgen.rooms_and_corridors(
                    w, h, self.rooms_count, rng) if ok else ([], []))
            cells = {(lx + x, ly + y): c for y, row in enumerate(g)
                     for x, c in enumerate(row)}
            ok = ok and any(c == "." for c in cells.values())
        if not ok:
            self.msg = _("Zone trop petite : %s au moins.") % small
            return
        name = GENERATOR_NAME[kind]
        self.paint(cells, label=name)
        self.msg = _("%s tracé(e) (u puis Espace : un autre tirage).") % name
        if kind == "rooms":
            self.msg = _("%d salle(s) reliée(s) par des couloirs (u puis "
                         "Espace : un autre tirage).") % len(rooms)

    def ask_generator(self):
        """Choix du générateur de l'outil Q, puis ses options."""
        self.gen_kind = self.pick(_("Générer dans une zone"),
                                  [(n, k) for k, n in GENERATORS],
                                  self.gen_kind)
        if self.gen_kind == "maze":
            self.ask_maze()
        elif self.gen_kind == "cave":
            self.ask_cave()
        else:
            self.rooms_count = self.ask_int(
                _("Nombre de salles voulu (moins si la zone est petite)"),
                self.rooms_count, 2, 12)

    def ask_cave(self):
        fill, walls = self.cave_opts
        fill = self.ask_int(_("Roche au départ en % (plus : grotte plus "
                              "étroite)"), fill, 30, 60)
        walls = self.pick(_("Bord de la grotte"), [
            (_("murs - et | (comme les cartes des mines)"), True),
            (_("roche"), False)], walls)
        self.cave_opts = (fill, walls)

    def ask_maze(self):
        """Options du labyrinthe : murs, passages, boucles."""
        wall = self.pick(_("Murs du labyrinthe"), [
            (_("murs - et | (comme une carte des.map)"), "-"),
            (_("roche (comme les labyrinthes de Géhenne)"), " "),
            (_("le pinceau courant : %s") % nhlevel.TERRAIN_DESC[
                self.brush], self.brush)], self.maze_opts[0])
        floor = self.pick(_("Passages"), [
            (_("sol de salle (.)"), "."), (_("couloir (#)"), "#")],
            self.maze_opts[1])
        s = self.prompt(_("Boucles : %% de murs intérieurs abattus en plus "
                          "(0 = labyrinthe parfait) : "),
                        str(self.maze_opts[2]))
        try:
            loops = max(0, min(100, int(s)))
        except ValueError:
            raise Cancel()
        self.maze_opts = (wall, floor, loops)

    def ask_replace(self):
        """Demande les paramètres du remplacement. Renvoie True s'il faut
        tracer une zone, False s'il a été fait sur toute la carte."""
        items = [("%s  %s" % ("e" if c == " " else c, d), c)
                 for c, d in nhlevel.TERRAIN if c != "x"]
        old = self.pick(_("Remplacer quel terrain ?"), items,
                        self.lvl.grid[self.cy][self.cx])
        new = self.pick(_("Remplacer « %s » par :")
                        % nhlevel.TERRAIN_DESC[old], items, self.brush)
        s = self.prompt(_("Proportion des cases à remplacer en %% (1-100) : "),
                        "100")
        try:
            pct = max(1, min(100, int(s)))
        except ValueError:
            raise Cancel()
        self.replace = (old, new, pct)
        where = self.pick(_("Où remplacer ?"), [
            (_("sur toute la carte"), "map"),
            (_("dans une zone (à tracer avec l'ancre)"), "zone")])
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
        self.paint(cells, sym=False, label=_("Remplacer « %s » par « %s »") % (
            nhlevel.TERRAIN_DESC[old].split(" (")[0],
            nhlevel.TERRAIN_DESC[new].split(" (")[0]))
        self.msg = _("%d case(s) « %s » remplacée(s) par « %s ».") % (
            len(cells), nhlevel.TERRAIN_DESC[old], nhlevel.TERRAIN_DESC[new])

    def edit_rows_cols(self):
        """Menu : insérer ou supprimer une ligne ou une colonne."""
        lvl = self.lvl
        choices = [(_("insérer une ligne au-dessus"), "row-above"),
                   (_("insérer une ligne en dessous"), "row-below"),
                   (_("supprimer la ligne"), "row-del"),
                   (_("insérer une colonne à gauche"), "col-left"),
                   (_("insérer une colonne à droite"), "col-right"),
                   (_("supprimer la colonne"), "col-del")]
        what = self.pick(_("Lignes et colonnes (curseur en %d,%d)")
                         % (self.cx, self.cy), choices)
        label = dict((v, k) for k, v in choices)[what].capitalize()
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
            self.msg = (_("Taille maximale atteinte (%dx%d).")
                        % (nhlevel.MAX_W, nhlevel.MAX_H)
                        if "del" not in what else
                        _("Impossible : la carte n'a plus qu'une ligne "
                          "ou colonne."))
            return
        self.checkpoint(label, snap)
        self.clamp_cursor()
        self.msg = _("Carte maintenant en %dx%d%s.") % (
            lvl.w, lvl.h, "" if len(lvl.entities) == n else
            _(" (%d entité(s) supprimée(s))") % (n - len(lvl.entities)))

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
            self.checkpoint(_("Couper une zone %dx%d") % (len(g[0]), len(g)))
            fill = self.lvl.init.get("fg", " ")
            if fill not in nhlevel.TERRAIN_CHARS or fill == "x":
                fill = " "
            for y in range(ly, hy + 1):
                for x in range(lx, hx + 1):
                    self.lvl.set(x, y, fill)
            self.lvl.entities = [e for e in self.lvl.entities
                                 if e not in inside]
        self.tool = "paste"
        self.msg = (_("Zone %dx%d %s (%d entités). Outil Coller actif.")
                    % (hx - lx + 1, hy - ly + 1,
                       _("coupée") if cut else _("copiée"), len(ents)))

    def transform_clip(self, how):
        """Miroir (« x » : gauche/droite, « y » : haut/bas) ou rotation
        d'un quart de tour dans le sens horaire (« rot ») du
        presse-papiers, entités comprises."""
        if self.tool == "stamp":
            name, g = self.stamp
            self.stamp = (name, transform_grid(g, how)[0])
            self.msg = _("Tampon « %s » %s.") % (name, {
                "x": _("retourné gauche/droite"),
                "y": _("retourné haut/bas"),
                "rot": _("tourné d'un quart de tour")}[how])
            return
        if not self.clip:
            self.msg = _("Presse-papiers vide (outil 7 ou D pour en remplir "
                         "un).")
            return
        g, ents = self.clip
        g, pos = transform_grid(g, how)
        for e in ents:
            e.x, e.y = pos(e.x, e.y)
        self.clip = (g, ents)
        self.tool = "paste"
        self.msg = _("Presse-papiers %s (%dx%d). Outil Coller actif.") % (
            {"x": _("retourné gauche/droite"), "y": _("retourné haut/bas"),
             "rot": _("tourné d'un quart de tour")}[how], len(g[0]), len(g))

    def stamps(self):
        """Touche ^ : choisir un tampon de terrain, posé ensuite par
        Espace autant de fois que voulu (centré sur le curseur)."""
        items = [("%-34s %dx%d" % (name, len(rows[0]), len(rows)), i)
                 for i, (name, rows) in enumerate(STAMPS)]
        cur = next((i for i, (n, _r) in enumerate(STAMPS)
                    if self.stamp and n == self.stamp[0]), 0)
        i = self.pick(_("Tampons de terrain (x : case laissée telle "
                        "quelle)"), items, cur)
        name, rows = STAMPS[i]
        self.stamp = (name, [list(r) for r in rows])
        if self.tool != "stamp":
            self.stamp_prev_tool = self.tool
        self.tool, self.anchor = "stamp", None
        self.msg = _("Tampon « %s » : Espace le pose.") % name

    def stamp_cells(self):
        """Cases du tampon centré sur le curseur, sans les « x »."""
        g = self.stamp[1]
        ox, oy = self.cx - len(g[0]) // 2, self.cy - len(g) // 2
        return {(ox + x, oy + y): c for y, row in enumerate(g)
                for x, c in enumerate(row) if c != "x"}

    def paste(self):
        if not self.clip:
            self.msg = _("Presse-papiers vide (outil 7 pour copier).")
            return
        g, ents = self.clip
        self.checkpoint(_("Coller %dx%d") % (len(g[0]), len(g)))
        for y, row in enumerate(g):
            for x, c in enumerate(row):
                self.lvl.set(self.cx + x, self.cy + y, c)
        for e in ents:
            c = e.copy()
            c.x += self.cx
            c.y += self.cy
            if c.x < self.lvl.w and c.y < self.lvl.h:
                self.lvl.entities.append(c)
        self.msg = _("Collé.")

    def eyedropper(self):
        """Pipette : le terrain sous le curseur devient le pinceau."""
        self.brush = self.lvl.grid[self.cy][self.cx]
        self.msg = _("Pipette : pinceau %s.") % nhlevel.TERRAIN_DESC.get(
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

    def templates(self):
        """Bibliothèque de modèles : le modèle choisi va dans le
        presse-papiers, et l'outil Coller le pose où l'on veut."""
        items = [("%-26s %s" % (t, d), p)
                 for t, d, p in nhexport.list_templates(TEMPLATE_DIRS,
                                                  self.game_theme())]
        items.append((_("+ enregistrer le presse-papiers comme modèle"),
                      "_save"))
        path = self.pick(_("Modèles (tapez pour filtrer)"), items)
        if path == "_save":
            return self.save_template()
        try:
            self.clip = nhexport.load_template(path)
        except (OSError, ValueError) as e:
            self.msg = _("Modèle illisible : %s") % e
            return
        g, ents = self.clip
        self.tool = "paste"
        self.msg = (_("Modèle %s (%dx%d, %d entités) : outil Coller actif, "
                      "X/Y/O pour le retourner.") % (
                        os.path.basename(path), len(g[0]), len(g),
                        len(ents)))

    def save_template(self):
        if not self.clip:
            self.msg = (_("Presse-papiers vide : copiez d'abord une zone "
                          "(outil 7)."))
            return
        title = self.prompt(_("Nom du modèle : ")).strip()
        if not title:
            raise Cancel()
        d = TEMPLATE_DIRS[-1]
        path = os.path.join(d, re.sub(r"[^\w-]+", "-", title).strip("-")
                            .lower() + ".lua")
        if os.path.exists(path) and not self.confirm(
                _("%s existe. Écraser ?") % path):
            raise Cancel()
        try:
            os.makedirs(d, exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                f.write(nhexport.template_lua(title, *self.clip))
        except OSError as e:
            self.msg = _("Erreur d'écriture : %s") % e
            return
        self.msg = _("Modèle enregistré : %s") % path

