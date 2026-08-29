"""Price every spike-avoidance strategy by actually BUILDING the route.

The claim "spikes are forced" was argued from connectivity alone. This solves each
scenario end to end - optimal route, coins collected, lives, treasure, token bonus -
so the comparison is a number rather than an assertion.

Critically it also models the DOOR DEPENDENCIES, which pure connectivity misses:
a door you reach without its key "does a lot of damage" (-5 = death), and the green
door D9 turns out to be the only way through to the red door and the whole west side.

Local tooling. NOT deployed.
"""
import importlib.util
import itertools
import json
import re
from collections import deque

spec = importlib.util.spec_from_file_location("ce", "codeexecution-lambda.py")
ce = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ce)
G = ce.R4_GRID
R, C = len(G), len(G[0])
MOVES = {"down": (1, 0), "up": (-1, 0), "right": (0, 1), "left": (0, -1)}

# Points per tile code, from the traces.
VALUE = {"c7": 250, "c5": 250, "c1": 100, "c2": 600, "c4": 800, "c3": 550,
         "c18": 500, "c30": 1000, "c31": 1000, "c40": 50, "c41": 50}
SPIKE = "c8"
START = (0, 0)
TREASURE = next((r, c) for r in range(R) for c in range(C) if G[r][c] == "treasure")


def lbl(p):
    return f"{chr(ord('A') + p[1])}{p[0] + 1}"


def passable(p, blocked):
    r, c = p
    return 0 <= r < R and 0 <= c < C and G[r][c] != "wall" and p not in blocked


def bfs(src, blocked):
    dist, prev = {src: 0}, {}
    q = deque([src])
    while q:
        cur = q.popleft()
        for name, (dr, dc) in MOVES.items():
            n = (cur[0] + dr, cur[1] + dc)
            if passable(n, blocked) and n not in dist:
                dist[n] = dist[cur] + 1
                prev[n] = (cur, name)
                q.append(n)
    return dist, prev


def moves_between(prev, src, dst):
    out, cur = [], dst
    while cur != src:
        cur, name = prev[cur]
        out.append(name)
    return out[::-1]


def solve(blocked, label):
    """Best route that never enters `blocked`, and the score it produces."""
    targets = [(r, c) for r in range(R) for c in range(C)
               if G[r][c] in VALUE and (r, c) not in blocked]
    nodes = list(dict.fromkeys([START] + targets + [TREASURE]))
    B = {n: bfs(n, blocked) for n in nodes}
    reach = B[START][0]

    targets = [t for t in targets if t in reach]
    if TREASURE not in reach:
        print(f"\n=== {label} ===\n  TREASURE UNREACHABLE - invalid")
        return None

    D = {a: {b: B[a][0].get(b, 10 ** 6) for b in nodes} for a in nodes}

    def tour_len(order):
        seq = [START] + order + [TREASURE]
        return sum(D[seq[i]][seq[i + 1]] for i in range(len(seq) - 1))

    unv, cur, order = set(targets), START, []
    while unv:
        nxt = min(unv, key=lambda n: D[cur][n])
        order.append(nxt)
        unv.discard(nxt)
        cur = nxt
    best, best_len = order[:], tour_len(order)
    improved = True
    while improved:
        improved = False
        for i in range(len(best) - 1):
            for j in range(i + 1, len(best)):
                cand = best[:i] + best[i:j + 1][::-1] + best[j + 1:]
                cl = tour_len(cand)
                if cl < best_len:
                    best, best_len, improved = cand, cl, True
        for seg in (1, 2, 3):
            for i in range(len(best) - seg + 1):
                chunk, rest = best[i:i + seg], best[:i] + best[i + seg:]
                for j in range(len(rest) + 1):
                    cand = rest[:j] + chunk + rest[j:]
                    cl = tour_len(cand)
                    if cl < best_len:
                        best, best_len, improved = cand, cl, True

    seq = [START] + best + [TREASURE]
    route = []
    for a, b in zip(seq, seq[1:]):
        route += moves_between(B[a][1], a, b)

    # Replay: what is actually stepped on, in order.
    pos, visited, order_hit = START, {START}, [START]
    for m in route:
        dr, dc = MOVES[m]
        pos = (pos[0] + dr, pos[1] + dc)
        if pos not in visited:
            order_hit.append(pos)
        visited.add(pos)

    spikes_hit = {p for p in visited if G[p[0]][p[1]] == SPIKE}
    got = [p for p in visited if G[p[0]][p[1]] in VALUE]

    # DOOR DEPENDENCY: a door reached before its key is fatal (-5 lives).
    keys = {"c30": "c40", "c31": "c41"}
    fatal = []
    seen = set()
    for p in order_hit:
        code = G[p[0]][p[1]]
        seen.add(code)
        if code in keys and keys[code] not in seen:
            fatal.append(lbl(p))

    coins = sum(VALUE[G[r][c]] for r, c in got)
    lives = 5 - len(spikes_hit)
    # ~4 tokens per emitted move, plus ~625 for everything else in a run.
    tokens = len(route) * 4 + 625
    bonus = 1000 - round(tokens / 19)
    total = coins + 250 * lives + bonus + 1000

    print(f"\n=== {label} ===")
    print(f"  route            {len(route)} moves")
    print(f"  reward tiles     {len(got)}/{len(VALUE and targets) + 0} reachable, all collected")
    print(f"  spikes stepped   {len(spikes_hit)} {sorted(lbl(p) for p in spikes_hit)}")
    print(f"  lives            {lives}  -> life bonus {250 * lives}")
    print(f"  coins            {coins}")
    if fatal:
        print(f"  *** DOOR WITHOUT ITS KEY at {fatal} -> -5 lives = DEAD RUN ***")
    print(f"  ~tokens {tokens} -> bonus {bonus}")
    print(f"  TOTAL            {total}" + ("   (INVALID - dead run)" if fatal else ""))
    return None if fatal else total


spikes = [(r, c) for r in range(R) for c in range(C) if G[r][c] == SPIKE]
print(f"spikes on the map: {[lbl(p) for p in spikes]}")

results = {}
results["take both (current)"] = solve(set(), "TAKE BOTH SPIKES  (current, 3 lives)")
for sp in spikes:
    results[f"avoid {lbl(sp)}"] = solve({sp}, f"AVOID {lbl(sp)} ONLY  (4 lives)")
results["avoid both"] = solve(set(spikes), "AVOID BOTH SPIKES  (5 lives)")

print("\n" + "=" * 62)
print("VERDICT")
print("=" * 62)
base = results["take both (current)"]
for k, v in results.items():
    if v is None:
        print(f"  {k:24} INVALID (dead run)")
    else:
        print(f"  {k:24} {v}   {v - base:+d} vs current")
