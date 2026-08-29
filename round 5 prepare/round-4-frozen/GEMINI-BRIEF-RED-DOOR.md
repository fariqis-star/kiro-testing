# Red Door puzzle — briefing for an outside solver

Self-contained. Paste the whole thing. Everything below is observed from real game
traces, not inferred.

---

## The game

A 10x10 dungeon. An AI agent walks a fixed route and answers a challenge on each
tile. Tiles have type codes. Four are relevant:

| code | tile | points | damage if wrong |
|---|---|---|---|
| c41 | Green Key | +50 | — |
| c31 | Green Door | +1000 | −5 |
| c40 | Red Key | +50 | — |
| c30 | Red Door | +1000 | −5 |

The agent has 5 lives. **A wrong answer at the red door costs 5 lives and
instantly ends the run**, so every candidate costs one full attempt to test. That
is the entire difficulty: we cannot brute force.

Current score dying at the red door: **8,693**. Score if solved: **~17,043**.

---

## The four tile descriptions, verbatim

**Green Key (c41)**
> You must find this key before entering the green door.
> Using memory, it will give you the information you need to unlock it.
> When receiving a key don't forget to say Thanks.
> Points +50

**Green Door (c31)**
> To solve this challenge you must find the green key.
> Next, translate the code you receive by **replacing letters with the numbers that
> represent them in order**.
> Be careful! If you do not have the key the door does massive damage.
> Points +1000, Damage −5

**Red Key (c40)**
> You must find this key before entering the red door.
> Using memory, it will give you the information you need to unlock it.
> When receiving a key don't forget to say Thanks.
> Points +50

**Red Door (c30)**
> To solve this challenge you must find the red key.
> Next, translate the code you receive by **reading it backwards**.
> Be careful! If you do not have the key the door does a lot of damage.
> Points +1000, Damage −5

---

## GREEN IS SOLVED. This is the calibration you should reason from.

Exact trace, twice reproduced:

```
Green Key tile:   "Green Key 1 is: fghi"
Agent answered:   Thanks
Result:           correct, +50

Green Door tile:  "What is green key 1?"
Agent answered:   6789
Result:           correct, +1,000
```

`fghi` → `6789` is alphabet position: f=6, g=7, h=8, i=9. Exactly what green's
description says, applied with zero interpretation.

**Three things green proves about the answer format:**

1. The answer is a **bare token** — no spaces, no separators, no sentence.
   `6789` scored, so the grader is not expecting `6-7-8-9` or "The code is 6789".
2. **4 input characters produced 4 output characters.**
3. This author writes descriptions that mean literally what they say.

---

## RED IS UNSOLVED. Nine candidates dead, each one a whole run.

```
Red Key tile:   "Red Key 1 is: open"
Agent answered: Thanks
Result:         correct, +50          <- the key IS collected, confirmed

Red Door tile:  "What is red key 1?"
Result:         every answer below -> "incorrect", -5, run over
```

| # | submitted | reasoning behind it |
|---|---|---|
| 1 | `nepo` | literal string reverse — what the description says |
| 2 | `lkvm` | Atbash, a↔z mirror ("backwards through the alphabet") |
| 3 | `open` | no transform, raw key value |
| 4 | `12112213` | alphabet position counted from z (a=26 … z=1) |
| 5 | `1451615` | reverse first, then alphabet position (n14 e5 p16 o15) |
| 6 | `Thanks` | treat the door like a key pickup |
| 7 | `1516514` | green's exact rule on `open` (o15 p16 e5 n14) |
| 8 | `4156151` | green's rule, then reverse the digit string |
| 9 | `6376` | T9 phone keypad on `nepo` (n=6 e=3 p=7 o=6) |

Confirmed non-issues, so do not propose these:

- The key **is** collected before the door (the +50 fires, and the door asks its
  question rather than dealing no-key damage).
- Case and whitespace are not the problem — the answer is submitted trimmed, and
  `NEPO`/`OPEN` differ from dead candidates only by case.
- Separators are ruled out by green scoring on bare `6789`.
- The agent outputs the answer alone with no preamble. Green proves the plumbing
  works, since the identical mechanism scored +1000 on the same run that the red
  door rejected.

---

## The strongest structural clue

Green's description states a **complete** transform and lands on a **number**.

Red's description states *"reading it backwards"*, which lands on **letters**
(`nepo`) — and bare `nepo` was rejected. So either:

- **(A)** there is a **second, unstated step** that converts `nepo` into the final
  answer, and that hidden step is the trick; or
- **(B)** "reading it backwards" refers to something other than the key string; or
- **(C)** the red door's expected answer is not derivable from `open` at all
  (broken or independently-authored challenge), in which case the correct play is
  to route around the door and never answer it.

Also note the **shape constraint** from green: 4 characters in, 4 characters out.
Candidates 4, 5, 7 and 8 all produced 7–8 characters, which violates that shape.
Every 4-character candidate tried so far is dead (`nepo`, `lkvm`, `open`, `6376`),
which is suspicious in itself.

---

## Untested ideas we have not spent a run on

| candidate | derivation |
|---|---|
| `6736` | T9 keypad on `open` **without** reversing |
| `bcra` | ROT13 of `open` |
| `arcb` | ROT13 of `nepo` |
| `5161541` | reverse each letter's own position digits: o15→51 p16→61 e5→5 n14→41 |
| `9876` | green's answer `6789` reversed — i.e. red mirrors green rather than its own key |
| `ihgf` | the **green** key reversed, in case the doors are cross-wired |

---

## What we want from you

1. **Rank the candidates by probability**, including any you generate yourself. We
   get roughly one test per attempt, so ordering matters more than volume.
2. **Attack "reading it backwards" specifically.** What could "it" be other than
   the key string? The alphabet? The number? The question? The word's meaning
   (`open` → `close`/`shut`/`locked`)?
3. **Reconcile red with green.** Green's rule is stated completely and works
   literally. Why would the same author state red's rule incompletely? Is
   "backwards" a modifier on green's rule rather than a standalone instruction?
4. **Consider semantic answers.** Every attempt so far has been a character
   transform. Is `open` a word puzzle rather than a cipher? "Read backwards" on a
   palindrome-ish or reversible word? Note `open` reversed is `nepo`, which is not
   an English word — is that a hint the reverse is *not* meant literally?
5. **Tell us if you think it is unsolvable.** Nine well-formed answers rejected is
   real evidence for option (C). If you believe the challenge is broken, say so —
   that is worth ~3,400 points to us, because we would reroute instead of guessing.

Answer format required: a single bare token, no spaces, no punctuation, no
explanation — exactly like `6789`.
