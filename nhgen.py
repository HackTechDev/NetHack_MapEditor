"""Générateurs de niveaux complets pour l'assistant (n → assistant) :
salles reliées par des couloirs, labyrinthe, caverne, grande salle ; puis
escaliers, monstres, objets et pièges posés sur des cases praticables.

Toutes les fonctions prennent un random.Random : un même germe redonne
le même niveau (tests)."""

import collections

from nhme_common import maze_cells

ROCK, FLOOR, CORR, DOOR = " ", ".", "#", "+"


def blank(w, h, c=ROCK):
    return [[c] * w for _ in range(h)]


# --- salles et couloirs ----------------------------------------------------
def rooms_and_corridors(w, h, n, rng, tries=40):
    """Jusqu'à n salles murées, sans chevauchement, reliées par des
    couloirs en L qui n'entrent dans une salle que par une porte au
    milieu d'un mur. Renvoie (grille, salles) ; salle = (x1, y1, x2, y2)
    murs compris."""
    for _attempt in range(tries):
        grid, rooms = blank(w, h), []
        for _i in range(n * 30):
            if len(rooms) == n:
                break
            rw, rh = rng.randint(5, min(14, w - 2)), rng.randint(4, min(8, h - 2))
            if rw < 5 or rh < 4:
                break
            x1, y1 = rng.randint(0, w - rw), rng.randint(0, h - rh)
            r = (x1, y1, x1 + rw - 1, y1 + rh - 1)
            # une case de roche au moins entre deux salles
            if any(r[0] <= o[2] + 2 and o[0] <= r[2] + 2
                   and r[1] <= o[3] + 2 and o[1] <= r[3] + 2 for o in rooms):
                continue
            rooms.append(r)
        if len(rooms) < min(n, 2):
            continue
        for r in rooms:
            _draw_room(grid, r)
        if _connect(grid, rooms, rng):
            return grid, rooms
    # repli : une seule grande salle
    grid = blank(w, h)
    r = (0, 0, w - 1, h - 1)
    _draw_room(grid, r)
    return grid, [r]


def _draw_room(grid, r):
    x1, y1, x2, y2 = r
    for y in range(y1, y2 + 1):
        for x in range(x1, x2 + 1):
            if y in (y1, y2):
                grid[y][x] = "-"
            elif x in (x1, x2):
                grid[y][x] = "|"
            else:
                grid[y][x] = FLOOR


def _center(r):
    return (r[0] + r[2]) // 2, (r[1] + r[3]) // 2


def _l_path(a, b, horizontal_first):
    (ax, ay), (bx, by) = a, b
    pts = []
    corner = (bx, ay) if horizontal_first else (ax, by)
    for (x0, y0), (x1, y1) in ((a, corner), (corner, b)):
        dx = (x1 > x0) - (x1 < x0)
        dy = (y1 > y0) - (y1 < y0)
        x, y = x0, y0
        while (x, y) != (x1, y1):
            pts.append((x, y))
            x, y = x + dx, y + dy
    pts.append(b)
    return pts


def _inside(r, p, walls=True):
    m = 0 if walls else 1
    return r[0] + m <= p[0] <= r[2] - m and r[1] + m <= p[1] <= r[3] - m


def _clean_path(grid, rooms, a, b, path):
    """Le couloir ne touche aucune autre salle et traverse le mur de
    chacune de ses deux salles une seule fois, hors des coins et pas à
    côté d'une porte déjà percée."""
    walls = []
    for p in path:
        ra = [r for r in rooms if _inside(r, p)]
        if any(r not in (a, b) for r in ra):
            return None
        if ra and not _inside(ra[0], p, walls=False):
            r = ra[0]
            if p[0] in (r[0], r[2]) and p[1] in (r[1], r[3]):
                return None             # coin de mur
            x, y = p
            if any(grid[y + dy][x + dx] == DOOR for dx, dy in
                   ((-1, 0), (1, 0), (0, -1), (0, 1))
                   if 0 <= y + dy < len(grid) and 0 <= x + dx < len(grid[0])):
                return None             # porte déjà voisine
            walls.append(p)
    return walls if len(walls) == 2 else None


def _connect(grid, rooms, rng):
    """Relie les salles (arbre couvrant des plus proches, plus quelques
    boucles). False si une salle reste isolée."""
    parent = list(range(len(rooms)))

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i
    pairs = sorted(((abs(_center(a)[0] - _center(b)[0])
                     + abs(_center(a)[1] - _center(b)[1]), i, j)
                    for i, a in enumerate(rooms)
                    for j, b in enumerate(rooms) if i < j))
    extra = max(1, len(rooms) // 3)
    for _d, i, j in pairs:
        joined = find(i) == find(j)
        if joined and (extra <= 0 or rng.random() < 0.5):
            continue
        a, b = rooms[i], rooms[j]
        for hf in rng.sample((True, False), 2):
            path = _l_path(_center(a), _center(b), hf)
            doors = _clean_path(grid, rooms, a, b, path)
            if doors:
                break
        else:
            continue
        for p in path:
            if p in doors:
                grid[p[1]][p[0]] = DOOR
            elif not any(_inside(r, p) for r in (a, b)):
                grid[p[1]][p[0]] = CORR
        if joined:
            extra -= 1
        parent[find(i)] = find(j)
    return len({find(i) for i in range(len(rooms))}) == 1


# --- caverne ---------------------------------------------------------------
def cave(w, h, rng, fill=45, steps=5):
    """Caverne de type « mines » : automate cellulaire (une case devient
    roche si 5 voisines ou plus le sont), puis seule la plus grande zone
    est gardée."""
    g = [[ROCK if x in (0, w - 1) or y in (0, h - 1)
          or rng.random() * 100 < fill else FLOOR for x in range(w)]
         for y in range(h)]
    for _s in range(steps):
        n = [row[:] for row in g]
        for y in range(1, h - 1):
            for x in range(1, w - 1):
                rock = sum(g[y + dy][x + dx] == ROCK
                           for dy in (-1, 0, 1) for dx in (-1, 0, 1))
                n[y][x] = ROCK if rock >= 5 else FLOOR
        g = n
    keep = max(zones(g), key=len, default=set())
    return [[FLOOR if (x, y) in keep else ROCK for x in range(w)]
            for y in range(h)]


def zones(grid, ok=lambda c: c not in " -|"):
    """Zones praticables (4 directions), en ensembles de cases."""
    h, w = len(grid), len(grid[0])
    left = {(x, y) for y in range(h) for x in range(w) if ok(grid[y][x])}
    out = []
    while left:
        start = left.pop()
        z, stack = {start}, [start]
        while stack:
            x, y = stack.pop()
            for p in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
                if p in left:
                    left.discard(p)
                    z.add(p)
                    stack.append(p)
        out.append(z)
    return out


# --- labyrinthe et grande salle --------------------------------------------
def maze(w, h, rng, wall="-", loops=0):
    cells = maze_cells(0, 0, w - 1, h - 1, rng, wall, FLOOR, loops)
    g = blank(w, h)
    for (x, y), c in cells.items():
        g[y][x] = c
    return g


def big_room(w, h, rng, features=8):
    """Une grande salle murée, avec des piliers, fontaines, arbres et
    bassins semés au hasard."""
    g = blank(w, h)
    _draw_room(g, (0, 0, w - 1, h - 1))
    spots = [(x, y) for y in range(2, h - 2) for x in range(2, w - 2)]
    for x, y in rng.sample(spots, min(features, len(spots))):
        c = rng.choice("{TP-")
        if c == "-":                    # pilier 2x2
            for dx in (0, 1):
                for dy in (0, 1):
                    if x + dx < w - 2 and y + dy < h - 2:
                        g[y + dy][x + dx] = "-"
        else:
            g[y][x] = c
    return g


# --- peuplement ------------------------------------------------------------
def distances(grid, start):
    """Distance (4 directions) de start à chaque case praticable."""
    h, w = len(grid), len(grid[0])
    dist, todo = {start: 0}, collections.deque([start])
    while todo:
        x, y = todo.popleft()
        for p in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
            if (0 <= p[0] < w and 0 <= p[1] < h and p not in dist
                    and grid[p[1]][p[0]] in ".#+"):
                dist[p] = dist[(x, y)] + 1
                todo.append(p)
    return dist


def populate(grid, rng, monsters=0, objects=0, traps=0):
    """Escalier montant sur une case de sol, descendant sur la case la
    plus éloignée, puis monstres, objets et pièges (tirés au hasard par
    NetHack) sur des cases de sol libres. Renvoie [(genre, x, y, valeur)]."""
    floor = [(x, y) for y, row in enumerate(grid)
             for x, c in enumerate(row) if c == FLOOR]
    if len(floor) < 2:
        return []
    up = rng.choice(floor)
    dist = distances(grid, up)
    down = max((p for p in floor if p in dist), key=lambda p: dist[p])
    out = [("stair", up[0], up[1], "up"), ("stair", down[0], down[1], "down")]
    free = [p for p in floor if p not in (up, down)]
    rng.shuffle(free)
    for kind, n in (("monster", monsters), ("object", objects),
                    ("trap", traps)):
        for _i in range(n):
            if not free:
                break
            x, y = free.pop()
            out.append((kind, x, y, None))
    return out
