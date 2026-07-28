# Round 2 - Combined Agent Setup (Experimental)

## Architecture
```
Supervisor (Nova 2 Lite or Claude)
└── Combined Agent (Claude + All 4 Lambdas)
    ├── RedKey Lambda (store key, reverse at door)
    ├── WebSearch Lambda (fetch URLs)
    ├── CodeExecution Lambda (run Python)
    └── Pathfinding Lambda (BFS path)
```

Optional: Add custom Qwen dummy agent for RL bonus.

## Strategy
- Fewer routing decisions = fewer tokens
- One agent handles everything = less supervisor thinking
- Supervisor only answers c5 (simple trivia) and c18 (healthcare JSON) directly

## Risk
- Combined agent might confuse which tool to use
- If it fails on judge's different questions, fall back to winning Setup A (ai-competition-stuff repo)

## Lambda Code
All Lambda code is the same as Round 1 (see ai-competition-stuff repo):
- subagent-pathfinding-lambda.py
- subagent-codeexecution-lambda.py
- subagent-websearch-lambda.py
- redkey-lambda-v2.py (from kiro-testing repo)
