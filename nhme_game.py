"""Intégration avec le jeu : test (tmux, #wizloaddes, THEMERM) et dungeon.lua."""

import getpass
import os
import re
import shlex
import shutil
import subprocess
import time

import nhdungeon
import nhlevel
from nhi18n import _
from nhme_common import (
    Cancel, GAME_OPTIONS, GAME_SESSION, HACKDIRS, LXD_GAME_DIR, LXD_PANICLOG,
    LXD_PUSH, LXD_SSH_DEVICE, TEST_PREFIX)

# Adresses du serveur LXD qui désignent ce poste (lxc lancé sans ssh)
LOCAL_HOSTS = ("", "localhost", "127.0.0.1", "::1")


# Erreurs Lua de NetHack, écrites par impossible() dans le paniclog (en
# anglais, suivies de la pile d'appels) et à l'écran (traduites) :
#   Lua error: 7:nom.lua [string "(nom.lua)"]:7: attempt to call a nil…
#   luaL_loadbuffer: Error loading (nom.lua): [string "(nom.lua)"]:7: …
#   Lua error: 5:nom.lua Unknown trap type (line 7 [string "(nom.lua)"])
LUA_POS = re.compile(r'\[string\s+"\(?([^"()]+?)\)?"\]:(\d+):\s*(.*)')
NHL_POS = re.compile(r'(?:Lua error|Erreur Lua)\s*:\s*\d+:\S+\s+(.*?)\s*'
                     r'\(line (\d+) \[string\s+"\(?([^"()]+?)\)?"\]\)')


def game_errors(text, name):
    """Erreurs Lua du fichier name.lua dans text (lignes du paniclog ou
    écran du jeu recollé) : liste de (ligne, message) sans doublon."""
    out = []
    for raw in text.splitlines():
        if raw[:1].isspace():
            continue                # pile d'appels du paniclog
        m = NHL_POS.search(raw)
        if m and m.group(3) == name + ".lua":
            err = (int(m.group(2)), m.group(1).strip())
        else:
            m = LUA_POS.search(raw)
            if not (m and m.group(1) == name + ".lua"):
                continue
            err = (int(m.group(2)), m.group(3).strip())
        if err not in out:
            out.append(err)
    return out


def screen_messages(screen):
    """Texte de la fenêtre des messages d'un écran de NetHack capturé
    par tmux, recollé en une ligne : le jeu coupe les messages longs à
    la largeur de son cadre (« │…│ ») et ajoute « >> » (--More--)."""
    parts = []
    for line in screen.splitlines():
        if line.startswith("│"):
            seg = line[1:].split("│", 1)[0].rstrip()
            parts.append(re.sub(r"\s*>>\s*$", "", seg).strip())
        elif parts and line.startswith("└"):
            break                   # fin de la fenêtre des messages
    return " ".join(p for p in parts if p)


class GameMixin:
    """Méthodes de l'éditeur (voir nhmapedit.Editor)."""

    # --- retour du jeu --------------------------------------------------
    def paniclog_path(self):
        return os.path.join(self.hackdir, "paniclog") if self.hackdir \
            else None

    def note_test(self, name, text, size=None, lxd=None):
        """Mémorise l'essai en cours : nom, texte copié et taille actuelle
        du paniclog (on ne lira que ce que le jeu y ajoutera) ; lxd : cible
        serveur ({box, host, user}), dont le paniclog fait size octets."""
        if size is None:
            try:
                size = os.path.getsize(self.paniclog_path())
            except (OSError, TypeError):
                size = 0
        self.last_test = {"name": name, "text": text, "size": size,
                          "lxd": lxd}

    def game_feedback(self, auto=False):
        """Touche ! (et après chaque chargement par tmux) : messages
        d'erreur de NetHack sur la dernière copie de test, avec la ligne
        Lua fautive ; le curseur va à l'élément de cette ligne."""
        t = self.last_test
        if not t:
            self.msg = _("Pas encore d'essai dans le jeu (touche t).")
            return []
        found = ""
        if t.get("lxd"):
            # paniclog du serveur, lu dans le conteneur
            found = self.lxc("exec", "-T", t["lxd"]["box"], "--", "sh",
                             "-c", LXD_PANICLOG, "sh", self.lxd_dir(),
                             str(t["size"] + 1),
                             remote=self.lxd_remote(t["lxd"]))[0] or ""
        else:
            try:
                with open(self.paniclog_path(), encoding="utf-8",
                          errors="replace") as f:
                    f.seek(t["size"])
                    found = f.read()
            except (OSError, TypeError):
                pass
        errors = game_errors(found, t["name"])
        if not errors and not t.get("lxd") and self.game_alive():
            # paniclog absent ou désactivé : l'écran du jeu
            screen = self.tmux("capture-pane", "-p", "-J", "-t",
                               self.game_pane) or ""
            errors = game_errors(screen_messages(screen), t["name"])
        if not errors:
            if not auto:
                self.msg = _("NetHack n'a signalé aucune erreur sur %s.lua "
                             "depuis le dernier essai.") % t["name"]
            return []
        lines = t["text"].split("\n")
        report = [_("NetHack signale %d erreur(s) dans %s.lua :")
                  % (len(errors), t["name"]), ""]
        target = None
        for n, msg in errors:
            report.append(_("ligne %d : %s") % (n, msg))
            if 0 < n <= len(lines):
                report.append("    " + lines[n - 1].strip()[:70])
                where = self.element_at_line(lines[n - 1])
                if where and target is None:
                    target = where
            report.append("")
        if target:
            self.cx, self.cy = target[1]
            report.append(_("Le curseur est placé sur : %s.") % target[0])
        self.message_box(_("Retour du jeu"), "\n".join(report))
        self.msg = _("Erreur NetHack ligne %d : %s") % errors[0]
        return errors

    def element_at_line(self, line):
        """(description, (x, y)) de l'entité ou de la région écrite sur
        cette ligne Lua de la copie de test ; None si aucune."""
        m = re.search(r"des\.(\w+)\s*\(", line)
        if not m:
            return None
        kind = m.group(1)
        nums = [int(n) for n in re.findall(r"-?\d+", line[m.end():])]
        pairs = set(zip(nums, nums[1:]))
        for e in self.lvl.entities:
            if e.kind == kind and (e.x, e.y) in pairs:
                return e.describe(), (e.x, e.y)
        for r in self.lvl.regions:
            if r.kind == kind and r.rect and r.rect[:2] in pairs:
                cells = r.cells(self.lvl)
                if cells:
                    return r.describe(), min(cells, key=lambda p: (p[1],
                                                                   p[0]))
        return None

    def edit_dungeon(self):
        """Ajoute, modifie ou supprime un niveau spécial de dungeon.lua."""
        path = self.prompt(_("Fichier dungeon.lua (dans dat/ des sources) : "),
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
            items = [(_("%-24s %d niveau(x) spécial(aux)") % (
                self.dungeon_label(df, d), len(df.levels(d))), i)
                for i, d in enumerate(df.dungeons())]
            try:
                di = self.pick(_("Donjons de %s (%d niveaux spéciaux sur %d)")
                               % (os.path.basename(path),
                                  len(df.all_level_names()),
                                  nhdungeon.LEV_LIMIT), items, di)
            except Cancel:
                return
            df = self.dungeon_levels(df, di)

    def dungeon_label(self, df, d):
        """Nom d'un donjon, suivi de son nom en jeu s'il diffère
        (« The Dungeons of Doom — Night City »)."""
        name = df.dungeon_name(d)
        shown = self.names.name("place", name)
        return "%s — %s" % (name, shown) if shown else name

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
            items.append((_("+ ajouter ce niveau"), "add"))
            hint = _("Entrée/e: modifier  d: supprimer  Échap: retour")
            try:
                i, action = self.pick_action(self.dungeon_label(df, d),
                                             items, sel, hint)
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
                    if self.confirm(_("Retirer %s du donjon ?")
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
            ("name", "str", _("nom du fichier, sans .lua")),
            ("base", "int", _("profondeur (négatif : depuis le bas)")),
            ("range", "int", _("profondeur : tirage en plus")),
            ("chance", "int", _("probabilité de présence, en %")),
            ("nlevels", "int", _("variantes (nom-1.lua … nom-N.lua)")),
            ("alignment", ("choice", nhdungeon.ALIGNMENTS), _("alignement")),
            ("flags", ("flags", nhdungeon.LEVEL_FLAGS), _("drapeaux")),
            ("bonetag", "str", _("lettre des fichiers bones")),
            ("chainlevel", ("choice", df.names_before(di, li)),
             _("base comptée depuis ce niveau")),
        ]
        while True:
            fields = self.form(_("Niveau du donjon"), form, fields, free=False)
            errs = nhdungeon.check_level(df, fields, di, li)
            if not errs:
                return fields
            if not self.confirm(_("%s. Corriger ?") % " ; ".join(errs)
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
            self.msg = _("Erreur d'écriture : %s") % e
            return None
        self.msg = _("Enregistré : %s") % path
        return df

    def after_dungeon_add(self, df, di, fields):
        """Propose de copier la carte dans le répertoire du jeu, puis
        rappelle les étapes pour jouer le niveau."""
        name = fields["name"]
        if fields.get("nlevels"):
            name += "-1"
        dest = None
        if self.hackdir and self.confirm(
                _("Copier la carte dans %s/%s.lua ?") % (self.hackdir, name)):
            dest = os.path.join(self.hackdir, name + ".lua")
            try:
                if not os.path.exists(dest) or self.confirm(
                        _("%s existe. Écraser ?") % dest):
                    with open(dest, "w", encoding="utf-8") as f:
                        f.write(self.lvl.to_lua(name))
                else:
                    dest = None
            except OSError as e:
                self.msg = _("Erreur d'écriture : %s") % e
                dest = None
        self.message_box(_("Niveau ajouté au donjon"), "\n".join([
            _("%s ajouté à « %s » dans :") % (fields["name"],
                                           df.dungeon_name(
                                               df.dungeons()[di])),
            "  " + self.dungeon_path,
            "",
            _("Pour le jouer :"),
            (_("  1. la carte est copiée dans ") + dest) if dest else
            _("  1. copiez la carte sous %s.lua dans le répertoire du jeu")
            % name,
            _("     (le jeu la lit là, puisqu'elle n'est pas dans nhdat) ;"),
            _("  2. dans les sources, « make install » range le nouveau"),
            _("     dungeon.lua dans nhdat ;"),
            _("  3. commencez une nouvelle partie (les parties en cours"),
            _("     gardent l'ancien donjon). En mode wizard, #wizwhere"),
            _("     donne la profondeur des niveaux spéciaux et Ctrl-V"),
            _("     téléporte de niveau."),
        ] + (["", _("Avec nlevels, il faut un fichier par variante :"),
              _("%s-1.lua … %s-%d.lua.") % (fields["name"], fields["name"],
                                          fields["nlevels"])]
             if fields.get("nlevels") else [])))

    @staticmethod
    def is_hackdir(d):
        return bool(d) and any(os.path.isfile(os.path.join(d, f))
                               for f in ("nhdat", "sysconf"))

    def test_copy(self):
        """(nom, texte) de la copie de test : préfixe nhme- (jamais le nom
        d'un niveau de nhdat) et drapeau noflip, car NetHack retourne au
        hasard les niveaux qui ne l'ont pas."""
        base = os.path.splitext(os.path.basename(self.path or "sans-nom"))[0]
        name = TEST_PREFIX + re.sub(r"[^A-Za-z0-9_-]", "_", base)
        flags = self.lvl.flags
        if not {"noflip", "noflipx", "noflipy"} & set(flags):
            self.lvl.flags = flags + ["noflip"]
        try:
            return name, self.lvl.to_lua(base)
        finally:
            self.lvl.flags = flags

    # --- serveur NetHack dans un conteneur LXD --------------------------
    def lxc(self, *args, input=None, timeout=30, remote=None):
        """(sortie, erreur) d'une commande lxc ; sortie None en cas
        d'échec. remote : (adresse, compte) d'un serveur distant, joint
        par ssh (clé SSH, sans question : l'éditeur ne peut pas en poser
        pendant l'affichage)."""
        cmd = ["lxc"] + list(args)
        if remote:
            host, user = remote
            cmd = ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=10",
                   "%s@%s" % (user, host) if user else host,
                   " ".join(shlex.quote(a) for a in cmd)]
        try:
            r = subprocess.run(cmd, capture_output=True, text=True,
                               input=input, timeout=timeout)
        except (OSError, subprocess.SubprocessError) as e:
            return None, str(e)
        if r.returncode:
            return None, (r.stderr or r.stdout).strip()
        return r.stdout, ""

    def lxd_dir(self):
        return self.config.get("lxd_dir") or LXD_GAME_DIR

    @staticmethod
    def lxd_remote(target):
        """(adresse, compte) d'un serveur distant ; None sur ce poste."""
        return (target["host"], target["user"]) if target["host"] else None

    @staticmethod
    def lxd_label(target):
        """« nethack » ou « nethack sur 192.168.1.20 »."""
        if target["host"]:
            return _("%s sur %s") % (target["box"], target["host"])
        return target["box"]

    def lxd_setting(self):
        """Conteneur imposé (clé serveur, ou NHMAPEDIT_LXD) ; « aucun »
        désactive la cible serveur."""
        return (os.environ.get("NHMAPEDIT_LXD")
                or self.config.get("lxd", "")).strip()

    def choose_test_target(self, always=False):
        """Cible des essais (t) : ce poste, ou un serveur LXD (sur ce
        poste ou distant). Demandée la première fois, puis retenue (@ la
        change). Renvoie "local", {box, host, user}, ou None."""
        if self.test_target and not always:
            return self.test_target
        if self.lxd_setting().lower() in ("aucun", "non", "none"):
            self.test_target = "local"
            return "local"
        items = [
            (_("Ce poste : %s") % (self.hackdir or _("répertoire du jeu à "
                                                     "indiquer")),
             "local", {"key": "l", "desc": _(
                 "Copie dans le répertoire du jeu local ; avec tmux, "
                 "l'éditeur lance NetHack en mode wizard et y charge la "
                 "carte.")}),
            (_("Serveur NetHack dans un conteneur LXD…"), "lxd", {
                "key": "s", "desc": _(
                    "Serveur installé par install-serveur-nethack.sh : "
                    "l'adresse IP du serveur est demandée (localhost : "
                    "conteneur sur ce poste) ; un serveur distant est "
                    "joint par ssh, avec une clé SSH.")}),
        ]
        what = self.pick(_("Où essayer la carte ?"), items,
                         "local" if self.test_target in (None, "local")
                         else "lxd")
        if what == "local":
            self.test_target = "local"
        else:
            self.test_target = self.ask_lxd_server()
        return self.test_target

    def ask_lxd_server(self):
        """Demande l'adresse du serveur LXD (et le compte SSH s'il est
        distant), puis trouve le conteneur du jeu. None si introuvable."""
        last = self.lxd_last or {}
        host = self.prompt(
            _("Adresse IP du serveur LXD (localhost : ce poste) : "),
            last.get("host") or self.config.get("lxd_host")
            or "localhost").strip()
        if host.lower() in LOCAL_HOSTS:
            host = None
        user = None
        if host:
            user = self.prompt(
                _("Compte SSH sur %s (membre du groupe lxd) : ") % host,
                last.get("user") or self.config.get("lxd_user")
                or getpass.getuser()).strip() or None
        remote = (host, user) if host else None
        box = self.lxd_setting()
        if not box:
            self.msg = (_("Recherche des conteneurs sur %s…")
                        % (host or "localhost"))
            self.draw()
            out, err = self.lxc("list", "--format", "csv", "-c", "ns",
                                timeout=20, remote=remote)
            if out is None:
                self.msg = _("Serveur LXD %s injoignable : %s") % (
                    host or "localhost",
                    err.splitlines()[-1] if err else "?")
                return None
            boxes = [line.split(",")[0] for line in out.splitlines()
                     if line.endswith(",RUNNING")]
            if not boxes:
                self.msg = (_("Aucun conteneur LXD en marche sur %s.")
                            % (host or "localhost"))
                return None
            if len(boxes) == 1:
                box = boxes[0]
            else:
                box = self.pick(_("Conteneur du serveur NetHack"),
                                [(b, b) for b in boxes],
                                "nethack" if "nethack" in boxes else None)
        self.lxd_last = {"box": box, "host": host, "user": user}
        return self.lxd_last

    def lxd_ssh_command(self, target):
        """Commande ssh des joueurs : clé serveur_ssh, sinon l'adresse
        écoutée par le proxy LXD du conteneur."""
        if self.config.get("lxd_ssh"):
            return self.config["lxd_ssh"]
        listen = (self.lxc("config", "device", "get", target["box"],
                           LXD_SSH_DEVICE, "listen", timeout=10,
                           remote=self.lxd_remote(target))[0] or "").strip()
        m = re.match(r"tcp:\[?([^\]]*?)\]?:(\d+)$", listen)
        if m:
            host = m.group(1)
            if host in ("0.0.0.0", "::", ""):
                host = target["host"] or "localhost"
            port = "" if m.group(2) == "22" else "-p %s " % m.group(2)
            return "ssh %snethack@%s" % (port, host)
        return _("ssh -p 2222 nethack@<adresse de l'hôte>")

    def test_in_lxd(self, target):
        """Copie la carte dans le jeu du serveur LXD (en root, mode 644,
        comme les autres fichiers du jeu) et explique comment l'essayer."""
        name, text = self.test_copy()
        d = self.lxd_dir()
        label = self.lxd_label(target)
        self.msg = _("Copie vers le serveur LXD « %s »…") % label
        self.draw()
        out, err = self.lxc("exec", "-T", target["box"], "--", "sh", "-c",
                            LXD_PUSH, "sh", d, name + ".lua", input=text,
                            remote=self.lxd_remote(target))
        if out is None:
            self.msg = _("Serveur LXD « %s » : copie impossible (%s).") % (
                label, err.splitlines()[-1] if err else "?")
            return
        lines = out.split("\n")
        try:
            size = int(lines[0])
        except ValueError:
            size = 0
        wizard = lines[1].strip() if len(lines) > 1 else ""
        self.note_test(name, text, size, target)
        dest = "%s/%s.lua" % (d, name)
        self.msg = (_("Copié sur le serveur LXD « %s » : %s ; #wizloaddes "
                      "%s en mode debug.") % (label, dest, name))
        if label in self.lxd_told:
            return
        self.lxd_told.add(label)
        report = [
            _("Carte copiée (état actuel, même non enregistré) dans le"),
            _("conteneur « %s » :") % label,
            "  " + dest,
            _("(fichier de root en lecture seule pour les parties, comme"),
            _("le reste du jeu ; drapeau noflip ajouté à la copie)"),
            "",
            _("Pour l'essayer :"),
            _("  1. connectez-vous :  %s") % self.lxd_ssh_command(target),
            _("  2. entrez avec le compte du mode debug%s ;") % (
                " (%s)" % wizard if wizard and wizard != "-aucun-" else ""),
            _("     dans le menu o, mettez  OPTIONS=playmode:debug"),
            _("  3. lancez une partie, tapez  #wizloaddes  puis :  ") + name,
            "",
            _("Après une modification, t recopie la carte : refaites"),
            _("#wizloaddes. ! relève les erreurs Lua que le jeu écrit"),
            _("dans le paniclog du serveur. @ change de cible (ce poste"),
            _("ou le serveur)."),
        ]
        if not wizard or wizard == "-aucun-":
            report += [
                "",
                _("Attention : le mode debug n'est pas encore accordé sur ce"),
                _("serveur (WIZARDS=%s dans sysconf). Inscrivez le compte du")
                % (wizard or "?"),
                _("mode debug par ssh, puis relancez"),
                _("install-serveur-nethack.sh dans un terminal (voir son"),
                _("README, « Activer le mode debug »)."),
            ]
        self.message_box(_("Tester sur le serveur LXD"), "\n".join(report))

    def test_in_game(self):
        """Copie l'état courant de la carte dans le répertoire du jeu,
        local ou du serveur LXD."""
        if self.lvl.theme:
            return self.test_theme()
        target = self.choose_test_target()
        if target is None:
            return
        if target != "local":
            return self.test_in_lxd(target)
        if not self.hackdir:
            d = self.prompt(
                _("Répertoire de données de NetHack (nethackdir) : "),
                HACKDIRS[1], self.path_completer)
            d = os.path.expanduser(d.strip())
            if not self.is_hackdir(d):
                self.msg = _("%s : ni nhdat ni sysconf, répertoire "
                             "refusé.") % d
                return
            self.hackdir = d
            self.load_game_names()
        name, text = self.test_copy()
        dest = os.path.join(self.hackdir, name + ".lua")
        try:
            self.note_test(name, text)
            with open(dest, "w", encoding="utf-8") as f:
                f.write(text)
        except OSError as e:
            self.msg = _("Erreur d'écriture : %s") % e
            return
        self.msg = _("Copié pour test : %s") % dest
        if self.game_alive():
            self.load_in_game(name)
            return
        if shutil.which("tmux") and self.launch is None:
            self.launch = self.confirm(
                _("Lancer NetHack (mode wizard) et y charger la carte ?"))
        if self.launch and shutil.which("tmux"):
            if self.start_game():
                self.load_in_game(name)
                return
        self.message_box(_("Tester dans NetHack"), "\n".join([
            _("Carte copiée (état actuel, même non enregistré) dans :"),
            "  " + dest,
            "",
            _("Dans un autre terminal :"),
            _("  1. lancez le jeu en mode wizard :  nethack -D"),
            _("  2. tapez  #wizloaddes  puis Entrée"),
            _("  3. répondez :  ") + name,
            "",
            _("Après une modification, appuyez de nouveau sur t puis"),
            _("refaites #wizloaddes : inutile de relancer le jeu."),
            _("Ctrl-F révèle toute la carte, Ctrl-T téléporte."),
            _("En cas d'erreur, ! affiche les messages de NetHack et"),
            _("place le curseur sur l'élément de la ligne fautive."),
            _("(La copie de test a le drapeau noflip : sinon NetHack"),
            _("retourne la carte au hasard à chaque chargement.)"),
            "",
            _("Avec tmux installé, l'éditeur peut lancer le jeu et"),
            _("charger la carte lui-même."),
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
        self.message_box(_("Tester une salle à thème"), "\n".join([
            _("themerms.lua est rangé dans nhdat : le jeu ne lit pas une"),
            _("copie posée à côté. Pour voir la salle « %s » :") % name,
            "",
            _("  1. enregistrez (s) : la carte est écrite dans"),
            "     " + self.lvl.theme["path"] + " ;",
            _("  2. dans les sources, lancez « make install » ;"),
            _("  3. lancez le jeu en mode wizard avec la variable THEMERM :"),
            "     THEMERM=%s nethack -D" % shlex.quote(name),
            "",
            _("Chaque salle des niveaux ordinaires est alors cette salle,"),
            _("quand elle y tient. Ctrl-F révèle la carte, Ctrl-V change de"),
            _("niveau pour en générer d'autres."),
        ]))
        if not (self.hackdir and shutil.which("tmux")):
            return
        if self.game_alive():
            self.msg = (_("Une partie lancée par l'éditeur est en cours : "
                          "quittez-la pour relancer avec THEMERM."))
            return
        if self.confirm(_("Lancer NetHack avec THEMERM=%s (après make "
                          "install) ?") % name):
            if self.start_game({"THEMERM": name}):
                self.msg = _("NetHack lancé avec THEMERM=%s (%s).") % (
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
            self.msg = _("Pas d'exécutable nethack dans %s.") % self.hackdir
            return False
        try:
            busy = subprocess.run(["pgrep", "-x", "nethack"],
                                  capture_output=True).returncode == 0
        except OSError:
            busy = False
        if busy:
            # même verrou de partie : un second jeu ne démarrerait pas
            self.msg = _("Une partie de NetHack est déjà en cours.")
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
                where = _("panneau tmux à droite")
            else:
                pane = self.tmux("new-window", "-d", "-n", "nethack", "-P",
                                 "-F", "#{pane_id}", cmd)
                where = _("fenêtre tmux « nethack »")
        else:
            self.tmux("kill-session", "-t", GAME_SESSION)
            pane = self.tmux("new-session", "-d", "-s", GAME_SESSION,
                             "-x", "100", "-y", "32", "-P", "-F",
                             "#{pane_id}", cmd)
            attach = "tmux attach -t " + GAME_SESSION
            where = _("session tmux « %s »") % GAME_SESSION
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
            self.msg = _("Impossible de lancer le jeu dans tmux.")
            return False
        self.game_pane = pane
        self.game_where = where
        self.msg = _("Lancement de NetHack…")
        self.draw()
        # attend que l'écran du jeu ne bouge plus
        last, stable, end = None, 0, time.time() + 15
        while time.time() < end and stable < 3:
            time.sleep(0.4)
            screen = self.tmux("capture-pane", "-p", "-t", pane)
            if screen is None:
                self.game_pane = None
                self.msg = _("Le jeu s'est arrêté au démarrage.")
                return False
            stable = stable + 1 if screen.strip() and screen == last else 0
            last = screen
        if attach:
            self.message_box(_("NetHack lancé"), "\n".join([
                _("Le jeu tourne dans la session tmux « %s ».") % GAME_SESSION,
                _("Pour le voir, dans un autre terminal :"),
                "  " + attach,
            ]))
        return True

    def load_in_game(self, name):
        """Envoie #wizloaddes au jeu ; Échap ferme d'abord un éventuel
        message ou menu en attente."""
        p = self.game_pane
        # après une erreur, le jeu attend plusieurs --More--
        for _i in range(3):
            self.tmux("send-keys", "-t", p, "Escape")
            time.sleep(0.25)
        self.tmux("send-keys", "-t", p, "-l", "#")
        time.sleep(0.2)
        self.tmux("send-keys", "-t", p, "-l", "wizloaddes")
        self.tmux("send-keys", "-t", p, "Enter")
        time.sleep(0.3)
        self.tmux("send-keys", "-t", p, "-l", name)
        self.tmux("send-keys", "-t", p, "Enter")
        self.msg = (_("Carte chargée dans NetHack (%s, %s) ; t la recharge "
                      "après une modification.") % (name, self.game_where))
        # le jeu écrit ses erreurs Lua aussitôt : on les relève
        time.sleep(0.8)
        self.game_feedback(auto=True)
