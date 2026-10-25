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

    def test_labels_and_messages(self):
        ed = editor(["....", "...."])
        two_points(ed, "line", (0, 0), (3, 0), "W")
        ed.cx, ed.cy = 1, 1
        ed.add_entity(Entity("stair", 0, 0, "up"))
        self.assertEqual([e.label for e in ed.undo_stack],
                         ["Ligne : eau", "Ajout : escalier up"])
        ed.undo()
        self.assertEqual(ed.msg, "Annulé : Ajout : escalier up.")
        self.assertEqual(ed.lvl.entities, [])
        ed.redo()
        self.assertEqual(ed.msg, "Rétabli : Ajout : escalier up.")
        self.assertEqual(len(ed.lvl.entities), 1)

    def test_cursor_back_to_command(self):
        ed = editor(["....", "...."])
        ed.tool, ed.brush, ed.cx, ed.cy = "pen", "W", 2, 1
        ed.apply()
        ed.cx, ed.cy = 0, 0
        ed.undo()
        self.assertEqual((ed.cx, ed.cy), (2, 1))

    def test_properties_undone(self):
        ed = editor(["...."])
        ed.checkpoint("Drapeaux")
        ed.lvl.flags = ["noflip"]
        ed.lvl.init = {"style": "mines"}
        ed.undo()
        self.assertEqual(ed.lvl.flags, ["mazelevel"])
        self.assertEqual(ed.lvl.init, {"style": "solidfill", "fg": " "})

    def test_modified_follows_saved_state(self):
        ed = editor(["...."])
        ed.mark_saved()
        ed.tool, ed.brush = "pen", "W"
        ed.apply()
        self.assertTrue(ed.modified)
        ed.undo()
        self.assertFalse(ed.modified)       # retour à l'état enregistré
        ed.redo()
        self.assertTrue(ed.modified)

    def test_history_jump(self):
        ed = editor(["...."])
        ed.tool = "pen"
        for x, c in enumerate("WLT"):
            ed.cx, ed.brush = x, c
            ed.apply()
        answers = iter([1, 3])          # revenir après la 1re, puis la 3e
        ed.pick = lambda *a, **k: next(answers)
        ed.history()
        self.assertEqual(grid(ed.lvl), ["W..."])
        self.assertEqual((len(ed.undo_stack), len(ed.redo_stack)), (1, 2))
        self.assertEqual(ed.msg, "2 commande(s) annulée(s).")
        ed.history()
        self.assertEqual(grid(ed.lvl), ["WLT."])
        self.assertEqual(ed.msg, "2 commande(s) rétablie(s).")


class ContextHint(unittest.TestCase):
    def test_states(self):
        ed = editor(["....", "...."])
        self.assertIn("?:aide", ed.context_hint())
        ed.tool = "rect"
        self.assertIn("poser l'ancre", ed.context_hint())
        ed.anchor = (0, 0)
        self.assertIn("annuler l'ancre", ed.context_hint())
        ed.anchor, ed.tool = None, "paste"
        self.assertIn("Presse-papiers vide", ed.context_hint())
        ed.clip = ([["-", "-", "-"], ["|", ".", "|"]], [])
        self.assertIn("coller (3x2", ed.context_hint())
        ed.tool, ed.pen_down = "pen", True
        self.assertIn("Crayon baissé", ed.context_hint())


if __name__ == "__main__":
    unittest.main()


class Maps(unittest.TestCase):
    def test_add_switch_undo(self):
        ed = editor(["...."] * 2)
        ed.prompt = lambda *a, **k: "5x3"
        answers = iter(["left", "top"])
        ed.pick = lambda *a, **k: next(answers)
        ed.lvl.grid[0][0] = "#"
        ed.add_map()
        self.assertEqual((ed.lvl.map_index, len(ed.lvl.maps)), (1, 2))
        self.assertEqual((ed.lvl.w, ed.lvl.h), (5, 3))
        ed.paint({(0, 0): "L"})
        ed.switch_map(0)
        self.assertEqual(ed.lvl.grid[0][0], "#")
        self.assertIn("L....", ed.lvl.to_lua())
        ed.undo()                   # le trait sur la carte 2
        self.assertEqual((ed.lvl.map_index, ed.lvl.grid[0][0]), (1, "."))
        ed.undo()                   # l'ajout de la carte
        self.assertEqual(len(ed.lvl.maps), 0)
        ed.redo()
        ed.redo()                   # retour sur la carte 1, comme avant
        self.assertEqual((ed.lvl.map_index, ed.lvl.grid[0][0]), (0, "#"))
        self.assertIn("L....", ed.lvl.to_lua())
        self.assertIn(".22222.", ed.maps_overview())


class Regions(unittest.TestCase):
    def test_draw_edit_undo(self):
        ed = editor(["....."] * 4)
        answers = iter(["table"])
        ed.pick = lambda *a, **k: next(answers)
        ed.form = lambda title, fields, values: dict(values, type="temple")
        ed.cx, ed.cy = 1, 1
        ed.start_region("region")
        self.assertEqual(ed.tool, "region")
        ed.cx, ed.cy = 3, 2
        ed.apply()
        self.assertEqual(ed.tool, "pen")
        r = ed.lvl.regions[0]
        self.assertEqual((r.rect, r.extra), ((1, 1, 3, 2), {"type": "temple"}))
        self.assertEqual(ed.lvl.regions_at(2, 2), [r])
        # redessin de la zone depuis la liste
        answers = iter(["rect"])
        ed.cx, ed.cy = 0, 0
        self.assertTrue(ed.region_action(r, "edit"))
        ed.cx, ed.cy = 1, 1
        ed.apply()
        self.assertEqual(ed.lvl.regions[0].rect, (0, 0, 1, 1))
        ed.undo()
        self.assertEqual(ed.lvl.regions[0].rect, (1, 1, 3, 2))
        ed.region_action(ed.lvl.regions[0], "delete")
        self.assertEqual(ed.lvl.regions, [])
        ed.undo()
        self.assertEqual(len(ed.lvl.regions), 1)

    def test_whole_level_and_escape(self):
        ed = editor(["..."] * 2)
        ed.pick = lambda *a, **k: "all"
        ed.start_region("non_passwall")
        self.assertEqual(ed.lvl.regions[0].rect, None)
        self.assertEqual(ed.tool, "pen")
        ed.pick = lambda *a, **k: "zone"
        ed.start_region("non_diggable")
        ed.end_region()
        self.assertEqual((ed.tool, len(ed.lvl.regions)), ("pen", 1))
