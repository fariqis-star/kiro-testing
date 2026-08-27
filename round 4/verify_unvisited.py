"""Which round-4 tiles does the verified route never step on?

The trace confirms the code of every tile the route VISITS. Tiles it never
touches would be transcription-only - codes never confirmed by the game - and a
single mislabelled tile there would change the Memento count.

RESULT: there are none. The route covers all 61 non-wall cells, so every tile
code is trace-confirmed and c4 = 2 is proven, not assumed.
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

ROUTE = ["down","down","right","right","right","right","right","right","right","right","right","down","down","down","down","down","down","down","up","up","up","up","up","left","left","down","down","down","down","down","left","left","up","up","up","up","up","down","down","down","down","down","left","left","up","up","up","up","up","left","left","left","down","down","down","down","down","right","up","up","up","left","up","up","right","right","right","down","down","down","down","down","right","right","right","right","up","up","up","up","up","right","right","up","up","left","left","left","left","left","left","left","left","left","up","up","right","right","right","right","right","right","right","right","right"]

# Game labels columns A-J and rows 1-10. GRID rows are game rows, GRID cols are
# game columns, so "down" walks along the row axis of the game = GRID column
# index, and the game's letter is the GRID column. Derived from the trace:
# start A1 -> down -> A2 -> down -> A3 (Code Challenge, GRID[2][0] == 'c2').
DELTA = {"down": (1, 0), "up": (-1, 0), "right": (0, 1), "left": (0, -1)}


def label(r, c):
    return f"{chr(ord('A') + c)}{r + 1}"


def main():
    r = c = 0
    visited = {(0, 0)}
    for mv in ROUTE:
        dr, dc = DELTA[mv]
        r, c = r + dr, c + dc
        if not (0 <= r < 10 and 0 <= c < 10):
            print(f"OFF GRID at {mv} -> {r},{c}")
            return
        if GRID[r][c] == "wall":
            print(f"WALL HIT at {label(r, c)}")
            return
        visited.add((r, c))

    print(f"end position    : {label(r, c)}  ({GRID[r][c]})")
    print(f"moves           : {len(ROUTE)}")

    nonwall = [(rr, cc) for rr in range(10) for cc in range(10)
               if GRID[rr][cc] != "wall"]
    unvisited = [p for p in nonwall if p not in visited]

    print(f"non-wall cells  : {len(nonwall)}")
    print(f"visited         : {len(visited)}")
    print(f"NEVER VISITED   : {len(unvisited)}")
    print()
    print("Codes the game never confirmed for us:")
    for rr, cc in unvisited:
        print(f"  {label(rr, cc):<4} transcribed as {GRID[rr][cc]}")

    print()
    c4_all = [label(rr, cc) for rr in range(10) for cc in range(10)
              if GRID[rr][cc] == "c4"]
    c4_unvis = [label(rr, cc) for rr, cc in unvisited if GRID[rr][cc] == "c4"]
    print(f"c4 in transcription : {len(c4_all)} -> {c4_all}")
    print(f"  of those unvisited: {c4_unvis}")
    print()
    if not unvisited:
        print("Every non-wall cell is visited, so every code is trace-confirmed.")
        print("c4 = 2 is PROVEN. Since 2, 1, 'two', a sentence and a labelled")
        print("count were all rejected, the Memento trial is not losing on the")
        print("number and not losing on the phrasing. Nothing left to tune from")
        print("here, and it is only -1, so it stops being worth runs.")


if __name__ == "__main__":
    main()
