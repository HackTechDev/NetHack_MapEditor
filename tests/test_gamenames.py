"""Noms vus en jeu (catalogue gettext de cybernethack)."""

import os
import struct
import tempfile
import unittest

from tests.util import level

import nhexport
import nhgamenames
import nhlevel
import nhpalette
import nhmapedit
from nhlevel import Entity
from nhme_common import game_view

# entrées du catalogue : (contexte, msgid, msgid_plural, traductions)
ENTRIES = [
    ("monster", "jackal", None, ["chien errant"]),
    ("monster", "newt", None, ["rat de labo"]),
    ("object", "potion of %s", "potions of %s", ["stim de %s", "stims de %s"]),
    ("object-elided", "potion of %s", "potions of %s",
     ["stim d'%s", "stims d'%s"]),
    ("object", "healing", "healings", ["soins", "soins"]),
    ("object", "oil", "oils", ["huile", "huiles"]),
    ("object", "invisibility", "invisibilities",
     ["invisibilité", "invisibilités"]),
    ("object", "gold piece", "gold pieces", ["eddie", "eddies"]),
    ("trap", "arrow trap", None, ["piège à flèches"]),
    (None, "The Dungeons of Doom", None, ["Night City"]),
]


def write_mo(path, entries):
    """Petit catalogue GNU .mo (format décrit dans le manuel de gettext)."""
    cat = {"": "Content-Type: text/plain; charset=UTF-8\n"
               "Plural-Forms: nplurals=2; plural=(n > 1);\n"}
    for ctx, mid, plural, tr in entries:
        key = ((ctx + "\x04" if ctx else "") + mid
               + ("\x00" + plural if plural else ""))
        cat[key] = "\x00".join(tr)
    keys = sorted(cat)
    ids = b"".join(k.encode() + b"\x00" for k in keys)
    strs = b"".join(cat[k].encode() + b"\x00" for k in keys)
    n = len(keys)
    start = 7 * 4 + 16 * n
    otab, ttab, o, t = [], [], 0, 0
    for k in keys:
        b = k.encode()
        otab += [len(b), start + o]
        o += len(b) + 1
    for k in keys:
        b = cat[k].encode()
        ttab += [len(b), start + len(ids) + t]
        t += len(b) + 1
    with open(path, "wb") as f:
        f.write(struct.pack("<7I", 0x950412de, 0, n, 28, 28 + 8 * n, 0, 0))
        f.write(struct.pack("<%dI" % len(otab), *otab))
        f.write(struct.pack("<%dI" % len(ttab), *ttab))
        f.write(ids + strs)


class GameNames(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        write_mo(os.path.join(self.tmp.name, "fr@cyber.mo"), ENTRIES)

    def tearDown(self):
        self.tmp.cleanup()
        nhlevel.GAME_NAME = None

    def names(self, lang="fr@cyber"):
        return nhgamenames.GameNames(self.tmp.name, lang,
                                     {"arrow": "arrow trap"})

    def test_names(self):
        n = self.names()
        self.assertTrue(n.active())
        self.assertEqual(n.name("monster", "jackal"), "chien errant")
        self.assertEqual(n.name("object", "potion of healing"),
                         "stim de soins")
        # élision devant une voyelle seulement, comme obj_pattern()
        self.assertEqual(n.name("object", "potion of invisibility"),
                         "stim d'invisibilité")
        self.assertEqual(n.name("object", "potion of oil"), "stim de huile")
        self.assertEqual(n.name("object", "gold piece"), "eddie")
        self.assertEqual(n.name("trap", "arrow"), "piège à flèches")
        # absent du catalogue, classe, aléatoire : rien à ajouter
        self.assertIsNone(n.name("monster", "Medusa"))
        self.assertIsNone(n.name("monster", "d"))
        self.assertIsNone(n.name("object", None))
        self.assertEqual(n.label("monster", "jackal"),
                         "jackal (chien errant)")
        self.assertEqual(n.label("monster", "Medusa"), "Medusa")

    def test_fallback_and_english(self):
        # fr@cyber absent : fr.mo, comme le jeu ; « en » : aucun catalogue
        os.rename(os.path.join(self.tmp.name, "fr@cyber.mo"),
                  os.path.join(self.tmp.name, "fr.mo"))
        self.assertEqual(self.names().name("monster", "newt"), "rat de labo")
        self.assertFalse(self.names("en").active())
        self.assertFalse(nhgamenames.GameNames(None).active())

    def test_language_from_options(self):
        with tempfile.NamedTemporaryFile("w", suffix="rc",
                                         delete=False) as f:
            f.write("OPTIONS=windowtype:curses\nOPTIONS=language:fr\n")
        try:
            lang = nhgamenames.game_language
            self.assertEqual(lang({}, f.name), "fr")
            self.assertEqual(lang({"NETHACKOPTIONS": "lang:en"}, f.name),
                             "en")
            self.assertEqual(lang({}, os.devnull), "fr@cyber")
        finally:
            os.remove(f.name)

    def test_editor_shows_game_names(self):
        ed = nhmapedit.Editor(None)
        ed.names = self.names()
        nhlevel.GAME_NAME = ed.names.name
        ed.lvl = level(["...."])
        ed.lvl.entities = [Entity("monster", 0, 0, "jackal"),
                           Entity("trap", 1, 0, "arrow")]
        self.assertEqual(ed.lvl.entities[0].describe(),
                         "monstre jackal (chien errant)")
        self.assertEqual(ed.pick_label("monster", {"sym": "d",
                                                   "name": "jackal"}),
                         ("d  jackal  — chien errant", "jackal"))
        text = ed.stats_text()
        self.assertIn("jackal (chien errant)", text)
        self.assertIn("arrow (piège à flèches)", text)
        # le script garde le nom anglais
        self.assertIn('des.monster("jackal", 0, 0);', ed.lvl.to_lua())


class Theme(unittest.TestCase):
    """Modèles, textes et lieux du thème cyberpunk."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        write_mo(os.path.join(self.tmp.name, "fr@cyber.mo"), ENTRIES)
        os.mkdir(os.path.join(self.tmp.name, "dat"))

    def tearDown(self):
        self.tmp.cleanup()

    def write_dat(self, name, text):
        with open(os.path.join(self.tmp.name, "dat", name), "w",
                  encoding="utf-8") as f:
            f.write(text)

    def test_place(self):
        n = nhgamenames.GameNames(self.tmp.name, "fr@cyber")
        self.assertEqual(n.name("place", "The Dungeons of Doom"),
                         "Night City")
        self.assertIsNone(n.name("place", "Sokoban"))
        self.assertEqual(nhgamenames.GameNames(None).place("Sokoban"),
                         "Sokoban")

    def test_template_theme(self):
        text = ("-- Modèle nhmapedit : Ruche\n-- Des abeilles.\n"
                "-- Modèle nhmapedit@cyber : Essaim de drones\n"
                "-- Des drones\n-- tueurs.\ndes.map([[\n.\n]]);\n")
        info = nhexport.template_info
        self.assertEqual(info(text, "ruche.lua"), ("Ruche", "Des abeilles."))
        self.assertEqual(info(text, "ruche.lua", "cyber"),
                         ("Essaim de drones", "Des drones tueurs."))
        # thème sans titre propre : celui de base
        self.assertEqual(info(text, "ruche.lua", "autre")[0], "Ruche")
        self.assertEqual(info("des.map()", "x/ruche.lua"), ("ruche", ""))

    def test_game_texts(self):
        texts = nhgamenames.game_texts
        self.write_dat("epitaph-fr.txt", "# commentaire\nRepose en paix\n"
                       "\nR.I.P.\nRepose en paix\n")
        self.assertEqual(texts([self.tmp.name], "epitaph", "fr@cyber"),
                         ["Repose en paix", "R.I.P."])
        self.write_dat("epitaph-fr@cyber.txt", "Déconnecté\n")
        self.assertEqual(texts([self.tmp.name], "epitaph", "fr@cyber"),
                         ["Déconnecté"])
        self.assertEqual(texts([self.tmp.name], "engrave", "fr"), [])

    def test_pick_text(self):
        self.write_dat("epitaph-fr@cyber.txt", "Déconnecté\nHors ligne\n")
        ed = nhmapedit.Editor(None)
        ed.names = nhgamenames.GameNames(self.tmp.name, "fr@cyber")
        ed.source_dirs = lambda: [self.tmp.name]
        seen = []

        def pick(title, items, initial=None, custom=False, hint=""):
            seen.append(items)
            return answers.pop(0)
        ed.pick = pick
        answers = ["Hors ligne", "_random", "Mon texte"]
        self.assertEqual(ed.pick_value("grave"), "Hors ligne")
        self.assertIsNone(ed.pick_value("grave"))
        self.assertEqual(ed.pick_value("grave", "Mon texte"), "Mon texte")
        self.assertEqual([v for _l, v in seen[2]],
                         ["_random", "Mon texte", "Déconnecté",
                          "Hors ligne"])
        # pas de textes de gravure : saisie libre
        ed.prompt = lambda *a, **k: "Elbereth"
        self.assertEqual(ed.pick_value("engraving"), "Elbereth")


class Palette(unittest.TestCase):
    RC = ("# palette\n"
          "OPTIONS=language:fr@cyber\n"
          "OPTIONS=glyph:S_vwall:U+2502/0-255-255\n"
          "OPTIONS=glyph:S_hwall:U+2500/0-255-255\n"
          "OPTIONS=glyph:S_tlcorn:U+250C/0-255-255\n"
          "OPTIONS=glyph:S_room:U+00B7/122-4-235\n"
          "OPTIONS=glyph:S_upstair:U+25B2/245-245-0\n"
          "OPTIONS=glyph:S_arrow_trap:^/255-42-109\n"
          "#OPTIONS=glyph:S_corr:X/1-2-3\n")
    USER = "OPTIONS=glyph:S_upstair:U+21E7,glyph:S_potion:U+00A1\n"

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.rc = os.path.join(self.tmp.name, "cyber.rc")
        self.user = os.path.join(self.tmp.name, "user.rc")
        with open(self.rc, "w", encoding="utf-8") as f:
            f.write(self.RC)
        with open(self.user, "w", encoding="utf-8") as f:
            f.write(self.USER)

    def tearDown(self):
        self.tmp.cleanup()

    def test_parse_and_merge(self):
        g = nhpalette.parse_rc(self.rc)
        self.assertEqual(g["S_room"], ("·", (122, 4, 235)))
        self.assertEqual(g["S_arrow_trap"], ("^", (255, 42, 109)))
        self.assertNotIn("S_corr", g)               # ligne commentée
        pal = nhpalette.Palette([self.rc, self.user])
        # le .nethackrc du joueur change le symbole, garde la couleur
        self.assertEqual(pal.apply("S_upstair", "<", "CLR_YELLOW"),
                         ("⇧", (245, 245, 0)))
        self.assertEqual(pal.apply("S_potion", "!", "CLR_MAGENTA"),
                         ("¡", "CLR_MAGENTA"))
        self.assertEqual(pal.apply("S_web", '"', "CLR_GRAY"),
                         ('"', "CLR_GRAY"))
        ascii_pal = nhpalette.Palette([self.rc], unicode=False)
        self.assertEqual(ascii_pal.apply("S_room", ".", "CLR_GRAY"),
                         (".", (122, 4, 235)))

    def test_game_view_and_entities(self):
        pal = nhpalette.Palette([self.rc, self.user])
        view = game_view([list("--"), list("|.")], " ", pal)
        self.assertEqual(view[0][0], ("┌", (0, 255, 255)))
        self.assertEqual(view[1][1], ("·", (122, 4, 235)))
        ed = nhmapedit.Editor(None)
        ed.palette, ed.game = pal, True
        self.assertEqual(ed.entity_glyph(Entity("stair", 0, 0, "up")),
                         ("⇧", (245, 245, 0)))
        self.assertEqual(ed.entity_glyph(Entity("trap", 0, 0, "arrow")),
                         ("^", (255, 42, 109)))
        self.assertEqual(ed.entity_glyph(Entity("object", 0, 0,
                                                "potion of healing")),
                         ("¡", "CLR_MAGENTA"))
        ed.game = False                 # rendu d'édition : inchangé
        self.assertEqual(ed.entity_glyph(Entity("stair", 0, 0, "up")),
                         ("<", "CLR_YELLOW"))

    def test_colors(self):
        self.assertEqual(nhpalette.xterm256((0, 255, 255)), 51)
        self.assertEqual(nhpalette.xterm256((128, 128, 128)), 244)
        self.assertEqual(nhpalette.nearest_basic((0, 255, 255)),
                         "CLR_BRIGHT_CYAN")
        self.assertEqual(nhexport.rgb((255, 42, 109)), "#ff2a6d")


if __name__ == "__main__":
    unittest.main()
