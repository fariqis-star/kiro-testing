"""Adaptive map solver, v2. Any map, phase-ordered, spike-averse but not spike-phobic.

STRATEGY, exactly as specified:
  1. shortest path that collects every coin and every challenge
  2. all KEYS first, then the doors they unlock
  3. avoid spikes - but take one when no route avoids it
  4. treasure LAST

WHY v2 IS FAST WHERE v1 WAS NOT. v1 enumerated every subset of spikes to skip and
rebuilt the whole route with fresh BFS inside a 2-opt loop; that blew a 120-second
budget. Two changes fix it:

  * SPIKES BECOME A COST, NOT A CASE. Entering an untriggered spike costs PENALTY
    moves. Dijkstra then routes around a spike whenever any detour exists and walks
    through it when none does - which is the requested behaviour, in one pass, with no
    subset enumeration at all.
  * DISTANCES ARE PRECOMPUTED ONCE per phase, and the 2-opt runs on that matrix. No
    graph search inside the improvement loop.

A life is 250 points and a move is ~4 tokens ~= 0.21 points, so a spike is worth about
1,190 moves of detour. PENALTY is set well above any detour a 10x10 map can require.
"""
import heapq
import time
from collections import deque

MOVES = {"down": (1, 0), "up": (-1, 0), "right": (0, 1), "left": (0, -1)}
VALUE = {"c7": 250, "c5": 250, "c1": 100, "c2": 600, "c4": 800, "c3": 550,
         "c18": 500, "c30": 1000, "c31": 1000, "c40": 50, "c41": 50}
DOOR_KEY = {"c30": "c40", "c31": "c41"}
SPIKE = "c8"
PENALTY = 5000          # cost of stepping on a fresh spike, in move-equivalents
LIFE = 250


def label(p):
    return f"{chr(ord('A') + p[1])}{p[0] + 1}"


def find(grid, code):
    return [(r, c) for r in range(len(grid)) for c in range(len(grid[0]))
            if grid[r][c] == code]


def valid_map(grid):
    if not grid or not isinstance(grid, list) or len(grid) < 5:
        return False
    w = len(grid[0]) if isinstance(grid[0], list) else 0
    if w < 5 or any(not isinstance(r, list) or len(r) != w for r in grid):
        return False
    if any(not isinstance(c, str) for r in grid for c in r):
        return False
    return (len(find(grid, "player")) == 1 and len(find(grid, "treasure")) == 1
            and len(find(grid, "wall")) > 0)


def dijkstra(grid, src, blocked, triggered):
    """Cheapest paths from src. A fresh spike costs PENALTY, so it is avoided if
    anything else exists and used when nothing else does."""
    R, C = len(grid), len(grid[0])
    dist = {src: 0}
    prev = {}
    pq = [(0, src)]
    while pq:
        d, cur = heapq.heappop(pq)
        if d > dist.get(cur, 1 << 60):
            continue
        for name, (dr, dc) in MOVES.items():
            n = (cur[0] + dr, cur[1] + dc)
            if not (0 <= n[0] < R and 0 <= n[1] < C):
                continue
            if grid[n[0]][n[1]] == "wall" or n in blocked:
                continue
            step = 1
            if grid[n[0]][n[1]] == SPIKE and n not in triggered:
                step += PENALTY
            nd = d + step
            if nd < dist.get(n, 1 << 60):
                dist[n] = nd
                prev[n] = (cur, name)
                heapq.heappush(pq, (nd, n))
    return dist, prev


def walk(prev, src, dst):
    out, cur = [], dst
    while cur != src:
        cur, name = prev[cur]
        out.append(name)
    return out[::-1]


def _sweep(grid, pos, targets, blocked, triggered, route, collected, deadline):
    """Visit every reachable target, nearest-first, collecting anything passed over."""
    remaining = set(targets)
    while remaining and time.monotonic() < deadline:
        dist, prev = dijkstra(grid, pos, blocked, triggered)
        avail = [t for t in remaining if t in dist]
        if not avail:
            break
        nxt = min(avail, key=lambda t: dist[t])
        leg = walk(prev, pos, nxt)
        route += leg
        p = pos
        for m in leg:
            dr, dc = MOVES[m]
            p = (p[0] + dr, p[1] + dc)
            collected.add(p)
            remaining.discard(p)
            if grid[p[0]][p[1]] == SPIKE:
                triggered.add(p)
        pos = nxt
    return pos, remaining


def _improve(grid, order, start, end, blocked, triggered, deadline):
    """2-opt the visit ORDER on a precomputed cost matrix - no search in the loop."""
    if len(order) < 4:
        return order
    nodes = [start] + list(order) + [end]
    tables = {n: dijkstra(grid, n, blocked, triggered)[0] for n in nodes}
    INF = 1 << 40

    def cost(seq):
        s = [start] + list(seq) + [end]
        return sum(tables[s[i]].get(s[i + 1], INF) for i in range(len(s) - 1))

    best, bc = list(order), cost(order)
    improved = True
    while improved and time.monotonic() < deadline:
        improved = False
        for i in range(len(best) - 1):
            if time.monotonic() >= deadline:
                break
            for j in range(i + 1, len(best)):
                cand = best[:i] + best[i:j + 1][::-1] + best[j + 1:]
                c = cost(cand)
                if c < bc:
                    best, bc, improved = cand, c, True
    return best


def _rebuild(grid, seq, start, end, blocked, triggered):
    """Walk a fixed order, returning moves and everything stepped on."""
    pos, route, collected, trig = start, [], {start}, set(triggered)
    for tgt in list(seq) + [end]:
        dist, prev = dijkstra(grid, pos, blocked, trig)
        if tgt not in dist:
            return None, None, None
        leg = walk(prev, pos, tgt)
        route += leg
        p = pos
        for m in leg:
            dr, dc = MOVES[m]
            p = (p[0] + dr, p[1] + dc)
            collected.add(p)
            if grid[p[0]][p[1]] == SPIKE:
                trig.add(p)
        pos = tgt
    return route, collected, trig


def solve(grid, budget=8.0, verbose=False):
    """Return {'route', 'coins', 'lives', 'spikes', 'total'} or None."""
    if not valid_map(grid):
        return None
    deadline = time.monotonic() + budget
    start = find(grid, "player")[0]
    treasure = find(grid, "treasure")[0]
    doors = {p for d in DOOR_KEY for p in find(grid, d)}
    keys = [p for k in DOOR_KEY.values() for p in find(grid, k)]
    rewards = {p for code in VALUE for p in find(grid, code)}

    route, collected, triggered = [], {start}, set()
    pos = start

    # --- PHASE 1: every KEY first. Doors and treasure are off limits. ---
    pos, _ = _sweep(grid, pos, keys, doors | {treasure}, triggered,
                    route, collected, deadline)

    # --- PHASE 2: everything else. Doors whose key we now hold are open. ---
    held = {grid[p[0]][p[1]] for p in collected}
    locked = {p for p in doors if DOOR_KEY[grid[p[0]][p[1]]] not in held}
    todo = [p for p in rewards if p not in collected]
    pos, left = _sweep(grid, pos, todo, locked | {treasure}, triggered,
                       route, collected, deadline)

    # --- PHASE 3: treasure LAST. ---
    dist, prev = dijkstra(grid, pos, set(), triggered)
    if treasure not in dist:
        return None
    route += walk(prev, pos, treasure)
    p = pos
    for m in walk(prev, pos, treasure):
        dr, dc = MOVES[m]
        p = (p[0] + dr, p[1] + dc)
        collected.add(p)
        if grid[p[0]][p[1]] == SPIKE:
            triggered.add(p)

    # --- IMPROVE the phase-2 order, then rebuild and keep it only if shorter. ---
    order = [p for p in rewards if p in collected and p not in keys]
    better = _improve(grid, order, start, treasure, set(), set(), deadline)
    r2, c2, t2 = _rebuild(grid, list(keys) + list(better), start, treasure,
                          set(), set())
    if r2 is not None and len(r2) < len(route):
        route, collected, triggered = r2, c2, t2

    coins = sum(VALUE[grid[r][c]] for r, c in collected if grid[r][c] in VALUE)
    spikes = {p for p in collected if grid[p[0]][p[1]] == SPIKE}
    lives = 5 - len(spikes)
    tokens = len(route) * 4 + 625
    total = coins + LIFE * lives + (1000 - round(tokens / 19)) + 1000
    if verbose:
        print(f"    {len(route)} moves, coins {coins}, spikes "
              f"{sorted(label(s) for s in spikes) or 'NONE'}, lives {lives} -> {total}")
    return {"route": route, "coins": coins, "lives": lives,
            "spikes": len(spikes), "total": total, "collected": collected}


def verify(grid, route):
    """Independent check: no walls, treasure last, every key before its door."""
    start = find(grid, "player")[0]
    treasure = find(grid, "treasure")[0]
    pos, seen, order = start, {start}, [start]
    for m in route:
        if m not in MOVES:
            return False, f"bad move {m!r}"
        dr, dc = MOVES[m]
        pos = (pos[0] + dr, pos[1] + dc)
        if not (0 <= pos[0] < len(grid) and 0 <= pos[1] < len(grid[0])):
            return False, "left the grid"
        if grid[pos[0]][pos[1]] == "wall":
            return False, f"wall at {label(pos)}"
        if pos == treasure and m is not route[-1]:
            pass
        if pos not in seen:
            order.append(pos)
        seen.add(pos)
    if pos != treasure:
        return False, "does not end on the treasure"
    if any(p == treasure for p in order[:-1]):
        return False, "touches the treasure early"
    held = set()
    for p in order:
        code = grid[p[0]][p[1]]
        held.add(code)
        if code in DOOR_KEY and DOOR_KEY[code] not in held:
            return False, f"door {label(p)} before its key"
    missed = [label(p) for p in
              {q for code in VALUE for q in find(grid, code)} if p not in seen] \
        if False else [label(p) for code in VALUE for p in find(grid, code)
                       if p not in seen]
    return True, f"ok, {len(route)} moves, missed {missed or 'nothing'}"
