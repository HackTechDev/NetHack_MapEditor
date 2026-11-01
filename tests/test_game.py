"""Retour du jeu : erreurs Lua de NetHack relues après un essai (t)."""

import os
import shlex
import tempfile
import unittest

from tests.util import level

import nhmapedit
import nhme_game
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


class Lxd(unittest.TestCase):
    """Cible « serveur LXD » de la touche t (lxc et ssh simulés)."""

    def editor(self, answers):
        ed = nhmapedit.Editor(None, config={"lxd_ssh": "ssh -p 2222 x@h"})
        ed.lvl = level(["....."] * 3)
        ed.lvl.entities = [Entity("trap", 3, 2, "pit")]
        ed.path = "/ailleurs/ma carte.lua"
        ed.draw = lambda: None
        self.calls, self.shown = [], []
        ed.message_box = lambda title, text: self.shown.append(text)

        def lxc(*args, input=None, timeout=30, remote=None):
            self.calls.append((args, input, remote))
            return answers.pop(0)
        ed.lxc = lxc
        return ed

    def test_choice_asks_address(self):
        ed = self.editor([("autre,STOPPED\nnethack,RUNNING\n", "")])
        old = os.environ.pop("NHMAPEDIT_LXD")
        try:
            ed.pick = lambda title, items, initial=None, **kw: "lxd"
            answers = ["192.168.1.20", "admin"]
            ed.prompt = lambda *a, **k: answers.pop(0)
            target = ed.choose_test_target()
            self.assertEqual(target, {"box": "nethack",
                                      "host": "192.168.1.20",
                                      "user": "admin"})
            self.assertEqual(self.calls[0][2], ("192.168.1.20", "admin"))
            # retenue : plus de question
            self.assertIs(ed.choose_test_target(), target)
            # localhost : lxc sur ce poste, sans compte SSH
            answers[:] = ["localhost"]
            ed.lxc = lambda *a, **k: ("nethack,RUNNING\n", "")
            self.assertEqual(ed.choose_test_target(always=True),
                             {"box": "nethack", "host": None, "user": None})
            # serveur injoignable : message, pas de cible
            answers[:] = ["10.0.0.9", "admin"]
            ed.lxc = lambda *a, **k: (None, "ssh: connect to host 10.0.0.9 "
                                            "port 22: Connection refused")
            self.assertIsNone(ed.choose_test_target(always=True))
            self.assertIn("Connection refused", ed.msg)
            os.environ["NHMAPEDIT_LXD"] = "aucun"
            ed.test_target = None
            self.assertEqual(ed.choose_test_target(), "local")
        finally:
            os.environ["NHMAPEDIT_LXD"] = old

    def test_remote_command(self):
        ed = nhmapedit.Editor(None)
        seen = []

        class R:
            returncode, stdout, stderr = 0, "ok\n", ""

        def run(cmd, **kw):
            seen.append((cmd, kw.get("input")))
            return R()
        real = nhme_game.subprocess.run
        nhme_game.subprocess.run = run
        try:
            ed.lxc("exec", "-T", "nethack", "--", "sh", "-c", "echo 'a b'",
                   input="carte", remote=("192.168.1.20", "admin"))
            ed.lxc("list")
        finally:
            nhme_game.subprocess.run = real
        cmd, text = seen[0]
        self.assertEqual(cmd[:6], ["ssh", "-o", "BatchMode=yes", "-o",
                                   "ConnectTimeout=10", "admin@192.168.1.20"])
        self.assertEqual(shlex.split(cmd[6]), ["lxc", "exec", "-T",
                                               "nethack", "--", "sh", "-c",
                                               "echo 'a b'"])
        self.assertEqual(text, "carte")
        self.assertEqual(seen[1][0], ["lxc", "list"])

    def test_push_and_feedback(self):
        ed = self.editor([("12\n-aucun-\n", ""),
                          (PANICLOG.replace("nhme-x", "nhme-ma_carte")
                           % (7, 7), "")])
        ed.test_target = {"box": "nethack", "host": "192.168.1.20",
                          "user": "admin"}
        ed.test_in_game()
        args, text, remote = self.calls[0]
        self.assertEqual(remote, ("192.168.1.20", "admin"))
        self.assertEqual(args[:6], ("exec", "-T", "nethack", "--", "sh",
                                    "-c"))
        self.assertEqual(args[-2:], ("/opt/nethack/chroot/home/util01/"
                                     "nethack500", "nhme-ma_carte.lua"))
        self.assertIn("mv -fT", args[6])        # pas de lien suivi
        self.assertIn('"noflip");', text)
        self.assertIn("ssh -p 2222 x@h", self.shown[0])
        self.assertIn("#wizloaddes", self.shown[0])
        self.assertIn("WIZARDS=-aucun-", self.shown[0])
        self.assertIn("nethack sur 192.168.1.20", self.shown[0])
        # le paniclog du serveur est relu après les 12 octets déjà là
        self.assertEqual(ed.game_feedback(), [(7, "Unknown trap type")])
        self.assertEqual(self.calls[1][0][-1], "13")
        self.assertEqual(self.calls[1][2], ("192.168.1.20", "admin"))
        # deuxième essai : message seul, sans les consignes (la seconde
        # fenêtre est celle du retour du jeu)
        ed.lxc = lambda *a, **k: ("0\nutildebug\n", "")
        ed.test_in_game()
        self.assertEqual(len(self.shown), 2)
        self.assertIn("nhme-ma_carte", ed.msg)

    def test_errors_and_ssh(self):
        ed = self.editor([(None, "Error: Instance not found")])
        local = {"box": "nethack", "host": None, "user": None}
        ed.test_in_lxd(local)
        self.assertIn("Instance not found", ed.msg)
        self.assertIsNone(ed.last_test)
        del ed.config["lxd_ssh"]
        ed.lxc = lambda *a, **k: ("tcp:192.168.1.228:2222\n", "")
        self.assertEqual(ed.lxd_ssh_command(local),
                         "ssh -p 2222 nethack@192.168.1.228")
        ed.lxc = lambda *a, **k: ("tcp:[::]:22\n", "")
        self.assertEqual(ed.lxd_ssh_command(local), "ssh nethack@localhost")
        # proxy ouvert sur toutes les adresses d'un serveur distant
        self.assertEqual(ed.lxd_ssh_command(dict(local, host="10.0.0.5")),
                         "ssh nethack@10.0.0.5")

if __name__ == "__main__":
    unittest.main()
