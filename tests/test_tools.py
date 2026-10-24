"""Outils de dessin de l'éditeur, sans écran (Editor(None))."""

import unittest

from tests.util import grid, level

import nhmapedit
from nhlevel import Entity


def editor(rows):
    ed = nhmapedit.Editor(None)
    ed.lvl = level(rows)
    return ed


def two_points(ed, tool, a, b, brush="."):
    ed.tool, ed.brush = tool, brush
    ed.cx, ed.cy = a
    ed.apply()
    ed.cx, ed.cy = b
    ed.apply()


class Shapes(unittest.TestCase):
    def test_room(self):
        ed = editor(["     "] * 4)
        two_points(ed, "room", (0, 0), (4, 3))
        self.assertEqual(grid(ed.lvl), ["-----", "|...|", "|...|", "-----"])

    def test_line_and_rect(self):
        ed = editor(["    "] * 3)
        two_points(ed, "line", (0, 0), (3, 0), "#")
        two_points(ed, "rect", (0, 1), (3, 2), "W")
        self.assertEqual(grid(ed.lvl), ["####", "WWWW", "WWWW"])

    def test_ellipse_outline_has_no_diagonal_gap(self):
        cells = set(nhmapedit.ellipse_cells(0, 0, 8, 6, False))
        for x, y in cells:
            # deux cases du contour en diagonale ont un voisin commun
            for dx, dy in ((1, 1), (1, -1)):
                if (x + dx, y + dy) in cells:
                    self.assertTrue((x + dx, y) in cells
                                    or (x, y + dy) in cells)

    def test_fill(self):
        ed = editor(["-----", "|...|", "-----"])
        ed.tool, ed.brush, ed.cx, ed.cy = "fill", "L", 2, 1
        ed.apply()
        self.assertEqual(grid(ed.lvl)[1], "|LLL|")

    def test_scatter_density(self):
        ed = editor(["." * 20] * 20)
        ed.density = 0
        two_points(ed, "scatter", (0, 0), (19, 19), "T")
        self.assertNotIn("T", "".join(grid(ed.lvl)))
        ed.density = 100
        two_points(ed, "scatter", (0, 0), (19, 19), "T")
        self.assertEqual(set("".join(grid(ed.lvl))), {"T"})

    def test_replace(self):
        ed = editor(["..W", "W.."])
        ed.replace = ("W", "L", 100)
        ed.replace_terrain((0, 0), (2, 1))
        self.assertEqual(grid(ed.lvl), ["..L", "L.."])


class Symmetry(unittest.TestCase):
    def test_pen_mirrored_both_axes(self):
        ed = editor(["   "] * 3)
        ed.sym = 3
        ed.tool, ed.brush = "pen", "T"
        ed.apply()
        self.assertEqual(grid(ed.lvl), ["T T", "   ", "T T"])


class Clipboard(unittest.TestCase):
    def test_cut_paste_moves_entities(self):
        ed = editor(["..  ", "..  "])
        ed.lvl.entities = [Entity("stair", 1, 1, "down")]
        two_points(ed, "cut", (0, 0), (1, 1))
        self.assertEqual(ed.lvl.entities, [])
        self.assertEqual(ed.tool, "paste")
        ed.cx, ed.cy = 2, 0
        ed.apply()
        self.assertEqual(grid(ed.lvl), ["  ..", "  .."])
        self.assertEqual((ed.lvl.entities[0].x, ed.lvl.entities[0].y),
                         (3, 1))

    def test_rotation_swaps_walls(self):
        ed = editor(["---", "|.|"])
        two_points(ed, "copy", (0, 0), (2, 1))
        ed.transform_clip("rot")
        g = ["".join(r) for r in ed.clip[0]]
        # le mur du haut devient le mur de droite ; les coins restent « - »
        self.assertEqual(g, ["--", ".|", "--"])

    def test_mirror(self):
        ed = editor([".W"])
        two_points(ed, "copy", (0, 0), (1, 0))
        ed.transform_clip("x")
        self.assertEqual(["".join(r) for r in ed.clip[0]], ["W."])


class Undo(unittest.TestCase):
    def test_undo_redo(self):
        ed = editor(["..."])
        ed.tool, ed.brush = "pen", "W"
        ed.apply()
        ed.undo()
        self.assertEqual(grid(ed.lvl), ["..."])
        ed.redo()
        self.assertEqual(grid(ed.lvl), ["W.."])

    def test_stroke_is_one_step(self):
        ed = editor(["....."])
        ed.tool, ed.brush, ed.pen_down = "pen", "W", True
        ed.begin_stroke()
        ed.apply()
        for _ in range(4):
            ed.move(1, 0)
        ed.end_stroke()
        self.assertEqual(grid(ed.lvl), ["WWWWW"])
        ed.undo()
        self.assertEqual(grid(ed.lvl), ["....."])


if __name__ == "__main__":
    unittest.main()
