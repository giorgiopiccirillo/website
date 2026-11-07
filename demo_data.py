"""Deterministic fake admissions data for the demo dashboard.

Everything here is invented. A fixed seed means every run writes the same
demo_data.json, byte for byte.
"""
from __future__ import annotations

import datetime as dt
import json
import random
from pathlib import Path

SEED = 20271107
TODAY = dt.date(2027, 7, 15)
WINDOW_START = dt.date(2027, 1, 18)  # Monday of 2027-W03
FIRST_WEEK, LAST_WEEK = 3, 28
N_STUDENTS = 640
OUT = "demo_data.json"

STATUS_PRIORITY = ["Enrolled", "Accepted", "Offer", "In review",
                   "Submitted", "Rejected", "Withdrawn"]
# Weight of each student's strongest status.
STATUS_WEIGHTS = [0.38, 0.07, 0.12, 0.13, 0.10, 0.14, 0.06]
OPEN_STATUSES = ("Offer", "In review", "Submitted")

# id, name_it, name_en, level, fee_eur, demand
PROGRAMMES = [
    ("ECM", "Economia e Management", "Economics and Management", "Laurea", 4800, 1.5),
    ("ING", "Ingegneria Informatica", "Computer Engineering", "Laurea", 5200, 1.4),
    ("DCO", "Design della Comunicazione", "Communication Design", "Laurea", 5000, 0.9),
    ("POL", "Scienze Politiche e Relazioni Internazionali",
     "Political Science and International Relations", "Laurea", 4600, 0.8),
    ("PSI", "Psicologia", "Psychology", "Laurea", 4900, 1.1),
    ("ARC", "Scienze dell'Architettura", "Architecture", "Laurea", 5400, 0.7),
    ("LIN", "Lingue e Comunicazione Interculturale",
     "Languages and Intercultural Communication", "Laurea", 4400, 0.6),
    ("FIN", "Finanza e Mercati", "Finance and Markets", "Laurea Magistrale", 6800, 1.0),
    ("DAT", "Data Science e Intelligenza Artificiale",
     "Data Science and Artificial Intelligence", "Laurea Magistrale", 7200, 1.6),
    ("MKT", "Marketing Digitale", "Digital Marketing", "Laurea Magistrale", 6400, 0.9),
    ("SOS", "Sostenibilità e Innovazione",
     "Sustainability and Innovation", "Laurea Magistrale", 6000, 0.5),
    ("MBA", "Master in Business Administration", "MBA", "MBA", 14500, 0.6),
]

# country_en, country_it, weight
COUNTRIES = [
    ("Italy", "Italia", 40.0), ("India", "India", 12.0), ("Pakistan", "Pakistan", 8.0),
    ("Nigeria", "Nigeria", 7.0), ("Iran", "Iran", 5.0), ("Egypt", "Egitto", 4.5),
    ("Turkey", "Turchia", 4.0), ("Morocco", "Marocco", 3.5), ("China", "Cina", 3.0),
    ("Albania", "Albania", 2.5), ("Bangladesh", "Bangladesh", 2.0),
    ("Brazil", "Brasile", 1.6), ("Ghana", "Ghana", 1.5), ("Kenya", "Kenya", 1.3),
    ("Nepal", "Nepal", 1.3), ("Colombia", "Colombia", 1.1), ("Vietnam", "Vietnam", 1.0),
    ("Ukraine", "Ucraina", 0.9),
]

ADVISORS = ["Chiara", "Marco", "Giulia", "Luca", "Elena", "Matteo"]

# 10 messy export rows and the same rows once cleaned.
BEFORE_AFTER = {
    "raw": [
        {"student": " mario ROSSI ", "country": "ITA", "programme": "Ec. e Management",
         "status": "submitted ", "submitted": "3/2/27"},
        {"student": "Aisha  khan", "country": "pakistan", "programme": "Ing. Informatica",
         "status": "In Review", "submitted": "2027-02-11"},
        {"student": "RAVI SHARMA", "country": "India ", "programme": "Data Science e IA",
         "status": "Offer ", "submitted": "14.02.2027"},
        {"student": "chidi okafor", "country": "Nigeria", "programme": "MBA ",
         "status": "Submited", "submitted": "02/17/2027"},
        {"student": "Sara  Hosseini", "country": "IRAN", "programme": "Psicologia",
         "status": "accepted", "submitted": "2027/02/20"},
        {"student": "omar hassan ", "country": "Egitto", "programme": "Finanza & Mercati",
         "status": "ENROLLED", "submitted": "23-2-2027"},
        {"student": "Elif  yilmaz", "country": "Turkiye", "programme": "Design Comunicazione",
         "status": "Rejected", "submitted": "1 Mar 2027"},
        {"student": "YOUSSEF BENALI", "country": "marocco", "programme": "Marketing Dig.",
         "status": "withdrawn", "submitted": "2027-03-04"},
        {"student": " li  wei", "country": "CN", "programme": "Architettura",
         "status": "In  review", "submitted": "9/3/27"},
        {"student": "elira HOXHA", "country": "albania ", "programme": "Sc. Politiche e RI",
         "status": "Offer", "submitted": "12.03.2027"},
    ],
    "clean": [
        {"student": "Mario Rossi", "country": "Italy", "programme": "Economics and Management",
         "status": "Submitted", "submitted": "2027-02-03"},
        {"student": "Aisha Khan", "country": "Pakistan", "programme": "Computer Engineering",
         "status": "In review", "submitted": "2027-02-11"},
        {"student": "Ravi Sharma", "country": "India",
         "programme": "Data Science and Artificial Intelligence",
         "status": "Offer", "submitted": "2027-02-14"},
        {"student": "Chidi Okafor", "country": "Nigeria", "programme": "MBA",
         "status": "Submitted", "submitted": "2027-02-17"},
        {"student": "Sara Hosseini", "country": "Iran", "programme": "Psychology",
         "status": "Accepted", "submitted": "2027-02-20"},
        {"student": "Omar Hassan", "country": "Egypt", "programme": "Finance and Markets",
         "status": "Enrolled", "submitted": "2027-02-23"},
        {"student": "Elif Yilmaz", "country": "Turkey", "programme": "Communication Design",
         "status": "Rejected", "submitted": "2027-03-01"},
        {"student": "Youssef Benali", "country": "Morocco", "programme": "Digital Marketing",
         "status": "Withdrawn", "submitted": "2027-03-04"},
        {"student": "Li Wei", "country": "China", "programme": "Architecture",
         "status": "In review", "submitted": "2027-03-09"},
        {"student": "Elira Hoxha", "country": "Albania",
         "programme": "Political Science and International Relations",
         "status": "Offer", "submitted": "2027-03-12"},
    ],
}


def strongest(statuses: list[str]) -> str:
    """The strongest status of a student's applications."""
    return min(statuses, key=STATUS_PRIORITY.index)


def _strongest_index(statuses: list[str]) -> int:
    # Ties (only possible between Withdrawn rows) go to the first one.
    return min(range(len(statuses)), key=lambda i: (STATUS_PRIORITY.index(statuses[i]), i))


def _week_no(d: dt.date) -> int:
    return d.isocalendar()[1]


def _il(n: int) -> str:
    """Italian article for a percentage: l'8%, l'11%, il 12%."""
    return "l'" if n in (8, 11) or 80 <= n <= 89 else "il "


def _pct(part: int, whole: int) -> int:
    return round(100 * part / whole)


def build_dataset(seed: int = SEED) -> dict:
    rng = random.Random(seed)
    prog_ids = [p[0] for p in PROGRAMMES]
    prog_weights = [p[5] for p in PROGRAMMES]
    span = (TODAY - WINDOW_START).days

    # ---- students and their applications
    students = []
    for n in range(N_STUDENTS):
        cen, _, _ = rng.choices(COUNTRIES, weights=[c[2] for c in COUNTRIES])[0]
        main = rng.choices(STATUS_PRIORITY, weights=STATUS_WEIGHTS)[0]
        n_apps = 1
        if rng.random() < 0.15:
            n_apps = 2 if rng.random() < 0.75 else 3
        progs = []
        while len(progs) < n_apps:
            p = rng.choices(prog_ids, weights=prog_weights)[0]
            if p not in progs:
                progs.append(p)
        weaker = STATUS_PRIORITY[STATUS_PRIORITY.index(main) + 1:] or ["Withdrawn"]
        statuses = [main] + [rng.choice(weaker) for _ in range(n_apps - 1)]
        rng.shuffle(statuses)
        top = _strongest_index(statuses)
        dates = []
        for i in range(n_apps):
            frac = rng.betavariate(1.5, 1.6)
            if i == top and statuses[i] in ("Enrolled", "Accepted"):
                frac *= 0.75  # people who got in applied earlier
            dates.append(WINDOW_START + dt.timedelta(days=int(frac * span)))
        deferred = None
        if statuses[top] == "Accepted" and rng.random() < 0.25:
            deferred = top
        enrol_date = None
        if statuses[top] == "Enrolled":
            enrol_date = min(TODAY, dates[top] + dt.timedelta(days=rng.randint(14, 56)))
        students.append({
            "student_id": f"S{n + 1:04d}", "country": cen,
            "advisor": rng.choice(ADVISORS), "progs": progs, "statuses": statuses,
            "dates": dates, "top": top, "deferred": deferred, "enrol_date": enrol_date,
        })

    # The current week is in progress: a few late applications land by TODAY.
    week_start = TODAY - dt.timedelta(days=TODAY.weekday())
    late_rng = random.Random(seed + 1)
    open_single = [s for s in students
                   if len(s["progs"]) == 1 and s["statuses"][0] in ("Submitted", "In review")]
    for s in late_rng.sample(open_single, 3):
        s["dates"][0] = week_start + dt.timedelta(days=late_rng.randint(0, (TODAY - week_start).days))

    rows = []
    for s in students:
        for i, p in enumerate(s["progs"]):
            rows.append({
                "student_id": s["student_id"], "programme_id": p,
                "country": s["country"], "national": s["country"] == "Italy",
                "status": s["statuses"][i], "submitted": s["dates"][i].isoformat(),
                "advisor": s["advisor"],
                "deferred_to": "2028/29" if s["deferred"] == i else None,
            })
    rows.sort(key=lambda r: (r["submitted"], r["student_id"], r["programme_id"]))
    for i, r in enumerate(rows):
        r["app_id"] = f"A{i + 1:05d}"

    # ---- student-level counts (one application per student)
    final = [strongest(s["statuses"]) for s in students]
    enrolled = final.count("Enrolled")
    accepted = enrolled + final.count("Accepted")
    offers = accepted + final.count("Offer")
    deferrals = sum(1 for s in students if s["deferred"] is not None)
    n_students = len(students)

    # ---- programmes: targets derived so enrolment lands near 72.5% of target
    prog_enrolled = {p: 0 for p in prog_ids}
    for s, f in zip(students, final):
        if f == "Enrolled":
            prog_enrolled[s["progs"][s["top"]]] += 1
    targets = {}
    for p in prog_ids:
        r = rng.uniform(0.58, 0.88)
        targets[p] = max(5, 5 * round(prog_enrolled[p] / r / 5))
    wanted = 5 * round(enrolled / 0.725 / 5)
    biggest = max(prog_ids, key=lambda p: targets[p])
    targets[biggest] += wanted - sum(targets.values())
    total_target = sum(targets.values())
    programmes = [{"id": p[0], "name_it": p[1], "name_en": p[2], "level": p[3],
                   "target": targets[p[0]], "fee_eur": p[4]} for p in PROGRAMMES]
    fee_of = {p[0]: p[4] for p in PROGRAMMES}

    # ---- countries
    country_it = {c[0]: c[1] for c in COUNTRIES}
    countries = []
    for cen in country_it:
        mine = [f for s, f in zip(students, final) if s["country"] == cen]
        if mine:
            countries.append({"country_it": country_it[cen], "country_en": cen,
                              "students": len(mine), "enrolled": mine.count("Enrolled"),
                              "national": cen == "Italy"})
    countries.sort(key=lambda c: (-c["students"], c["country_en"]))

    # ---- fees and deferrals (per programme of the strongest application)
    fees, deferral_rows = [], []
    for p in prog_ids:
        mine = [(s, f) for s, f in zip(students, final) if s["progs"][s["top"]] == p]
        paying = sum(1 for s, f in mine
                     if f == "Enrolled" or (f == "Accepted" and s["deferred"] is None))
        fees.append({"programme_id": p, "students": paying, "fee_eur": fee_of[p],
                     "expected_eur": paying * fee_of[p]})
        d = sum(1 for s, f in mine if s["deferred"] is not None)
        if d:
            deferral_rows.append({"programme_id": p, "students": d})

    # ---- advisors
    advisors = []
    for a in ADVISORS:
        open_cases = sum(1 for s, f in zip(students, final)
                         if s["advisor"] == a and f in OPEN_STATUSES)
        advisors.append({"advisor": a, "open_cases": open_cases,
                         "decided_this_week": rng.randint(3, 14)})

    # ---- weekly cumulative series
    first_sub = [_week_no(min(s["dates"])) for s in students]
    enrol_wk = [_week_no(s["enrol_date"]) for s in students if s["enrol_date"]]
    last_year = round(n_students * 0.90)
    weekly = []
    for i, w in enumerate(range(FIRST_WEEK, LAST_WEEK + 1)):
        cum = sum(1 for x in first_sub if x <= w)
        frac = cum / n_students
        weekly.append({
            "week": f"2027-W{w:02d}",
            "applications_cum": cum,
            "enrolled_cum": sum(1 for x in enrol_wk if x <= w),
            "target_cum": round(total_target * ((i + 1) / 26) ** 1.15),
            "applications_cum_last_year": round(last_year * frac ** 0.9),
        })

    # ---- key points
    top_intl = next(c for c in countries if not c["national"])
    nat = sum(c["students"] for c in countries if c["national"])
    pending = final.count("Offer")
    growth = _pct(n_students - last_year, last_year)
    done = _pct(enrolled, total_target)
    kp_en = [
        f"{n_students} students have applied so far ({len(rows)} applications in total; "
        f"each student is counted once), {growth}% more than at this point last year.",
        f"{enrolled} are already enrolled against a target of {total_target}, "
        f"which is {done}% of the way there.",
        f"{_pct(nat, n_students)}% of applicants are Italian; the largest international "
        f"source is {top_intl['country_en']} with {top_intl['students']} students.",
        f"{deferrals} accepted students have deferred to 2028/29 and {pending} offers "
        f"are still waiting for a reply.",
    ]
    pari = "all'" if _il(done) == "l'" else "al "
    kp_it = [
        f"{n_students} studenti hanno presentato domanda finora ({len(rows)} candidature in "
        f"totale; ogni studente è contato una volta), {_il(growth)}{growth}% in più rispetto allo "
        f"stesso punto dell'anno scorso.",
        f"{enrolled} sono già iscritti su un obiettivo di {total_target}, pari "
        f"{pari}{done}% del traguardo.",
        f"{_il(_pct(nat, n_students)).capitalize()}{_pct(nat, n_students)}% dei candidati è italiano; primo paese estero: "
        f"{top_intl['country_it']}, con {top_intl['students']} studenti.",
        f"{deferrals} studenti accettati hanno rinviato al 2028/29 e {pending} offerte "
        f"attendono ancora una risposta.",
    ]

    return {
        "meta": {"seed": seed, "generated": TODAY.isoformat(),
                 "intake_it": "A.A. 2027/28", "intake_en": "Intake 2027/28"},
        "programmes": programmes,
        "applications": rows,
        "summary": {"applications": n_students, "students": n_students,
                    "offers": offers, "accepted": accepted, "enrolled": enrolled,
                    "deferrals": deferrals, "target": total_target,
                    "applications_last_year": last_year},
        "weekly": weekly,
        "countries": countries,
        "funnel": {"applications": n_students, "offers": offers,
                   "accepted": accepted, "enrolled": enrolled},
        "advisors": advisors,
        "fees": fees,
        "deferrals": deferral_rows,
        "key_points_it": kp_it,
        "key_points_en": kp_en,
        "before_after": BEFORE_AFTER,
    }


def main() -> None:
    data = build_dataset()
    with open(Path(__file__).parent / OUT, "w", encoding="utf-8") as fh:
        fh.write(json.dumps(data, indent=1, sort_keys=True, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    main()
