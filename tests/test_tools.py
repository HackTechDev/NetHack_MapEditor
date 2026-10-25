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


class Layers(unittest.TestCase):
    def test_presets_and_toggles(self):
        ed = editor(["..."])
        answers = iter(["regions", "tele", "terrain_l"])

        def pick(*a, **k):
            try:
                return next(answers)
            except StopIteration:
                raise nhmapedit.Cancel()
        ed.pick = pick
        ed.layers()
        self.assertEqual((ed.show_terrain, ed.show_ents, ed.show_regions),
                         (True, False, {"room", "lit", "dig"}))


class Annotate(unittest.TestCase):
    def test_annotate(self):
        ed = editor(["...", "..."])
        ed.lvl.entities = [Entity("monster", 1, 1, "newt")]
        ed.prompt = lambda *a, **k: "  case   vide "
        ed.annotate()                       # case sans entité
        self.assertEqual(ed.lvl.notes, {(0, 0): "case vide"})
        self.assertEqual(ed.region_overlay(), {(0, 0): "note"})
        ed.cx = ed.cy = 1
        ed.pick = lambda *a, **k: 0         # la première entité
        ed.prompt = lambda *a, **k: "le gardien"
        ed.annotate()
        self.assertEqual(ed.lvl.entities[0].note, "le gardien")
        self.assertIn("-- le gardien", ed.lvl.entities[0].describe())
        ed.undo()
        self.assertIsNone(ed.lvl.entities[0].note)
        ed.cx = ed.cy = 0
        ed.prompt = lambda *a, **k: ""
        ed.annotate()
        self.assertEqual(ed.lvl.notes, {})


class Maze(unittest.TestCase):
    def test_perfect_maze(self):
        import random
        for seed in range(5):
            cells = nhmapedit.maze_cells(2, 1, 22, 11, random.Random(seed))
            floor = {p for p, c in cells.items() if c == "."}
            # 10x5 cases reliées par 49 passages : un arbre, donc tout est
            # relié sans boucle
            self.assertEqual(len(floor), 50 + 49)
            seen, stack = set(), [min(floor)]
            while stack:
                x, y = stack.pop()
                if (x, y) in floor and (x, y) not in seen:
                    seen.add((x, y))
                    stack += [(x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)]
            self.assertEqual(seen, floor)
            # bordure fermée, murs en - et |
            self.assertTrue(all(cells[(x, 1)] == "-" for x in range(2, 23)))
            self.assertEqual({cells[(2, y)] for y in range(2, 11)}, {"|"})
            self.assertLessEqual(set(cells.values()), set(".-|"))

    def test_loops_and_tool(self):
        import random
        cells = nhmapedit.maze_cells(0, 0, 20, 10, random.Random(1), " ", "#",
                                     100)
        self.assertEqual(sum(c == "#" for c in cells.values()),
                         10 * 5 + 9 * 5 + 10 * 4)
        ed = editor(["     "] * 3 + ["    "  + " "])
        ed.maze_opts = ("-", ".", 0)
        two_points(ed, "maze", (0, 0), (4, 2))
        self.assertEqual(grid(ed.lvl)[:3], ["-----", "|...|", "-----"])
        self.assertEqual(ed.undo_stack[-1].label, "Labyrinthe")
        two_points(ed, "maze", (0, 0), (1, 1))
        self.assertIn("3x3", ed.msg)


class Walls(unittest.TestCase):
    def test_auto_walls_brush(self):
        ed = editor(["     "] * 4)
        ed.auto_walls = True
        ed.brush = "|"
        two_points(ed, "rect", (0, 0), (4, 3), "|")
        self.assertEqual(grid(ed.lvl), ["-----", "|   |", "|   |", "-----"])
        # mur intérieur : jonctions en | sur les murs verticaux
        two_points(ed, "line", (0, 2), (4, 2), "-")
        self.assertEqual(grid(ed.lvl), ["-----", "|   |", "|---|", "-----"])
        # effacer un mur corrige ses voisins
        ed.brush, ed.tool = " ", "pen"
        ed.cx, ed.cy = 0, 1
        ed.apply()
        self.assertEqual(grid(ed.lvl), ["-----", "    |", "----|", "-----"])

    def test_fix_walls(self):
        ed = editor(["|||||", "-...-", "-.+.-", "|||||"])
        ed.pick = lambda *a, **k: "map"
        ed.walls_menu()
        self.assertEqual(grid(ed.lvl), ["-----", "|...|", "|.+.|", "-----"])
        self.assertEqual(ed.undo_stack[-1].label, "Murs corrigés")
        ed.walls_menu()
        self.assertEqual(ed.msg, "Murs déjà corrects.")
        # dans une zone seulement
        ed = editor(["|||", "|||"])
        ed.pick = lambda *a, **k: "zone"
        ed.walls_menu()
        self.assertEqual(ed.tool, "walls")
        ed.cx = 1
        ed.apply()
        self.assertEqual(grid(ed.lvl), ["--|", "|||"])
        self.assertEqual(ed.tool, "pen")


class FindReplace(unittest.TestCase):
    def setUp(self):
        self.ed = editor(["....."] * 2)
        self.ed.lvl.entities = [
            Entity("monster", 0, 0, "orc"), Entity("monster", 1, 0, "orc"),
            Entity("monster", 2, 0, "kobold"), Entity("object", 3, 0, None)]

    def answer(self, *answers):
        it = iter(answers)
        self.ed.pick = lambda *a, **k: next(it)

    def test_replace_value_and_undo(self):
        ed = self.ed
        self.answer("monster", "'orc'", "value", "hill orc")
        ed.find_replace()
        self.assertEqual([e.value for e in ed.lvl.entities],
                         ["hill orc", "hill orc", "kobold", None])
        self.assertEqual(ed.undo_stack[-1].label,
                         "Remplacer : monstre orc → hill orc (2)")
        ed.undo()
        self.assertEqual(ed.lvl.entities[0].value, "orc")

    def test_options_and_delete(self):
        ed = self.ed
        ed.ask_extra = lambda *a: {"asleep": 1}
        self.answer("monster", "\0", "set")
        ed.find_replace()
        self.assertEqual([e.extra for e in ed.lvl.entities[:3]],
                         [{"asleep": 1}] * 3)
        self.answer("monster", "'kobold'", "unset", "asleep")
        ed.find_replace()
        self.assertEqual(ed.lvl.entities[2].extra, {})
        self.answer("object", "None", "delete")
        ed.find_replace()
        self.assertEqual(len(ed.lvl.entities), 3)


class EntitySelection(unittest.TestCase):
    def setUp(self):
        self.ed = ed = editor(["......"] * 4)
        ed.lvl.entities = [Entity("monster", 0, 0, "orc"),
                           Entity("object", 1, 1, "dagger"),
                           Entity("trap", 5, 3, "pit")]
        ed.lvl.grid[0][0] = "#"

    def select(self, action, a=(0, 0), b=(1, 1)):
        ed = self.ed
        ed.pick = lambda *a, **k: action
        ed.cx, ed.cy = a
        ed.start_entity_selection()
        ed.cx, ed.cy = b
        ed.apply()

    def test_move(self):
        ed = self.ed
        self.select("move")
        self.assertEqual(ed.tool, "entpaste")
        self.assertEqual(set(ed.preview_cells()), {(0, 0), (1, 1)})
        ed.cx, ed.cy = 3, 2
        ed.apply()
        self.assertEqual(ed.tool, "pen")
        self.assertEqual(sorted((e.kind, e.x, e.y) for e in ed.lvl.entities),
                         [("monster", 3, 2), ("object", 4, 3),
                          ("trap", 5, 3)])
        self.assertEqual(ed.lvl.grid[0][0], "#")      # terrain intact
        ed.undo()
        self.assertEqual(sorted((e.x, e.y) for e in ed.lvl.entities),
                         [(0, 0), (1, 1), (5, 3)])

    def test_copy_twice_and_delete(self):
        ed = self.ed
        self.select("copy")
        for x in (2, 5):
            ed.cx, ed.cy = x, 0
            ed.apply()
        self.assertEqual(ed.tool, "entpaste")
        self.assertEqual(len(ed.lvl.entities), 3 + 2 + 1)   # 1 hors carte
        self.assertIn("hors de la carte", ed.msg)
        self.select("delete", (0, 0), (5, 3))
        self.assertEqual(ed.lvl.entities, [])


class Stats(unittest.TestCase):
    def test_stats_text(self):
        ed = editor(["--+--", "|...|", "-----"])
        ed.lvl.entities = [Entity("monster", 1, 1, "jackal"),
                           Entity("monster", 2, 1, "jackal"),
                           Entity("monster", 3, 1, "d"),
                           Entity("object", 2, 1, None),
                           Entity("trap", 1, 1, "pit")]
        text = ed.stats_text()
        self.assertIn("Carte 5x3", text)
        self.assertRegex(text, r"-  mur horizontal / coin +9 +60 %")
        self.assertIn("Entités à position fixe : 5", text)
        self.assertRegex(text, r"d +3  jackal ×2, classe aléatoire")
        self.assertRegex(text, r"\? +1  aléatoire")
        self.assertRegex(text, r"pit +1")

    def test_difficulty(self):
        ed = editor(["......"])
        self.assertIsNone(ed.difficulty())
        ed.lvl.entities = [Entity("monster", 0, 0, None)]
        self.assertIsNone(ed.difficulty()["max"])
        self.assertIn("tous aléatoires", "\n".join(ed.difficulty_lines()))
        ed.lvl.entities += [Entity("monster", 1, 0, "newt"),
                            Entity("monster", 2, 0, "Medusa"),
                            Entity("monster", 3, 0, "gnome lady")]
        d = ed.difficulty()
        self.assertEqual((d["count"], d["named"], d["unknown"]), (4, 3, 1))
        self.assertEqual((d["hardest"], d["max"], d["depth"]),
                         ("Medusa", 25, 25))
        self.assertEqual(d["levels"], 0 + 20 + 3)
        self.assertAlmostEqual(d["mean"], (1 + 25 + 4) / 3)
        # une classe compte pour sa difficulté médiane
        ed.lvl.entities = [Entity("monster", 0, 0, "D")]
        d = ed.difficulty()
        self.assertEqual((d["classes"], d["hardest"]), (1, "classe D"))
        self.assertIn("profondeur conseillée : %d" % d["depth"],
                      ed.stats_text())


class Minimap(unittest.TestCase):
    def test_minimap(self):
        ed = editor(["..........    ", "..........    ",
                     "              ", "         WWWWW"])
        self.assertIsNone(ed.minimap_size(14, 4))        # tout est visible
        self.assertIsNone(ed.minimap_size(10, 3))        # vue trop petite
        ed.minimap = "on"
        self.assertEqual(ed.minimap_size(30, 12), (10, 4))
        rows = ed.minimap_cells(7, 2, 6, 2)
        self.assertEqual("".join(c for c, _s, _h in rows[0]), ".....  ")
        self.assertEqual("".join(c for c, _s, _h in rows[1]), "    WWW")
        # la vue (6x2 depuis 0,0) et le curseur (0,0)
        self.assertEqual([s for _c, s, _h in rows[0]], [True] * 3 + [False] * 4)
        self.assertEqual([h for _c, _s, h in rows[0]], [True] + [False] * 6)
        ed.minimap = "off"
        self.assertIsNone(ed.minimap_size(30, 12))
