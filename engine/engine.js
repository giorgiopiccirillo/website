/* ==========================================================================
   TEMPLATE ENGINE · reads a template (what to show) and data (the numbers),
   draws the page with the blocks below, on top of the HUD helpers.
   A block is: BLOCKS[type] = (cfg, data, ctx) => { html, init(el), start() }.
   Blocks talk to each other only through ctx.bus ("focus" = a record was picked).
   No libraries, no network.
   ========================================================================== */
(function () {
  const esc = s => String(s).replace(/[&<>"]/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
  const BLOCKS = {};
  const OUTSIDE = new Set(["graph", "cmdbar"]); // drawn above the grid, not as a numbered grid panel

  const head = (n, cfg) =>
    `<div class="panel-head"><span class="tab">${String(n).padStart(2, "0")}</span>` +
    `<span class="title">${cfg.title || ""}</span><span class="tag">${cfg.tag || ""}</span></div>`;
  const panel = (n, cfg, inner, extra = "") =>
    `<section class="panel${cfg.tone ? " tone-" + cfg.tone : ""}${cfg.span ? " span-" + cfg.span : ""}${extra}">${head(n, cfg)}${inner}` +
    `${cfg.foot ? `<div class="panel-foot">${cfg.foot}</div>` : ""}</section>`;
  const fill = (tpl, o) => tpl.replace(/\{(\w+)\}/g, (_, k) => (o[k] == null ? "" : o[k]));

  /* ---------- 00 graph (needs groups + nodes in data) ---------- */
  BLOCKS.graph = (cfg, data, ctx, n) => {
    const f = cfg.fields || { group: "group", school: "type" };
    return {
      html: `<section class="panel stage span-4">
        <div class="panel-head"><span class="tab">${String(n).padStart(2, "0")}</span><span class="title">${cfg.title} · <span data-r="count">0</span> ${cfg.unit || ""} · ${cfg.tag || ""}</span><span class="tag" data-r="yaw">yaw 0.0°</span></div>
        <canvas data-r="canvas"></canvas>
        <div class="callout" data-r="callout" style="opacity:0"><b data-r="co">—</b> / <em>MATCHED</em></div>
        <div class="infocard" data-r="info">
          <div class="t" data-r="ic-name">—</div>
          <div class="k">${f.group}</div><div data-r="ic-group">—</div>
          <div class="k">${f.school}</div><div class="v" data-r="ic-school">—</div>
        </div>
        <div class="stage-foot" data-r="foot">match :: —</div></section>`,
      init(el) {
        const r = k => el.querySelector(`[data-r="${k}"]`);
        r("count").textContent = data.nodes.filter(x => x.school !== "—").length;
        const groups = data.groups.map((g, i) => ({ ...g, color: ctx.C(i + 1) }));
        const callout = r("callout"), info = r("info");
        const graph = HUD.graph(r("canvas"), data.nodes, groups, {
          onFrame(api) {
            const p = api.screenPos; if (!p) return;
            const stage = callout.parentElement, SW = stage.clientWidth, SH = stage.clientHeight;
            const clamp = (v, lo, hi) => Math.max(lo, Math.min(hi, v));
            callout.style.left = clamp(p.x + 34, 14, SW - callout.offsetWidth - 14) + "px";
            callout.style.top = clamp(p.y - 46, 34, SH - 60) + "px"; callout.style.opacity = 1;
            const leftSide = p.x > SW / 2;
            info.style.left = clamp(leftSide ? p.x - 330 : p.x + 90, 14, SW - info.offsetWidth - 14) + "px";
            info.style.top = clamp(p.y + 30, 34, SH - info.offsetHeight - 30) + "px";
          }
        });
        setInterval(() => { r("yaw").textContent = "yaw " + ((performance.now() * 0.0016 * 60 / 1000 * 180 / Math.PI) % 360).toFixed(1) + "°"; }, 200);
        ctx.bus.on("focus", ({ id }) => {
          const rec = ctx.record(id); if (!rec) return;
          graph.focusOn(id);
          r("co").textContent = `${rec.label} · ${rec.code}`;
          r("ic-name").textContent = rec.label;
          r("ic-group").textContent = `${rec.group} (${rec.code})`;
          r("ic-school").textContent = rec.school;
          r("foot").textContent = `match :: ${rec.label} · ${rec.group} · ${rec.school}`;
        });
      }
    };
  };

  /* ---------- command bar: types the questions, sends "focus" ---------- */
  BLOCKS.cmdbar = (cfg, data, ctx) => ({
    html: `<div class="cmdbar"><span class="prompt">&gt;</span><span data-r="cmd"></span><span class="caret"></span><span class="who">${cfg.label || ""}</span></div>`,
    start(el) {
      HUD.typer(el.querySelector('[data-r="cmd"]'), data.queries.map(q => q[0]), {
        onLine(i) { ctx.bus.emit("focus", { id: data.queries[i][1], i }); }
      });
    }
  });

  /* ---------- KPI: big number + notes ---------- */
  BLOCKS.kpi = (cfg, data, ctx, n) => {
    const d = data[cfg.data];
    return {
      html: panel(n, cfg, `<div class="kpi-label">${cfg.label || ""}</div><div class="kpi-name">${cfg.name || ""}</div>
        <div class="kpi-value" data-r="v">0</div><div class="kpi-sub">${cfg.sub || ""}</div>
        <div class="kpi-notes">${d.notes.map((x, i) => `${x.label} · <b data-r="n${i}">0${x.suffix || ""}</b>`).join("<br>")}</div>`),
      init(el) {
        HUD.countUp(el.querySelector('[data-r="v"]'), d.value);
        d.notes.forEach((x, i) => HUD.countUp(el.querySelector(`[data-r="n${i}"]`), x.value, x.suffix ? { suffix: x.suffix } : {}));
      }
    };
  };

  /* ---------- live bars, coloured by group ---------- */
  BLOCKS.bars = (cfg, data, ctx, n) => {
    const d = data[cfg.data];
    return {
      html: panel(n, cfg, `<div class="bars" data-r="bars"></div>`),
      init(el) {
        const rows = () => d.map((x, i) => ({ label: x.label, value: vals[i], color: ctx.C(i + 1), hot: i === 0 }));
        let vals = d.map(x => x.value);
        const bars = HUD.bars(el.querySelector('[data-r="bars"]'), rows());
        setInterval(() => { vals = vals.map(v => v + (Math.random() < .35 ? 1 : 0)); bars.update(rows()); }, 2200);
      }
    };
  };

  /* ---------- record card: text template filled from the picked record ---------- */
  BLOCKS.card = (cfg, data, ctx, n) => ({
    html: panel(n, cfg, `<div class="codebox" data-r="card"></div>`),
    init(el) {
      ctx.bus.on("focus", ({ id }) => {
        const rec = ctx.record(id); if (rec) el.querySelector('[data-r="card"]').innerHTML = fill(cfg.body, rec);
      });
    }
  });

  /* ---------- tree: lines with a group code, lit when that group is picked ---------- */
  BLOCKS.tree = (cfg, data, ctx, n) => {
    const d = data[cfg.data];
    return {
      html: panel(n, cfg, `<div class="tree" data-r="tree">${d.map(l => `<span class="node"${l.c ? ` data-c="${l.c}"` : ""}>${esc(l.t)}</span>`).join("")}</div>
        <div class="shellbox"><span style="color:var(--hud-text-2)">${cfg.cmd}</span><span data-r="cmd">${d.find(l => l.c).c}</span><br><span class="ok">✓ <span data-r="n">0</span> ${cfg.loaded}</span></div>`),
      init(el) {
        ctx.bus.on("focus", ({ id }) => {
          const rec = ctx.record(id); if (!rec) return;
          el.querySelectorAll(".node").forEach(x => x.classList.toggle("on", x.dataset.c === rec.code || x.dataset.id === id));
          el.querySelector('[data-r="cmd"]').textContent = rec.code;
          HUD.countUp(el.querySelector('[data-r="n"]'), rec.orders || 0, { ms: 700 });
        });
      }
    };
  };

  /* ---------- donut: follows the picked record's position ---------- */
  BLOCKS.donut = (cfg, data, ctx, n) => {
    const d = data[cfg.data];
    return {
      html: panel(n, cfg, `<div data-r="donut"></div>`),
      init(el) {
        const donut = HUD.donut(el.querySelector('[data-r="donut"]'),
          d.map((x, i) => ({ label: x.label, value: x.value, color: ctx.C(i + 1) })),
          { center: cfg.centre || "", sub: cfg.sub || "" });
        ctx.bus.on("focus", ({ i }) => { if (i != null) donut.focus(i % d.length); });
      }
    };
  };

  /* ---------- tail -f log ---------- */
  BLOCKS.log = (cfg, data, ctx, n) => ({
    html: panel(n, cfg, `<ul class="log" data-r="log"></ul>`),
    init(el) { HUD.log(el.querySelector('[data-r="log"]'), data[cfg.data], { every: 1400, keep: 9 }); }
  });

  /* ---------- scrolling column stream ---------- */
  BLOCKS.stream = (cfg, data, ctx, n) => ({
    html: panel(n, cfg, `<div data-r="s" style="margin-top:auto"></div><div class="big" data-r="big">0<small>${cfg.unit || ""}</small></div>`),
    init(el) {
      const big = el.querySelector('[data-r="big"]'), seed = data[cfg.data];
      big.firstChild.nodeValue = seed[seed.length - 1];
      HUD.stream(el.querySelector('[data-r="s"]'), seed, {
        color: "var(--c1)", every: 1600,
        next: () => { const v = 35 + Math.round(Math.random() * 90); big.firstChild.nodeValue = v; return v; },
        label: (i, v) => `${v} ${cfg.item || ""}`.trim()
      });
    }
  });

  /* ---------- meters (target vs actual) + one square per closed period ---------- */
  BLOCKS.meters = (cfg, data, ctx, n) => {
    const d = data[cfg.data], weeks = data.weeks || 8;
    return {
      html: panel(n, cfg, d.map((m, i) => `<div class="meter-lbl"><span>${m.label}</span><span data-r="t${i}">0%</span></div><div class="meter"><span data-r="m${i}" style="--m:var(--c${m.colour})"></span></div>`).join("") +
        `<div class="squares" data-r="sq">${Array.from({ length: weeks }, (_, i) => `<span data-tip="week ${i + 1}" style="--sq:${ctx.C((i % 3) * 2 + 1)}"></span>`).join("")}</div>`),
      init(el) {
        HUD.later(() => d.forEach((m, i) => {
          el.querySelector(`[data-r="m${i}"]`).style.width = m.value + "%";
          HUD.countUp(el.querySelector(`[data-r="t${i}"]`), m.value, { suffix: "%" });
        }));
        const s = el.querySelector('[data-r="sq"]').children; let w = 0;
        setInterval(() => {
          [...s].forEach((e, i) => e.classList.toggle("on", i < w));
          s[Math.max(0, w - 1)] && (s[Math.max(0, w - 1)].textContent = w ? "✓" : "");
          w = (w + 1) % (weeks + 1); if (w === 0) [...s].forEach(e => e.textContent = "");
        }, 1300);
      }
    };
  };


  /* ---------- KPI cards with a small trend line (one panel, 2-4 cards) ---------- */
  const spark = (vals, colour) => {
    const W = 120, H = 34, mx = Math.max(...vals), mn = Math.min(...vals), r = (mx - mn) || 1;
    const pts = vals.map((v, i) => [i / (vals.length - 1) * W, H - 3 - (v - mn) / r * (H - 8)]);
    const d = pts.map((p, i) => (i ? "L" : "M") + p[0].toFixed(1) + " " + p[1].toFixed(1)).join(" ");
    return `<svg viewBox="0 0 ${W} ${H}" preserveAspectRatio="none"><path d="${d} L${W} ${H} L0 ${H} Z" fill="${colour}" opacity=".12"/><path d="${d}" fill="none" stroke="${colour}" stroke-width="1.6" vector-effect="non-scaling-stroke"/></svg>`;
  };
  BLOCKS.kpis = (cfg, data, ctx, n) => {
    const d = data[cfg.data];
    return {
      html: panel(n, { ...cfg, span: cfg.span || 4 }, `<div class="kpis">${d.map((k, i) => `<div class="k"><div class="l">${k.label}</div>
        <div class="v" data-r="v${i}">0</div><div class="d ${k.trend || ""}">${k.note || ""}</div>${k.series ? spark(k.series, `var(--c${i + 1})`) : ""}</div>`).join("")}</div>`),
      init(el) { d.forEach((k, i) => HUD.countUp(el.querySelector(`[data-r="v${i}"]`), k.value, { suffix: k.suffix || "", dec: Number.isInteger(k.value) ? 0 : 1 })); }
    };
  };

  /* ---------- line chart: 1-3 lines, hover crosshair, optional range toggle ---------- */
  const smooth = pts => pts.map((p, i) => {
    if (!i) return `M${p[0].toFixed(1)} ${p[1].toFixed(1)}`;
    const q = pts[i - 1], mx = (q[0] + p[0]) / 2;
    return `C${mx.toFixed(1)} ${q[1].toFixed(1)} ${mx.toFixed(1)} ${p[1].toFixed(1)} ${p[0].toFixed(1)} ${p[1].toFixed(1)}`;
  }).join(" ");
  BLOCKS.line = (cfg, data, ctx, n) => {
    const d = data[cfg.data], ranges = cfg.ranges || [{ label: "", key: "v" }];
    return {
      html: panel(n, { ...cfg, tag: "" }, `<div class="legend">${d.series.map((s, i) => `<span><i style="background:var(--c${s.colour || i + 1})"></i>${s.label}</span>`).join("")}
        ${ranges.length > 1 ? `<span class="seg" data-r="seg">${ranges.map((r, i) => `<button data-k="${r.key}"${i ? "" : ' class="on"'}>${r.label}</button>`).join("")}</span>` : ""}</div>
        <div class="chart" data-r="chart"></div>`),
      init(el) {
        const host = el.querySelector('[data-r="chart"]'); let key = ranges[0].key;
        const W = 640, H = 220, L = 34, B = 20, T = 8, R = 8;
        const draw = () => {
          const all = d.series.flatMap(s => s[key]), mx = Math.max(...all) * 1.08, X = i => L + i / (d.x.length - 1) * (W - L - R), Y = v => T + (1 - v / mx) * (H - T - B);
          const ticks = [0, .25, .5, .75, 1].map(f => f * mx);
          const lines = d.series.map((s, i) => {
            const pts = s[key].map((v, j) => [X(j), Y(v)]), col = `var(--c${s.colour || i + 1})`;
            return `<path d="${smooth(pts)}" fill="none" stroke="${col}" stroke-width="2" ${s.dashed ? 'stroke-dasharray="4 4"' : ""}/>` +
              (i === 0 ? `<path d="${smooth(pts)} L${X(pts.length - 1)} ${Y(0)} L${X(0)} ${Y(0)} Z" fill="${col}" opacity=".08"/>` : "");
          }).join("");
          const step = Math.ceil(d.x.length / 7);
          host.innerHTML = `<svg viewBox="0 0 ${W} ${H}">${ticks.map(v => `<line class="grid-line" x1="${L}" x2="${W - R}" y1="${Y(v)}" y2="${Y(v)}"/><text class="axis" x="${L - 6}" y="${Y(v) + 3}" text-anchor="end">${Math.round(v)}</text>`).join("")}
            ${d.x.map((x, i) => i % step ? "" : `<text class="axis" x="${X(i)}" y="${H - 5}" text-anchor="middle">${x}</text>`).join("")}${lines}
            <line data-r="cross" class="grid-line" y1="${T}" y2="${H - B}" style="stroke:var(--hud-text-2);opacity:0"/></svg><div class="tt" data-r="tt"></div>`;
          const svg = host.querySelector("svg"), cross = host.querySelector('[data-r="cross"]'), tt = host.querySelector('[data-r="tt"]');
          svg.onmousemove = e => {
            const r = svg.getBoundingClientRect(), f = (e.clientX - r.left) / r.width * W;
            const i = Math.max(0, Math.min(d.x.length - 1, Math.round((f - L) / (W - L - R) * (d.x.length - 1))));
            cross.setAttribute("x1", X(i)); cross.setAttribute("x2", X(i)); cross.style.opacity = 1;
            tt.innerHTML = `<b>${d.x[i]}</b><br>` + d.series.map((s, k) => `<i style="background:var(--c${s.colour || k + 1})"></i>${s.label} ${s[key][i]}`).join("<br>");
            tt.style.opacity = 1; tt.style.left = Math.min(X(i) / W * r.width + 12, r.width - 150) + "px"; tt.style.top = "6px";
          };
          svg.onmouseleave = () => { cross.style.opacity = 0; tt.style.opacity = 0; };
        };
        draw();
        const seg = el.querySelector('[data-r="seg"]');
        if (seg) seg.onclick = e => { const b = e.target.closest("button"); if (!b) return; key = b.dataset.k; seg.querySelectorAll("button").forEach(x => x.classList.toggle("on", x === b)); draw(); };
      }
    };
  };

  /* ---------- columns with a target tick on each ---------- */
  BLOCKS.columns = (cfg, data, ctx, n) => {
    const d = data[cfg.data];
    return {
      html: panel(n, cfg, `<div class="legend"><span><i style="background:var(--c1)"></i>${cfg.actual || "Actual"}</span><span><i style="background:transparent;border:1px dashed var(--hud-text-2)"></i>${cfg.targetLabel || "Target"}</span></div><div class="chart" data-r="chart"></div>`),
      init(el) {
        const W = 640, H = 200, L = 30, B = 22, T = 8, mx = Math.max(...d.map(x => Math.max(x.value, x.target))) * 1.12, bw = (W - L) / d.length;
        const Y = v => T + (1 - v / mx) * (H - T - B);
        el.querySelector('[data-r="chart"]').innerHTML = `<svg viewBox="0 0 ${W} ${H}">${[0, .5, 1].map(f => `<line class="grid-line" x1="${L}" x2="${W}" y1="${Y(f * mx)}" y2="${Y(f * mx)}"/><text class="axis" x="${L - 5}" y="${Y(f * mx) + 3}" text-anchor="end">${Math.round(f * mx)}</text>`).join("")}
          ${d.map((x, i) => { const cx = L + i * bw + bw / 2, w = bw * .5, over = x.value >= x.target;
            return `<g data-tip="${esc(x.full || x.label)} · ${x.value} of ${x.target}"><rect x="${cx - w / 2}" y="${Y(x.value)}" width="${w}" height="${Math.max(1, Y(0) - Y(x.value))}" rx="2" fill="var(--${over ? "c3" : "c1"})" opacity=".85"/>
            <line x1="${cx - w / 2 - 4}" x2="${cx + w / 2 + 4}" y1="${Y(x.target)}" y2="${Y(x.target)}" stroke="var(--hud-text)" stroke-dasharray="3 3"/>
            <text class="axis" x="${cx}" y="${H - 7}" text-anchor="middle">${esc(x.label)}</text></g>`; }).join("")}</svg>`;
      }
    };
  };

  /* ---------- table with status pills ---------- */
  BLOCKS.table = (cfg, data, ctx, n) => {
    const rows = data[cfg.data], tones = cfg.tones || {};
    return {
      html: panel(n, cfg, `<table class="t"><thead><tr>${cfg.cols.map(c => `<th class="${c.num ? "n" : ""}">${c.label}</th>`).join("")}</tr></thead>
        <tbody>${rows.map(r => `<tr>${cfg.cols.map(c => { const v = r[c.key]; return `<td class="${c.num ? "n" : ""}">${c.pill ? `<span class="pill ${tones[v] || ""}">${esc(v)}</span>` : esc(v)}</td>`; }).join("")}</tr>`).join("")}</tbody></table>`)
    };
  };

  /* ---------- "ask the data": suggestion cards, answers typed out ---------- */
  BLOCKS.ask = (cfg, data, ctx, n) => {
    const d = data[cfg.data];
    return {
      html: panel(n, cfg, `<div class="ask"><div class="sugg">${d.map((s, i) => `<button data-i="${i}"><b>${esc(s.title)}</b><small>${esc(s.q)}</small></button>`).join("")}</div>
        <div class="ans idle" data-r="ans">Pick a question. The answer comes from the numbers on this page.</div></div>`),
      init(el) {
        const ans = el.querySelector('[data-r="ans"]'); let timer;
        el.querySelector(".sugg").onclick = e => {
          const b = e.target.closest("button"); if (!b) return;
          el.querySelectorAll(".sugg button").forEach(x => x.classList.toggle("on", x === b));
          const s = d[+b.dataset.i].a; ans.classList.remove("idle"); clearInterval(timer); let k = 0;
          timer = setInterval(() => { ans.textContent = s.slice(0, ++k); if (k >= s.length) clearInterval(timer); }, 14);
        };
      }
    };
  };

  /* ---------- the engine ---------- */
  function run(tpl, data) {
    const bus = (() => { const h = {}; return { on: (e, f) => (h[e] = h[e] || []).push(f), emit: (e, p) => (h[e] || []).forEach(f => f(p)) }; })();
    const ctx = {
      bus,
      C: n => getComputedStyle(document.body).getPropertyValue("--c" + n).trim(),
      record(id) {
        const node = (data.nodes || []).find(x => x.id === id); if (!node) return null;
        const g = data.groups.find(x => x.id === node.group);
        return { ...node, code: g ? g.code : "", ...(data.records || {})[id] };
      }
    };
    const root = document.getElementById("root");
    const made = []; let n = 0;
    tpl.blocks.forEach(cfg => {
      const make = BLOCKS[cfg.type];
      if (!make) { console.warn("unknown block", cfg.type); return; }
      const outside = OUTSIDE.has(cfg.type);
      const b = make(cfg, data, ctx, n);
      if (cfg.type !== "cmdbar") n++;
      made.push({ b, outside });
    });
    const wrap = html => { const t = document.createElement("template"); t.innerHTML = html.trim(); return t.content.firstElementChild; };
    const grid = document.createElement("div"); grid.className = "hud-grid";
    made.forEach(m => { m.el = wrap(m.b.html); (m.outside ? root : grid).appendChild(m.el); });
    // grid goes after the outside blocks, as in the first page
    root.appendChild(grid);
    made.forEach(m => m.b.init && m.b.init(m.el));
    HUD.clock(document.getElementById("clock"));
    made.forEach(m => m.b.start && m.b.start(m.el));
  }

  window.ENGINE = { BLOCKS, run };
})();
