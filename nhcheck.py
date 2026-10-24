"""Vérifications d'un niveau : connexité et règles de NetHack.

Chaque fonction renvoie une liste de messages ; le premier caractère
indique la gravité : « ! » erreur, « ? » à vérifier, « - » remarque.
"""

import glob
import os
import shutil
import subprocess
import tempfile

import nhlevel
from nhi18n import LANG, _

# Terrain praticable à pied (« x » : transparent, le terrain d'avant reste
# en place ; on le suppose praticable)
WALK = set(".#{\\KIACx")
DOORS = set("+")            # porte : pas de déplacement en diagonale
SECRET = set("SH")          # porte et couloir secrets
LIQUID = set("WP}L")        # eau, bassin, douves, lave (à franchir)
# États de porte qui laissent passer en diagonale (pas de porte, cassée)
OPEN_DOOR = {"nodoor", "broken"}


def _passable(lvl, secret, liquid):
    ok = WALK | DOORS
    if secret:
        ok |= SECRET
    if liquid:
        ok |= LIQUID
    return lambda c: c in ok


def _door_cells(lvl):
    """Cases de porte intacte (pas de diagonale), selon la carte et les
    entités des.door."""
    doors = {(x, y) for y in range(lvl.h) for x in range(lvl.w)
             if lvl.grid[y][x] in "+S"}
    for e in lvl.entities:
        if e.kind == "door":
            if e.value in OPEN_DOOR:
                doors.discard((e.x, e.y))
            else:
                doors.add((e.x, e.y))
    return doors


def reachable(lvl, start, secret=True, liquid=False):
    """Cases atteignables depuis start, en huit directions (pas de
    diagonale vers ou depuis une porte intacte)."""
    ok = _passable(lvl, secret, liquid)
    doors = _door_cells(lvl)
    seen, stack = {start}, [start]
    while stack:
        x, y = stack.pop()
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                nx, ny = x + dx, y + dy
                if (nx, ny) in seen or not (0 <= nx < lvl.w
                                            and 0 <= ny < lvl.h):
                    continue
                if not ok(lvl.grid[ny][nx]):
                    continue
                if dx and dy and ((x, y) in doors or (nx, ny) in doors):
                    continue
                seen.add((nx, ny))
                stack.append((nx, ny))
    return seen


def _stairs(lvl, d):
    return [(e.x, e.y) for e in lvl.entities
            if e.kind in ("stair", "ladder") and e.value == d]


def zones(lvl):
    """Zones praticables séparées (passages secrets compris, sans
    traverser l'eau ni la lave), de la plus grande à la plus petite."""
    ok = _passable(lvl, True, False)
    left = {(x, y) for y in range(lvl.h) for x in range(lvl.w)
            if ok(lvl.grid[y][x])}
    out = []
    while left:
        z = reachable(lvl, next(iter(left)))
        z &= left | z
        left -= z
        out.append(z)
    out.sort(key=len, reverse=True)
    return out


def connectivity(lvl):
    """L'escalier descendant est-il accessible depuis le montant ? Et
    quelles zones restent fermées ?"""
    out = []
    ups, downs = _stairs(lvl, "up"), _stairs(lvl, "down")
    if ups and downs:
        a, b = ups[0], downs[0]
        if b in reachable(lvl, a, secret=False):
            pass
        elif b in reachable(lvl, a, secret=True):
            out.append(_("- Connexité : l'escalier descendant (%d,%d) n'est "
                         "accessible que par un passage secret (S ou H).") % b)
        elif b in reachable(lvl, a, secret=True, liquid=True):
            out.append(_("? Connexité : l'escalier descendant (%d,%d) n'est "
                         "accessible qu'en traversant l'eau ou la lave.") % b)
        else:
            out.append(_("! Connexité : l'escalier descendant (%d,%d) est "
                         "inaccessible depuis le montant (%d,%d).") % (b + a))
    zs = zones(lvl)
    if len(zs) > 1:
        main = None
        if ups:
            main = next((z for z in zs if ups[0] in z), None)
        main = main or zs[0]
        full = lvl.w >= nhlevel.MAP_X_LIM - 1 and lvl.h >= 20
        closed = [z for z in zs if z is not main]
        wet = reachable(lvl, next(iter(main)), liquid=True)
        for z in closed[:8]:
            x, y = min(z, key=lambda p: (p[1], p[0]))
            if (x, y) in wet:
                out.append(_("- Zone de %d case(s), par exemple en (%d,%d), "
                             "accessible seulement par l'eau ou la lave.")
                           % (len(z), x, y))
                continue
            edge = any(p[0] in (0, lvl.w - 1) or p[1] in (0, lvl.h - 1)
                       for p in z)
            note = (_(" ; elle touche le bord de la carte et peut être "
                      "reliée au reste du niveau") if edge and not full
                    else "")
            out.append(_("? Zone fermée de %d case(s), par exemple en "
                         "(%d,%d)%s.") % (len(z), x, y, note))
        if len(closed) > 8:
            out.append(_("? … et %d autre(s) zone(s) séparée(s).")
                       % (len(closed) - 8))
    return out


FLIPS = {1: _("haut/bas"), 2: _("gauche/droite"),
         3: _("dans les deux sens")}
WALLS = set("-|")


def temple_regions(lvl):
    """Cases des salles « temple » déclarées par des.region() à
    coordonnées littérales ; None si une région temple n'est pas lisible
    (on ne peut alors rien affirmer)."""
    if not lvl.source:
        return set()
    cells = set()
    for c in nhlevel.scan_des_calls(lvl.source[0]):
        if c["name"] != "region":
            continue
        try:
            vals = nhlevel._parse_args(c["args"], 0, len(c["args"]))[0]
            t = nhlevel._to_py(vals[0]) if len(vals) == 1 else None
        except nhlevel.NotLiteral:
            t = None
        if not isinstance(t, dict):
            if "temple" in lvl.source[0][c["start"]:c["end"]]:
                return None
            continue
        if t.get("type") != "temple":
            continue
        r = t.get("region")
        if not (isinstance(r, list) and len(r) == 4
                and all(isinstance(v, int) for v in r)):
            return None
        x1, y1, x2, y2 = r
        if t.get("irregular"):
            # salle de forme libre : remplissage depuis le premier point
            stack, room = [(x1, y1)], set()
            while stack:
                x, y = stack.pop()
                if ((x, y) in room or not (0 <= x < lvl.w and 0 <= y < lvl.h)
                        or lvl.grid[y][x] in WALLS | set("+S ")):
                    continue
                room.add((x, y))
                stack += [(x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)]
            cells |= room
        else:
            cells |= {(x, y) for x in range(x1, x2 + 1)
                      for y in range(y1, y2 + 1)}
    return cells


def _door_problems(lvl, x, y):
    g = lvl.grid

    def wall(px, py):
        return 0 <= px < lvl.w and 0 <= py < lvl.h and g[py][px] in WALLS

    h = wall(x - 1, y) and wall(x + 1, y)
    v = wall(x, y - 1) and wall(x, y + 1)
    if h and v or (wall(x - 1, y) or wall(x + 1, y)) and (
            wall(x, y - 1) or wall(x, y + 1)) and not (h or v):
        return _("! Porte en (%d,%d) dans un coin de mur.") % (x, y)
    if not (h or v):
        return _("? Porte en (%d,%d) qui n'est pas encadrée par des murs.") % (
            x, y)
    return None


def rules(lvl, monsters=None, objects=None):
    """Règles de NetHack : placement de la carte, entités, portes."""
    out = []
    if lvl.w > nhlevel.MAP_X_LIM:
        out.append(_("! Largeur %d > %d (MAP_X_LIM) : risque de refus "
                     "par NetHack.") % (lvl.w, nhlevel.MAP_X_LIM))
    o = lvl.origin()
    if o:
        x, y = o
        if x < 1 or x + lvl.w > nhlevel.COLNO or y < 0 \
                or y + lvl.h > nhlevel.ROWNO:
            out.append(_("! La carte placée en (%d,%d) déborde du niveau "
                         "(80x21).") % (x, y))
    if lvl.allowed_flips():
        out.append(_("- NetHack peut retourner ce niveau au chargement (%s) "
                     ": f pour un aperçu, drapeau noflip pour l'empêcher.")
                   % FLIPS[lvl.allowed_flips()])
    kinds = [(e.kind, e.value) for e in lvl.entities]
    for d, lab in (("up", _("montant")), ("down", _("descendant"))):
        if ("stair", d) not in kinds and ("ladder", d) not in kinds:
            out.append(_("- Pas d'escalier/échelle %s à position fixe "
                         "(peut être placé ailleurs dans le script).") % lab)
    temples = temple_regions(lvl)
    # NetHack compare les noms sans tenir compte de la casse
    monsters = {n.lower() for n in monsters or ()}
    objects = {n.lower() for n in objects or ()}
    for e in lvl.entities:
        if not (0 <= e.x < lvl.w and 0 <= e.y < lvl.h):
            # permis par NetHack (coordonnées relatives à la carte)
            out.append(_("? %s en (%d,%d) hors de la carte (invisible dans "
                         "l'éditeur).") % (e.describe(), e.x, e.y))
            continue
        t = lvl.grid[e.y][e.x]
        if e.kind == "door":
            # sur un mur, des.door() le remplace par la porte
            if t not in "+S-|":
                out.append(_("? Porte en (%d,%d) sur '%s'.") % (e.x, e.y, t))
        elif t in " -|STZFB":
            out.append(_("! %s en (%d,%d) sur du terrain solide '%s'.") % (
                e.describe(), e.x, e.y, t))
        elif e.kind in ("stair", "ladder", "altar") and t in LIQUID:
            out.append(_("! %s en (%d,%d) dans '%s' (%s).") % (
                e.describe(), e.x, e.y, t, nhlevel.TERRAIN_DESC.get(t, t)))
        elif e.kind in ("stair", "ladder", "altar") and t not in ".#x":
            out.append(_("? %s en (%d,%d) sur '%s' : le terrain sera "
                         "remplacé.") % (e.describe(), e.x, e.y, t))
        if e.kind == "altar" and temples is not None \
                and (e.x, e.y) not in temples:
            out.append(_("? Autel en (%d,%d) hors d'une salle temple "
                         "(des.region type « temple ») : pas de prêtre.")
                       % (e.x, e.y))
        if e.kind == "monster" and e.value and len(e.value) > 1 \
                and monsters and e.value.lower() not in monsters:
            out.append(_("? Monstre inconnu : %s") % e.value)
        if e.kind == "object" and e.value and len(e.value) > 1 \
                and objects and e.value.lower() not in objects:
            out.append(_("? Objet inconnu (vérifiez le nom) : %s") % e.value)
    seen = {}
    for e in lvl.entities:
        if e.kind in ("stair", "ladder"):
            seen.setdefault((e.kind, e.value), []).append(e)
    for (k, v), lst in seen.items():
        if len(lst) > 1:
            out.append(_("! %s %s présent %d fois : un seul est permis par "
                         "niveau.") % (nhlevel.ENTITY_LABEL[k].capitalize(), v,
                                    len(lst)))
    doors = {(x, y) for y in range(lvl.h) for x in range(lvl.w)
             if lvl.grid[y][x] == "+"}
    doors |= {(e.x, e.y) for e in lvl.entities if e.kind == "door"
              and 0 <= e.x < lvl.w and 0 <= e.y < lvl.h}
    for x, y in sorted(doors, key=lambda p: (p[1], p[0])):
        m = _door_problems(lvl, x, y)
        if m:
            out.append(m)
    return out


def check(lvl, monsters=None, objects=None):
    """Toutes les vérifications ; ["Aucun problème détecté."] sinon."""
    out = rules(lvl, monsters, objects) + connectivity(lvl)
    return out or [_("Aucun problème détecté.")]


# ----------------------------------------------------------------------
# Vérification avec le vrai Lua
# ----------------------------------------------------------------------
HERE = os.path.dirname(os.path.abspath(__file__))
SOURCES = os.path.join(HERE, "..", "NetHack-5.0.0")
CACHE = os.path.join(os.environ.get("XDG_CACHE_HOME")
                     or os.path.expanduser("~/.cache"), "nhmapedit")


def lua_sources():
    """Sources de Lua livrées avec NetHack (lib/lua-5.x.y), ou None."""
    found = sorted(glob.glob(os.path.join(SOURCES, "lib", "lua-5.*")))
    return found[-1] if found else None


def find_lua():
    """Interpréteur Lua : $NHMAPEDIT_LUA, lua5.4 ou lua dans le PATH,
    ou celui compilé par build_lua() ; None si aucun."""
    for c in (os.environ.get("NHMAPEDIT_LUA"), "lua5.4", "lua"):
        if c and shutil.which(c):
            return shutil.which(c)
    built = os.path.join(CACHE, "lua", "src", "lua")
    return built if os.access(built, os.X_OK) else None


def build_lua():
    """Compile l'interpréteur Lua des sources de NetHack dans le cache.
    Renvoie son chemin, ou lève OSError avec la sortie de make."""
    src = lua_sources()
    if not src:
        raise OSError(_("sources de Lua introuvables dans %s/lib") % SOURCES)
    dest = os.path.join(CACHE, "lua")
    shutil.rmtree(dest, ignore_errors=True)
    shutil.copytree(src, dest)
    r = subprocess.run(["make", "-C", os.path.join(dest, "src"),
                        "linux-noreadline"], capture_output=True, text=True)
    lua = os.path.join(dest, "src", "lua")
    if r.returncode or not os.access(lua, os.X_OK):
        raise OSError((r.stdout + r.stderr)[-500:])
    return lua


def nhlib():
    for d in (os.environ.get("NHMAPEDIT_DAT"), os.path.join(SOURCES, "dat")):
        if d and os.path.isfile(os.path.join(d, "nhlib.lua")):
            return os.path.join(d, "nhlib.lua")
    return None


def lua_check(text, lua, data):
    """Exécute le script du niveau avec la bibliothèque des factice
    (nhcheck_des.lua). Renvoie les messages, préfixés de « Lua »."""
    with tempfile.TemporaryDirectory() as d:
        level = os.path.join(d, "niveau.lua")
        with open(level, "w", encoding="utf-8") as f:
            f.write(text)
        datafile = os.path.join(d, "donnees.lua")
        with open(datafile, "w", encoding="utf-8") as f:
            f.write("DATA = {\n")
            for key, items in (("monsters", data.get("monsters", [])),
                               ("objects", data.get("objects", []))):
                names = {n.lower() for i in items
                         for n in [i["name"]] + i.get("aliases", [])}
                f.write("  %s = { %s },\n" % (key, ", ".join(
                    nhlevel.lua_value(n) for n in sorted(names))))
            f.write("  traps = { %s },\n}\n" % ", ".join(
                nhlevel.lua_value(t) for t in data.get("traps", [])))
        try:
            r = subprocess.run([lua, os.path.join(HERE, "nhcheck_des.lua"),
                                datafile, nhlib() or "-", level, LANG],
                               capture_output=True, text=True, timeout=20)
        except (OSError, subprocess.SubprocessError) as e:
            return [_("? Lua : impossible de lancer %s (%s).") % (lua, e)]
    out = []
    for line in (r.stdout + r.stderr).splitlines():
        if line[:2] in ("! ", "? "):
            out.append(_("%s Lua, %s") % (line[0], line[2:]))
        elif line.strip():
            out.append(_("? Lua : ") + line.strip())
    return out
