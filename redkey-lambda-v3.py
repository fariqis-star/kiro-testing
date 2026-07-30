"""
AWS Lambda - Key/Door tool for Bedrock Agent Game v3 (Round 2).

Handles BOTH Red Key/Door AND Green Key/Door:
- Red Key (c40): store value, return "Thanks"
- Red Door (c30): return stored value reversed (spelled backward)
- Green Key (c41): store value, return "Thanks"
- Green Door (c31): return stored value as letter-to-number conversion (a=1, b=2... z=26)

Uses /tmp file + global variable for persistence within warm Lambda instance.
"""

import json
import re
import os

# Global storage
KEY_STORAGE = {}
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


def _letters_to_numbers(word):
    """Convert letters to their position numbers: a=1, b=2... z=26."""
    result = []
    for c in word.lower():
        if c.isalpha():
            result.append(str(ord(c) - ord('a') + 1))
    return ' '.join(result)


def _reverse_word(word):
    """Reverse the word and lowercase: MalaysiaBoleh → helobaisyalam."""
    return word[::-1].lower()


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
        props = event.get("requestBody", {}).get("content", {}).get("application/json", {}).get("properties", [])
        for p in (props or []):
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

    # STORE: "Red Key X is: [word]" or "Green Key X is: [word]"
    store_match = re.search(r'(?:Red|Green)\s*[Kk]ey\s*(\d+)\s*is[:\s]+(\w+)', text_str, re.IGNORECASE)
    if store_match:
        key_num = store_match.group(1)
        key_value = store_match.group(2).strip()
        # Detect color
        color = "red"
        if re.search(r'[Gg]reen', text_str):
            color = "green"
        storage_key = f"{color}_{key_num}"
        KEY_STORAGE[storage_key] = key_value
        _save_storage()
        return {"statusCode": 200, "body": json.dumps({"answer": "Thanks"})}

    # RETRIEVE RED DOOR: "What is red key X?"
    red_retrieve = re.search(r'[Ww]hat\s+is\s+[Rr]ed\s*[Kk]ey\s*(\d+)', text_str)
    if red_retrieve:
        key_num = red_retrieve.group(1)
        storage_key = f"red_{key_num}"
        if storage_key in KEY_STORAGE:
            value = KEY_STORAGE[storage_key]
            # Return ORIGINAL value (game accepts raw key value)
            return {"statusCode": 200, "body": json.dumps({"answer": value})}
        return {"statusCode": 200, "body": json.dumps({"answer": "unknown"})}

    # RETRIEVE GREEN DOOR: "What is green key X?"
    green_retrieve = re.search(r'[Ww]hat\s+is\s+[Gg]reen\s*[Kk]ey\s*(\d+)', text_str)
    if green_retrieve:
        key_num = green_retrieve.group(1)
        storage_key = f"green_{key_num}"
        if storage_key in KEY_STORAGE:
            value = KEY_STORAGE[storage_key]
            # Return ORIGINAL value (game accepts raw key value)
            return {"statusCode": 200, "body": json.dumps({"answer": value})}
        return {"statusCode": 200, "body": json.dumps({"answer": "unknown"})}

    # FALLBACK: Generic key detection
    if re.search(r'[Kk]ey.*is[:\s]', text_str):
        # Store it
        words = text_str.split()
        last_word = words[-1].strip().lower().rstrip('.!?')
        KEY_STORAGE["generic_1"] = last_word
        _save_storage()
        return {"statusCode": 200, "body": json.dumps({"answer": "Thanks"})}

    if re.search(r'[Ww]hat\s+is.*[Kk]ey', text_str):
        # Try to retrieve and reverse (default to red door behavior)
        if "green" in text_str.lower():
            for k, v in KEY_STORAGE.items():
                if "green" in k:
                    return {"statusCode": 200, "body": json.dumps({"answer": _letters_to_numbers(v)})}
        for k, v in KEY_STORAGE.items():
            if "red" in k:
                return {"statusCode": 200, "body": json.dumps({"answer": _reverse_word(v)})}
        if "generic_1" in KEY_STORAGE:
            return {"statusCode": 200, "body": json.dumps({"answer": _reverse_word(KEY_STORAGE["generic_1"])})}

    # Default
    return {"statusCode": 200, "body": json.dumps({"answer": "Thanks"})}
