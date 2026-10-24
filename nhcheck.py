"""Vérifications d'un niveau : connexité et règles de NetHack.

Chaque fonction renvoie une liste de messages ; le premier caractère
indique la gravité : « ! » erreur, « ? » à vérifier, « - » remarque.
"""

import nhlevel

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
            out.append("- Connexité : l'escalier descendant (%d,%d) n'est "
                       "accessible que par un passage secret (S ou H)." % b)
        elif b in reachable(lvl, a, secret=True, liquid=True):
            out.append("? Connexité : l'escalier descendant (%d,%d) n'est "
                       "accessible qu'en traversant l'eau ou la lave." % b)
        else:
            out.append("! Connexité : l'escalier descendant (%d,%d) est "
                       "inaccessible depuis le montant (%d,%d)." % (b + a))
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
                out.append("- Zone de %d case(s), par exemple en (%d,%d), "
                           "accessible seulement par l'eau ou la lave."
                           % (len(z), x, y))
                continue
            edge = any(p[0] in (0, lvl.w - 1) or p[1] in (0, lvl.h - 1)
                       for p in z)
            note = (" ; elle touche le bord de la carte et peut être "
                    "reliée au reste du niveau" if edge and not full
                    else "")
            out.append("? Zone fermée de %d case(s), par exemple en "
                       "(%d,%d)%s." % (len(z), x, y, note))
        if len(closed) > 8:
            out.append("? … et %d autre(s) zone(s) séparée(s)."
                       % (len(closed) - 8))
    return out
