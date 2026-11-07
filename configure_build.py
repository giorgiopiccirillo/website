"""Build configure.html: the "Build your dashboard" configurator page.

CORE_JS holds the page's pure, testable JavaScript, as marker-delimited
functions (/*<name>*/ ... /*</name>*/) so tests can extract them. UI_JS wires
the form to the live preview. render() returns the page; main() writes
configure.html beside this file. The page uses the demo's Executive light
tokens and its own IT|EN switch (default IT, remembered as "cfg.lang").
"""

from __future__ import annotations

import json
import os
from html import escape

import demo_build
import demo_i18n

TAB_IDS = [t for t in demo_i18n.TABS if t not in demo_build.FLAGGED]
STYLE_IDS = list(demo_build.STYLES)
PAGE_TOKENS = demo_build.STYLES["exec-light"]

CORE_JS = r"""
/*<buildDemoUrl>*/
var DEMO_DEFAULT_STYLE = "exec-light";
var DEMO_DEFAULT_TABS = ["overview", "weekly", "countries", "programmes", "natint",
  "funnel", "deferrals", "advisors", "fees"];
var DEMO_FLAGGED_TABS = { beforeafter: "beforeafter" };

function buildDemoUrl(cfg, base) {
  var q = new URLSearchParams();
  // Always explicit: the demo fills a missing style from the viewer's last-used one.
  q.set("style", cfg.style || DEMO_DEFAULT_STYLE);
  q.set("lang", cfg.lang);
  var flags = (cfg.flags || []).filter(function (f, i, a) { return a.indexOf(f) === i; });
  // The demo appends a flag's tab itself, last, so it is left out of the list.
  var tabs = (cfg.tabs || []).filter(function (id) { return !DEMO_FLAGGED_TABS[id]; });
  var isDefault = tabs.length === DEMO_DEFAULT_TABS.length &&
    tabs.every(function (id, i) { return id === DEMO_DEFAULT_TABS[i]; });
  if (tabs.length && !isDefault) { q.set("tabs", tabs.join(",")); }
  var name = Array.from(String(cfg.name || "").trim()).slice(0, 80).join("").trim();
  if (name) { q.set("name", name); }
  if (cfg.accent) { q.set("accent", cfg.accent); }
  if (flags.length) { q.set("flag", flags.join(",")); }
  return base + "?" + q.toString();
}
/*</buildDemoUrl>*/

/*<formToCfg>*/
var FORM_STYLE_IDS = ["exec-light", "exec-dark", "command", "editorial"];
var FORM_TAB_IDS = ["overview", "weekly", "countries", "programmes", "natint", "funnel", "deferrals", "advisors", "fees"];

// state = {name, tabs: ticked tab ids (any order), beforeafter: bool,
//          style, accent: "#rrggbb" | "rrggbb" | null, lang}
// -> cfg for buildDemoUrl, or {error: "no_tabs"} when no section is ticked.
function formToCfg(state) {
  var ticked = state.tabs || [];
  var tabs = FORM_TAB_IDS.filter(function (id) { return ticked.indexOf(id) >= 0; });
  if (!tabs.length) { return { error: "no_tabs" }; }
  var hex = String(state.accent || "").replace(/^#/, "");
  return {
    style: FORM_STYLE_IDS.indexOf(state.style) >= 0 ? state.style : FORM_STYLE_IDS[0],
    lang: state.lang === "en" ? "en" : "it",
    tabs: tabs,
    name: String(state.name || ""),
    accent: /^[0-9a-fA-F]{6}$/.test(hex) ? hex.toUpperCase() : null,
    flags: state.beforeafter ? ["beforeafter"] : []
  };
}
/*</formToCfg>*/

/*<buildMailto>*/
// labels: the page-language LABELS dict (tab.*, style.*, cfg.mail_*, ...).
// cfg: a formToCfg result; contact: {name, role, email}, all optional.
// The result is never longer than MAIL_MAX characters: it is shortened in
// steps (subject without the name, shorter contact details, no embedded link).
var MAIL_MAX = 1800;
function buildMailto(cfg, contact, labels) {
  if (!cfg || cfg.error) { return ""; }
  contact = contact || {};
  var to = "giorgiopiccirillo89" + "@" + "gmail.com";
  var L = function (k) { return labels[k] || k; };
  var cut = function (v, n) { return Array.from(String(v)).slice(0, n).join("").trim(); };
  var clean = function (v, n) {
    return cut(String(v || "").replace(/\s+/g, " ").trim(), n) || "\u2014";
  };
  var uni = cut(String(cfg.name || "").trim(), 80) || L("uni.default_name");
  var ids = (cfg.tabs || []).concat(cfg.flags || []);
  var sections = ids.filter(function (id, i) { return ids.indexOf(id) === i; })
    .map(function (id) { return L("tab." + id); }).join(", ");
  var colour = cfg.accent ? "#" + cfg.accent : L("cfg.colour_from_style");
  var link = buildDemoUrl(cfg, "https://giorgiopiccirillo.com/demo.html");
  var fallbackLink = L("cfg.mail_link_long") + " https://giorgiopiccirillo.com/configure.html";
  function make(o) {
    var u = cut(uni, o.uniMax);
    var body = [
      L("cfg.mail_university") + ": " + u,
      L("cfg.mail_role") + ": " + clean(contact.role, o.max),
      L("cfg.mail_name") + ": " + clean(contact.name, o.max),
      L("cfg.mail_email") + ": " + clean(contact.email, o.max),
      L("cfg.mail_sections") + ": " + sections,
      L("cfg.mail_style") + ": " + L("style." + cfg.style),
      L("cfg.mail_colour") + ": " + colour,
      L("cfg.mail_dashlang") + ": " + (cfg.lang === "en" ? "English" : "Italiano"),
      o.link ? L("cfg.mail_link") + ": " + link : fallbackLink
    ].join("\r\n");
    var subject = L("cfg.mail_subject") + (o.subjectName ? " \u2014 " + u : "");
    return "mailto:" + to + "?subject=" + encodeURIComponent(subject) +
      "&body=" + encodeURIComponent(body);
  }
  var steps = [
    { subjectName: true, max: 80, uniMax: 80, link: true },
    { subjectName: false, max: 80, uniMax: 80, link: true },
    { subjectName: false, max: 40, uniMax: 80, link: true },
    { subjectName: false, max: 40, uniMax: 80, link: false },
    { subjectName: false, max: 20, uniMax: 40, link: false },
    { subjectName: false, max: 10, uniMax: 20, link: false }
  ];
  var out = "";
  for (var i = 0; i < steps.length; i++) {
    out = make(steps[i]);
    if (out.length <= MAIL_MAX) { return out; }
  }
  return out;
}
/*</buildMailto>*/
"""

UI_JS = r"""
(function () {
  "use strict";
  var LABELS = __LABELS__;
  var STYLE_ACCENTS = __STYLE_ACCENTS__;
  var LANG_KEY = "cfg.lang";

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

  var form = document.getElementById("cfg-form");
  var frame = document.getElementById("preview");
  var nameInput = document.getElementById("uni");
  var colour = document.getElementById("colour");
  var colourReset = document.getElementById("colour-reset");
  var colourValue = document.getElementById("colour-value");
  var colourFromStyle = document.getElementById("colour-from-style");
  var tabsError = document.getElementById("tabs-error");
  var linkUrl = document.getElementById("link-url");
  var linkCopy = document.getElementById("link-copy");
  var linkOpen = document.getElementById("link-open");
  var linkCopied = document.getElementById("link-copied");
  var sendBtn = document.getElementById("send-btn");
  var contactName = document.getElementById("send-name");
  var contactRole = document.getElementById("send-role");
  var contactEmail = document.getElementById("send-email");
  var linkHint = document.getElementById("link-copy-hint");
  var currentLang = "it";
  var copiedTimer = null;
  var langButtons = Array.prototype.slice.call(document.querySelectorAll("[data-setlang]"));
  var accent = null;  // null until the visitor touches the picker
  var lastUrl = frame.getAttribute("src");
  var timer = null;

  function checkedValue(name) {
    var el = form.querySelector('input[name="' + name + '"]:checked');
    return el ? el.value : null;
  }

  function readState() {
    var tabs = Array.prototype.map.call(
      form.querySelectorAll('input[name="tab"]:checked'), function (el) { return el.value; });
    return {
      name: nameInput.value,
      tabs: tabs,
      beforeafter: document.getElementById("opt-beforeafter").checked,
      style: checkedValue("style"),
      accent: accent,
      lang: checkedValue("dlang")
    };
  }

  function showColour() {
    var custom = accent !== null;
    colourReset.disabled = !custom;
    colourFromStyle.hidden = custom;
    colourValue.hidden = !custom;
    colourValue.textContent = custom ? accent.toUpperCase() : "";
    if (!custom) { colour.value = STYLE_ACCENTS[checkedValue("style")] || colour.value; }
  }

  function refreshSend() {
    var cfg = window.currentCfg;
    var blocked = !cfg || !!cfg.error;
    var link = blocked ? "" : buildDemoUrl(cfg, "https://giorgiopiccirillo.com/demo.html");
    linkUrl.value = link;
    linkCopy.disabled = blocked;
    if (blocked) {
      linkOpen.removeAttribute("href");
      linkOpen.setAttribute("aria-disabled", "true");
      sendBtn.removeAttribute("href");
      sendBtn.setAttribute("aria-disabled", "true");
      return;
    }
    linkOpen.setAttribute("href", link);
    linkOpen.removeAttribute("aria-disabled");
    sendBtn.setAttribute("href", buildMailto(cfg, {
      name: contactName.value, role: contactRole.value, email: contactEmail.value
    }, LABELS[currentLang]));
    sendBtn.removeAttribute("aria-disabled");
  }

  linkCopy.addEventListener("click", function () {
    if (linkCopy.disabled) { return; }
    var done = function () {
      linkCopied.hidden = false;
      clearTimeout(copiedTimer);
      copiedTimer = setTimeout(function () { linkCopied.hidden = true; }, 2000);
    };
    var fallback = function () {
      linkUrl.focus();
      linkUrl.select();
      var ok = false;
      try { ok = document.execCommand("copy"); } catch (e) { ok = false; }
      if (ok) { done(); } else { linkHint.hidden = false; }
    };
    linkHint.hidden = true;
    try {
      navigator.clipboard.writeText(linkUrl.value).then(done, fallback);
    } catch (e) {
      fallback();
    }
  });
  linkUrl.addEventListener("focus", function () { linkUrl.select(); });
  [linkOpen, sendBtn].forEach(function (a) {
    a.addEventListener("click", function (e) {
      if (a.getAttribute("aria-disabled") === "true") { e.preventDefault(); }
    });
  });

  // The current cfg, or {error}; the link box and Send read it too.
  function update(now) {
    var cfg = formToCfg(readState());
    var blocked = !!cfg.error;
    tabsError.hidden = !blocked;
    form.toggleAttribute("data-blocked", blocked);
    window.currentCfg = cfg;
    refreshSend();
    if (blocked) { clearTimeout(timer); return; }
    var url = buildDemoUrl(cfg, "demo.html");
    clearTimeout(timer);
    var go = function () {
      if (url !== lastUrl) { lastUrl = url; frame.src = url; }
    };
    if (now) { go(); } else { timer = setTimeout(go, 250); }
  }

  function setOwnText(el, text) {
    var n = el.firstChild;
    while (n && n.nodeType !== 3) { n = n.nextSibling; }
    if (n) { n.data = text; } else { el.insertBefore(document.createTextNode(text), el.firstChild); }
  }

  // Changes only the configurator's own labels, never the dashboard language.
  function setPageLang(lang) {
    lang = lang === "en" ? "en" : "it";
    var dict = LABELS[lang];
    document.documentElement.setAttribute("lang", lang);
    Array.prototype.forEach.call(document.querySelectorAll("[data-i18n]"), function (el) {
      var v = dict[el.getAttribute("data-i18n")];
      if (typeof v === "string") { setOwnText(el, v); }
    });
    Array.prototype.forEach.call(document.querySelectorAll("[data-i18n-title]"), function (el) {
      var v = dict[el.getAttribute("data-i18n-title")];
      if (typeof v === "string") { el.setAttribute("title", v); }
    });
    Array.prototype.forEach.call(document.querySelectorAll("[data-i18n-ph]"), function (el) {
      var v = dict[el.getAttribute("data-i18n-ph")];
      if (typeof v === "string") { el.setAttribute("placeholder", v); }
    });
    document.title = dict["cfg.page_title"];
    currentLang = lang;
    if (typeof refreshSend === "function" && window.currentCfg) { refreshSend(); }
    langButtons.forEach(function (b) {
      b.setAttribute("aria-pressed", b.getAttribute("data-setlang") === lang ? "true" : "false");
    });
    return lang;
  }

  langButtons.forEach(function (b) {
    b.addEventListener("click", function () {
      savePref(LANG_KEY, setPageLang(b.getAttribute("data-setlang")));
    });
  });

  colour.addEventListener("input", function () {
    accent = colour.value;
    showColour();
    update(false);
  });
  colourReset.addEventListener("click", function () {
    accent = null;
    showColour();
    update(false);
    colour.focus();
  });
  form.addEventListener("submit", function (e) { e.preventDefault(); });
  form.addEventListener("input", function (e) {
    if (e.target === colour) { return; }
    if (e.target.name === "style") { showColour(); }
    update(false);
  });
  form.addEventListener("change", function (e) {
    if (e.target === colour) { return; }
    if (e.target.name === "style") { showColour(); }
    update(false);
  });

  // Start: page language from the saved choice (default IT); the dashboard
  // language starts equal to it, then stays independent of the page switch.
  var pageLang = setPageLang(loadPref(LANG_KEY) || "it");
  document.getElementById("dlang-" + pageLang).checked = true;
  showColour();
  update(true);
})();
"""

CSS = """
:root {
__TOKENS__
}
* { box-sizing: border-box; }
html { -webkit-text-size-adjust: 100%; }
body { margin: 0; background: var(--bg); color: var(--ink); font-family: var(--font-body);
  font-size: 15px; line-height: 1.45; }
a { color: var(--accent); }
.wrap { max-width: 1440px; margin: 0 auto; padding: 18px 24px 40px; }
.top { display: flex; flex-wrap: wrap; align-items: center; justify-content: space-between;
  gap: 10px 24px; padding-bottom: 14px; border-bottom: 1px solid var(--line); }
.who { min-width: 0; }
.brand { display: block; color: var(--ink-2); font-size: 13px; font-weight: 600; }
h1 { margin: 2px 0 0; font-size: 26px; line-height: 1.2; font-weight: 700; letter-spacing: -0.01em; }
.top-ctl { display: flex; flex-wrap: wrap; align-items: center; gap: 10px 16px; font-size: 13px; }
.back { font-weight: 600; text-decoration: none; }
.back:hover { text-decoration: underline; }
.seg { display: inline-flex; border: 1px solid var(--line); border-radius: 6px; overflow: hidden; }
.seg button { font: inherit; font-size: 13px; font-weight: 600; border: 0; background: var(--panel);
  color: var(--ink-2); padding: 5px 10px; cursor: pointer; }
.seg button + button { border-left: 1px solid var(--line); }
.seg button[aria-pressed="true"] { background: var(--accent); color: #FFFFFF; }
.seg button:focus-visible { outline: 2px solid var(--accent); outline-offset: -2px; }
.intro { margin: 14px 0 18px; color: var(--ink-2); font-size: 14px; max-width: 70ch; }
.layout { display: grid; grid-template-columns: minmax(0, 1fr); gap: 20px; align-items: start; }
.card { background: var(--panel); border: 1px solid var(--line); border-radius: var(--radius);
  padding: 16px 18px; box-shadow: var(--shadow); min-width: 0; }
form { display: grid; gap: 14px; min-width: 0; }
fieldset.card { margin: 0; }
legend, .card h2 { padding: 0; font-size: 15px; font-weight: 700; margin: 0 0 10px; }
fieldset.card legend { float: left; width: 100%; }
fieldset.card legend + * { clear: both; }
.num { display: inline-flex; align-items: center; justify-content: center; width: 22px; height: 22px;
  margin-right: 8px; border-radius: 50%; background: var(--accent-soft); color: var(--accent);
  font-size: 12px; font-weight: 700; vertical-align: 1px; }
.hint { margin: 6px 0 0; color: var(--ink-2); font-size: 12px; }
.field-label { display: block; font-size: 13px; font-weight: 600; margin-bottom: 6px; }
.checks { display: grid; grid-template-columns: repeat(auto-fill, minmax(190px, 1fr)); gap: 6px 14px; }
.check { display: flex; align-items: flex-start; gap: 8px; font-size: 14px; cursor: pointer; padding: 3px 0; }
.check input { margin: 3px 0 0; accent-color: var(--accent); width: 16px; height: 16px; flex: 0 0 auto; }
.extra { margin-top: 12px; padding-top: 10px; border-top: 1px solid var(--line); }
.extra-head { display: block; font-size: 12px; font-weight: 600; color: var(--ink-2);
  text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 4px; }
.check small { display: block; color: var(--ink-2); font-size: 12px; }
.error { margin: 10px 0 0; padding: 8px 10px; border-radius: 6px; background: #FDECEC;
  color: #9B1C1C; font-size: 13px; font-weight: 600; }
.error[hidden] { display: none; }
.styles { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 10px; }
.style-card { position: relative; display: block; border: 1px solid var(--line); border-radius: 8px;
  padding: 8px; cursor: pointer; background: var(--panel); }
.style-card:hover { border-color: var(--ink-2); }
.style-card:has(input:checked) { border-color: var(--accent); box-shadow: 0 0 0 1px var(--accent); }
.style-card:has(input:focus-visible) { outline: 2px solid var(--accent); outline-offset: 2px; }
.style-card input { position: absolute; opacity: 0; width: 1px; height: 1px; margin: 0; }
.style-card input:checked ~ .sw { outline: 2px solid var(--accent); outline-offset: 2px; }
.style-card input:checked ~ .style-name .tick { border: 5px solid var(--accent); }
.style-card input:focus-visible ~ .sw { outline: 2px solid var(--accent); outline-offset: 2px;
  box-shadow: 0 0 0 4px var(--accent-soft); }
.vh { position: absolute; width: 1px; height: 1px; padding: 0; margin: -1px; overflow: hidden;
  clip: rect(0, 0, 0, 0); white-space: nowrap; border: 0; }
.sw { display: grid; grid-template-columns: 1fr 1.6fr; gap: 5px; height: 58px; padding: 6px;
  border-radius: 4px; background: var(--sw-bg); border: 1px solid rgba(0, 0, 0, 0.08); }
.sw-kpi { border-radius: 3px; background: var(--sw-kpi); }
.sw-panel { border-radius: 3px; background: var(--sw-panel); padding: 6px; display: flex;
  flex-direction: column; justify-content: flex-end; gap: 4px; }
.sw-bar { display: block; height: 6px; border-radius: 2px; background: var(--sw-accent); width: 85%; }
.sw-bar + .sw-bar { width: 55%; opacity: 0.6; }
.style-name { display: flex; align-items: center; justify-content: space-between; gap: 6px;
  margin-top: 7px; font-size: 13px; font-weight: 600; }
.tick { width: 16px; height: 16px; border-radius: 50%; border: 1px solid var(--line); flex: 0 0 auto; }
.colour-row { display: flex; flex-wrap: wrap; align-items: center; gap: 10px 14px; }
input[type="color"] { width: 52px; height: 36px; padding: 2px; border: 1px solid var(--line);
  border-radius: 6px; background: var(--panel); cursor: pointer; }
input[type="color"]:focus-visible { outline: 2px solid var(--accent); outline-offset: 1px; }
.colour-state { font-size: 13px; color: var(--ink-2); font-variant-numeric: tabular-nums; }
.btn { font: inherit; font-size: 13px; font-weight: 600; color: var(--accent); background: var(--panel);
  border: 1px solid var(--line); border-radius: 6px; padding: 6px 10px; cursor: pointer; }
.btn:hover:not(:disabled) { border-color: var(--accent); }
.btn:disabled { color: var(--ink-2); opacity: 0.6; cursor: default; }
.btn:focus-visible { outline: 2px solid var(--accent); outline-offset: 1px; }
.radios { display: flex; flex-wrap: wrap; gap: 6px 22px; }
.radios .check input { accent-color: var(--accent); }
#send { display: grid; gap: 14px; min-width: 0; }
input[type="text"], input[type="email"] { width: 100%; font: inherit; color: var(--ink); background: var(--panel);
  border: 1px solid var(--line); border-radius: 6px; padding: 8px 10px; }
input[type="text"]:focus-visible, input[type="email"]:focus-visible { outline: 2px solid var(--accent);
  outline-offset: 0; border-color: var(--accent); }
#link-url { font-size: 13px; text-overflow: ellipsis; }
.btn-row { display: flex; flex-wrap: wrap; align-items: center; gap: 8px 10px; margin-top: 10px; }
a.btn { display: inline-block; text-decoration: none; }
a.btn[aria-disabled="true"] { color: var(--ink-2); opacity: 0.6; cursor: default; pointer-events: none; }
.btn-primary { background: var(--accent); color: #FFFFFF; border-color: var(--accent); padding: 8px 14px; }
a.btn-primary[aria-disabled="true"] { color: #FFFFFF; }
.copied { font-size: 13px; color: var(--ink-2); }
.copied[hidden] { display: none; }
.contact { display: grid; gap: 10px; margin-top: 8px; }
.send-hint { margin: 0 0 4px; }
.preview { min-width: 0; padding: 12px; }
.preview h2 { margin: 0 0 10px 4px; font-size: 13px; font-weight: 700; color: var(--ink-2);
  text-transform: uppercase; letter-spacing: 0.05em; }
#preview { display: block; width: 100%; height: 900px; border: 1px solid var(--line);
  border-radius: 6px; background: var(--bg); }
@media (min-width: 1000px) {
  .layout { grid-template-columns: minmax(0, 4fr) minmax(0, 6fr); gap: 24px; }
  .preview { position: sticky; top: 16px; }
  #preview { height: calc(100vh - 80px); min-height: 560px; }
}
@media (max-width: 480px) {
  .wrap { padding: 14px 16px 32px; }
  h1 { font-size: 22px; }
  .card { padding: 14px; }
}
"""

PAGE = """<!doctype html>
<html lang="it">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>__TITLE__</title>
<style>__CSS__</style>
</head>
<body>
<div class="wrap">
<header class="top">
  <div class="who">
    <span class="brand">Giorgio Piccirillo</span>
    <h1 data-i18n="cfg.page_title">__TITLE__</h1>
  </div>
  <div class="top-ctl">
    <span class="vh" id="page-lang-label" data-i18n="cfg.page_language">__PAGE_LANG__</span><span class="seg" role="group" aria-labelledby="page-lang-label">__LANG_BTNS__</span>
    <a class="back" href="index.html" data-i18n="cfg.back">__BACK__</a>
  </div>
</header>
<p class="intro" data-i18n="cfg.intro">__INTRO__</p>
<div class="layout">
<form id="cfg-form" novalidate>
__SECTIONS__
<section id="send">__SEND__</section>
</form>
<section class="card preview" aria-labelledby="preview-head">
  <h2 id="preview-head" data-i18n="cfg.preview">__PREVIEW__</h2>
  <iframe id="preview" title="__PREVIEW_TITLE__" data-i18n-title="cfg.preview_title" src="demo.html?style=exec-light&amp;lang=it" loading="lazy"></iframe>
</section>
</div>
</div>
<script id="app">
__JS__
</script>
</body>
</html>
"""


def _q(s: object) -> str:
    return escape(str(s), quote=True)


def _t(key: str) -> str:
    return _q(demo_i18n.t(key, "it"))


def _i18n(tag: str, key: str, attrs: str = "") -> str:
    return f'<{tag}{attrs} data-i18n="{key}">{_t(key)}</{tag}>'


def _legend(n: int, key: str) -> str:
    return f'<legend><span class="num" aria-hidden="true">{n}</span>{_i18n("span", key)}</legend>'


def _sections() -> str:
    s1 = (f'<fieldset class="card">{_legend(1, "cfg.s1")}<div>'
          f'<label class="field-label" for="uni" data-i18n="cfg.name_label">{_t("cfg.name_label")}</label>'
          f'<input type="text" id="uni" name="uni" maxlength="80" autocomplete="organization" '
          f'placeholder="{_t("cfg.name_ph")}" data-i18n-ph="cfg.name_ph" aria-describedby="uni-hint">'
          f'<p class="hint" id="uni-hint" data-i18n="cfg.name_hint">{_t("cfg.name_hint")}</p>'
          f'</div></fieldset>')

    checks = "".join(
        f'<label class="check" for="opt-{tid}"><input type="checkbox" id="opt-{tid}" name="tab" '
        f'value="{tid}" checked>{_i18n("span", "tab." + tid)}</label>' for tid in TAB_IDS)
    s2 = (f'<fieldset class="card" id="tabs-set" aria-describedby="tabs-error">{_legend(2, "cfg.s2")}<div>'
          f'<div class="checks">{checks}</div>'
          f'<p class="hint" data-i18n="cfg.s2_hint">{_t("cfg.s2_hint")}</p>'
          f'<p class="error" id="tabs-error" role="alert" hidden data-i18n="cfg.no_tabs">{_t("cfg.no_tabs")}</p>'
          f'<div class="extra">{_i18n("span", "cfg.extra", " class=" + chr(34) + "extra-head" + chr(34))}'
          f'<label class="check" for="opt-beforeafter"><input type="checkbox" id="opt-beforeafter" '
          f'name="flag" value="beforeafter"><span>{_i18n("span", "tab.beforeafter")}'
          f'{_i18n("small", "tab.beforeafter.sub")}</span></label></div>'
          f'</div></fieldset>')

    cards = []
    for sid, toks in demo_build.STYLES.items():
        style = (f'--sw-bg: {toks["bg"]}; --sw-panel: {toks["panel"]}; '
                 f'--sw-accent: {toks["accent"]}; --sw-kpi: {toks["kpi-bg"]};')
        checked = " checked" if sid == demo_build.DEFAULT_STYLE else ""
        cards.append(
            f'<label class="style-card" style="{style}" for="style-{sid}">'
            f'<input type="radio" name="style" id="style-{sid}" value="{sid}"{checked}>'
            f'<span class="sw" aria-hidden="true"><span class="sw-kpi"></span>'
            f'<span class="sw-panel"><span class="sw-bar"></span><span class="sw-bar"></span></span></span>'
            f'<span class="style-name">{_i18n("span", "style." + sid)}'
            f'<span class="tick" aria-hidden="true"></span></span></label>')
    s3 = f'<fieldset class="card">{_legend(3, "cfg.s3")}<div class="styles">{"".join(cards)}</div></fieldset>'

    default_accent = PAGE_TOKENS["accent"].lower()
    s4 = (f'<fieldset class="card">{_legend(4, "cfg.s4")}<div class="colour-row">'
          f'<label class="vh" for="colour" data-i18n="cfg.colour_label">{_t("cfg.colour_label")}</label>'
          f'<input type="color" id="colour" value="{default_accent}" '
          f'data-i18n-title="cfg.colour_label" title="{_t("cfg.colour_label")}">'
          f'<span class="colour-state"><span id="colour-from-style" data-i18n="cfg.colour_from_style">'
          f'{_t("cfg.colour_from_style")}</span><span id="colour-value" hidden></span></span>'
          f'<button type="button" class="btn" id="colour-reset" disabled data-i18n="cfg.colour_reset">'
          f'{_t("cfg.colour_reset")}</button></div></fieldset>')

    radios = "".join(
        f'<label class="check" for="dlang-{lg}"><input type="radio" name="dlang" id="dlang-{lg}" '
        f'value="{lg}"{" checked" if lg == "it" else ""}><span lang="{lg}">{word}</span></label>'
        for lg, word in (("it", "Italiano"), ("en", "English")))
    s5 = f'<fieldset class="card">{_legend(5, "cfg.s5")}<div class="radios">{radios}</div></fieldset>'
    return "\n".join([s1, s2, s3, s4, s5])



def _send() -> str:
    link = (f'<div class="card"><h2>{_i18n("span", "cfg.link_title")}</h2>'
            f'<label class="vh" for="link-url" data-i18n="cfg.link_title">{_t("cfg.link_title")}</label>'
            f'<input type="text" id="link-url" readonly aria-describedby="link-hint" value="">'
            f'<p class="hint" id="link-hint" data-i18n="cfg.link_hint">{_t("cfg.link_hint")}</p>'
            f'<div class="btn-row"><button type="button" class="btn" id="link-copy" '
            f'data-i18n="cfg.link_copy">{_t("cfg.link_copy")}</button>'
            f'<a class="btn" id="link-open" target="_blank" rel="noopener" '
            f'data-i18n="cfg.link_open">{_t("cfg.link_open")}</a>'
            f'<span class="copied" id="link-copy-hint" role="status" hidden '
            f'data-i18n="cfg.link_copy_hint">{_t("cfg.link_copy_hint")}</span>'
            f'<span class="copied" id="link-copied" role="status" hidden '
            f'data-i18n="cfg.link_copied">{_t("cfg.link_copied")}</span></div></div>')

    def field(fid: str, typ: str, key: str, auto: str) -> str:
        return (f'<div><label class="field-label" for="{fid}" data-i18n="{key}">{_t(key)}</label>'
                f'<input type="{typ}" id="{fid}" maxlength="80" autocomplete="{auto}"></div>')

    send = (f'<div class="card"><h2>{_i18n("span", "cfg.send_title")}</h2>'
            f'<p class="hint send-hint" data-i18n="cfg.send_hint">{_t("cfg.send_hint")}</p>'
            f'<div class="contact">{field("send-name", "text", "cfg.contact_name", "name")}'
            f'{field("send-role", "text", "cfg.contact_role", "organization-title")}'
            f'{field("send-email", "email", "cfg.contact_email", "email")}</div>'
            f'<div class="btn-row"><a class="btn btn-primary" id="send-btn" '
            f'data-i18n="cfg.send_btn">{_t("cfg.send_btn")}</a></div>'
            f'<p class="hint" data-i18n="cfg.privacy">{_t("cfg.privacy")}</p></div>')
    return link + send


def _page_labels() -> dict:
    keys = [k for k in demo_i18n.LABELS["it"]
            if k.startswith("cfg.") or k.startswith("style.") or k in
            ["tab." + t for t in demo_i18n.TABS] + ["tab.beforeafter.sub", "uni.default_name"]]
    return {lg: {k: demo_i18n.LABELS[lg][k] for k in keys} for lg in ("it", "en")}


def render() -> str:
    tokens = "\n".join(f"  --{k}: {v};" for k, v in PAGE_TOKENS.items())
    tokens += f"\n  --accent-text: {PAGE_TOKENS['accent']};"
    lang_btns = "".join(
        f'<button type="button" data-setlang="{lg}" lang="{lg}" aria-pressed="{"true" if lg == "it" else "false"}">'
        f'{lg.upper()}</button>' for lg in ("it", "en"))
    style_accents = {sid: toks["accent"].lower() for sid, toks in demo_build.STYLES.items()}
    ui = (UI_JS.strip("\n")
          .replace("__LABELS__", json.dumps(_page_labels(), ensure_ascii=False, sort_keys=True).replace("</", "<\\/"))
          .replace("__STYLE_ACCENTS__", json.dumps(style_accents)))
    js = CORE_JS.strip("\n") + "\n\n" + ui
    return (PAGE
            .replace("__CSS__", CSS.replace("__TOKENS__", tokens))
            .replace("__SECTIONS__", _sections())
            .replace("__SEND__", _send())
            .replace("__LANG_BTNS__", lang_btns)
            .replace("__TITLE__", _t("cfg.page_title"))
            .replace("__PAGE_LANG__", _t("cfg.page_language"))
            .replace("__BACK__", _t("cfg.back"))
            .replace("__INTRO__", _t("cfg.intro"))
            .replace("__PREVIEW_TITLE__", _t("cfg.preview_title"))
            .replace("__PREVIEW__", _t("cfg.preview"))
            .replace("__JS__", js))


def main() -> None:
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "configure.html")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(render())


if __name__ == "__main__":
    main()
