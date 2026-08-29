"""Round 4 route that never steps on the red door.

Eleven attempts have failed and a wrong answer at the red door is ALWAYS fatal:
the best possible arrival has 5 lives, and -5 leaves 0, which is a loss. So the
door can only be solved or avoided, never survived.

This builds the best route that treats D6 (red door) as a wall, visits every cell
still reachable, and finishes on the treasure at J1.

Greedy nearest-unvisited with en-route marking, many random restarts. The earlier
version tried to permute an ordering and timed out; this marks every cell the walk
passes through as visited, which is what the game actually does.
"""

from collections import deque
import random

GRID = [
    ["player", "path", "c7", "c7", "c7", "c5", "c7", "c7", "c1", "treasure"],
    ["path", "wall", "wall", "wall", "wall", "wall", "wall", "wall", "wall", "wall"],
    ["c2", "path", "c7", "c5", "c7", "path", "c7", "c4", "path", "c7"],
    ["wall", "wall", "wall", "wall", "wall", "wall", "wall", "wall", "wall", "c7"],
    ["c7", "c7", "c7", "c7", "wall", "c41", "wall", "path", "c7", "c7"],
    ["c8", "wall", "wall", "c30", "wall", "c7", "wall", "c5", "wall", "c1"],
    ["c1", "c2", "wall", "c7", "wall", "c8", "wall", "path", "wall", "path"],
    ["c7", "c7", "wall", "c1", "wall", "c4", "wall", "c7", "wall", "c5"],
    ["c7", "c7", "wall", "c31", "wall", "path", "wall", "c7", "wall", "c7"],
    ["c18", "c7", "wall", "path", "c7", "c3", "path", "c7", "wall", "c40"],
]

N = 10
START = (0, 0)
TREASURE = (0, 9)
RED_DOOR = (5, 3)
GREEN_DOOR = (8, 3)
GREEN_KEY = (4, 5)

# Tile meanings CONFIRMED from the run traces, not guessed:
#   C3 "some Coins" -> c7        A3 "Code Challenge" -> c2     D3/H6/J8 "Simple Q" -> c5
#   J6/D8 "Guardrail"  -> c1     H3/F8 "Web Search"  -> c4     F10 "Memory Trial"  -> c3
#   J10 "Red Key" -> c40         F5 "Green Key" -> c41         D9 "Green Door" -> c31
VALUE = {"c7": 250, "c1": 100, "c2": 600, "c5": 250, "c4": 800, "c3": 550,
         "c40": 50, "c41": 50, "c31": 1000, "c30": 1000, "c8": 0,
         "c18": 250, "path": 0, "player": 0, "treasure": 0}

# We still answer the Memento tile wrong, so c3 scores 0 and costs a life.
UNSOLVED = {"c3"}

MOVES = [("down", (1, 0)), ("up", (-1, 0)), ("right", (0, 1)), ("left", (0, -1))]


def label(p):
    return f"{chr(ord('A') + p[1])}{p[0] + 1}"


def open_cell(p, blocked):
    return GRID[p[0]][p[1]] != "wall" and p not in blocked


def bfs(src, blocked):
    dist = {src: 0}
    prev = {}
    dq = deque([src])
    while dq:
        u = dq.popleft()
        for _, (dr, dc) in MOVES:
            v = (u[0] + dr, u[1] + dc)
            if 0 <= v[0] < N and 0 <= v[1] < N and v not in dist and open_cell(v, blocked):
                dist[v] = dist[u] + 1
                prev[v] = u
                dq.append(v)
    return dist, prev


def trace(prev, src, dst):
    out = [dst]
    while out[-1] != src:
        out.append(prev[out[-1]])
    return out[::-1]


def sweep(targets, blocked, seed):
    """Walk to the nearest unvisited target, marking everything passed through."""
    rng = random.Random(seed)
    cur = START
    cells = [START]
    unvisited = set(targets) - {START}
    while unvisited:
        dist, prev = bfs(cur, blocked)
        cand = [t for t in unvisited if t in dist]
        if not cand:
            return None
        best = min(dist[t] for t in cand)
        slack = rng.choice([0, 0, 0, 0, 1, 2])
        pool = [t for t in cand if dist[t] <= best + slack]
        pick = rng.choice(pool)
        seg = trace(prev, cur, pick)
        for c in seg[1:]:
            cells.append(c)
            unvisited.discard(c)
        cur = pick
    return cells


def to_moves(cells):
    out = []
    for a, b in zip(cells, cells[1:]):
        d = (b[0] - a[0], b[1] - a[1])
        for name, delta in MOVES:
            if delta == d:
                out.append(name)
                break
        else:
            raise ValueError("non-adjacent step")
    return out


def main():
    # Treasure blocked during the sweep: stepping on it ENDS the game, so it can
    # only ever be the final tile.
    blocked = {RED_DOOR, TREASURE}

    reach, _ = bfs(START, blocked)
    all_open = [(r, c) for r in range(N) for c in range(N) if GRID[r][c] != "wall"]
    gated = [p for p in all_open
             if p not in reach and p not in (RED_DOOR, TREASURE)]

    print(f"open cells                   : {len(all_open)}")
    print(f"reachable without the red door: {len(reach)}")
    print(f"gated behind the red door    : {len(gated)}")
    if gated:
        print("  " + ", ".join(f"{label(p)}({GRID[p[0]][p[1]]})" for p in gated))
    print(f"value given up               : {sum(VALUE.get(GRID[p[0]][p[1]], 0) for p in gated)}")
    print()

    targets = sorted(reach)
    best = None
    for seed in range(400):
        cells = sweep(targets, blocked, seed)
        if cells is None:
            continue
        d, prev = bfs(cells[-1], {RED_DOOR})
        if TREASURE not in d:
            continue
        full = cells + trace(prev, cells[-1], TREASURE)[1:]
        if best is None or len(full) < len(best):
            best = full

    moves = to_moves(best)
    visited = set(best)
    spikes = {p for p in visited if GRID[p[0]][p[1]] == "c8"}
    gi, gd = best.index(GREEN_KEY), best.index(GREEN_DOOR)

    print(f"moves                        : {len(moves)}")
    print(f"ends at                      : {label(best[-1])} ({GRID[best[-1][0]][best[-1][1]]})")
    print(f"walls hit                    : {sum(1 for p in best if GRID[p[0]][p[1]] == 'wall')}")
    print(f"steps on the RED DOOR        : {RED_DOOR in visited}")
    print(f"visits every reachable cell  : {visited >= set(reach)}")
    print(f"touches treasure early       : {TREASURE in best[:-1]}")
    print(f"distinct spike tiles         : {len(spikes)} -> {sorted(label(p) for p in spikes)}")
    print(f"green key before green door  : {gi < gd}")
    print()

    earned = 0
    for p in visited:
        code = GRID[p[0]][p[1]]
        if code not in UNSOLVED:
            earned += VALUE.get(code, 0)
    memento_hits = sum(1 for p in visited if GRID[p[0]][p[1]] in UNSOLVED)
    lives = 5 - len(spikes) - memento_hits

    print("=== PROJECTED SCORE ===")
    print(f"tile value collected         : {earned}")
    print(f"lives left  (5 - {len(spikes)} spike - {memento_hits} memento) : {lives}")
    print(f"life bonus  ({lives} x 250)          : {lives * 250}")
    print("treasure bonus               : 1000")
    print("token bonus (observed)       : ~940")
    print(f"TOTAL                        : ~{earned + lives * 250 + 1000 + 940}")
    print()
    print("versus dying at the red door : 8,693")
    print()
    print("ROUTE:")
    print('["' + '","'.join(moves) + '"]')


if __name__ == "__main__":
    main()
