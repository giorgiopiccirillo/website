/* ==========================================================================
   STYLE KIT 1 · TERMINAL — motion + chart helpers (no libraries, no network)
   All functions live on window.HUD. Each one respects prefers-reduced-motion.
   ========================================================================== */
(function () {
  const RM = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  const css = (name, el = document.body) => getComputedStyle(el).getPropertyValue(name).trim();
  const fmt = n => Math.round(n).toLocaleString("en-GB");
  const HUD = {};
  /* run after first paint so CSS transitions play (timer, not rAF: works in background tabs) */
  HUD.later = fn => setTimeout(fn, 60);

  /* ---- tooltip: any element with data-tip="text" ---- */
  const tip = document.createElement("div");
  tip.className = "hud-tip";
  document.addEventListener("DOMContentLoaded", () => document.body.appendChild(tip));
  document.addEventListener("mousemove", e => {
    const t = e.target.closest && e.target.closest("[data-tip]");
    if (!t) { tip.classList.remove("show"); return; }
    tip.textContent = t.getAttribute("data-tip");
    tip.style.left = (e.clientX + 12) + "px";
    tip.style.top = (e.clientY + 12) + "px";
    tip.classList.add("show");
  });
  HUD.tip = tip;

  /* ---- count-up number ---- */
  HUD.countUp = (el, to, { ms = 1400, suffix = "" } = {}) => {
    if (RM) { el.textContent = fmt(to) + suffix; return; }
    const from = parseFloat((el.textContent || "0").replace(/[^\d.]/g, "")) || 0;
    const t0 = performance.now();
    const id = setInterval(() => {
      const p = Math.min(1, (performance.now() - t0) / ms), e = 1 - Math.pow(1 - p, 3);
      el.textContent = fmt(from + (to - from) * e) + suffix;
      if (p >= 1) clearInterval(id);
    }, 16);
  };

  /* ---- bar list: rows = [{label, value, color?, hot?}] ---- */
  HUD.bars = (root, rows, { max } = {}) => {
    const m = max || Math.max(...rows.map(r => r.value));
    root.innerHTML = rows.map(r => `
      <div class="bar-row${r.hot ? " is-hot" : ""}" data-tip="${r.label}: ${fmt(r.value)}">
        <div class="lbl"><span>${r.label}</span><b>${fmt(r.value)}</b></div>
        <div class="bar-track"><div class="bar-fill" style="--bar:${r.color || "var(--tone)"}"></div></div>
      </div>`).join("");
    HUD.later(() => root.querySelectorAll(".bar-fill").forEach((f, i) => f.style.width = (rows[i].value / m * 100) + "%"));
    return {
      update(newRows) {
        const m2 = Math.max(...newRows.map(r => r.value));
        root.querySelectorAll(".bar-row").forEach((row, i) => {
          row.querySelector(".bar-fill").style.width = (newRows[i].value / m2 * 100) + "%";
          row.querySelector("b").textContent = fmt(newRows[i].value);
          row.dataset.tip = `${newRows[i].label}: ${fmt(newRows[i].value)}`;
        });
      }
    };
  };

  /* ---- typewriter that cycles lines ---- */
  HUD.typer = (el, lines, { speed = 45, hold = 2600, onLine } = {}) => {
    let i = 0;
    const run = () => {
      const s = lines[i % lines.length];
      if (onLine) onLine(i % lines.length);
      if (RM) { el.textContent = s; i++; setTimeout(run, hold * 2); return; }
      let k = 0;
      const tick = () => {
        el.textContent = s.slice(0, ++k);
        if (k < s.length) setTimeout(tick, speed); else { i++; setTimeout(run, hold); }
      };
      tick();
    };
    run();
  };

  /* ---- tail -f log: lines = [[verb, msg], ...] ---- */
  HUD.log = (ul, lines, { every = 1500, keep = 9 } = {}) => {
    let i = 0;
    const push = () => {
      const [v, m] = lines[i++ % lines.length];
      const li = document.createElement("li");
      li.innerHTML = `<span class="verb">${v}</span><span class="msg">${m}</span>`;
      ul.appendChild(li);
      while (ul.children.length > keep) ul.removeChild(ul.firstChild);
    };
    for (let k = 0; k < Math.min(keep - 2, lines.length); k++) push();
    if (!RM) setInterval(push, every);
  };

  /* ---- donut: parts = [{label, value, color}] ---- */
  HUD.donut = (root, parts, { center = "", sub = "" } = {}) => {
    const total = parts.reduce((a, p) => a + p.value, 0);
    const R = 70, C = 2 * Math.PI * R, GAP = 3;
    let off = 0;
    const segs = parts.map(p => {
      const len = Math.max(0, p.value / total * C - GAP);
      const s = `<circle r="${R}" cx="90" cy="90" fill="none" stroke="${p.color}" stroke-width="16"
        stroke-dasharray="0 ${C}" data-len="${len}" stroke-dashoffset="${-off}"
        data-tip="${p.label}: ${fmt(p.value)} (${(p.value / total * 100).toFixed(1)}%)"
        style="transition: stroke-dasharray 1.4s cubic-bezier(.2,.7,.2,1); cursor: default"/>`;
      off += p.value / total * C;
      return s;
    }).join("");
    root.innerHTML = `
      <svg viewBox="0 0 180 180" style="width:100%;max-width:190px;display:block;margin:4px auto 0;transform:rotate(-90deg)">${segs}</svg>
      <div style="position:relative;margin-top:-118px;height:118px;text-align:center;pointer-events:none">
        <div class="hud-center-sub" style="color:var(--hud-text-2);font-size:11px">${sub}</div>
        <div class="hud-center" style="font-size:20px;font-weight:700">${center}</div>
      </div>
      <div class="legend">${parts.map(p => `<span><i style="background:${p.color}"></i>${p.label}</span>`).join("")}</div>`;
    HUD.later(() => root.querySelectorAll("circle").forEach(c => c.setAttribute("stroke-dasharray", `${c.dataset.len} ${C}`)));
    const segEls = [...root.querySelectorAll("circle")];
    return {
      focus(i) {
        segEls.forEach((c, k) => c.style.opacity = k === i ? 1 : .35);
        root.querySelector(".hud-center").textContent = (parts[i].value / total * 100).toFixed(0) + "%";
        root.querySelector(".hud-center-sub").textContent = parts[i].label.toLowerCase();
      }
    };
  };

  /* ---- scrolling column stream (SVG) ---- */
  HUD.stream = (root, seed, { color = "var(--tone)", next, every = 1200, n = 36, label } = {}) => {
    const data = seed.slice(-n);
    const W = 300, H = 150, bw = W / n;
    root.innerHTML = `<svg viewBox="0 0 ${W} ${H}" preserveAspectRatio="none" style="width:100%;height:150px;display:block"></svg>`;
    const svg = root.querySelector("svg");
    const draw = () => {
      const m = Math.max(...data) * 1.1;
      svg.innerHTML = data.map((v, i) => {
        const h = Math.max(2, v / m * H);
        const fade = 0.45 + 0.55 * (i / (n - 1));
        return `<rect x="${i * bw + 1}" y="${H - h}" width="${bw - 2}" height="${h}" rx="1"
          fill="${color}" opacity="${fade.toFixed(2)}" data-tip="${label ? label(i, v) : fmt(v)}"/>`;
      }).join("");
    };
    draw();
    if (!RM && next) setInterval(() => { data.push(next()); data.shift(); draw(); }, every);
    return { data };
  };

  /* ---- constellation graph (canvas) ----
     nodes: [{id, label, group}], groups: [{id, color}]
     edges are drawn inside each group and to a few random neighbours. */
  HUD.graph = (canvas, nodes, groups, opts = {}) => {
    const ctx = canvas.getContext("2d");
    const accent = css("--hud-accent");
    let W = 0, H = 0, DPR = Math.min(2, window.devicePixelRatio || 1);
    const resize = () => {
      const r = canvas.getBoundingClientRect();
      W = r.width; H = r.height;
      canvas.width = W * DPR; canvas.height = H * DPR;
      ctx.setTransform(DPR, 0, 0, DPR, 0, 0);
    };
    resize(); window.addEventListener("resize", resize);

    const gIdx = Object.fromEntries(groups.map((g, i) => [g.id, i]));
    // place group centres on an ellipse in 3D-ish space
    const centres = groups.map((g, i) => {
      const a = i / groups.length * Math.PI * 2;
      return { x: Math.cos(a) * 0.55, y: (i % 2 ? 0.18 : -0.18), z: Math.sin(a) * 0.55 };
    });
    const P = nodes.map(n => {
      const c = centres[gIdx[n.group]];
      const rr = () => (Math.random() - .5) * 0.55;
      return { ...n, x: c.x + rr(), y: c.y + rr() * 1.3, z: c.z + rr(), r: n.r != null ? n.r : 1.2 + Math.random() * (n.big ? 4 : 2.2) };
    });
    const edges = [];
    P.forEach((p, i) => {
      for (let k = 0; k < 2; k++) {
        const same = P.filter(q => q.group === p.group && q !== p);
        if (same.length) edges.push([i, P.indexOf(same[Math.floor(Math.random() * same.length)])]);
      }
      if (Math.random() < .12) edges.push([i, Math.floor(Math.random() * P.length)]);
    });
    const stars = Array.from({ length: 140 }, () => ({ x: Math.random(), y: Math.random(), a: Math.random() * .5 }));

    let yaw = 0, focus = -1, focusT = 0, mouse = null;
    const proj = p => {
      const c = Math.cos(yaw), s = Math.sin(yaw);
      const x = p.x * c - p.z * s, z = p.x * s + p.z * c;
      const k = 1 / (1.9 - z * 0.6);
      const scale = Math.min(W, H * 1.9) * 0.62;
      return { sx: W / 2 + x * scale * k, sy: H / 2 + p.y * scale * k, k, z };
    };
    canvas.addEventListener("mousemove", e => { const r = canvas.getBoundingClientRect(); mouse = { x: e.clientX - r.left, y: e.clientY - r.top }; });
    canvas.addEventListener("mouseleave", () => { mouse = null; HUD.tip.classList.remove("show"); });

    const api = { focusOn(id) { focus = P.findIndex(p => p.id === id); focusT = performance.now(); }, nodes: P, screenPos: null };

    const frame = now => {
      if (!RM) yaw += 0.0016;
      ctx.clearRect(0, 0, W, H);
      stars.forEach(s => { ctx.fillStyle = `rgba(236,235,230,${s.a})`; ctx.fillRect(s.x * W, s.y * H, 1, 1); });
      const S = P.map(proj);
      const fp = focus >= 0 ? S[focus] : null;

      // edges
      ctx.lineWidth = 0.6;
      edges.forEach(([a, b]) => {
        const A = S[a], B = S[b], col = groups[gIdx[P[a].group]].color;
        const lit = fp && (a === focus || b === focus || P[a].group === P[focus].group);
        ctx.strokeStyle = col; ctx.globalAlpha = lit ? 0.45 : 0.10 * ((A.k + B.k) / 2);
        ctx.beginPath(); ctx.moveTo(A.sx, A.sy); ctx.lineTo(B.sx, B.sy); ctx.stroke();
      });
      ctx.globalAlpha = 1;

      // nodes, back to front
      let hover = null;
      S.map((s, i) => [s, i]).sort((a, b) => a[0].z - b[0].z).forEach(([s, i]) => {
        const p = P[i], col = groups[gIdx[p.group]].color;
        const dim = fp && P[focus].group !== p.group ? 0.35 : 1;
        ctx.globalAlpha = (0.35 + 0.65 * Math.min(1, s.k)) * dim;
        ctx.fillStyle = col;
        ctx.beginPath(); ctx.arc(s.sx, s.sy, p.r * s.k * 1.4, 0, Math.PI * 2); ctx.fill();
        if (mouse && Math.hypot(mouse.x - s.sx, mouse.y - s.sy) < 8) hover = { p, s };
      });
      ctx.globalAlpha = 1;

      // focus: crosshair + pulsing rings + labels of neighbours
      if (fp) {
        ctx.strokeStyle = accent; ctx.globalAlpha = 0.5; ctx.lineWidth = 0.7;
        ctx.beginPath(); ctx.moveTo(0, fp.sy); ctx.lineTo(W, fp.sy); ctx.moveTo(fp.sx, 0); ctx.lineTo(fp.sx, H); ctx.stroke();
        const t = (now - focusT) / 1000;
        for (let k = 0; k < 3; k++) {
          const rr = 14 + k * 14 + (RM ? 0 : Math.sin(t * 2 + k) * 3);
          ctx.globalAlpha = 0.6 - k * 0.15;
          ctx.beginPath(); ctx.arc(fp.sx, fp.sy, rr, 0, Math.PI * 2); ctx.stroke();
        }
        ctx.globalAlpha = 1; ctx.fillStyle = "#fff";
        ctx.beginPath(); ctx.arc(fp.sx, fp.sy, 4.5, 0, Math.PI * 2); ctx.fill();
        ctx.font = "10px JetBrains Mono, monospace"; ctx.fillStyle = "rgba(236,235,230,.75)";
        P.forEach((p, i) => {
          if (i === focus || p.group !== P[focus].group || !p.big) return;
          ctx.fillText(p.label, S[i].sx + 6, S[i].sy - 4);
        });
        api.screenPos = { x: fp.sx, y: fp.sy };
      }
      if (hover) {
        HUD.tip.textContent = `${hover.p.label} · ${hover.p.group}`;
        const r = canvas.getBoundingClientRect();
        HUD.tip.style.left = (r.left + hover.s.sx + 12) + "px"; HUD.tip.style.top = (r.top + hover.s.sy + 12) + "px";
        HUD.tip.classList.add("show");
      }
      if (opts.onFrame) opts.onFrame(api, now);
      requestAnimationFrame(frame);
    };
    requestAnimationFrame(frame);
    return api;
  };

  /* ---- live clock ---- */
  HUD.clock = el => {
    const t = () => el.textContent = new Date().toLocaleTimeString("en-GB", { timeZone: "Europe/Berlin" }) + " BERLIN";
    t(); setInterval(t, 1000);
  };

  window.HUD = HUD;
})();
