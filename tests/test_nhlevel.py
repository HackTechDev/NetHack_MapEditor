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

    def test_regions(self):
        calls = ['des.region({ region = { 1, 0, 3, 1 }, lit = 1, '
                 'type = "temple", filled = 1 });',
                 'des.region(selection.area(0,0,2,1), "unlit");',
                 'des.non_diggable(selection.area(0,0,4,2));',
                 'des.non_diggable();',
                 'des.non_passwall(selection.area(1,1,2,2));',
                 'des.teleport_region({ region = { 1, 1, 3, 2 }, '
                 'dir = "down" });',
                 'des.levregion({ region = { 70, 2, 75, 18 }, '
                 'type = "stair-up" });']
        code = 'des.region({ region = { 0, 0, 1, 1 }, type = rnd(), lit = 0 });'
        src = INIT + 'des.map([[\n.....\n.....\n.....\n]]);\n' + "\n".join(
            calls + [code]) + "\n"
        lvl = nhlevel.parse_level(src)[0]
        self.assertEqual(lvl.to_lua(), src)
        self.assertEqual([r.to_lua() for r in lvl.regions[:-1]], calls)
        self.assertEqual([len(r.cells(lvl)) for r in lvl.regions],
                         [6, 6, 15, 15, 4, 6, 0, 4])
        # appel avec du code : affiché, non modifiable, recopié tel quel
        self.assertTrue(lvl.regions[-1].readonly)
        self.assertEqual(lvl.regions_at(1, 1)[0].extra["type"], "temple")
        # insertion d'une ligne : zones décalées, sauf le niveau entier
        lvl.insert_row(0)
        self.assertEqual([r.rect for r in lvl.regions[:4]], [
            (1, 1, 3, 2), (0, 1, 2, 2), (0, 1, 4, 3), None])
        self.assertIn("des.non_passwall(selection.area(1,2,2,3));",
                      lvl.to_lua())
        self.assertIn(code, lvl.to_lua())
        # suppression de la ligne qui porte une zone d'une ligne de haut
        lvl = nhlevel.parse_level(src)[0]
        lvl.delete_row(0)
        self.assertEqual(lvl.regions[0].rect, (1, 0, 3, 0))
        lvl.delete_row(0)
        self.assertNotIn("type = \"temple\"", lvl.to_lua())

    def test_map_contents(self):
        src = (INIT + 'des.map({ halign = "center", valign = "center", '
               'map = [[\n....\n....\n]], contents = function(rm)\n'
               '   des.stair("up", 0, 0)\n'
               '   des.monster("orc", 1, 1)\n'
               '   des.non_diggable(selection.area(0,0,3,1))\n'
               '   if percent(50) then des.object("gem", 2, 1) end\n'
               '   des.trap()\n'
               'end });\n')
        lvl = nhlevel.parse_level(src)[0]
        self.assertEqual(lvl.to_lua(), src)
        self.assertEqual([e.kind for e in lvl.entities], ["stair", "monster"])
        self.assertEqual(lvl.regions[0].rect, (0, 0, 3, 1))
        lvl.entities[0].x = 3
        del lvl.entities[1]
        lvl.grid[1][0] = "#"
        out = lvl.to_lua()
        self.assertIn('[[\n....\n#...\n]], contents = function(rm)\n'
                      '   des.stair("up", 3, 0);\n'
                      '   des.non_diggable(selection.area(0,0,3,1))\n'
                      '   if percent(50)', out)
        self.assertNotIn("orc", out)

    def test_several_maps(self):
        src = (INIT + 'des.map({ halign = "left", valign = "top", '
               'map = [[\n...\n]] });\ndes.stair("up", 0, 0);\n'
               'des.map({ halign = "right", valign = "bottom", '
               'map = [[\n||\n||\n]] });\ndes.stair("down", 1, 1);\n')
        for i, kind in ((0, "up"), (1, "down")):
            lvl = nhlevel.parse_level(src, i)[0]
            self.assertEqual((lvl.map_index, len(lvl.maps)), (i, 2))
            self.assertEqual([e.value for e in lvl.entities], [kind])
            self.assertEqual(lvl.to_lua(), src)
        self.assertEqual(lvl.maps[1], {"w": 2, "h": 2, "halign": "right",
                                       "valign": "bottom", "pos": None})
        lvl.grid[0][0] = "-"
        lvl.flags = ["noflip"]
        out = lvl.to_lua()
        # drapeaux ajoutés avant la première carte, pas avant celle-ci
        self.assertIn('des.level_flags("noflip");\ndes.map({ halign = '
                      '"left"', out)
        self.assertIn("[[\n-|\n||\n]]", out)

    def test_new_region_written(self):
        lvl = level(["...."] * 3)
        lvl.regions.append(nhlevel.Region("region", (0, 0, 3, 2),
                                          {"type": "temple", "lit": 1}))
        lvl.regions.append(nhlevel.Region("non_diggable", None, style="sel"))
        out = lvl.to_lua()
        self.assertIn('des.region({ region = { 0, 0, 3, 2 }, '
                      'type = "temple", lit = 1 });', out)
        self.assertIn("des.non_diggable();", out)
        self.assertEqual(nhlevel.parse_level(out)[0].to_lua(), out)

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
