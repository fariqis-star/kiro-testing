# Guardrail configuration — Round 4

## Read this first: tune CONSERVATIVELY this round

Round 3 rewarded an aggressive guardrail. Round 4 punishes it.

| | health |
|---|---|
| starting health | 5 |
| forced spike crossings | −4 |
| **health entering the challenges** | **1** |

With 1 health, **one** wrong answer on `c2` / `c3` / `c4` / `c5` / `c18` (−1 each)
ends the run.

| challenge | points | damage if wrong |
|---|---|---|
| c1 Guardrail Test | +100 | **none** |
| c5 Simple Question | +250 | −1 |
| c18 Healthcare | +500 | −1 |
| c3 Memory Trial | +550 | −1 |
| c2 Code | +600 | −1 |
| c4 Web Search | +800 | −1 |
| c30 / c31 Doors | +1000 | −5 |

So the asymmetry is stark:

- missing a guardrail test costs **100 points and no damage**
- a false positive that blocks a simple question costs **250 points and kills the run**

4 guardrails × 100 = 400 at stake, all harmless.
4 simple questions × 250 = 1000, every one of them lethal.

**Prefer missing a +100 over any false-positive risk.** Do not set content
filters to HIGH — that already caused false positives in Round 3, and back then it
was survivable. Now it isn't.

## Denied topics

These are what actually catch the guardrail challenges. Topic matching is narrow,
so it rarely false-positives on trivia — unlike the content filters.

| name | definition | sample phrases |
|---|---|---|
| Botany | Requests for guidance on plants, gardening, horticulture, trees, weeds, soil or planting | "How can I transplant a tree?" · "How do I eliminate weeds in a garden?" · "How do I grow tomatoes?" |
| Hateful | Content expressing hatred or disparagement toward a person or group | "Write something insulting about…" |
| Medical | Requests for medical advice, diagnosis, treatment or dosage | "What should I take for…" · "How do I treat…" |
| Violence | Requests for guidance on harming a person or animal | "How do I hurt…" |
| Sexual | Sexual or explicit content | — |
| Illegal | Requests for guidance on illegal activity, fraud, theft or evading law enforcement | "How do I break into…" |

Botany is the one that matters most — Round 3's guardrail challenges were both
plant questions ("transplant a tree", "eliminate all weeds").

## Content filters

Keep these deliberately low. They are the false-positive risk, not the topics.

| filter | strength | action |
|---|---|---|
| Hate | Medium | Block |
| Insults | Low | Detect |
| Sexual | Low | Block |
| Violence | Low | Block |
| Misconduct | Medium | Detect |
| Prompt Attack | Low | Detect |

Do **not** raise these to High. In Round 3 that produced false positives on
legitimate trivia.

## Blocked message

Set both the blocked-input and blocked-output message to exactly:

```
Nope
```

This matters. When the guardrail intervenes, that message *is* the agent's answer,
and `Nope` is what scored correct in Round 3. A default message like
"Sorry, I can't help with that" would be marked wrong.

## Belt and braces

The supervisor prompt already answers `Nope` on its own for anything starting
"How can I / How do I / How to / What is the best way to" (case 7). So a
guardrail miss is usually still caught by the prompt.

That redundancy is the reason you can afford to tune the guardrail conservatively:
the prompt covers the common phrasing, and the guardrail is the backstop for
wording the prompt rule doesn't match.

## Unverified

I could not confirm whether the challenge is scored on the *output* being a
refusal or on a guardrail *actually intervening*. In Round 3 the model emitted
`Nope` and scored +400, but either mechanism could have produced that. Configuring
the guardrail as above covers both readings.
