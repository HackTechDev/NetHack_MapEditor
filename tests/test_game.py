"""Retour du jeu : erreurs Lua de NetHack relues après un essai (t)."""

import os
import tempfile
import unittest

from tests.util import level

import nhmapedit
from nhlevel import Entity
from nhme_game import game_errors, screen_messages

# formats relevés dans NetHack 5.0 (#wizloaddes d'un fichier fautif)
PANICLOG = (
    '5.0.0 20261025 213111 1000 D: impossible Lua error: 5:nhme-x.lua '
    'Unknown trap type (line %d [string "(nhme-x.lua)"])\n'
    'stack traceback:\n'
    "\t[C]: in field 'trap'\n"
    '\t[string "(nhme-x.lua)"]:%d: in main chunk\n'
    '5.0.0 20261025 213132 1000 D: impossible luaL_loadbuffer: Error '
    'loading (nhme-y.lua): [string "(nhme-y.lua)"]:9: \')\' expected '
    "near ';'\n"
    "5.0.0 20261025 213134 1000 D: impossible Couldn't place lregion "
    "type 3!\n")
SCREEN = (
    "┌──────┐┌──────┐\n"
    "│Charger quel fichier lua de niveau ? nhme-x          ││┌───┬\n"
    "│Erreur Lua : 7:nhme-x.lua [string                    │││ . │\n"
    "│\"(nhme-x.lua)\"]:7: attempt to call a nil value >>    │││ ‡ │\n"
    "└──────┘││ ( │\n"
    "│ la carte                                             ││\n")


class Parsing(unittest.TestCase):
    def test_paniclog(self):
        self.assertEqual(game_errors(PANICLOG % (7, 7), "nhme-x"),
                         [(7, "Unknown trap type")])
        self.assertEqual(game_errors(PANICLOG % (7, 7), "nhme-y"),
                         [(9, "')' expected near ';'")])
        self.assertEqual(game_errors(PANICLOG, "nhme-z"), [])

    def test_screen(self):
        text = screen_messages(SCREEN)
        self.assertNotIn("la carte", text)
        self.assertEqual(game_errors(text, "nhme-x"),
                         [(7, "attempt to call a nil value")])


class Feedback(unittest.TestCase):
    def test_after_test_in_game(self):
        with tempfile.TemporaryDirectory() as d:
            open(os.path.join(d, "sysconf"), "w").close()
            log = os.path.join(d, "paniclog")
            with open(log, "w") as f:
                f.write("ancienne erreur sans rapport\n")
            ed = nhmapedit.Editor(None)
            ed.lvl = level(["....."] * 3)
            ed.lvl.entities = [Entity("trap", 3, 2, "pit"),
                               Entity("monster", 1, 1, "orc")]
            ed.path = os.path.join(d, "essai.lua")
            ed.hackdir, ed.launch = d, False
            shown = []
            ed.message_box = lambda title, text: shown.append(text)
            ed.test_in_game()
            with open(os.path.join(d, "nhme-essai.lua")) as f:
                lines = f.read().split("\n")
            n = 1 + next(i for i, ln in enumerate(lines) if "des.trap" in ln)
            ed.game_feedback()
            self.assertIn("aucune erreur", ed.msg)
            with open(log, "a") as f:
                f.write(PANICLOG.replace("nhme-x", "nhme-essai") % (n, n))
            ed.cx = ed.cy = 0
            self.assertEqual(ed.game_feedback(), [(n, "Unknown trap type")])
            self.assertEqual((ed.cx, ed.cy), (3, 2))
            self.assertIn("ligne %d : Unknown trap type" % n, shown[-1])
            self.assertIn("piège pit", shown[-1])


if __name__ == "__main__":
    unittest.main()
