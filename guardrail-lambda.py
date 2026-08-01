"""
AWS Lambda - Guardrail Check tool for Bedrock Agent Game.

Checks if a question should be blocked (Violent Violet challenge).
More reliable than Bedrock guardrail (no RNG/race conditions).

Blocks: violence, medical, illegal, hate, misconduct, 
        edible flowers, transplanting, weeds, botany.

Input: {"text": "question text"}
Output: {"blocked": true/false, "answer": "Sorry, the model cannot answer this question."}
"""

import json
import re


# Keywords that trigger blocking
BLOCK_PATTERNS = [
    # Medical
    r'prescri\w+', r'medication', r'dosage', r'dose', r'drug', r'medicine',
    r'diagnos\w+', r'symptom', r'treatment', r'doctor.*prescri', r'mg\b',
    r'blood pressure', r'lisinopril', r'losartan', r'alternative.*medication',
    
    # Violence
    r'kill', r'murder', r'weapon', r'bomb', r'attack', r'assault',
    r'shoot', r'stab', r'poison', r'harm', r'hurt.*people', r'violence',
    r'self.?harm', r'suicide',
    
    # Illegal
    r'illegal', r'hack', r'exploit', r'steal', r'fraud', r'drug.*mak',
    r'break.*law', r'crime', r'smuggl',
    
    # Hate
    r'hate', r'discriminat', r'racist', r'slur', r'supremac',
    
    # Misconduct
    r'misconduct', r'cheat', r'plagiari',
    
    # Botany (Violet Violet specific!)
    r'edible.*flower', r'flower.*edible', r'edible.*plant',
    r'transplant', r'weed\b', r'weeds', r'garden.*illegal',
    r'illegal.*plant', r'plant.*illegal',
    r'herb.*illegal', r'grow.*illegal',
]

DENIAL = "Sorry, the model cannot answer this question."


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
    text = _parse_input(event)

    if not text:
        return {"statusCode": 200, "body": json.dumps({"blocked": False, "answer": ""})}

    text_lower = text.lower()

    # Check all block patterns
    for pattern in BLOCK_PATTERNS:
        if re.search(pattern, text_lower):
            return {"statusCode": 200, "body": json.dumps({"blocked": True, "answer": DENIAL})}

    # Not blocked
    return {"statusCode": 200, "body": json.dumps({"blocked": False, "answer": ""})}
