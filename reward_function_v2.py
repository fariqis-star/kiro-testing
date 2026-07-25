import json
import re
from typing import Dict, Any, List, Optional


# =========================================================================================
# SECTION 1: Helper function - Extract tool calls from model output
# =========================================================================================
def extract_tool_call(response: str) -> Optional[Dict[str, Any]]:
    """
    Extract tool call from model's raw text output.
    Supports Qwen native <tool_call> tags and legacy [TOOL_CALL] tags.
    """
    if not response:
        return None

    # Qwen native: <tool_call>...</tool_call>
    match = re.search(r'<tool_call>\s*(.*?)\s*</tool_call>', response, re.DOTALL)
    if match:
        try:
            parsed = json.loads(match.group(1).strip())
            name = parsed.get('name', '')
            arguments = parsed.get('arguments', {})
            if isinstance(arguments, str):
                try:
                    arguments = json.loads(arguments)
                except:
                    arguments = {}
            return {'tool': name, 'parameters': arguments}
        except json.JSONDecodeError:
            pass

    # Legacy: [TOOL_CALL]...[/TOOL_CALL]
    match = re.search(r'\[TOOL_CALL\]\s*(.*?)\s*\[/TOOL_CALL\]', response, re.DOTALL | re.IGNORECASE)
    if match:
        try:
            parsed = json.loads(match.group(1).strip())
            return {
                'tool': parsed.get('tool', parsed.get('name', '')),
                'parameters': parsed.get('parameters', parsed.get('arguments', {})),
            }
        except json.JSONDecodeError:
            pass

    return None


# =========================================================================================
# SECTION 2: Helper function - Compute brevity and preamble scores
# =========================================================================================
def compute_brevity_score(response_text: str) -> float:
    """
    Score response brevity. Shorter = better for AI League.
    Returns score between 0.0 and 1.0.
    """
    response_len = len(response_text)
    if response_len == 0:
        return 0.0
    elif response_len <= 10:
        return 1.0
    elif response_len <= 30:
        return 0.9
    elif response_len <= 80:
        return 0.7
    elif response_len <= 200:
        return 0.4
    elif response_len <= 500:
        return 0.2
    else:
        return 0.05


def compute_preamble_score(answer_text: str) -> float:
    """
    Penalize preamble/reasoning in answers.
    Returns 1.0 for no preamble, lower for more preamble.
    """
    preamble_patterns = [
        r'(?i)^(looking at|let me|i need to|this is a|based on|according to)',
        r'(?i)(the answer is|here\'s|explanation|reasoning)',
        r'(?i)(c5 type|c2 type|c4 type|task type|challenge type)',
        r'(?i)(let me analyze|let me examine|let me count)',
        r'\*\*',
        r'```',
    ]

    preamble_count = 0
    for pattern in preamble_patterns:
        if re.search(pattern, answer_text):
            preamble_count += 1

    if preamble_count == 0:
        return 1.0
    elif preamble_count == 1:
        return 0.6
    elif preamble_count == 2:
        return 0.3
    else:
        return 0.1


# =========================================================================================
# SECTION 3: Reward function
# =========================================================================================
def reward_function(sample: Dict[str, Any], index: int) -> Dict[str, Any]:
    """
    Multi-objective reward function for AI League agent.
    Scores on correctness, brevity, tool discipline, and no preamble.

    Args:
        sample: Dictionary containing prompt and reward_model ground truth
        index: Sample index in batch

    Returns:
        Dictionary with reward scores and metrics
    """
    # ========================================================================
    # SECTION 4: Parse input
    # ========================================================================
    messages = sample.get('messages', sample.get('prompt', []))

    # Get the assistant's response
    response = ""
    for msg in messages:
        if msg.get('role') == 'assistant':
            content = msg.get('content', '')
            if isinstance(content, list):
                content = ' '.join(str(b.get('text', b)) for b in content)
            if isinstance(content, str):
                response = content

    # Parse ground truth from reward_model
    ground_truth_str = ""
    if 'reward_model' in sample:
        ground_truth_str = sample['reward_model'].get('ground_truth', '')

    ground_truth = {}
    if ground_truth_str:
        if isinstance(ground_truth_str, dict):
            ground_truth = ground_truth_str
        elif isinstance(ground_truth_str, str):
            try:
                ground_truth = json.loads(ground_truth_str)
            except json.JSONDecodeError:
                ground_truth = {'expected_answer': ground_truth_str}
        else:
            ground_truth = {'expected_answer': str(ground_truth_str)}

    expected_answer = ground_truth.get('expected_answer', '')
    if not expected_answer and isinstance(ground_truth_str, str):
        expected_answer = ground_truth_str

    challenge_type = ground_truth.get('challenge_type', 'unknown')
    requires_tool = ground_truth.get('requires_tool', False)
    expected_tool = ground_truth.get('expected_tool', '')

    # ========================================================================
    # SECTION 5: Compute reward scores
    # ========================================================================
    correctness_score = 0.0
    brevity_score = 0.0
    tool_discipline_score = 0.0
    preamble_score = 0.0

    predicted_tool = extract_tool_call(response)
    response_text = response.strip()

    # Remove tool call tags to get the answer portion
    answer_text = re.sub(r'<tool_call>.*?</tool_call>', '', response, flags=re.DOTALL).strip()
    answer_text = re.sub(r'\[TOOL_CALL\].*?\[/TOOL_CALL\]', '', answer_text, flags=re.DOTALL | re.IGNORECASE).strip()

    # --- Correctness (0.0 - 1.0) ---
    if expected_answer:
        expected_lower = expected_answer.lower().strip()
        answer_lower = answer_text.lower().strip()

        if expected_lower == answer_lower:
            correctness_score = 1.0
        elif expected_lower in answer_lower:
            correctness_score = 0.8
        elif answer_lower in expected_lower and len(answer_lower) > 0:
            correctness_score = 0.7
        else:
            try:
                pred_num = float(re.sub(r'[,$]', '', answer_lower))
                exp_num = float(re.sub(r'[,$]', '', expected_lower))
                if pred_num == exp_num:
                    correctness_score = 1.0
            except (ValueError, TypeError):
                pass

    if requires_tool and predicted_tool:
        tool_name = predicted_tool.get('tool', '').lower()
        if expected_tool.lower() in tool_name or tool_name in expected_tool.lower():
            correctness_score = max(correctness_score, 0.5)

    # --- Brevity (0.0 - 1.0) ---
    brevity_score = compute_brevity_score(response_text)

    # --- Tool Discipline (0.0 - 1.0) ---
    if requires_tool:
        tool_discipline_score = 1.0 if predicted_tool else 0.3
    else:
        tool_discipline_score = 0.0 if predicted_tool else 1.0

    # --- Preamble Score (0.0 - 1.0) ---
    preamble_score = compute_preamble_score(answer_text)

    # --- Aggregate Reward ---
    if correctness_score == 0.0:
        aggregate_reward = 0.05 * brevity_score
    else:
        aggregate_reward = (
            correctness_score * 0.45 +
            brevity_score * 0.25 +
            tool_discipline_score * 0.15 +
            preamble_score * 0.15
        )

    aggregate_reward = max(0.0, min(1.0, aggregate_reward))

    # ========================================================================
    # SECTION 6: Form the metrics list
    # ========================================================================
    metrics = [
        {'name': 'correctness', 'value': float(correctness_score), 'type': 'Reward'},
        {'name': 'brevity', 'value': float(brevity_score), 'type': 'Reward'},
        {'name': 'tool_discipline', 'value': float(tool_discipline_score), 'type': 'Reward'},
        {'name': 'no_preamble', 'value': float(preamble_score), 'type': 'Reward'},
        {'name': 'response_length', 'value': float(len(response_text)), 'type': 'Metric'},
        {'name': 'used_tool', 'value': float(1.0 if predicted_tool else 0.0), 'type': 'Metric'},
    ]

    # ========================================================================
    # SECTION 7: Return output
    # ========================================================================
    sample_id = sample.get('id', sample.get('extra_info', {}).get('index', f'sample-{index:03d}'))

    return {
        'id': str(sample_id),
        'aggregate_reward_score': float(aggregate_reward),
        'metrics_list': metrics
    }


def lambda_handler(event: Dict[str, Any], context: Any) -> List[Dict[str, Any]]:
    """
    AWS Lambda Handler for reward function.
    Returns a list of score objects directly.
    """
    try:
        batch = event.get('input', event) if isinstance(event, dict) else event
        if 'batch' in event:
            batch = event.get('batch', [])
        elif 'body' in event:
            body = json.loads(event.get('body', '{}'))
            batch = body.get('batch', [])

        if not batch:
            return [{"id": "0", "aggregate_reward_score": 0.0}]

        results = []
        for i, sample in enumerate(batch):
            try:
                result = reward_function(sample, i)
                results.append(result)
            except Exception as e:
                results.append({
                    'id': str(i),
                    'aggregate_reward_score': 0.0,
                    'metrics_list': []
                })

        return results

    except Exception as e:
        return [{"id": "0", "aggregate_reward_score": 0.0}]
