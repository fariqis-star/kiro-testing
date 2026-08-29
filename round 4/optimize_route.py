"""Is the 105-move route optimal? Token bonus = 1000 - round(tokens/challenges),
so every emitted move costs real points - the array is billed as our output AND
again as the tool result. Cutting moves is the single biggest safe saving.

Solves it as a TSP-path: start A1, end on the treasure, visit every reward tile.
BFS for exact pairwise distances, then nearest-neighbour + 2-opt + Or-opt.
Spikes stay passable (both are forced) but are never a target.

Local tooling. NOT deployed.
"""
import importlib.util
import json
import re
from collections import deque

spec = importlib.util.spec_from_file_location("ce", "codeexecution-lambda.py")
ce = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ce)
GRID = ce.R4_GRID
R = len(GRID)
C = len(GRID[0])

START = (0, 0)
MOVES = {"down": (1, 0), "up": (-1, 0), "right": (0, 1), "left": (0, -1)}


def passable(r, c):
    return 0 <= r < R and 0 <= c < C and GRID[r][c] != "wall"


def bfs(src):
    """Shortest distance and predecessor from src to every reachable cell."""
    dist = {src: 0}
    prev = {}
    q = deque([src])
    while q:
        cur = q.popleft()
        for name, (dr, dc) in MOVES.items():
            nxt = (cur[0] + dr, cur[1] + dc)
            if passable(*nxt) and nxt not in dist:
                dist[nxt] = dist[cur] + 1
                prev[nxt] = (cur, name)
                q.append(nxt)
    return dist, prev


def path_moves(prev, src, dst):
    out = []
    cur = dst
    while cur != src:
        cur, name = prev[cur]
        out.append(name)
    return out[::-1]


treasure = next((r, c) for r in range(R) for c in range(C)
                if GRID[r][c] == "treasure")

# Every tile that pays out. c8 is a spike - passable, never a target.
targets = [(r, c) for r in range(R) for c in range(C)
           if re.fullmatch(r"c\d+", str(GRID[r][c] or "")) and GRID[r][c] != "c8"]

nodes = [START] + targets + [treasure]
nodes = list(dict.fromkeys(nodes))
BFS = {n: bfs(n) for n in nodes}
D = {a: {b: BFS[a][0].get(b, 10**6) for b in nodes} for a in nodes}

must = [n for n in nodes if n not in (START, treasure)]
print(f"grid {R}x{C}  reward tiles {len(targets)}  treasure {treasure}")
print(f"deployed route: 105 moves\n")


def tour_len(order):
    seq = [START] + order + [treasure]
    return sum(D[seq[i]][seq[i + 1]] for i in range(len(seq) - 1))


# nearest neighbour
unvisited = set(must)
cur = START
order = []
while unvisited:
    nxt = min(unvisited, key=lambda n: D[cur][n])
    order.append(nxt)
    unvisited.discard(nxt)
    cur = nxt
best = order[:]
best_len = tour_len(best)
print(f"nearest neighbour : {best_len}")

# 2-opt + Or-opt until no improvement
improved = True
while improved:
    improved = False
    n = len(best)
    for i in range(n - 1):
        for j in range(i + 1, n):
            cand = best[:i] + best[i:j + 1][::-1] + best[j + 1:]
            cl = tour_len(cand)
            if cl < best_len:
                best, best_len, improved = cand, cl, True
    for seg in (1, 2, 3):
        for i in range(len(best) - seg + 1):
            chunk = best[i:i + seg]
            rest = best[:i] + best[i + seg:]
            for j in range(len(rest) + 1):
                cand = rest[:j] + chunk + rest[j:]
                cl = tour_len(cand)
                if cl < best_len:
                    best, best_len, improved = cand, cl, True
print(f"after 2-opt/Or-opt: {best_len}")

# Expand to an actual move list, collecting anything passed through for free.
seq = [START] + best + [treasure]
moves = []
for a, b in zip(seq, seq[1:]):
    moves += path_moves(BFS[a][1], a, b)

# Replay to confirm correctness.
pos = START
visited = {START}
for m in moves:
    dr, dc = MOVES[m]
    pos = (pos[0] + dr, pos[1] + dc)
    assert passable(*pos), f"walked into a wall at {pos}"
    visited.add(pos)
missed = [t for t in targets if t not in visited]
spikes = [p for p in visited if GRID[p[0]][p[1]] == "c8"]

print(f"\nwalk           : {len(moves)} moves")
print(f"ends on treasure: {pos == treasure}")
print(f"reward tiles hit: {len(targets) - len(missed)}/{len(targets)}  missed={missed}")
print(f"spikes stepped on: {len(spikes)}  -> lives {5 - len(spikes) - 1}")
print(f"\nvs deployed 105 : {len(moves) - 105:+d} moves")

chars_long = len(json.dumps(moves, separators=(",", "")))
short = [m[0] for m in moves]
chars_short = len(json.dumps(short, separators=(",", "")))
print(f"\nemitted chars long form  : {chars_long:4}  ~{round(chars_long/4)} tok")
print(f"emitted chars 1-letter   : {chars_short:4}  ~{round(chars_short/4)} tok"
      f"  (saves ~{round((chars_long-chars_short)/4)} tok/emission)")

if len(moves) < 105:
    print("\nSHORTER ROUTE:")
    print(json.dumps(moves, separators=(",", ":")))
