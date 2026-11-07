"""Build demo.html: the self-contained demo admissions dashboard.

render(data) turns the dataset from demo_data.build_dataset() into one HTML
document (inline CSS, inline SVG, one <script id="app">, no external requests).
Italian text is rendered; every UI word carries data-i18n (keys in
demo_i18n.LABELS) and every data name carries data-it / data-en, so the
language switch can swap them later. main() writes demo.html beside this file.
"""

from __future__ import annotations

import datetime as dt
import json
import os
import re
from html import escape
from typing import Dict, List, Optional, Sequence, Tuple

import demo_charts as charts
import demo_data
import demo_i18n

TABS = demo_i18n.TABS
FLAGGED = {"beforeafter"}

LEVELS: List[Tuple[str, Tuple[str, str], Tuple[str, str]]] = [
    # (dataset level, full name it/en, short heatmap column it/en)
    ("Laurea", ("Laurea", "Bachelor's"), ("L", "BA")),
    ("Laurea Magistrale", ("Laurea Magistrale", "Master's"), ("LM", "MA")),
    ("MBA", ("MBA", "MBA"), ("MBA", "MBA")),
]

REGIONS: List[Tuple[Tuple[str, str], List[str]]] = [
    (("Italia", "Italy"), ["Italy"]),
    (("Europa", "Europe"), ["Albania", "Ukraine", "Turkey"]),
    (("Nord Africa", "North Africa"), ["Morocco", "Egypt"]),
    (("Africa subsahariana", "Sub-Saharan Africa"), ["Nigeria", "Ghana", "Kenya"]),
    (("Asia", "Asia"), ["India", "Pakistan", "Bangladesh", "Nepal", "Iran", "China", "Vietnam"]),
    (("America Latina", "Latin America"), ["Brazil", "Colombia"]),
]
OTHER_REGION = ("Altri", "Other")
OTHER_COUNTRIES = ("Altri paesi", "Other countries")
MONTHS_IT = ["gen", "feb", "mar", "apr", "mag", "giu", "lug", "ago", "set", "ott", "nov", "dic"]
MONTHS_EN = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

STATUS_IT = {
    "Submitted": "Inviata", "In review": "In valutazione", "Offer": "Offerta",
    "Accepted": "Accettata", "Enrolled": "Iscritto", "Rejected": "Respinta",
    "Withdrawn": "Ritirata",
}

SANS = '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif'
MONO = 'ui-monospace, SFMono-Regular, Menlo, Consolas, "Liberation Mono", monospace'
SERIF = 'Georgia, "Times New Roman", Times, serif'

DEFAULT_STYLE = "exec-light"

# Four looks, one token set each. Charts read only these variables, so every
# style recolours them too. Same keys in every style (tested).
STYLES: Dict[str, Dict[str, str]] = {
    "exec-light": {
        "bg": "#F3F4F5",
        "panel": "#FFFFFF",
        "panel-2": "#F7F8F9",
        "ink": "#15191E",
        "ink-2": "#5E6671",
        "line": "#DCE0E4",
        "accent": "#0E7C86",
        "accent-2": "#7DB9BF",
        "accent-soft": "#E2F0F1",
        "kpi-bg": "#15191E",
        "kpi-ink": "#FFFFFF",
        "font-body": SANS,
        "font-num": SANS,
        "radius": "10px",
        "shadow": "0 1px 2px rgba(21, 25, 30, 0.05)",
        "glow": "none",
    },
    "exec-dark": {
        "bg": "#0F161E",
        "panel": "#18212B",
        "panel-2": "#1F2A36",
        "ink": "#E8EDF2",
        "ink-2": "#A3AFBB",
        "line": "#2D3A47",
        "accent": "#3FC1C9",
        "accent-2": "#5B8F96",
        "accent-soft": "#173A41",
        "kpi-bg": "#0B1117",
        "kpi-ink": "#F2F5F8",
        "font-body": SANS,
        "font-num": SANS,
        "radius": "10px",
        "shadow": "0 1px 3px rgba(0, 0, 0, 0.45)",
        "glow": "none",
    },
    "command": {
        "bg": "#050A13",
        "panel": "#0A1422",
        "panel-2": "#0F1D31",
        "ink": "#E3F6FB",
        "ink-2": "#8EB4C6",
        "line": "#1B4558",
        "accent": "#22D3EE",
        "accent-2": "#3E8FA6",
        "accent-soft": "#0B2A3A",
        "kpi-bg": "#03070D",
        "kpi-ink": "#E3F6FB",
        "font-body": SANS,
        "font-num": MONO,
        "radius": "4px",
        "shadow": "0 0 0 1px rgba(34, 211, 238, 0.06)",
        "glow": "0 0 18px rgba(34, 211, 238, 0.16)",
    },
    "editorial": {
        "bg": "#F5EFE4",
        "panel": "#FBF8F2",
        "panel-2": "#F1E9DB",
        "ink": "#2A211B",
        "ink-2": "#66574A",
        "line": "#DDCFBB",
        "accent": "#A0522D",
        "accent-2": "#D2A582",
        "accent-soft": "#F1E1D2",
        "kpi-bg": "#FBF8F2",
        "kpi-ink": "#2A211B",
        "font-body": SANS,
        "font-num": SERIF,
        "radius": "2px",
        "shadow": "none",
        "glow": "none",
    },
}


# ---------------------------------------------------------------- helpers

def _q(s: object) -> str:
    return escape(str(s), quote=True)


def _t(key: str) -> str:
    return escape(demo_i18n.t(key, "it"))


def _ui(key: str, tag: str = "span", cls: str = "") -> str:
    c = f' class="{cls}"' if cls else ""
    return f'<{tag}{c} data-i18n="{_q(key)}">{_t(key)}</{tag}>'


def _name(pair: Tuple[str, str], tag: str = "span", cls: str = "") -> str:
    c = f' class="{cls}"' if cls else ""
    return f'<{tag}{c} data-it="{_q(pair[0])}" data-en="{_q(pair[1])}">{escape(pair[0])}</{tag}>'


def _pct(part: float, whole: float) -> int:
    return int(round(100.0 * part / whole)) if whole else 0


def _int_it(n: int) -> str:
    return f"{n:,}".replace(",", ".")


def _eur(n: int) -> Tuple[str, str]:
    return f"{_int_it(n)} €", f"€{n:,}"


def _signed(n: int) -> str:
    if n > 0:
        return f"+{n}"
    if n < 0:
        return f"−{abs(n)}"
    return "0"


def _week_label(iso_week: str) -> Tuple[str, str]:
    """'2027-W28' -> Monday of that ISO week as ('12 lug', '12 Jul')."""
    year, week = iso_week.split("-W")
    d = dt.date.fromisocalendar(int(year), int(week), 1)
    return f"{d.day} {MONTHS_IT[d.month - 1]}", f"{d.day} {MONTHS_EN[d.month - 1]}"


def _bold_first_number(sentence: str) -> str:
    m = re.search(r"\d[\d.,]*%?", sentence)
    if not m:
        return escape(sentence)
    return (escape(sentence[:m.start()]) + "<b>" + escape(m.group(0)) + "</b>"
            + escape(sentence[m.end():]))


def _card(title_key: str, sub_key: str, body: str, span: int = 1, cls: str = "") -> str:
    classes = "card" + (f" span-{span}" if span > 1 else "") + (f" {cls}" if cls else "")
    return (f'<article class="{classes}">'
            f'{_ui(title_key, "h3")}{_ui(sub_key, "p", "card-sub")}'
            f'<div class="card-body">{body}</div></article>')


def _table(head: Sequence[str], rows: Sequence[str], cls: str = "") -> str:
    c = f' class="{cls}"' if cls else ""
    th = "".join(head)
    return (f'<div class="table-wrap"><table{c}><thead><tr>{th}</tr></thead>'
            f'<tbody>{"".join(rows)}</tbody></table></div>')


def _th(key: str, num: bool = False) -> str:
    c = ' class="num"' if num else ""
    return f'<th{c} data-i18n="{_q(key)}">{_t(key)}</th>'


# ---------------------------------------------------------------- data views

def _top_apps(applications: Sequence[dict]) -> List[dict]:
    """One application per student: the one with the strongest status."""
    by: Dict[str, List[dict]] = {}
    for a in applications:
        by.setdefault(a["student_id"], []).append(a)
    order = demo_data.STATUS_PRIORITY.index
    return [min(by[sid], key=lambda a: order(a["status"])) for sid in sorted(by)]


def _views(data: dict) -> dict:
    progs = data["programmes"]
    prog = {p["id"]: p for p in progs}
    tops = _top_apps(data["applications"])
    level_of = {p["id"]: p["level"] for p in progs}

    applicants = {p["id"]: 0 for p in progs}
    enrolled = {p["id"]: 0 for p in progs}
    intl = {p["id"]: 0 for p in progs}
    by_level = {lv[0]: 0 for lv in LEVELS}
    for a in tops:
        pid = a["programme_id"]
        applicants[pid] += 1
        by_level[level_of[pid]] += 1
        if a["status"] == "Enrolled":
            enrolled[pid] += 1
        if not a["national"]:
            intl[pid] += 1

    region_of = {c: i for i, (_, cs) in enumerate(REGIONS) for c in cs}
    regions = [r for r, _ in REGIONS]
    cells = [[0] * len(LEVELS) for _ in REGIONS]
    level_idx = {lv[0]: j for j, lv in enumerate(LEVELS)}
    for a in tops:
        i = region_of.get(a["country"])
        if i is None:
            if len(regions) == len(REGIONS):
                regions.append(OTHER_REGION)
                cells.append([0] * len(LEVELS))
            i = len(REGIONS)
        cells[i][level_idx[level_of[a["programme_id"]]]] += 1

    return {"prog": prog, "applicants": applicants, "enrolled": enrolled, "intl": intl,
            "by_level": by_level, "regions": regions, "region_cells": cells}


def _pname(p: dict) -> Tuple[str, str]:
    return p["name_it"], p["name_en"]


# ---------------------------------------------------------------- panels

def _kpi(label_key: str, value: str, sub: str) -> str:
    return (f'<div class="kpi">{_ui(label_key, "div", "kpi-label")}'
            f'<div class="kpi-value">{value}</div>'
            f'<div class="kpi-sub">{sub}</div></div>')


def _kpi_strip(data: dict) -> str:
    s = data["summary"]
    nat = sum(c["students"] for c in data["countries"] if c["national"])
    intl = s["students"] - nat
    abroad = sum(1 for c in data["countries"] if not c["national"] and c["students"] > 0)
    growth = _pct(s["students"] - s["applications_last_year"], s["applications_last_year"])
    num = lambda v: f'<span class="kpi-num">{v}</span> '
    kpis = [
        _kpi("kpi.students", str(s["students"]),
             num(_signed(growth) + "%") + _ui("kpi.sub.vs_last_year")),
        _kpi("kpi.offers", str(s["offers"]),
             num(f'{_pct(s["offers"], s["students"])}%') + _ui("kpi.sub.of_students")),
        _kpi("kpi.accepted", str(s["accepted"]),
             num(f'{_pct(s["accepted"], s["offers"])}%') + _ui("kpi.sub.of_offers")),
        _kpi("kpi.enrolled", str(s["enrolled"]),
             num(f'{_pct(s["enrolled"], s["target"])}%') + _ui("kpi.sub.of_target")
             + f' <span class="kpi-num">{s["target"]}</span>'),
        _kpi("kpi.deferrals", str(s["deferrals"]),
             num(f'{_pct(s["deferrals"], s["accepted"])}%') + _ui("kpi.sub.of_accepted_deferred")),
        _kpi("kpi.international", str(intl), num(str(abroad)) + _ui("kpi.sub.countries")),
    ]
    return f'<div class="kpis">{"".join(kpis)}</div>'


def _key_points(data: dict) -> str:
    items = []
    for it, en in zip(data["key_points_it"], data["key_points_en"]):
        items.append(f'<li><span data-lang="it">{_bold_first_number(it)}</span>'
                     f'<span data-lang="en" hidden>{_bold_first_number(en)}</span></li>')
    return (f'<article class="card keypoints">{_ui("ui.key_points", "h3")}'
            f'<ol>{"".join(items)}</ol></article>')


def _level_donut(v: dict, students: int) -> str:
    parts = [(full, v["by_level"][lv]) for lv, full, _ in LEVELS]
    return charts.donut(parts, str(students))


# Overview cards, shared by the Overview tab and the printed report.

def _enrolled_card(data: dict, span: int = 1) -> str:
    w = data["weekly"]
    return _card("card.enrolled_vs_target", "card.cumulative",
                 charts.line_vs_target([r["enrolled_cum"] for r in w], [r["target_cum"] for r in w],
                                       series_key="kpi.enrolled"), span=span)


def _top_countries_card(data: dict) -> str:
    top = [((c["country_it"], c["country_en"]), c["students"]) for c in data["countries"][:6]]
    return _card("card.top_countries", "card.top_countries.sub", charts.hbars(top, data["summary"]["students"]))


def _level_card(data: dict, v: dict) -> str:
    return _card("card.by_level", "card.by_level.sub", _level_donut(v, data["summary"]["students"]))


def _overview(data: dict, v: dict) -> str:
    return (_kpi_strip(data)
            + '<div class="grid">'
            + _enrolled_card(data, span=2)
            + _key_points(data)
            + _top_countries_card(data)
            + _level_card(data, v)
            + _card("card.split", "card.split.sub", _natint_donut(data))
            + "</div>")


def _report(data: dict, v: dict) -> str:
    """One A4 landscape page for the board: shown only when printing."""
    gen = dt.date.fromisoformat(data["meta"]["generated"])
    as_of = (f"{gen.day} {MONTHS_IT[gen.month - 1]} {gen.year}",
             f"{gen.day} {MONTHS_EN[gen.month - 1]} {gen.year}")
    sep = " · "
    return ('<section id="report" class="print-only">'
            '<div class="report-head">'
            f'<span class="report-uni" data-uni-name>{_t("uni.default_name")}</span>'
            f'{_ui("report.title", "span", "report-title")}</div>'
            + _kpi_strip(data)
            + '<div class="report-grid">'
            + _enrolled_card(data)
            + _top_countries_card(data)
            + _level_card(data, v)
            + _key_points(data)
            + "</div>"
            + f'<p class="source">{_ui("ui.source_line")}{sep}{_ui("ui.demo_notice")}{sep}'
            + f'{_ui("report.as_of")} {_name(as_of)}</p>'
            + "</section>")


def _natint_donut(data: dict) -> str:
    s = data["summary"]
    nat = sum(c["students"] for c in data["countries"] if c["national"])
    return charts.donut([(("Italiani", "Italian"), nat),
                         (("Internazionali", "International"), s["students"] - nat)], str(s["students"]))


def _weekly(data: dict) -> str:
    w = data["weekly"]
    new = [w[0]["applications_cum"]] + [b["applications_cum"] - a["applications_cum"]
                                       for a, b in zip(w, w[1:])]
    rows = []
    for i in range(max(1, len(w) - 8), len(w)):
        ch = new[i] - new[i - 1]
        cls = "up" if ch > 0 else ("down" if ch < 0 else "flat")
        cell = _name(_week_label(w[i]["week"]), "span")
        if i == len(w) - 1:
            cell += ' <small class="wip" data-i18n="wk.in_progress">%s</small>' % escape(demo_i18n.t("wk.in_progress", "it"))
        rows.append(f'<tr class="wk"><td>{cell}</td>'
                    f'<td class="num">{new[i]}</td>'
                    f'<td class="num {cls}">{_signed(ch)}</td></tr>')
    table = _table([_th("col.week"), _th("col.new_apps", True), _th("col.change", True)], rows)
    return ('<div class="grid">'
            + _card("card.apps_vs_last_year", "card.cumulative",
                    charts.line_vs_target([r["applications_cum"] for r in w], [],
                                          [r["applications_cum_last_year"] for r in w]))
            + _card("card.enrolled_vs_target", "card.cumulative",
                    charts.line_vs_target([r["enrolled_cum"] for r in w], [r["target_cum"] for r in w],
                                          series_key="kpi.enrolled"))
            + _card("card.last_weeks", "card.last_weeks.sub", table)
            + "</div>")


def _countries(data: dict, v: dict) -> str:
    cs = data["countries"]
    total = data["summary"]["students"]
    rows = [((c["country_it"], c["country_en"]), c["students"]) for c in cs[:12]]
    rest = sum(c["students"] for c in cs[12:])
    if rest:
        rows.append((OTHER_COUNTRIES, rest))
    cols = [short for _, _, short in LEVELS]
    return ('<div class="grid">'
            + _card("card.countries", "card.countries.sub", charts.hbars(rows, total), span=2)
            + _card("card.region_level", "card.region_level.sub",
                    charts.heatmap(v["regions"], cols, v["region_cells"]))
            + "</div>")


def _programmes(data: dict, v: dict) -> str:
    level_name = {lv: full for lv, full, _ in LEVELS}
    rows = []
    for p in data["programmes"]:
        pid = p["id"]
        pct = _pct(v["enrolled"][pid], p["target"])
        rows.append(f'<tr>{_name(_pname(p), "td")}{_name(level_name[p["level"]], "td")}'
                    f'<td class="num">{v["applicants"][pid]}</td>'
                    f'<td class="num">{v["enrolled"][pid]}</td>'
                    f'<td class="num">{p["target"]}</td>'
                    f'<td class="progress"><span class="bar"><i style="width:{min(pct, 100)}%"></i></span>'
                    f'<span class="pct">{pct}%</span></td></tr>')
    tot_app = sum(v["applicants"].values())
    tot_enr = sum(v["enrolled"].values())
    tot_tgt = sum(p["target"] for p in data["programmes"])
    pct = _pct(tot_enr, tot_tgt)
    rows.append(f'<tr class="total">{_ui("chart.total", "td")}<td></td>'
                f'<td class="num">{tot_app}</td><td class="num">{tot_enr}</td>'
                f'<td class="num">{tot_tgt}</td>'
                f'<td class="progress"><span class="bar"><i style="width:{min(pct, 100)}%"></i></span>'
                f'<span class="pct">{pct}%</span></td></tr>')
    head = [_th("col.programme"), _th("col.level"), _th("col.applicants", True),
            _th("kpi.enrolled", True), _th("kpi.target", True), _th("col.progress")]
    return ('<div class="grid">'
            + _card("card.programmes", "card.programmes.sub", _table(head, rows, "wide"), span=3)
            + "</div>")


def _natint(data: dict, v: dict) -> str:
    total_intl = sum(v["intl"].values())
    rows = sorted(((_pname(v["prog"][pid]), n) for pid, n in v["intl"].items()),
                  key=lambda r: -r[1])
    return ('<div class="grid">'
            + _card("card.split", "card.split.sub", _natint_donut(data))
            + _card("card.intl_by_programme", "card.intl_by_programme.sub",
                    charts.hbars(rows, total_intl), span=2)
            + "</div>")


def _funnel(data: dict) -> str:
    f = data["funnel"]
    steps = [(("Candidati", "Applicants"), f["applications"]), (("Offerte", "Offers"), f["offers"]),
             (("Accettati", "Accepted"), f["accepted"]), (("Iscritti", "Enrolled"), f["enrolled"])]
    conv = [("conv.offer", _pct(f["offers"], f["applications"])),
            ("conv.accept", _pct(f["accepted"], f["offers"])),
            ("conv.enrol", _pct(f["enrolled"], f["accepted"])),
            ("conv.overall", _pct(f["enrolled"], f["applications"]))]
    items = "".join(f'<li>{_ui(k)}<b class="conv-num">{p}%</b></li>' for k, p in conv)
    return ('<div class="grid">'
            + _card("card.funnel", "card.funnel.sub", charts.funnel(steps), span=2)
            + _card("card.conversion", "card.conversion.sub", f'<ul class="conv">{items}</ul>')
            + "</div>")


def _deferrals(data: dict, v: dict) -> str:
    rows = sorted(((_pname(v["prog"][d["programme_id"]]), d["students"]) for d in data["deferrals"]),
                  key=lambda r: -r[1])
    return ('<div class="grid">'
            + _card("card.deferrals", "card.deferrals.sub",
                    charts.hbars(rows, data["summary"]["deferrals"]), span=2)
            + "</div>")


def _advisors(data: dict) -> str:
    adv = data["advisors"]
    open_rows = sorted(((a["advisor"], a["open_cases"]) for a in adv), key=lambda r: -r[1])
    dec_rows = sorted(((a["advisor"], a["decided_this_week"]) for a in adv), key=lambda r: -r[1])
    return ('<div class="grid">'
            + _card("card.open_cases", "card.open_cases.sub",
                    charts.hbars(open_rows, sum(r[1] for r in open_rows)))
            + _card("card.decided", "card.decided.sub",
                    charts.hbars(dec_rows, sum(r[1] for r in dec_rows)))
            + "</div>")


def _fees(data: dict, v: dict) -> str:
    rows = []
    for fr in data["fees"]:
        p = v["prog"][fr["programme_id"]]
        rows.append(f'<tr>{_name(_pname(p), "td")}<td class="num">{fr["students"]}</td>'
                    f'{_name(_eur(fr["fee_eur"]), "td", "num")}'
                    f'{_name(_eur(fr["expected_eur"]), "td", "num")}</tr>')
    tot_s = sum(fr["students"] for fr in data["fees"])
    tot_e = sum(fr["expected_eur"] for fr in data["fees"])
    rows.append(f'<tr class="total">{_ui("chart.total", "td")}<td class="num">{tot_s}</td><td></td>'
                f'{_name(_eur(tot_e), "td", "num")}</tr>')
    head = [_th("col.programme"), _th("kpi.students", True), _th("col.fee", True), _th("col.expected", True)]
    return ('<div class="grid">'
            + _card("card.fees", "card.fees.sub", _table(head, rows, "wide"), span=3)
            + "</div>")


def _beforeafter(data: dict) -> str:
    ba = data["before_after"]
    cols = ["student", "country", "programme", "status", "submitted"]
    head = [_th("col." + c) for c in cols]
    raw_rows = ["<tr>" + "".join(f'<td class="raw">{escape(r[c])}</td>' for c in cols) + "</tr>"
                for r in ba["raw"]]
    country = {c["country_en"]: (c["country_it"], c["country_en"]) for c in data["countries"]}
    prog = {p["name_en"]: _pname(p) for p in data["programmes"]}
    clean_rows = []
    for r in ba["clean"]:
        cells = [f'<td>{escape(r["student"])}</td>',
                 _name(country.get(r["country"], (r["country"], r["country"])), "td"),
                 _name(prog.get(r["programme"], (r["programme"], r["programme"])), "td"),
                 _name((STATUS_IT.get(r["status"], r["status"]), r["status"]), "td"),
                 f'<td>{escape(r["submitted"])}</td>']
        clean_rows.append("<tr>" + "".join(cells) + "</tr>")
    return ('<div class="grid">'
            + _card("card.raw", "card.raw.sub", _table(head, raw_rows, "wide"), span=3)
            + _card("card.clean", "card.clean.sub", _table(head, clean_rows, "wide"), span=3)
            + "</div>")


def _panel(tid: str, body: str, on: bool = False) -> str:
    extra = ""
    if on:
        extra += " data-on"
    if tid in FLAGGED:
        extra += f' hidden data-flag="{tid}"'
    return (f'<section class="panel" id="{tid}" role="tabpanel" aria-labelledby="tab-{tid}"{extra}>'
            f'<div class="panel-head">{_ui(f"tab.{tid}.title", "h2")}{_ui(f"tab.{tid}.sub", "p")}</div>'
            f'{body}'
            f'{_ui("ui.source_line", "p", "source")}'
            f'</section>')


def _style_control() -> str:
    opts = "".join(
        f'<option value="{sid}"{" selected" if sid == DEFAULT_STYLE else ""} '
        f'data-i18n="style.{sid}">{_t("style." + sid)}</option>'
        for sid in STYLES)
    return (f'<label class="ctl" for="style-select">{_ui("ui.style")}'
            f'<select id="style-select">{opts}</select></label>')


def _lang_control() -> str:
    btns = "".join(
        f'<button type="button" data-setlang="{lg}" aria-pressed="{"true" if lg == "it" else "false"}">'
        f'{lg.upper()}</button>' for lg in ("it", "en"))
    return (f'<span class="ctl"><span id="lang-label" data-i18n="ui.language">{_t("ui.language")}</span>'
            f'<span class="seg" role="group" aria-labelledby="lang-label">{btns}</span></span>')


def _report_button() -> str:
    return (f'<button type="button" class="btn" id="report-btn" '
            f'data-i18n="ui.download_report">{_t("ui.download_report")}</button>')


def _tab_button(tid: str, on: bool) -> str:
    extra = f' hidden data-flag="{tid}"' if tid in FLAGGED else ""
    sel = "true" if on else "false"
    tabindex = "0" if on else "-1"
    return (f'<button data-tab="{tid}" id="tab-{tid}" type="button" role="tab" aria-controls="{tid}" '
            f'aria-selected="{sel}" tabindex="{tabindex}"{extra} data-i18n="tab.{tid}">{_t("tab." + tid)}</button>')


# ---------------------------------------------------------------- page

def _css() -> str:
    blocks = []
    for sid, toks in STYLES.items():
        sel = f':root,\n[data-style="{sid}"]' if sid == DEFAULT_STYLE else f'[data-style="{sid}"]'
        body = "\n".join(f"  --{k}: {val};" for k, val in toks.items())
        blocks.append(f"{sel} {{\n{body}\n}}")
    return "\n".join(blocks) + f"""
*, *::before, *::after {{ box-sizing: border-box; }}
[hidden] {{ display: none !important; }}
html {{ -webkit-text-size-adjust: 100%; }}
body {{ margin: 0; background: var(--bg); color: var(--ink); font-family: var(--font-body);
  font-size: 15px; line-height: 1.45; }}
.wrap {{ max-width: 1280px; margin: 0 auto; padding: 20px 24px 32px; }}
.top {{ display: flex; flex-wrap: wrap; align-items: flex-end; justify-content: space-between; gap: 12px 24px;
  padding-bottom: 14px; border-bottom: 1px solid var(--line); }}
.brand {{ min-width: 0; }}
#uni-name {{ margin: 0; font-size: 26px; line-height: 1.2; font-weight: 700; letter-spacing: -0.01em;
  overflow-wrap: anywhere; }}
.meta {{ display: flex; flex-wrap: wrap; align-items: center; gap: 8px; margin-top: 6px; color: var(--ink-2);
  font-size: 13px; }}
.tag {{ display: inline-block; padding: 2px 8px; border-radius: 999px; background: var(--accent-soft);
  color: var(--accent); font-weight: 600; font-size: 12px; }}
.controls {{ display: flex; flex-wrap: wrap; gap: 8px; }}
.ctl {{ display: inline-flex; align-items: center; gap: 6px; min-width: 0; color: var(--ink-2);
  font-size: 12px; font-weight: 600; }}
.ctl select {{ font: inherit; font-size: 13px; font-weight: 600; color: var(--ink); background: var(--panel);
  border: 1px solid var(--line); border-radius: 6px; padding: 5px 8px; max-width: 100%; cursor: pointer; }}
.seg {{ display: inline-flex; border: 1px solid var(--line); border-radius: 6px; overflow: hidden; }}
.seg button {{ font: inherit; font-size: 13px; font-weight: 600; border: 0; background: var(--panel);
  color: var(--ink-2); padding: 5px 10px; cursor: pointer; }}
.seg button + button {{ border-left: 1px solid var(--line); }}
.seg button[aria-pressed="true"] {{ background: var(--accent); color: var(--panel); }}
.seg button:focus-visible {{ outline: 2px solid var(--accent); outline-offset: -2px; }}
.ctl select:focus-visible {{ outline: 2px solid var(--accent); outline-offset: 1px; }}
.notice {{ margin: 10px 0 0; color: var(--ink-2); font-size: 12px; }}
.tabs {{ display: flex; gap: 4px; margin: 16px 0 18px; overflow-x: auto; border-bottom: 1px solid var(--line);
  scrollbar-width: thin; }}
.tabs button {{ flex: 0 0 auto; white-space: nowrap; border: 0; background: none; color: var(--ink-2);
  font: inherit; font-size: 14px; font-weight: 600; padding: 10px 12px; cursor: pointer;
  border-bottom: 2px solid transparent; margin-bottom: -1px; }}
.tabs button:hover {{ color: var(--ink); }}
.tabs button[aria-selected="true"] {{ color: var(--accent); border-bottom-color: var(--accent); }}
.tabs button:focus-visible {{ outline: 2px solid var(--accent); outline-offset: -2px; }}
.panel {{ display: none; }}
.panel[data-on] {{ display: block; }}
.panel-head h2 {{ margin: 0; font-size: 19px; font-weight: 700; }}
.panel-head p {{ margin: 2px 0 14px; color: var(--ink-2); font-size: 13px; }}
.kpis {{ display: grid; grid-template-columns: repeat(6, minmax(0, 1fr)); gap: 1px;
  background: var(--kpi-bg); color: var(--kpi-ink); border-radius: var(--radius); overflow: hidden;
  margin-bottom: 16px; box-shadow: var(--shadow); }}
.kpi {{ padding: 14px 16px 16px; min-width: 0; }}
.kpi + .kpi {{ border-left: 1px solid rgba(255, 255, 255, 0.12); }}
.kpi-label {{ font-size: 12px; text-transform: uppercase; letter-spacing: 0.06em; opacity: 0.72; }}
.kpi-value {{ font-family: var(--font-num); font-size: 34px; line-height: 1.1; font-weight: 700;
  font-variant-numeric: tabular-nums; margin: 4px 0 4px; }}
.kpi-sub {{ font-size: 12px; opacity: 0.66; }}
.kpi-num {{ font-weight: 700; }}
.grid {{ display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 16px; }}
.card {{ background: var(--panel); border: 1px solid var(--line); border-radius: var(--radius);
  padding: 16px 18px; min-width: 0; box-shadow: var(--shadow); }}
.card h3 {{ margin: 0; font-size: 14px; font-weight: 700; }}
.card-sub {{ margin: 2px 0 12px; font-size: 12px; color: var(--ink-2); }}
.span-2 {{ grid-column: span 2; }}
.span-3 {{ grid-column: 1 / -1; }}
.card-body svg {{ display: block; max-width: 100%; height: auto; }}
.keypoints {{ background: var(--accent-soft); border-color: transparent; }}
.keypoints h3 {{ color: var(--accent); }}
.keypoints ol {{ margin: 10px 0 0; padding-left: 20px; }}
.keypoints li {{ margin: 0 0 10px; font-size: 14px; }}
.keypoints b {{ font-family: var(--font-num); color: var(--ink); }}
.table-wrap {{ overflow-x: auto; -webkit-overflow-scrolling: touch; }}
table {{ width: 100%; border-collapse: collapse; font-size: 13px; }}
table.wide {{ min-width: 560px; }}
th {{ text-align: left; font-size: 11px; text-transform: uppercase; letter-spacing: 0.05em;
  color: var(--ink-2); font-weight: 600; padding: 6px 8px; border-bottom: 1px solid var(--line);
  white-space: nowrap; }}
td {{ padding: 7px 8px; border-bottom: 1px solid var(--line); vertical-align: middle; }}
.num {{ text-align: right; font-family: var(--font-num); font-variant-numeric: tabular-nums; white-space: nowrap; }}
small.wip {{ color: var(--ink-2); font-size: 0.8em; margin-left: 0.4em; }}
td.up {{ color: var(--accent); font-weight: 600; }}
td.down {{ color: var(--ink-2); font-weight: 600; }}
tr.total td {{ font-weight: 700; border-bottom: 0; border-top: 2px solid var(--ink); }}
td.raw {{ font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; font-size: 12px;
  white-space: pre; color: var(--ink-2); }}
.progress {{ white-space: nowrap; min-width: 140px; }}
.bar {{ display: inline-block; vertical-align: middle; width: 90px; height: 8px; border-radius: 4px;
  background: var(--line); overflow: hidden; }}
.bar i {{ display: block; height: 100%; background: var(--accent); border-radius: 4px; }}
.pct {{ display: inline-block; min-width: 42px; text-align: right; font-weight: 600; font-size: 12px;
  font-variant-numeric: tabular-nums; }}
.conv {{ list-style: none; margin: 0; padding: 0; }}
.conv li {{ display: flex; justify-content: space-between; align-items: baseline; gap: 12px;
  padding: 10px 0; border-bottom: 1px solid var(--line); font-size: 13px; color: var(--ink-2); }}
.conv li:last-child {{ border-bottom: 0; }}
.conv-num {{ font-family: var(--font-num); font-size: 22px; color: var(--ink); }}
.source {{ margin: 16px 0 0; font-size: 11px; color: var(--ink-2); }}
.btn {{ font: inherit; font-size: 13px; font-weight: 600; color: var(--panel); background: var(--accent);
  border: 1px solid var(--accent); border-radius: 6px; padding: 5px 10px; cursor: pointer; white-space: nowrap; }}
.btn:hover {{ filter: brightness(1.08); }}
.btn:focus-visible {{ outline: 2px solid var(--accent); outline-offset: 2px; }}
.print-only {{ display: none; }}
/* style: exec-dark */
[data-style="exec-dark"], [data-style="command"] {{ color-scheme: dark; }}
[data-style="exec-dark"] .kpis {{ border: 1px solid var(--line); }}
/* style: command */
[data-style="command"] body {{ background: radial-gradient(ellipse at 50% -10%, #0E2A44 0%, #071322 45%, var(--bg) 80%) fixed,
  var(--bg); }}
[data-style="command"] .card, [data-style="command"] .kpis {{ box-shadow: var(--shadow), var(--glow); }}
[data-style="command"] .card, [data-style="command"] .kpis {{ border: 1px solid var(--line); }}
[data-style="command"] .keypoints {{ border-color: var(--line); }}
[data-style="command"] .kpi + .kpi {{ border-left-color: var(--line); }}
[data-style="command"] .kpi-label, [data-style="command"] .card h3, [data-style="command"] th,
[data-style="command"] .tabs button, [data-style="command"] .tag, [data-style="command"] .ctl,
[data-style="command"] .source, [data-style="command"] .panel-head p {{ font-family: var(--font-num); }}
[data-style="command"] .card h3, [data-style="command"] .tabs button {{ text-transform: uppercase;
  letter-spacing: 0.08em; font-size: 12px; }}
[data-style="command"] .kpi-label {{ color: var(--accent); opacity: 1; }}
[data-style="command"] .kpi-value {{ text-shadow: 0 0 12px rgba(34, 211, 238, 0.45); }}
[data-style="command"] .tag {{ background: transparent; border: 1px solid var(--accent); }}
[data-style="command"] .tabs button[aria-selected="true"] {{ text-shadow: 0 0 8px rgba(34, 211, 238, 0.6); }}
[data-style="command"] .card-body polyline:last-of-type,
[data-style="command"] .bar i {{ filter: drop-shadow(0 0 4px rgba(34, 211, 238, 0.7)); }}
[data-style="command"] .bar i {{ box-shadow: var(--glow); }}
/* style: editorial */
[data-style="editorial"] #uni-name, [data-style="editorial"] .panel-head h2,
[data-style="editorial"] .card h3 {{ font-family: var(--font-num); font-weight: 400; letter-spacing: 0; }}
[data-style="editorial"] #uni-name {{ font-size: 30px; }}
[data-style="editorial"] .card h3 {{ font-size: 17px; }}
[data-style="editorial"] .kpis {{ border-radius: 0; border-top: 2px solid var(--ink); border-bottom: 1px solid var(--ink);
  background: var(--kpi-bg); }}
[data-style="editorial"] .kpi + .kpi {{ border-left-color: var(--line); }}
[data-style="editorial"] .kpi-label {{ color: var(--accent); opacity: 1; font-weight: 600; }}
[data-style="editorial"] .kpi-value {{ font-weight: 400; }}
[data-style="editorial"] .kpi-sub {{ opacity: 1; color: var(--ink-2); }}
[data-style="editorial"] .keypoints {{ border-color: var(--line); border-left: 3px solid var(--accent); }}
[data-style="editorial"] .conv-num {{ font-weight: 400; }}
[data-style="editorial"] .tag {{ border-radius: 2px; }}
{_print_css()}
@media (max-width: 1000px) {{
  .kpis {{ grid-template-columns: repeat(3, minmax(0, 1fr)); }}
  .kpi + .kpi {{ border-left: 0; }}
  .grid {{ grid-template-columns: repeat(2, minmax(0, 1fr)); }}
  .span-2 {{ grid-column: 1 / -1; }}
}}
@media (max-width: 700px) {{
  .wrap {{ padding: 14px 16px 24px; }}
  #uni-name {{ font-size: 21px; }}
  .kpis {{ grid-template-columns: repeat(2, minmax(0, 1fr)); }}
  .kpi {{ padding: 12px; }}
  .kpi-value {{ font-size: 26px; }}
  .grid {{ grid-template-columns: minmax(0, 1fr); gap: 12px; }}
  .span-2, .span-3 {{ grid-column: auto; }}
  .card {{ padding: 14px; }}
}}
"""


def _print_css() -> str:
    """Print: one A4 landscape page with the #report section, always in exec-light.

    :root[data-style] (0,2,0) beats [data-style="x"] on <html>, while the inline
    --accent from ?accent= still wins. #report rules undo the per-style tweaks.
    """
    toks = "\n".join(f"    --{k}: {val};" for k, val in STYLES[DEFAULT_STYLE].items())
    return f"""@media print {{
  @page {{ size: A4 landscape; margin: 10mm; }}
  :root[data-style] {{
{toks}
    color-scheme: light;
  }}
  html, body {{ background: #FFFFFF !important; -webkit-print-color-adjust: exact; print-color-adjust: exact; }}
  body {{ font-size: 13px; }}
  .wrap {{ max-width: none; padding: 0; }}
  .top, .controls, .notice, .tabs, main {{ display: none !important; }}
  .print-only {{ display: block !important; }}
  #report {{ break-inside: avoid; page-break-inside: avoid; }}
  #report * {{ text-shadow: none !important; filter: none !important; box-shadow: none !important; }}
  .report-head {{ display: flex; justify-content: space-between; align-items: baseline; gap: 16px;
    padding-bottom: 6px; margin-bottom: 10px; border-bottom: 1px solid var(--line); }}
  .report-uni {{ font-size: 20px; font-weight: 700; letter-spacing: -0.01em; }}
  .report-title {{ font-size: 13px; font-weight: 600; color: var(--ink-2); }}
  #report .kpis {{ grid-template-columns: repeat(6, minmax(0, 1fr)); border: 0; border-radius: var(--radius);
    margin-bottom: 12px; }}
  #report .kpi {{ padding: 10px 12px 12px; }}
  #report .kpi + .kpi {{ border-left: 1px solid rgba(255, 255, 255, 0.12); }}
  #report .kpi-label {{ font-family: var(--font-body); color: inherit; opacity: 0.72; font-weight: 400; }}
  #report .kpi-value {{ font-size: 28px; font-weight: 700; }}
  #report .kpi-sub {{ color: inherit; opacity: 0.66; }}
  .report-grid {{ display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 10px; align-items: stretch; }}
  #report .keypoints {{ grid-column: 1 / -1; }}
  #report .keypoints ol {{ columns: 2; column-gap: 32px; margin-top: 6px; }}
  #report .card {{ padding: 12px 14px; border: 1px solid var(--line); border-radius: var(--radius); break-inside: avoid; }}
  #report .card h3 {{ font-family: var(--font-body); font-size: 13px; font-weight: 700; text-transform: none;
    letter-spacing: 0; }}
  #report .card-sub {{ margin-bottom: 8px; font-size: 11px; }}
  #report .keypoints {{ border: 1px solid transparent; }}
  #report .keypoints li {{ font-size: 12px; margin-bottom: 7px; break-inside: avoid; }}
  #report .keypoints b {{ font-weight: 700; }}
  #report .source {{ margin-top: 10px; font-family: var(--font-body); font-size: 10px; }}
}}"""


JS = r"""(function () {
  "use strict";
  var LABELS = __LABELS__;
  var buttons = Array.prototype.slice.call(document.querySelectorAll(".tabs [data-tab]"));
  var panels = Array.prototype.slice.call(document.querySelectorAll("section.panel"));

  function showTab(id) {
    var found = false;
    panels.forEach(function (p) {
      if (p.id === id) {
        p.setAttribute("data-on", "");
        found = true;
      } else {
        p.removeAttribute("data-on");
      }
    });
    buttons.forEach(function (b) {
      var on = b.getAttribute("data-tab") === id;
      b.setAttribute("aria-selected", on ? "true" : "false");
      b.tabIndex = on ? 0 : -1;
    });
    return found;
  }

  function visibleButtons() {
    return Array.prototype.slice.call(document.querySelectorAll(".tabs [data-tab]"))
      .filter(function (b) { return !b.hidden; });
  }

  buttons.forEach(function (b) {
    b.addEventListener("click", function () {
      showTab(b.getAttribute("data-tab"));
    });
    b.addEventListener("keydown", function (e) {
      var list = visibleButtons();
      var i = list.indexOf(b);
      var next = null;
      if (e.key === "ArrowRight") { next = list[(i + 1) % list.length]; }
      else if (e.key === "ArrowLeft") { next = list[(i - 1 + list.length) % list.length]; }
      else if (e.key === "Home") { next = list[0]; }
      else if (e.key === "End") { next = list[list.length - 1]; }
      if (next) {
        e.preventDefault();
        showTab(next.getAttribute("data-tab"));
        next.focus();
      }
    });
  });

  window.showTab = showTab;

  /*<prefs>*/
  function loadPref(key) {
    try {
      var v = globalThis.localStorage.getItem(key);
      return typeof v === "string" ? v : null;
    } catch (e) {
      return null;
    }
  }

  function savePref(key, value) {
    try {
      globalThis.localStorage.setItem(key, String(value));
    } catch (e) {
      /* storage blocked or full: the choice simply is not remembered */
    }
  }
  /*</prefs>*/

  /*<parseConfig>*/
  var STYLE_IDS = __STYLE_IDS__;
  var ALL_TABS = __TAB_IDS__;
  var FLAGGED_TABS = __FLAGGED_TABS__;
  var KNOWN_FLAGS = __KNOWN_FLAGS__;
  var DEFAULT_NAMES = __DEFAULT_NAMES__;

  function splitList(v) {
    return (v || "").split(",").map(function (x) { return x.trim(); })
      .filter(function (x) { return x !== ""; });
  }

  function parseConfig(search) {
    var q = new URLSearchParams(search || "");
    var cfg = { given: {} };

    var style = q.get("style");
    cfg.given.style = STYLE_IDS.indexOf(style) >= 0;
    cfg.style = cfg.given.style ? style : STYLE_IDS[0];

    var lang = q.get("lang");
    cfg.given.lang = lang === "it" || lang === "en";
    if (cfg.given.lang) {
      cfg.lang = lang;
    } else {
      var nav = (typeof navigator !== "undefined" && navigator.language) || "";
      cfg.lang = String(nav).toLowerCase().indexOf("it") === 0 ? "it" : "en";
    }

    cfg.flags = [];
    splitList(q.get("flag")).forEach(function (f) {
      if (KNOWN_FLAGS.indexOf(f) >= 0 && cfg.flags.indexOf(f) < 0) { cfg.flags.push(f); }
    });

    function allowed(id) {
      return ALL_TABS.indexOf(id) >= 0 &&
        (!FLAGGED_TABS[id] || cfg.flags.indexOf(FLAGGED_TABS[id]) >= 0);
    }
    var tabs = [];
    splitList(q.get("tabs")).forEach(function (id) {
      if (allowed(id) && tabs.indexOf(id) < 0) { tabs.push(id); }
    });
    if (!tabs.length) {
      tabs = ALL_TABS.filter(function (id) { return !FLAGGED_TABS[id]; });
    }
    ALL_TABS.forEach(function (id) {
      if (FLAGGED_TABS[id] && allowed(id) && tabs.indexOf(id) < 0) { tabs.push(id); }
    });
    cfg.tabs = tabs;

    var name = Array.from((q.get("name") || "").trim()).slice(0, 80).join("").trim();
    cfg.given.name = name !== "";
    cfg.name = cfg.given.name ? name : DEFAULT_NAMES[cfg.lang];

    var accent = q.get("accent");
    cfg.accent = accent !== null && /^[0-9a-fA-F]{6}$/.test(accent) ? accent : null;
    return cfg;
  }
  /*</parseConfig>*/

  var STYLE_KEY = "demo.style";
  var LANG_KEY = "demo.lang";
  var styleSelect = document.getElementById("style-select");
  var nameEl = document.getElementById("uni-name");
  var nav = document.querySelector(".tabs");
  var langButtons = Array.prototype.slice.call(document.querySelectorAll("[data-setlang]"));
  var current = null;
  var nameIsCustom = false;

  function applyStyle(id) {
    if (STYLE_IDS.indexOf(id) < 0) { id = STYLE_IDS[0]; }
    document.documentElement.setAttribute("data-style", id);
    if (styleSelect) { styleSelect.value = id; }
    return id;
  }

  // Replace only the element's own first text node, so a <title> child
  // (heatmap tooltip) survives the swap.
  function setOwnText(el, text) {
    var n = el.firstChild;
    while (n && n.nodeType !== 3) { n = n.nextSibling; }
    if (n) { n.data = text; } else { el.insertBefore(document.createTextNode(text), el.firstChild); }
  }

  function applyConfig(cfg) {
    var lang = cfg.lang === "en" ? "en" : "it";
    var dict = LABELS[lang];
    document.documentElement.setAttribute("lang", lang);
    cfg.style = applyStyle(cfg.style);

    Array.prototype.forEach.call(document.querySelectorAll("[data-i18n]"), function (el) {
      var v = dict[el.getAttribute("data-i18n")];
      if (typeof v === "string") { setOwnText(el, v); }
    });
    Array.prototype.forEach.call(document.querySelectorAll("[data-it][data-en]"), function (el) {
      var v = el.getAttribute("data-" + lang);
      if (v !== null) { setOwnText(el, v); }
    });
    Array.prototype.forEach.call(document.querySelectorAll("[data-lang]"), function (el) {
      el.hidden = el.getAttribute("data-lang") !== lang;
    });
    if (dict["ui.page_title"]) { document.title = dict["ui.page_title"]; }
    langButtons.forEach(function (b) {
      b.setAttribute("aria-pressed", b.getAttribute("data-setlang") === lang ? "true" : "false");
    });

    if (nameEl) { nameEl.textContent = cfg.name; }
    Array.prototype.forEach.call(document.querySelectorAll("[data-uni-name]"), function (el) {
      el.textContent = cfg.name;
    });
    if (cfg.accent) {
      document.documentElement.style.setProperty("--accent", "#" + cfg.accent);
    } else {
      document.documentElement.style.removeProperty("--accent");
    }

    cfg.tabs.forEach(function (id) {
      var b = document.getElementById("tab-" + id);
      if (b && nav) { nav.appendChild(b); }
    });
    buttons.forEach(function (b) {
      var id = b.getAttribute("data-tab");
      b.hidden = cfg.tabs.indexOf(id) < 0;
    });
    panels.forEach(function (p) {
      p.hidden = cfg.tabs.indexOf(p.id) < 0;
    });
    var active = buttons.filter(function (b) { return b.getAttribute("aria-selected") === "true"; })[0];
    if (!active || active.hidden) { showTab(cfg.tabs[0]); }
    return cfg;
  }

  function updateUrl(key, value) {
    try {
      var q = new URLSearchParams(window.location.search);
      q.set(key, value);
      window.history.replaceState(null, "", window.location.pathname + "?" + q.toString() + window.location.hash);
    } catch (e) {
      /* replaceState can throw on file:// in some browsers: the URL just stays as it is */
    }
  }

  function init() {
    var cfg = parseConfig(window.location.search);
    nameIsCustom = cfg.given.name;
    if (!cfg.given.lang) {
      var pl = loadPref(LANG_KEY);
      if (pl === "it" || pl === "en") {
        cfg.lang = pl;
        if (!cfg.given.name) { cfg.name = DEFAULT_NAMES[pl]; }
      }
    }
    if (!cfg.given.style) {
      var ps = loadPref(STYLE_KEY);
      if (STYLE_IDS.indexOf(ps) >= 0) { cfg.style = ps; }
    }
    current = applyConfig(cfg);
  }

  langButtons.forEach(function (b) {
    b.addEventListener("click", function () {
      var lang = b.getAttribute("data-setlang");
      if (!current || current.lang === lang) { return; }
      current.lang = lang;
      if (!nameIsCustom) { current.name = DEFAULT_NAMES[lang]; }
      applyConfig(current);
      savePref(LANG_KEY, lang);
      updateUrl("lang", lang);
    });
  });

  if (styleSelect) {
    styleSelect.addEventListener("change", function () {
      var id = applyStyle(styleSelect.value);
      if (current) { current.style = id; }
      savePref(STYLE_KEY, id);
      updateUrl("style", id);
    });
  }

  var reportBtn = document.getElementById("report-btn");
  if (reportBtn) {
    reportBtn.addEventListener("click", function () { window.print(); });
  }

  window.parseConfig = parseConfig;
  window.applyConfig = applyConfig;
  init();
})();
"""


def _js() -> str:
    default_names = {lg: demo_i18n.t("uni.default_name", lg) for lg in ("it", "en")}
    labels = json.dumps(demo_i18n.LABELS, ensure_ascii=True, sort_keys=True).replace("</", "<\\/")
    return (JS.replace("__STYLE_IDS__", json.dumps(list(STYLES)))
            .replace("__TAB_IDS__", json.dumps(list(TABS)))
            .replace("__FLAGGED_TABS__", json.dumps({t: t for t in sorted(FLAGGED)}))
            .replace("__KNOWN_FLAGS__", json.dumps(sorted(FLAGGED)))
            .replace("__DEFAULT_NAMES__", json.dumps(default_names, ensure_ascii=True))
            .replace("__LABELS__", labels))


def render(data: dict) -> str:
    v = _views(data)
    bodies = {
        "overview": _overview(data, v),
        "weekly": _weekly(data),
        "countries": _countries(data, v),
        "programmes": _programmes(data, v),
        "natint": _natint(data, v),
        "funnel": _funnel(data),
        "deferrals": _deferrals(data, v),
        "advisors": _advisors(data),
        "fees": _fees(data, v),
        "beforeafter": _beforeafter(data),
    }
    first = TABS[0]
    tabs = "".join(_tab_button(tid, tid == first) for tid in TABS)
    panels = "\n".join(_panel(tid, bodies[tid], tid == first) for tid in TABS)
    return f"""<!doctype html>
<html lang="it" data-style="exec-light">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{_t("ui.page_title")}</title>
<style>
{_css()}</style>
</head>
<body>
<div class="wrap">
<header class="top">
<div class="brand">
<h1 id="uni-name">{_t("uni.default_name")}</h1>
<div class="meta">{_ui("uni.intake")}{_ui("ui.demo_tag", "span", "tag")}</div>
</div>
<div class="controls" id="controls">{_lang_control()}{_style_control()}{_report_button()}</div>
</header>
{_ui("ui.demo_notice", "p", "notice")}
<nav class="tabs" role="tablist" aria-label="{_t("ui.tabs")}">{tabs}</nav>
<main>
{panels}
</main>
{_report(data, v)}
</div>
<script id="app">
{_js()}</script>
</body>
</html>
"""


def main(out: Optional[str] = None) -> None:
    path = out or os.path.join(os.path.dirname(os.path.abspath(__file__)), "demo.html")
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(render(demo_data.build_dataset()))


if __name__ == "__main__":
    main()
