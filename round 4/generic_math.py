"""Generic computational-question solver.

Last-resort fallback for the CodeExecution lambda. It runs only after every existing
handler has declined, so it cannot change any currently-working behaviour - it only
replaces the "Question not recognised" error with a real answer.

Design rules:
  * No hardcoded answers. Everything is parsed and computed from the question text.
  * No eval(). Expressions go through a restricted AST walker with a whitelist of
    node types and a whitelist of callables, so a hostile string cannot execute code.
  * Integer-exact wherever possible: results that are whole numbers print without a
    trailing .0, because grading is exact-string.
"""

from __future__ import annotations

import ast
import math
import re

# ---------------------------------------------------------------------------
# Safe expression evaluation
# ---------------------------------------------------------------------------

_ALLOWED_CALLS = {
    "factorial": math.factorial,
    "comb": math.comb,
    "perm": math.perm,
    "gcd": math.gcd,
    "lcm": getattr(math, "lcm", lambda a, b: a * b // math.gcd(a, b)),
    "isqrt": math.isqrt,
    "sqrt": math.sqrt,
    "abs": abs,
    "pow": pow,
}

_MAX_BITS = 2_000_000       # ~600k digits, well inside lambda memory
_MAX_FACT = 20_000
_MAX_NTH_PRIME = 200_000


class _Unsafe(ValueError):
    pass


def _bits(v) -> int:
    if isinstance(v, int):
        return v.bit_length()
    return 64


def _check(v):
    """Reject anything that has grown beyond a sane size."""
    if isinstance(v, int) and v.bit_length() > _MAX_BITS:
        raise _Unsafe("result too large")
    if isinstance(v, float) and not math.isfinite(v):
        raise _Unsafe("non-finite")
    return v


def _ev(node):
    """Explicit recursive evaluator. No eval, no compile, no builtins reachable."""
    if isinstance(node, ast.Expression):
        return _ev(node.body)

    if isinstance(node, ast.Constant):
        if isinstance(node.value, bool) or not isinstance(node.value, (int, float)):
            raise _Unsafe("only numeric literals")
        return node.value

    if isinstance(node, ast.UnaryOp):
        v = _ev(node.operand)
        if isinstance(node.op, ast.USub):
            return -v
        if isinstance(node.op, ast.UAdd):
            return v
        raise _Unsafe("unary op")

    if isinstance(node, ast.BinOp):
        l = _ev(node.left)
        r = _ev(node.right)
        op = node.op
        if isinstance(op, ast.Pow):
            # bound BEFORE computing, so 9**9**9 can never be materialised
            if not isinstance(r, (int, float)) or r > 100_000:
                raise _Unsafe("exponent too large")
            if r < 0:
                return _check(float(l) ** float(r))
            if _bits(l) * max(int(r), 1) > _MAX_BITS:
                raise _Unsafe("power too large")
            return _check(l ** int(r) if isinstance(l, int) and float(r).is_integer()
                          else float(l) ** float(r))
        if isinstance(op, ast.Add):
            return _check(l + r)
        if isinstance(op, ast.Sub):
            return _check(l - r)
        if isinstance(op, ast.Mult):
            if _bits(l) + _bits(r) > _MAX_BITS:
                raise _Unsafe("product too large")
            return _check(l * r)
        if isinstance(op, ast.Div):
            if r == 0:
                raise _Unsafe("division by zero")
            if isinstance(l, int) and isinstance(r, int) and l % r == 0:
                return l // r
            return _check(l / r)
        if isinstance(op, ast.FloorDiv):
            if r == 0:
                raise _Unsafe("division by zero")
            return _check(l // r)
        if isinstance(op, ast.Mod):
            if r == 0:
                raise _Unsafe("modulo by zero")
            return _check(l % r)
        raise _Unsafe("operator")

    if isinstance(node, ast.Call):
        if not isinstance(node.func, ast.Name) or node.func.id not in _ALLOWED_CALLS:
            raise _Unsafe("call not allowed")
        if node.keywords:
            raise _Unsafe("keywords not allowed")
        name = node.func.id
        args = [_ev(a) for a in node.args]
        if name == "factorial":
            if len(args) != 1 or args[0] < 0 or args[0] > _MAX_FACT:
                raise _Unsafe("factorial out of range")
            return _check(math.factorial(int(args[0])))
        if name in ("comb", "perm"):
            if len(args) != 2 or max(args) > 100_000:
                raise _Unsafe("comb out of range")
            return _check(_ALLOWED_CALLS[name](int(args[0]), int(args[1])))
        if name == "pow":
            if len(args) == 3:
                return pow(int(args[0]), int(args[1]), int(args[2]))
            if len(args) == 2 and args[1] > 100_000:
                raise _Unsafe("exponent too large")
            return _check(_ALLOWED_CALLS[name](*[int(a) for a in args]))
        return _check(_ALLOWED_CALLS[name](*args))

    raise _Unsafe("disallowed syntax: %s" % type(node).__name__)


def _safe_eval(expr: str):
    """Parse then walk with the bounded evaluator above."""
    if len(expr) > 400:
        raise _Unsafe("expression too long")
    return _ev(ast.parse(expr, mode="eval"))


def _fmt(v) -> str:
    """Exact-string friendly formatting."""
    if isinstance(v, bool):
        return "Yes" if v else "No"
    if isinstance(v, int):
        return str(v)
    if isinstance(v, float):
        if math.isfinite(v) and abs(v - round(v)) < 1e-9:
            return str(int(round(v)))
        return repr(round(v, 10))
    return str(v)


# ---------------------------------------------------------------------------
# Text normalisation
# ---------------------------------------------------------------------------

_WORD_OPS = [
    (r"\bto the power of\b", "**"),
    (r"\braised to the power of\b", "**"),
    (r"\braised to\b", "**"),
    (r"\bmultiplied by\b", "*"),
    (r"\btimes\b", "*"),
    (r"\bdivided by\b", "/"),
    (r"\bover\b", "/"),
    (r"\bplus\b", "+"),
    (r"\bminus\b", "-"),
    (r"\bmodulo\b", "%"),
    (r"\bmodulus\b", "%"),
    (r"\bmod\b", "%"),
]


def _normalise(text: str) -> str:
    s = text.strip()
    s = s.replace("\u2212", "-").replace("\u00d7", "*").replace("\u00f7", "/")
    # 1,000,000,007 -> 1000000007  (digit groups only, so dates/lists survive)
    s = re.sub(r"(?<=\d),(?=\d{3}\b)", "", s)
    low = s.lower()
    for pat, rep in _WORD_OPS:
        low = re.sub(pat, rep, low)
    # 1e9+7 -> 10**9+7 so the result stays an exact integer
    def _sci(mant, exp, add=0):
        e = int(exp)
        if e > 40:                      # keep literals sane
            raise ValueError("exponent too large")
        return str(int(mant) * 10 ** e + int(add))
    # "1e9+7" -> 1000000007 as ONE literal. Without this, "a % 1e9+7" would parse as
    # (a % 1e9) + 7, because % binds tighter than +.
    try:
        low = re.sub(r"\b(\d+)e(\d+)\s*\+\s*(\d+)\b",
                     lambda m: _sci(m.group(1), m.group(2), m.group(3)), low)
        low = re.sub(r"\b(\d+)e(\d+)\b",
                     lambda m: _sci(m.group(1), m.group(2)), low)
    except ValueError:
        pass
    # caret is exponentiation in maths prose, not XOR
    low = low.replace("^", "**")
    # 100! -> factorial(100)
    low = re.sub(r"(\d+)\s*!", r"factorial(\1)", low)
    return low


def _nth_prime(n: int) -> int:
    if n < 1 or n > _MAX_NTH_PRIME:
        raise ValueError("n out of range")
    count, cand = 0, 1
    while count < n:
        cand += 1
        if _is_prime(cand):
            count += 1
    return cand


def _is_prime(n: int) -> bool:
    if n < 2:
        return False
    if n < 4:
        return True
    if n % 2 == 0:
        return False
    f = 3
    while f * f <= n:
        if n % f == 0:
            return False
        f += 2
    return True


# ---------------------------------------------------------------------------
# Named question shapes, tried before the raw-expression fallback
# ---------------------------------------------------------------------------

def _named_forms(low: str):
    m = re.search(r"is\s+(\d+)\s+(?:a\s+)?prime", low)
    if m:
        return _is_prime(int(m.group(1)))

    m = re.search(r"(\d+)\s*(?:th|st|nd|rd)?\s*prime", low)
    if m and "sum" not in low:
        return _nth_prime(int(m.group(1)))

    m = re.search(r"sum of (?:the )?primes? (?:below|under|less than) (\d+)", low)
    if m:
        n = int(m.group(1))
        return sum(p for p in range(2, n) if _is_prime(p))

    m = re.search(r"(\d+)\s*choose\s*(\d+)", low)
    if m:
        return math.comb(int(m.group(1)), int(m.group(2)))

    m = re.search(r"sum of (?:the )?first (\d+)(?: positive)? (?:integers|numbers|whole numbers)", low)
    if m:
        n = int(m.group(1))
        return n * (n + 1) // 2

    m = re.search(r"square root of (\d+)", low)
    if m:
        n = int(m.group(1))
        r = math.isqrt(n)
        return r if r * r == n else math.sqrt(n)

    m = re.search(r"how many digits (?:are )?in (.+?)[\?\.]*$", low)
    if m:
        try:
            return len(str(int(_safe_eval(m.group(1).strip()))))
        except Exception:
            return None

    m = re.search(r"(?:number of divisors|how many divisors) of (\d+)", low)
    if m:
        n = int(m.group(1))
        return sum(2 if d * d != n else 1
                   for d in range(1, math.isqrt(n) + 1) if n % d == 0)
    return None


_TOKEN_RE = re.compile(
    r"(?:factorial|comb|perm|gcd|lcm|isqrt|sqrt|pow|abs)\s*\(|"   # call opener
    r"\d+\.\d+|\d+|"                                            # numbers
    r"\*\*|[+\-*/%(),]"                                          # operators
)


def _balanced(toks) -> bool:
    depth = 0
    for t in toks:
        if t.endswith("("):
            depth += 1
        elif t == ")":
            depth -= 1
            if depth < 0:
                return False
    return depth == 0


def _expression_fallback(low: str):
    """Find the LONGEST balanced arithmetic sub-expression in the prose and evaluate it.

    Prose words are dropped by the tokeniser, so "what is 50! mod 1e9+7" normalises to
    the token run  factorial( 50 ) % ( 1 * 10 ** 9 ) + 7  and evaluates whole. Every
    window is bounded by _safe_eval, so an unparseable or oversized one just fails and
    the search continues.
    """
    toks = _TOKEN_RE.findall(low)
    if not toks:
        return None
    if len(toks) > 60:
        toks = toks[:60]

    best = None
    best_len = 0
    unsafe_seen = False
    n = len(toks)
    for i in range(n):
        for j in range(n, i, -1):
            span = toks[i:j]
            if len(span) <= best_len:
                break            # no longer window available from this start
            if not _balanced(span):
                continue
            # require real computation, not a bare number
            if not any(t == "**" or t in ("+", "-", "*", "/", "%")
                       or (t.endswith("(") and len(t) > 1) for t in span):
                continue
            if not any(ch.isdigit() for ch in "".join(span)):
                continue
            try:
                v = _safe_eval("".join(span))
            except _Unsafe:
                unsafe_seen = True
                continue
            except Exception:
                continue
            if v is not None:
                best, best_len = v, len(span)
                break
    if unsafe_seen:
        return None
    return best


def solve(text: str):
    """Return a formatted answer string, or None if nothing could be computed."""
    if not text or not text.strip():
        return None
    low = _normalise(text)
    try:
        v = _named_forms(low)
    except Exception:
        v = None
    if v is None:
        try:
            v = _expression_fallback(low)
        except Exception:
            v = None
    if v is None:
        return None
    try:
        return _fmt(v)
    except Exception:
        return None
