# AI League Round 2 - PolyCC Malaysia

## Folder Structure

```
working-version/          ← DEPLOYED (scores 15,666 on judge, 17,900 on test)
├── pathfinding-lambda.py
├── codeexecution-lambda.py
├── websearch-lambda.py
├── keydoor-lambda.py
└── supervisor-prompt.txt

experimental/             ← TESTING (fixes for counting on judge)
├── pathfinding-with-counts.py    ← adds tile_counts to pathfinding response
└── supervisor-prompt-with-counts.txt  ← tells model to recall counts from pathfinding

game-events-*.json        ← test run logs
```

## Current Status
- Test score: 17,900+ (14/14 correct)
- Judge score: 15,666 (11/14 correct - fails Violet + 2 counting)
- Leaderboard: #17

## Known Issues on Judge
1. **Violet (c1)**: Guardrail doesn't fire reliably (RNG on denied topic matching)
2. **Counting (c3) x2**: Model can't recall map data (conversation truncated on judge)

## The Fix (experimental/)
- Pathfinding Lambda returns `tile_counts` in its response alongside the path
- Model sees counts in pathfinding tool response (stays in conversation history)
- When counting question comes later, model recalls from earlier tool response
- No hardcoding, no map needed in context, works for ANY counting question

## Architecture
- Supervisor: Claude Haiku
- 4 Lambda tools: Pathfinding, Codeexecution, WebSearch, Keydoor
- 2 dummy custom models (Qwen3-0.6B) for token bonus (+70% reduction)
- Guardrail: 6 denied topics (Medical, Botany, Hateful, Violence, Sexual, Illegal)
- Memento: game_memory (currently blank)
