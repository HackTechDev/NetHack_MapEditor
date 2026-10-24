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


class Image(unittest.TestCase):
    def test_svg(self):
        text = nhexport.svg([[("-", "CLR_GRAY"), ("<", "CLR_YELLOW", None)],
                             [("&", "CLR_RED", "#7a3e8a"), (" ", "CLR_GRAY")]],
                            "essai")
        self.assertTrue(text.startswith("<svg"))
        self.assertIn("&amp;", text)
        self.assertIn('fill="#7a3e8a"', text)
        self.assertEqual(text.count("<text"), 3)

    def test_editor_export_svg(self):
        with tempfile.TemporaryDirectory() as d:
            ed = nhmapedit.Editor(None)
            ed.lvl = level(["-----", "|.<.|", "-----"])
            out = os.path.join(d, "carte.svg")
            self.assertTrue(ed.export(out))
            with open(out) as f:
                self.assertIn("&lt;", f.read())


if __name__ == "__main__":
    unittest.main()
