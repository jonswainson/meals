#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Write each recipe's `serve` block: how a cooked dish reaches the plates.

Written 8 October 2026. Three stages, three kinds of quantity (Jon, 7 October):
the shop buys whole things, the recipe card weighs in grams, and serving uses
common sense. This script is the serving stage. It never changes what is
bought or cooked, only how the finished dish is shared out:

- what is cooked together is shared together: "split the pot into 10, Jon 4,
  Cheryl 3, your daughter 3", with plate weights underneath as a check;
- what is cooked apart (rice, pasta, bulgur, bread) is weighed cooked;
- whole things (fillets, loins, wraps, kofta, potatoes) are counted, one each
  at least, and where that moves Jon's or Cheryl's plate by more than 40 kcal
  the named side makes it up;
- cold tubs keep a per-component table, in the weights that go in the tub.

Per-ingredient serving grams for a mixed dish are gone: nobody can weigh 160g
of coconut milk out of a curry.

    python3 tools/build_serve.py          # rewrites recipes.json in place
"""
import io, json, os

BASE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
PATH = os.path.join(BASE, "recipes.json")
DATA = json.load(io.open(PATH, encoding="utf-8"))
COMP = json.load(io.open(os.path.join(BASE, "composition.json"), encoding="utf-8"))["items"]
WHO = ("jon", "cheryl", "daughter")

def yld(item):
    y = COMP.get(item, {}).get("cookedYield")
    return 1.0 if y is None else y

def kcal_per_g(item, cooked=False):
    k = COMP[item]["kcal"] / 100.0
    return k / yld(item) if cooked and yld(item) else k

# --------------------------------------------------------------- per recipe
# pot:     cooked together, shared by ratio. "all" = the whole plate.
# label:   what the pot is called on the card
# apart:   cooked separately, served by cooked weight
# count:   item -> (grams each, raw), one, many
# adjust:  the side that absorbs a count's rounding
# cut:     how a pot that sets (a tortilla) is shared
# tub:     cold assembly: components as served, nothing cooked together
# cookedahead: tub items listed raw but cooked before they go in
CFG = {
    # one pot or tray, everything together
    "bolognese-hidden-lentils":  dict(pot="all", label="the sauce", apart=["Wholewheat spaghetti, dry"]),
    "turkey-black-bean-chilli":  dict(pot="all", label="the chilli"),
    "beef-chilli-slow-cooker":   dict(pot="all", label="the chilli"),
    "beef-barley-stew-slow-cooker": dict(pot="all", label="the stew"),
    "chicken-chickpea-tagine-slow-cooker": dict(pot="all", label="the tagine"),
    "egg-fried-brown-rice-prawns": dict(pot="all", label="the fried rice"),
    "smoked-haddock-egg-kedgeree": dict(pot="all", label="the kedgeree"),
    "prawn-pea-barley-orzotto":  dict(pot="all", label="the orzotto"),
    "chicken-bean-spinach-pot":  dict(pot="all", label="the pot"),
    "coconut-chicken-rice":      dict(pot="all", label="the pot"),
    "chicken-arrabbiata-penne":  dict(pot="all", label="the pasta"),
    "harissa-chicken-chickpeas": dict(pot="all", label="the trays"),
    "cod-cannellini-leek-braise": dict(pot="all", label="the braise", apart=["Wholemeal sourdough"]),
    "spanish-chicken-butter-beans": dict(pot="all", label="the dish", apart=["Wholegrain baguette"]),
    "baked-meatballs-ciabatta":  dict(pot="all", label="the meatballs and sauce", apart=["Wholemeal ciabatta"]),
    "smoky-chicken-chickpea-braise": dict(pot="all", label="the braise"),
    "roast-broccoli-soup-halloumi": dict(pot="all", label="the soup"),
    "tortilla-chicken-piquillo": dict(pot="all", label="the tortilla", cut=True),

    # cooked apart, plated apart
    "penang-chicken-curry": dict(label="the curry", apart=["Jasmine rice, dry"],
        potitems=["Chicken thighs, skinless boneless", "Reduced-fat coconut milk, tinned",
                  "Baby corn", "Red peppers"]),
    "beef-kofta-bulgur-skyr": dict(label="the sauce",
        count={"Beef mince, 5%": (50, "kofta", "kofta")},
        apart=["Bulgur wheat, dry"], potitems=["Passata", "Red peppers", "Spinach"],
        within=["Onions"],
        adjust="Bulgur wheat, dry"),
    "chicken-fajitas": dict(label="the chicken and peppers",
        potitems=["Chicken breast, raw", "Red and yellow peppers", "Onions"],
        count={"Wholemeal wraps": (60, "wrap", "wraps")}),
    "loaded-jacket-potatoes": dict(label="the tuna mayo",
        count={"Baking potatoes": (275, "potato", "potatoes")},
        potitems=["Tuna in spring water, no added salt"], note="Smaller potatoes for Cheryl and your daughter."),
    "baked-salmon-lentils": dict(label="the lentils and tomatoes",
        count={"Salmon fillets, raw": (150, "fillet", "fillets")},
        potitems=["Green lentils, tinned", "Cherry tomatoes", "Spinach or kale"],
        adjust="Green lentils, tinned"),
    "salmon-roasted-veg-traybake": dict(label="the vegetables",
        count={"Salmon fillets, raw": (180, "fillet", "fillets")},
        potitems=["Sweet potato", "Courgette", "Red onions", "Asparagus", "Cherry tomatoes",
                  "Butter beans"], adjust="pot"),
    "chicken-pepper-potato-traybake": dict(label="the potatoes, peppers and beans",
        count={"Chicken breast, raw": (200, "breast", "breasts")},
        potitems=["New potatoes", "Peppers", "Red onions", "Butter beans", "Tenderstem broccoli"],
        adjust="pot"),
    "crumbed-cod-crushed-potato": dict(
        count={"Haddock loins, unsmoked": (190, "loin", "loins")},
        adjust="New potatoes"),
    "piri-piri-chicken-crushed-potato": dict(),
    "crispy-duck-lentils-red-cabbage": dict(manual=[("Duck, carved", 200), ("Puy lentils, cooked", 145),
                                                    ("Red cabbage", 106), ("Tenderstem", 109)]),
    "convenience-fallback": dict(asis=True),
    "honey-glazed-chicken-wedges": dict(),

    # cold tubs and plates, assembled not cooked together
    "tuna-chickpea-salad": dict(tub=True),
    "tuna-butter-bean-fennel-tub": dict(tub=True),
    "chicken-butter-bean-tub": dict(tub=True),
    "prawn-butter-bean-salad": dict(tub=True, drop=["Lemons", "Olive oil"]),
    "dip-box": dict(tub=True, cookedahead=["Chicken breast, raw"]),
    "pitta-poached-chicken-slaw": dict(tub=True, cookedahead=["Chicken breast, raw"]),
}

# what a raw ingredient is called once it is on the plate
SERVED_NAME = {
    "Chicken breast, raw": "Chicken, cooked", "Chicken thighs, skinless boneless": "Chicken, cooked",
    "Wholewheat spaghetti, dry": "Spaghetti, cooked", "Jasmine rice, dry": "Rice, cooked",
    "Bulgur wheat, dry": "Bulgur, cooked", "Potatoes": "Potatoes, cooked",
    "New potatoes": "Crushed potatoes", "Frozen peas": "Peas", "Pointed/hispi cabbage": "Hispi cabbage",
    "Tenderstem broccoli": "Tenderstem", "Frozen edamame": "Edamame", "Asparagus": "Asparagus",
    "Salmon fillets, raw": "Salmon", "Haddock loins, unsmoked": "Haddock",
    "Baking potatoes": "Baked potato", "Beef mince, 5%": "Kofta",
}
def served_name(item):
    if item in SERVED_NAME: return SERVED_NAME[item]
    return item.split(",")[0]

def r1(x): return int(round(x))

def build(r, cfg):
    plates, ps = r["plates"], r.get("plateSplit") or {}
    eaters = [w for w in WHO if isinstance(plates.get(w), dict) and plates[w].get("plateGrams")]
    pg = {w: plates[w]["plateGrams"] for w in eaters}
    ing = {i["item"]: i["grams"] for i in r["ingredients"]}
    comps = {c["item"]: c for c in ps.get("components") or []}

    # each eater's share of the batch: from the split rows where there are any,
    # otherwise from the portion convention (Jon 1, Cheryl 0.75, daughter by plate)
    def share(w):
        rows = [c[w] / ing[c["item"]] for c in comps.values() if c.get(w) and ing.get(c["item"])]
        if rows: return sorted(rows)[len(rows) // 2]
        return (pg[w] / pg["jon"]) / r["basePortions"]
    sh = {w: share(w) for w in eaters}
    raw = lambda item, w: (comps[item][w] if item in comps and comps[item].get(w) is not None
                           else ing.get(item, 0) * sh[w])

    out = {"rows": [], "share": None, "adjusted": {}}

    # nothing cooked: the things themselves, Cheryl at three-quarters of each
    if cfg.get("asis"):
        for i in r["ingredients"]:
            row = {"what": i["item"].split(",")[0], "unit": i.get("packUnit") or "g"}
            for w in eaters: row[w] = r1(i["grams"] * (pg[w] / pg["jon"]))
            out["rows"].append(row)
        return out
    # cooked weights stated on the recipe, carried across in proportion to each plate
    if cfg.get("manual"):
        for what, g in cfg["manual"]:
            row = {"what": what, "unit": "g"}
            for w in eaters: row[w] = r1(g * pg[w] / pg["jon"])
            out["rows"].append(row)
        return out

    if cfg.get("tub"):
        for c in ps.get("components") or []:
            if c["item"] in cfg.get("drop", []): continue
            ck = c["item"] in cfg.get("cookedahead", [])
            already = "cooked weight" in (c.get("note") or "")
            row = {"what": served_name(c["item"]) if ck else
                           ("Prawns, cooked" if already else c["item"].split(",")[0]), "unit": "g"}
            if c.get("note") and not already: row["note"] = c["note"]
            for w in eaters:
                if c.get(w) is not None: row[w] = r1(c[w] * (yld(c["item"]) if ck else 1))
            out["rows"].append(row)
        out["tub"] = True
        return out

    # cooked apart: weighed cooked
    for item in cfg.get("apart", []):
        row = {"what": served_name(item), "unit": "g"}
        for w in eaters: row[w] = r1(raw(item, w) * yld(item))
        out["rows"].append(row)

    # counted
    for item, (each, one, many) in (cfg.get("count") or {}).items():
        row = {"what": served_name(item).replace(", cooked", ""), "unit": "count",
               "one": one, "many": many, "item": item}
        for w in eaters:
            n = max(1, int(round(raw(item, w) / each)))
            row[w] = n
            drift = (n * each - raw(item, w)) * kcal_per_g(item)
            if w != "daughter" and abs(drift) > 40 and cfg.get("adjust"):
                out["adjusted"][w] = drift
        out["rows"].append(row)

    # separate components not otherwise placed, for plated dishes
    placed = (set(cfg.get("apart", [])) | set(cfg.get("count") or {}) | set(cfg.get("potitems", []))
              | set(cfg.get("within", [])))
    if cfg.get("pot") != "all":
        for item, c in comps.items():
            if item in placed: continue
            row = {"what": served_name(item), "unit": "g"}
            for w in eaters:
                if c.get(w) is not None: row[w] = r1(c[w] * yld(item))
            out["rows"].append(row)

    # the shared part is whatever of the finished plate the rows do not account for
    if cfg.get("pot") == "all" or cfg.get("potitems"):
        sp = {"label": cfg.get("label", "the dish")}
        for w in eaters:
            rest = pg[w]
            for row in out["rows"]:
                if row["unit"] == "g": rest -= row.get(w, 0)
                else:
                    # the planned share, not the whole counted thing: the count's
                    # rounding is settled in kcal below, not taken out of the pot
                    rest -= raw(row["item"], w) * yld(row["item"])
            sp[w] = max(0, r1(rest))
        if cfg.get("cut"): sp["cut"] = True
        out["share"] = sp

    # make up a count's rounding with the named side, in kcal
    for w, drift in out["adjusted"].items():
        side = cfg["adjust"]
        if side == "pot" and out["share"]:
            # the pot's energy density: everything in it, cooked, per gram
            pot_items = cfg.get("potitems", [])
            k = sum(ing[i] * COMP[i]["kcal"] / 100 for i in pot_items)
            g = sum(ing[i] * yld(i) for i in pot_items)
            delta = -drift / (k / g)
            out["share"][w] = max(0, r1(out["share"][w] + delta))
        else:
            name = served_name(side)
            row = next((x for x in out["rows"] if x["what"] == name), None)
            cooked = side in cfg.get("apart", []) or yld(side) != 1
            delta = -drift / kcal_per_g(side, cooked=cooked)
            if row is None and out["share"]:
                out["share"][w] = max(0, r1(out["share"][w] + delta))
            elif row is not None:
                row[w] = max(0, r1(row[w] + delta))
        out["adjusted"][w] = r1(drift)
    if not out["adjusted"]: del out["adjusted"]
    if cfg.get("note"): out["note"] = cfg["note"]
    if cfg.get("adjust") and out.get("adjusted"):
        out["adjustSide"] = (out["share"]["label"] if cfg["adjust"] == "pot"
                             else served_name(cfg["adjust"]).replace(", cooked", "").lower())
    for row in out["rows"]: row.pop("item", None)
    return out

missing = []
for r in DATA["recipes"]:
    if r.get("retired"): continue
    cfg = CFG.get(r["id"])
    if cfg is None:
        missing.append(r["id"]); continue
    r["serve"] = build(r, cfg)

if missing:
    raise SystemExit("no serving rule for: " + ", ".join(missing))
import sys
if "--dry" in sys.argv:
    for r in DATA["recipes"]:
        if "serve" not in r: continue
        sv = r["serve"]; print("\n" + r["id"], "plates", {w: (r["plates"].get(w) or {}).get("plateGrams") for w in WHO})
        if sv.get("share"): print("   SHARE", sv["share"])
        for row in sv["rows"]: print("   ", row)
        if sv.get("adjusted"): print("   ADJUSTED kcal drift", sv["adjusted"])
    raise SystemExit(0)
io.open(PATH, "w", encoding="utf-8").write(json.dumps(DATA, indent=2, ensure_ascii=False) + "\n")
print("serve written for %d recipes" % sum(1 for r in DATA["recipes"] if "serve" in r))
