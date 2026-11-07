"""Tests for configure_build: the committed page equals render(), and the page's form,
preview, i18n keys and safety rules (no external requests, no banned strings)."""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import tempfile
import unittest
from html import unescape
from html.parser import HTMLParser

import configure_build
import demo_build
import demo_i18n

HERE = os.path.dirname(os.path.abspath(__file__))
TAB_IDS = ["overview", "weekly", "countries", "programmes", "natint",
           "funnel", "deferrals", "advisors", "fees"]
STYLE_IDS = ["exec-light", "exec-dark", "command", "editorial"]


def load_banned():
    """Banned strings live in a git-ignored local file; tests skip without it."""
    path = os.path.join(HERE, "local_banned_strings.json")
    if not os.path.exists(path):
        raise unittest.SkipTest("local_banned_strings.json not present")
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


class ConfigureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.html = configure_build.render()

    def _tags(self, pattern):
        return re.findall(pattern, self.html)

    def _one(self, pattern):
        m = self._tags(pattern)
        self.assertEqual(len(m), 1, pattern)
        return m[0]

    def test_committed_page_equals_render(self):
        with open(os.path.join(HERE, "configure.html"), encoding="utf-8") as fh:
            self.assertEqual(fh.read(), self.html)

    def test_core_markers_present(self):
        for name in ("buildDemoUrl", "formToCfg", "buildMailto"):
            self.assertIn("/*<%s>*/" % name, self.html)
            self.assertIn("/*</%s>*/" % name, self.html)
            self.assertIn("/*<%s>*/" % name, configure_build.CORE_JS)

    def test_core_style_and_tab_ids_match_the_demo(self):
        self.assertEqual(list(demo_build.STYLES), STYLE_IDS)
        self.assertIn(json.dumps(STYLE_IDS), configure_build.CORE_JS)
        self.assertIn(json.dumps(TAB_IDS), configure_build.CORE_JS)

    def test_nine_tab_checkboxes_ticked_and_flag_unticked(self):
        for tid in TAB_IDS:
            tag = self._one(r'<input type="checkbox" id="opt-%s"[^>]*>' % tid)
            self.assertIn(' checked', tag)
            self.assertIn('value="%s"' % tid, tag)
        self.assertEqual(len(self._tags(r'<input type="checkbox" id="opt-[a-z]+"')), 10)
        flag = self._one(r'<input type="checkbox" id="opt-beforeafter"[^>]*>')
        self.assertNotIn(" checked", flag)

    def test_four_style_radios(self):
        for sid in STYLE_IDS:
            tag = self._one(r'<input type="radio" name="style" id="style-%s"[^>]*>' % sid)
            self.assertIn('value="%s"' % sid, tag)
            self.assertEqual(" checked" in tag, sid == "exec-light", sid)
            self.assertIn('data-i18n="style.%s"' % sid, self.html)
            # The swatch is built from that style's tokens.
            toks = demo_build.STYLES[sid]
            card = self._one(r'<label class="style-card"[^>]*for="style-%s"[^>]*>' % sid)
            for k in ("bg", "panel", "accent", "kpi-bg"):
                self.assertIn(toks[k], card, (sid, k))

    def test_colour_input_and_reset(self):
        tag = self._one(r'<input type="color" id="colour"[^>]*>')
        self.assertIn('value="#0e7c86"', tag)
        self.assertIn('id="colour-reset"', self.html)
        self.assertIn('data-i18n="cfg.colour_reset"', self.html)

    def test_name_input(self):
        tag = self._one(r'<input type="text" id="uni"[^>]*>')
        self.assertIn('maxlength="80"', tag)

    def test_dashboard_language_radios(self):
        for lg in ("it", "en"):
            self._one(r'<input type="radio" name="dlang" id="dlang-%s" value="%s"[^>]*>' % (lg, lg))

    def test_preview_iframe(self):
        tag = self._one(r'<iframe id="preview"[^>]*>')
        self.assertIn('src="demo.html?style=exec-light&amp;lang=it"', tag)
        self.assertIn('title="', tag)
        self.assertNotIn("sandbox", tag)

    def test_sections_in_order_and_send_placeholder(self):
        keys = ["cfg.s1", "cfg.s2", "cfg.s3", "cfg.s4", "cfg.s5"]
        pos = [self.html.index('data-i18n="%s"' % k) for k in keys]
        self.assertEqual(pos, sorted(pos))
        send = self.html.index('<section id="send"')
        self.assertGreater(send, pos[-1])
        self.assertLess(send, self.html.index('<iframe id="preview"'))

    def test_header(self):
        self.assertIn("Giorgio Piccirillo", self.html)
        self.assertIn('href="index.html"', self.html)
        self.assertIn('data-setlang="it"', self.html)
        self.assertIn('data-setlang="en"', self.html)
        self.assertIn('<html lang="it">', self.html)
        self.assertEqual(demo_i18n.t("cfg.page_title", "it"), "Costruisci la tua dashboard")
        self.assertEqual(demo_i18n.t("cfg.page_title", "en"), "Build your dashboard")
        self.assertEqual(demo_i18n.t("cfg.no_tabs", "it"), "Scegli almeno una sezione qui sopra")
        self.assertEqual(demo_i18n.t("cfg.no_tabs", "en"), "Pick at least one section above")
        self.assertEqual(demo_i18n.t("cfg.colour_reset", "it"), "Usa il colore dello stile")
        self.assertEqual(demo_i18n.t("cfg.colour_reset", "en"), "Use the style's colour")
        self.assertIn("<title>Costruisci la tua dashboard</title>", self.html)

    def test_uses_executive_light_tokens(self):
        for k in ("bg", "panel", "line", "accent", "ink"):
            self.assertIn("--%s: %s;" % (k, demo_build.STYLES["exec-light"][k]), self.html)

    def test_i18n_keys_exist_and_text_is_italian(self):
        keys = set(re.findall(r'data-i18n(?:-[a-z]+)?="([^"]+)"', self.html))
        self.assertGreater(len(keys), 20)
        for k in keys:
            self.assertIn(k, demo_i18n.LABELS["it"], k)
            self.assertIn(k, demo_i18n.LABELS["en"], k)
        for k, txt in re.findall(r'data-i18n="([^"]+)"[^>]*>([^<]*)<', self.html):
            self.assertEqual(unescape(txt), demo_i18n.t(k, "it"), k)
        for attr in ("title", "ph"):
            real = {"title": "title", "ph": "placeholder"}[attr]
            for tag in re.findall(r'<[^>]*data-i18n-%s="[^"]+"[^>]*>' % attr, self.html):
                k = re.search(r'data-i18n-%s="([^"]+)"' % attr, tag).group(1)
                v = re.search(r'\s%s="([^"]*)"' % real, tag).group(1)
                self.assertEqual(unescape(v), demo_i18n.t(k, "it"), k)

    def test_no_external_requests(self):
        for pat in ('src="http', "src='http", 'href="http', "href='http", "@import",
                    "url(http", "url('http", 'url("http'):
            self.assertNotIn(pat, self.html, pat)
        self.assertNotIn("<link", self.html)

    def test_giorgio_address_is_not_a_plain_string(self):
        self.assertNotIn("giorgiopiccirillo89@gmail.com", self.html)
        self.assertNotIn("mailto:giorgio", self.html)

    def test_send_section_controls(self):
        send = re.search(r'<section id="send".*?</section>', self.html, re.S).group(0)
        for i in ("link-url", "link-copy", "link-open", "send-name", "send-role",
                  "send-email", "send-btn"):
            self.assertIn('id="%s"' % i, send, i)
        self.assertIn('type="email"', send)
        self.assertEqual(len(re.findall(r'<input type="email"', send)), 1)
        self.assertIn('readonly', re.search(r'<input[^>]*id="link-url"[^>]*>', send).group(0))
        self.assertIn('data-i18n="cfg.privacy"', send)
        self.assertEqual(demo_i18n.t("cfg.privacy", "it"),
                         "Nulla viene salvato su questo sito. 'Invia a Giorgio' apre la tua app email "
                         "con le tue scelte; decidi tu se inviarla.")
        self.assertEqual(demo_i18n.t("cfg.privacy", "en"),
                         "Nothing is saved on this site. 'Send to Giorgio' opens your own email app "
                         "with your choices; you decide whether to send it.")

    def test_contact_fields_are_never_stored(self):
        self.assertEqual(self.html.count("localStorage"), 2)
        self.assertNotIn("sessionStorage", self.html)
        prefs = re.search(r"/\*<prefs>\*/(.*?)/\*</prefs>\*/", self.html, re.S).group(1)
        names = ("send-name", "send-role", "send-email", "contactName", "contactRole",
                 "contactEmail")
        calls = re.findall(r"savePref\([^;]*;", self.html)
        self.assertTrue(calls)
        for call in calls:
            for fid in names:
                self.assertNotIn(fid, call)
        for fid in names:
            self.assertNotIn(fid, prefs)
        self.assertNotIn("cfg.s6", demo_i18n.LABELS["it"])

    def test_no_banned_strings(self):
        low = self.html.lower()
        for b in load_banned():
            self.assertNotIn(b.lower(), low)
        text = re.sub(r"<(style|script)\b.*?</\1>", " ", low, flags=re.S)
        text = re.sub(r"<[^>]+>", " ", text)
        self.assertIsNone(re.search(r"\b(correct|right|corretto)\b", text))

    def test_storage_only_through_prefs(self):
        self.assertEqual(self.html.count("localStorage"), 2)
        self.assertIn('"cfg.lang"', self.html)

    def test_inline_script_has_no_closing_sequence(self):
        scripts = re.findall(r"<script\b[^>]*>(.*?)</script>", self.html, re.S)
        for body in scripts:
            # the /*</name>*/ test markers are comments inside a script, not tags
            self.assertNotIn("</", re.sub(r"/\*</\w+>\*/", "", body))

    def test_one_app_script_and_node_check(self):
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

    def test_selected_and_focused_style_without_has(self):
        css = re.search(r"<style>(.*?)</style>", self.html, re.S).group(1)
        rules = [r.strip() for r in re.findall(r"([^{}]+)\{", css)]
        checked = [r for r in rules if "input:checked ~" in r and ":has(" not in r]
        focused = [r for r in rules if "input:focus-visible ~" in r and ":has(" not in r]
        self.assertTrue(checked)
        self.assertTrue(focused)
        # The radio comes before the card content, so sibling selectors reach it.
        for sid in STYLE_IDS:
            card = re.search(r'<label class="style-card"[^>]*for="style-%s".*?</label>' % sid,
                             self.html, re.S).group(0)
            self.assertLess(card.index('<input type="radio"'), card.index('class="sw"'))

    def test_no_static_aria_labels(self):
        for tag in re.findall(r"<[^>]*\saria-label=[^>]*>", self.html):
            self.assertIn("data-i18n-aria=", tag)
        for ref in re.findall(r'aria-labelledby="([^"]+)"', self.html):
            for rid in ref.split():
                tag = self._one(r'<[^>]*\sid="%s"[^>]*>' % re.escape(rid))
                self.assertIn("data-i18n=", tag, rid)
        self._one(r'<label class="vh" for="colour" data-i18n="cfg.colour_label">')

    def test_no_tabs_message_describes_the_tab_fieldset(self):
        tag = self._one(r'<fieldset[^>]*id="tabs-set"[^>]*>')
        self.assertIn('aria-describedby="tabs-error"', tag)

    def test_demo_does_not_carry_configurator_labels(self):
        import demo_data
        demo = demo_build.render(demo_data.build_dataset())
        self.assertNotIn('"cfg.', demo)
        self.assertIn('"tab.overview"', demo)

    def test_markup_balanced(self):
        void = {"meta", "br", "hr", "img", "input", "link", "source", "wbr", "col"}
        problems = []

        class P(HTMLParser):
            def __init__(self):
                super().__init__()
                self.stack = []

            def handle_starttag(self, tag, attrs):
                if tag not in void:
                    self.stack.append(tag)

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


if __name__ == "__main__":
    unittest.main()
