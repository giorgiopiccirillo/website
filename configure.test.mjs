// Tests for the configurator's JS core in configure.html.
// Run: node --test configure.test.mjs
import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const conf = readFileSync(join(here, "configure.html"), "utf8");
const demo = readFileSync(join(here, "demo.html"), "utf8");

function between(src, open, close) {
  const a = src.indexOf(open);
  const b = src.indexOf(close);
  assert.ok(a >= 0 && b > a, `markers ${open} ... ${close} not found`);
  return src.slice(a + open.length, b);
}

const buildDemoUrl = new Function(
  between(conf, "/*<buildDemoUrl>*/", "/*</buildDemoUrl>*/") + "\nreturn buildDemoUrl;")();
const parseConfig = new Function("navigator",
  between(demo, "/*<parseConfig>*/", "/*</parseConfig>*/") + "\nreturn parseConfig;")(
  { language: "en-GB" });

const BASE = "https://giorgiopiccirillo.com/demo.html";
const DEFAULT_TABS = ["overview", "weekly", "countries", "programmes", "natint",
  "funnel", "deferrals", "advisors", "fees"];
const STYLES = ["exec-light", "exec-dark", "command", "editorial"];
const NAMES = ["Università di Pavia", "<script>alert(1)</script>", "A&B #1 100%",
  "🎓 Ateneo", "x".repeat(200)];

function shuffled(arr, seed) {
  const a = arr.slice();
  let s = seed;
  for (let i = a.length - 1; i > 0; i--) {
    s = (s * 1103515245 + 12345) % 2147483648;
    const j = s % (i + 1);
    [a[i], a[j]] = [a[j], a[i]];
  }
  return a;
}

const trim80 = (n) => Array.from(String(n).trim()).slice(0, 80).join("").trim();
const SPACE_AT_80 = "a".repeat(79) + " " + "tail";
const ACCENTS = [null, "FFE600", "ffe600"];

const CONFIGS = [];
// Every style x language: 8 configs, accents and names rotating.
STYLES.forEach((style, si) => ["it", "en"].forEach((lang, li) => {
  const k = si * 2 + li;
  CONFIGS.push({ style, lang, tabs: shuffled(DEFAULT_TABS, k + 1).slice(0, 2 + (k % 8)),
    name: NAMES[k % NAMES.length], accent: ACCENTS[k % 3], flags: [] });
}));
CONFIGS.push(
  { style: "exec-light", lang: "en", tabs: DEFAULT_TABS.slice().reverse(),
    name: "", accent: null, flags: [] },
  { style: "command", lang: "it", tabs: DEFAULT_TABS.slice(), name: NAMES[0],
    accent: "ffe600", flags: [] },
  // The flag with its tab missing from the list: the demo appends it last.
  { style: "editorial", lang: "en", tabs: ["fees", "overview"], name: "",
    accent: null, flags: ["beforeafter"] },
  { style: "exec-dark", lang: "it", tabs: ["weekly", "funnel"], name: NAMES[3],
    accent: "FFE600", flags: ["beforeafter"] },
  // The flag with its tab already in the list.
  { style: "exec-light", lang: "en", tabs: ["funnel", "beforeafter", "overview"],
    name: NAMES[1], accent: null, flags: ["beforeafter"] },
  { style: "exec-light", lang: "it", tabs: DEFAULT_TABS.concat(["beforeafter"]),
    name: "", accent: "ffe600", flags: ["beforeafter"] },
  { style: "command", lang: "en", tabs: ["overview"], name: "  Pavia  ",
    accent: null, flags: [] },
  { style: "editorial", lang: "it", tabs: ["natint", "advisors"], name: SPACE_AT_80,
    accent: "FFE600", flags: [] },
  { style: "exec-dark", lang: "en", tabs: ["countries"], name: NAMES[4],
    accent: "ffe600", flags: [] },
  { style: "exec-dark", lang: "it", tabs: DEFAULT_TABS.slice(), name: "",
    accent: null, flags: [] },
  { style: "command", lang: "it", tabs: shuffled(DEFAULT_TABS, 99), name: "A&B #1 100%",
    accent: "FFE600", flags: ["beforeafter"] },
  { style: "editorial", lang: "en", tabs: shuffled(DEFAULT_TABS, 7).slice(0, 5),
    name: "🎓 Ateneo", accent: "ffe600", flags: [] },
  { style: "exec-light", lang: "it", tabs: ["programmes", "deferrals"], name: "   ",
    accent: null, flags: [] },
);

function roundTrip(cfg) {
  const url = buildDemoUrl(cfg, BASE);
  assert.ok(url.startsWith(BASE));
  const got = parseConfig(new URL(url).search);
  const given = got.given;
  delete got.given;
  const want = { ...cfg };
  if (cfg.flags.includes("beforeafter")) {
    want.tabs = cfg.tabs.filter((t) => t !== "beforeafter").concat(["beforeafter"]);
  }
  if (trim80(cfg.name) === "") {
    // Not sent; the demo shows its own default name for the language.
    const dflt = parseConfig("?lang=" + cfg.lang).name;
    assert.equal(given.name, false);
    assert.equal(got.name, dflt);
    assert.equal(new URL(url).searchParams.has("name"), false);
    want.name = dflt;
  } else {
    assert.equal(given.name, true);
    want.name = trim80(cfg.name);
  }
  assert.deepEqual(got, want);
  return url;
}

test(`round trip over ${CONFIGS.length} configurations`, () => {
  assert.ok(CONFIGS.length >= 20);
  CONFIGS.forEach(roundTrip);
});

test("a reversed list of the nine default tabs keeps its order in the link", () => {
  const rev = DEFAULT_TABS.slice().reverse();
  const url = roundTrip({ style: "exec-light", lang: "en", tabs: rev, name: "x",
    accent: null, flags: [] });
  assert.equal(new URL(url).searchParams.get("tabs"), rev.join(","));
  assert.deepEqual(parseConfig(new URL(url).search).tabs, rev);
});

test("a flag appends its tab last when the list omits it", () => {
  const url = roundTrip({ style: "exec-light", lang: "en", tabs: ["fees", "overview"],
    name: "x", accent: null, flags: ["beforeafter"] });
  assert.deepEqual(parseConfig(new URL(url).search).tabs, ["fees", "overview", "beforeafter"]);
});

test("a name is trimmed, then cut at 80 code points, then trimmed again", () => {
  const url = buildDemoUrl({ style: "exec-light", lang: "en", tabs: DEFAULT_TABS.slice(),
    name: SPACE_AT_80, accent: null, flags: [] }, BASE);
  assert.equal(new URL(url).searchParams.get("name"), "a".repeat(79));
});

test("a name over 80 code points is trimmed in the link itself", () => {
  const url = buildDemoUrl({ style: "exec-light", lang: "en", tabs: DEFAULT_TABS.slice(),
    name: "🎓".repeat(100), accent: null, flags: [] }, BASE);
  assert.equal(Array.from(new URL(url).searchParams.get("name")).length, 80);
});

test("default cfg yields only style and lang", () => {
  const url = buildDemoUrl({ style: "exec-light", lang: "it", tabs: DEFAULT_TABS.slice(),
    name: "", accent: null, flags: [] }, BASE);
  assert.equal(url, BASE + "?style=exec-light&lang=it");
});

test("every style is explicit in the link, so a stored demo.style never overrides it", () => {
  const stored = { getItem: (k) => (k === "demo.style" ? "command" : null) };
  for (const style of STYLES) {
    const url = buildDemoUrl({ style, lang: "en", tabs: DEFAULT_TABS.slice(),
      name: "", accent: null, flags: [] }, "demo.html");
    const cfg = parseConfig(url.slice(url.indexOf("?")));
    assert.equal(cfg.given.style, true, style);
    assert.equal(cfg.style, style, style);
    assert.equal(stored.getItem("demo.style"), "command");
  }
});

// ---------------------------------------------------------------- formToCfg
const formToCfg = new Function(
  between(conf, "/*<formToCfg>*/", "/*</formToCfg>*/") + "\nreturn formToCfg;")();

const DEFAULT_STATE = { name: "", tabs: DEFAULT_TABS.slice(), beforeafter: false,
  style: "exec-light", accent: null, lang: "it" };

test("the default form state maps to the default cfg and a style-and-lang link", () => {
  const cfg = formToCfg(DEFAULT_STATE);
  assert.deepEqual(cfg, { style: "exec-light", lang: "it", tabs: DEFAULT_TABS,
    name: "", accent: null, flags: [] });
  assert.equal(buildDemoUrl(cfg, "demo.html"), "demo.html?style=exec-light&lang=it");
});

test("ticked tabs come out in display order, unknown ids dropped", () => {
  const cfg = formToCfg({ ...DEFAULT_STATE, tabs: ["fees", "bogus", "overview", "funnel", "fees"] });
  assert.deepEqual(cfg.tabs, ["overview", "funnel", "fees"]);
});

test("no tab ticked gives the no_tabs error, even with Before and after ticked", () => {
  assert.deepEqual(formToCfg({ ...DEFAULT_STATE, tabs: [] }), { error: "no_tabs" });
  assert.deepEqual(formToCfg({ ...DEFAULT_STATE, tabs: [], beforeafter: true }),
    { error: "no_tabs" });
  assert.deepEqual(formToCfg({ ...DEFAULT_STATE, tabs: ["beforeafter"], beforeafter: true }),
    { error: "no_tabs" });
});

test("the Before and after box maps to the beforeafter flag", () => {
  assert.deepEqual(formToCfg({ ...DEFAULT_STATE, beforeafter: true }).flags, ["beforeafter"]);
  assert.deepEqual(formToCfg(DEFAULT_STATE).flags, []);
});

test("the colour picker value loses its # and invalid colours become null", () => {
  assert.equal(formToCfg({ ...DEFAULT_STATE, accent: "#ffe600" }).accent, "FFE600");
  assert.equal(formToCfg({ ...DEFAULT_STATE, accent: "A0522D" }).accent, "A0522D");
  for (const bad of [null, "", "#fff", "red", "#12345g", undefined]) {
    assert.equal(formToCfg({ ...DEFAULT_STATE, accent: bad }).accent, null, String(bad));
  }
});

test("unknown style and language fall back to the defaults", () => {
  const cfg = formToCfg({ ...DEFAULT_STATE, style: "neon", lang: "fr" });
  assert.equal(cfg.style, "exec-light");
  assert.equal(cfg.lang, "it");
  assert.equal(formToCfg({ ...DEFAULT_STATE, style: "command", lang: "en" }).style, "command");
  assert.equal(formToCfg({ ...DEFAULT_STATE, lang: "en" }).lang, "en");
});

test("formToCfg does not change the state it is given", () => {
  const state = { ...DEFAULT_STATE, tabs: ["fees", "overview"] };
  const copy = JSON.parse(JSON.stringify(state));
  formToCfg(state);
  assert.deepEqual(state, copy);
});

test("form state -> link -> demo parseConfig keeps every choice", () => {
  const state = { name: "  A&B #1 100%  ", tabs: ["weekly", "overview", "fees"],
    beforeafter: true, style: "editorial", accent: "#ffe600", lang: "en" };
  const url = buildDemoUrl(formToCfg(state), BASE);
  const got = parseConfig(new URL(url).search);
  assert.equal(got.style, "editorial");
  assert.equal(got.lang, "en");
  assert.deepEqual(got.tabs, ["overview", "weekly", "fees", "beforeafter"]);
  assert.equal(got.name, "A&B #1 100%");
  assert.equal(got.accent, "FFE600");
  assert.deepEqual(got.flags, ["beforeafter"]);
});

// -------------------------------------------------------------- buildMailto
const mailSrc = between(conf, "/*<buildMailto>*/", "/*</buildMailto>*/");
const buildMailto = new Function("buildDemoUrl", mailSrc + "\nreturn buildMailto;")(buildDemoUrl);
const ADDRESS = "giorgiopiccirillo89" + "@" + "gmail.com";
const LABELS_ENV = JSON.parse(between(conf, "var LABELS = ", ";\n  var STYLE_ACCENTS"));

function parseMail(m) {
  assert.ok(m.startsWith("mailto:"));
  const [to, query] = m.slice("mailto:".length).split("?");
  const q = {};
  query.split("&").forEach((p) => {
    const i = p.indexOf("=");
    q[p.slice(0, i)] = decodeURIComponent(p.slice(i + 1));
  });
  return { to, subject: q.subject, body: q.body };
}

const MAIL_CFG = { style: "editorial", lang: "en", tabs: ["overview", "fees"],
  name: "A&B #1 100%", accent: "FFE600", flags: [] };
const CONTACT = { name: "Ada <Rossi>", role: "Head of Admissions", email: "ada@uni.example" };

test("mailto goes to Giorgio, with subject and body decoding to the expected text", () => {
  const m = buildMailto(MAIL_CFG, CONTACT, LABELS_ENV.en);
  const p = parseMail(m);
  assert.equal(p.to, ADDRESS);
  assert.ok(m.includes("%0D%0A"), "CRLF line breaks");
  assert.equal(p.subject, "Dashboard request — A&B #1 100%");
  const link = buildDemoUrl(MAIL_CFG, "https://giorgiopiccirillo.com/demo.html");
  const lines = p.body.split(/\r?\n/);
  assert.ok(lines.includes("University: A&B #1 100%"), p.body);
  assert.ok(lines.includes("Role: Head of Admissions"));
  assert.ok(lines.includes("Name: Ada <Rossi>"));
  assert.ok(lines.includes("Email: ada@uni.example"));
  assert.ok(lines.includes("Sections: Overview, " + LABELS_ENV.en["tab.fees"]));
  assert.ok(lines.includes("Style: Editorial"));
  assert.ok(lines.includes("Colour: #FFE600"));
  assert.ok(lines.includes("Dashboard language: English"));
  assert.ok(lines.includes("Link: " + link));
});

test("the Italian mailto uses Italian labels; an empty name falls back to the default", () => {
  const cfg = { ...MAIL_CFG, name: "  ", accent: null, lang: "it" };
  const p = parseMail(buildMailto(cfg, {}, LABELS_ENV.it));
  assert.equal(p.subject, "Richiesta dashboard — La tua Università");
  assert.ok(p.body.includes("Sezioni: Panoramica, "));
  assert.ok(p.body.includes("Lingua della dashboard: Italiano"));
  assert.ok(p.body.includes("Colore: " + LABELS_ENV.it["cfg.colour_from_style"]));
});

test("every part is encoded: no raw angle brackets, spaces or newlines", () => {
  const m = buildMailto(MAIL_CFG, CONTACT, LABELS_ENV.en);
  assert.ok(!/[<> \r\n]/.test(m));
  assert.equal(m.split("?").length, 2);
  assert.equal(m.split("&").length, 2);
});

test("a normal case keeps the full link and is under 1800 characters", () => {
  const cfg = { style: "command", lang: "it", tabs: DEFAULT_TABS.slice(),
    name: "x".repeat(80), accent: "FFE600", flags: ["beforeafter"] };
  for (const lang of ["it", "en"]) {
    const m = buildMailto(cfg, { name: "N".repeat(40), role: "R".repeat(40),
      email: "someone@university.example" }, LABELS_ENV[lang]);
    assert.ok(m.length <= 1800, String(m.length));
    assert.ok(parseMail(m).body.includes(buildDemoUrl(cfg, "https://giorgiopiccirillo.com/demo.html")));
  }
});

test("worst cases with &, e-acute and emoji in every field stay within 1800", () => {
  for (const ch of ["&", "\u00e9", "\u{1F393}"]) {
    for (const lang of ["it", "en"]) {
      const cfg = { style: "editorial", lang, tabs: DEFAULT_TABS.slice(),
        name: ch.repeat(80), accent: "FFE600", flags: ["beforeafter"] };
      const m = buildMailto(cfg, { name: ch.repeat(80), role: ch.repeat(80),
        email: ch.repeat(80) }, LABELS_ENV[lang]);
      assert.ok(m.length <= 1800, `${ch} ${lang} ${m.length}`);
      const p = parseMail(m);
      assert.equal(p.to, ADDRESS);
      assert.ok(p.subject.startsWith(LABELS_ENV[lang]["cfg.mail_subject"]));
      const lines = p.body.split(/\r?\n/);
      assert.ok(lines.length >= 9, p.body);
      assert.ok(lines[0].startsWith(LABELS_ENV[lang]["cfg.mail_university"] + ": "));
      assert.ok(lines[4].startsWith(LABELS_ENV[lang]["cfg.mail_sections"] + ": "));
    }
  }
});

test("when the link cannot fit, the body points to the configurator instead", () => {
  const cfg = { style: "editorial", lang: "en", tabs: DEFAULT_TABS.slice(),
    name: "\u{1F393}".repeat(80), accent: "FFE600", flags: [] };
  const p = parseMail(buildMailto(cfg, { name: "\u{1F393}".repeat(80) }, LABELS_ENV.en));
  assert.ok(!p.body.includes("demo.html"));
  assert.ok(p.body.includes("Link too long for email: set it up again at https://giorgiopiccirillo.com/configure.html"));
});

test("a blocked cfg gives an empty string", () => {
  assert.equal(buildMailto({ error: "no_tabs" }, {}, LABELS_ENV.en), "");
});
