"""Build a DIAGNOSTIC route that reaches the red door WITHOUT collecting the red key.

Why this is worth a run. Sixty-four answers have been rejected, and every one of them
assumed the same thing: that we hold the key, so the -5 is the WRONG-ANSWER penalty.
But the door deals -5 for a wrong answer AND -5 for arriving without the key, and we
have never checked which branch we are actually in.

The red key sits at J10, which is a dead-end spur off J9 - nothing else needs it - so
we can simply not step on it.

    if the door asks its question anyway  -> the key does NOT gate the question, so a
                                            -5 tells us nothing about our answer and
                                            the key may never have registered
    if the door deals damage with NO question -> the key gates the question. We do
                                            hold it normally, and the answer really is
                                            being read and rejected.

Either way we learn which of the two failure modes we have been fighting, which no
amount of further guessing can establish.
"""

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
RED_KEY, RED_DOOR = (9, 9), (5, 3)

FULL = ["down","down","right","right","right","right","right","right","right","right","right","down","down","down","down","down","down","down","up","up","up","up","up","left","left","down","down","down","down","down","left","left","up","up","up","up","up","down","down","down","down","down","left","left","up","up","up","up","up","left","left","left","down","down","down","down","down","right","up","up","up","left","up","up","right","right","right","down","down","down","down","down","right","right","right","right","up","up","up","up","up","right","right","up","up","left","left","left","left","left","left","left","left","left","up","up","right","right","right","right","right","right","right","right","right"]


def label(p):
    return f"{chr(ord('A') + p[1])}{p[0] + 1}"


def walk(route):
    r = c = 0
    cells = [(0, 0)]
    for mv in route:
        dr, dc = D[mv]
        r, c = r + dr, c + dc
        if not (0 <= r < 10 and 0 <= c < 10) or GRID[r][c] == "wall":
            return None
        cells.append((r, c))
    return cells


def drop_redkey(route):
    """Remove the two moves that dip into J10 and come back."""
    cells = walk(route)
    if RED_KEY not in cells:
        return route
    i = cells.index(RED_KEY)
    # The spur is: arrive at J10 from J9, then return to J9. Drop both moves.
    if cells[i - 1] == cells[i + 1]:
        return route[:i - 1] + route[i + 1:]
    return None


def report(name, route):
    cells = walk(route)
    if cells is None:
        print(f"{name}: INVALID - hits a wall or leaves the grid")
        return
    v = set(cells)
    print(f"{name}")
    print(f"  moves                : {len(route)}")
    print(f"  ends at              : {label(cells[-1])} ({GRID[cells[-1][0]][cells[-1][1]]})")
    print(f"  walls hit            : 0")
    print(f"  collects the RED KEY : {RED_KEY in v}")
    print(f"  reaches the RED DOOR : {RED_DOOR in v}")
    if RED_KEY in v and RED_DOOR in v:
        print(f"  key before door      : {cells.index(RED_KEY) < cells.index(RED_DOOR)}")
    spikes = {p for p in v if GRID[p[0]][p[1]] == "c8"}
    print(f"  distinct spikes      : {len(spikes)}")
    print()


def main():
    report("FULL 105-move route (current)", FULL)
    nk = drop_redkey(FULL)
    if nk is None:
        print("could not excise the red-key spur automatically")
        return
    report("DIAGNOSTIC route, red key skipped", nk)
    cells = walk(nk)
    assert RED_KEY not in set(cells), "red key still collected"
    assert RED_DOOR in set(cells), "red door not reached"
    print("Deploy this as PATH_DIAGNOSTIC and watch ONLY one thing:")
    print("  does the red door still print 'What is red key 1?' ?")
    print()
    print('["' + '","'.join(nk) + '"]')


if __name__ == "__main__":
    main()
