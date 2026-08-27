# Round 4

## Deploy

| file | where |
|---|---|
| `pathfinding-lambda.py` | Pathfinding Lambda |
| `codeexecution-lambda.py` | CodeExecution Lambda |
| `websearch-lambda.py` | WebSearch Lambda (unchanged from Round 3) |
| `supervisor-prompt.txt` | supervisor prompt |

No keydoor Lambda. Doors go through CodeExecution.

## What changed from Round 3

| | Round 3 | Round 4 |
|---|---|---|
| doors | grey = first2+last2, yellow = 5th+7th | **red = reverse**, **green = letters→numbers** |
| keys | grey c42, yellow c43 | red c40, green c41 |
| new challenge | — | **Memory Trial c3** — counts tiles on the map |
| guardrail | c1, +400 | c1, **+100**, four of them |
| spikes | avoidable | **NOT avoidable** — 4 crossings are forced |
| distraction c17 | present | gone |
| start / treasure | A5 → J1 | **A1 → J1** |
| route | 69 moves | **105 moves** |

## Route: 105 moves, 4 spike crossings

Verified by simulation against the map:

```
moves 105  end J1  treasure True
walls hit NONE   spike crossings 4
scoring tiles 46  collected 46  missed 0
green key before green door: True
red key before red door    : True
```

**Spikes cannot be avoided.** Ten tiles sit in pockets whose only entrance is a
spike:

- `F5 c41` (the **green key**) and `F6 c7`, behind the spike at `F7`
- `A7 c1  B7 c2  A8 c7  B8 c7  A9 c7  B9 c7  A10 c18  B10 c7`, behind `A6`

Each pocket costs 2 crossings, in and out, so **4 is the minimum**. A local
search over 60,000 iterations could not beat 105 moves at 4 spikes — your manual
route was already optimal.

Skipping the pockets is worse. The A–B block alone is 2,450 points against 500 of
life bonus, and `F5` holds the green key that unlocks the +1000 green door.

**Expect to finish with 1 life** (5 − 4 spikes). That is correct, not a bug.

## The one real unknown: green door format

The challenge says *"replace letters with the numbers that represent them in
order"* but not how to join them. `zebra` = z26 e5 b2 r18 a1 could be:

| separator | output |
|---|---|
| `""` **(shipped)** | `2652181` |
| `"-"` | `26-5-2-18-1` |
| `" "` | `26 5 2 18 1` |

**Test the green door on the test map first.** If it is wrong, change
`GREEN_SEPARATOR` in `codeexecution-lambda.py` and redeploy. Nothing else needs
touching.

## Score estimate

| | |
|---|---|
| coins | 14,350 |
| life bonus (1 life) | 250 |
| treasure | 1,000 |
| token bonus | ~980 |
| **total** | **~16,580** |

18 challenges, so the token budget per challenge is looser than Round 3's 16.

## Carried over from Round 3 — do not re-test these

| finding | evidence |
|---|---|
| move array must use full words | `["r","u"]` and `"rruu"` both forfeited the run |
| never trust the model's map | it hallucinates one; the Lambda ignores all input |
| key pickup outputs only `Thanks`, no tool | transforming there fails to collect the key |
| doors via the tool | the only door path ever confirmed on the judge |
| score = lives + coins + treasure + token bonus | time and the custom-model line add nothing |
| 1 token ≈ 0.019 points | with 2 custom models, so ~53 tokens per point |
| run-to-run variance ≈ 44 tokens | ~1 point of noise on an unchanged config |
| prompt text is INPUT, so free | verbose reliability wording costs nothing |

Dead ends: shorter move encodings, shortening the route, renaming the Lambda
function, numbered character enumeration, hardcoding answers.
