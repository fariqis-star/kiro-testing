# Round 3 v4

## Deploy

| file | where |
|---|---|
| `pathfinding-lambda.py` | Pathfinding Lambda |
| `codeexecution-lambda.py` | CodeExecution Lambda |
| `websearch-lambda.py` | WebSearch Lambda |
| `supervisor-prompt.txt` **or** `supervisor-prompt-safe.txt` | supervisor prompt |
| `schemas/` | optional, skip — see its README |

There is no keydoor Lambda. Doors go through CodeExecution.

## Which prompt

The two files are identical except for the door section.

| | doors | test | judge |
|---|---|---|---|
| `supervisor-prompt.txt` | yellow via tool, grey in prompt | ~13,981 | grey in prompt unproven |
| `supervisor-prompt-safe.txt` | **both via tool** | ~13,980 | **this path scored 13,978** |

Tool-based doors are the only door handling ever confirmed on the judge. In-prompt
doors have now passed on the test map twice and failed on the judge twice.

**The door token saving is no longer needed.** Earlier runs were ~1201 tokens with
both doors on the tool; since then compact math (−36), dropped JSON fences (−15)
and capped web keywords (−18) landed independently. Both-doors-on-tool now sits
at ~1059 tokens, and **1040–1093 all score 13,980**. So the safe variant already
meets the 13,980 target with nothing at risk.

Use `supervisor-prompt-safe.txt` unless you are specifically chasing 13,981.

## Judge is undiagnosable

Combat logs are test-map only — the competition blocks judge logs to prevent
reverse engineering. So judge failures can only be inferred from the score and
from which change correlates with the failure. Change **one thing per
submission**, or a failure tells you nothing.

## What is settled

| finding | status |
|---|---|
| move array must be full words | `letters` and `compact` both forfeited on judge |
| 69-move route is optimal | verified, 60k local-search iterations |
| never trust the model's map | it hallucinates one; Lambda ignores input entirely |
| key pickup outputs only `Thanks` | transforming there fails to collect the key |
| doors via tool | only judge-confirmed path |
| yellow needs positional counting | the fragile operation — always tool |
| score = lives + coins + treasure + token bonus | time and the custom-model line add nothing |
| 1 token ≈ 0.019 points | 53 tokens per point, with 2 custom models |
| run-to-run variance ≈ 44 tokens | ~1 point of noise on an unchanged config |

## Dead ends — do not spend submissions here

- shorter move encodings (parser rejects anything but full words)
- shortening the route below 69 moves (proven optimal)
- renaming the Lambda function (tool name comes from gateway target + schema
  operationId, not the function name)
- numbered character enumeration (`1A 2W`) — collides with digits in the value
- hardcoding answers (fails the moment the judge varies a question)
