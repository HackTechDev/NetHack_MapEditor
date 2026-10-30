"""Thèmes et style des menus, repris du lanceur NetHack."""

import unittest

import tests.util  # noqa: F401  (chemin du projet)

import nhme_theme
import nhmapedit


class Theme(unittest.TestCase):
    def test_choice(self):
        name = nhme_theme.theme_name
        self.assertEqual(name("auto", "cyber"), "cyber")
        self.assertEqual(name("auto", None), "classique")
        self.assertEqual(name("sobre", "cyber"), "sobre")
        self.assertEqual(name("inconnu", None), "classique")

    def test_editor_theme(self):
        ed = nhmapedit.Editor(None, config={"theme": "cyber"})
        self.assertEqual(ed.ui_theme(), "cyber")
        # tests/util.py : jeu en anglais, donc thème classique en auto
        self.assertEqual(nhmapedit.Editor(None).ui_theme(), "classique")

    def test_styles(self):
        st = nhme_theme.curses_styles("cyber", {})
        for elem in ("titre", "separateur", "groupe", "numero", "touche",
                     "selection", "description", "aide", "message"):
            self.assertIn(elem, st)
        self.assertEqual(set(nhme_theme.THEMES["cyber"]),
                         set(nhme_theme.THEMES["classique"]) | {"titre"})

    def test_lines(self):
        self.assertEqual(nhme_theme.group_line("Outils", 16),
                         "── Outils ──────")
        self.assertEqual(nhme_theme.group_line("Outils", 12, False),
                         "-- Outils --")
        self.assertEqual(nhme_theme.dotted(" ?:aide  m:entité   q:quitter"),
                         "?:aide · m:entité · q:quitter")


if __name__ == "__main__":
    unittest.main()
