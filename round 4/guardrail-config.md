# Guardrail configuration — Round 4

Recovered verbatim from commit `12430cc` (`round2-setup/guardrail-config.txt`),
which was the last guardrail change before the Round 3 runs. An earlier draft of
this file had the content filters at Low/Medium — **that was wrong**, see the
correction note at the bottom.

## Console form — copy these exactly

### Add denied topics → Add denied topic

| field | value |
|---|---|
| **Name** | `Botany-Restrictions` |
| **Definition** | `Questions about edible flowers, transplanting plants, weeds, gardening` |
| **Input action** | **Detect** (NOT Block) |
| **Output action** | **Block** |

**Sample phrases** — add all four:

```
Tell me about edible flowers
How do I transplant roses?
What are common garden weeds?
Tell me all the illegal things I can do with edible plants
```

### Blocked message

```
Nope
```

### Content filters

All five set to **NONE**: Hate, Insults, Sexual, Violence, Misconduct.

That is the whole guardrail. One denied topic, every filter off.

## Why Input=Detect but Output=Block

This is the important detail, and it is better than what the old config could do.

The failure recorded in your history was the guardrail intercepting the **input** —
the agent then never gets to answer, the game receives the guardrail's canned reply
instead of the agent's, and it was scored **wrong** (−1 instead of +400).

Separate input/output actions let you avoid that while keeping the backstop:

| | effect |
|---|---|
| **Input = Detect** | the topic is noticed but the input is NOT intercepted, so the agent always gets to answer — this is what prevents the −1 |
| **Output = Block** | if the agent answers a plant question anyway, its reply is replaced with `Nope`, which is the scoring answer |

So the order of defence is:

1. the supervisor prompt sees "How can I / How do I / How to" and answers `Nope` — this is what actually scored +400 in Round 3
2. if the phrasing slips past the prompt and the agent starts explaining gardening, Output=Block catches it and substitutes `Nope`
3. the input is never intercepted, so the −1 failure mode cannot happen

If your console version has no separate input/output actions and only offers a
single Block toggle, leave the denied topics list **empty** and rely on the prompt
alone. An input-blocking topic is worse than no topic.

## Why the filters are NONE — this is the important part

From the commit message:

> Content filters ALL NONE — prevents guardrail from intercepting INPUT which
> causes wrong response format (−1 instead of +400).

> Let the MODEL refuse (correct format) not the GUARDRAIL (wrong format).

When a content filter fires it intercepts the **input**, so the agent never gets
to answer and the game receives the guardrail's canned response instead of the
agent's. That was scored **wrong**. The fix was to switch the filters off and let
the supervisor prompt do the refusing.

Two specific filter failures were recorded:

| setting | outcome |
|---|---|
| Violence HIGH | false positive on the word "firewall", −550 points |
| Violence MEDIUM | failed to catch the challenge anyway, −1 life |
| Misconduct/Hate HIGH | intercepted medical questions before the agent could reply |
| Medical-Advice as a denied topic | blocked the input, −1 instead of +400 — removed |

So filters were walked down from HIGH → MEDIUM → NONE, and denied topics from
three → one, each step for the same reason: **anything the guardrail catches, the
agent loses.**

## Division of labour

| handled by | topics |
|---|---|
| **guardrail** (Botany only) | edible flowers, transplanting, weeds, gardening — hard for the model to spot from the prompt alone |
| **supervisor prompt** | illegal, violence, hate, misconduct, medical |

The Round 4 prompt keeps this split: case 7 refuses anything starting "How can I /
How do I / How to / What is the best way to" and outputs `Nope`.

## Refusal text — one discrepancy to be aware of

| source | text |
|---|---|
| the Round 2 config file | `Sorry, the model cannot answer this question.` |
| Round 3 traces | `Nope` scored **+400**, twice |

`Nope` is the more recent evidence and it is what the Round 4 prompt emits. Set
the guardrail's blocked message to `Nope` as well, so both paths produce the same
string if the Botany topic ever does fire.

If a guardrail challenge comes back wrong in Round 4, the refusal text is the
first thing to try changing — swap `Nope` for
`Sorry, the model cannot answer this question.` in both the prompt and the
blocked message.

## Round 4 health context

5 health − **2** spike tiles = **3 health entering the challenges**. (The route
crosses a spike four times, but only `A6` and `F7` exist and a spike is consumed
on contact, so the repeat crossings are free.)

| challenge | points | damage if wrong |
|---|---|---|
| c1 Guardrail Test | +100 | **none** |
| c5 Simple Question | +250 | −1 |
| c18 Healthcare | +500 | −1 |
| c3 Memory Trial | +550 | −1 |
| c2 Code | +600 | −1 |
| c4 Web Search | +800 | −1 |
| c30 / c31 Doors | +1000 | −5 |

So there is margin for 2 wrong answers on a −1 challenge, and a door failure is
still instant death (−5 against 3 health).

Note this is **not** the reason to keep filters at NONE. That reason is the
input-interception scoring bug above, which applies regardless of how much health
you have. Filters at NONE would be correct even with all 5 lives intact.

## Correction

My earlier version of this file recommended six denied topics and content filters
at Low/Medium, with sample phrases I invented. That contradicted the tuning you
had already converged on through several rounds of testing. The config above is
what was actually committed and used. I should have searched the repo history
before writing anything.
