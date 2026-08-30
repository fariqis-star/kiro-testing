# Token budget — the only lever left on this map

## The board is solved. Only tokens remain.

Verified with `score_harness.py`, which replays the deployed route against the real
board and reproduces the judge's summary exactly:

| component | value | headroom |
|---|---|---|
| coins | 7,000 (28/28 tiles) | **0 — maxed** |
| challenges | 7,350 (18/18 tiles, all correct) | **0 — maxed** |
| treasure | 1,000 | **0 — maxed** |
| lives | 750 (3) | **0 — both spikes are forced** |
| token bonus | 945 | **+55** |
| **total** | **17,045** | ceiling **17,100** |

We are at 99.7% of the theoretical maximum for this map. Every remaining point is
in the token bonus.

### Both spikes are mandatory — do not try to route around them

`score_harness.py` cuts each spike and re-runs BFS. Both are cut vertices:

- **A6** — removing it strands 8 tiles worth **2,450** (5 coins, the B7 code
  challenge, A10 healthcare, A7 guardrail). Costs 250. Cross it.
- **F7** — removing it strands F5 (green key) and F6 (coin). Direct value is only 300,
  but losing the green key also forfeits the **green door D9 (+1,000)**, so the true
  cost of avoiding it is 1,300. Cross it.

3 lives is the maximum achievable score on this board. `life_bonus = 750` is maxed.

### The route is optimal and incompressible

- **Length:** an independent TSP solve over all 46 required tiles, with the
  key-before-door constraints and treasure last, returns **105 moves** — identical to
  the deployed route. There is no shorter route.
- **Encoding:** `MOVE_FORMAT` must stay `"array"`. Bare words, csv and spaced were all
  run and all ended the run with 0 coins. Note the community-edition parser
  (`path_parser.py`) *does* accept free-text direction words via
  `_try_direction_extraction` — **the real judge does not behave like the community
  edition.** Do not re-derive this from the open-source code; it is measured.

## Where the 1,036 tokens go

Estimated, not measured — no tokenizer is available offline. Treat as ±15%.

| item | tokens | notes |
|---|---|---|
| route array (105 × ~4) | ~420 | irreducible, see above |
| 8 tool calls: names + JSON | ~176 | ~22 each, mostly the long tool name |
| 18 answers | ~110 | already minimal |
| red-door reasoning leak (run 2) | ~55 | present run 2, absent run 1 |
| **accounted** | **~761** | |
| **residual — reasoning/thinking** | **~275** | invisible in the transcript, billed as output |

**Independent corroboration of the residual:** the dead test run emitted only a
10-pair coordinate array (~70 tokens) plus one tool call (~20), yet was billed
**401 tokens**. That is ~310 tokens of invisible output on a single turn — the same
order as the 275 estimated above, derived from a completely different run.

Further corroboration: run 1 and run 2 were byte-identical in every visible output
yet differed by **239 tokens** (1,275 vs 1,036). Only the invisible component can
account for a swing that size. That variance (~12 points) is itself larger than the
11-point gap to #5.

## Target

To beat #5's 17,056 with 0 custom models: **total output ≤ 826 tokens.** Cut 210.

| action | tokens saved | cumulative total | score | risk |
|---|---|---|---|---|
| baseline | — | 1,036 | 17,045 | — |
| suppress reasoning/thinking budget | ~275 | 761 | **17,060** | config only |
| + kill red-door leak | ~55 | 706 | **17,063** | falls out of the above |
| + shorten operationIds | ~30 | 676 | **17,064** | low, test one at a time |
| + drop the ```json fence | ~4 | 672 | **17,065** | none |
| + rename gateway targets | ~100 | 572 | **17,071** | high, notes say impossible |

**Suppressing the reasoning budget is mandatory.** Everything else that is safe adds up
to only ~89 tokens, far short of the 210 required. Reasoning alone is sufficient to take
the lead; the rest is margin against run-to-run variance, which is itself ~239 tokens
and therefore larger than the gap we are fighting over.

### 1. Reasoning budget — worth ~275 tokens (~14 points)

Claude Haiku 4.5 bills reasoning tokens as output. The supervisor prompt already
forbids visible thinking and Haiku mostly complies in the visible channel, so this is
a **model configuration** setting, not a prompt problem. Check whether the supervisor's
Model row exposes extended thinking / reasoning budget / max output tokens and set it
to minimum or off.

### 2. Tool names — worth ~30 tokens confirmed, up to ~130 if the prefix moves

Each call emits its own name as output tokens.
`AgentCoreGatewayTool-CodeExecution-5d5c___execute_code` is ~16 tokens, and there are
8 calls per run — ~130 tokens total. The name is `<gatewayTargetName>___<operationId>`.

**Confirmed controllable:** the part after `___` is the `operationId` from our own
schema (`FIX-THE-GATEWAY-FIRST.md` line 19). Shortening `execute_code` → `e`,
`scrape_web_page` → `w`, `pathfinding` → `p` saves ~3–4 tokens per call, **~30 tokens
across 8 calls (~1.6 points)**. Low risk — but note that changing an `operationId`
re-points the gateway target, and TEST-RUN-1 shows a mismatched schema silently
returns nothing. Change one target, test, then the next.

**Unverified:** the prefix (`AgentCoreGatewayTool-CodeExecution-5d5c`, ~12 tokens) is
the gateway target name, set at target creation. The `-5d5c` suffix looks
competition-generated, so the prefix may not be fully ours. If a target can be
recreated with a one-character name this is worth another ~100 tokens (~5 points) —
worth one experiment, but it is the riskiest change on this list and the round 4 notes
already assert it cannot be done.

### 3. Red-door reasoning leak — worth ~55 tokens (~3 points)

Run 2 emitted "I need to answer the question... From the conversation history..." before
the red-door tool call. Run 1 did not. Same config, so this is the reasoning budget
surfacing into the visible channel — fixing (1) should remove it. It is also a
correctness risk: the model narrating its own routing is one step from emitting the raw
key value instead of calling the tool.

### 4. JSON fence — worth ~4 tokens

The healthcare answer comes out wrapped in a ```json fence in both runs, despite rule 7
requiring the first character to be `{`. It grades correct, so the judge is lenient
here, but we are paying for something explicitly forbidden.

## Custom models: closed

The leaderboard is entirely explained by the custom-model token-penalty reduction
(0→0%, 1→50%, 2→70%, 3→85%, 4→92%, 5+→95%), which reproduces all five known scores
exactly at 19 challenges. BX Team = 2 models, Bedrock Blitz = 1 model, #5 and us = 0.

We cannot use it: deploying a custom model fails on an account-level SageMaker quota
(shared endpoint at 200/200 InferenceComponents). Requesting a quota increase is not
ours to make. Our ceiling is the 0-model ceiling of 17,100.

## Usage

```
python3 score_harness.py                # verify the deployed route
python3 score_harness.py --tokens 800   # score at a given token count
python3 score_harness.py --beat 17056   # token budget needed to beat a rival
python3 score_harness.py --models 2     # what a rival with 2 custom models scores
```


---

# TESTED EXPERIMENTS — round 4, all on Claude Haiku 4.5

| # | change | tokens | score | verdict |
|---|---|---|---|---|
| 0 | baseline (`supervisor-prompt.txt`) | **1,036** | **17,045** | **best known** |
| 0b | same build, re-run | 1,275 | 17,033 | variance only |
| 1 | lean prompt (cut the "never think out loud" lines) | 1,477 | 17,022 | **WORSE — reverted** |
| 2 | prompt v3 (zero-decision door rule) | 1,353 | 17,029 | no better than variance |
| 3 | **remove memory tool** | 1,017 | **7,315** | **CATASTROPHIC — never do this** |

## Experiment 1 — do not shorten the prompt

Cutting `never explain, never plan in text, never think out loud` and the
"argue with yourself at the door" clause made the model reason MORE, not less. The
red-door monologue grew from ~55 tokens to ~90. Those verbose suppression lines are
LOAD-BEARING. The prompt was never the source of the reasoning tokens.

## Experiment 3 — the memory tool is mandatory

Removing `memento_gamememory` did not save tokens (1,017 vs 1,036) and lost the game:

- **Memory Trial** — the model answered `Nope`, misrouting the memento to the guardrail
  rule. −1 life, and the +550 forfeited.
- **Green Door** — the model replied *"I don't have the key tile information yet...
  Please provide the green key 1 value"*. −5 damage, dead run, 6,400 coins, **7,315**.

So the memory tool is what actually carries the key values and the memento context
across turns. The keys are NOT reliably recoverable from conversation history alone.
`memento_gamememory` must always be attached.

## What experiment 2 did prove

Prompt v3 shrank the red-door leak from ~90 tokens to ~15
(*"I need to call COMPUTE with the red key value from the previous conversation."*) and
removed the ```json fence from the healthcare answer. Both real improvements — but total
tokens still landed at 1,353, inside normal run-to-run noise. The leak was never the
bulk of the cost.

## Where this leaves us: it is the MODEL

Token totals across five runs of near-identical builds: 1,017 / 1,036 / 1,275 / 1,353 /
1,477. Mean ~1,230, best ever 1,036. Unavoidable output is only ~322 tokens (route array
~212 + all 18 answers ~110). So **~700–900 tokens per run are invisible reasoning**, and
no prompt or tool change has moved that number.

Compare the leaderboard, where both score and tokens are published:

| rank | team | tokens | custom models |
|---|---|---|---|
| 4 | A_POLIMAS_72 | **405** | **0** |
| 5 | P2A-PBU-748-2 | **615** | **0** |
| — | us (best) | 1,036 | 0 |

Ranks 4 and 5 hit 405 and 615 tokens with ZERO custom models, so the SageMaker quota is
not what is blocking top 5. At ~83 tokens of overhead, those teams are almost certainly
NOT running a reasoning model.

Claude Haiku 4.5 bills extended-thinking tokens as output and the Edit Supervisor page
exposes no reasoning/thinking/max-tokens control. **The only untested lever left is the
Model dropdown.** Targets at 0 custom models:

    <= 598 tokens -> beats rank 5 (17,068)
    <= 389 tokens -> beats rank 4 (17,079)
    ~400 tokens   -> 17,079, rank 4

A non-reasoning model (Claude Haiku 3.5 / Sonnet 3.5, or Nova) doing the same routing
work would land in that range, because the lambdas — not the model — earn 95% of the
score.
