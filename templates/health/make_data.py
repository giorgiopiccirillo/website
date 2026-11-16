"""Make data.json for the health template (clinic operations). Invented, aggregated numbers. No patient data of any kind."""
import json
import random
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent.parent / "engine"))
from gen import pct, per_step, spark, curve, graph_nodes, LOG_TAIL

random.seed(20261119)
DEPTS = [("Outpatient", "OUT"), ("Emergency", "EMR"), ("Surgery", "SUR"), ("Diagnostics", "DIA")]
code = dict(DEPTS)
# unit, dept, appointments/week, no-show %, wait min, beds, beds used
UNITS = [("Cardiology", "Outpatient", 420, 6.1, 24, 30, 26), ("Orthopaedics", "Surgery", 310, 4.2, 31, 40, 39),
         ("Paediatrics", "Outpatient", 380, 8.9, 19, 28, 18), ("Emergency room", "Emergency", 960, 2.0, 46, 36, 34),
         ("General surgery", "Surgery", 190, 3.1, 28, 44, 37), ("Radiology", "Diagnostics", 640, 7.4, 22, 0, 0),
         ("Laboratory", "Diagnostics", 880, 1.8, 12, 0, 0), ("Dermatology", "Outpatient", 350, 11.2, 27, 0, 0),
         ("Maternity", "Surgery", 150, 2.4, 20, 32, 25), ("Neurology", "Outpatient", 260, 5.5, 35, 24, 21),
         ("Oncology", "Outpatient", 300, 3.3, 26, 38, 33), ("Intensive care", "Emergency", 40, 0.0, 5, 16, 14)]
items = [(n, d, f"{a} a week", {"appts": a, "noshow": ns, "wait": w, "beds": b, "used": bu, "occ": pct(bu, b) if b else 0})
         for n, d, a, ns, w, b, bu in UNITS]
nodes, records = graph_nodes(items, code)

appts = sum(u[2] for u in UNITS)
ns = sum(u[2] * u[3] for u in UNITS) / appts
wait = round(sum(u[2] * u[4] for u in UNITS) / appts)
beds = sum(u[5] for u in UNITS); used = sum(u[6] for u in UNITS)
wards = [u for u in UNITS if u[5]]
fullest = max(wards, key=lambda u: u[6] / u[5]); worst_ns = max(UNITS, key=lambda u: u[3]); longest = max(UNITS, key=lambda u: u[4])
x = [f"D-{d}" for d in range(13, -1, -1)]
this_c = curve(appts * 2, [.06, .07, .07, .08, .08, .03, .02, .07, .08, .08, .09, .09, .04, .04])
last_c = curve(round(appts * 2 * .94), [.06, .07, .08, .08, .07, .03, .02, .07, .08, .08, .08, .09, .04, .05])

def status(u): f = u[6] / u[5]; return "Full" if f >= .92 else "Busy" if f >= .75 else "OK"
data = {
    "groups": [{"id": g, "code": c} for g, c in DEPTS], "nodes": nodes, "records": records,
    "queries": [[f"waiting time in {u[0]}", f"{u[0]}-{code[u[1]]}"] for u in UNITS[:6]],
    "kpis": [
        {"label": "Appointments a week", "value": appts, "note": "all units", "series": spark(appts)},
        {"label": "No-show rate", "value": round(ns, 1), "suffix": "%", "note": f"highest: {worst_ns[0]}", "trend": "down", "series": [7.2, 6.9, 6.4, 6.6, 6.0, 5.8, 5.5, 5.3, round(ns, 1)]},
        {"label": "Average wait (min)", "value": wait, "note": f"longest: {longest[0]}", "series": [34, 33, 31, 30, 29, 28, 27, 27, wait]},
        {"label": "Bed occupancy", "value": pct(used, beds), "suffix": "%", "note": f"{beds - used} beds free", "series": [78, 81, 83, 80, 84, 86, 85, 87, pct(used, beds)]},
    ],
    "trend": {"x": x, "series": [{"label": "Last 14 days", "colour": 1, "cum": this_c, "week": per_step(this_c)},
                                 {"label": "Previous 14 days", "colour": 2, "dashed": True, "cum": last_c, "week": per_step(last_c)}]},
    "columns": [{"label": u[0][:7], "full": u[0], "value": u[6], "target": u[5]} for u in wards],
    "types": [{"label": l, "value": round(appts * f)} for l, f in [("Check-up", .34), ("Follow-up", .31), ("Urgent", .17), ("Screening", .11), ("Other", .07)]],
    "wards": [{"name": u[0], "occ": f"{pct(u[6], u[5])}%", "wait": f"{u[4]} min", "status": status(u)} for u in sorted(wards, key=lambda u: -u[6] / u[5])],
    "ask": [
        {"title": "Which ward is fullest?", "q": "Highest bed occupancy", "a": f"{fullest[0]} is at {pct(fullest[6], fullest[5])}% ({fullest[6]} of {fullest[5]} beds). The hospital as a whole is at {pct(used, beds)}%."},
        {"title": "Where do people not show up?", "q": "Highest no-show rate", "a": f"{worst_ns[0]} has the most missed appointments, at {worst_ns[3]}%. The average is {ns:.1f}%."},
        {"title": "Where do people wait longest?", "q": "Average waiting time", "a": f"{longest[0]} has the longest wait, {longest[4]} minutes. The average across all units is {wait} minutes."},
        {"title": "Are we busier than before?", "q": "Last 14 days against the 14 before", "a": f"{this_c[-1]} appointments in the last 14 days against {last_c[-1]} before. That is {pct(this_c[-1] - last_c[-1], last_c[-1])}% more."},
    ],
    "log": [["fetch", "booking system export · 4,860 rows"], ["dedupe", "one row per appointment id"], ["clean", "no names, no patient ids"],
            ["join", "bed counts per ward"], ["norm", "waits in minutes"], ["flag", "wards above 90% full"]] + LOG_TAIL,
    "occ": [{"label": d, "value": pct(sum(u[6] for u in wards if u[1] == d), sum(u[5] for u in wards if u[1] == d)), "colour": c} for (d, _), c in zip([x for x in DEPTS if any(u[1] == x[0] and u[5] for u in UNITS)], (1, 3, 6))],
    "weeks": 8,
}
(HERE / "data.json").write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
print("health ok", appts, "appointments")
