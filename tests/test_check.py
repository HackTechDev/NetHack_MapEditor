"""Vérifications : connexité et règles de NetHack."""

import unittest

from tests.util import level

import nhcheck
import nhlevel
from nhlevel import Entity


def with_stairs(rows, up, down):
    lvl = level(rows)
    lvl.entities = [Entity("stair", up[0], up[1], "up"),
                    Entity("stair", down[0], down[1], "down")]
    return lvl


class Connectivity(unittest.TestCase):
    def test_connected(self):
        lvl = with_stairs(["-------", "|.....|", "-------"], (1, 1), (5, 1))
        self.assertEqual(nhcheck.connectivity(lvl), [])

    def test_blocked(self):
        lvl = with_stairs(["-------", "|..|..|", "-------"], (1, 1), (5, 1))
        msgs = nhcheck.connectivity(lvl)
        self.assertTrue(msgs[0].startswith("! Connexité"))

    def test_secret_door(self):
        lvl = with_stairs(["-------", "|..S..|", "-------"], (1, 1), (5, 1))
        msgs = nhcheck.connectivity(lvl)
        self.assertIn("passage secret", msgs[0])

    def test_water(self):
        lvl = with_stairs(["-------", "|..W..|", "-------"], (1, 1), (5, 1))
        msgs = nhcheck.connectivity(lvl)
        self.assertIn("eau", msgs[0])

    def test_no_diagonal_through_door(self):
        # la seule sortie est en diagonale depuis la porte : interdit
        lvl = with_stairs(["----.", "|..+-", "-----"], (1, 1), (4, 0))
        msgs = nhcheck.connectivity(lvl)
        self.assertTrue(msgs[0].startswith("! Connexité"))
        lvl.entities.append(Entity("door", 3, 1, "nodoor"))
        self.assertFalse(any(m.startswith("! Connexité")
                             for m in nhcheck.connectivity(lvl)))

    def test_closed_zone(self):
        lvl = with_stairs(["----------", "|...||...|", "----------"],
                          (1, 1), (2, 1))
        msgs = nhcheck.connectivity(lvl)
        self.assertEqual(len(msgs), 1)
        self.assertIn("Zone fermée de 3 case(s)", msgs[0])


class Rules(unittest.TestCase):
    def messages(self, lvl):
        return [m for m in nhcheck.rules(lvl) if m[0] in "!?"]

    def test_door_in_corner(self):
        lvl = level(["+---", "|...", "|..."])
        self.assertIn("! Porte en (0,0) dans un coin de mur.",
                      self.messages(lvl))

    def test_framed_door_is_fine(self):
        lvl = level(["--+--", "|...|"])
        self.assertEqual(self.messages(lvl), [])

    def test_stair_in_water(self):
        lvl = level(["...", ".W."])
        lvl.entities = [Entity("stair", 1, 1, "down")]
        self.assertTrue(any("dans 'W'" in m for m in self.messages(lvl)))

    def test_altar_needs_temple_region(self):
        src = ('des.map([[\n-----\n|...|\n-----\n]]);\n'
               'des.altar({ x = 2, y = 1, align = "law" });\n')
        lvl = nhlevel.parse_level(src)[0]
        self.assertTrue(any("temple" in m for m in self.messages(lvl)))
        src += 'des.region({ region = {1,1,3,1}, type = "temple" });\n'
        lvl = nhlevel.parse_level(src)[0]
        self.assertFalse(any("temple" in m for m in self.messages(lvl)))

    def test_terrain_entity_opens_a_path(self):
        lvl = with_stairs(["..|.."], (0, 0), (4, 0))
        self.assertTrue(any(m.startswith("! Connexité")
                            for m in nhcheck.check(lvl)))
        lvl.entities.append(Entity("terrain", 2, 0, "."))
        self.assertFalse(any(m.startswith("! Connexité")
                             for m in nhcheck.check(lvl)))
        self.assertEqual(self.messages(lvl), [])

    def test_drawbridge_needs_water(self):
        lvl = level(["|}.", "|.."])
        lvl.entities = [Entity("drawbridge", 1, 0, "west")]
        self.assertEqual(self.messages(lvl), [])
        lvl.entities[0].y = 1
        self.assertTrue(any("Pont-levis" in m for m in self.messages(lvl)))

    def test_shop_needs_one_door(self):
        rows = ["-----", "|...|", "|...+", "|...|", "--+--"]
        lvl = level(rows)
        lvl.regions = [nhlevel.Region("region", (1, 1, 3, 3),
                                      {"type": "tool shop", "lit": 1})]
        out = nhcheck.region_problems(lvl)
        self.assertEqual(len(out), 1)
        self.assertIn("2 porte(s) et 0 ouverture(s)", out[0])
        lvl.grid[4][2] = "-"
        self.assertEqual(nhcheck.region_problems(lvl), [])
        lvl.grid[0][2] = "."            # brèche dans le mur
        self.assertIn("1 porte(s) et 1 ouverture(s)",
                      nhcheck.region_problems(lvl)[0])

    def test_region_outside_level(self):
        lvl = level(["....."])
        lvl.pos = (10, 5)
        lvl.regions = [
            nhlevel.Region("teleport_region", (1, 0, 79, 20)),   # rognée
            nhlevel.Region("levregion", (85, 0, 90, 3),
                           {"type": "branch", "region_islev": 1})]
        out = nhcheck.region_problems(lvl)
        self.assertEqual(len(out), 1)
        self.assertIn("entièrement hors du niveau", out[0])

    def test_enclosed_entities(self):
        lvl = with_stairs(["-------", "|..|..|", "-------"], (1, 1), (2, 1))
        lvl.entities.append(Entity("object", 5, 1, "diamond"))
        out = nhcheck.enclosed(lvl)
        self.assertEqual(len(out), 1)
        self.assertIn("objet diamond en (5,1)", out[0])
        lvl.grid[1][3] = "S"            # passage secret : atteignable
        self.assertEqual(nhcheck.enclosed(lvl), [])

    def test_entity_outside_map(self):
        lvl = level(["..."])
        lvl.entities = [Entity("stair", 5, 0, "up")]
        self.assertTrue(any("hors de la carte" in m
                            for m in self.messages(lvl)))


@unittest.skipUnless(nhcheck.find_lua(), "pas d'interpréteur Lua "
                     "(NHMAPEDIT_LUA)")
class RealLua(unittest.TestCase):
    def run_lua(self, text):
        import json
        import os
        from tests.util import ROOT
        with open(os.path.join(ROOT, "nhdata.json"), encoding="utf-8") as f:
            data = json.load(f)
        return nhcheck.lua_check(text, nhcheck.find_lua(), data)

    def test_valid_level(self):
        text = ('des.level_flags("mazelevel", "noflip")\n'
                'des.map([[\n...\n]])\n'
                'des.monster("aligned cleric", 0, 0)\n'
                'des.object("wishing", 1, 0)\n'
                'des.object({ id = "walking shoes", x = 2, y = 0 })\n'
                'if percent(50) then des.trap("hole", 2, 0) end\n')
        self.assertEqual(self.run_lua(text), [])

    def test_errors(self):
        text = ('des.level_flags("nofilp")\n'
                'des.map([[\n...\n]])\n'
                'des.monster("jackall", 0, 0)\n'
                'des.object({ id = "dagger", x = 1, y = 0, spee = 2 })\n'
                'des.dorr("open", 2, 0)\n'
                'frobnicate()\n')
        msgs = self.run_lua(text)
        self.assertEqual([m.split(" : ")[0] for m in msgs], [
            "! Lua, ligne 1", "! Lua, ligne 5", "? Lua, ligne 6",
            "! Lua, ligne 7", "! Lua, ligne 8"])

    def test_syntax_error(self):
        msgs = self.run_lua("des.map([[\n.\n]]\ndes.monster(")
        self.assertTrue(msgs[0].startswith("! Lua, ligne"))


if __name__ == "__main__":
    unittest.main()
