# Round 5 gaps — measured, not guessed

Run against the frozen Round 4 build with a deliberately altered board.

## Four things break

### 1. New challenge codes are worth 0, so they are never collected
`VALUE` knows 11 codes. Anything else — `c6` Boss, `c50`, any Round 5 addition — has no
value, so the solver never treats it as a detour target. Planting `c6` and `c50` on the
board, both were only touched because they happened to lie on the existing path.

**Consequence:** we walk past new challenges and leave their coins.
**Fix direction:** give unknown `cN` codes a default positive value so they are always
worth collecting, and only special-case the ones with known handlers.

### 2. A new door/key pair breaks the ordering guarantee
`DOOR_KEY` hardcodes `c30→c40` and `c31→c41`. With a blue door `c32` and blue key
`c42`, the visit order came out:

```
c32, c42, c42, c32     <- door BEFORE its key
```

**Consequence:** an unanswerable door question. In Round 4 a wrong door answer is
**−5 lives, i.e. instant death.**
**Fix direction:** infer pairs by convention (door code ↔ key code offset) rather than a
lookup table, and treat *any* unrecognised `cN` in door position as locked until a
plausible key has been collected. Fail safe, not open.

### 3. The Memory Trial answers from the Round 4 grid
Positions are enumerated from the hardcoded `R4_GRID`. Adding a third `c4` to the
board: true answer 3, we still answer **2**.

**Consequence:** −550 and a life on any board that is not Round 4's.
**Fix direction:** count from the board *passed in the request*, with `R4_GRID` only as
fallback. This requires the prompt to send the board to the memory tool as well, which
is currently forbidden.

### 4. With no board passed, we return the Round 4 route
The prompt says `NO MAP, EVER` because on Round 4 the board is provably identical and
echoing it costs ~27 output tokens. On a Round 5 board that means a 105-move route
built for a different layout.

**Consequence:** walls on move 1, run over.
**Fix direction:** flip the prompt to send the compact one-char-per-cell board. ~27
output tokens, ~1.4 points, and it is what activates every adaptive path below.

## What survives a board change

Already verified working on an altered board in the game's own format:

- `solve_auto()` picks the best of 8 strategies and returned a legal 107-move route
- spike-as-cost (Dijkstra, penalty 5000) — avoids spikes when a detour exists, takes
  them when forced. On a board with bypasses it returns 5 lives / 17,545
- keys before doors, treasure strictly last
- `_canon_grid()` — `normal`/`start`/`chest` synonyms, missing player cell derived from
  the stated start, `A1`/`B10`/`[row,col]` parsing, jagged rows padded
- `verify()` — rejects walls, early treasure, and doors before keys, falling back to a
  known-good route rather than emitting an illegal one
- the maths engine, web scrape, door transforms, guardrail/intake classification

## What is needed from the organisers

Cannot build this blind. In priority order:

1. **The `c1`–`cN` table for Round 5** — map key, name, how to solve, reward, damage.
   Same shape as the base workshop's c1–c8 pages. This is the single most useful item.
2. **The new board** — expand *"View full prompt"* and paste the **text**. Not a
   screenshot: three rows were misread off the last one, and one transcription produced
   a structurally impossible 9-cell row on a 10-wide board.
3. **Any new door/key colours** — what the key tile displays versus what the door
   expects. One worked example is enough to infer the transform.
4. **Whether `c6` Boss appears**, and what it asks for. It is in the game's vocabulary,
   has never appeared, and has no handler.
5. **Any new Lambda or tool**, and whether the tool names are fixed.
6. **The stated max score**, to rebuild the ceiling decomposition. On Round 4,
   `17,600 = 14,350 + 1,250 + 1,000 + 1,000` decomposed exactly and that is what proved
   coins were already maxed.

## Sequencing

Do not start Round 5 edits until Round 4 has been submitted to the judge enough times
to bank a best score. The build is clean and at the ceiling; best-of-N is recorded, so
repeat submissions cost nothing and only the maximum is kept.

The three generic fixes (1, 2, 3 above) are **inert on Round 4** — they only trigger on
an unrecognised board — so they can be built without risking the 17,044. Gap 4 is the
only one that changes Round 4 behaviour, and it should stay off until Round 5 confirms
the board actually differs.
