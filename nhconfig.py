"""Fichier de configuration de l'éditeur (~/.config/nhmapedit/config).

Format INI ; toutes les clés sont facultatives. Voir docs/config.exemple.
"""

import configparser
import os

import nhlevel
from nhi18n import _

COLORS = ["CLR_BLACK", "CLR_RED", "CLR_GREEN", "CLR_BROWN", "CLR_BLUE",
          "CLR_MAGENTA", "CLR_CYAN", "CLR_GRAY", "NO_COLOR", "CLR_ORANGE",
          "CLR_BRIGHT_GREEN", "CLR_YELLOW", "CLR_BRIGHT_BLUE",
          "CLR_BRIGHT_MAGENTA", "CLR_BRIGHT_CYAN", "CLR_WHITE"]
YES = {"oui": True, "o": True, "yes": True, "y": True, "1": True,
       "vrai": True, "true": True, "non": False, "n": False, "no": False,
       "0": False, "faux": False, "false": False}
# Noms des touches spéciales dans la section [touches]
KEY_NAMES = {"espace": " ", "space": " ", "entree": "\n", "entrée": "\n",
             "tab": "\t", "echap": "\x1b", "échap": "\x1b"}


def default_path(config_dir):
    return os.environ.get("NHMAPEDIT_CONFIG") or os.path.join(config_dir,
                                                               "config")


def _key(s):
    """Touche de la section [touches] : un caractère, ctrl-x, ou un nom."""
    low = s.lower()
    if low in KEY_NAMES:
        return KEY_NAMES[low]
    if low.startswith("ctrl-") and len(s) == 6 and s[5].isalpha():
        return chr(ord(s[5].lower()) - 96)
    if len(s) == 1:
        return s
    raise ValueError(s)


def load(path):
    """Lit le fichier. Renvoie (réglages, erreurs) ; réglages ne contient
    que les clés présentes et valides."""
    cfg, errs = {}, []
    if not os.path.isfile(path):
        return cfg, errs
    # les clés de [couleurs] et [touches] sont sensibles à la casse
    cp = configparser.ConfigParser(interpolation=None,
                                   inline_comment_prefixes=(";",))
    cp.optionxform = str
    try:
        with open(path, encoding="utf-8") as f:
            cp.read_file(f)
    except (OSError, configparser.Error, UnicodeDecodeError) as e:
        return cfg, ["%s : %s" % (path, e)]

    def bad(section, key, why):
        errs.append("[%s] %s : %s" % (section, key, why))

    for key, val in cp.items("jeu") if cp.has_section("jeu") else []:
        if key in ("repertoire", "répertoire", "hackdir"):
            cfg["hackdir"] = os.path.expanduser(val)
        elif key == "dungeon":
            cfg["dungeon"] = os.path.expanduser(val)
        elif key == "langue":
            # langue du jeu (fr@cyber, fr, en) ; défaut : celle du
            # .nethackrc, sinon le thème par défaut du jeu
            cfg["game_lang"] = val.strip()
        elif key == "palette":
            # rendu jeu : auto (néon du thème cyberpunk et .nethackrc),
            # aucune, ou le chemin d'un .nethackrc
            low = val.strip().lower()
            cfg["palette"] = (low if low in ("auto", "aucune")
                              else os.path.expanduser(val.strip()))
        else:
            bad("jeu", key, _("clé inconnue"))
    for key, val in (cp.items("editeur") if cp.has_section("editeur")
                     else []):
        low = val.strip().lower()
        if key == "taille":
            try:
                w, h = (int(v) for v in low.split("x"))
                cfg["size"] = (max(1, min(w, nhlevel.MAX_W)),
                               max(1, min(h, nhlevel.MAX_H)))
            except ValueError:
                bad("editeur", key, _("LARGEURxHAUTEUR attendu"))
        elif key in ("regles", "règles", "entites", "entités"):
            if low not in YES:
                bad("editeur", key, _("oui ou non attendu"))
            else:
                cfg[{"regles": "rulers", "règles": "rulers"}.get(
                    key, "entities")] = YES[low]
        elif key == "unicode":
            if low == "auto":
                pass
            elif low in YES:
                cfg["unicode"] = YES[low]
            else:
                bad("editeur", key, _("auto, oui ou non attendu"))
        elif key == "sauvegarde":
            try:
                cfg["autosave"] = max(0, int(low))
            except ValueError:
                bad("editeur", key, _("nombre de secondes attendu (0 : "
                    "désactivée)"))
        elif key == "langue":
            if low in ("fr", "en", "auto"):
                cfg["lang"] = low
            else:
                bad("editeur", key, _("fr, en ou auto attendu"))
        else:
            bad("editeur", key, _("clé inconnue"))
    for key, val in (cp.items("couleurs") if cp.has_section("couleurs")
                     else []):
        # « # » et l'espace ne peuvent pas être des clés INI
        c = {"roche": " ", "couloir": "#"}.get(key.lower(), key)
        col = val.strip().upper()
        if not col.startswith(("CLR_", "NO_")):
            col = "CLR_" + col
        if c not in nhlevel.TERRAIN_CHARS:
            bad("couleurs", key, _("terrain inconnu"))
        elif col not in COLORS:
            bad("couleurs", key, _("couleur inconnue (%s)") % ", ".join(
                c[4:].lower() for c in COLORS if c.startswith("CLR_")))
        else:
            cfg.setdefault("colors", {})[c] = col
    for key, val in (cp.items("touches") if cp.has_section("touches")
                     else []):
        try:
            cfg.setdefault("keys", {})[_key(key)] = _key(val.strip())
        except ValueError as e:
            bad("touches", key, _("touche invalide %s") % e)
    for s in cp.sections():
        if s not in ("jeu", "editeur", "couleurs", "touches"):
            errs.append(_("[%s] : section inconnue") % s)
    return cfg, errs
