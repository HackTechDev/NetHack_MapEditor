#!/usr/bin/env python3
"""nhmapedit — petit éditeur de cartes NetHack en mode terminal.

Usage : python3 nhmapedit.py [fichier.lua] [--new LARGEURxHAUTEUR]

Appuyez sur « ? » dans l'éditeur pour l'aide.
"""

import curses
import locale
import os
import sys
import time

import nhconfig
import nhlevel
from nhi18n import _
from nhlevel import Level
from nhme_common import (
    AUTOSAVE_DELAY, CONFIG_DIR, Cancel, DUNGEON_FILES, FLIP_CYCLE, FLIP_NAME,
    HACKDIRS, HELP, SYM_NAME, TERRAIN_COLOR, TOOL_KEY, TOOL_NAME, TWO_POINT,
    bresenham, load_data)
from nhme_dialogs import DialogsMixin
from nhme_display import DisplayMixin
from nhme_entities import EntitiesMixin
from nhme_game import GameMixin
from nhme_level import LevelMixin
from nhme_tools import ToolsMixin

# noms publics réexportés (docs/capture.py, tests)
from nhme_common import *  # noqa: E402,F401,F403


class Editor(DisplayMixin, DialogsMixin, ToolsMixin, EntitiesMixin,
             LevelMixin, GameMixin):
    """L'éditeur : état, boucle des touches et souris. Les méthodes sont
    réparties par thème dans les modules nhme_*."""

    def __init__(self, scr, path=None, size=None, config=None):
        self.scr = scr
        # réglages du fichier de configuration (voir nhconfig)
        self.config = config or {}
        self.data = load_data()
        # noms et alias (formes féminines, noms sans préfixe…)
        self.mon = {n: m for m in self.data["monsters"]
                    for n in [m["name"]] + m.get("aliases", [])}
        self.obj = {n: o for o in self.data["objects"]
                    for n in [o["name"]] + o.get("aliases", [])}
        self.lvl = Level(*(size or self.config.get("size", (75, 19))))
        self.path = None
        self.modified = False
        self.cx = self.cy = 0
        self.ox = self.oy = 0       # décalage de la vue
        self.brush = "."
        self.tool = "pen"
        self.anchor = None
        self.pen_down = False
        self.advance = False
        self.show_ents = self.config.get("entities", True)
        # calques des régions affichés (familles de region_family())
        self.show_regions = {"room", "tele", "rand"}
        self.show_terrain = True    # calque du terrain (touche ;)
        self.maze_opts = ("-", ".", 0)  # murs, passages, % de boucles
        self.auto_walls = False     # pinceau mur automatique (touche =)
        # sélection multiple d'entités (touche *) : copies relatives au
        # coin de la sélection, et originaux à retirer pour un déplacement
        self.ent_clip, self.ent_moved = [], []
        self.pending_region = None  # région en cours de tracé
        # règles de coordonnées autour de la carte
        self.rulers = self.config.get("rulers", True)
        self.game = False           # rendu « comme dans le jeu »
        self.flip = 0               # aperçu retourné (bits de FLIP_NAME)
        self.sym = 0                # symétrie de dessin (mêmes bits)
        enc = locale.getpreferredencoding(False).lower().replace("-", "")
        self.unicode = self.config.get("unicode", enc == "utf8")
        # remplacement de touches : [touches] du fichier de configuration
        self.keymap = self.config.get("keys", {})
        TERRAIN_COLOR.update(self.config.get("colors", {}))
        self.clip = None
        self.density = 30           # densité de l'outil Semis, en %
        self.replace = None         # (ancien, nouveau, %) de l'outil Remplacer
        self.template = None        # dernière entité placée
        self.hackdir = next((d for d in [self.config.get("hackdir", "")]
                             + HACKDIRS if self.is_hackdir(d)), None)
        self.game_pane = None       # panneau tmux du jeu lancé par « t »
        self.dungeon_path = next((f for f in [self.config.get("dungeon")]
                                  + DUNGEON_FILES
                                  if f and os.path.isfile(f)), "")
        self.game_where = ""
        self.launch = None          # réponse à « lancer le jeu ? »
        self.lua_refused = False    # compilation de Lua refusée
        self.autosave_delay = self.config.get("autosave", AUTOSAVE_DELAY)
        self.autosave_time = time.time()
        # historique des commandes (voir ToolsMixin.checkpoint) ;
        # saved_state : numéro de l'état enregistré dans le fichier
        self.undo_stack, self.redo_stack = [], []
        self.serial = self.saved_state = 0
        # trait en cours (crayon baissé ou glisser à la souris) : un seul
        # point d'annulation pour tout le trait
        self.stroke = self.stroke_saved = False
        self.msg = _("Bienvenue ! « ? » pour l'aide.")
        self.mouse_down = False
        self.pairs = {}
        if scr is not None:         # Editor(None) : sans écran (tests)
            self.init_colors()
        if path:
            if os.path.exists(path):
                self.open_file(path)
            else:
                self.path = path
                self.msg = _("Nouveau fichier : %s") % path
                self.offer_autosave()
        else:
            self.offer_autosave()

    def run(self):
        curses.raw()
        curses.mousemask(curses.ALL_MOUSE_EVENTS
                         | curses.REPORT_MOUSE_POSITION)
        curses.mouseinterval(0)
        # suivi du glissement de la souris (xterm 1002)
        sys.stdout.write("\033[?1002h")
        sys.stdout.flush()
        try:
            while True:
                self.draw()
                try:
                    k = self.scr.get_wch()
                except curses.error:
                    continue
                k = self.keymap.get(k, k)
                try:
                    if self.handle(k) is False:
                        self.drop_autosave()
                        break
                except Cancel:
                    self.msg = _("Annulé.")
                self.autosave()
        finally:
            sys.stdout.write("\033[?1002l")
            sys.stdout.flush()

    def handle(self, k):
        lvl = self.lvl
        lay = self.layout()
        vh = lay[3]
        moves = {curses.KEY_LEFT: (-1, 0), curses.KEY_RIGHT: (1, 0),
                 curses.KEY_UP: (0, -1), curses.KEY_DOWN: (0, 1),
                 "h": (-1, 0), "l": (1, 0), "k": (0, -1), "j": (0, 1),
                 curses.KEY_SLEFT: (-8, 0), curses.KEY_SRIGHT: (8, 0),
                 curses.KEY_SR: (0, -4), curses.KEY_SF: (0, 4),
                 curses.KEY_PPAGE: (0, -vh), curses.KEY_NPAGE: (0, vh)}
        if k not in moves and k not in (curses.KEY_HOME, curses.KEY_END,
                                         curses.KEY_MOUSE,
                                         curses.KEY_RESIZE):
            self.end_stroke()       # toute autre touche termine le trait
        if k in moves:
            self.move(*moves[k])
        elif k == curses.KEY_HOME:
            self.move(-self.fl(self.cx, 0)[0], 0)
        elif k == curses.KEY_END:
            self.move(lvl.w - 1 - self.fl(self.cx, 0)[0], 0)
        elif k == curses.KEY_MOUSE:
            self.mouse(lay)
        elif k == curses.KEY_RESIZE:
            pass
        elif k in (" ", "\n", "\r", curses.KEY_ENTER):
            self.apply()
        elif k == "\x1b":
            if self.anchor:
                self.anchor = None
                self.msg = _("Tracé annulé.")
                if self.tool == "region":
                    self.end_region()
                elif self.tool == "walls":
                    self.tool = self.walls_prev_tool
                elif self.tool == "entsel":
                    self.tool = self.sel_prev_tool
            elif self.tool == "paste":
                self.tool = "pen"
                self.msg = _("Outil Pinceau.")
            elif self.tool == "entpaste":
                self.tool = self.sel_prev_tool
                self.msg = _("Entités laissées en place.")
        elif k in TOOL_KEY:
            if TOOL_KEY[k] == "scatter":
                s = self.prompt(_("Densité du semis en %% (1-100) : "),
                                str(self.density))
                try:
                    self.density = max(1, min(100, int(s)))
                except ValueError:
                    self.msg = _("Densité invalide.")
                    return True
            elif TOOL_KEY[k] == "maze":
                self.ask_maze()
            elif TOOL_KEY[k] == "replace" and not self.ask_replace():
                return True         # déjà fait sur toute la carte
            self.tool = TOOL_KEY[k]
            self.anchor = None
            self.msg = _("Outil : %s.") % TOOL_NAME[self.tool]
            if self.tool == "paste" and not self.clip:
                self.msg += _(" (presse-papiers vide)")
        elif isinstance(k, str) and (k in nhlevel.TERRAIN_CHARS
                                     and k != " " or k == "e"):
            self.brush = " " if k == "e" else k
            if self.tool == "pen":
                self.paint({(self.cx, self.cy): self.brush})
                if self.advance:
                    self.move(1, 0)
            self.msg = _("Pinceau : %s.") % nhlevel.TERRAIN_DESC[self.brush]
        elif k == "d":
            self.pen_down = not self.pen_down
            if self.pen_down and self.tool == "pen":
                self.begin_stroke()
                self.paint({(self.cx, self.cy): self.brush})
            self.msg = (_("Crayon baissé.") if self.pen_down
                        else _("Crayon levé."))
        elif k == "y":
            self.eyedropper()
        elif k == "M":
            self.sym = FLIP_CYCLE[self.sym]
            self.msg = (_("Symétrie : %s.") % SYM_NAME[self.sym] if self.sym
                        else _("Symétrie désactivée."))
        elif k == "E":
            self.edit_rows_cols()
        elif k in ("X", "Y", "O"):
            self.transform_clip({"X": "x", "Y": "y", "O": "rot"}[k])
        elif k == "a":
            self.advance = not self.advance
            self.msg = _("Avance automatique %s.") % (
                _("activée") if self.advance else _("désactivée"))
        elif k == "m":
            self.place_entity()
        elif k == "r":
            if self.template and not self.no_entities():
                self.add_entity(self.template.copy())
            else:
                self.msg = _("Aucune entité à répéter (m pour en placer une).")
        elif k in (curses.KEY_DC, curses.KEY_BACKSPACE, "\x7f", "\x08", "z"):
            self.delete_entities()
        elif k == "i":
            self.entity_list()
        elif k == "\t":
            self.show_ents = not self.show_ents
        elif k == "J":
            self.game = not self.game
            self.msg = (_("Rendu « comme dans le jeu ».") if self.game
                        else _("Rendu des caractères de carte (des.map)."))
        elif k == "f":
            self.flip = FLIP_CYCLE[self.flip]
            if not self.flip:
                self.msg = _("Carte affichée dans son sens d'origine.")
            else:
                self.msg = _("Aperçu retourné : %s. %s") % (
                    FLIP_NAME[self.flip],
                    _("NetHack peut le faire au chargement.")
                    if self.flip & lvl.allowed_flips() == self.flip else
                    _("Empêché par les drapeaux du niveau (noflip...)."))
        elif k == "c":
            self.rulers = not self.rulers
            self.msg = _("Règles de coordonnées %s.") % (
                _("affichées") if self.rulers else _("masquées"))
        elif k == "p":
            self.properties()
        elif k == "v":
            self.check()
        elif k == "t":
            self.test_in_game()
        elif k == "g":
            s = self.prompt(_("Aller à « x y » : "),
                            "%d %d" % (self.cx, self.cy))
            try:
                x, y = (int(v) for v in s.split())
                self.cx, self.cy = x, y
                self.clamp_cursor()
            except ValueError:
                self.msg = _("Position invalide.")
        elif k in ("u", "\x1a"):
            self.undo()
        elif k in ("U", "\x12", "\x19"):
            self.redo()
        elif k in ("[", "]"):
            if len(lvl.maps) < 2:
                self.msg = _("Une seule carte dans ce fichier (N pour en "
                             "ajouter une).")
            else:
                self.switch_map((lvl.map_index + (1 if k == "]" else -1))
                                % len(lvl.maps))
        elif k == "N":
            self.maps_menu()
        elif k == ";":
            self.layers()
        elif k == "=":
            self.walls_menu()
        elif k == "/":
            self.find_replace()
        elif k == "*":
            self.start_entity_selection()
        elif k == "%":
            self.show_stats()
        elif k == "V":
            self.history()
        elif k == "n":
            self.new_level()
        elif k == "b":
            self.templates()
        elif k == "o":
            self.check_unsaved()
            path = self.prompt(_("Ouvrir : "), os.getcwd() + "/",
                               self.path_completer)
            self.open_file(os.path.expanduser(path.strip()))
        elif k in ("s", "\x13"):
            self.save()
        elif k == "w":
            self.save(as_new=True)
        elif k == "?":
            self.message_box(_("Aide"), HELP.rstrip())
        elif k in ("q", "\x11"):
            if self.check_unsaved():
                return False
        elif k == "\x03":
            if not self.modified or self.confirm(
                    _("Quitter sans enregistrer ?")):
                return False
        return True

    def mouse(self, lay):
        vw, vh, top, left = lay[2], lay[3], lay[5], lay[6]
        try:
            _id, mx, my, _z, bstate = curses.getmouse()
        except curses.error:
            return
        sx, sy = mx - left - 1, my - top - 1
        x, y = self.fl(sx + self.ox, sy + self.oy)
        inside = 0 <= sx < vw and 0 <= sy < vh
        if bstate & (curses.BUTTON3_PRESSED | curses.BUTTON3_CLICKED):
            if inside:
                self.cx, self.cy = x, y
                self.eyedropper()
        elif bstate & curses.BUTTON1_PRESSED and inside:
            self.mouse_down = True
            self.cx, self.cy = x, y
            if self.tool == "pen":
                self.begin_stroke()
            self.apply()
        elif bstate & curses.BUTTON1_CLICKED and inside:
            self.cx, self.cy = x, y
            self.apply()
        elif bstate & curses.BUTTON1_RELEASED:
            # fin d'un glisser avec un outil à deux points
            if (self.mouse_down and inside and self.tool in TWO_POINT
                    and self.anchor and (x, y) != self.anchor):
                self.cx, self.cy = x, y
                self.apply()
            self.mouse_down = False
            self.end_stroke()
        elif bstate & curses.REPORT_MOUSE_POSITION and inside:
            if self.mouse_down and self.tool == "pen":
                self.paint({p: self.brush
                            for p in bresenham(self.cx, self.cy, x, y)})
            self.cx, self.cy = x, y
        elif bstate & curses.BUTTON4_PRESSED:
            self.move(0, -1)
        elif bstate & getattr(curses, "BUTTON5_PRESSED", 0):
            self.move(0, 1)


def main():
    args = sys.argv[1:]
    size, path = None, None
    while args:
        a = args.pop(0)
        if a in ("-h", "--help"):
            print(_(__doc__.strip()))
            print()
            print(HELP)
            return
        if a == "--new" and args:
            try:
                w, h = (int(v) for v in args.pop(0).lower().split("x"))
                size = (min(w, nhlevel.MAX_W), min(h, nhlevel.MAX_H))
            except ValueError:
                sys.exit(_("--new attend LARGEURxHAUTEUR, ex: --new 40x12"))
        else:
            path = a
    locale.setlocale(locale.LC_ALL, "")
    os.environ.setdefault("ESCDELAY", "25")
    config, errors = nhconfig.load(nhconfig.default_path(CONFIG_DIR))

    def run(scr):
        scr.keypad(True)
        ed = Editor(scr, path, size, config)
        if errors:
            ed.msg = _("Configuration : %s") % "; ".join(errors)
        ed.run()

    curses.wrapper(run)


if __name__ == "__main__":
    main()
