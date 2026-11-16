"""Make data.json for the finance template (small-business lender). All names and numbers are invented."""
import json
import random
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent.parent / "engine"))
from gen import pct, per_step, spark, curve, graph_nodes, LOG_TAIL

random.seed(20261118)
LINES = [("Working capital", "WCP"), ("Equipment", "EQP"), ("Property", "PRP"), ("Trade finance", "TRF")]
code = dict(LINES)
# segment, line, limit EUR k, balance EUR k, arrears %, loans
SEG = [("Bakeries", "Working capital", 8000, 6100, 2.1, 214), ("Logistics", "Equipment", 14000, 12600, 3.4, 96),
       ("Clinics", "Equipment", 9000, 7400, 1.2, 71), ("Restaurants", "Working capital", 10000, 9300, 6.8, 188),
       ("Builders", "Property", 20000, 15800, 4.1, 64), ("Retail shops", "Working capital", 12000, 8900, 5.2, 240),
       ("Farms", "Equipment", 7000, 5200, 2.8, 58), ("Wholesale", "Trade finance", 16000, 12100, 1.9, 77),
       ("Importers", "Trade finance", 11000, 9900, 7.5, 49), ("Offices", "Property", 15000, 9800, 0.9, 41),
       ("Workshops", "Equipment", 6000, 5600, 3.9, 83), ("Online shops", "Working capital", 9000, 6300, 4.6, 152)]
items = [(n, l, f"limit €{lim/1000:.0f}M", {"loans": ln, "balance": f"{bal/1000:.1f}", "limit": f"{lim/1000:.0f}", "arrears": arr, "use": pct(bal, lim)})
         for n, l, lim, bal, arr, ln in SEG]
nodes, records = graph_nodes(items, code)

portfolio = sum(s[3] for s in SEG); limit = sum(s[2] for s in SEG); loans = sum(s[5] for s in SEG)
arrears = sum(s[3] * s[4] for s in SEG) / portfolio
apps = 2150
approved = round(apps * .64)
worst = max(SEG, key=lambda s: s[4]); lowest_use = min(SEG, key=lambda s: s[3] / s[2])
x = [f"W{w}" for w in range(1, 27)]
shape = [.025, .03, .035, .04, .04, .04, .04, .04, .04, .045, .04, .04, .04, .04, .04, .04, .04, .04, .035, .035, .035, .035, .03, .03, .03, .03]
this_c = curve(apps, shape); last_c = curve(round(apps * .88), shape)

def status(a): return "Default risk" if a >= 7 else "Late" if a >= 4 else "Watch"
data = {
    "groups": [{"id": g, "code": c} for g, c in LINES], "nodes": nodes, "records": records,
    "queries": [[f"balance for {s[0]}", f"{s[0]}-{code[s[1]]}"] for s in SEG[:6]],
    "kpis": [
        {"label": "Loans in book", "value": loans, "note": f"{approved} approved this half-year", "series": spark(loans)},
        {"label": "Portfolio (€M)", "value": round(portfolio / 1000, 1), "note": f"limit €{limit/1000:.0f}M", "series": spark(round(portfolio / 1000))},
        {"label": "Approval rate", "value": pct(approved, apps), "suffix": "%", "note": "of applications", "trend": "up", "series": [52, 55, 54, 58, 57, 60, 59, 62, pct(approved, apps)]},
        {"label": "Arrears rate", "value": round(arrears, 1), "suffix": "%", "note": f"highest: {worst[0]}", "trend": "down", "series": [3.1, 3.3, 3.2, 3.6, 3.9, 3.8, 4.0, 4.1, round(arrears, 1)]},
    ],
    "trend": {"x": x, "series": [{"label": "Applications this half-year", "colour": 1, "cum": this_c, "week": per_step(this_c)},
                                 {"label": "Last year", "colour": 2, "dashed": True, "cum": last_c, "week": per_step(last_c)}]},
    "columns": [{"label": s[0][:7], "full": s[0], "value": round(s[3] / 1000, 1), "target": round(s[2] / 1000, 1)} for s in SEG],
    "lines": [{"label": l, "value": sum(s[3] for s in SEG if s[1] == l)} for l, _ in LINES],
    "watch": [{"name": s[0], "balance": f"€{s[3]/1000:.1f}M", "arrears": f"{s[4]}%", "status": status(s[4])}
              for s in sorted(SEG, key=lambda s: -s[4])[:7]],
    "ask": [
        {"title": "Where is the risk?", "q": "Highest arrears", "a": f"{worst[0]} has the highest arrears at {worst[4]}% on a balance of €{worst[3]/1000:.1f}M. The book as a whole sits at {arrears:.1f}%."},
        {"title": "How full are the limits?", "q": "Balance against limit", "a": f"The book uses {pct(portfolio, limit)}% of its limits (€{portfolio/1000:.0f}M of €{limit/1000:.0f}M). {lowest_use[0]} has the most room, at {pct(lowest_use[3], lowest_use[2])}% used."},
        {"title": "Are we approving enough?", "q": "Approval rate", "a": f"{approved} of {apps} applications were approved. That is {pct(approved, apps)}%."},
        {"title": "Are we ahead of last year?", "q": "Applications against last year", "a": f"{apps} applications so far. Last year ended at {last_c[-1]}. That is {pct(apps - last_c[-1], last_c[-1])}% more."},
    ],
    "log": [["fetch", "loan system export · 2,150 rows"], ["dedupe", "one record per loan id"], ["clean", "closed and test loans out"],
            ["join", "limits per segment"], ["norm", "amounts in EUR thousand"], ["flag", "arrears above 4%"]] + LOG_TAIL,
    "usage": [{"label": l, "value": pct(sum(s[3] for s in SEG if s[1] == l), sum(s[2] for s in SEG if s[1] == l)), "colour": c} for (l, _), c in zip(LINES, (1, 3, 6, 4))],
    "weeks": 8,
}
(HERE / "data.json").write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
print("finance ok", loans, "loans", round(portfolio / 1000, 1), "M")
