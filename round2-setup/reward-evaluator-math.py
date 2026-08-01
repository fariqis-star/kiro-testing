import json
import re
import boto3
from typing import Dict, Any, Optional

lambda_client = boto3.client('lambda')

TOOL_NAME = "Codeexecution"


def extract_tool_call(response: str) -> Optional[Dict[str, Any]]:
    if not response:
        return None

    # 1. Qwen native: <tool_call>...</tool_call>
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

    # 2. Fallback: raw JSON
    json_pattern = r'\{[^{}]*"(?:name|tool)"[^{}]*\}'
    match = re.search(json_pattern, response, re.DOTALL)
    if match:
        try:
            parsed = json.loads(match.group(0))
            return {
                'tool': parsed.get('name', parsed.get('tool', '')),
                'parameters': parsed.get('arguments', parsed.get('parameters', {})),
            }
        except json.JSONDecodeError:
            pass

    return None


def invoke_lambda(function_name: str, payload: dict) -> dict:
    try:
        response = lambda_client.invoke(
            FunctionName=function_name,
            InvocationType='RequestResponse',
            Payload=json.dumps(payload)
        )
        return json.loads(response['Payload'].read().decode('utf-8'))
    except Exception as e:
        return {"error": str(e)}


def reward_function(sample: Dict[str, Any], index: int) -> Dict[str, Any]:
    messages = sample.get('messages', sample.get('prompt', []))

    response = ""
    for msg in messages:
        if msg.get('role') == 'assistant':
            content = msg.get('content', '')
            if isinstance(content, list):
                content = ' '.join(str(b.get('text', b)) for b in content)
            if isinstance(content, str):
                response = content

    # Parse ground truth
    ground_truth_str = sample.get('reward_model', {}).get('ground_truth', '')
    ground_truth = {}
    if ground_truth_str:
        try:
            ground_truth = json.loads(ground_truth_str) if isinstance(ground_truth_str, str) else ground_truth_str
        except json.JSONDecodeError:
            ground_truth = {}

    expected_output = ground_truth.get('output', {})
    expected_answer = ""
    if expected_output:
        try:
            body = json.loads(expected_output.get('body', '{}'))
            expected_answer = body.get('output', '').strip()
        except:
            pass

    # Extract tool call from model response
    predicted = extract_tool_call(response)

    tool_score = 0.0
    code_score = 0.0
    lambda_score = 0.0
    answer_score = 0.0

    if not predicted:
        aggregate_reward = 0.0
    else:
        tool_name = predicted.get('tool', '').lower()
        if tool_name == TOOL_NAME.lower():
            tool_score = 1.0

        pred_params = predicted.get('parameters', {})
        code = pred_params.get('code', '')

        if code and tool_score > 0:
            # Check if code contains relevant math operations
            if 'factorial' in code or 'math.factorial' in code or 'fast_fib' in code or 'pow(' in code:
                code_score = 0.5

            # Actually invoke Lambda to verify
            try:
                lambda_output = invoke_lambda(TOOL_NAME, {"code": code})
                if lambda_output and 'body' in lambda_output:
                    body = json.loads(lambda_output['body']) if isinstance(lambda_output['body'], str) else lambda_output['body']
                    actual_output = body.get('output', '').strip()

                    if actual_output and actual_output == expected_answer:
                        answer_score = 1.0
                        lambda_score = 1.0
                    elif actual_output:
                        lambda_score = 0.5  # Lambda ran but wrong answer
            except:
                pass

        aggregate_reward = (
            tool_score * 0.20 +
            code_score * 0.20 +
            lambda_score * 0.20 +
            answer_score * 0.40
        )

    aggregate_reward = max(0.0, min(1.0, aggregate_reward))

    metrics = [
        {'name': 'correct_tool', 'value': float(tool_score), 'type': 'Reward'},
        {'name': 'valid_code', 'value': float(code_score), 'type': 'Reward'},
        {'name': 'lambda_success', 'value': float(lambda_score), 'type': 'Metric'},
        {'name': 'answer_match', 'value': float(answer_score), 'type': 'Metric'},
    ]

    sample_id = sample.get('id', sample.get('extra_info', {}).get('index', f'sample-{index:03d}'))

    return {
        'id': str(sample_id),
        'aggregate_reward_score': float(aggregate_reward),
        'metrics_list': metrics
    }


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    try:
        batch = event.get('input', event) if isinstance(event, dict) else event

        if 'batch' in event:
            batch = event.get('batch', [])
        elif 'body' in event:
            body = json.loads(event.get('body', '{}'))
            batch = body.get('batch', [])

        if not batch:
            return {"error": "Missing or empty batch"}

        results = []
        for i, sample in enumerate(batch):
            try:
                result = reward_function(sample, i)
                results.append(result)
            except Exception as e:
                sample_id = sample.get('id', sample.get('extra_info', {}).get('index', f'sample-{i:03d}'))
                results.append({
                    'id': str(sample_id),
                    'aggregate_reward_score': 0.0,
                    'metrics_list': [{'name': 'error', 'value': 1.0, 'type': 'Metric'}]
                })

        return {
            'statusCode': 200,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps(results)
        }

    except Exception as e:
        return {
            'statusCode': 400,
            'body': json.dumps({"error": str(e)})
        }
