"""Diff the current build against the 17,045 judge build.

Both builds score ~17,044 on the TEST map, but the old one scored 17,045 on the judge
and the current one scores 16,181. A test-map run cannot see the difference, so compare
them directly instead: same payloads into both, and report every disagreement.

Usage: put the four deployed files in known-good-17045/ then run this.

Local tooling. NOT deployed.
"""
import importlib.util
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
OLD = os.path.join(HERE, "known-good-17045")


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def call(mod, code):
    try:
        r = mod.lambda_handler({"body": json.dumps({"code": code})}, None)
        b = r.get("body") if isinstance(r, dict) else r
        try:
            return json.loads(b).get("output")
        except Exception:
            return b
    except Exception as e:
        return f"<{type(e).__name__}: {e}>"


missing = [f for f in ("codeexecution-lambda.py", "pathfinding-lambda.py")
           if not os.path.exists(os.path.join(OLD, f))]
if missing:
    print(f"waiting on: {', '.join(missing)} in known-good-17045/")
    sys.exit(0)

new_ce = load(os.path.join(HERE, "codeexecution-lambda.py"), "new_ce")
old_ce = load(os.path.join(OLD, "codeexecution-lambda.py"), "old_ce")

print("=" * 70)
print("FLAGS")
print("=" * 70)
flags = sorted({k for m in (new_ce, old_ce) for k, v in vars(m).items()
                if k.isupper() and isinstance(v, (str, int, bool, type(None)))
                and not k.startswith("_")})
for f in flags:
    a = getattr(old_ce, f, "<absent>")
    b = getattr(new_ce, f, "<absent>")
    if a != b:
        print(f"  DIFF  {f:24} 17045={a!r}  now={b!r}")
print()

print("=" * 70)
print("HANDLER OUTPUTS - same payload into both builds")
print("=" * 70)
payloads = [
    "red open", "red shut", "red sesame", "green fghi", "green abcd",
    "Red Key 1 is: shut", "Green Key 1 is: fghi",
    "100! mod 1e9+7", "What is 100! modulo 1,000,000,007?",
    "fib 500 mod 1e10", "500th fibonacci mod 1e10", "500th fibonacci mod 1e9+7",
    "fib 3000 last 10",
    "c4", "How many c4 challenges are on the map?", "how many c7 are on the map",
    "Patient ID P-9934, name Cynthia Park. Provider: Dr. Alan Foster. "
    "Insurance ID: INS-61803.",
    "find optimal path",
]
diffs = 0
for p in payloads:
    a, b = call(old_ce, p), call(new_ce, p)
    if a != b:
        diffs += 1
        print(f"  DIFF  {p[:58]!r}")
        print(f"        17045: {str(a)[:100]!r}")
        print(f"        now:   {str(b)[:100]!r}")
print(f"  ({diffs} disagreement(s) across {len(payloads)} payloads)\n")

print("=" * 70)
print("ROUTE")
print("=" * 70)
try:
    new_pf = load(os.path.join(HERE, "pathfinding-lambda.py"), "new_pf")
    old_pf = load(os.path.join(OLD, "pathfinding-lambda.py"), "old_pf")

    def route(m):
        b = json.loads(m.lambda_handler({}, None)["body"])
        p = b.get("path")
        return p if isinstance(p, list) else re.split(r'[,\s]+', str(p).strip("[]"))
    ra, rb = route(old_pf), route(new_pf)
    print(f"  17045: {len(ra)} moves     now: {len(rb)} moves")
    if ra != rb:
        for i, (x, y) in enumerate(zip(ra, rb)):
            if x != y:
                print(f"  first difference at move {i}: 17045={x!r} now={y!r}")
                break
    else:
        print("  routes are IDENTICAL")
except Exception as e:
    print(f"  could not compare: {e}")
print()

print("=" * 70)
print("PROMPT RULES")
print("=" * 70)
op = next((os.path.join(OLD, f) for f in ("supervisor-prompt.txt",
                                          "supervisor-prompt-min.txt")
           if os.path.exists(os.path.join(OLD, f))), None)
if not op:
    print("  no prompt in known-good-17045/ - add it to compare")
else:
    a = open(op).read()
    b = open(os.path.join(HERE, "supervisor-prompt-min.txt")).read()
    print(f"  17045 prompt: {len(a)} chars     now: {len(b)} chars")
    # Compare the RULES, not the prose: short uppercase directives and key phrases.
    def rules(t):
        out = set()
        for line in t.splitlines():
            s = line.strip()
            for kw in ("NEVER", "NO TOOL", "MUST", "ALWAYS", "DO NOT", "CALL NO TOOL",
                       "ONLY", "Never", "never"):
                if kw in s:
                    out.add(re.sub(r'\s+', ' ', s)[:90])
                    break
        return out
    ra_, rb_ = rules(a), rules(b)
    only_old = sorted(ra_ - rb_)
    only_new = sorted(rb_ - ra_)
    print(f"\n  --- IN THE 17045 PROMPT BUT NOT NOW ({len(only_old)}) "
          f"<-- suspects for the regression")
    for r in only_old:
        print(f"      {r}")
    print(f"\n  --- ADDED SINCE ({len(only_new)}) <-- suspects for breaking it")
    for r in only_new:
        print(f"      {r}")
