"""Make data.json for the university template from the invented demo_data.json.
Every name and number is made up. No real university data."""
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
src = json.loads((HERE.parent.parent / "demo_data.json").read_text(encoding="utf-8"))

LEVELS = [("Laurea", "Bachelor's", "BA"), ("Laurea Magistrale", "Master's", "MA"), ("MBA", "MBA", "MBA")]
lv = {k: (en, code) for k, en, code in LEVELS}
progs = src["programmes"]
fees = {f["programme_id"]: f for f in src["fees"]}
apps = src["applications"]

def count(pid, statuses=None):
    return sum(1 for a in apps if a["programme_id"] == pid and (statuses is None or a["status"] in statuses))

nodes, records = [], {}
for p in progs:
    en, code = lv[p["level"]]
    nid = f'{p["name_en"]}-{code}'
    nodes.append({"id": nid, "label": p["name_en"], "group": en, "school": f'€{p["fee_eur"]:,} a year', "big": True})
    records[nid] = {"applications": count(p["id"]), "offers": count(p["id"], {"Offer", "Accepted", "Enrolled"}),
                    "enrolled": fees[p["id"]]["students"], "target": p["target"]}
for _, en, code in LEVELS:
    for k in range(24):
        nodes.append({"id": f"x{code}{k}", "label": "applicant", "group": en, "school": "—"})

top = sorted(progs, key=lambda p: -records[f'{p["name_en"]}-{lv[p["level"]][1]}']["applications"])[:6]
queries = [[f'applications for {p["name_en"]}', f'{p["name_en"]}-{lv[p["level"]][1]}'] for p in top]

wk = src["weekly"]
labels = [w["week"].split("-")[1] for w in wk]
def per_week(cum): return [cum[0]] + [cum[i] - cum[i - 1] for i in range(1, len(cum))]
this = [w["applications_cum"] for w in wk]; last = [w["applications_cum_last_year"] for w in wk]
s = src["summary"]
tgt = s["target"]
lvl_t = {}
for p in progs:
    en, _ = lv[p["level"]]
    a = lvl_t.setdefault(en, [0, 0]); a[0] += fees[p["id"]]["students"]; a[1] += p["target"]

ctry = sorted(src["countries"], key=lambda c: -c["students"])
other = sum(c["students"] for c in ctry[5:])
best = max(progs, key=lambda p: fees[p["id"]]["students"] / p["target"])
worst = min(progs, key=lambda p: fees[p["id"]]["students"] / p["target"])
adv = max(src["advisors"], key=lambda a: a["open_cases"])
pct = lambda a, b: round(a / b * 100)

data = {
    "groups": [{"id": en, "code": code} for _, en, code in LEVELS],
    "nodes": nodes, "queries": queries, "records": records,
    "kpis": [
        {"label": "Students applied", "value": s["students"], "note": f'+{pct(s["applications"] - s["applications_last_year"], s["applications_last_year"])}% vs last year', "trend": "up", "series": this},
        {"label": "Offers made", "value": s["offers"], "note": f'{pct(s["offers"], s["students"])}% of applicants', "series": [w["applications_cum"] * s["offers"] // s["students"] for w in wk]},
        {"label": "Enrolled", "value": s["enrolled"], "note": f'target {tgt}', "series": [w["enrolled_cum"] for w in wk]},
        {"label": "Target reached", "value": pct(s["enrolled"], tgt), "suffix": "%", "note": f'{tgt - s["enrolled"]} places to go', "series": [w["target_cum"] for w in wk]},
    ],
    "trend": {"x": labels, "series": [
        {"label": "This year", "colour": 1, "cum": this, "week": per_week(this)},
        {"label": "Last year", "colour": 2, "dashed": True, "cum": last, "week": per_week(last)}]},
    "columns": [{"label": p["id"], "full": p["name_en"], "value": fees[p["id"]]["students"], "target": p["target"]} for p in progs],
    "countries": [{"label": c["country_en"], "value": c["students"]} for c in ctry[:5]] + [{"label": "Other countries", "value": other}],
    "advisers": [{"name": a["advisor"], "decided": a["decided_this_week"], "open": a["open_cases"],
                  "load": "Overloaded" if a["open_cases"] >= 45 else "Busy" if a["open_cases"] >= 38 else "On track"}
                 for a in src["advisors"]],
    "ask": [
        {"title": "Are we on target?", "q": "Enrolment against the intake target",
         "a": f'{s["enrolled"]} students are enrolled against a target of {tgt}. That is {pct(s["enrolled"], tgt)}%. {tgt - s["enrolled"]} places are still open.'},
        {"title": "Where do we lose people?", "q": "The step with the biggest drop",
         "a": f'{s["students"]} applied. {s["offers"]} got an offer ({pct(s["offers"], s["students"])}%). {s["enrolled"]} enrolled ({pct(s["enrolled"], s["offers"])}% of offers). The biggest gap is between offer and enrolment.'},
        {"title": "Which programme needs help?", "q": "Lowest share of target",
         "a": f'{worst["name_en"]} has {fees[worst["id"]]["students"]} of {worst["target"]} places filled ({pct(fees[worst["id"]]["students"], worst["target"])}%). {best["name_en"]} is furthest ahead at {pct(fees[best["id"]]["students"], best["target"])}%.'},
        {"title": "Who has the most open cases?", "q": "Adviser workload",
         "a": f'{adv["advisor"]} has {adv["open_cases"]} open cases, the most of the team. Consider moving some to the adviser with the fewest.'},
    ],
    "log": [["fetch", "applications export · 754 rows"], ["dedupe", "one record per student"],
            ["clean", "test applications out"], ["join", "intake targets · 12 programmes"],
            ["norm", "country names · fees in EUR"], ["flag", "offers older than 14 days"],
            ["check", "totals match last run ✓"], ["done", "dashboard refreshed"], ["wait", "next sync in 5 min"]],
    "levels": [{"label": en, "value": pct(*lvl_t[en]), "colour": c} for (_, en, _), c in zip(LEVELS, (1, 3, 6))],
    "weeks": 8,
}
(HERE / "data.json").write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
print("wrote data.json", len(nodes), "nodes")
