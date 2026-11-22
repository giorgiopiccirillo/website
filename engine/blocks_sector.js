/* ==========================================================================
   SECTOR BLOCKS · one hero picture per field, so no two demos share a layout.
   finance: ticker + riskmap + limits · health: bedmap + hours · uni: headline + funnel + leaderboard
   events: lineup + countdown · shop: citymap + shelf. Loaded after engine.js.
   ========================================================================== */
(function () {
  const B = ENGINE.BLOCKS;
  const esc = s => String(s).replace(/[&<>"]/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
  const RM = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  const head = (n, cfg) => `<div class="panel-head"><span class="tab">${String(n).padStart(2, "0")}</span><span class="title">${cfg.title || ""}</span><span class="tag">${cfg.tag || ""}</span></div>`;
  const panel = (n, cfg, inner, cls = "") =>
    `<section class="panel ${cls}${cfg.tone ? " tone-" + cfg.tone : ""}${cfg.span ? " span-" + cfg.span : ""}${cfg.rows ? " rows-" + cfg.rows : ""}">${head(n, cfg)}${inner}${cfg.foot ? `<div class="panel-foot">${cfg.foot}</div>` : ""}</section>`;
  // the 12 named records, joined with their node (label, group, date/fee)
  const named = data => (data.nodes || []).filter(x => (data.records || {})[x.id]).map(x => ({ ...x, ...data.records[x.id] }));

  /* ---------- ticker strip (finance) ---------- */
  B.ticker = (cfg, data) => {
    const items = named(data).map(r => `<span><b>${esc(r.label.toUpperCase())}</b> €${r.balance}M <i class="${r.arrears > 4 ? "dn" : "up"}">${r.arrears > 4 ? "▼" : "▲"} ${r.arrears}%</i></span>`).join("");
    return { html: `<div class="ticker span-4"><div class="ticker-track">${items}${items}</div></div>` };
  };

  /* ---------- risk map: limit use (x) vs arrears (y), bubble = balance ---------- */
  B.riskmap = (cfg, data, ctx, n) => {
    const pts = named(data);
    return {
      html: panel(n, cfg, `<div class="chart riskmap" data-r="c"></div><div class="rm-card" data-r="card"></div>`, "hero"),
      init(el) {
        const W = 720, H = 360, L = 44, R = 16, T = 16, Bt = 32;
        const X = v => L + (v - 60) / 40 * (W - L - R), Y = v => T + (1 - v / 9) * (H - T - Bt);
        const gi = Object.fromEntries((data.groups || []).map((g, i) => [g.id, i + 1]));
        el.querySelector('[data-r="c"]').innerHTML = `<svg viewBox="0 0 ${W} ${H}">
          <rect x="${X(85)}" y="${Y(9)}" width="${X(100) - X(85)}" height="${Y(4) - Y(9)}" fill="var(--bad)" opacity=".08"/>
          <text class="axis" x="${X(99)}" y="${Y(8.5)}" text-anchor="end" style="fill:var(--bad)">DANGER ZONE · full limit + late payers</text>
          ${[0, 2, 4, 6, 8].map(v => `<line class="grid-line" x1="${L}" x2="${W - R}" y1="${Y(v)}" y2="${Y(v)}"/><text class="axis" x="${L - 8}" y="${Y(v) + 3}" text-anchor="end">${v}%</text>`).join("")}
          ${[60, 70, 80, 90, 100].map(v => `<line class="grid-line" y1="${T}" y2="${H - Bt}" x1="${X(v)}" x2="${X(v)}"/><text class="axis" x="${X(v)}" y="${H - 12}" text-anchor="middle">${v}%</text>`).join("")}
          <text class="axis" x="${W - R}" y="${H - 1}" text-anchor="end">LIMIT USED →</text><text class="axis" x="4" y="${T + 4}">ARREARS ↑</text>
          ${pts.map((p, i) => `<g class="rm-pt" data-i="${i}" data-tip="${esc(p.label)} · €${p.balance}M · ${p.use}% used · ${p.arrears}% late" style="--d:${i * 70}ms">
            <circle cx="${X(p.use)}" cy="${Y(p.arrears)}" r="${6 + Math.sqrt(+p.balance) * 4}" fill="var(--c${gi[p.group] || 1})" fill-opacity=".28" stroke="var(--c${gi[p.group] || 1})" stroke-width="1.5"/>
            <text class="axis rm-l" x="${X(p.use)}" y="${Y(p.arrears) - 10 - Math.sqrt(+p.balance) * 4}" text-anchor="middle">${esc(p.label)}</text></g>`).join("")}</svg>
          <div class="legend">${(data.groups || []).map((g, i) => `<span><i style="background:var(--c${i + 1})"></i>${esc(g.id)}</span>`).join("")}</div>`;
        const card = el.querySelector('[data-r="card"]'), gs = el.querySelectorAll(".rm-pt");
        const order = pts.map((p, i) => i).sort((a, b) => pts[b].arrears * pts[b].use - pts[a].arrears * pts[a].use);
        let k = 0;
        const show = () => {
          const i = order[k % order.length], p = pts[i]; k++;
          gs.forEach(g => g.classList.toggle("on", +g.dataset.i === i));
          card.innerHTML = `<div class="k">segment</div><div class="t">${esc(p.label)}</div><div class="k">balance / limit</div><div>€${p.balance}M / €${p.limit}M</div><div class="k">arrears</div><div class="v">${p.arrears}%</div><div class="k">loans</div><div>${p.loans}</div>`;
        };
        show(); if (!RM) setInterval(show, 2600);
      }
    };
  };

  /* ---------- horizontal bars with a target tick (limits / leaderboard) ---------- */
  B.hbars = (cfg, data, ctx, n) => {
    let d = data[cfg.data].slice();
    if (cfg.sort === "gap") d.sort((a, b) => a.value / a.target - b.value / b.target);
    if (cfg.sort === "use") d.sort((a, b) => b.value / b.target - a.value / a.target);
    const mx = Math.max(...d.map(x => Math.max(x.value, x.target)));
    return {
      html: panel(n, cfg, `<div class="hb">${d.map(x => { const p = Math.round(x.value / x.target * 100), c = p >= 100 ? "var(--ok)" : p >= (cfg.warn || 80) ? "var(--c1)" : "var(--bad)";
        return `<div class="hb-row" data-tip="${esc(x.full || x.label)} · ${x.value} of ${x.target}"><span class="hb-l">${esc(x.full || x.label)}</span>
          <span class="hb-t"><span class="hb-f" style="--w:${x.value / mx * 100}%;background:${c}"></span><span class="hb-k" style="left:${x.target / mx * 100}%"></span></span><b class="hb-p">${p}%</b></div>`; }).join("")}</div>`),
      init(el) { HUD.later(() => el.querySelectorAll(".hb-f").forEach(f => f.style.width = f.style.getPropertyValue("--w"))); }
    };
  };

  /* ---------- bed map: one square per bed, per ward (health) ---------- */
  B.bedmap = (cfg, data, ctx, n) => {
    const d = data[cfg.data];
    return {
      html: panel(n, cfg, `<div class="beds">${d.map((w, i) => `<div class="bed-row"><span class="bed-l">${esc(w.full)}</span><span class="bed-g" data-w="${i}">${Array.from({ length: w.target }, (_, j) => `<i class="${j < w.value ? "u" : ""}"></i>`).join("")}</span><b class="bed-n" data-n="${i}">${w.value}/${w.target}</b></div>`).join("")}</div>
        <div class="legend"><span><i class="u-key"></i>bed in use</span><span><i class="f-key"></i>free bed</span><span><i class="w-key"></i>ward over 90%</span></div>`, "hero"),
      init(el) {
        const mark = () => d.forEach((w, i) => el.querySelector(`[data-w="${i}"]`).classList.toggle("hot", w.value / w.target > .9));
        mark();
        if (!RM) setInterval(() => {
          const i = Math.floor(Math.random() * d.length), w = d[i], up = Math.random() < .5;
          w.value = Math.max(0, Math.min(w.target, w.value + (up ? 1 : -1)));
          [...el.querySelector(`[data-w="${i}"]`).children].forEach((b, j) => b.classList.toggle("u", j < w.value));
          el.querySelector(`[data-n="${i}"]`).textContent = `${w.value}/${w.target}`; mark();
        }, 1500);
      }
    };
  };

  /* ---------- 24-hour heat strip (health waits) ---------- */
  B.hours = (cfg, data, ctx, n) => {
    const v = cfg.values, mx = Math.max(...v), now = new Date().getHours();
    return {
      html: panel(n, cfg, `<div class="hours">${v.map((x, h) => `<div class="hr${h === now ? " now" : ""}" data-tip="${String(h).padStart(2, "0")}:00 · ${x} min wait" style="--q:${Math.round(x / mx * 100)}%"><span>${x}</span><small>${String(h).padStart(2, "0")}</small></div>`).join("")}</div>
        <div class="panel-foot">${cfg.note || ""}</div>`)
    };
  };

  /* ---------- editorial headline (uni) ---------- */
  B.headline = cfg => ({
    html: `<header class="headline span-4"><div class="kicker">${esc(cfg.kicker || "")}</div><h1>${esc(cfg.text)}</h1><p>${esc(cfg.standfirst || "")}</p></header>`
  });

  /* ---------- funnel with drop-off between stages (uni) ---------- */
  B.funnel = (cfg, data, ctx, n) => {
    const s = cfg.stages, top = s[0].value;
    return {
      html: panel(n, cfg, `<div class="funnel">${s.map((x, i) => `${i ? `<div class="drop">− ${s[i - 1].value - x.value} lost here · ${Math.round((1 - x.value / s[i - 1].value) * 100)}%</div>` : ""}
        <div class="f-row"><span class="f-bar" style="--w:${x.value / top * 100}%;--fc:var(--c${i + 1})"><b data-v="${x.value}">0</b></span><span class="f-l">${esc(x.label)}<small>${esc(x.note || "")}</small></span></div>`).join("")}</div>`, "hero"),
      init(el) {
        HUD.later(() => el.querySelectorAll(".f-bar").forEach(b => b.style.width = b.style.getPropertyValue("--w")));
        el.querySelectorAll("[data-v]").forEach(b => HUD.countUp(b, +b.dataset.v));
      }
    };
  };

  /* ---------- line-up wall: one poster tile per night (events) ---------- */
  B.lineup = (cfg, data, ctx, n) => {
    const ev = named(data), worst = ev.reduce((a, b) => (b.fill < a.fill ? b : a));
    const gi = Object.fromEntries((data.groups || []).map((g, i) => [g.id, i + 1]));
    const ring = f => { const C = 2 * Math.PI * 22; return `<svg viewBox="0 0 54 54"><circle cx="27" cy="27" r="22" fill="none" stroke="var(--hud-line-soft)" stroke-width="5"/><circle class="ring" cx="27" cy="27" r="22" fill="none" stroke="currentColor" stroke-width="5" stroke-linecap="round" stroke-dasharray="${C}" stroke-dashoffset="${C}" data-o="${C * (1 - f / 100)}" transform="rotate(-90 27 27)"/><text x="27" y="31" text-anchor="middle">${f}%</text></svg>`; };
    return {
      html: panel(n, cfg, `<div class="lineup">${ev.map(e => { const [d, m] = e.school.split(" ");
        return `<div class="night${e === worst ? " push" : ""}${e.fill >= 100 ? " out" : ""}" style="color:var(--c${gi[e.group] || 1})" data-tip="${esc(e.label)} · ${e.sold} of ${e.cap} sold · €${e.revenue}">
          <div class="date"><b>${d}</b><span>${m}</span></div><div class="nm">${esc(e.label)}</div><div class="sr">${esc(e.group)} · €${e.price}</div>${ring(e.fill)}
          <div class="st">${e.fill >= 100 ? "SOLD OUT" : e === worst ? "NEEDS A PUSH" : `${e.cap - e.sold} left`}</div></div>`; }).join("")}</div>`, "hero"),
      init(el) { HUD.later(() => el.querySelectorAll(".ring").forEach(r => r.style.strokeDashoffset = r.dataset.o)); }
    };
  };

  /* ---------- countdown to the next night (events) ---------- */
  B.countdown = (cfg, data, ctx, n) => ({
    html: panel(n, cfg, `<div class="cd-name">${esc(cfg.event)}</div><div class="cd" data-r="cd">00:00:00:00</div><div class="cd-u"><span>days</span><span>hrs</span><span>min</span><span>sec</span></div>
      <div class="cd-left"><b data-r="left">${cfg.left}</b> tickets left · <span data-r="sold">${cfg.sold}</span> sold in the last hour</div>`),
    init(el) {
      const end = Date.now() + cfg.hours * 3600e3, cd = el.querySelector('[data-r="cd"]'), left = el.querySelector('[data-r="left"]'), sold = el.querySelector('[data-r="sold"]');
      let l = cfg.left, s = cfg.sold;
      const tick = () => { let t = Math.max(0, (end - Date.now()) / 1000); const p = [86400, 3600, 60, 1].map(u => { const v = Math.floor(t / u); t -= v * u; return String(v).padStart(2, "0"); }); cd.textContent = p.join(":"); };
      tick(); setInterval(tick, 1000);
      if (!RM) setInterval(() => { if (l > 3 && Math.random() < .5) { l--; s++; left.textContent = l; sold.textContent = s; left.classList.add("flash"); setTimeout(() => left.classList.remove("flash"), 400); } }, 1800);
    }
  });

  /* ---------- city map: orders by market, routes from the roastery (shop) ---------- */
  const CITY = { Vienna: [560, 250], London: [250, 130], Rome: [470, 400], Paris: [300, 220], Madrid: [140, 390], Amsterdam: [360, 120] };
  B.citymap = (cfg, data, ctx, n) => {
    const d = data[cfg.data], mx = Math.max(...d.map(x => x.value)), hub = CITY[cfg.hub || "Vienna"];
    return {
      html: panel(n, cfg, `<div class="chart citymap"><svg viewBox="0 0 700 470">
        <defs><pattern id="dots" width="14" height="14" patternUnits="userSpaceOnUse"><circle cx="2" cy="2" r="1.3" class="dot"/></pattern></defs>
        <rect width="700" height="470" fill="url(#dots)"/>
        ${d.map(x => { const p = CITY[x.group]; return p && p !== hub ? `<path class="route" d="M${hub[0]} ${hub[1]} Q${(hub[0] + p[0]) / 2} ${Math.min(hub[1], p[1]) - 70} ${p[0]} ${p[1]}"/>` : ""; }).join("")}
        ${d.map((x, i) => { const p = CITY[x.group]; if (!p) return ""; const r = 14 + Math.sqrt(x.value / mx) * 46;
          return `<g class="city" data-tip="${esc(x.group)} · ${x.value} orders" style="--d:${i * 120}ms"><circle cx="${p[0]}" cy="${p[1]}" r="${r}" fill="var(--c${i + 1})" class="bub"/><circle cx="${p[0]}" cy="${p[1]}" r="${r}" fill="none" stroke="var(--c${i + 1})" class="pulse"/>
          <text x="${p[0]}" y="${p[1] - 2}" text-anchor="middle" class="cn">${esc(x.group)}</text><text x="${p[0]}" y="${p[1] + 16}" text-anchor="middle" class="cv">${x.value.toLocaleString("en-GB")}</text></g>`; }).join("")}
        </svg></div>`, "hero")
    };
  };

  /* ---------- product shelf: one tile per product, mini funnel inside (shop) ---------- */
  B.shelf = (cfg, data, ctx, n) => {
    const p = named(data), best = p.reduce((a, b) => (b.orders > a.orders ? b : a));
    return {
      html: panel(n, cfg, `<div class="shelf">${p.map((x, i) => `<div class="prod${x === best ? " best" : ""}" style="--pc:var(--c${i + 1})">
        ${x === best ? `<span class="badge">Best seller</span>` : ""}<div class="pic">${esc(x.label.split(" ").map(w => w[0]).join(""))}</div>
        <div class="pn">${esc(x.label)}</div><div class="pm">${esc(x.group)} · ${esc(x.school)}</div><div class="po">${x.orders}<small> orders</small></div>
        <div class="pf"><span style="width:100%"></span><span style="width:${x.carts / x.visits * 100}%"></span><span style="width:${x.orders / x.visits * 100}%"></span></div>
        <div class="pfl">${x.visits} visits → ${x.carts} carts → ${Math.round(x.orders / x.visits * 1000) / 10}% buy</div></div>`).join("")}</div>`)
    };
  };
})();
