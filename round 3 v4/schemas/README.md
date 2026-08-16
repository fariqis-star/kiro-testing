# Short-name schemas

Replace the API schema on each gateway target with the matching file here.

## Why

The model has to *generate* the tool name every time it calls a tool, so the name
costs output tokens on every call. The part after `___` is the `operationId` from
your schema, which is the part you control.

```
AgentCoreGatewayTool-CodeExecution-c3e5___execute_code
|------------- gateway target -------------|  |- operationId -|
```

| | chars/run | approx tokens |
|---|---|---|
| current names | 363 | ~104 |
| `p` / `c` / `w` | 282 | ~81 |

About **23 tokens**, plus another **~10** from the path tool taking no arguments
at all (no more `game_map=[[]]`). Roughly 33 tokens total, which is about
0.6 points. Small, but it is free and carries no correctness risk.

## Mapping

| file | target | operationId | arguments |
|---|---|---|---|
| `pathfinding-schema.json` | Pathfinding | `p` | none |
| `codeexecution-schema.json` | CodeExecution | `c` | `code` |
| `websearch-schema.json` | WebSearch | `w` | `url`, `keywords` |

## Important

Do **one** target first, run a test, and confirm the model still calls it.

Short names lean on the `description` field for routing, so each schema has a
deliberately explicit description. The supervisor prompt no longer references
tool names at all — it describes them as PATH TOOL / COMPUTE TOOL / PAGE TOOL —
so renaming cannot desynchronise the prompt.

The pathfinding Lambda ignores all input and returns the verified path, so
declaring zero parameters is safe. Verified against an empty event.
