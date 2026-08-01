"""
AWS Lambda - Map Counter tool for Bedrock Agent Game.

Counts specific cell types on the game map. 100% accurate.
No LLM memory/recall errors possible.

Input: {"game_map": [[...]], "count_type": "c7"} or {"game_map": [[...]], "count_type": "c1+c2"}
Output: {"count": N}
"""

import json
import re


def _parse_input(event):
    """Extract parameters from any event format."""
    # Try Bedrock agent format
    if "parameters" in event:
        params = {}
        for p in event.get("parameters", []):
            params[p.get("name", "")] = p.get("value", "")
        return params

    # Try requestBody format
    try:
        props = event.get("requestBody", {}).get("content", {}).get("application/json", {}).get("properties", [])
        params = {}
        for p in (props or []):
            if isinstance(p, dict):
                params[p.get("name", "")] = p.get("value", "")
        if params:
            return params
    except:
        pass

    # Try body format
    if "body" in event:
        body = event["body"]
        if isinstance(body, str):
            try:
                return json.loads(body)
            except:
                pass
        elif isinstance(body, dict):
            return body

    # Direct params
    return event


def lambda_handler(event, context):
    params = _parse_input(event)

    # Get game map
    game_map = params.get("game_map", [])
    if isinstance(game_map, str):
        try:
            game_map = json.loads(game_map)
        except:
            return {"statusCode": 200, "body": json.dumps({"count": 0, "error": "Invalid map"})}

    # Get what to count
    count_type = str(params.get("count_type", params.get("count", params.get("cell_type", ""))))

    if not game_map or not count_type:
        return {"statusCode": 200, "body": json.dumps({"count": 0, "error": "Missing game_map or count_type"})}

    # Handle "c1+c2" style (addition of multiple types)
    count_type = count_type.strip().lower()

    # Parse addition: "c1 + c2" or "c1+c2"
    if "+" in count_type:
        types_to_count = [t.strip() for t in count_type.split("+")]
    else:
        types_to_count = [count_type]

    # Count
    total = 0
    for row in game_map:
        for cell in row:
            if cell.lower() in types_to_count:
                total += 1

    return {"statusCode": 200, "body": json.dumps({"count": total})}
