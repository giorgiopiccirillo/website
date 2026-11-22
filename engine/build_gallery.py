"""Build gallery.html: one card per template folder in templates/ (live preview, field, question, links),
plus the message: different fields, same engine; data first, then the picture.
Run after adding a template:  python3 engine/build_gallery.py"""
import json
from html import escape
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ORDER = ["finance", "health", "uni", "events", "shop"]  # sector priority: finance and health first, then universities

cards, fields = [], []
names = sorted((p.name for p in (ROOT / "templates").iterdir() if (p / "template.json").exists()),
               key=lambda n: (ORDER.index(n) if n in ORDER else 99, n))
for nm in names:
    t = json.loads((ROOT / "templates" / nm / "template.json").read_text(encoding="utf-8"))
    href = f"dash-{nm}.html"
    fields.append(t["field"])
    note = f'<p class="note">{escape(t["note"])}</p>' if t.get("note") else ""
    cards.append(f"""<article class="card">
  <a class="thumb" href="{href}" aria-label="Open the {escape(t['field'])} demo"><iframe src="{href}?embed=1" loading="lazy" tabindex="-1" title=""></iframe></a>
  <div class="body">
    <span class="field">{escape(t['field'])}</span>
    <h2>{escape(t['question'])}</h2>
    <p class="meta">Live demo · {escape(t.get('look', ''))} look · invented data</p>{note}
    <p class="links"><a class="go" href="{href}">Open the live demo →</a></p>
  </div></article>""")

chips = "".join(f'<span class="chip on">{escape(f)}</span>' for f in fields) + \
    '<span class="chip">Logistics</span><span class="chip">Insurance</span><span class="chip">Real estate</span><span class="chip">Non-profit</span><a class="chip ask" href="index.html#contact">Your field? Tell me →</a>'

PAGE = """<!doctype html>
<html lang="en-GB"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Dashboard gallery · Giorgio Piccirillo</title>
<meta name="description" content="Live dashboard demos for finance, health, education, events and retail. Built on your data. Every demo uses invented data.">
<style>
:root{--bg:#0b0d14;--panel:#12151f;--line:#232838;--text:#ecebe6;--mute:#8b90a0;--acc:#6f8cff}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--text);font:15px/1.5 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif}
header,main,.steps,.foot{max-width:1100px;margin:0 auto;padding:0 16px}header{padding-top:40px}
h1{font-size:clamp(26px,4vw,40px);margin:0 0 8px;line-height:1.15}header p{color:var(--mute);max-width:62ch;margin:0 0 20px}
.back{color:var(--mute);text-decoration:none;font-size:13px}
.chips{display:flex;flex-wrap:wrap;gap:8px;margin:0 0 28px}.chip{font-size:12px;color:var(--mute);border:1px dashed var(--line);padding:3px 11px;border-radius:99px;text-decoration:none}
.chip.on{color:var(--text);border:1px solid var(--acc);background:color-mix(in srgb,var(--acc) 12%,transparent)}.chip.ask{color:var(--text);border-style:solid}
.grid{display:grid;gap:20px;grid-template-columns:repeat(auto-fill,minmax(min(100%,320px),1fr));padding-bottom:40px}
.card{background:var(--panel);border:1px solid var(--line);border-radius:12px;overflow:hidden;display:flex;flex-direction:column}
.thumb{display:block;position:relative;aspect-ratio:16/10;overflow:hidden;background:#000}
.thumb iframe{position:absolute;left:0;top:0;width:1400px;height:875px;border:0;transform-origin:0 0;transform:scale(var(--s,.25));pointer-events:none}
.body{padding:14px 16px 16px}.field{font-size:11px;letter-spacing:.12em;text-transform:uppercase;color:var(--acc)}
h2{font-size:18px;margin:4px 0 6px;line-height:1.3}.meta{color:var(--mute);font-size:13px;margin:0 0 10px}.note{color:var(--mute);font-size:12px;margin:-4px 0 10px}
.links{display:flex;flex-wrap:wrap;gap:8px;margin:0}.links a{color:var(--mute);font-size:12px;text-decoration:none;border:1px solid var(--line);padding:2px 9px;border-radius:99px}
.links a.go{color:var(--text);border-color:var(--acc);font-size:13px}.links a:hover{color:var(--text)}
.steps{padding-bottom:60px}.steps h2{font-size:clamp(20px,3vw,28px);margin:0 0 6px}.steps>p{color:var(--mute);max-width:62ch;margin:0 0 18px}
.row{display:grid;gap:16px;grid-template-columns:repeat(auto-fit,minmax(min(100%,250px),1fr))}
.step{background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:16px}.step b{display:block;font-size:11px;letter-spacing:.12em;color:var(--acc);margin-bottom:4px}
.step h3{margin:0 0 6px;font-size:17px}.step p{margin:0;color:var(--mute);font-size:14px}
.foot{padding-bottom:50px;color:var(--mute);font-size:13px}.foot a{color:var(--text)}
@media (prefers-reduced-motion:reduce){.thumb iframe{display:none}}
</style></head><body>
<header><a class="back" href="projects.html">← Projects</a><h1>One engine. Your field.</h1>
<p>Every sector gets its own layout, its own main picture and its own look, built around the question that sector asks. Open a demo and try it. All numbers are invented.</p>
<div class="chips">{chips}</div></header>
<main><div class="grid">
{cards}
</div></main>
<section class="steps"><h2>The picture is the last step</h2>
<p>A dashboard is only as good as the data behind it. So the work starts one layer down.</p>
<div class="row">
<div class="step"><b>01 · ORGANISE</b><h3>Get your data in order</h3><p>Pull it out of your systems, remove duplicates, give every number one name and one source. The same clean layer can feed a company brain that answers questions in plain words.</p></div>
<div class="step"><b>02 · SHOW</b><h3>Make it easy to read</h3><p>A live screen for the team and a report for leadership, in the look you choose. Problems first, targets next to the numbers.</p></div>
<div class="step"><b>03 · ASK</b><h3>Ask it anything</h3><p>The question bar answers in plain words, from the same numbers as the charts.</p></div>
</div>
<p class="foot" style="padding:18px 0 0">Your data is messy, or you only want it to look better? Both are fine. <a href="index.html#contact">Tell me what you have →</a> · <a href="index.html#services">What else I build</a></p>
</section>
<script>
  // scale each live preview to the width of its card
  const fit = () => document.querySelectorAll(".thumb").forEach(t => t.style.setProperty("--s", t.clientWidth / 1400));
  fit(); addEventListener("resize", fit);
</script></body></html>
"""
(ROOT / "gallery.html").write_text(PAGE.replace("{chips}", chips).replace("{cards}", "\n".join(cards)), encoding="utf-8")
print("wrote gallery.html with", len(cards), "cards")
