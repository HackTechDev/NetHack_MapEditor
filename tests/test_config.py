"""Fichier de configuration (nhconfig) et son effet sur l'éditeur."""

import os
import tempfile
import unittest

import tests.util  # noqa: F401  (chemin du projet)

import nhconfig
import nhmapedit


def load(text):
    with tempfile.TemporaryDirectory() as d:
        path = os.path.join(d, "config")
        with open(path, "w", encoding="utf-8") as f:
            f.write(text)
        return nhconfig.load(path)


class Load(unittest.TestCase):
    def test_absent(self):
        self.assertEqual(nhconfig.load("/nexiste/pas"), ({}, []))

    def test_values(self):
        cfg, errs = load("""
[jeu]
repertoire = ~/jeu
[editeur]
taille = 40x12   ; commentaire
regles = non
entites = oui
unicode = non
sauvegarde = 0
langue = en
[couleurs]
} = bright_blue
couloir = yellow
roche = CLR_RED
[touches]
z = u
ctrl-z = u
espace = .
""")
        self.assertEqual(errs, [])
        self.assertEqual(cfg["hackdir"], os.path.expanduser("~/jeu"))
        self.assertEqual(cfg["size"], (40, 12))
        self.assertFalse(cfg["rulers"])
        self.assertTrue(cfg["entities"])
        self.assertFalse(cfg["unicode"])
        self.assertEqual(cfg["autosave"], 0)
        self.assertEqual(cfg["lang"], "en")
        self.assertEqual(cfg["colors"], {"}": "CLR_BRIGHT_BLUE",
                                         "#": "CLR_YELLOW",
                                         " ": "CLR_RED"})
        self.assertEqual(cfg["keys"], {"z": "u", "\x1a": "u", " ": "."})

    def test_errors(self):
        cfg, errs = load("""
[editeur]
taille = grand
inconnue = 1
[couleurs]
} = fuchsia
[autre]
""")
        self.assertEqual(cfg, {})
        self.assertEqual(len(errs), 4)
        self.assertTrue(errs[0].startswith("[editeur] taille"))

    def test_syntax_error(self):
        cfg, errs = load("pas de section\n")
        self.assertEqual(cfg, {})
        self.assertEqual(len(errs), 1)


class Editor(unittest.TestCase):
    def test_applied(self):
        ed = nhmapedit.Editor(None, config={
            "size": (30, 10), "rulers": False, "autosave": 5,
            "keys": {"z": "u"}, "hackdir": "/nexiste/pas"})
        self.assertEqual((ed.lvl.w, ed.lvl.h), (30, 10))
        self.assertFalse(ed.rulers)
        self.assertEqual(ed.autosave_delay, 5)
        self.assertEqual(ed.keymap, {"z": "u"})


if __name__ == "__main__":
    unittest.main()
