"""
AWS Lambda - Red Key/Door tool for Bedrock Agent Game v2.

Uses /tmp file storage (persists within same Lambda warm instance).
Also uses a global variable as primary storage.

Two modes:
1. STORE: Input contains "Red Key" and "is:" → stores value, returns "Thanks"
2. RETRIEVE: Input contains "what is red key" → returns stored value reversed
"""

import json
import re
import os

# Global storage (persists across warm invocations)
KEY_STORAGE = {}

# Also use /tmp as backup
STORAGE_FILE = "/tmp/red_keys.json"


def _load_storage():
    """Load from /tmp file as backup."""
    global KEY_STORAGE
    try:
        if os.path.exists(STORAGE_FILE):
            with open(STORAGE_FILE, 'r') as f:
                KEY_STORAGE = json.loads(f.read())
    except:
        pass
    return KEY_STORAGE


def _save_storage():
    """Save to /tmp file as backup."""
    try:
        with open(STORAGE_FILE, 'w') as f:
            f.write(json.dumps(KEY_STORAGE))
    except:
        pass


def _parse_input(event):
    """Extract text input from any event format."""
    # Try parameters list format
    if "parameters" in event:
        for p in event.get("parameters", []):
            name = p.get("name", "")
            value = p.get("value", "")
            if name in ("text", "input", "question", "message"):
                return value
            if value:
                return value

    # Try requestBody format
    try:
        props = event.get("requestBody", {}).get("content", {}).get("application/json", {}).get("properties", [])
        for p in (props or []):
            if isinstance(p, dict):
                val = p.get("value", "")
                if val:
                    return val
    except:
        pass

    # Try body format
    if "body" in event:
        body = event["body"]
        if isinstance(body, str):
            try:
                parsed = json.loads(body)
                if isinstance(parsed, dict):
                    for key in ("text", "input", "question", "message"):
                        if key in parsed:
                            return str(parsed[key])
                    # Return first string value
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

    # Try direct keys
    for key in ("text", "input", "question", "message"):
        if key in event:
            return str(event[key])

    # Last resort: convert entire event to string
    return str(event)


def lambda_handler(event, context):
    global KEY_STORAGE

    # Load any previously stored keys
    _load_storage()

    text = _parse_input(event)

    if not text:
        return {"statusCode": 200, "body": json.dumps({"answer": "Thanks"})}

    text_str = str(text)

    # MODE 1: STORE - "Red Key X is: [word]"
    # Match patterns like "Red Key 1 is: open" or "Red Key 2 is: blue"
    store_match = re.search(r'[Rr]ed\s*[Kk]ey\s*(\d+)\s*is[:\s]+(\w+)', text_str)
    if store_match:
        key_num = store_match.group(1)
        key_value = store_match.group(2).strip().lower()
        KEY_STORAGE[key_num] = key_value
        _save_storage()
        return {"statusCode": 200, "body": json.dumps({"answer": "Thanks"})}

    # MODE 2: RETRIEVE - "What is red key X?"
    # Match patterns like "What is red key 1?" or "what is red key 2"
    retrieve_match = re.search(r'[Ww]hat\s+is\s+[Rr]ed\s*[Kk]ey\s*(\d+)', text_str)
    if retrieve_match:
        key_num = retrieve_match.group(1)
        if key_num in KEY_STORAGE:
            value = KEY_STORAGE[key_num]
            reversed_value = value[::-1]
            return {"statusCode": 200, "body": json.dumps({"answer": reversed_value})}
        else:
            # Key not found - try to reverse any word that looks like it could be the key
            # Search for "open" or similar in the text
            return {"statusCode": 200, "body": json.dumps({"answer": "unknown", "error": "key not found in storage"})}

    # MODE 3: If text contains a key-like pattern but doesn't match above
    # Try to detect if this is a store or retrieve
    if "red key" in text_str.lower() and "is:" in text_str.lower():
        # Likely a store command
        words = text_str.split()
        last_word = words[-1].strip().lower().rstrip('.')
        KEY_STORAGE["1"] = last_word
        _save_storage()
        return {"statusCode": 200, "body": json.dumps({"answer": "Thanks"})}

    if "what" in text_str.lower() and "red key" in text_str.lower():
        # Likely a retrieve command
        if "1" in KEY_STORAGE:
            value = KEY_STORAGE["1"]
            reversed_value = value[::-1]
            return {"statusCode": 200, "body": json.dumps({"answer": reversed_value})}

    # Default: return Thanks (safe fallback for key)
    return {"statusCode": 200, "body": json.dumps({"answer": "Thanks"})}
