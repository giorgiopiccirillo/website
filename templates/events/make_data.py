"""Make data.json for the events template (club nights and festivals). All names and numbers are invented."""
import json
import random
from pathlib import Path

random.seed(20261117)
HERE = Path(__file__).resolve().parent

SERIES = [("Techno", "TEC"), ("House", "HOU"), ("Disco", "DIS"), ("Live", "LIV")]
# name, series, date, capacity, price EUR, demand 0-1.3
EVENTS = [
    ("Night Shift", "Techno", "12 Dec", 900, 22, 1.25), ("Low Tide", "House", "13 Dec", 600, 18, 1.0),
    ("Warehouse 9", "Techno", "19 Dec", 1200, 25, 0.88), ("Sundial", "Disco", "20 Dec", 450, 16, 1.2),
    ("Static Bloom", "Live", "10 Jan", 700, 28, 0.55), ("Deep Cut", "House", "16 Jan", 500, 15, 0.8),
    ("Afterglow", "Disco", "17 Jan", 450, 16, 0.62), ("Concrete", "Techno", "23 Jan", 1000, 24, 0.7),
    ("Paper Moon", "Live", "30 Jan", 650, 30, 0.9), ("Slow Burn", "House", "6 Feb", 550, 17, 0.5),
    ("Red Room", "Techno", "13 Feb", 1100, 26, 0.45), ("Velvet", "Disco", "14 Feb", 500, 20, 0.95),
]
code = dict(SERIES)
rows = []
for name, ser, date, cap, price, dem in EVENTS:
    sold = min(cap, round(cap * dem * random.uniform(.93, 1.04)))
    rows.append({"name": name, "series": ser, "date": date, "cap": cap, "price": price, "sold": sold})

nodes, records = [], {}
for r in rows:
    nid = f'{r["name"]}-{code[r["series"]]}'
    r["id"] = nid
    nodes.append({"id": nid, "label": r["name"], "group": r["series"], "school": r["date"], "big": True})
    records[nid] = {"sold": r["sold"], "cap": r["cap"], "fill": round(r["sold"] / r["cap"] * 100),
                    "revenue": f'{r["sold"] * r["price"]:,}', "price": r["price"]}
for ser, c in SERIES:
    for k in range(24):
        nodes.append({"id": f"x{c}{k}", "label": "ticket buyer", "group": ser, "school": "—"})

tot_sold = sum(r["sold"] for r in rows); tot_cap = sum(r["cap"] for r in rows)
revenue = sum(r["sold"] * r["price"] for r in rows)
sold_out = [r for r in rows if r["sold"] >= r["cap"]]
fill = lambda r: r["sold"] / r["cap"]
slow = min(rows, key=fill); best = max(rows, key=fill)
pct = lambda a, b: round(a / b * 100)

# weeks to the door for the next big night: this edition vs the last one
x = [f"T-{w}" for w in range(8, -1, -1)]
def curve(total, shape):
    out, acc = [], 0
    for i in range(9):
        acc += total * shape[i]; out.append(round(acc))
    out[-1] = total; return out
shape = [.04, .06, .09, .1, .13, .16, .2, .14, .08]
big = rows[0]
this_c = curve(big["sold"], shape)
last_c = curve(round(big["sold"] * .86), [.03, .05, .07, .09, .11, .15, .2, .18, .12])
wk = lambda c: [c[0]] + [c[i] - c[i - 1] for i in range(1, len(c))]
spark = lambda total: [round(total * f) for f in (.05, .1, .18, .27, .38, .52, .68, .85, 1)]

def status(r):
    f = fill(r)
    return "Sold out" if f >= 1 else "Selling" if f >= .6 else "Slow"

data = {
    "groups": [{"id": s, "code": c} for s, c in SERIES],
    "nodes": nodes, "queries": [[f'tickets sold for {r["name"]}', r["id"]] for r in rows[:6]],
    "records": records,
    "kpis": [
        {"label": "Tickets sold", "value": tot_sold, "note": f'of {tot_cap:,} places', "series": spark(tot_sold)},
        {"label": "Ticket revenue (€)", "value": revenue, "note": "before fees", "series": spark(revenue)},
        {"label": "Average fill", "value": pct(tot_sold, tot_cap), "suffix": "%", "note": "across 12 events", "series": spark(pct(tot_sold, tot_cap))},
        {"label": "Sold out", "value": len(sold_out), "note": ", ".join(r["name"] for r in sold_out), "trend": "up", "series": [0, 0, 1, 1, 1, 2, 2, 3, len(sold_out)]},
    ],
    "trend": {"x": x, "series": [
        {"label": f'{big["name"]} · this edition', "colour": 1, "cum": this_c, "week": wk(this_c)},
        {"label": "Last edition", "colour": 2, "dashed": True, "cum": last_c, "week": wk(last_c)}]},
    "columns": [{"label": r["name"][:7], "full": r["name"], "value": r["sold"], "target": r["cap"]} for r in rows],
    "types": [{"label": l, "value": v} for l, v in [
        ("Early bird", round(tot_sold * .22)), ("Regular", round(tot_sold * .46)),
        ("Door", round(tot_sold * .17)), ("Guest list", round(tot_sold * .08)), ("Partner codes", round(tot_sold * .07))]],
    "upcoming": [{"name": r["name"], "date": r["date"], "fill": f'{pct(r["sold"], r["cap"])}%', "left": r["cap"] - r["sold"], "status": status(r)}
                 for r in rows[:7]],
    "ask": [
        {"title": "Which night needs a push?", "q": "Lowest fill",
         "a": f'{slow["name"]} on {slow["date"]} is at {pct(slow["sold"], slow["cap"])}% ({slow["cap"] - slow["sold"]} places left). It is the slowest of all {len(rows)} events.'},
        {"title": "What is our best night?", "q": "Highest fill",
         "a": f'{best["name"]} is at {pct(best["sold"], best["cap"])}% with {best["sold"]} tickets. {len(sold_out)} events are sold out.'},
        {"title": "How much have we earned?", "q": "Ticket revenue",
         "a": f'Tickets bring €{revenue:,} so far. The average ticket costs €{round(revenue / tot_sold)}.'},
        {"title": "Are we ahead of last time?", "q": "This edition against the last",
         "a": f'{big["name"]} has {big["sold"]} tickets sold. The last edition ended with {last_c[-1]}. That is {pct(big["sold"] - last_c[-1], last_c[-1])}% more.'},
    ],
    "log": [["fetch", "ticket shop export · 6,340 rows"], ["dedupe", "one ticket per QR code"],
            ["clean", "refunds and test orders out"], ["join", "capacity per venue"],
            ["norm", "event names · prices in EUR"], ["flag", "events under 50% a week out"],
            ["check", "totals match last run ✓"], ["done", "dashboard refreshed"], ["wait", "next sync in 5 min"]],
    "series": [{"label": s, "value": pct(sum(r["sold"] for r in rows if r["series"] == s), sum(r["cap"] for r in rows if r["series"] == s)), "colour": c}
               for (s, _), c in zip(SERIES, (1, 3, 6, 4))],
    "weeks": 8,
}
(HERE / "data.json").write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
print("wrote data.json", tot_sold, "tickets", revenue, "EUR", len(sold_out), "sold out")
