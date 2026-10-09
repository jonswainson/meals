#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Every consistency check the planner has needed, in one place.

Written 21 September 2026. Each check exists because something reached Jon's
kitchen that should not have: a card telling him to weigh 350g of cottage
cheese for himself, a tin of beans the list would not buy enough of, a
smoothie with three different fibre figures. Run it before shipping anything.

    python3 tools/check.py        # exit 0 = clean, 1 = findings
"""
import json, io, re, sys, os, collections

BASE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
def load(n): return json.load(io.open(os.path.join(BASE, n), encoding="utf-8"))
COMP = load("composition.json")["items"]
DATA = load("recipes.json")
PLAN = io.open(os.path.join(BASE, "plan.html"), encoding="utf-8").read()
K = ["kcal", "protein", "fibre", "salt"]
findings = []
def fail(check, what, detail): findings.append((check, what, detail))

# names the cards use for things the composition table calls something else
EQUIV = {
    "Skyr": "Plain Skyr", "Skyr, plain or raspberry": "Plain Skyr",
    "Whey": "Whey protein powder", "Vanilla protein powder": "Whey protein powder",
    "Milk": "Semi-skimmed milk", "Reduced-fat milk": "Semi-skimmed milk",
    "Porridge oats": "Rolled oats", "Cinnamon, a pinch": "Ground cinnamon",
    "Walnuts, chopped": "Walnuts", "Walnuts or almonds": "Walnuts",
    "Whole roasted almonds": "Whole almonds", "Banana, weighed": "Bananas",
    "Blueberries, for the jam": "Frozen blueberries",
    "Frozen cherries, pitted": "Frozen cherries",
    "High-protein wrap": "High-protein wraps", "Water": None,
}
def canon(name):
    if name in EQUIV: return EQUIV[name]
    if re.match(r"^Banana", name): return "Bananas"
    return name

# spices the card gives as spoons in the method, not as grams in the
# how-much-each table (27 Sept). They are still eaten and still on the list.
SPOONED = {"Ground cinnamon", "Ground nutmeg", "Ground ginger"}

# ---------------------------------------------------------------- fixed items
mixes = dict(re.findall(r'FIXED\["([a-z0-9-]+)"\]\.mix = (\[.*?\]);', PLAN, re.S))
ings  = {}
for rid, body in re.findall(r'FIXED\["([a-z0-9-]+)"\]\.ing\s*=\s*\{(.*?)\};', PLAN, re.S):
    ings[rid] = body.split("cheryl:")[0]
stated = {}
for rid, body in re.findall(r'"([a-z0-9-]+)":\s*\{name:.*?jon:\{([^}]+)\}', PLAN, re.S):
    stated[rid] = {k: float(v) for k, v in re.findall(r"(\w+):([\d.]+)", body)}
MIX = re.compile(r'\["([^"]+)",\s*([\d.]+)')
ING = re.compile(r'I\("([^"]+)",\s*([\d.]+)')

# 1. what the card tells you to weigh == what the list buys
for rid in sorted(set(mixes) & set(ings)):
    M, G = collections.Counter(), collections.Counter()
    for n, g in MIX.findall(mixes[rid]):
        c = canon(n)
        if c: M[c] += float(g)
    for n, g in ING.findall(ings[rid]):
        c = canon(n)
        if c: G[c] += float(g)
    for k in set(M) | set(G):
        if k in SPOONED and k not in M: continue
        a, b = M.get(k, 0), G.get(k, 0)
        if abs(a - b) > max(0.6, max(a, b) * 0.05):
            fail("card vs shopping line", rid, "%s: card %gg, list %gg" % (k, a, b))

# 2. stated macros == the mix, costed from the table
for rid in sorted(set(mixes) & set(stated)):
    tot, miss = {k: 0.0 for k in K}, []
    rows = MIX.findall(mixes[rid])
    listed = {canon(n) for n, g in rows}
    rows += [(n, g) for n, g in ING.findall(ings.get(rid, ""))
             if n in SPOONED and n not in listed]
    for n, g in rows:
        c = canon(n)
        if c is None: continue
        if c not in COMP: miss.append(n); continue
        for k in K: tot[k] += COMP[c].get(k, 0) * float(g) / 100.0
    if miss:
        fail("macros vs table", rid, "not in the table: " + ", ".join(miss)); continue
    for k in K:
        a = stated[rid].get(k)
        if a is None: continue
        if abs(a - tot[k]) > max(0.05 if k == "salt" else 0.5, abs(a) * 0.04):
            fail("macros vs table", rid, "%s: stated %g, ingredients give %.2f" % (k, a, tot[k]))

# 3. every shopping item exists in the table
for n in sorted(set(re.findall(r'I\("([^"]+)"', PLAN))):
    if n not in COMP: fail("unknown ingredient", "plan.html", n)

# ------------------------------------------------------------------- recipes
for r in DATA["recipes"]:
    if r.get("retired"): continue
    rid = r["id"]
    ing = {i["item"]: i["grams"] for i in r["ingredients"]}
    for n in ing:
        if n not in COMP: fail("unknown ingredient", rid, n)
    # 4. plates cannot take more of something than the batch contains
    for c in ((r.get("plateSplit") or {}).get("components") or []):
        if c["item"] not in ing:
            fail("split vs batch", rid, "%s is not an ingredient" % c["item"]); continue
        tot = sum(v for k, v in c.items()
                  if k in ("jon", "cheryl", "daughter") and isinstance(v, (int, float)))
        if tot > ing[c["item"]] * 1.02:
            fail("split vs batch", rid,
                 "%s: plates take %.0fg of a %.0fg batch" % (c["item"], tot, ing[c["item"]]))
    # 5. the plate weight is that person's share of the finished batch.
    # Rows are raw weights of the main items only; the plate is cooked and
    # carries everything (oil, dressing, garnish), so the rows cannot sum to it.
    # The share is read off the rows, then applied to the batch costed through
    # cookedYield, which is how composition.json says plates are weighed.
    ps = r.get("plateSplit") or {}
    comps = ps.get("components") or []
    if comps and ps.get("grams"):
        done = sum(g * (COMP.get(n, {}).get("cookedYield") or 1) for n, g in ing.items())
        for who in ("jon", "cheryl"):
            if who not in ps["grams"]: continue
            shares = sorted(c[who] / ing[c["item"]] for c in comps
                            if c.get(who) and ing.get(c["item"]))
            if not shares: continue
            exp = done * shares[len(shares) // 2]
            if abs(exp - ps["grams"][who]) > max(12, exp * 0.06):
                fail("plate vs batch", rid, "%s: share of the cooked batch is %.0fg, plate says %.0fg"
                     % (who, exp, ps["grams"][who]))
    # 6. Cheryl is three-quarters of Jon. It is the rule, not an outcome.
    pj, pc = r["plates"]["jon"], r["plates"].get("cheryl")
    if pc:
        for k in ("kcal", "protein", "plateGrams"):
            if pj.get(k) and pc.get(k):
                exp = pj[k] * 0.75
                if abs(pc[k] - exp) > max(8, exp * 0.04):
                    fail("4:3 ratio", rid, "%s: Cheryl %g vs 0.75 x Jon = %.0f" % (k, pc[k], exp))
    # 7. the daughter carries weights only
    pd = r["plates"].get("daughter")
    if isinstance(pd, dict):
        for k in K:
            if k in pd: fail("daughter has numbers", rid, "%s is present on her plate" % k)

# 8. anything used drained needs a drained yield, or the list buys too few tins
# Being in drainedYields is what marks an item drained: the card labels it and works
# out the tins from it, so the note must not count tins by hand - those counts went
# stale (900g of butter beans was "2 tins").
YIELDS = DATA.get("drainedYields", {})
for r in DATA["recipes"]:
    if r.get("retired"): continue
    for i in r["ingredients"]:
        note = (i.get("note") or "").lower()
        if "drain" in note and i.get("packSize") and i["item"] not in YIELDS:
            fail("no drained yield", r["id"],
                 "%s is used drained against a %sg gross pack" % (i["item"], i["packSize"]))
        if i["item"] in YIELDS:
            if not i.get("packSize"):
                fail("no drained yield", r["id"], "%s has a drained yield but no pack size" % i["item"])
            if re.search(r"\b(tins?|jars?|cans?)\b", note):
                fail("tins by hand", r["id"], "%s: note %r counts packs; the card does that"
                     % (i["item"], i["note"]))

# 9. every meal the weeks plan resolves to a live recipe or a fixed item
LIVE = {r["id"] for r in DATA["recipes"] if not r.get("retired")}
FIXED_IDS = set(re.findall(r'^\s*"([a-z0-9-]+)":\s*\{name:', PLAN, re.M))
for rid in sorted(set(re.findall(r'kind:"recipe",\s*id:"([^"]+)"', PLAN))):
    if rid not in LIVE and not rid.startswith("own-"):
        fail("plan points nowhere", "plan.html", "recipe %s is missing or retired" % rid)
for fid in sorted(set(re.findall(r'(?:kind:"fixed",\s*id|cheryl):"([a-z0-9-]+)"', PLAN))):
    if fid not in FIXED_IDS:
        fail("plan points nowhere", "plan.html", "fixed item %s does not exist" % fid)

# 10. every recipe says how it reaches the plates (tools/build_serve.py), and the
#     shared part never comes out below nothing
for r in DATA["recipes"]:
    if r.get("retired"): continue
    sv = r.get("serve")
    if not sv:
        fail("no serving guide", r["id"], "run tools/build_serve.py"); continue
    for who, g in (sv.get("share") or {}).items():
        if who in ("jon", "cheryl", "daughter") and g <= 0:
            fail("no serving guide", r["id"], "%s's share of %s is %sg" % (who, sv["share"]["label"], g))

# ------------------------------------------------------------------- report
if findings:
    w = max(len(f[0]) for f in findings)
    for c, what, d in findings: print("%-*s  %-34s %s" % (w, c, what, d))
    print("\n%d finding(s)" % len(findings))
else:
    print("clean: %d recipes, %d fixed items, %d ingredients" %
          (len([r for r in DATA["recipes"] if not r.get("retired")]),
           len(set(mixes) & set(stated)), len(COMP)))
sys.exit(1 if findings else 0)
