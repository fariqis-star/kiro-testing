"""Full audit of the Round 4 setup. Verifies every handler and the route.

Run this before any deploy. It checks the things that have actually cost points in
this competition, not just that the code imports.
"""

import importlib.util
import json
import sys

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
D = {"down": (1, 0), "up": (-1, 0), "right": (0, 1), "left": (0, -1)}
RED_DOOR, GREEN_DOOR, GREEN_KEY, TREASURE = (5, 3), (8, 3), (4, 5), (0, 9)

FAILS = []


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def check(label, good, detail=""):
    print(f"  {'OK  ' if good else 'FAIL'}  {label}{('  -> ' + detail) if detail else ''}")
    if not good:
        FAILS.append(label)


def main():
    ce = load("codeexecution-lambda.py", "ce")
    pf = load("pathfinding-lambda.py", "pf")

    def run(code):
        r = ce.lambda_handler({"body": json.dumps({"code": code})}, None)
        b = r.get("body")
        try:
            b = json.loads(b)
        except Exception:
            pass
        return b.get("output", "").strip()

    print("=== FLAGS ===")
    print(f"  SKIP_RED_DOOR  codeexec={ce.SKIP_RED_DOOR}  pathfinding={pf.SKIP_RED_DOOR}")
    print(f"  RED_AUTO={ce.RED_AUTO}  RED_MODE={ce.RED_MODE}")
    print(f"  MEMORY_FORMAT={ce.MEMORY_FORMAT}  SWAP_C3_RED={ce.SWAP_C3_RED}")
    print()

    print("=== FLAGS AGREE ACROSS BOTH LAMBDAS ===")
    check("SKIP_RED_DOOR matches", ce.SKIP_RED_DOOR == pf.SKIP_RED_DOOR,
          f"{ce.SKIP_RED_DOOR} vs {pf.SKIP_RED_DOOR}")
    print()

    print("=== SCORING HANDLERS ===")
    g = run("green fghi")
    check("green door returns 6789 (proven +1000)", g == "6789", repr(g))
    check("maths 100! mod 1e9+7", run("100! mod 1e9+7") == "437918130")
    check("maths fib 3000 last 10", run("fib 3000 last 10") == "6709796000")
    m = run("How many c4 challenges are on the map?")
    if getattr(ce, "MEMORY_AUTO", False):
        print(f"  --    memento is in DIAGNOSTIC mode, answering {m!r} "
              f"(all tile counts already rejected)")
    else:
        check("memory returns a bare number", m.isdigit(), repr(m))
    r = run("red open")
    print(f"  --    red door currently answers {r!r}")
    print()

    print("=== ROUTE ===")
    body = json.loads(pf.lambda_handler({}, None)["body"])
    route = body["path"]
    fb = json.loads(run("find optimal path"))
    check("both Lambdas return the same route", route == fb["path"],
          f"{len(route)} vs {len(fb['path'])} moves")
    check("counts strings identical", body["counts"] == fb["counts"])

    r_, c_ = 0, 0
    cells = [(0, 0)]
    walls = 0
    for mv in route:
        dr, dc = D[mv]
        r_, c_ = r_ + dr, c_ + dc
        if not (0 <= r_ < 10 and 0 <= c_ < 10):
            check("stays on the grid", False, f"off grid at {mv}")
            break
        if GRID[r_][c_] == "wall":
            walls += 1
        cells.append((r_, c_))
    visited = set(cells)

    check("no walls hit", walls == 0, f"{walls} walls")
    check("ends on the treasure", cells[-1] == TREASURE)
    check("treasure not touched early", TREASURE not in cells[:-1])
    check("green key before green door",
          GREEN_KEY in cells and GREEN_DOOR in cells
          and cells.index(GREEN_KEY) < cells.index(GREEN_DOOR))

    diag = getattr(ce, "DIAGNOSTIC_NO_REDKEY", False)
    check("DIAGNOSTIC_NO_REDKEY matches across both Lambdas",
          diag == getattr(pf, "DIAGNOSTIC_NO_REDKEY", False))

    on_red = RED_DOOR in visited
    if diag:
        RED_KEY = (9, 9)
        check("DIAGNOSTIC: red key NOT collected", RED_KEY not in visited)
        check("DIAGNOSTIC: red door still reached", on_red)
        print("  --   diagnostic run: watch whether the door still asks its question")
    else:
        check(f"red door visited matches SKIP flag (skip={ce.SKIP_RED_DOOR})",
              on_red == (not ce.SKIP_RED_DOOR), f"visited={on_red}")

    spikes = {p for p in visited if GRID[p[0]][p[1]] == "c8"}
    memento = sum(1 for p in visited if GRID[p[0]][p[1]] == "c3")
    lives = 5 - len(spikes) - memento
    print(f"  --    {len(route)} moves, {len(spikes)} spike(s), {memento} memento, "
          f"{lives} lives left")
    if on_red:
        print(f"  --    WARNING: a wrong red door answer is -5, and {lives} - 5 <= 0")
    print()

    print("=== PROMPT CONSISTENCY ===")
    p = open("supervisor-prompt.txt").read()
    flat = " ".join(p.split())
    want = "103" if diag else ("83" if ce.SKIP_RED_DOOR else "105")
    check(f"prompt accepts the deployed route length ({want})", want in flat)
    check("key pickup does not ask the model to transform",
          "SPELLED BACKWARDS" not in flat,
          "model echoed 'open' when asked to reverse - never ask it to transform")
    check("prompt tells the model to output the memento reply verbatim",
          "IT MAY NOT BE A NUMBER" in flat or "bare number" in flat)
    check("guardrail checked before patient JSON", "BEFORE CASE 7" in flat)
    check("never invent a path", "NEVER INVENT A PATH" in flat)
    print()

    print("=" * 60)
    if FAILS:
        print(f"{len(FAILS)} PROBLEM(S):")
        for f in FAILS:
            print(f"  - {f}")
        sys.exit(1)
    print("ALL CHECKS PASSED")


if __name__ == "__main__":
    main()
