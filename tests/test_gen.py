"""Assistant de niveau et générateurs (nhgen)."""

import random
import unittest

import nhcheck
import nhgen
import nhlevel
import nhmapedit


def errors(lvl):
    """Messages graves (!) de la vérification, connexité comprise."""
    return [m for m in nhcheck.check(lvl) if m.startswith("!")]


class Generators(unittest.TestCase):
    def test_rooms_connected_with_proper_doors(self):
        for seed in range(8):
            grid, rooms = nhgen.rooms_and_corridors(75, 19, 7,
                                                    random.Random(seed))
            self.assertGreaterEqual(len(rooms), 2)
            # une seule zone praticable (portes et couloirs compris)
            self.assertEqual(len(nhgen.zones(grid)), 1)
            for y, row in enumerate(grid):
                for x, c in enumerate(row):
                    if c == "+":
                        # porte dans un mur (murs des deux côtés, sur une
                        # même ligne ou colonne), jamais dans un coin
                        def wall(px, py):
                            return (0 <= px < 75 and 0 <= py < 19
                                    and grid[py][px] in "-|")
                        horiz = wall(x - 1, y) and wall(x + 1, y)
                        vert = wall(x, y - 1) and wall(x, y + 1)
                        self.assertTrue(horiz != vert, (seed, x, y))

    def test_cave_single_zone_and_maze(self):
        g = nhgen.cave(60, 15, random.Random(3))
        self.assertEqual(len(nhgen.zones(g)), 1)
        self.assertGreater(sum(r.count(".") for r in g), 100)
        g = nhgen.maze(21, 9, random.Random(1))
        self.assertEqual(len(nhgen.zones(g)), 1)

    def test_populate_stairs_far_apart(self):
        g = nhgen.big_room(30, 8, random.Random(2), 0)
        out = nhgen.populate(g, random.Random(5), 3, 2, 1)
        kinds = [k for k, _x, _y, _v in out]
        self.assertEqual(kinds, ["stair", "stair"] + ["monster"] * 3
                         + ["object"] * 2 + ["trap"])
        (_k, ux, uy, _v), (_k2, dx, dy, _v2) = out[:2]
        dist = nhgen.distances(g, (ux, uy))
        self.assertEqual(dist[(dx, dy)], max(dist[p] for p in dist
                                             if g[p[1]][p[0]] == "."))
        self.assertEqual(len({(x, y) for _k, x, y, _v in out}), len(out))


class Wizard(unittest.TestCase):
    def run_wizard(self, kind, seed=1, w=75, h=19):
        ed = nhmapedit.Editor(None)
        ed.pick = lambda title, items, initial=None, **k: (
            kind if items[0][1] == "rooms" else
            initial if initial is not None else items[0][1])
        ed.prompt = lambda label, default="", *a: default
        return ed.level_wizard(w, h, random.Random(seed))

    def test_every_kind_gives_a_valid_level(self):
        for kind in ("rooms", "maze", "cave", "big"):
            for seed in range(3):
                lvl = self.run_wizard(kind, seed)
                self.assertEqual(errors(lvl), [], (kind, seed))
                stairs = sorted(e.value for e in lvl.entities
                                if e.kind == "stair")
                self.assertEqual(stairs, ["down", "up"])
                self.assertTrue(any(e.kind == "monster"
                                    for e in lvl.entities))
                # le Lua écrit se relit à l'identique
                again = nhlevel.parse_level(lvl.to_lua())[0]
                self.assertEqual(again.grid, lvl.grid)
                self.assertEqual(len(again.entities), len(lvl.entities))

    def test_too_small(self):
        self.assertIsNone(self.run_wizard("rooms", w=10, h=5))
