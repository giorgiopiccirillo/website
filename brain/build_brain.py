"""Build brain.html: a live company-brain demo for the FICTIONAL Beispiel Räder GmbH.

Reads the finished demo brain in ../Company-Brain/demo (wiki pages, number tables, tests)
and inlines it into one page. The page searches in the visitor's browser: no AI model,
no server, nothing leaves the page. Run:  python3 brain/build_brain.py
"""
import csv
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEMO = ROOT.parent / "Company-Brain" / "demo"
SKIP = {"index", "log"}  # navigation and change log, not knowledge


def front(text):
    m = re.match(r"^---\n(.*?)\n---\n(.*)$", text, re.S)
    meta = {}
    for line in m.group(1).splitlines():
        if ":" in line:
            k, v = line.split(":", 1); meta[k.strip()] = v.strip()
    return meta, m.group(2).strip()


pages = []
for p in sorted((DEMO / "wiki").glob("*.md")):
    if p.stem in SKIP:
        continue
    meta, body = front(p.read_text(encoding="utf-8"))
    body = body.replace("service@beispiel-raeder.example", "the service e-mail address")
    pages.append({"slug": p.stem, "title": meta.get("title", p.stem), "type": meta.get("type", ""),
                  "owner": meta.get("owner", ""), "updated": meta.get("updated", ""),
                  "status": meta.get("status", ""), "body": body})


def table(name):
    folder = DEMO / "raw" / "data" / "service"
    rows = list(csv.DictReader((folder / f"{name}.csv").open(encoding="utf-8")))
    for r in rows:
        for k in ("jobs", "revenue_eur"):
            r[k] = int(r[k])
    meta = json.loads((folder / f"{name}.meta.json").read_text(encoding="utf-8")) if (folder / f"{name}.meta.json").exists() else {}
    return {"rows": rows, "meta": meta}


data = {"service_jobs": table("service_jobs"), "monthly_totals": table("monthly_totals")}
golden = {}
for r in csv.DictReader((DEMO / "evals/golden/finance_report_2026-10.csv").open(encoding="utf-8"), delimiter=";"):
    golden[(r["Monat"], r["Bereich"])] = float(r["Umsatz"].replace(".", "").replace(",", "."))
evals = json.loads((DEMO / "evals/evals.json").read_text(encoding="utf-8"))
evals.pop("_help", None)
evals["golden"][0]["golden_value"] = golden[("2026-10", "Service")]
docs = len(list((DEMO / "raw" / "docs").rglob("*.md")))

blob = json.dumps({"pages": pages, "data": data, "evals": evals, "docs": docs}, ensure_ascii=False).replace("</", "<\\/")
tpl = (ROOT / "brain" / "brain_page.html").read_text(encoding="utf-8")
(ROOT / "brain.html").write_text(tpl.replace("/*BRAIN_DATA*/", blob), encoding="utf-8")
print("wrote brain.html:", len(pages), "pages,", sum(len(v) for v in evals.values()), "tests,", docs, "source docs")
