"""dungeon.lua et themerms.lua : modifications ciblées du texte."""

import os
import unittest

from tests.util import DAT

import nhdungeon
import nhtheme

DUNGEON = os.path.join(DAT, "dungeon.lua")
THEMES = os.path.join(DAT, "themerms.lua")


def read(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


@unittest.skipUnless(os.path.exists(DUNGEON), "dungeon.lua absent")
class Dungeon(unittest.TestCase):
    def setUp(self):
        self.src = read(DUNGEON)
        self.df = nhdungeon.DungeonFile(self.src)

    def test_read(self):
        names = [self.df.dungeon_name(d) for d in self.df.dungeons()]
        self.assertEqual(names[0], "The Dungeons of Doom")
        self.assertIn("castle", self.df.all_level_names())

    def test_add_then_delete_restores_file(self):
        fields = {"name": "essai", "base": 3, "range": 2,
                  "flags": ["town"]}
        self.assertEqual(nhdungeon.check_level(self.df, fields, 0), [])
        df = self.df.add_level(0, fields)
        levels = df.levels(df.dungeons()[0])
        self.assertEqual(levels[-1].py(), {"name": "essai", "base": 3,
                                           "range": 2, "flags": "town"})
        df = df.delete_level(0, len(levels) - 1)
        self.assertEqual(df.text, self.src)

    def test_add_after_trailing_comma(self):
        last = len(self.df.dungeons()) - 1
        df = self.df.add_level(last, {"name": "essai", "base": 3})
        self.assertIn("essai", df.all_level_names())

    def test_checks(self):
        errs = nhdungeon.check_level(
            self.df, {"name": "oracle", "bonetag": "AB"}, 0)
        self.assertEqual(len(errs), 3)      # doublon, base, bonetag
        errs = nhdungeon.check_level(
            self.df, {"name": "nom-tres-long", "base": 1, "nlevels": 3}, 0)
        self.assertEqual(len(errs), 1)


@unittest.skipUnless(os.path.exists(THEMES), "themerms.lua absent")
class Themes(unittest.TestCase):
    def setUp(self):
        self.src = read(THEMES)
        self.tf = nhtheme.ThemeFile(self.src)

    def test_rooms_with_maps(self):
        names = [n for _, (n, _) in self.tf.editable()]
        self.assertIn("L-shaped", names)
        self.assertNotIn("Fake Delphi", names)     # des.room seulement

    def test_replace_same_map_is_identity(self):
        m = self.tf.map_text("Cross", 0)
        self.assertEqual(self.tf.replace_map("Cross", 0, m), self.src)

    def test_add_room(self):
        text = self.tf.add_room("Essai", "-----\n|...|\n-----")
        tf = nhtheme.ThemeFile(text)
        self.assertEqual(tf.map_text("Essai", 0), "-----\n|...|\n-----")
        self.assertIn("filler_region(1,1)", text)


if __name__ == "__main__":
    unittest.main()
