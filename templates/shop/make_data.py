"""Make data.json for the shop template. All data is invented. Fixed seed: same file every run."""
import json
import math
import random
from pathlib import Path

random.seed(20261116)

GROUPS = [("Vienna", "VIE"), ("London", "LON"), ("Rome", "ROM"),
          ("Paris", "PAR"), ("Madrid", "MAD"), ("Amsterdam", "AMS")]
PRODUCTS = [("Espresso Blend", "Coffee"), ("House Filter", "Coffee"), ("Single Origin", "Coffee"),
            ("Decaf", "Coffee"), ("Cold Brew", "Coffee"), ("Subscription", "Coffee"),
            ("Green Tea", "Tea"), ("Chai", "Tea"), ("Earl Grey", "Tea"), ("Grinder", "Gear"),
            ("Kettle", "Gear"), ("Dripper", "Gear"), ("Mug", "Gear"), ("Gift Box", "Gear"),
            ("Beans 1kg", "Coffee"), ("Matcha", "Tea")]
QUERIES = [
    ("orders for Espresso Blend in Vienna", "Espresso Blend-VIE"),
    ("repeat buyers of House Filter in London", "House Filter-LON"),
    ("conversion for Single Origin in Rome", "Single Origin-ROM"),
    ("stock left for Decaf in Paris", "Decaf-PAR"),
    ("returns for Espresso Blend in Madrid", "Espresso Blend-MAD"),
    ("new customers for House Filter in Amsterdam", "House Filter-AMS"),
]

nodes = []
for gid, code in GROUPS:
    for i, (p, s) in enumerate(PRODUCTS):
        if (i + len(code) + len(gid)) % 3 != 0 or i < 4:
            nodes.append({"id": f"{p}-{code}", "label": p, "group": gid, "school": s, "big": i < 9})
    for k in range(22):
        nodes.append({"id": f"x{code}{k}", "label": "product variant", "group": gid, "school": "—"})

records = {}
for _, nid in QUERIES:
    visits = 900 + (len(nid) * 137) % 1600
    carts = round(visits * .21)
    records[nid] = {"visits": visits, "carts": carts, "orders": round(carts * .58)}

tree = [{"t": "markets/", "c": None}]
for ci, (gid, code) in enumerate(GROUPS):
    last = ci == len(GROUPS) - 1
    tree.append({"t": f"{'└' if last else '├'} {code} {gid.lower()}/", "c": code})
    if ci < 2:
        for si, s in enumerate(["coffee", "tea", "gear"]):
            tree.append({"t": f"{' ' if last else '│'}  {'└' if si == 2 else '├'} {s}/", "c": code})

orders, carts, target = 4826, 8310, 5500
data = {
    "groups": [{"id": g, "code": c} for g, c in GROUPS],
    "nodes": nodes,
    "queries": [[q, i] for q, i in QUERIES],
    "records": records,
    "tree": tree,
    "kpi": {"value": orders, "notes": [
        {"label": "carts", "value": carts},
        {"label": "conversion", "value": round(orders / carts * 100, 1), "suffix": "%"},
        {"label": "vs target", "value": round(orders / target * 100, 1), "suffix": "%"}]},
    "bars": [{"label": g.lower(), "value": v, "group": g}
             for (g, _), v in zip(GROUPS, [1384, 1022, 806, 655, 519, 440])],
    "channels": [{"label": l, "value": v} for l, v in [
        ("Web shop", 2140), ("Subscriptions", 980), ("Marketplaces", 702),
        ("Cafés (B2B)", 511), ("Pop-up stores", 298), ("Gift partners", 195)]],
    "log": [["fetch", "shop export · 12,480 rows"], ["dedupe", "one order per checkout"],
            ["clean", "refunds and test orders out"], ["join", "quarter targets · 3 categories"],
            ["norm", "market names · currency in EUR"], ["flag", "low stock under 2 weeks"],
            ["check", "totals match last run ✓"], ["done", "dashboard refreshed"],
            ["wait", "next sync in 5 min"]],
    "stream": [40 + round(30 * math.sin(i / 3) + random.random() * 45) for i in range(36)],
    "meters": [{"label": "Coffee", "value": 88, "colour": 1}, {"label": "Tea", "value": 74, "colour": 3},
               {"label": "Gear", "value": 61, "colour": 6}],
    "weeks": 8,
}
out = Path(__file__).with_name("data.json")
out.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
print("wrote", out, len(nodes), "nodes")
