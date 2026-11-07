// Tests for the URL configuration and preference helpers in demo.html.
// Run: node --test demo_config.test.mjs
import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const html = readFileSync(join(here, "demo.html"), "utf8");

function between(open, close) {
  const a = html.indexOf(open);
  const b = html.indexOf(close);
  assert.ok(a >= 0 && b > a, `markers ${open} ... ${close} not found`);
  return html.slice(a + open.length, b);
}

const DEFAULT_TABS = ["overview", "weekly", "countries", "programmes", "natint",
  "funnel", "deferrals", "advisors", "fees"];

function loadParse(language = "en-GB") {
  const code = between("/*<parseConfig>*/", "/*</parseConfig>*/");
  const nav = { language };
  return new Function("navigator", code + "\nreturn parseConfig;")(nav);
}

test("style and lang are read", () => {
  const c = loadParse()("?style=command&lang=en");
  assert.equal(c.style, "command");
  assert.equal(c.lang, "en");
});

test("invalid style, unknown tabs and bad accent are dropped", () => {
  const c = loadParse()("?style=xyz&tabs=nope,overview&accent=zzz");
  assert.equal(c.style, "exec-light");
  assert.deepEqual(c.tabs, ["overview"]);
  assert.equal(c.accent, null);
});

test("accent accepts exactly six hex digits", () => {
  const p = loadParse();
  assert.equal(p("?accent=1a2B3c").accent, "1a2B3c");
  assert.equal(p("?accent=%231a2b3c").accent, null);
  assert.equal(p("?accent=1a2b3").accent, null);
  assert.equal(p("?accent=1a2b3c4").accent, null);
});

test("empty or all-invalid tabs fall back to the nine default tabs", () => {
  const p = loadParse();
  assert.deepEqual(p("?tabs=").tabs, DEFAULT_TABS);
  assert.deepEqual(p("").tabs, DEFAULT_TABS);
  assert.deepEqual(p("?tabs=nope,zzz").tabs, DEFAULT_TABS);
});

test("tabs keep the given order and drop duplicates", () => {
  const c = loadParse()("?tabs=fees,overview,fees");
  assert.deepEqual(c.tabs, ["fees", "overview"]);
});

test("beforeafter tab needs its flag", () => {
  const p = loadParse();
  assert.deepEqual(p("?tabs=overview,beforeafter").tabs, ["overview"]);
  const c = p("?tabs=overview,beforeafter&flag=beforeafter");
  assert.deepEqual(c.tabs, ["overview", "beforeafter"]);
});

test("flag appends the beforeafter tab last when the list omits it", () => {
  const p = loadParse();
  assert.deepEqual(p("?tabs=overview,weekly&flag=beforeafter").tabs, ["overview", "weekly", "beforeafter"]);
  assert.deepEqual(p("?flag=beforeafter").tabs, [...DEFAULT_TABS, "beforeafter"]);
});

test("name is returned as a plain string, never HTML-processed", () => {
  const c = loadParse()("?name=" + encodeURIComponent("<script>alert(1)</script>"));
  assert.equal(c.name, "<script>alert(1)</script>");
});

test("name is trimmed to 80 characters", () => {
  const c = loadParse()("?name=" + "x".repeat(200));
  assert.equal(c.name.length, 80);
});

test("empty name falls back to the default for the language", () => {
  const p = loadParse();
  assert.equal(p("?lang=en&name=").name, "Your University");
  assert.equal(p("?lang=it&name=%20%20").name, "La tua Università");
});

test("flag beforeafter is recognised, unknown flags are dropped", () => {
  const p = loadParse();
  assert.deepEqual(p("?flag=beforeafter").flags, ["beforeafter"]);
  assert.deepEqual(p("?flag=beforeafter,evil").flags, ["beforeafter"]);
  assert.deepEqual(p("").flags, []);
});

test("language defaults from navigator.language", () => {
  assert.equal(loadParse("it-IT")("").lang, "it");
  assert.equal(loadParse("en-US")("").lang, "en");
  assert.equal(loadParse("de-DE")("").lang, "en");
  assert.equal(loadParse("it-IT")("").given.lang, false);
  assert.equal(loadParse("it-IT")("?lang=en").given.lang, true);
});

test("applyConfig writes the name with textContent, never innerHTML", () => {
  assert.ok(!/uni-?[nN]ame[^;\n]*innerHTML/.test(html));
  assert.ok(!/innerHTML/.test(between('<script id="app">', "</script>")));
});

function loadPrefs(storage) {
  const code = between("/*<prefs>*/", "/*</prefs>*/");
  const g = { localStorage: storage };
  return new Function("globalThis", code + "\nreturn {loadPref, savePref};")(g);
}

test("loadPref and savePref work with a normal storage", () => {
  const m = new Map();
  const p = loadPrefs({ getItem: (k) => (m.has(k) ? m.get(k) : null), setItem: (k, v) => m.set(k, v) });
  p.savePref("demo.lang", "en");
  assert.equal(p.loadPref("demo.lang"), "en");
  assert.equal(p.loadPref("missing"), null);
});

test("loadPref and savePref survive a storage that throws", () => {
  const boom = () => { throw new Error("blocked"); };
  const p = loadPrefs({ getItem: boom, setItem: boom });
  assert.equal(p.loadPref("demo.lang"), null);
  assert.doesNotThrow(() => p.savePref("demo.lang", "it"));
});

test("loadPref survives a missing storage object", () => {
  const p = loadPrefs(undefined);
  assert.equal(p.loadPref("k"), null);
  assert.doesNotThrow(() => p.savePref("k", "v"));
});
