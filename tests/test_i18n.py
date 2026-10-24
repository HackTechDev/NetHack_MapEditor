"""Traduction anglaise : catalogue complet et cohérent, langue choisie."""

import ast
import glob
import os
import re
import subprocess
import sys
import unittest

from tests.util import ROOT

import nhi18n
from nhi18n_en import EN

FORMAT = re.compile(r"%[-\d.]*[sdr%]")


def keys():
    """Textes passés à _() dans les modules du projet : {texte: lieu}."""
    out = {}
    for path in sorted(glob.glob(os.path.join(ROOT, "*.py"))):
        with open(path, encoding="utf-8") as f:
            tree = ast.parse(f.read())
        for n in ast.walk(tree):
            if (isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
                    and n.func.id == "_" and n.args
                    and isinstance(n.args[0], ast.Constant)):
                out.setdefault(n.args[0].value, "%s:%d" % (
                    os.path.basename(path), n.lineno))
    # _(__doc__.strip()) : l'usage affiché par --help
    with open(os.path.join(ROOT, "nhmapedit.py"), encoding="utf-8") as f:
        out[ast.get_docstring(ast.parse(f.read()), clean=False).strip()] = \
            "nhmapedit.py"
    return out


class Catalog(unittest.TestCase):
    def test_every_text_translated(self):
        missing = ["%s %r" % (where, k) for k, where in keys().items()
                   if k not in EN]
        self.assertEqual(missing, [])

    def test_no_stale_entry(self):
        used = set(keys())
        self.assertEqual(sorted(k for k in EN if k not in used), [])

    def test_same_placeholders(self):
        bad = [k for k, v in EN.items()
               if FORMAT.findall(k) != FORMAT.findall(v)]
        self.assertEqual(bad, [])


class Detect(unittest.TestCase):
    def detect(self, **env):
        old = dict(os.environ)
        try:
            for var in ("NHMAPEDIT_LANG", "LANGUAGE", "LC_ALL",
                        "LC_MESSAGES", "LANG"):
                os.environ.pop(var, None)
            os.environ["NHMAPEDIT_CONFIG"] = os.devnull
            os.environ.update(env)
            return nhi18n.detect()
        finally:
            os.environ.clear()
            os.environ.update(old)

    def test_locale(self):
        self.assertEqual(self.detect(LANG="fr_FR.UTF-8"), "fr")
        self.assertEqual(self.detect(LANG="en_US.UTF-8"), "en")
        self.assertEqual(self.detect(LANG="de_DE.UTF-8"), "en")
        self.assertEqual(self.detect(LANG="en_US.UTF-8",
                                     LC_ALL="fr_CA.UTF-8"), "fr")

    def test_override(self):
        self.assertEqual(self.detect(LANG="fr_FR.UTF-8",
                                     NHMAPEDIT_LANG="en"), "en")


class English(unittest.TestCase):
    def run_en(self, code):
        env = dict(os.environ, NHMAPEDIT_LANG="en")
        return subprocess.run([sys.executable, "-c", code], cwd=ROOT,
                              env=env, capture_output=True, text=True,
                              check=True).stdout

    def test_messages(self):
        out = self.run_en(
            "import nhmapedit, nhcheck, nhlevel\n"
            "ed = nhmapedit.Editor(None)\n"
            "print(ed.msg)\n"
            "print(nhmapedit.TOOL_NAME['fill'])\n"
            "print(nhcheck.check(nhlevel.Level(3, 3))[0])\n"
            "print(nhmapedit.HELP.split(chr(10))[0])\n")
        self.assertEqual(out.split("\n")[:4], [
            "Welcome! '?' for help.", "Flood fill",
            "- NetHack may flip this level on load (both ways): f for a "
            "preview, noflip flag to prevent it.",
            "nhmapedit — NetHack map editor (the .lua files of dat/)"])


if __name__ == "__main__":
    unittest.main()
