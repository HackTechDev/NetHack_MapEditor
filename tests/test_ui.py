"""Interface : l'éditeur piloté au clavier dans un pseudo-terminal."""

import os
import select
import struct
import sys
import tempfile
import time
import unittest

from tests.util import ROOT

import nhlevel

try:
    import fcntl
    import pty
    import termios
except ImportError:             # Windows
    pty = None

RIGHT, DOWN = "\x1bOC", "\x1bOB"


def drive(args, keys, rows=30, cols=110, delay=0.15, env=None):
    """Lance nhmapedit.py, tape les touches, puis le tue. Renvoie la
    sortie brute du terminal."""
    pid, fd = pty.fork()
    if pid == 0:
        os.environ["TERM"] = "xterm-256color"
        # pas de configuration personnelle pendant les tests
        os.environ["NHMAPEDIT_CONFIG"] = os.devnull
        os.environ.update(env or {})
        os.execvp(sys.executable, [sys.executable,
                                   os.path.join(ROOT, "nhmapedit.py")]
                  + args)
    fcntl.ioctl(fd, termios.TIOCSWINSZ, struct.pack("HHHH", rows, cols, 0, 0))
    out = b""

    def drain(t):
        nonlocal out
        end = time.time() + t
        while time.time() < end:
            if select.select([fd], [], [], 0.05)[0]:
                try:
                    out += os.read(fd, 65536)
                except OSError:
                    return

    drain(1.0)
    for k in keys:
        os.write(fd, k.encode())
        drain(delay)
    os.kill(pid, 9)
    os.waitpid(pid, 0)
    os.close(fd)
    return out.decode("utf-8", "replace")


@unittest.skipIf(pty is None, "pseudo-terminal indisponible")
class Ui(unittest.TestCase):
    def test_draw_room_place_stair_save(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "essai.lua")
            keys = (["5", " "] + [RIGHT] * 4 + [DOWN] * 3 + [" "]
                    # escalier descendant au centre de la salle
                    + ["\x1bOD", "\x1bOD", "\x1bOA", "m", "\r", DOWN, "\r",
                       "s"])
            out = drive([path], keys, env={"HOME": d})
            self.assertNotIn("Traceback", out)
            with open(path, encoding="utf-8") as f:
                lvl = nhlevel.parse_level(f.read())[0]
            rows = ["".join(r[:5]) for r in lvl.grid[:4]]
            self.assertEqual(rows, ["-----", "|...|", "|...|", "-----"])
            self.assertEqual([(e.kind, e.x, e.y, e.value)
                              for e in lvl.entities],
                             [("stair", 2, 2, "down")])

    def test_config_keys_and_size(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "essai.lua")
            conf = os.path.join(d, "config")
            with open(conf, "w", encoding="utf-8") as f:
                f.write("[editeur]\ntaille = 12x5\n[touches]\nz = s\n")
            out = drive([path], ["z"], env={"HOME": d,
                                            "NHMAPEDIT_CONFIG": conf})
            self.assertNotIn("Traceback", out)
            with open(path, encoding="utf-8") as f:
                lvl = nhlevel.parse_level(f.read())[0]
            self.assertEqual((lvl.w, lvl.h), (12, 5))


if __name__ == "__main__":
    unittest.main()
