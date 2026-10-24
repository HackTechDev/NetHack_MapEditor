"""Import et export de la carte seule."""

import os
import tempfile
import unittest

from tests.util import grid, level

import nhexport
import nhlevel
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


class Templates(unittest.TestCase):
    def test_shipped_templates_load(self):
        import nhme_common
        found = nhexport.list_templates(nhme_common.TEMPLATE_DIRS[:1])
        self.assertGreaterEqual(len(found), 5)
        for title, desc, path in found:
            g, ents = nhexport.load_template(path)
            self.assertTrue(g and desc, path)
            self.assertTrue(all(e.origin is None for e in ents))

    def test_save_and_paste(self):
        import nhme_tools
        with tempfile.TemporaryDirectory() as d:
            ed = nhmapedit.Editor(None)
            ed.lvl = level(["---", "|.|", "---"])
            ed.lvl.entities = [nhlevel.Entity("stair", 1, 1, "up")]
            ed.copy((0, 0), (2, 2))
            ed.prompt = lambda *a, **k: "Ma salle"
            old = nhme_tools.TEMPLATE_DIRS
            nhme_tools.TEMPLATE_DIRS = [d]
            try:
                ed.save_template()
                path = os.path.join(d, "ma-salle.lua")
                self.assertTrue(os.path.exists(path))
                found = nhexport.list_templates([d])
                self.assertEqual(found[0][0], "Ma salle")
                ed.pick = lambda *a, **k: path
                ed.lvl = level(["     "] * 4)
                ed.templates()
                ed.cx, ed.cy = 1, 1
                ed.apply()
            finally:
                nhme_tools.TEMPLATE_DIRS = old
            self.assertEqual(grid(ed.lvl), ["     ", " --- ", " |.| ",
                                            " --- "])
            self.assertEqual((ed.lvl.entities[0].x, ed.lvl.entities[0].y),
                             (2, 2))


if __name__ == "__main__":
    unittest.main()
