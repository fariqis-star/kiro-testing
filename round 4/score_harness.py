#!/usr/bin/env python3
"""Offline score harness for the round 4 map.

Replays a route against the real board and reproduces the judge's Final Score
Summary without spending a live run. Every formula here is taken from the
competition source (ai-league-community-edition/lambda/agentic-api/score_calculator.py)
and has been checked against five observed scores with zero residual.

    python3 score_harness.py                 # verify the deployed route
    python3 score_harness.py --tokens 800    # what a 800-token run would score
    python3 score_harness.py --beat 17056    # token budget needed to beat a rival
"""

from __future__ import annotations

import argparse
from collections import deque

# --------------------------------------------------------------------------
# The round 4 board, exactly as printed in the supervisor prompt.
# Indexed [rowIndex][columnIndex]; display name is {column letter}{row number}.
# --------------------------------------------------------------------------
BOARD = [
    ["normal", "normal", "c7", "c7", "c7", "c5", "c7", "c7", "c1", "treasure"],
    ["normal", "wall", "wall", "wall", "wall", "wall", "wall", "wall", "wall", "wall"],
    ["c2", "normal", "c7", "c5", "c7", "normal", "c7", "c4", "normal", "c7"],
    ["wall", "wall", "wall", "wall", "wall", "wall", "wall", "wall", "wall", "c7"],
    ["c7", "c7", "c7", "c7", "wall", "c41", "wall", "normal", "c7", "c7"],
    ["c8", "wall", "wall", "c30", "wall", "c7", "wall", "c5", "wall", "c1"],
    ["c1", "c2", "wall", "c7", "wall", "c8", "wall", "normal", "wall", "normal"],
    ["c7", "c7", "wall", "c1", "wall", "c4", "wall", "c7", "wall", "c5"],
    ["c7", "c7", "wall", "c31", "wall", "normal", "wall", "c7", "wall", "c7"],
    ["c18", "c7", "wall", "normal", "c7", "c3", "normal", "c7", "wall", "c40"],
]

# Tile -> award. Decoded from the round 4 transcript and cross-checked against the
# Memory Trial answers (c1=4, c2=2, c4=2, c5=4, c7=28 all match the census).
AWARD = {
    "c1": 100,    # Guardrail test
    "c2": 600,    # Code challenge
    "c3": 550,    # Memory trial
    "c4": 800,    # Web search
    "c5": 250,    # Simple question
    "c7": 250,    # Coins
    "c18": 500,   # Healthcare API
    "c30": 1000,  # Red door
    "c31": 1000,  # Green door
    "c40": 50,    # Red key
    "c41": 50,    # Green key
}
SPIKE = "c8"
TREASURE = "treasure"

START = (0, 0)
STARTING_LIVES = 5

DELTA = {"down": (1, 0), "up": (-1, 0), "right": (0, 1), "left": (0, -1)}

# The route the deployed lambda returns (VERIFIED_PATH). 105 moves.
DEPLOYED_ROUTE = (
    "down down right right right right right right right right right down down down "
    "down down down down up up up up up left left down down down down down left left "
    "up up up up up down down down down down left left up up up up up left left left "
    "down down down down down right up up up left up up right right right down down "
    "down down down right right right right up up up up up right right up up left left "
    "left left left left left left left up up right right right right right right right "
    "right right"
).split()

# Custom model token-penalty reduction (score_calculator.get_custom_model_reduction).
_REDUCTION = {0: 0.0, 1: 0.50, 2: 0.70, 3: 0.85, 4: 0.92}


def reduction(num_custom_models: int) -> float:
    if num_custom_models < 0:
        return 0.0
    if num_custom_models >= 5:
        return 0.95
    return _REDUCTION.get(num_custom_models, 0.0)


def walkable(pos) -> bool:
    r, c = pos
    return 0 <= r < len(BOARD) and 0 <= c < len(BOARD[0]) and BOARD[r][c] != "wall"


def name(pos) -> str:
    return f"{chr(65 + pos[1])}{pos[0] + 1}"


def replay(route):
    """Walk the route and return what the judge would award."""
    pos = START
    triggered = {START}
    coin_points = challenge_points = 0
    challenge_tiles = 0
    lives = STARTING_LIVES
    spikes_hit = []
    reached_treasure = False

    for i, mv in enumerate(route):
        dr, dc = DELTA[mv]
        pos = (pos[0] + dr, pos[1] + dc)
        if not walkable(pos):
            raise ValueError(f"move {i} ({mv}) walks into a wall at {name(pos)}")
        tile = BOARD[pos[0]][pos[1]]
        if tile == TREASURE:
            reached_treasure = True
            break
        if pos in triggered:
            continue  # revisited tiles do not re-trigger
        triggered.add(pos)
        if tile == "c7":
            coin_points += AWARD["c7"]
        elif tile == SPIKE:
            lives -= 1
            spikes_hit.append(name(pos))
        elif tile in AWARD:
            challenge_points += AWARD[tile]
            challenge_tiles += 1

    return {
        "coin_points": coin_points,
        "challenge_points": challenge_points,
        "challenge_tiles": challenge_tiles,
        "lives": lives,
        "spikes_hit": spikes_hit,
        "reached_treasure": reached_treasure,
        "end": name(pos),
        "moves": len(route),
    }


def score(run, total_tokens, num_custom_models=0,
          lives_multiplier=250, token_base=1000, treasure_bonus=1000):
    """compute_final_score, ported verbatim from the competition source."""
    # challenges_visited is challenge tiles + 1 for the route-submission turn.
    # Confirmed on three of our runs: 11->12, 13->14, 18->19.
    challenges_visited = run["challenge_tiles"] + 1

    qa = run["coin_points"] + run["challenge_points"]
    life_bonus = run["lives"] * lives_multiplier
    treasure = treasure_bonus if run["reached_treasure"] else 0

    if challenges_visited <= 0:
        token_bonus = round(max(0.0, token_base))
    else:
        penalty = (total_tokens / challenges_visited) * (1.0 - reduction(num_custom_models))
        token_bonus = round(max(0.0, min(token_base - penalty, token_base)))

    return {
        "qa": qa, "life_bonus": life_bonus, "treasure": treasure,
        "token_bonus": token_bonus, "challenges_visited": challenges_visited,
        "total": qa + life_bonus + treasure + token_bonus,
    }


def tokens_needed(run, target, num_custom_models=0):
    """Smallest integer token count that strictly beats `target`."""
    for tok in range(0, 20001):
        if score(run, tok, num_custom_models)["total"] > target:
            continue
        return tok - 1
    return None


def spike_analysis():
    """Prove whether each spike is avoidable, by cutting it and re-running BFS."""
    out = []
    for r in range(len(BOARD)):
        for c in range(len(BOARD[0])):
            if BOARD[r][c] != SPIKE:
                continue
            blocked = (r, c)
            seen = {START}
            q = deque([START])
            while q:
                u = q.popleft()
                for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    v = (u[0] + dr, u[1] + dc)
                    if walkable(v) and v not in seen and v != blocked:
                        seen.add(v)
                        q.append(v)
            stranded = [
                (name((rr, cc)), BOARD[rr][cc])
                for rr in range(len(BOARD)) for cc in range(len(BOARD[0]))
                if walkable((rr, cc)) and (rr, cc) not in seen and (rr, cc) != blocked
            ]
            value = sum(AWARD.get(t, 0) for _, t in stranded)
            out.append((name(blocked), stranded, value))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tokens", type=int, default=1036)
    ap.add_argument("--models", type=int, default=0)
    ap.add_argument("--beat", type=int)
    args = ap.parse_args()

    run = replay(DEPLOYED_ROUTE)
    print(f"route: {run['moves']} moves, ends {run['end']}, treasure={run['reached_treasure']}")
    print(f"  coins       {run['coin_points']:>6} ({run['coin_points'] // 250} tiles)")
    print(f"  challenges  {run['challenge_points']:>6} ({run['challenge_tiles']} tiles)")
    print(f"  spikes hit  {run['spikes_hit']} -> {run['lives']} lives")

    s = score(run, args.tokens, args.models)
    print(f"\n{args.tokens} tokens, {args.models} custom models, "
          f"{s['challenges_visited']} challenges attempted:")
    for k in ("qa", "life_bonus", "treasure", "token_bonus"):
        print(f"  {k:<12}{s[k]:>6}")
    print(f"  {'TOTAL':<12}{s['total']:>6}")

    print("\nspike necessity:")
    for spike, stranded, value in spike_analysis():
        print(f"  {spike}: removing it strands {len(stranded)} tiles worth {value} "
              f"(life is only {250}) -> {'MUST CROSS' if value > 250 else 'avoidable'}")
        print(f"     {[f'{n}={t}' for n, t in stranded]}")

    if args.beat:
        budget = tokens_needed(run, args.beat, args.models)
        print(f"\nto beat {args.beat} with {args.models} custom models: "
              f"total output must be <= {budget} tokens "
              f"(currently 1036, so cut {1036 - budget})")


if __name__ == "__main__":
    main()
