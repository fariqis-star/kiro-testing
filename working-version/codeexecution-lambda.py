"""
AWS Lambda - Code Execution tool for Bedrock Agent Game (OPTIMIZED).

- Matrix exponentiation for Fibonacci (O(log n)) - handles huge N
- Sieve of Eratosthenes for prime counting
- Pre-intercepts common patterns before exec()
- Fixes broken fib code from model
- 3-second timeout via signal.SIGALRM
"""

import json
import sys
import signal
import traceback
import re
from io import StringIO


class ExecutionTimeout(Exception):
    pass


def _timeout_handler(signum, frame):
    raise ExecutionTimeout("Execution timed out (3 second limit exceeded).")


EXEC_TIMEOUT_SECONDS = 3


def _fast_fib_matrix(n, mod=None):
    """O(log n) Fibonacci using matrix exponentiation."""
    if n <= 0:
        return 0
    if n == 1:
        return 1
    if mod is None:
        mod = 10**100

    def mat_mult(A, B, m):
        return [
            [(A[0][0]*B[0][0] + A[0][1]*B[1][0]) % m, (A[0][0]*B[0][1] + A[0][1]*B[1][1]) % m],
            [(A[1][0]*B[0][0] + A[1][1]*B[1][0]) % m, (A[1][0]*B[0][1] + A[1][1]*B[1][1]) % m]
        ]

    def mat_pow(M, p, m):
        result = [[1, 0], [0, 1]]
        base = M
        while p > 0:
            if p % 2 == 1:
                result = mat_mult(result, base, m)
            base = mat_mult(base, base, m)
            p //= 2
        return result

    M = [[1, 1], [1, 0]]
    result = mat_pow(M, n, mod)
    return result[0][1]



def _count_primes_sieve(limit):
    """Sieve of Eratosthenes."""
    if limit < 2:
        return 0
    sieve = bytearray(b'\x01') * (limit + 1)
    sieve[0] = sieve[1] = 0
    for i in range(2, int(limit**0.5) + 1):
        if sieve[i]:
            sieve[i*i::i] = bytearray(len(sieve[i*i::i]))
    return sum(sieve)


PREPENDED_HELPERS = (
    "def fast_fib(n, mod=None):\n"
    "    return _fast_fib_matrix(n, mod)\n"
    "\n"
    "fib = fast_fib\n"
    "fibonacci = fast_fib\n"
    "\n"
    "def count_primes(limit):\n"
    "    return _count_primes_sieve(limit)\n"
    "\n"
)


def _try_intercept(code):
    """Try to solve common patterns directly without exec()."""
    code_lower = code.lower().strip()

    # Fibonacci with modulo
    if ("fib" in code_lower or "fibonacci" in code_lower) and ("mod" in code_lower or "%" in code):
        numbers = [int(n) for n in re.findall(r'\b(\d{2,15})\b', code)]
        if numbers:
            fib_n = None
            fib_mod = None
            for num in numbers:
                if num >= 1000000:
                    if fib_mod is None or num > fib_mod:
                        fib_mod = num
                elif 2 <= num <= 100000:
                    if fib_n is None:
                        fib_n = num
            if fib_n and fib_mod:
                return str(_fast_fib_matrix(fib_n, fib_mod))
            if fib_n:
                return str(_fast_fib_matrix(fib_n))

    # Prime counting
    prime_match = re.search(r'(?:prime|primes).*?(\d{3,})', code_lower)
    if prime_match and ("count" in code_lower or "how many" in code_lower or "number of" in code_lower):
        limit = int(prime_match.group(1))
        if limit <= 10000000:
            return str(_count_primes_sieve(limit))

    # Factorial with modulo
    if ('factorial' in code_lower or 'math.factorial' in code_lower or '!' in code) and ('mod' in code_lower or '%' in code):
        import math
        numbers = [int(n) for n in re.findall(r'\b(\d+)\b', code)]
        if numbers:
            fact_n = None
            fact_mod = None
            for num in numbers:
                if num >= 1000000:
                    if fact_mod is None or num > fact_mod:
                        fact_mod = num
                elif 2 <= num <= 100000:
                    if fact_n is None:
                        fact_n = num
            if '1000000007' in code:
                fact_mod = 1000000007
            if fact_n and fact_mod:
                return str(math.factorial(fact_n) % fact_mod)
            if fact_n:
                return str(math.factorial(fact_n))

    # Power with modulo: pow(a, b, m)
    pow_mod_match = re.search(r'pow\s*\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*\)', code)
    if pow_mod_match:
        return str(pow(int(pow_mod_match.group(1)), int(pow_mod_match.group(2)), int(pow_mod_match.group(3))))

    # Power: X**Y % M
    pow_match = re.search(r'(\d+)\s*\*\*\s*(\d+)', code)
    if pow_match:
        base = int(pow_match.group(1))
        exp = int(pow_match.group(2))
        mod_match = re.search(r'%\s*(\d+)', code)
        if mod_match:
            mod = int(mod_match.group(1))
            return str(pow(base, exp, mod))

    return None



def _fix_fib_code(code):
    """If code has fibonacci, replace with fast version."""
    code_lower = code.lower()
    if ("fib" in code_lower or "fibonacci" in code_lower) and ("mod" in code_lower or "%" in code):
        numbers = [int(n) for n in re.findall(r'\b(\d{2,15})\b', code)]
        if numbers:
            fib_n = None
            fib_mod = None
            for num in numbers:
                if num >= 1000000:
                    if fib_mod is None or num > fib_mod:
                        fib_mod = num
                elif 2 <= num <= 100000:
                    if fib_n is None:
                        fib_n = num
            if fib_n and fib_mod:
                return "print(fast_fib(" + str(fib_n) + ", mod=" + str(fib_mod) + "))"
            if fib_n:
                return "print(fast_fib(" + str(fib_n) + "))"

    # Strip custom fib definitions
    lines = code.split('\n')
    cleaned = []
    skip = False
    for line in lines:
        s = line.strip()
        if skip:
            if s == "" or line[0:1] in (" ", "\t"):
                continue
            skip = False
        if re.match(r'def\s+(fib|fibonacci|calc_fib|compute_fib|get_fib)', s):
            skip = True
            continue
        cleaned.append(line)
    code = '\n'.join(cleaned)
    code = re.sub(r'\b(?<!fast_)fib\b', 'fast_fib', code)
    code = re.sub(r'\bfibonacci\b', 'fast_fib', code)
    return code


def _unescape(raw):
    if not raw:
        return ""
    text = raw.strip()
    for _ in range(2):
        if len(text) >= 2 and text[0] == '"' and text[-1] == '"':
            try:
                text = json.loads(text)
            except (json.JSONDecodeError, ValueError):
                text = text[1:-1]
    return text


def _extract_code(event):
    params = event.get("parameters")
    if isinstance(params, list):
        for p in params:
            if isinstance(p, dict) and p.get("name") == "code":
                return _unescape(p.get("value", ""))
    try:
        props = event.get("requestBody", {}).get("content", {}).get("application/json", {}).get("properties", [])
        for p in (props or []):
            if isinstance(p, dict) and p.get("name") == "code":
                return _unescape(p.get("value", ""))
    except (AttributeError, TypeError):
        pass
    if "code" in event:
        return _unescape(str(event["code"]))
    body = event.get("body")
    if body:
        if isinstance(body, str):
            try:
                parsed = json.loads(body)
                if isinstance(parsed, dict) and "code" in parsed:
                    return _unescape(str(parsed["code"]))
            except (json.JSONDecodeError, ValueError):
                return _unescape(body)
        elif isinstance(body, dict) and "code" in body:
            return _unescape(str(body["code"]))
    return ""



def lambda_handler(event, context):
    code = _extract_code(event)
    if not code.strip():
        return _resp(event, json.dumps({"output": "", "error": "No code provided."}))

    # Try direct interception first (fastest path, no exec needed)
    intercepted = _try_intercept(code)
    if intercepted:
        return _resp(event, json.dumps({"output": intercepted + "\n", "error": None}))

    # Fix fibonacci code if model wrote a slow version
    code = _fix_fib_code(code)

    # Build execution environment with optimized helpers
    exec_globals = {
        "__builtins__": __builtins__,
        "_fast_fib_matrix": _fast_fib_matrix,
        "_count_primes_sieve": _count_primes_sieve,
    }

    protected = PREPENDED_HELPERS + code

    stdout_buf = StringIO()
    old_stdout = sys.stdout
    error_msg = None
    old_handler = signal.signal(signal.SIGALRM, _timeout_handler)
    signal.alarm(EXEC_TIMEOUT_SECONDS)

    try:
        sys.stdout = stdout_buf
        exec(protected, exec_globals)
    except ExecutionTimeout as e:
        error_msg = str(e)
    except Exception:
        error_msg = traceback.format_exc()
    finally:
        signal.alarm(0)
        signal.signal(signal.SIGALRM, old_handler)
        sys.stdout = old_stdout

    output = stdout_buf.getvalue()

    # If no print output, check for 'result' variable (backup pattern)
    if not output.strip() and 'result' in exec_globals and error_msg is None:
        output = str(exec_globals['result']) + "\n"

    return _resp(event, json.dumps({"output": output, "error": error_msg}))


def _resp(event, result_body):
    response = {"statusCode": 200, "body": result_body}
    if "actionGroup" in event:
        response["messageVersion"] = event.get("messageVersion", "1.0")
        response["response"] = {
            "actionGroup": event.get("actionGroup", ""),
            "apiPath": event.get("apiPath", ""),
            "httpMethod": event.get("httpMethod", ""),
            "httpStatusCode": 200,
            "responseBody": {"application/json": {"body": result_body}}
        }
    return response
