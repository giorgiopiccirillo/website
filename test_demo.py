from __future__ import annotations

import json
import re
import unittest
from pathlib import Path

import demo_data
from demo_data import STATUS_PRIORITY, build_dataset, strongest

def load_banned():
    """Banned strings live in a git-ignored local file; tests skip without it."""
    path = Path(__file__).with_name("local_banned_strings.json")
    if not path.exists():
        raise unittest.SkipTest("local_banned_strings.json not present")
    return json.loads(path.read_text(encoding="utf-8"))


def dump(d):
    return json.dumps(d, sort_keys=True, indent=1, ensure_ascii=False)


class DemoDataTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.d = build_dataset()

    def test_deterministic(self):
        a, b = build_dataset(), build_dataset()
        self.assertEqual(a, b)
        self.assertEqual(dump(a).encode("utf-8"), dump(b).encode("utf-8"))

    def test_funnel_monotonic(self):
        f = self.d["funnel"]
        self.assertGreaterEqual(f["applications"], f["offers"])
        self.assertGreaterEqual(f["offers"], f["accepted"])
        self.assertGreaterEqual(f["accepted"], f["enrolled"])
        self.assertGreater(f["enrolled"], 0)
        s = self.d["summary"]
        for k in ("offers", "accepted", "enrolled"):
            self.assertEqual(s[k], f[k])
        self.assertEqual(s["applications"], f["applications"])

    def test_one_per_student(self):
        apps = self.d["applications"]
        ids = {a["student_id"] for a in apps}
        self.assertEqual(self.d["summary"]["students"], len(ids))
        self.assertLess(self.d["summary"]["students"], len(apps))

    def test_dedupe_uses_priority(self):
        self.assertEqual(strongest(["Offer", "Enrolled"]), "Enrolled")
        self.assertEqual(strongest(["Rejected", "Withdrawn"]), "Rejected")
        # enrolled count equals students whose strongest status is Enrolled
        by = {}
        for a in self.d["applications"]:
            by.setdefault(a["student_id"], []).append(a["status"])
        n = sum(1 for s in by.values() if strongest(s) == "Enrolled")
        self.assertEqual(n, self.d["summary"]["enrolled"])

    def test_countries_sum(self):
        c = self.d["countries"]
        self.assertEqual(sum(x["students"] for x in c), self.d["summary"]["students"])
        self.assertEqual(sum(x["enrolled"] for x in c), self.d["summary"]["enrolled"])
        counts = [x["students"] for x in c]
        self.assertEqual(counts, sorted(counts, reverse=True))

    def test_weekly_cumulative(self):
        w = self.d["weekly"]
        self.assertEqual(len(w), 26)
        self.assertEqual(w[0]["week"], "2027-W03")
        self.assertEqual(w[-1]["week"], "2027-W28")
        for k in ("applications_cum", "enrolled_cum", "target_cum", "applications_cum_last_year"):
            s = [r[k] for r in w]
            self.assertEqual(s, sorted(s), k)
        self.assertEqual(w[-1]["applications_cum"], self.d["summary"]["students"])
        self.assertEqual(w[-1]["enrolled_cum"], self.d["summary"]["enrolled"])
        self.assertEqual(w[-1]["target_cum"], self.d["summary"]["target"])

    def test_current_week_has_applications(self):
        w = self.d["weekly"]
        self.assertGreater(w[-1]["applications_cum"] - w[-2]["applications_cum"], 0)

    def test_key_point_wording(self):
        en, it = self.d["key_points_en"][0], self.d["key_points_it"][0]
        self.assertIn("applications in total; each student is counted once)", en)
        self.assertIn("candidature in totale; ogni studente \u00e8 contato una volta)", it)
        self.assertIn("; primo paese estero: ", self.d["key_points_it"][2])
        self.assertNotIn("il primo paese estero", self.d["key_points_it"][2])

    def test_no_banned_strings(self):
        text = dump(self.d).lower()
        for b in load_banned():
            self.assertNotIn(b.lower(), text, b)
        self.assertNotIn("univers", text)

    def test_story_shape(self):
        s = self.d["summary"]
        self.assertTrue(0.70 <= s["enrolled"] / s["target"] <= 0.75)
        nat = sum(x["students"] for x in self.d["countries"] if x["national"])
        self.assertTrue(0.36 <= nat / s["students"] <= 0.44)
        self.assertEqual(sum(x["students"] for x in self.d["deferrals"]), s["deferrals"])
        self.assertGreater(s["deferrals"], 0)
        multi = {}
        for a in self.d["applications"]:
            multi[a["student_id"]] = multi.get(a["student_id"], 0) + 1
        self.assertTrue(set(multi.values()) <= {1, 2, 3})
        share = sum(1 for v in multi.values() if v > 1) / len(multi)
        self.assertTrue(0.10 <= share <= 0.20)

    def test_shapes(self):
        d = self.d
        self.assertEqual(len(d["programmes"]), 12)
        self.assertEqual(len(d["advisors"]), 6)
        self.assertEqual(len(d["key_points_it"]), 4)
        self.assertEqual(len(d["key_points_en"]), 4)
        self.assertEqual(len(d["before_after"]["raw"]), 10)
        self.assertEqual(len(d["before_after"]["clean"]), 10)
        self.assertEqual(d["meta"]["generated"], "2027-07-15")
        self.assertEqual(d["meta"]["seed"], 20271107)
        self.assertEqual(d["meta"]["intake_it"], "A.A. 2027/28")
        self.assertEqual(d["meta"]["intake_en"], "Intake 2027/28")
        self.assertTrue({a["status"] for a in d["applications"]} <= set(STATUS_PRIORITY))

    def test_key_points_wording(self):
        text = " ".join(self.d["key_points_en"] + self.d["key_points_it"]).lower()
        for w in ("correct", "right", "corretto"):
            self.assertIsNone(re.search(w, text), w)
        for k in ("students", "enrolled"):
            self.assertIn(str(self.d["summary"][k]), self.d["key_points_en"][0] + self.d["key_points_en"][1])


class DemoLabelTests(unittest.TestCase):
    def test_labels_same_keys(self):
        import demo_i18n
        self.assertEqual(set(demo_i18n.LABELS["it"]), set(demo_i18n.LABELS["en"]))

    def test_labels_non_empty(self):
        import demo_i18n
        for lang in ("it", "en"):
            for k, v in demo_i18n.LABELS[lang].items():
                self.assertTrue(v.strip(), (lang, k))

    def test_labels_required_keys_and_exact_strings(self):
        import demo_i18n
        tabs = ["overview", "weekly", "countries", "programmes", "natint",
                "funnel", "deferrals", "advisors", "fees", "beforeafter"]
        need = ["ui.style", "ui.language", "ui.download_report", "ui.key_points",
                "ui.source", "ui.demo_notice", "uni.default_name", "uni.intake",
                "kpi.applications", "kpi.students", "kpi.offers", "kpi.enrolled",
                "kpi.deferrals", "kpi.target"]
        for tid in tabs:
            need += ["tab." + tid, "tab.%s.title" % tid, "tab.%s.sub" % tid]
        for lang in ("it", "en"):
            for k in need:
                self.assertIn(k, demo_i18n.LABELS[lang], (lang, k))
        L = demo_i18n.LABELS
        self.assertEqual(L["it"]["ui.demo_notice"], "Dati dimostrativi: nessun dato reale.")
        self.assertEqual(L["en"]["ui.demo_notice"], "Demo data: no real data.")
        self.assertEqual(L["it"]["uni.default_name"], "La tua Università")
        self.assertEqual(L["en"]["uni.default_name"], "Your University")
        self.assertEqual(L["it"]["uni.intake"], "A.A. 2027/28")
        self.assertEqual(L["en"]["uni.intake"], "Intake 2027/28")
        self.assertEqual(demo_i18n.t("uni.intake"), "A.A. 2027/28")
        self.assertEqual(demo_i18n.t("uni.intake", "en"), "Intake 2027/28")

    def test_natint_label_mentions_international(self):
        import demo_i18n
        self.assertIn("international", demo_i18n.LABELS["en"]["tab.natint"])

    def test_labels_no_banned_words(self):
        import demo_i18n
        banned = [b.lower() for b in load_banned()]
        for lang in ("it", "en"):
            for k, v in demo_i18n.LABELS[lang].items():
                low = v.lower()
                for w in banned:
                    self.assertNotIn(w, low, (lang, k, w))
                self.assertIsNone(re.search(r"\b(correct|right|corretto)\b", low), (lang, k))


class DemoChartTests(unittest.TestCase):
    def _parse(self, svg):
        import xml.etree.ElementTree as ET
        root = ET.fromstring(svg)
        self.assertEqual(root.get("width"), "100%")
        self.assertTrue(root.get("viewBox"))
        self.assertIsNone(re.search(r"#[0-9a-fA-F]{3,6}", svg))
        return root

    def test_hbars(self):
        import demo_charts
        svg = demo_charts.hbars([("Italia", 38), (("Germania", "Germany"), 62)], 100)
        self._parse(svg)
        self.assertIn("38 \u00b7 38%", svg)
        self.assertIn("62 \u00b7 62%", svg)
        self.assertIn('data-it="Germania"', svg)
        self.assertIn('data-en="Germany"', svg)
        self.assertIn("var(--accent)", svg)

    def test_hbars_escapes_and_zero_total(self):
        import demo_charts
        svg = demo_charts.hbars([("A<b>&", 0)], 0)
        self._parse(svg)
        self.assertIn("A&lt;b&gt;&amp;", svg)
        self._parse(demo_charts.hbars([], 0))

    def test_line_vs_target(self):
        import demo_charts
        svg = demo_charts.line_vs_target([5, 9, 14], [6, 10, 12], [4, 7, 9])
        self._parse(svg)
        for v in ("14", "12"):
            self.assertIn(">" + v + "<", svg)
        self.assertIn('data-i18n="kpi.target"', svg)
        self.assertIn('data-i18n="chart.last_year"', svg)
        self._parse(demo_charts.line_vs_target([0, 0], [0, 0]))
        self._parse(demo_charts.line_vs_target([3], [3]))
        self.assertNotIn("chart.last_year", demo_charts.line_vs_target([1, 2], [1, 2]))

    def test_donut(self):
        import demo_charts
        svg = demo_charts.donut([("Italiani", 30), (("Internazionali", "International"), 70)], "100")
        self._parse(svg)
        for v in ("30 \u00b7 30%", "70 \u00b7 70%", ">100<"):
            self.assertIn(v, svg)
        self._parse(demo_charts.donut([("A", 0)], "0"))
        self._parse(demo_charts.donut([("A", 5)], "5"))

    def test_funnel(self):
        import demo_charts
        svg = demo_charts.funnel([("Offerte", 200), ("Accettate", 120), ("Iscritti", 90)])
        self._parse(svg)
        for v in ("200", "120", "90", "60%", "75%"):
            self.assertIn(v, svg)
        self._parse(demo_charts.funnel([("A", 0), ("B", 0)]))

    def test_heatmap(self):
        import demo_charts
        svg = demo_charts.heatmap(["UE", "Extra"], ["L", "LM"], [[3, 5], [1, 0]])
        self._parse(svg)
        for v in (">3<", ">5<", ">8<", ">4<", ">9<"):
            self.assertIn(v, svg)
        self.assertIn('data-i18n="chart.total"', svg)
        self.assertIn("fill-opacity", svg)

    def test_heatmap_all_zeros(self):
        import demo_charts
        svg = demo_charts.heatmap(["A"], ["X", "Y"], [[0, 0]])
        self._parse(svg)
        self._parse(demo_charts.heatmap([], [], []))

    def _all_svgs(self):
        import demo_charts as c
        return [
            c.hbars([(("Germania", "Germany"), 62), ("Italia", 1234)], 2000),
            c.hbars([(("Totale", "Total"), 5)], 5, label_keys=["chart.total"]),
            c.line_vs_target([5, 9, 14], [6, 10, 12], [4, 7, 9]),
            c.donut([("Italiani", 30), ("Internazionali", 70), ("Altro", 5)], "105"),
            c.funnel([("Offerte", 200), ("Accettate", 120), ("Iscritti", 90)]),
            c.heatmap(["Unione Europea", "Extra UE lungo nome davvero"], ["Triennale", "Magistrale", "Ciclo unico", "Master"], [[3, 5, 1, 0], [1, 0, 2, 2]]),
        ]

    def test_text_legible_at_375(self):
        import xml.etree.ElementTree as ET
        for svg in self._all_svgs():
            root = ET.fromstring(svg)
            vw = float(root.get("viewBox").split()[2])
            for el in root.iter("{http://www.w3.org/2000/svg}text"):
                self.assertGreaterEqual(float(el.get("font-size")) * 343 / vw, 10, el.text)

    def test_ui_words_italian_by_default(self):
        import demo_charts as c, demo_i18n
        svg = c.line_vs_target([1, 2], [1, 2], [1, 2])
        for k in ("kpi.target", "chart.last_year", "kpi.applications"):
            self.assertIn(">" + demo_i18n.t(k, "it") + "<", svg)
        self.assertIn(demo_i18n.t("chart.of_prev", "it"), c.funnel([("A", 2), ("B", 1)]))
        self.assertIn(">" + demo_i18n.t("chart.total", "it") + "<", c.heatmap(["A"], ["X"], [[1]]))

    def test_label_keys_tuple_fallback(self):
        import demo_charts as c
        svg = c.hbars([(("Ciao", "Hi"), 1)], 1, label_keys=["chart.total"])
        self.assertIn(">Ciao<", svg)
        self.assertNotIn("(&#x27;", svg)

    def test_heatmap_truncates_long_labels(self):
        import demo_charts as c
        svg = c.heatmap(["x" * 60], ["y" * 40], [[1]])
        self.assertIn("\u2026", svg)
        self.assertIn(">" + "x" * 60 + "</title>", svg)

    def test_heatmap_truncated_data_attrs(self):
        import xml.etree.ElementTree as ET
        import demo_charts as c
        long_it, long_en = "i" * 60, "e" * 60
        root = ET.fromstring(c.heatmap([(long_it, long_en)], ["X"], [[1]]))
        ns = "{http://www.w3.org/2000/svg}"
        txt = [e for e in root.iter(ns + "text") if e.find(ns + "title") is not None][0]
        self.assertTrue(txt.get("data-it").endswith("\u2026"))
        self.assertTrue(txt.get("data-en").endswith("\u2026"))
        self.assertLess(len(txt.get("data-it")), 60)
        self.assertEqual(txt.text, txt.get("data-it"))
        title = txt.find(ns + "title")
        self.assertEqual((title.get("data-it"), title.get("data-en"), title.text), (long_it, long_en, long_it))

    def test_line_series_key_and_no_target_legend(self):
        import demo_charts as c
        svg = c.line_vs_target([1, 2], [1, 3], series_key="kpi.enrolled")
        self.assertIn('data-i18n="kpi.enrolled"', svg)
        self.assertNotIn('data-i18n="kpi.applications"', svg)
        svg2 = c.line_vs_target([1, 2], [], [1, 1])
        self._parse(svg2)
        self.assertNotIn('data-i18n="kpi.target"', svg2)
        self.assertIn('data-i18n="chart.last_year"', svg2)

    def test_chart_i18n_keys_exist(self):
        import demo_i18n
        for k in ("chart.last_year", "chart.total", "kpi.target"):
            self.assertIn(k, demo_i18n.LABELS["it"])
            self.assertIn(k, demo_i18n.LABELS["en"])


TAB_IDS = ["overview", "weekly", "countries", "programmes", "natint",
           "funnel", "deferrals", "advisors", "fees", "beforeafter"]


class DemoBuildTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import demo_build
        cls.data = build_dataset()
        cls.html = demo_build.render(cls.data)

    def _tag(self, pattern):
        m = re.findall(pattern, self.html)
        self.assertEqual(len(m), 1, pattern)
        return m[0]

    def test_panels_and_tab_buttons(self):
        for tid in TAB_IDS:
            self.assertEqual(self.html.count('<section class="panel" id="%s"' % tid), 1, tid)
            self.assertEqual(self.html.count('<button data-tab="%s"' % tid), 1, tid)
        self.assertEqual(len(re.findall(r'<button data-tab="', self.html)), 10)
        self.assertEqual(len(re.findall(r'<section class="panel"', self.html)), 10)

    def test_beforeafter_hidden_and_flagged(self):
        btn = self._tag(r'<button data-tab="beforeafter"[^>]*>')
        sec = self._tag(r'<section class="panel" id="beforeafter"[^>]*>')
        for tag in (btn, sec):
            self.assertRegex(tag, r'\shidden[\s>]')
            self.assertIn('data-flag="beforeafter"', tag)
        for tid in TAB_IDS[:-1]:
            tag = self._tag(r'<button data-tab="%s"[^>]*>' % tid)
            self.assertNotRegex(tag, r'\shidden[\s>]')

    def test_no_external_requests(self):
        for pat in ('src="http', "src='http", 'href="http', "href='http", "@import", "url(http", "url('http", 'url("http'):
            self.assertNotIn(pat, self.html, pat)
        self.assertNotIn("<link", self.html)

    def test_no_banned_strings(self):
        low = self.html.lower()
        for b in load_banned():
            self.assertNotIn(b.lower(), low, b)
        text = re.sub(r"<(style|script)\b.*?</\1>", " ", low, flags=re.S)
        text = re.sub(r"<[^>]+>", " ", text)  # visible copy only (CSS has text-align: right)
        self.assertIsNone(re.search(r"\b(correct|right|corretto)\b", text))
        for v in re.findall(r'data-(?:it|en)="([^"]*)"', low):
            self.assertIsNone(re.search(r"\b(correct|right|corretto)\b", v), v)

    def test_demo_notice_and_header(self):
        import demo_i18n
        self.assertIn(demo_i18n.t("ui.demo_notice", "it"), self.html)
        self.assertIn('data-style="exec-light"', self.html)
        name = self._tag(r'<[a-z0-9]+ id="uni-name"[^>]*>[^<]*<')
        self.assertIn(demo_i18n.t("uni.default_name", "it"), name)
        self.assertIn('id="controls"', self.html)
        self.assertIn(">A.A. 2027/28<", self.html)
        self.assertIn(">Dati dimostrativi<", self.html)

    def test_i18n_keys_exist(self):
        import demo_i18n
        keys = set(re.findall(r'data-i18n="([^"]+)"', self.html))
        self.assertGreater(len(keys), 40)
        for k in keys:
            self.assertIn(k, demo_i18n.LABELS["it"], k)

    def test_i18n_text_is_italian(self):
        import demo_i18n
        for k, txt in re.findall(r'data-i18n="([^"]+)"[^>]*>([^<]*)<', self.html):
            from html import unescape
            self.assertEqual(unescape(txt), demo_i18n.t(k, "it"), k)

    def test_source_line_on_every_panel(self):
        import demo_i18n
        src = demo_i18n.t("ui.source_line", "it")
        self.assertIn("A.A. 2027/28", src)
        self.assertIn("uno studente = una candidatura", src)
        for tid in TAB_IDS:
            start = self.html.index('<section class="panel" id="%s"' % tid)
            end = self.html.index("</section>", start)
            self.assertIn('data-i18n="ui.source_line"', self.html[start:end], tid)

    def test_tokens_and_style(self):
        for v in ("--bg", "--panel", "--panel-2", "--ink", "--ink-2", "--line", "--accent",
                  "--accent-2", "--accent-soft", "--kpi-bg", "--kpi-ink", "--font-body",
                  "--font-num", "--radius", "--shadow", "--glow"):
            self.assertRegex(self.html, r"%s\s*:" % re.escape(v))
        self.assertIn("#0E7C86", self.html)
        self.assertIn("@media (max-width: 700px)", self.html)
        self.assertIn("overflow-x: auto", self.html)

    def test_overview_content(self):
        start = self.html.index('<section class="panel" id="overview"')
        ov = self.html[start:self.html.index("</section>", start)]
        self.assertEqual(ov.count('class="kpi"'), 6)
        self.assertEqual(ov.count('class="kpi-sub"'), 6)
        self.assertIn('data-i18n="ui.key_points"', ov)
        self.assertEqual(len(re.findall(r'<li[ >]', ov)), 4)
        self.assertEqual(ov.count("<b>"), 8)  # 4 IT + 4 EN sentences, one bold figure each
        self.assertIn(">%d<" % self.data["summary"]["students"], ov)
        self.assertIn(">%d<" % self.data["summary"]["enrolled"], ov)

    def _panel(self, tid):
        start = self.html.index('<section class="panel" id="%s"' % tid)
        return self.html[start:self.html.index("</section>", start)]

    def test_weekly_table(self):
        w = self._panel("weekly")
        rows = re.findall(r'<tr class="wk">(.*?)</tr>', w)
        self.assertEqual(len(rows), 8)
        self.assertNotIn("2027-W", w)
        self.assertIn('<span data-it="12 lug" data-en="12 Jul">12 lug</span>', rows[-1])
        self.assertIn('data-i18n="wk.in_progress"', rows[-1])
        self.assertNotIn("wk.in_progress", rows[0])
        self.assertIn('data-it="24 mag" data-en="24 May"', rows[0])
        wk = self.data["weekly"]
        new = [b["applications_cum"] - a["applications_cum"] for a, b in zip(wk, wk[1:])]
        self.assertIn(">%d<" % new[-1], rows[-1])
        ch = new[-1] - new[-2]
        sign = "+" if ch > 0 else ("\u2212" if ch < 0 else "")
        self.assertIn(">%s%d<" % (sign, abs(ch)), rows[-1])

    def test_countries_heatmap_and_other(self):
        c = self._panel("countries")
        self.assertIn('data-it="Altri paesi" data-en="Other countries"', c)
        self.assertNotIn("chart.other", c)
        self.assertGreaterEqual(c.count("<svg"), 2)
        self.assertIn(">%d<" % self.data["summary"]["students"], c)  # heatmap grand total

    def test_heatmap_level_legend(self):
        import demo_i18n
        it = demo_i18n.t("card.region_level.sub", "it")
        en = demo_i18n.t("card.region_level.sub", "en")
        self.assertIn("L = Laurea", it)
        self.assertIn("LM = Laurea Magistrale", it)
        self.assertIn("BA = Bachelor's", en)
        self.assertIn("MA = Master's", en)
        c = self._panel("countries")
        for short in ('data-it="L" data-en="BA"', 'data-it="LM" data-en="MA"'):
            self.assertIn(short, c)

    def test_deferral_kpi_has_figure(self):
        s = self.data["summary"]
        ov = self._panel("overview")
        kpi = re.search(r'data-i18n="kpi.deferrals".*?<div class="kpi-sub">(.*?)</div>', ov).group(1)
        pct = int(round(100.0 * s["deferrals"] / s["accepted"]))
        self.assertIn('<span class="kpi-num">%d%%</span>' % pct, kpi)

    def test_funnel_rates_state_base(self):
        import demo_i18n
        for k in ("conv.offer", "conv.accept", "conv.enrol", "conv.overall"):
            for lang in ("it", "en"):
                self.assertIn(" / ", demo_i18n.t(k, lang), (k, lang))
        self.assertIn('data-i18n="chart.of_prev"', self._panel("funnel"))

    def test_programme_and_fee_names(self):
        for p in self.data["programmes"]:
            self.assertIn('data-en="%s"' % p["name_en"].replace("'", "&#x27;"), self.html)
        f = self._panel("fees")
        total = sum(x["expected_eur"] for x in self.data["fees"])
        self.assertIn("{:,}".format(total).replace(",", "."), f)

    def test_one_app_script_and_node_check(self):
        import shutil, subprocess, tempfile, os
        scripts = re.findall(r"<script\b([^>]*)>(.*?)</script>", self.html, re.S)
        self.assertEqual(len(scripts), 1)
        self.assertIn('id="app"', scripts[0][0])
        node = shutil.which("node")
        if not node:
            self.skipTest("node not installed")
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "app.js")
            with open(p, "w", encoding="utf-8") as fh:
                fh.write(scripts[0][1])
            r = subprocess.run([node, "--check", p], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)

    def test_markup_balanced(self):
        from html.parser import HTMLParser
        void = {"meta", "br", "hr", "img", "input", "link", "source", "wbr", "col",
                "circle", "rect", "line", "polyline", "path"}
        problems = []

        class P(HTMLParser):
            def __init__(self):
                super().__init__()
                self.stack = []

            def handle_starttag(self, tag, attrs):
                if tag not in void:
                    self.stack.append(tag)

            def handle_startendtag(self, tag, attrs):
                pass

            def handle_endtag(self, tag):
                if tag in void:
                    return
                if not self.stack or self.stack[-1] != tag:
                    problems.append((tag, list(self.stack[-3:])))
                    return
                self.stack.pop()

        p = P()
        p.feed(self.html)
        self.assertEqual(problems, [])
        self.assertEqual(p.stack, [])

    STYLE_IDS = ["exec-light", "exec-dark", "command", "editorial"]
    STYLE_KEYS = {"bg", "panel", "panel-2", "ink", "ink-2", "line", "accent", "accent-2",
                  "accent-soft", "kpi-bg", "kpi-ink", "font-body", "font-num", "radius",
                  "shadow", "glow"}

    def test_styles_same_keys(self):
        import demo_build
        self.assertEqual(list(demo_build.STYLES), self.STYLE_IDS)
        self.assertEqual(demo_build.DEFAULT_STYLE, "exec-light")
        for sid, tokens in demo_build.STYLES.items():
            self.assertEqual(set(tokens), self.STYLE_KEYS, sid)
        S = demo_build.STYLES
        self.assertEqual(S["exec-light"]["accent"], "#0E7C86")
        self.assertEqual(S["exec-dark"]["accent"], "#3FC1C9")
        self.assertEqual(S["command"]["accent"], "#22D3EE")
        self.assertEqual(S["editorial"]["accent"], "#A0522D")
        self.assertNotEqual(S["command"]["glow"], "none")
        for sid in ("exec-light", "exec-dark", "editorial"):
            self.assertEqual(S[sid]["glow"], "none", sid)
        self.assertIn("monospace", S["command"]["font-num"])
        self.assertTrue(S["editorial"]["font-num"].startswith("Georgia"))
        self.assertEqual(S["editorial"]["shadow"], "none")
        for sid, tokens in S.items():
            for k, val in tokens.items():
                self.assertNotIn("url(", val, (sid, k))

    def test_no_banned_colour(self):
        import demo_build
        colours = [b.lower() for b in load_banned() if re.fullmatch(r"[0-9a-fA-F]{6}", b)]
        self.assertTrue(colours)
        for c in colours:
            self.assertNotIn(c, self.html.lower())
            for sid, tokens in demo_build.STYLES.items():
                for val in tokens.values():
                    self.assertNotIn(c, val.lower(), sid)

    def test_style_selectors(self):
        for sid in self.STYLE_IDS:
            self.assertRegex(self.html, r'\[data-style="%s"\]\s*[,{]' % re.escape(sid))
        self.assertIn('<html lang="it" data-style="exec-light">', self.html)

    def test_style_contrast(self):
        import demo_build

        def lum(hexv):
            h = hexv.lstrip("#")
            ch = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
            ch = [c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4 for c in ch]
            return 0.2126 * ch[0] + 0.7152 * ch[1] + 0.0722 * ch[2]

        def ratio(a, b):
            la, lb = sorted((lum(a), lum(b)), reverse=True)
            return (la + 0.05) / (lb + 0.05)

        for sid, t in demo_build.STYLES.items():
            for fg, bg, need in (("ink", "bg", 4.5), ("ink", "panel", 4.5), ("ink-2", "panel", 4.5),
                                 ("ink-2", "bg", 4.5), ("kpi-ink", "kpi-bg", 4.5),
                                 ("accent", "panel", 3.0), ("accent", "accent-soft", 3.0),
                                 ("ink", "accent-soft", 4.5), ("panel-2", "accent", 3.0)):
                self.assertGreaterEqual(ratio(t[fg], t[bg]), need, (sid, fg, bg))

    def test_style_switch(self):
        import demo_i18n
        ctl = re.search(r'<div class="controls" id="controls">(.*?)</div>', self.html, re.S)
        self.assertIsNotNone(ctl)
        inner = ctl.group(1)
        self.assertIn('data-i18n="ui.style"', inner)
        self.assertIn('id="style-select"', inner)
        opts = re.findall(r'<option value="([^"]+)"[^>]*data-i18n="([^"]+)"', inner)
        self.assertEqual([o[0] for o in opts], self.STYLE_IDS)
        for sid, key in opts:
            self.assertEqual(key, "style." + sid)
            for lang in ("it", "en"):
                self.assertIn(key, demo_i18n.LABELS[lang])
        self.assertIn('value="exec-light" selected', inner)

    def test_prefs_helpers(self):
        script = re.search(r'<script id="app">(.*?)</script>', self.html, re.S).group(1)
        prefs = re.search(r"/\*<prefs>\*/(.*?)/\*</prefs>\*/", script, re.S)
        self.assertIsNotNone(prefs)
        body = prefs.group(1)
        self.assertIn("function loadPref(key)", body)
        self.assertIn("function savePref(key, value)", body)
        self.assertEqual(body.count("try {"), 2)
        self.assertEqual(body.count("catch"), 2)
        rest = script.replace(prefs.group(0), "")
        self.assertNotIn("localStorage", rest)
        self.assertIn('"demo.style"', rest)

    def test_language_switch_and_config_hooks(self):
        self.assertEqual(self.html.count('data-setlang="'), 2)
        self.assertIn('data-setlang="it"', self.html)
        self.assertIn('data-setlang="en"', self.html)
        self.assertIn("/*<parseConfig>*/", self.html)
        self.assertIn("function applyConfig", self.html)
        self.assertIn("history.replaceState", self.html)
        self.assertIn("<title>Cruscotto ammissioni", self.html)
        self.assertNotIn("__LABELS__", self.html)
        self.assertNotIn("__DEFAULT_NAMES__", self.html)

    # ---- Task 7: one-page report
    def _print_css(self):
        start = self.html.index("@media print {")
        depth, i = 0, self.html.index("{", start)
        while True:
            ch = self.html[i]
            depth += ch == "{"
            depth -= ch == "}"
            if depth == 0:
                return self.html[start:i + 1]
            i += 1

    def _report(self):
        start = self.html.index('<section id="report"')
        return self.html[start:self.html.index("</section>", start)]

    def test_print_page_a4_landscape(self):
        css = self._print_css()
        self.assertEqual(self.html.count("@media print {"), 1)
        self.assertRegex(css, r"@page\s*\{[^}]*size:\s*A4 landscape;[^}]*margin:\s*10mm")
        self.assertIn("-webkit-print-color-adjust: exact", css)
        self.assertIn("print-color-adjust: exact", css.replace("-webkit-print-color-adjust", ""))
        for sel in (".tabs", ".controls", "main", ".notice"):
            self.assertRegex(css, r"%s[^{]*\{[^}]*display:\s*none" % re.escape(sel), sel)

    def test_print_css_forces_exec_light(self):
        import demo_build
        css = self._print_css()
        for k, val in demo_build.STYLES["exec-light"].items():
            self.assertIn("--%s: %s;" % (k, val), css, k)
        # beats [data-style="..."] on <html> (0,1,0) but stays below the inline --accent override
        self.assertIn(':root[data-style]', css)
        self.assertNotIn("!important", re.search(r":root\[data-style\][^{]*\{([^}]*)\}", css).group(1))

    def test_report_section(self):
        import demo_i18n
        self.assertEqual(self.html.count('id="report"'), 1)
        self._tag(r'<section id="report" class="print-only"[^>]*>')
        rep = self._report()
        self.assertIn('data-i18n="report.title"', rep)
        self.assertEqual(demo_i18n.t("report.title", "it"), "Report di sintesi · A.A. 2027/28")
        self.assertEqual(demo_i18n.t("report.title", "en"), "Summary report · Intake 2027/28")
        self.assertRegex(rep, r'data-uni-name[^>]*>%s<' % re.escape(demo_i18n.t("uni.default_name", "it")))
        self.assertEqual(rep.count('class="kpi"'), 6)
        self.assertEqual(rep.count('<article class="card'), 4)  # 3 cards + key points
        self.assertIn('data-i18n="ui.key_points"', rep)
        self.assertEqual(len(re.findall(r'data-lang="(?:it|en)"', rep)), 8)
        for k in ("card.enrolled_vs_target", "card.top_countries", "card.by_level",
                  "ui.source_line", "ui.demo_notice", "report.as_of"):
            self.assertIn('data-i18n="%s"' % k, rep, k)
        self.assertIn('data-it="15 lug 2027" data-en="15 Jul 2027"', rep)
        self.assertNotIn('<section class="panel"', rep)
        self.assertRegex(self.html, r"\.print-only\s*\{\s*display:\s*none;")

    def test_report_reuses_overview_builders(self):
        ov = self._panel("overview")
        rep = self._report()
        kpis = re.search(r'<div class="kpis">.*?</div></div></div>', ov).group(0)
        self.assertIn(kpis, rep)
        for svg in re.findall(r"<svg\b.*?</svg>", rep, re.S):
            self.assertIn(svg, ov)
        self.assertEqual(len(re.findall(r"<svg\b", rep)), 3)

    def test_download_button(self):
        import demo_i18n
        ctl = re.search(r'<div class="controls" id="controls">(.*?)</div>', self.html, re.S).group(1)
        btn = re.search(r'<button[^>]*id="report-btn"[^>]*>([^<]*)</button>', ctl)
        self.assertIsNotNone(btn)
        self.assertIn('data-i18n="ui.download_report"', btn.group(0))
        self.assertEqual(demo_i18n.t("ui.download_report", "it"), "Scarica report")
        self.assertEqual(demo_i18n.t("ui.download_report", "en"), "Download report")
        self.assertEqual(btn.group(1), "Scarica report")
        script = re.search(r'<script id="app">(.*?)</script>', self.html, re.S).group(1)
        self.assertIn("window.print()", script)
        self.assertIn("[data-uni-name]", script)

    def test_beforeafter_still_hidden_by_default(self):
        btn = self._tag(r'<button data-tab="beforeafter"[^>]*>')
        self.assertRegex(btn, r'\shidden[\s>]')
        self.assertNotIn("beforeafter", self._report())


    def test_deterministic_and_committed_file(self):
        import os, demo_build
        self.assertEqual(demo_build.render(build_dataset()), self.html)
        path = os.path.join(os.path.dirname(os.path.abspath(demo_build.__file__)), "demo.html")
        with open(path, encoding="utf-8") as fh:
            self.assertEqual(fh.read(), self.html)


if __name__ == "__main__":
    unittest.main()
