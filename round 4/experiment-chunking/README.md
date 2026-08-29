# Experiment: can we raise `challenges_attempted`?

## RESULT: NO. DISPROVEN. DO NOT DEPLOY THESE FILES.

Kept only as the record of the test. The live build is `round 4/pathfinding-lambda.py`
with `ROUTE_SPLIT = 0`.

## What was tested

`ROUTE_SPLIT = 2` split the proven 105-move route into:

- part 1 = **104 moves**, ending on **I1** — a guardrail tile, so the game had every
  reason to come back to the agent
- part 2 = **1 move**, `["right"]`, stepping onto the treasure

## What happened

Part 1 executed perfectly. All 18 challenges answered correctly, all 14,350 coins
collected, the I1 guardrail scored +100. Then:

- the pathfinding tool was **never called a second time**
- the game **never asked for more moves**
- the treasure was never reached
- **no score summary was printed at all**
- the player was **removed from the dungeon**

## What it means

An incomplete route is not "pause and ask again" — it is a **forfeited run**. That is
worse than the −1,000 treasure bonus predicted as the downside; there is no score at
all.

Two different split shapes have now failed the same way: one splitting mid-corridor, one
landing squarely on a challenge tile. The mechanism does not exist.

## The denominator is closed generally, not just via splitting

A "challenge attempted" is one agent turn answering one game prompt:

```
1 route turn + 18 challenge tiles = 19
```

- The game prompts only at the start and on a challenge tile.
- It never asks for moves — now proven twice.
- Re-entering a tile does not re-trigger it. Our route re-crosses F7, F10 and D9 and
  each gives a bare `You moved to X`.

Reaching 38 turns would need **37 challenge encounters on a board that has 18.**

## So how did the rival score 17,056?

Solving 17,056 against the formula with 1,654 tokens, across every combination of coins,
lives and treasure, yields **only** solutions at 38 attempted challenges. None exists at
19 or 20.

They are playing a board with roughly 37 challenge tiles. **Their score is not a target
on this map**, and the comparison was never like-for-like.
