"""Intégration avec le jeu : test (tmux, #wizloaddes, THEMERM) et dungeon.lua."""

import os
import re
import shlex
import shutil
import subprocess
import time

import nhdungeon
import nhlevel
from nhme_common import (
    Cancel, GAME_OPTIONS, GAME_SESSION, HACKDIRS, TEST_PREFIX)


class GameMixin:
    """Méthodes de l'éditeur (voir nhmapedit.Editor)."""

    def edit_dungeon(self):
        """Ajoute, modifie ou supprime un niveau spécial de dungeon.lua."""
        path = self.prompt("Fichier dungeon.lua (dans dat/ des sources) : ",
                           self.dungeon_path, self.path_completer)
        path = os.path.expanduser(path.strip())
        try:
            with open(path, encoding="utf-8") as f:
                df = nhdungeon.DungeonFile(f.read())
        except (OSError, ValueError) as e:
            self.msg = "%s : %s" % (path, e)
            return
        self.dungeon_path = path
        di = 0
        while True:
            items = [("%-24s %d niveau(x) spécial(aux)" % (
                df.dungeon_name(d), len(df.levels(d))), i)
                for i, d in enumerate(df.dungeons())]
            try:
                di = self.pick("Donjons de %s (%d niveaux spéciaux sur %d)"
                               % (os.path.basename(path),
                                  len(df.all_level_names()),
                                  nhdungeon.LEV_LIMIT), items, di)
            except Cancel:
                return
            df = self.dungeon_levels(df, di)

    def dungeon_levels(self, df, di):
        """Liste des niveaux spéciaux d'un donjon. Renvoie le fichier
        tel qu'il est après les modifications (déjà enregistrées)."""
        sel = 0
        while True:
            d = df.dungeons()[di]
            levels = [l.py() for l in df.levels(d)]
            items = [("%-10s %s" % (l.get("name"), " ".join(
                "%s=%s" % (k, v if not isinstance(v, (list, str)) or
                           k == "name" else nhlevel.lua_value(v))
                for k, v in l.items() if k != "name")), i)
                for i, l in enumerate(levels)]
            items.append(("+ ajouter ce niveau", "add"))
            hint = "Entrée/e: modifier  d: supprimer  Échap: retour"
            try:
                i, action = self.pick_action(df.dungeon_name(d), items, sel,
                                             hint)
            except Cancel:
                return df
            try:
                if i == "add":
                    base = os.path.splitext(os.path.basename(
                        self.path or "niveau"))[0]
                    fields = self.dungeon_form(df, di, None, {"name": base})
                    if fields:
                        df = self.write_dungeon(df.add_level(di, fields))
                        sel = len(levels)
                        if df:
                            self.after_dungeon_add(df, di, fields)
                elif action == "delete":
                    if self.confirm("Retirer %s du donjon ?"
                                    % levels[i].get("name")):
                        df = self.write_dungeon(df.delete_level(di, i))
                        sel = max(0, i - 1)
                else:
                    fields = self.dungeon_form(df, di, i, levels[i])
                    if fields:
                        df = self.write_dungeon(df.replace_level(di, i,
                                                                 fields))
                        sel = i
            except Cancel:
                pass
            if df is None:          # erreur d'écriture
                return self.reload_dungeon()

    def reload_dungeon(self):
        with open(self.dungeon_path, encoding="utf-8") as f:
            return nhdungeon.DungeonFile(f.read())

    def dungeon_form(self, df, di, li, fields):
        """Formulaire d'un niveau du donjon ; None si abandon."""
        fields = dict(fields)
        if isinstance(fields.get("flags"), str):
            fields["flags"] = [fields["flags"]]
        form = [
            ("name", "str", "nom du fichier, sans .lua"),
            ("base", "int", "profondeur (négatif : depuis le bas)"),
            ("range", "int", "profondeur : tirage en plus"),
            ("chance", "int", "probabilité de présence, en %"),
            ("nlevels", "int", "variantes (nom-1.lua … nom-N.lua)"),
            ("alignment", ("choice", nhdungeon.ALIGNMENTS), "alignement"),
            ("flags", ("flags", nhdungeon.LEVEL_FLAGS), "drapeaux"),
            ("bonetag", "str", "lettre des fichiers bones"),
            ("chainlevel", ("choice", df.names_before(di, li)),
             "base comptée depuis ce niveau"),
        ]
        while True:
            fields = self.form("Niveau du donjon", form, fields, free=False)
            errs = nhdungeon.check_level(df, fields, di, li)
            if not errs:
                return fields
            if not self.confirm("%s. Corriger ?" % " ; ".join(errs)
                                .capitalize()):
                return None

    def write_dungeon(self, df):
        """Enregistre dungeon.lua (l'original est gardé sous ~)."""
        path = self.dungeon_path
        try:
            if not os.path.exists(path + "~"):
                shutil.copy2(path, path + "~")
            with open(path, "w", encoding="utf-8") as f:
                f.write(df.text)
        except OSError as e:
            self.msg = "Erreur d'écriture : %s" % e
            return None
        self.msg = "Enregistré : %s" % path
        return df

    def after_dungeon_add(self, df, di, fields):
        """Propose de copier la carte dans le répertoire du jeu, puis
        rappelle les étapes pour jouer le niveau."""
        name = fields["name"]
        if fields.get("nlevels"):
            name += "-1"
        dest = None
        if self.hackdir and self.confirm(
                "Copier la carte dans %s/%s.lua ?" % (self.hackdir, name)):
            dest = os.path.join(self.hackdir, name + ".lua")
            try:
                if not os.path.exists(dest) or self.confirm(
                        "%s existe. Écraser ?" % dest):
                    with open(dest, "w", encoding="utf-8") as f:
                        f.write(self.lvl.to_lua(name))
                else:
                    dest = None
            except OSError as e:
                self.msg = "Erreur d'écriture : %s" % e
                dest = None
        self.message_box("Niveau ajouté au donjon", "\n".join([
            "%s ajouté à « %s » dans :" % (fields["name"],
                                           df.dungeon_name(
                                               df.dungeons()[di])),
            "  " + self.dungeon_path,
            "",
            "Pour le jouer :",
            ("  1. la carte est copiée dans " + dest) if dest else
            "  1. copiez la carte sous %s.lua dans le répertoire du jeu"
            % name,
            "     (le jeu la lit là, puisqu'elle n'est pas dans nhdat) ;",
            "  2. dans les sources, « make install » range le nouveau",
            "     dungeon.lua dans nhdat ;",
            "  3. commencez une nouvelle partie (les parties en cours",
            "     gardent l'ancien donjon). En mode wizard, #wizwhere",
            "     donne la profondeur des niveaux spéciaux et Ctrl-V",
            "     téléporte de niveau.",
        ] + (["", "Avec nlevels, il faut un fichier par variante :",
              "%s-1.lua … %s-%d.lua." % (fields["name"], fields["name"],
                                          fields["nlevels"])]
             if fields.get("nlevels") else [])))

    @staticmethod
    def is_hackdir(d):
        return bool(d) and any(os.path.isfile(os.path.join(d, f))
                               for f in ("nhdat", "sysconf"))

    def test_in_game(self):
        """Copie l'état courant de la carte dans le répertoire du jeu."""
        if self.lvl.theme:
            return self.test_theme()
        if not self.hackdir:
            d = self.prompt("Répertoire de données de NetHack (nethackdir) : ",
                            HACKDIRS[1], self.path_completer)
            d = os.path.expanduser(d.strip())
            if not self.is_hackdir(d):
                self.msg = "%s : ni nhdat ni sysconf, répertoire refusé." % d
                return
            self.hackdir = d
        base = os.path.splitext(os.path.basename(self.path or "sans-nom"))[0]
        name = TEST_PREFIX + re.sub(r"[^A-Za-z0-9_-]", "_", base)
        dest = os.path.join(self.hackdir, name + ".lua")
        # NetHack retourne au hasard les niveaux sans « noflip » : on
        # l'ajoute à la copie de test pour retrouver la carte telle quelle
        flags = self.lvl.flags
        if not {"noflip", "noflipx", "noflipy"} & set(flags):
            self.lvl.flags = flags + ["noflip"]
        try:
            with open(dest, "w", encoding="utf-8") as f:
                f.write(self.lvl.to_lua(base))
        except OSError as e:
            self.msg = "Erreur d'écriture : %s" % e
            return
        finally:
            self.lvl.flags = flags
        self.msg = "Copié pour test : %s" % dest
        if self.game_alive():
            self.load_in_game(name)
            return
        if shutil.which("tmux") and self.launch is None:
            self.launch = self.confirm(
                "Lancer NetHack (mode wizard) et y charger la carte ?")
        if self.launch and shutil.which("tmux"):
            if self.start_game():
                self.load_in_game(name)
                return
        self.message_box("Tester dans NetHack", "\n".join([
            "Carte copiée (état actuel, même non enregistré) dans :",
            "  " + dest,
            "",
            "Dans un autre terminal :",
            "  1. lancez le jeu en mode wizard :  nethack -D",
            "  2. tapez  #wizloaddes  puis Entrée",
            "  3. répondez :  " + name,
            "",
            "Après une modification, appuyez de nouveau sur t puis",
            "refaites #wizloaddes : inutile de relancer le jeu.",
            "Ctrl-F révèle toute la carte, Ctrl-T téléporte.",
            "(La copie de test a le drapeau noflip : sinon NetHack",
            "retourne la carte au hasard à chaque chargement.)",
            "",
            "Avec tmux installé, l'éditeur peut lancer le jeu et",
            "charger la carte lui-même.",
        ]))

    @staticmethod
    def tmux(*args):
        try:
            r = subprocess.run(["tmux"] + list(args), capture_output=True,
                               text=True, timeout=5)
        except (OSError, subprocess.SubprocessError):
            return None
        return r.stdout.strip() if r.returncode == 0 else None

    def game_alive(self):
        """Le panneau du jeu existe-t-il encore ? (il se ferme avec le jeu)"""
        if not self.game_pane:
            return False
        cmd = self.tmux("display-message", "-p", "-t", self.game_pane,
                        "#{pane_current_command}")
        if cmd is None:
            self.game_pane = None
        return bool(cmd)

    def test_theme(self):
        """Une salle à thème se teste avec THEMERM, une fois themerms.lua
        rangé dans nhdat (le jeu lit nhdat avant les fichiers à part)."""
        name = self.lvl.theme["name"]
        self.message_box("Tester une salle à thème", "\n".join([
            "themerms.lua est rangé dans nhdat : le jeu ne lit pas une",
            "copie posée à côté. Pour voir la salle « %s » :" % name,
            "",
            "  1. enregistrez (s) : la carte est écrite dans",
            "     " + self.lvl.theme["path"] + " ;",
            "  2. dans les sources, lancez « make install » ;",
            "  3. lancez le jeu en mode wizard avec la variable THEMERM :",
            "     THEMERM=%s nethack -D" % shlex.quote(name),
            "",
            "Chaque salle des niveaux ordinaires est alors cette salle,",
            "quand elle y tient. Ctrl-F révèle la carte, Ctrl-V change de",
            "niveau pour en générer d'autres.",
        ]))
        if not (self.hackdir and shutil.which("tmux")):
            return
        if self.game_alive():
            self.msg = ("Une partie lancée par l'éditeur est en cours : "
                        "quittez-la pour relancer avec THEMERM.")
            return
        if self.confirm("Lancer NetHack avec THEMERM=%s (après make "
                        "install) ?" % name):
            if self.start_game({"THEMERM": name}):
                self.msg = "NetHack lancé avec THEMERM=%s (%s)." % (
                    name, self.game_where)

    def game_command(self, env=None):
        d = self.hackdir
        opts = os.environ.get("NETHACKOPTIONS", "")
        # une valeur qui désigne un fichier remplace le .nethackrc : on
        # n'y touche pas
        if not opts.startswith(("/", "@")):
            opts = opts + "," + GAME_OPTIONS if opts else GAME_OPTIONS
        # -D : mode wizard ; -@ : personnage tiré au hasard, sans question
        extra = "".join("%s=%s " % (k, shlex.quote(v))
                        for k, v in (env or {}).items())
        return "cd %s && %sHACKDIR=%s NETHACKOPTIONS=%s %s -D -@" % (
            shlex.quote(d), extra, shlex.quote(d), shlex.quote(opts),
            shlex.quote(os.path.join(d, "nethack")))

    def start_game(self, env=None):
        """Lance NetHack dans tmux : un panneau ou une fenêtre de la
        session courante, sinon une session à part ouverte dans un
        nouveau terminal. Renvoie True si le jeu est prêt."""
        if not os.access(os.path.join(self.hackdir, "nethack"), os.X_OK):
            self.msg = "Pas d'exécutable nethack dans %s." % self.hackdir
            return False
        try:
            busy = subprocess.run(["pgrep", "-x", "nethack"],
                                  capture_output=True).returncode == 0
        except OSError:
            busy = False
        if busy:
            # même verrou de partie : un second jeu ne démarrerait pas
            self.msg = "Une partie de NetHack est déjà en cours."
            return False
        cmd = self.game_command(env)
        attach = None
        if os.environ.get("TMUX"):
            here = os.environ.get("TMUX_PANE", "")
            width = int(self.tmux("display-message", "-p", "-t", here,
                                  "#{window_width}") or 0)
            # assez large : panneau à droite (80 colonnes pour le jeu),
            # sinon une fenêtre tmux à part
            if width >= 170:
                pane = self.tmux("split-window", "-h", "-d", "-t", here,
                                 "-P", "-F", "#{pane_id}", cmd)
                where = "panneau tmux à droite"
            else:
                pane = self.tmux("new-window", "-d", "-n", "nethack", "-P",
                                 "-F", "#{pane_id}", cmd)
                where = "fenêtre tmux « nethack »"
        else:
            self.tmux("kill-session", "-t", GAME_SESSION)
            pane = self.tmux("new-session", "-d", "-s", GAME_SESSION,
                             "-x", "100", "-y", "32", "-P", "-F",
                             "#{pane_id}", cmd)
            attach = "tmux attach -t " + GAME_SESSION
            where = "session tmux « %s »" % GAME_SESSION
            term = (os.environ.get("TERMINAL")
                    or shutil.which("x-terminal-emulator"))
            if pane and os.environ.get("DISPLAY") and term:
                try:
                    subprocess.Popen([term, "-e", "tmux", "attach", "-t",
                                      GAME_SESSION],
                                     stdin=subprocess.DEVNULL,
                                     stdout=subprocess.DEVNULL,
                                     stderr=subprocess.DEVNULL,
                                     start_new_session=True)
                    attach = None
                except OSError:
                    pass
        if not pane:
            self.msg = "Impossible de lancer le jeu dans tmux."
            return False
        self.game_pane = pane
        self.game_where = where
        self.msg = "Lancement de NetHack…"
        self.draw()
        # attend que l'écran du jeu ne bouge plus
        last, stable, end = None, 0, time.time() + 15
        while time.time() < end and stable < 3:
            time.sleep(0.4)
            screen = self.tmux("capture-pane", "-p", "-t", pane)
            if screen is None:
                self.game_pane = None
                self.msg = "Le jeu s'est arrêté au démarrage."
                return False
            stable = stable + 1 if screen.strip() and screen == last else 0
            last = screen
        if attach:
            self.message_box("NetHack lancé", "\n".join([
                "Le jeu tourne dans la session tmux « %s »." % GAME_SESSION,
                "Pour le voir, dans un autre terminal :",
                "  " + attach,
            ]))
        return True

    def load_in_game(self, name):
        """Envoie #wizloaddes au jeu ; Échap ferme d'abord un éventuel
        message ou menu en attente."""
        p = self.game_pane
        self.tmux("send-keys", "-t", p, "Escape")
        time.sleep(0.3)
        self.tmux("send-keys", "-t", p, "-l", "#")
        time.sleep(0.2)
        self.tmux("send-keys", "-t", p, "-l", "wizloaddes")
        self.tmux("send-keys", "-t", p, "Enter")
        time.sleep(0.3)
        self.tmux("send-keys", "-t", p, "-l", name)
        self.tmux("send-keys", "-t", p, "Enter")
        self.msg = ("Carte chargée dans NetHack (%s, %s) ; t la recharge "
                    "après une modification." % (name, self.game_where))
