"""Red door search, v2 - models the two doors as ONE mechanic plus a MODIFIER.

v1 searched for rules that turn fghi into 6789 and applied them unchanged to open.
That is the wrong model. The two descriptions state DIFFERENT modifiers on what is
plainly the same underlying mechanic:

    green (c31):  "translate the code you receive by replacing letters with the
                   numbers that represent them IN ORDER"
    red   (c30):  "translate the code you receive by READING IT BACKWARDS"

So the correct procedure is:
    1. find BASE rules that satisfy green's control, fghi -> 6789
    2. for each, insert a "backwards" modifier at every stage it could apply
    3. apply to open, drop anything already rejected

v1 also over-weighted degenerate rules. This version excludes arbitrary constants
(rot-k), because an author writing "reading it backwards" does not mean "rotate by
12", and ranks what remains by how simply it can be stated in English.
"""

import itertools

GREEN_KEY, GREEN_ANSWER, RED_KEY = "fghi", "6789", "open"

TESTED = {
    "nepo", "open", "lkvm", "mvkl", "bcra", "arcb", "6376", "6736",
    "1516514", "1451615", "4156151", "5161541", "1615145",
    "14 5 16 15", "14-5-16-15", "15 16 5 14", "15-16-5-14", "14,5,16,15",
    "5576", "4565", "6755", "5654",
    "12112213", "31221121", "13221112", "4423", "3212",
    "peon", "pone", "shut", "closed", "close", "locked",
    "NEPO", "Nepo", "neop", '"nepo"', "nepo.", "n e p o", "n-e-p-o",
    "open is: 1 Key Red", "open is 1 Key Red", "1 Key Red",
    "nepo :si 1 yeK deR", "4321",
    "6789", "9876", "ihgf", "Thanks", "sknahT", "2", "1", "30", "c30",
    "Red key 1 is nepo", "red nepo",
}

CONV = {
    "alphabet position (a=1)": lambda s: [ord(c) - 96 for c in s if c.isalpha()],
    "reverse alphabet (z=1)": lambda s: [27 - (ord(c) - 96) for c in s if c.isalpha()],
}

COMPRESS = {
    "": lambda ns: ns,
    " + digital root": lambda ns: [_dr(n) for n in ns],
    " + last digit": lambda ns: [n % 10 for n in ns],
}

RENDER = {
    "": lambda ns: "".join(str(n) for n in ns),
    ", spaced": lambda ns: " ".join(str(n) for n in ns),
    ", dashed": lambda ns: "-".join(str(n) for n in ns),
}


def _dr(n):
    while n > 9:
        n = sum(int(d) for d in str(n))
    return n


def build(word, conv, comp, render, order, backwards_stage):
    """Apply one full pipeline. backwards_stage says WHERE 'backwards' applies."""
    s = word
    if backwards_stage == "letters":
        s = s[::-1]
    ns = CONV[conv](s)
    if order == "sorted":
        ns = sorted(ns)
    if backwards_stage == "numbers":
        ns = ns[::-1]
    if backwards_stage == "order" and order == "sorted":
        ns = sorted(ns, reverse=True)
    ns = COMPRESS[comp](ns)
    out = RENDER[render](ns)
    if backwards_stage == "output":
        out = out[::-1]
    return out


def main():
    # Step 1: which base pipelines satisfy the green control?
    bases = []
    for conv in CONV:
        for comp in COMPRESS:
            for render in RENDER:
                for order in ("asis", "sorted"):
                    if build(GREEN_KEY, conv, comp, render, order, None) == GREEN_ANSWER:
                        bases.append((conv, comp, render, order))

    print(f"base pipelines consistent with green (fghi -> 6789): {len(bases)}")
    for b in bases:
        conv, comp, render, order = b
        print(f"    {conv}{comp}{render}"
              + ("  [sorted]" if order == "sorted" else ""))
    print()

    # Step 2: insert "backwards" at each stage it could mean.
    stages = ["letters", "numbers", "output", "order"]
    results = {}
    for conv, comp, render, order in bases:
        for st in stages:
            if st == "order" and order != "sorted":
                continue
            out = build(RED_KEY, conv, comp, render, order, st)
            desc = (f"{conv}{comp}{render}"
                    + ("  [sorted]" if order == "sorted" else "")
                    + f"  --  backwards applied to the {st}")
            results.setdefault(out, []).append(desc)

    fresh = {k: v for k, v in results.items() if k not in TESTED}
    dead = {k: v for k, v in results.items() if k in TESTED}

    print(f"distinct red answers generated : {len(results)}")
    print(f"  already rejected             : {len(dead)}  {sorted(dead)}")
    print()
    print(f"*** UNTESTED AND CONSISTENT WITH EVERY PIECE OF EVIDENCE: {len(fresh)}")
    print()
    order_hint = ["output", "numbers", "letters", "order"]
    ranked = sorted(fresh.items(),
                    key=lambda kv: (len(kv[0]), -len(kv[1])))
    for out, descs in ranked:
        print(f"  {out!r}")
        for d in descs:
            print(f"      {d}")
    print()
    print("SHORTLIST for the ladder, shortest first (green's answer was 4 chars):")
    print("   " + "  ".join(repr(o) for o, _ in ranked))


if __name__ == "__main__":
    main()
