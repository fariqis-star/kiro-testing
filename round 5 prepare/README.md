# Round 5 Prepare

Staging area for AWS AI League Round 5 (PolyCC Malaysia). Nothing here is deployed.

## Rules of engagement

**`round-4-frozen/` IS FROZEN.** Do not edit, refactor, reformat or "tidy" anything in
it without being told to. It is the exact build that scored **17,044 on the test map
and 17,045 on the judge**, copied byte for byte on 2026-07-24 at commit `e2d5caf`.
Verified identical by md5 for all five deployables, and its `audit.py` passes standing
alone inside the folder.

If Round 5 work needs to change a file, **copy it out** into a new working folder. The
frozen copy stays untouched so there is always a known-good build to fall back to and
to diff against.

## What is here

| file | what it is for |
|---|---|
| `round-4-frozen/` | the 17,044 build, complete and frozen |
| `KNOWLEDGE-BASE.md` | proven mechanics, flag values, test vectors, and every approach already ruled out |
| `RUN-HISTORY.md` | every scored run, what broke, and what fixed it |
| `ROUND-5-GAPS.md` | measured failures on a changed board, and what is needed from the organisers |

## Read this first, in this order

1. `KNOWLEDGE-BASE.md` — the scoring formula and the ceiling. Everything else follows
   from those two facts.
2. `ROUND-5-GAPS.md` — what actually breaks when the board changes. Four measured
   failures, not guesses.
3. `RUN-HISTORY.md` — only if a fix looks arbitrary. It probably is not; most oddities
   in the code are load-bearing and cost a run to learn.

## The one-line summary

Round 4 is **optimised, not generalised**: the 17,044 comes from a hardcoded 105-move
route on a board proven identical between test and judge. A genuinely adaptive solver
exists underneath and is tested, but it only activates when the board is passed to the
tool, which the Round 4 prompt deliberately forbids to save output tokens.

Round 5 almost certainly inverts that trade. See `ROUND-5-GAPS.md`.
