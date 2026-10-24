"""Import et export de la carte seule."""

import os
import tempfile
import unittest

from tests.util import grid, level

import nhexport
import nhmapedit


class Text(unittest.TestCase):
    def test_import(self):
        lvl = nhexport.import_text("\n\n-----\n|...|\n---\n\n")
        self.assertEqual((lvl.w, lvl.h), (5, 3))
        self.assertEqual(grid(lvl), ["-----", "|...|", "---  "])

    def test_import_errors(self):
        with self.assertRaises(ValueError):
            nhexport.import_text("..?..")
        with self.assertRaises(ValueError):
            nhexport.import_text("." * 90)

    def test_export_roundtrip(self):
        lvl = level(["-----", "|.{.|", "-----"])
        back = nhexport.import_text(nhexport.export_text(lvl))
        self.assertEqual(grid(back), grid(lvl))

    def test_editor_open_and_export(self):
        with tempfile.TemporaryDirectory() as d:
            src = os.path.join(d, "carte.txt")
            with open(src, "w") as f:
                f.write("---\n|.|\n---\n")
            ed = nhmapedit.Editor(None)
            self.assertTrue(ed.open_file(src))
            self.assertEqual(ed.path, os.path.join(d, "carte.lua"))
            self.assertTrue(ed.modified)
            out = os.path.join(d, "copie.txt")
            self.assertTrue(ed.export(out))
            with open(out) as f:
                self.assertEqual(f.read(), "---\n|.|\n---\n")
            self.assertEqual(ed.path, os.path.join(d, "carte.lua"))


if __name__ == "__main__":
    unittest.main()
