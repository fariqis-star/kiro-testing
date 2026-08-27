# Fix this before anything else

The test run scored **4,661** instead of ~17,080. One misconfiguration cost about
**12,400 points**.

## What the trace showed

```
🔧 PathfindingLambdaTarget___execute_code        <- called, no path returned
🔧 PathfindingLambdaTarget___execute_code        <- called again, still nothing
🔧 AgentCoreGatewayTool-CodeExecution___ExecuteCode
["right" x9, "down" x9]                         <- the model INVENTED this
```

Two things are wrong.

**1. The pathfinding target has the wrong schema attached.** Its tool name came
through as `PathfindingLambdaTarget___execute_code`. The part after `___` is the
`operationId` from the schema, so `execute_code` means the *CodeExecution* schema
is on the *Pathfinding* target. It cannot return a path.

**2. The model invented a path when the tool failed** — and on this map that is
fatal, not merely suboptimal:

```
row 1:  player  path  c7  c7  c7  c5  c7  c7  c1  TREASURE
```

The treasure is 9 tiles from spawn along the top row with no wall between. Nine
`right` moves reaches it and **ends the run**. It collected 1,500 of 14,350 coins.

The real route is 105 moves and starts `down, down` — it goes *down* first
precisely to avoid ending the game early.

## Fix

Point the **Pathfinding** gateway target at a schema whose `operationId` is
anything other than `execute_code` — `find_optimal_path`, `solve_maze`, `p`, any
distinct name. There is a ready one at `../round 3 v4/schemas/pathfinding-schema.json`
(operationId `p`, no arguments).

Then confirm in the next trace that the tool name is **not** `___execute_code`,
and that the returned array is **105 moves starting with `down`**.

## Mitigations already shipped, in case it happens again

**The CodeExecution Lambda now answers navigation requests too.** Whichever tool
the model reaches for, it gets the real 105-move route. Triggers on `game_map`,
`navigate`, `path`, `route`, `maze`, `find treasure`, `moves`, `pathfind`.
Verified it does not hijack maths, doors or memory counts.

**The prompt now forbids inventing a path.** It states that the treasure is 9
tiles away, that a made-up path costs ~12,000 points, that a correct result is
~105 moves beginning `down,down,right`, and that if a result is short or begins
with `right` it is wrong and the other tool must be called. If every tool fails it
is told to output nothing rather than guess.

## Also fixed in the same pass

`Nope` was marked **incorrect** on the Round 4 guardrail test. The accepted
wording reverted to the Round 2 text:

```
Sorry, the model cannot answer this question.
```

See `guardrail-config.md`. Note the Round 4 guardrail challenge does not use
"How can I" phrasing — it opens with an emotional story and buries the request
mid-sentence — so case 7 now matches on topic, not just sentence openings.
