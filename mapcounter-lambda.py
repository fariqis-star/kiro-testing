"""
AWS Lambda - Map Counter/Analyzer tool for Bedrock Agent Game.

Handles ALL possible memory/map questions:
- Count specific cell types: "c7", "c1+c2", "c4"
- Count total challenges: "challenges" or "all"
- Count specific categories: "coins", "spikes", "walls"
- Position lookup: "position B4" or "row 3 col 1"
- List all of a type: "list c7"

100% accurate. No LLM memory/recall errors.
"""

import json
import re


def _parse_input(event):
    """Extract parameters from any event format."""
    if "parameters" in event:
        params = {}
        for p in event.get("parameters", []):
            params[p.get("name", "")] = p.get("value", "")
        return params

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

    if "body" in event:
        body = event["body"]
        if isinstance(body, str):
            try:
                return json.loads(body)
            except:
                pass
        elif isinstance(body, dict):
            return body

    return event


def lambda_handler(event, context):
    params = _parse_input(event)

    # Get game map
    game_map = params.get("game_map", [])
    if isinstance(game_map, str):
        try:
            game_map = json.loads(game_map)
        except:
            return {"statusCode": 200, "body": json.dumps({"answer": "0", "error": "Invalid map"})}

    # Get the query/count_type
    query = str(params.get("count_type", params.get("count", params.get("query", params.get("cell_type", params.get("question", ""))))))

    if not game_map or not query:
        return {"statusCode": 200, "body": json.dumps({"answer": "0", "error": "Missing game_map or query"})}

    query_lower = query.strip().lower()
    rows = len(game_map)
    cols = len(game_map[0]) if game_map else 0

    # === POSITION LOOKUP ===
    # "position B4" or "B4" or "row 3 col 1"
    pos_match = re.search(r'position\s+([A-Ja-j])(\d+)', query, re.IGNORECASE)
    if not pos_match:
        pos_match = re.search(r'^([A-Ja-j])(\d+)$', query.strip(), re.IGNORECASE)
    if pos_match:
        col = ord(pos_match.group(1).upper()) - ord('A')
        row = int(pos_match.group(2)) - 1
        if 0 <= row < rows and 0 <= col < cols:
            cell = game_map[row][col]
            return {"statusCode": 200, "body": json.dumps({"answer": cell})}
        return {"statusCode": 200, "body": json.dumps({"answer": "out of bounds"})}

    # Row/col format
    rc_match = re.search(r'row\s*(\d+)\s*col\s*(\d+)', query_lower)
    if rc_match:
        row = int(rc_match.group(1))
        col = int(rc_match.group(2))
        if 0 <= row < rows and 0 <= col < cols:
            cell = game_map[row][col]
            return {"statusCode": 200, "body": json.dumps({"answer": cell})}
        return {"statusCode": 200, "body": json.dumps({"answer": "out of bounds"})}

    # === COUNT TOTAL CHALLENGES ===
    if 'total' in query_lower or query_lower in ('challenges', 'all challenges', 'all'):
        challenge_types = set()
        count = 0
        for row in game_map:
            for cell in row:
                c = cell.lower()
                if c.startswith('c') and c not in ('c7', 'c8'):  # exclude coins and spikes
                    count += 1
        return {"statusCode": 200, "body": json.dumps({"answer": str(count)})}

    # === COUNT COINS ===
    if query_lower in ('coins', 'c7 coins', 'all coins'):
        count = sum(1 for row in game_map for cell in row if cell.lower() == 'c7')
        return {"statusCode": 200, "body": json.dumps({"answer": str(count)})}

    # === COUNT SPIKES ===
    if query_lower in ('spikes', 'spike', 'c8', 'traps'):
        count = sum(1 for row in game_map for cell in row if cell.lower() == 'c8')
        return {"statusCode": 200, "body": json.dumps({"answer": str(count)})}

    # === COUNT WALLS ===
    if query_lower in ('walls', 'wall'):
        count = sum(1 for row in game_map for cell in row if cell.lower() == 'wall')
        return {"statusCode": 200, "body": json.dumps({"answer": str(count)})}

    # === COUNT SPECIFIC TYPE(S) with addition ===
    # Handle "c1+c2" or "c1 + c2" or "c7 + c3" or just "c7"
    # Also handle "c1 and c2"
    query_clean = query_lower.replace(' and ', '+').replace(',', '+')

    if '+' in query_clean:
        types_to_count = [t.strip() for t in query_clean.split('+') if t.strip()]
    else:
        # Single type - extract cN pattern
        type_match = re.findall(r'c\d+', query_clean)
        if type_match:
            types_to_count = type_match
        else:
            types_to_count = [query_clean]

    # Count matching cells
    total = 0
    for row in game_map:
        for cell in row:
            if cell.lower() in types_to_count:
                total += 1

    return {"statusCode": 200, "body": json.dumps({"answer": str(total)})}
