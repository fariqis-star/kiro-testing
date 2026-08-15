"""
AWS Lambda - Key/Door tool for Bedrock Agent Game v3 (Round 3).

Handles ALL key/door colors:
- Red Key (c40): store value, return "Thanks"
- Red Door (c30): return stored value as-is (original)
- Green Key (c41): store value, return "Thanks"
- Green Door (c31): return stored value as-is (original)
- Grey Key (c42): store value, return "Thanks"
- Grey Door (c32): return first 2 chars + last 2 chars of stored value
- Yellow Key (c43): store value, return "Thanks"
- Yellow Door (c33): return 5th char + 7th char of stored value (1-indexed)

Uses /tmp/game_keys.json for persistence within warm Lambda instance.
"""

import json
import re
import os

# Global storage
KEY_STORAGE = {}
# Secondary in-memory map: value -> color for when /tmp is wiped
VALUE_TO_COLOR = {}
STORAGE_FILE = "/tmp/game_keys.json"


def _load_storage():
    global KEY_STORAGE
    try:
        if os.path.exists(STORAGE_FILE):
            with open(STORAGE_FILE, 'r') as f:
                KEY_STORAGE = json.loads(f.read())
    except:
        pass
    return KEY_STORAGE


def _save_storage():
    try:
        with open(STORAGE_FILE, 'w') as f:
            f.write(json.dumps(KEY_STORAGE))
    except:
        pass


def _transform_red(value):
    """Red Door (c30): return original value as-is."""
    return value


def _transform_green(value):
    """Green Door (c31): return original value as-is."""
    return value


def _transform_grey(value):
    """Grey Door (c32): first 2 chars + last 2 chars of stored value.
    Example: 'AWSisAwesome' -> 'AWme'
    """
    if len(value) <= 4:
        return value
    return value[:2] + value[-2:]


def _transform_yellow(value):
    """Yellow Door (c33): 5th char + 7th char of stored value (1-indexed).
    Example: 'sunshine' -> 'hn' (s=1, u=2, n=3, s=4, h=5, i=6, n=7, e=8)
    """
    result = ""
    if len(value) >= 5:
        result += value[4]  # 5th char (1-indexed = index 4)
    if len(value) >= 7:
        result += value[6]  # 7th char (1-indexed = index 6)
    return result


# Map color names to their transformation functions
DOOR_TRANSFORMS = {
    "red": _transform_red,
    "green": _transform_green,
    "grey": _transform_grey,
    "gray": _transform_grey,  # handle alternate spelling
    "yellow": _transform_yellow,
}

# All recognized key colors
KEY_COLORS = ["red", "green", "grey", "gray", "yellow"]


def _parse_input(event):
    """Extract text input from any event format."""
    if "parameters" in event:
        for p in event.get("parameters", []):
            name = p.get("name", "")
            value = p.get("value", "")
            if name in ("text", "input", "question", "message"):
                return value
            if value and len(str(value)) > 3:
                return str(value)

    try:
        props = event.get("requestBody", {}).get("content", {})
        json_props = props.get("application/json", {}).get("properties", [])
        for p in (json_props or []):
            if isinstance(p, dict):
                val = p.get("value", "")
                if val:
                    return str(val)
    except:
        pass

    if "body" in event:
        body = event["body"]
        if isinstance(body, str):
            try:
                parsed = json.loads(body)
                if isinstance(parsed, dict):
                    for key in ("text", "input", "question", "message"):
                        if key in parsed:
                            return str(parsed[key])
                    for v in parsed.values():
                        if isinstance(v, str) and len(v) > 3:
                            return v
                return body
            except:
                return body
        elif isinstance(body, dict):
            for key in ("text", "input", "question", "message"):
                if key in body:
                    return str(body[key])

    for key in ("text", "input", "question", "message"):
        if key in event:
            return str(event[key])

    return str(event)


def lambda_handler(event, context):
    global KEY_STORAGE

    _load_storage()

    text = _parse_input(event)

    if not text:
        return {"statusCode": 200, "body": json.dumps({"answer": "Thanks"})}

    text_str = str(text)

    # Debug: log what we received and current storage state
    print(f"INPUT: {text_str[:200]}")
    print(f"STORAGE: {json.dumps(KEY_STORAGE)}")
    print(f"VALUE_MAP: {json.dumps(VALUE_TO_COLOR)}")

    # STORE: "[Color] Key X is: [value]"
    # Universal pattern for any color key
    store_match = re.search(
        r'(Red|Green|Grey|Gray|Yellow)\s*[Kk]ey\s*(\d+)\s*is[:\s]+(.+)',
        text_str, re.IGNORECASE
    )
    if store_match:
        color = store_match.group(1).lower()
        if color == "gray":
            color = "grey"
        key_num = store_match.group(2)
        key_value = store_match.group(3).strip()
        storage_key = f"{color}_{key_num}"
        KEY_STORAGE[storage_key] = key_value
        _save_storage()
        VALUE_TO_COLOR[key_value] = color
        return {"statusCode": 200, "body": json.dumps({"answer": "Thanks"})}

    # RETRIEVE/DOOR: "What is [color] key/code X?"
    retrieve_match = re.search(
        r'[Ww]hat\s+is\s+(Red|Green|Grey|Gray|Yellow)\s*(?:[Kk]ey|[Cc]ode)\s*(\d+)',
        text_str, re.IGNORECASE
    )
    if retrieve_match:
        color = retrieve_match.group(1).lower()
        if color == "gray":
            color = "grey"
        key_num = retrieve_match.group(2)
        storage_key = f"{color}_{key_num}"
        if storage_key in KEY_STORAGE:
            value = KEY_STORAGE[storage_key]
            # Apply the door transformation for this color
            transform_fn = DOOR_TRANSFORMS.get(color, _transform_red)
            answer = transform_fn(value)
            return {"statusCode": 200, "body": json.dumps({"answer": answer})}
        return {"statusCode": 200, "body": json.dumps({"answer": "unknown"})}

    # FALLBACK: Generic key store detection
    if re.search(r'[Kk]ey.*is[:\s]', text_str):
        # Try to detect color from text
        color = "generic"
        for c in KEY_COLORS:
            if c in text_str.lower():
                color = c if c != "gray" else "grey"
                break
        words = text_str.split()
        last_word = words[-1].strip().rstrip('.!?')
        KEY_STORAGE[f"{color}_1"] = last_word
        _save_storage()
        VALUE_TO_COLOR[last_word] = color
        return {"statusCode": 200, "body": json.dumps({"answer": "Thanks"})}

    # FALLBACK: Generic key/code retrieve
    if re.search(r'[Ww]hat\s+is.*(?:[Kk]ey|[Cc]ode)', text_str):
        # Detect color
        color = None
        for c in KEY_COLORS:
            if c in text_str.lower():
                color = c if c != "gray" else "grey"
                break
        if color:
            for k, v in KEY_STORAGE.items():
                if color in k:
                    transform_fn = DOOR_TRANSFORMS.get(color, _transform_red)
                    return {"statusCode": 200, "body": json.dumps({"answer": transform_fn(v)})}
        # Try any stored key
        if "generic_1" in KEY_STORAGE:
            return {"statusCode": 200, "body": json.dumps({"answer": KEY_STORAGE["generic_1"]})}

    # FALLBACK: If text matches a stored key VALUE, apply its transform
    # Check KEY_STORAGE first
    for k, v in KEY_STORAGE.items():
        if v == text_str or text_str == v:
            color = k.split('_')[0]
            transform_fn = DOOR_TRANSFORMS.get(color, _transform_red)
            answer = transform_fn(v)
            return {"statusCode": 200, "body": json.dumps({"answer": answer})}

    # Check VALUE_TO_COLOR (survives if /tmp was wiped but Lambda is warm)
    if text_str in VALUE_TO_COLOR:
        color = VALUE_TO_COLOR[text_str]
        transform_fn = DOOR_TRANSFORMS.get(color, _transform_red)
        answer = transform_fn(text_str)
        return {"statusCode": 200, "body": json.dumps({"answer": answer})}

    # Partial match: check if text_str contains any stored value
    for k, v in KEY_STORAGE.items():
        if v in text_str:
            color = k.split('_')[0]
            transform_fn = DOOR_TRANSFORMS.get(color, _transform_red)
            answer = transform_fn(v)
            return {"statusCode": 200, "body": json.dumps({"answer": answer})}

    for val, color in VALUE_TO_COLOR.items():
        if val in text_str:
            transform_fn = DOOR_TRANSFORMS.get(color, _transform_red)
            answer = transform_fn(val)
            return {"statusCode": 200, "body": json.dumps({"answer": answer})}

    # Default
    return {"statusCode": 200, "body": json.dumps({"answer": "unknown"})}
