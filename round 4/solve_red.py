"""Systematic search for the red door transform.

Ad-hoc guessing has burned 57 candidates. This instead enumerates a large space of
composable transforms, and keeps ONLY those that reproduce the one thing we know for
certain:

    green key "fghi"  ->  "6789"   scored +1000

Any rule that fails that test cannot be the door mechanic, so it is discarded without
costing a run. Every rule that passes it is then applied to "open" and checked against
the list of values already rejected. What survives is, by construction, consistent
with all available evidence and untested.

Pipeline shape:
    letters -> [letter ops] -> optional numeric conversion -> [number ops] -> render
"""

import itertools
import json

GREEN_KEY, GREEN_ANSWER = "fghi", "6789"
RED_KEY = "open"

# Everything already submitted to the door and rejected.
TESTED = {
    "nepo", "open", "lkvm", "mvkl", "bcra", "arcb", "6376", "6736",
    "1516514", "1451615", "4156151", "5161541", "1615145",
    "14 5 16 15", "14-5-16-15", "15 16 5 14", "15-16-5-14", "14,5,16,15",
    "5576", "4565", "6755", "5654",
    "12112213", "31221121", "13221112", "4423", "3212",
    "peon", "pone", "shut", "closed", "close", "locked",
    "NEPO", "Nepo", "neop", '"nepo"', "nepo.",
    "n e p o", "n-e-p-o",
    "open is: 1 Key Red", "open is 1 Key Red", "1 Key Red",
    "nepo :si 1 yeK deR", "4321",
    "6789", "9876", "ihgf", "Thanks", "sknahT", "2", "1", "30", "c30",
    "Red key 1 is nepo", "red nepo",
}


# ---------------------------------------------------------------- letter ops
def op_identity(s):
    return s


def op_reverse(s):
    return s[::-1]


def op_atbash(s):
    return "".join(chr(219 - ord(c)) if c.isalpha() else c for c in s)


def op_swaphalves(s):
    h = len(s) // 2
    return s[h:] + s[:h]


def make_rot(k):
    def f(s):
        return "".join(chr((ord(c) - 97 + k) % 26 + 97) if c.isalpha() else c
                       for c in s)
    f.__name__ = f"rot{k}"
    return f


LETTER_OPS = [op_identity, op_reverse, op_atbash, op_swaphalves]
LETTER_OPS += [make_rot(k) for k in range(1, 26)]


# ------------------------------------------------------- numeric conversions
def conv_a1(s):
    return [ord(c) - 96 for c in s if c.isalpha()]


def conv_z1(s):
    return [27 - (ord(c) - 96) for c in s if c.isalpha()]


def conv_a0(s):
    return [ord(c) - 97 for c in s if c.isalpha()]


_T9 = {}
for _d, _l in (("2", "abc"), ("3", "def"), ("4", "ghi"), ("5", "jkl"),
               ("6", "mno"), ("7", "pqrs"), ("8", "tuv"), ("9", "wxyz")):
    for _c in _l:
        _T9[_c] = int(_d)


def conv_t9(s):
    return [_T9[c] for c in s if c in _T9]


CONVERSIONS = [("a1", conv_a1), ("z1", conv_z1), ("a0", conv_a0), ("t9", conv_t9)]


# ---------------------------------------------------------------- number ops
def n_identity(ns):
    return ns


def n_reverse(ns):
    return ns[::-1]


def n_digitalroot(ns):
    out = []
    for n in ns:
        while n > 9:
            n = sum(int(d) for d in str(n))
        out.append(n)
    return out


def n_mod10(ns):
    return [n % 10 for n in ns]


def n_revdigits(ns):
    return [int(str(n)[::-1]) for n in ns]


def n_sortasc(ns):
    return sorted(ns)


def n_sortdesc(ns):
    return sorted(ns, reverse=True)


NUMBER_OPS = [n_identity, n_reverse, n_digitalroot, n_mod10, n_revdigits,
              n_sortasc, n_sortdesc]


# ------------------------------------------------------------------- renders
RENDERS = [
    ("concat", lambda ns: "".join(str(n) for n in ns)),
    ("concat_rev", lambda ns: "".join(str(n) for n in ns)[::-1]),
    ("space", lambda ns: " ".join(str(n) for n in ns)),
    ("dash", lambda ns: "-".join(str(n) for n in ns)),
    ("comma", lambda ns: ",".join(str(n) for n in ns)),
    ("pad2", lambda ns: "".join(f"{n:02d}" for n in ns)),
]


def search():
    hits = []

    # Branch 1: letters only, no numeric conversion.
    for n_ops in (1, 2):
        for combo in itertools.product(LETTER_OPS, repeat=n_ops):
            g = GREEN_KEY
            for f in combo:
                g = f(g)
            for label, cased in (("raw", lambda x: x), ("upper", str.upper),
                                 ("title", str.capitalize)):
                if cased(g) == GREEN_ANSWER:
                    r = RED_KEY
                    for f in combo:
                        r = f(r)
                    hits.append((" > ".join(f.__name__ for f in combo) + f" > {label}",
                                 cased(r)))

    # Branch 2: letter ops, then numeric conversion, then number ops, then render.
    for n_lops in (1, 2):
        for lcombo in itertools.product(LETTER_OPS, repeat=n_lops):
            for cname, conv in CONVERSIONS:
                for n_nops in (1, 2):
                    for ncombo in itertools.product(NUMBER_OPS, repeat=n_nops):
                        for rname, render in RENDERS:
                            g = GREEN_KEY
                            for f in lcombo:
                                g = f(g)
                            try:
                                gn = conv(g)
                                for f in ncombo:
                                    gn = f(gn)
                                gs = render(gn)
                            except Exception:
                                continue
                            if gs != GREEN_ANSWER:
                                continue
                            r = RED_KEY
                            for f in lcombo:
                                r = f(r)
                            try:
                                rn = conv(r)
                                for f in ncombo:
                                    rn = f(rn)
                                rs = render(rn)
                            except Exception:
                                continue
                            desc = (" > ".join(f.__name__ for f in lcombo)
                                    + f" > {cname} > "
                                    + " > ".join(f.__name__ for f in ncombo)
                                    + f" > {rname}")
                            hits.append((desc, rs))
    return hits


def main():
    hits = search()
    print(f"rules that reproduce fghi -> 6789 : {len(hits)}")

    by_out = {}
    for desc, out in hits:
        by_out.setdefault(out, []).append(desc)

    print(f"distinct outputs for 'open'       : {len(by_out)}")
    print()

    already = {o: d for o, d in by_out.items() if o in TESTED}
    fresh = {o: d for o, d in by_out.items() if o not in TESTED}

    print(f"already rejected                  : {len(already)}")
    for o in sorted(already):
        print(f"    {o!r:22} ({len(already[o])} rule(s))")
    print()
    print(f"*** SURVIVING, UNTESTED           : {len(fresh)} ***")
    for o in sorted(fresh, key=lambda x: (-len(fresh[x]), x)):
        print(f"    {o!r:22} supported by {len(fresh[o])} rule(s)")
        for d in fresh[o][:3]:
            print(f"        {d}")
    print()
    with open("solve_red_results.json", "w") as fh:
        json.dump({"untested": {k: v for k, v in fresh.items()},
                   "rejected": {k: v for k, v in already.items()}}, fh, indent=1)
    print("written to solve_red_results.json")


if __name__ == "__main__":
    main()
