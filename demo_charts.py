"""SVG chart helpers for the demo dashboard.

Every helper returns an SVG string that scales to its container (viewBox plus
width="100%") and takes all colours from CSS variables, so each style re-colours
the charts by redefining those variables. Data-name labels may be a str or an
(italian, english) pair; the Italian text is rendered and both are carried in
data-it / data-en. UI words carry data-i18n keys from demo_i18n.LABELS.
"""

from __future__ import annotations

from html import escape
import demo_i18n
from typing import Optional, Sequence, Tuple, Union

Label = Union[str, Tuple[str, str]]

INK = "var(--ink)"
INK2 = "var(--ink-2)"
LINE = "var(--line)"
ACCENT = "var(--accent)"
ACCENT2 = "var(--accent-2)"
PANEL2 = "var(--panel-2)"
FONT = 'font-family="inherit"'


def _q(s: object) -> str:
    return escape(str(s), quote=True)


def _ui(key: str) -> str:
    return escape(demo_i18n.t(key, "it"))


def _fs(base: int, w: float) -> float:
    """Font size that still renders at >= 10 px when the viewBox is w wide in a 343 px box."""
    return max(base, round(10.3 * w / 343, 1))


def _pct(part: float, whole: float) -> int:
    return int(round(100.0 * part / whole)) if whole else 0


def _pair(label: Label) -> Tuple[str, str]:
    if isinstance(label, (tuple, list)):
        return str(label[0]), str(label[1])
    return str(label), str(label)


def _text(x: float, y: float, content: str, size: int = 13, fill: str = INK,
          anchor: str = "start", weight: str = "400", extra: str = "") -> str:
    return (f'<text x="{x:g}" y="{y:g}" font-size="{size}" fill="{fill}" '
            f'text-anchor="{anchor}" font-weight="{weight}" {FONT}{extra}>{content}</text>')


def _name_text(x: float, y: float, label: Label, **kw) -> str:
    it, en = _pair(label)
    extra = f' data-it="{_q(it)}" data-en="{_q(en)}"'
    return _text(x, y, escape(it), extra=extra, **kw)


def _svg(w: float, h: float, body: str) -> str:
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w:g} {h:g}" '
            f'width="100%" role="img" preserveAspectRatio="xMidYMid meet">{body}</svg>')


def hbars(rows: Sequence[Tuple[Label, int]], total: int,
          label_keys: Optional[Sequence[str]] = None) -> str:
    """Horizontal bars; label above each bar, "value · pct%" to its right.

    label_keys, if given, are data-i18n keys for UI-word labels (one per row);
    they replace the data-it/data-en pair for that row.
    """
    w, bar_max, row_h = 360, 220, 40
    mx = max([v for _, v in rows] + [1])
    body = []
    for i, (label, value) in enumerate(rows):
        y = 6 + i * row_h
        if label_keys and i < len(label_keys) and label_keys[i]:
            body.append(_text(0, y + 13, escape(_pair(label)[0]), fill=INK2,
                              extra=f' data-i18n="{_q(label_keys[i])}"'))
        else:
            body.append(_name_text(0, y + 13, label, fill=INK2))
        bw = max(2.0, bar_max * value / mx) if value > 0 else 2.0
        body.append(f'<rect x="0" y="{y + 19}" width="{bar_max}" height="8" rx="4" fill="{LINE}" fill-opacity="0.5"/>')
        body.append(f'<rect x="0" y="{y + 19}" width="{bw:.1f}" height="8" rx="4" fill="{ACCENT}"/>')
        body.append(_text(bar_max + 10, y + 27, f"{value} · {_pct(value, total)}%",
                          fill=INK, weight="600"))
    return _svg(w, max(10, 12 + len(rows) * row_h), "".join(body))


def line_vs_target(series: Sequence[int], target: Sequence[int],
                   last_year: Optional[Sequence[int]] = None,
                   series_key: str = "kpi.applications") -> str:
    """Cumulative line against a dashed target (and an optional last-year line).

    series_key is the data-i18n key of the series legend; the target legend is
    drawn only when a target is given.
    """
    w, h = 360, 210
    l, r, t, b = 34, 40, 30, 24
    n = max(len(series), len(target), len(last_year or []), 1)
    vals = list(series) + list(target) + list(last_year or [])
    mx = max(vals + [1])

    def px(i: int) -> float:
        return l + (w - l - r) / 2 if n == 1 else l + (w - l - r) * i / (n - 1)

    def py(v: float) -> float:
        return t + (h - t - b) * (1 - v / mx)

    def pts(data: Sequence[int]) -> str:
        return " ".join(f"{px(i):.1f},{py(v):.1f}" for i, v in enumerate(data))

    body = [f'<line x1="{l}" y1="{h - b}" x2="{w - r}" y2="{h - b}" stroke="{LINE}" stroke-width="1"/>',
            f'<line x1="{l}" y1="{py(mx):.1f}" x2="{w - r}" y2="{py(mx):.1f}" stroke="{LINE}" stroke-width="1" stroke-dasharray="2 4"/>',
            _text(l - 6, py(mx) + 4, str(mx), size=11, fill=INK2, anchor="end"),
            _text(l - 6, h - b + 4, "0", size=11, fill=INK2, anchor="end")]
    if last_year:
        body.append(f'<polyline points="{pts(last_year)}" fill="none" stroke="{ACCENT2}" stroke-width="1.5" stroke-opacity="0.7"/>')
    if target:
        body.append(f'<polyline points="{pts(target)}" fill="none" stroke="{INK2}" stroke-width="1.5" stroke-dasharray="5 4"/>')
    if series:
        body.append(f'<polyline points="{pts(series)}" fill="none" stroke="{ACCENT}" stroke-width="2.5" stroke-linejoin="round" stroke-linecap="round"/>')
        for i, v in enumerate(series):
            if i == len(series) - 1 or len(series) == 1:
                body.append(f'<circle cx="{px(i):.1f}" cy="{py(v):.1f}" r="3.5" fill="{ACCENT}"/>')
    # end-point value labels, kept apart when the two ends are close
    s_end = series[-1] if series else None
    t_end = target[-1] if target else None
    if s_end is not None:
        up = t_end is None or s_end >= t_end
        body.append(_text(px(len(series) - 1) + 8, py(s_end) + (-2 if up else 12), str(s_end),
                          size=12, fill=ACCENT, weight="700"))
    if t_end is not None:
        up = s_end is not None and s_end < t_end
        body.append(_text(px(len(target) - 1) + 8, py(t_end) + (-2 if up else 12), str(t_end),
                          size=12, fill=INK2, weight="600"))
    # legend
    lx = l
    body.append(f'<line x1="{lx}" y1="10" x2="{lx + 16}" y2="10" stroke="{ACCENT}" stroke-width="2.5"/>')
    body.append(_text(lx + 22, 14, _ui(series_key), size=11, fill=INK2, extra=f' data-i18n="{_q(series_key)}"'))
    lx += 100
    if target:
        body.append(f'<line x1="{lx}" y1="10" x2="{lx + 16}" y2="10" stroke="{INK2}" stroke-width="1.5" stroke-dasharray="5 4"/>')
        body.append(_text(lx + 22, 14, _ui("kpi.target"), size=11, fill=INK2, extra=' data-i18n="kpi.target"'))
        lx += 84
    if last_year:
        body.append(f'<line x1="{lx}" y1="10" x2="{lx + 16}" y2="10" stroke="{ACCENT2}" stroke-width="1.5"/>')
        body.append(_text(lx + 22, 14, _ui("chart.last_year"), size=11, fill=INK2, extra=' data-i18n="chart.last_year"'))
    return _svg(w, h, "".join(body))


def donut(parts: Sequence[Tuple[Label, int]], centre: str) -> str:
    w, cx, cy, rad, sw = 360, 76, 84, 56, 20
    circ = 2 * 3.141592653589793 * rad
    total = sum(v for _, v in parts)
    fills = [(ACCENT, "1"), (ACCENT2, "1"), (INK2, "0.8"), (ACCENT, "0.5"), (ACCENT2, "0.5"), (INK2, "0.45")]
    body = [f'<circle cx="{cx}" cy="{cy}" r="{rad}" fill="none" stroke="{LINE}" stroke-opacity="0.5" stroke-width="{sw}"/>']
    off = 0.0
    for i, (_, v) in enumerate(parts):
        if total and v > 0:
            seg = circ * v / total
            colour, op = fills[i % len(fills)]
            body.append(f'<circle cx="{cx}" cy="{cy}" r="{rad}" fill="none" stroke="{colour}" stroke-opacity="{op}" '
                        f'stroke-width="{sw}" stroke-dasharray="{seg:.2f} {circ - seg:.2f}" '
                        f'stroke-dashoffset="{-off:.2f}" transform="rotate(-90 {cx} {cy})"/>')
            off += seg
    body.append(_text(cx, cy + 8, escape(str(centre)), size=22, anchor="middle", weight="700"))
    for i, (label, v) in enumerate(parts):
        y = 40 + i * 34
        colour, op = fills[i % len(fills)]
        body.append(f'<rect x="168" y="{y - 10}" width="12" height="12" rx="3" fill="{colour}" fill-opacity="{op}"/>')
        body.append(_name_text(188, y, label, fill=INK2))
        body.append(_text(188, y + 16, f"{v} · {_pct(v, total)}%", weight="600"))
    return _svg(w, max(2 * cy + 10, 40 + len(parts) * 34 + 6), "".join(body))


def funnel(steps: Sequence[Tuple[Label, int]]) -> str:
    w, bar_max, row_h = 360, 230, 50
    mx = max([v for _, v in steps] + [1])
    body = []
    for i, (label, v) in enumerate(steps):
        y = 6 + i * row_h
        body.append(_name_text(0, y + 13, label, fill=INK2))
        bw = max(2.0, bar_max * v / mx) if v > 0 else 2.0
        op = max(0.35, 1 - 0.18 * i)
        body.append(f'<rect x="0" y="{y + 19}" width="{bar_max}" height="10" rx="5" fill="{LINE}" fill-opacity="0.5"/>')
        body.append(f'<rect x="0" y="{y + 19}" width="{bw:.1f}" height="10" rx="5" fill="{ACCENT}" fill-opacity="{op:.2f}"/>')
        body.append(_text(bar_max + 10, y + 28, str(v), weight="600"))
        if i > 0:
            prev = steps[i - 1][1]
            body.append(_text(0, y + 44, f'{_pct(v, prev)}% <tspan data-i18n="chart.of_prev">{_ui("chart.of_prev")}</tspan>',
                              size=11, fill=INK2))
    return _svg(w, max(10, 12 + len(steps) * row_h), "".join(body))


def _trunc(text: str, max_chars: int) -> str:
    return text if len(text) <= max_chars else text[:max(1, max_chars - 1)].rstrip() + "\u2026"


def _fit_text(x: float, y: float, label: Label, max_chars: int, **kw) -> str:
    """Text whose data-it/data-en hold the truncated display forms; the full
    forms live in a <title> child (also carrying data-it/data-en)."""
    it, en = _pair(label)
    vis_it, vis_en = _trunc(it, max_chars), _trunc(en, max_chars)
    extra = f' data-it="{_q(vis_it)}" data-en="{_q(vis_en)}"'
    title = ""
    if vis_it != it or vis_en != en:
        title = f'<title data-it="{_q(it)}" data-en="{_q(en)}">{escape(it)}</title>'
    return _text(x, y, escape(vis_it) + title, extra=extra, **kw)


def heatmap(rows: Sequence[Label], cols: Sequence[Label],
            cells: Sequence[Sequence[int]]) -> str:
    ncols = len(cols)
    longest = max([len(_pair(r)[0]) for r in rows] + [5])
    lw = min(130, max(60, int(longest * 6.8) + 8))
    cw, ch, top = 50, 30, 30
    w = lw + (ncols + 1) * cw
    fs = _fs(11, w)
    mx = max([v for r in cells for v in r] + [1])
    hchars = max(3, int(cw / (fs * 0.58)))
    rchars = max(4, int((lw - 8) / (fs * 0.58)))
    body = []
    for j, c in enumerate(cols):
        body.append(_fit_text(lw + j * cw + cw / 2, 20, c, hchars, size=fs, fill=INK2, anchor="middle"))
    body.append(_text(lw + ncols * cw + cw / 2, 20, _ui("chart.total"), size=fs, fill=INK2,
                      anchor="middle", weight="700", extra=' data-i18n="chart.total"'))
    col_tot = [0] * ncols
    for i, rlabel in enumerate(rows):
        y = top + i * ch
        body.append(_fit_text(0, y + 19, rlabel, rchars, size=fs, fill=INK2))
        row = list(cells[i]) if i < len(cells) else []
        for j in range(ncols):
            v = row[j] if j < len(row) else 0
            col_tot[j] += v
            op = 0.06 + 0.8 * v / mx
            fill_txt = PANEL2 if op > 0.65 else INK
            body.append(f'<rect x="{lw + j * cw + 1}" y="{y + 1}" width="{cw - 2}" height="{ch - 2}" rx="4" '
                        f'fill="{ACCENT}" fill-opacity="{op:.2f}"/>')
            body.append(_text(lw + j * cw + cw / 2, y + 19, str(v), size=fs, fill=fill_txt, anchor="middle"))
        body.append(_text(lw + ncols * cw + cw / 2, y + 19, str(sum(row[:ncols])), size=fs,
                          anchor="middle", weight="700"))
    ty = top + len(rows) * ch
    body.append(f'<line x1="0" y1="{ty + 1}" x2="{w}" y2="{ty + 1}" stroke="{LINE}" stroke-width="1"/>')
    body.append(_text(0, ty + 20, _ui("chart.total"), size=fs, fill=INK2, weight="700", extra=' data-i18n="chart.total"'))
    for j in range(ncols):
        body.append(_text(lw + j * cw + cw / 2, ty + 20, str(col_tot[j]), size=fs, anchor="middle", weight="700"))
    body.append(_text(lw + ncols * cw + cw / 2, ty + 20, str(sum(col_tot)), size=fs, anchor="middle", weight="700"))
    return _svg(w, ty + 32, "".join(body))
