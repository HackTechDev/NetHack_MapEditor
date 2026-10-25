"""Modèle de niveau : lecture et écriture du Lua."""

import os
import subprocess
import tempfile
import unittest

from tests.util import DAT, dat_files, level, luac, grid

import nhlevel
from nhlevel import Entity


# Sans level_init, l'éditeur en ajoute un à l'enregistrement
INIT = 'des.level_init({ style = "solidfill", fg = " " });\n'


class RoundTrip(unittest.TestCase):
    @unittest.skipUnless(dat_files(), "niveaux de NetHack absents (%s)" % DAT)
    def test_dat_identical(self):
        """Ouvrir puis enregistrer sans modification ne change rien."""
        n = 0
        for f in dat_files():
            with open(f, encoding="utf-8") as fh:
                src = fh.read()
            try:
                lvl = nhlevel.parse_level(src)[0]
            except ValueError:
                continue            # pas de des.map (dungeon.lua, nhlib…)
            with self.subTest(f=os.path.basename(f)):
                self.assertEqual(lvl.to_lua(), src)
            n += 1
        self.assertGreater(n, 80)

    @unittest.skipUnless(dat_files(), "niveaux de NetHack absents")
    def test_dat_regenerated_reparses(self):
        """Chaque entité régénérée se relit à l'identique."""
        for f in dat_files():
            with open(f, encoding="utf-8") as fh:
                src = fh.read()
            try:
                lvl = nhlevel.parse_level(src)[0]
            except ValueError:
                continue
            for e in lvl.entities:
                code = e.to_lua()
                call = nhlevel.scan_des_calls(code)[0]
                vals = nhlevel._parse_args(call["args"], 0,
                                           len(call["args"]))[0]
                again = nhlevel._entity_from_call(call["name"], vals)
                self.assertEqual(again.to_lua(), code)


class Generation(unittest.TestCase):
    def new_level(self):
        lvl = level(["-----", "|...|", "|...|", "-----"])
        lvl.flags = ["mazelevel", "noflip"]
        lvl.entities = [
            Entity("stair", 1, 1, "up"),
            Entity("monster", 2, 1, "jackal", {"peaceful": 1}),
            Entity("object", 3, 2, "!"),
            Entity("monster", 3, 1, None),
            Entity("object", 1, 2, "chest", {"contents": nhlevel.Contents(
                [Entity("object", None, None, "dagger", {"spe": 2})])}),
            Entity("engraving", 2, 2, "Elbereth", {"type": "burn"}),
        ]
        return lvl

    def test_new_level_parses_back(self):
        lvl = self.new_level()
        text = lvl.to_lua("essai")
        back = nhlevel.parse_level(text)[0]
        self.assertEqual(grid(back), grid(lvl))
        self.assertEqual(back.flags, lvl.flags)
        self.assertEqual(sorted(e.to_lua() for e in back.entities),
                         sorted(e.to_lua() for e in lvl.entities))

    def test_contents_written_as_function(self):
        e = self.new_level().entities[4]
        self.assertEqual(e.to_lua(), "\n".join([
            'des.object({ x = 1, y = 2, id = "chest", contents = function()',
            '   des.object({ id = "dagger", spe = 2 });',
            'end });']))

    def test_non_literal_contents_kept_verbatim(self):
        src = (INIT + 'des.map([[\n...\n]]);\n'
               'des.object({ id = "statue", x = 1, y = 0, contents = '
               'function() if percent(50) then des.object() end end });\n')
        lvl = nhlevel.parse_level(src)[0]
        self.assertEqual(lvl.entities, [])
        self.assertEqual(lvl.to_lua(), src)

    def test_modified_entity_only(self):
        src = (INIT + 'des.map([[\n...\n]]);\n'
               'des.monster("jackal", 0, 0)   -- commentaire\n'
               'des.object("dagger", 1, 0)\n')
        lvl = nhlevel.parse_level(src)[0]
        lvl.entities[1].value = "long sword"
        self.assertEqual(lvl.to_lua(), src.replace(
            'des.object("dagger", 1, 0)', 'des.object("long sword", 1, 0);'))

    def test_more_entities(self):
        calls = ['des.gold(100, 1, 1);', 'des.gold({ x = 2, y = 1 });',
                 'des.grave(0, 0, "Ci-gît");',
                 'des.drawbridge({ x = 2, y = 0, dir = "east", '
                 'state = "closed" });',
                 'des.feature("fountain", 3, 0);',
                 'des.terrain(2, 1, "L");',
                 'des.terrain({ x = 0, y = 1, typ = "W", lit = 1 });']
        src = INIT + 'des.map([[\n....\n....\n]]);\n' + "\n".join(
            calls) + "\n"
        lvl = nhlevel.parse_level(src)[0]
        self.assertEqual([e.kind for e in lvl.entities], [
            "gold", "gold", "grave", "drawbridge", "feature", "terrain",
            "terrain"])
        self.assertEqual(lvl.to_lua(), src)
        self.assertEqual([e.to_lua() for e in lvl.entities], calls)
        # autres formes acceptées par NetHack
        for call, kind, xy, value in [
                ('des.gold(7, {3, 1})', "gold", (3, 1), 7),
                ('des.feature("sink", {0, 1})', "feature", (0, 1), "sink"),
                ('des.terrain({3, 1}, "-")', "terrain", (3, 1), "-")]:
            e = nhlevel.parse_level(INIT + 'des.map([[\n....\n]]);\n'
                                    + call)[0].entities[0]
            self.assertEqual((e.kind, (e.x, e.y), e.value), (kind, xy, value))

    @unittest.skipUnless(luac(), "luac absent (NHMAPEDIT_LUAC)")
    def test_luac_accepts_output(self):
        with tempfile.NamedTemporaryFile("w", suffix=".lua",
                                         delete=False) as f:
            f.write(self.new_level().to_lua("essai"))
        try:
            r = subprocess.run([luac(), "-p", f.name], capture_output=True,
                               text=True)
            self.assertEqual(r.returncode, 0, r.stderr)
        finally:
            os.unlink(f.name)


class Geometry(unittest.TestCase):
    def test_origin_center(self):
        lvl = level(["." * 11] * 5)
        lvl.halign, lvl.valign = "center", "center"
        x, y = lvl.origin()
        # coordonnées impaires, comme lspo_map()
        self.assertEqual((x % 2, y % 2), (1, 1))
        self.assertEqual(x, 35)    # 2 + (78 - 2 - 11) / 2 = 34 -> 35

    def test_insert_delete_row_moves_entities(self):
        lvl = level(["...", "...", "..."])
        lvl.entities = [Entity("stair", 1, 2, "down")]
        lvl.insert_row(1)
        self.assertEqual(lvl.h, 4)
        self.assertEqual(lvl.entities[0].y, 3)
        lvl.delete_row(0)
        self.assertEqual(lvl.entities[0].y, 2)
        lvl.insert_col(0)
        self.assertEqual((lvl.w, lvl.entities[0].x), (4, 2))

    def test_flips(self):
        lvl = level(["..."])
        self.assertEqual(lvl.allowed_flips(), 3)
        lvl.flags = ["noflipx"]
        self.assertEqual(lvl.allowed_flips(), 1)
        lvl.flags = ["noflip"]
        self.assertEqual(lvl.allowed_flips(), 0)


if __name__ == "__main__":
    unittest.main()
