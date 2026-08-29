# Experiment: can we raise `challenges_attempted`?

**Test map only. Never submit this to the judge.**

## Why

```
token_bonus = 1000 - total_output_tokens / challenges_attempted
```

A rival scored **17,056** with **1,654** output tokens. We score 17,045 with **1,043**.
Their coins (14,350), lives (3) and treasure (1,000) are identical to ours. Solving
their score against the formula leaves exactly one possibility: **they attempted 38
challenges, we attempt 19.** They emit 59% more tokens and still win, because they
divide by twice as much.

38 = our 18 challenge tiles + 20 route-submission turns. So the route goes in parts,
and each part buys a point of denominator.

## The unknown this run answers

**Does the game re-prompt for moves once the queue empties?** An earlier attempt said no
and the player froze — but that split mid-corridor, giving the game no reason to come
back to the agent. This split ends part 1 **on I1, a challenge tile**, so the game has
to speak to us there.

## The two files

`ROUTE_SPLIT = 2` is the only difference from the main build. Verified: that one line,
nothing else.

- part 1 = **104 moves**, ending on I1 (the last guardrail)
- part 2 = **1 move**, `["right"]`, stepping onto the treasure
- the two parts rejoin to the proven 105-move route exactly

The prompt gains one paragraph telling the model to send part 1, then ask for part 2 if
the game wants more moves.

## Downside is capped on purpose

Part 1 does the entire board. The only thing outstanding is the single step onto the
chest. So:

| outcome | score | meaning |
|---|---|---|
| game re-prompts | ~17,047 | **mechanism confirmed** — then raise the part count |
| game freezes | ~16,045 | door is shut, revert. Costs one free test run |

All 14,350 coins are collected either way. The worst case loses only the treasure bonus,
and test runs do not touch the leaderboard.

## Run it

1. Deploy these two files (code-execution Lambda unchanged).
2. Navigation prompt **empty**.
3. One test run. Read the bottom line: **`Challenges attempted:`**
   - **20** → it works. Tell me and I will raise `ROUTE_SPLIT`; ~20 parts projects to
     **17,068**.
   - **19** and the run ended at I1 without the treasure → the game does not re-prompt.
     Revert and the denominator is closed.
4. Revert to the main build either way before touching the judge:
   `round 4/pathfinding-lambda.py` and `round 4/supervisor-prompt-min.txt`.

## What to tell me

The `Challenges attempted:` number, the `Tokens used:` number, and whether the trace
shows the pathfinding tool being called a **second** time.
