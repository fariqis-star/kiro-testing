# Sub-agents multiply `challenges attempted`. The leaderboard proves it.

## The evidence

Assume every top team maxes coins (14,350) with 3 lives (750) and the treasure (1,000).
That fixes 16,100, so `bonus = score - 16,100` and `challenges = tokens / (1000 - bonus)`.

| # | alias | score | tokens | bonus | avg | implied challenges |
|---|---|---|---|---|---|---|
| 1 | Bedrock Blitz POLIMAS 659 | 17,094 | **370** | 994 | 6 | **57–67** |
| 2 | BX Team Polimas225 | 17,093 | **423** | 993 | 7 | **56–65** |
| 3 | SixSevenPSMZA13 | 17,084 | 985 | 984 | 16 | **60–64** |
| 4 | PSPTechnician258 | 17,057 | 1,615 | 957 | 43 | **37–38** |
| 5 | P2A-PBU-748-3 | 17,056 | 837 | 956 | 44 | 19 |
| 6 | Ideas Beyond PMJ 1061 | 17,048 | 984 | 948 | 52 | 19 |
| 7 | PhineasAndFerbPMKL164 | 17,046 | 1,019 | 946 | 54 | 19 |
| 8 | PBU Sygentic 01 | 17,045 | 1,045 | 945 | 55 | 19 |
| 9 | ZeroTwo-KKTS-1023 | 17,042 | 1,094 | 942 | 58 | 19 |
| 10 | Inifity agents ptss sem1 | 17,031 | 1,311 | 931 | 69 | 19 |

A 19-challenge model predicts ranks **5 through 10 exactly** — six consecutive rows, to
the point. It then fails for ranks 1–4, by +13, +15, +36 and +42.

The implied challenge counts are not arbitrary:

```
19 x 1 = 19   ranks 5-10   (supervisor only - us)
19 x 2 = 38   rank 4       (37-38 implied)
19 x 3 = 57   ranks 1-3    (56-67 implied)
```

**Every agent that participates multiplies the denominator.** The orchestration panel
allows up to 5 sub-agents.

## And it cuts tokens at the same time

Ranks 1 and 2 report **370 and 423** output tokens against our 1,045 — less than our
route array alone. So sub-agent output is evidently **not billed to the total**, which
means work moved off the supervisor stops being charged.

That is the opposite of the objection ("a sub-agent just adds tokens"): the denominator
grows *and* the numerator shrinks. Both directions favourable.

## Why I got this wrong twice

First I proposed sub-agents for the wrong reason (I guessed `19 x 2 = 38` without knowing
what the counter counted). Then, when challenged, I abandoned the idea using the failed
coordinate run as proof that the counter is purely game-side. That run reported
`Challenges attempted: 1` — consistent with *one agent* submitting one route, and equally
consistent with the multiplier theory. I treated an ambiguous data point as decisive
because it agreed with the objection in front of me.

Six exact predictions and a clean 19/38/57 pattern is what evidence actually looks like.

## The test: one sub-agent, one run

Add a single **pathfinding sub-agent** (prompt in `pathfinding-subagent.txt`), give it the
Pathfinding Lambda, and run the test map once. Read two numbers:

| observation | meaning |
|---|---|
| `Challenges attempted: 38` | multiplier confirmed |
| `Tokens used` well below 1,045 | sub-agent output is not billed |

Projected, assuming coins/lives/treasure unchanged:

| challenges | tokens | total |
|---|---|---|
| 19 | 1,045 | 17,045 (today) |
| 38 | 1,045 | **17,073** |
| 38 | 800 | **17,079** |
| 57 | 800 | **17,086** |
| 57 | 400 | **17,093** |

Rank 1 is 17,094. This is a ~50-point opportunity, not the 11 I had been chasing.

## Sequence

1. One sub-agent (pathfinding). Confirm 38 and watch the token count.
2. If confirmed, add a second and third for the challenge-answering path, aiming at 57.
3. Keep the guardrail on the supervisor — it emits `Nope` for one token and passes.
4. Never trade accuracy for tokens: a wrong door is −1,000 **and −5 lives**, which ends
   the run, while 200 tokens is ~11 points.
