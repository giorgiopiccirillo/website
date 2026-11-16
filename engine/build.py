"""Build one page from a template folder:  python3 engine/build.py shop

Reads templates/<name>/template.json and data.json, writes dash-<name>.html in the
project root. The page inlines both files, so it also opens from a plain file.
Kits (looks) are chosen in the browser: ?kit=1 terminal, 2 aurora, 3 noir.
"""
import json
import sys
from html import escape
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def js_json(obj) -> str:
    return json.dumps(obj, ensure_ascii=False).replace("</", "<\\/")


PAGE = """<!doctype html>
<html lang="en-GB">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<meta name="description" content="{description}">
<link rel="stylesheet" href="kits/stylekit1_terminal.css">
<script>
  // ?kit=1 terminal (default) · ?kit=2 aurora glass · ?kit=3 noir gold · &embed=1 hides the switch
  const KITS = {{ 2: ["stylekit2_aurora.css", "kit-aurora"], 3: ["stylekit3_noir.css", "kit-noir"] }};
  const Q = new URLSearchParams(location.search);
  const KIT = Q.get("kit") || "1";
  const EMBED = Q.get("embed") === "1";
  if (KITS[KIT]) document.write(`<link rel="stylesheet" href="kits/${{KITS[KIT][0]}}">`);
</script>
<style>
  .kit-switch {{ display: flex; gap: 6px; }}
  .kit-switch a {{ color: var(--hud-muted); text-decoration: none; border: 1px solid var(--hud-line); padding: 2px 8px; border-radius: var(--hud-r); }}
  .kit-switch a.on {{ color: var(--hud-text); border-color: var(--hud-accent); }}
  .back {{ color: var(--hud-muted); text-decoration: none; border: 1px solid var(--hud-line); padding: 2px 8px; border-radius: var(--hud-r); }}
  body.embed .kit-switch, body.embed .back {{ display: none; }}
  body.embed {{ overflow: hidden; }}
</style>
</head>
<body class="hud">
<script>
  if (KITS[KIT]) document.body.classList.add(KITS[KIT][1]);
  if (EMBED) document.body.classList.add("embed");
</script>
<div class="hud-wrap" id="root">
  <div class="hud-top">
    <span class="brand">{brand}</span>
    <span class="sample-flag">{flag}</span>
    <span class="right">
      {back}
      <span class="kit-switch"><a href="?kit=1" data-k="1">Terminal</a><a href="?kit=2" data-k="2">Aurora</a><a href="?kit=3" data-k="3">Noir</a></span>
      <span><span class="live-dot"></span>LIVE</span><span id="clock"></span>
    </span>
  </div>
</div>
<script id="tpl" type="application/json">{tpl}</script>
<script id="data" type="application/json">{data}</script>
<script src="kits/stylekit1_terminal.js"></script>
<script src="engine/engine.js"></script>
<script>
  document.querySelectorAll(".kit-switch a").forEach(a => a.classList.toggle("on", a.dataset.k === KIT));
  ENGINE.run(JSON.parse(document.getElementById("tpl").textContent), JSON.parse(document.getElementById("data").textContent));
</script>
</body>
</html>
"""


def build(name: str) -> Path:
    folder = ROOT / "templates" / name
    tpl = json.loads((folder / "template.json").read_text(encoding="utf-8"))
    data = json.loads((folder / "data.json").read_text(encoding="utf-8"))
    back = tpl.get("back")
    page = PAGE.format(
        title=escape(tpl["title"]), description=escape(tpl.get("description", "")),
        brand=escape(tpl["brand"]), flag=escape(tpl.get("flag", "")),
        back=f'<a class="back" href="{escape(back["href"])}">{escape(back["label"])}</a>' if back else "",
        tpl=js_json(tpl), data=js_json(data))
    out = ROOT / f"dash-{name}.html"
    out.write_text(page, encoding="utf-8")
    return out


if __name__ == "__main__":
    for nm in sys.argv[1:] or ["shop"]:
        print("wrote", build(nm))
