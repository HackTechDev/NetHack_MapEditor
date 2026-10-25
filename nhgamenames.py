"""Noms des monstres, objets et pièges tels que le jeu les affiche.

La branche cybernethack de NetHack traduit à l'affichage, par un
catalogue GNU gettext (fr.mo, ou fr@cyber.mo pour le thème cyberpunk)
installé dans le répertoire du jeu. Les scripts de niveau gardent les
noms anglais (des.monster("jackal")) ; l'éditeur montre à côté le nom
vu en jeu (« chien errant »), lu dans le même catalogue que le jeu.
"""

import gettext
import os
import re

# Thème par défaut du jeu sans option language (NHI18N_DEFAULT_LANG
# dans include/unixconf.h de cybernethack)
DEFAULT_LANG = "fr@cyber"

# Objets dont le nom se compose : « potion of %s » -> « stim de %s »
PREFIXES = ("potion of ", "scroll of ", "wand of ", "ring of ",
            "spellbook of ")
# initiales de i18n_vowel_start() (src/nhi18n.c)
VOWELS = "aeiouyAEIOUYàâéèêëîïôûÉ"


def game_language(env=None, rc_path=None):
    """Langue choisie par le joueur : NETHACKOPTIONS, puis ~/.nethackrc
    (la dernière option language l'emporte), sinon le défaut du jeu."""
    env = os.environ if env is None else env
    found = None
    texts = []
    rc = rc_path or env.get("NETHACKRC") or os.path.expanduser(
        "~/.nethackrc")
    try:
        with open(rc, encoding="utf-8", errors="replace") as f:
            texts += [line.split("=", 1)[1] for line in f
                      if line.strip().upper().startswith("OPTIONS=")]
    except OSError:
        pass
    opts = env.get("NETHACKOPTIONS", "")
    if not opts.startswith("@"):        # « @fichier » : un autre .nethackrc
        texts.append(opts)
    for t in texts:
        for opt in t.split(","):
            m = re.match(r"\s*(?:language|lang)\s*:\s*(\S+)", opt)
            if m:
                found = m.group(1)
    return found or DEFAULT_LANG


class GameNames:
    """Traductions du jeu ; sans catalogue (jeu en anglais, répertoire
    introuvable), chaque nom reste le nom anglais."""

    def __init__(self, hackdir=None, lang=None, trap_names=None):
        self.lang = lang or DEFAULT_LANG
        self.trap_names = trap_names or {}
        self.cat = None
        self.path = None
        if hackdir and self.lang not in ("en", "C", "POSIX"):
            # fr@cyber.mo, puis fr.mo, comme i18n_datafile() du jeu
            for name in dict.fromkeys([self.lang, self.lang.split("@")[0]]):
                path = os.path.join(hackdir, name + ".mo")
                try:
                    with open(path, "rb") as f:
                        self.cat = gettext.GNUTranslations(f)
                    self.path = path
                    break
                except (OSError, ValueError):     # absent ou illisible
                    continue

    def active(self):
        return self.cat is not None

    def _ctx(self, ctx, s):
        return self.cat.pgettext(ctx, s) if self.cat else s

    def monster(self, name):
        return self._ctx("monster", name)

    def object(self, name):
        if not self.cat:
            return name
        for pre in PREFIXES:
            if name.startswith(pre):
                en = name[len(pre):]
                inner = self.cat.npgettext("object", en, en, 1)
                fmt = pre + "%s"
                elided = self.cat.npgettext("object-elided", fmt, fmt, 1)
                # obj_pattern() (objnam.c) : élision devant une voyelle
                if inner[:1] in VOWELS and elided != fmt:
                    return elided % inner
                return self.cat.npgettext("object", fmt, fmt, 1) % inner
        return self.cat.npgettext("object", name, name, 1)

    def trap(self, des_name):
        return self._ctx("trap", self.trap_names.get(des_name, des_name))

    def place(self, name):
        """Nom d'un donjon en jeu (« The Dungeons of Doom » -> « Night
        City ») : dungeon.c le traduit par _(dname), sans contexte."""
        return self.cat.gettext(name) if self.cat else name

    def name(self, kind, value):
        """Nom vu en jeu d'une valeur d'entité, ou None s'il est le même
        que dans le script (ou sans objet : classe, aléatoire)."""
        if not self.cat or not isinstance(value, str) or len(value) < 2:
            return None
        shown = {"monster": self.monster, "object": self.object,
                 "trap": self.trap, "place": self.place}.get(kind, lambda v: v)(value)
        return shown if shown != value else None

    def label(self, kind, value):
        """« jackal (chien errant) », ou la valeur seule."""
        shown = self.name(kind, value)
        return "%s (%s)" % (value, shown) if shown else str(value)


def game_texts(source_dirs, base, lang=None):
    """Textes aléatoires du jeu (base « epitaph » ou « engrave ») : le
    fichier source dat/<base>-<langue>.txt de la langue du jeu, à défaut
    celui de la langue sans thème, puis l'anglais ; sans les commentaires."""
    lang = lang or DEFAULT_LANG
    names = ["%s-%s.txt" % (base, lang)]
    if "@" in lang:
        names.append("%s-%s.txt" % (base, lang.split("@")[0]))
    names.append(base + ".txt")
    for d in source_dirs:
        for n in names:
            try:
                with open(os.path.join(d, "dat", n), encoding="utf-8",
                          errors="replace") as f:
                    lines = [line.strip() for line in f]
            except OSError:
                continue
            return [t for t in dict.fromkeys(lines)
                    if t and not t.startswith("#")]
    return []
