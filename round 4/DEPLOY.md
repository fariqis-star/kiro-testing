# What to deploy — the only 4 things

## DEPLOY THESE

| file | goes where |
|---|---|
| `codeexecution-lambda.py` | the **CodeExecution** Lambda function |
| `pathfinding-lambda.py` | the **Pathfinding** Lambda function |
| `websearch-lambda.py` | the **WebSearch** Lambda function |
| `supervisor-prompt.txt` | paste into the **supervisor agent's instructions** box |

That is the whole list. Three Lambdas, one prompt.

## NEVER DEPLOY THESE — they are my local tools, not game code

| file | what it is |
|---|---|
| `audit.py` | pre-deploy checker. Runs on my side, verifies both Lambdas agree, route hits no walls, prompt matches the route length. Not part of the agent. |
| `solve_red.py` | transform search, v1 |
| `solve_red2.py` | transform search, v2 — produced the current candidate ladder |
| `route_skip_red.py` | route solver for the skip-the-door path |
| `verify_route.py` | route validator |
| `verify_unvisited.py` | proved the route visits all 61 non-wall cells |

If any of these went into a Lambda it would break that Lambda. They are throwaway
analysis scripts.

## NOT CODE AT ALL — notes and console settings

`guardrail-config.md` is console configuration you type into Bedrock by hand — the
denied topics, thresholds, `PatientRecordsLookup`. It is not deployed anywhere.

Every other `.md` is a record of findings: `RED-DOOR-TRIED.md`,
`RED-DOOR-EXHAUSTED.md`, `TEST-RUN-1-FINDINGS.md`, `DEPLOY-CHECKLIST.md`,
`FIX-THE-GATEWAY-FIRST.md`, `GEMINI-BRIEF-RED-DOOR.md`, `README.md`.

## For the run you are about to do

Changed since your last deploy, so all three need updating:

```
codeexecution-lambda.py    new red door ladder (7655, 6545, ...)
pathfinding-lambda.py      SKIP_RED_DOOR = False -> 105-move route, through the door
supervisor-prompt.txt      door discipline: tool call first, no narration
```

`websearch-lambda.py` has not changed in a long time. Only deploy it if you are
setting up from scratch.

## The one rule that keeps biting

`SKIP_RED_DOOR` exists in **both** `codeexecution-lambda.py` and
`pathfinding-lambda.py` and the two values **must match**. Either tool can answer a
navigation request, so if they disagree you get a different route depending on which
one the model reaches first.

```
False  ->  105 moves, goes through the red door   (hunting its answer)
True   ->   83 moves, turns back before it        (banks ~12,054)
```

Right now both are `False`.
