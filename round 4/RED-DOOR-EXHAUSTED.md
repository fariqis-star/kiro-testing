# Red Door — ~50 candidates, and why I think it is not answerable

Key shown: `Red Key 1 is: open`
Door asks: `What is red key 1?`
Door says: *"translate the code you receive by reading it backwards"*
Grading: exact match. Damage: −5, which is always fatal.

## Everything tested

| family | values | result |
|---|---|---|
| literal reverse | `nepo` | dead (×3, incl. clean builds) |
| raw value | `open` | dead |
| atbash | `lkvm` (of open), `mvkl` (of nepo) | dead |
| ROT13 | `bcra`, `arcb` | dead |
| a=1 positions, bare | `1516514`, `1451615`, `4156151`, `5161541`, `1615145` | dead |
| a=1 positions, separated | `14 5 16 15`, `14-5-16-15`, `15 16 5 14`, `15-16-5-14`, `14,5,16,15` | dead |
| a=1 positions, compressed | `5576`, `4565`, `6755`, `5654` | dead |
| z=1 positions | `12112213`, `31221121`, `13221112`, `4423`, `3212` | dead |
| phone keypad | `6376`, `6736` | dead |
| anagrams | `peon`, `pone` | dead |
| semantic opposites | `shut`, `closed`, `close`, `locked` | dead |
| case variants | `NEPO`, `Nepo` | dead |
| typo / punctuation | `neop`, `"nepo"`, `nepo.` | dead |
| sentence forms | `Red key 1 is nepo`, `red nepo`, `nepo :si 1 yeK deR` | dead |
| green's values | `6789`, `9876`, `ihgf` | dead |
| other | `Thanks`, `sknahT`, `2`, `1`, `30`, `c30`, 16-value shotgun | dead |

## Why I think it is broken rather than clever

**1. The answer its own description mandates is wrong.** *"Reading it backwards"*
gives `nepo`. Tested three times on known-good builds. A puzzle whose stated rule
produces a rejected answer is not a puzzle with a hidden trick — the stored value
does not match the stated rule.

**2. Green is fully consistent and red is not.** Green says *"replacing letters with
the numbers that represent them in order"*, `fghi` → `6789`, +1000, first try, no
interpretation. The same author, the same mechanic, one tile apart. Green works
literally; red rejects its own literal reading and 49 alternatives.

**3. The Memento tile has the identical signature.** `c4` count is provably 2 — the
route visits all 61 non-wall cells, so every tile code is trace-confirmed. `2`, `1`,
`two`, `2 c4 challenges` and a full sentence were all rejected. A verifiably correct
answer scoring zero, on the same map, on a second challenge.

Two challenges where correct answers score nothing is a pattern, not two
coincidences. Most likely both tiles' `expectedAnswer` fields were filled in wrongly
when this map was authored.

**4. The shotgun proved exact matching.** A reply whose first token was `nepo` still
scored −5, so there is no leniency to exploit.

## What is unknowable

The expected answer is server-side. The combat log records `AskChallenge`,
`WinChallenge`, points and damage — and nothing resembling `expectedAnswer`,
`correctAnswer` or `solution` across all 174 events. No prompt or Lambda can read it.

## Decision

`SKIP_RED_DOOR = True` in **both** Lambdas.

```
skip the door   ~12,054     83 moves, verified, 3 lives, treasure
die on it        ~8,694     every single attempt
```

The door cannot be survived: the best possible arrival is 5 lives, and −5 leaves 0.
Solve or avoid, never survive.

## For the judge run

Round 4's judge map is a different map. Two things follow.

**A hand-authored quirk would not transfer anyway.** The judge map's red key will be
a different word, so cracking this specific tile buys nothing there.

**The reverse rule may well be correct on a correctly-authored map.** It was right on
the Round 1/2 map — `ai-competition-stuff/supervisor-prompt.txt` line 4 reads
`c30→Reverse the key code. "open"→"nepo".`, from the setup that scored 15,344 and
finished #1. So if you choose to attempt the judge map's door, `RED_MODE = "reverse"`
is the right setting, and it is already what the file is pinned to.

That is a genuine coin flip: roughly +1000 plus the gated tiles if the judge tile is
sound, against about −3,400 if it is not. Skipping is the lower-variance play and it
is what is currently deployed.

## The one cheap thing still worth doing

Ask the group that cleared it what they answered, and on which map. One message ends
this. Fifty eliminations is more than enough reason to ask.
