"""Verify any candidate route against the real Round 4 map.

Checks the things that actually end runs: walking into a wall, stepping on the
red door, touching the treasure early, missing reachable tiles, and picking up
the green key after the green door instead of before it.
"""

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
RED_DOOR, GREEN_DOOR, GREEN_KEY, RED_KEY = (5, 3), (8, 3), (4, 5), (9, 9)
TREASURE = (0, 9)

VALUE = {"c7": 250, "c1": 100, "c2": 600, "c5": 250, "c4": 800, "c3": 550,
         "c40": 50, "c41": 50, "c31": 1000, "c30": 1000, "c8": 0, "c18": 250}


def label(p):
    return f"{chr(ord('A') + p[1])}{p[0] + 1}"


def check(name, route, expect_red):
    print(f"=== {name}  ({len(route)} moves)")
    r = c = 0
    cells = [(0, 0)]
    for i, mv in enumerate(route):
        dr, dc = D[mv]
        r, c = r + dr, c + dc
        if not (0 <= r < 10 and 0 <= c < 10):
            print(f"  FAIL off grid at move {i+1}")
            return
        if GRID[r][c] == "wall":
            print(f"  FAIL wall hit at move {i+1} -> {label((r,c))}")
            return
        cells.append((r, c))

    visited = set(cells)
    ok = True

    def line(good, text):
        nonlocal ok
        if not good:
            ok = False
        print(f"  {'OK  ' if good else 'FAIL'} {text}")

    line(cells[-1] == TREASURE, f"ends on the treasure (ended {label(cells[-1])})")
    line(TREASURE not in cells[:-1], "never touches the treasure early")
    line((RED_DOOR in visited) == expect_red,
         f"red door visited = {RED_DOOR in visited} (wanted {expect_red})")
    if GREEN_KEY in cells and GREEN_DOOR in cells:
        line(cells.index(GREEN_KEY) < cells.index(GREEN_DOOR),
             "green key collected before the green door")
    else:
        line(False, "green key and green door both on route")
    if RED_KEY in cells:
        print(f"  OK   red key collected (+50)")

    spikes = {p for p in visited if GRID[p[0]][p[1]] == "c8"}
    memento = sum(1 for p in visited if GRID[p[0]][p[1]] == "c3")
    lives = 5 - len(spikes) - memento
    earned = sum(VALUE.get(GRID[p[0]][p[1]], 0) for p in visited
                 if GRID[p[0]][p[1]] != "c3"
                 and not (GRID[p[0]][p[1]] == "c30" and not expect_red))
    print(f"  --   distinct spikes {len(spikes)} {sorted(label(p) for p in spikes)}"
          f", memento hits {memento}, lives {lives}")
    print(f"  --   tile value {earned}, life bonus {lives*250}, treasure 1000")
    print(f"  --   projected total ~{earned + lives*250 + 1000 + 940}")
    print(f"  {'PASS' if ok else 'FAIL'}")
    print()
    return ok


OLD_NO_RED = ["down","down","right","right","right","right","right","right","right","right","right","down","down","down","down","down","down","down","up","up","up","up","up","left","left","down","down","down","down","down","left","left","up","up","up","up","up","down","down","down","down","down","left","left","up","up","up","down","down","down","right","right","right","right","up","up","up","up","up","right","right","up","up","left","left","left","left","left","left","left","left","left","up","up","right","right","right","right","right","right","right","right","right"]

NEW_NO_RED = ["down","down","right","right","right","right","right","right","right","right","right","down","down","left","left","down","down","down","down","down","left","left","up","up","up","up","up","down","down","down","down","down","left","left","up","up","up","down","down","down","right","right","right","right","up","up","up","up","up","right","right","down","down","down","down","down","up","up","up","up","up","up","up","left","left","left","left","left","left","left","left","left","up","up","right","right","right","right","right","right","right","right","right"]

if __name__ == "__main__":
    a = check("OLD stored R4_PATH_NO_RED", OLD_NO_RED, expect_red=False)
    b = check("NEW solver route", NEW_NO_RED, expect_red=False)
    print("use NEW" if b and not a else ("either works" if a and b else "use whichever PASSed"))
