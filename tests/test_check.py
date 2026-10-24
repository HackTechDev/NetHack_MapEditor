"""Vérifications : connexité et règles de NetHack."""

import unittest

from tests.util import level

import nhcheck
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


if __name__ == "__main__":
    unittest.main()
