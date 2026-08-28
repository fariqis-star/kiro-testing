"""Round 4 route that never steps on the red door.

Ten attempts at the red door have failed, and a wrong answer there is always
fatal: best case lives are 5 - 2 spikes - 1 memory = 2, and the door deals -5.
Even a flawless run arrives with at most 5 and -5 leaves 0, which is a loss. So
the door cannot be survived, only solved or avoided.

This builds the best route that treats D6 (the red door) as a wall, visits every
cell still reachable, and finishes on the treasure at J1.
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
RED_DOOR = (5, 3)          # D6
GREEN_DOOR = (8, 3)        # D9
GREEN_KEY = (4, 5)         # F5

POINTS = {"c7": 250, "c1": 250, "c5": 250, "c2": 250, "c18": 250, "c40": 50,
          "c41": 50, "c4": 800, "c3": 550, "c31": 1000, "c8": 0, "path": 0,
          "player": 0, "treasure": 0, "c30": 1000}

MOVES = {"down": (1, 0), "up": (-1, 0), "right": (0, 1), "left": (0, -1)}


def label(p):
    return f"{chr(ord('A') + p[1])}{p[0] + 1}"


def blocked(p, extra_walls):
    return GRID[p[0]][p[1]] == "wall" or p in extra_walls


def neighbours(p, extra_walls):
    for dr, dc in MOVES.values():
        q = (p[0] + dr, p[1] + dc)
        if 0 <= q[0] < N and 0 <= q[1] < N and not blocked(q, extra_walls):
            yield q


def bfs(src, extra_walls):
    dist = {src: 0}
    prev = {}
    dq = deque([src])
    while dq:
        u = dq.popleft()
        for v in neighbours(u, extra_walls):
            if v not in dist:
                dist[v] = dist[u] + 1
                prev[v] = u
                dq.append(v)
    return dist, prev


def path_between(a, b, extra_walls):
    _, prev = bfs(a, extra_walls)
    if b == a:
        return [a]
    if b not in prev:
        return None
    out = [b]
    while out[-1] != a:
        out.append(prev[out[-1]])
    return out[::-1]


def route_moves(cells):
    out = []
    for a, b in zip(cells, cells[1:]):
        dr, dc = b[0] - a[0], b[1] - a[1]
        for name, d in MOVES.items():
            if d == (dr, dc):
                out.append(name)
                break
        else:
            raise ValueError(f"non-adjacent step {a}->{b}")
    return out


def build(order, extra_walls):
    """Walk an ordering of targets, stitching shortest paths."""
    cells = [START]
    for tgt in order:
        seg = path_between(cells[-1], tgt, extra_walls)
        if seg is None:
            return None
        cells.extend(seg[1:])
    return cells


def greedy(targets, extra_walls, seed):
    rng = random.Random(seed)
    remaining = set(targets)
    cur = START
    order = []
    while remaining:
        dist, _ = bfs(cur, extra_walls)
        cand = [t for t in remaining if t in dist]
        if not cand:
            break
        best = min(dist[t] for t in cand)
        pool = [t for t in cand if dist[t] <= best + rng.choice([0, 0, 0, 1])]
        pick = rng.choice(pool)
        order.append(pick)
        remaining.discard(pick)
        cur = pick
    order.append(TREASURE)
    return order


def polish(order, extra_walls, rounds, seed):
    rng = random.Random(seed)
    best = order[:]
    cells = build(best, extra_walls)
    best_len = len(cells)
    for _ in range(rounds):
        i = rng.randrange(0, len(best) - 1)
        j = rng.randrange(0, len(best) - 1)
        if i == j:
            continue
        trial = best[:]
        if rng.random() < 0.5:
            trial[i], trial[j] = trial[j], trial[i]
        else:
            a, b = min(i, j), max(i, j)
            trial[a:b + 1] = reversed(trial[a:b + 1])
        if trial[-1] != TREASURE:
            continue
        c = build(trial, extra_walls)
        if c is None:
            continue
        if len(c) < best_len:
            best, best_len = trial, len(c)
    return best


def main():
    extra = {RED_DOOR}

    reach, _ = bfs(START, extra)
    reachable = sorted(reach)
    all_open = [(r, c) for r in range(N) for c in range(N)
                if GRID[r][c] != "wall"]
    gated = [p for p in all_open if p not in reach and p != RED_DOOR]

    print(f"open cells                 : {len(all_open)}")
    print(f"reachable without D6       : {len(reachable)}")
    print(f"gated behind the red door  : {len(gated)}")
    print("  " + ", ".join(f"{label(p)}({GRID[p[0]][p[1]]})" for p in gated))
    lost = sum(POINTS.get(GRID[p[0]][p[1]], 0) for p in gated)
    print(f"coin/challenge value given up: {lost}")
    print()

    targets = [p for p in reachable if p != START and p != TREASURE]
    best, best_cells = None, None
    for seed in range(60):
        order = greedy(targets, extra, seed)
        order = polish(order, extra, 4000, seed)
        cells = build(order, extra)
        if cells is None:
            continue
        if best_cells is None or len(cells) < len(best_cells):
            best, best_cells = order, cells

    moves = route_moves(best_cells)
    visited = set(best_cells)

    print(f"moves                      : {len(moves)}")
    print(f"ends at                    : {label(best_cells[-1])}")
    print(f"visits all reachable       : {visited >= set(reachable)}")
    print(f"steps on the red door      : {RED_DOOR in visited}")
    print(f"walls hit                  : {sum(1 for p in best_cells if GRID[p[0]][p[1]] == 'wall')}")

    spikes = {p for p in visited if GRID[p[0]][p[1]] == "c8"}
    print(f"distinct spike tiles       : {len(spikes)} -> {[label(p) for p in spikes]}")

    gi = best_cells.index(GREEN_KEY) if GREEN_KEY in best_cells else -1
    gd = best_cells.index(GREEN_DOOR) if GREEN_DOOR in best_cells else -1
    print(f"green key before green door: {gi != -1 and gd != -1 and gi < gd}")
    print()
    print("ROUTE:")
    print('["' + '","'.join(moves) + '"]')


if __name__ == "__main__":
    main()
