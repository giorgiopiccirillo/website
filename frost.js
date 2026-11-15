/*
 * Frost overlay — plain-JavaScript port of the WebGL engine in
 * @canvas-ui/frost-react (createFrost). React wrapper and the experimental
 * HTML-in-canvas capture are left out: this site only uses the overlay mode,
 * where the frost is drawn as a transparent icy layer that melts under the
 * pointer and freezes back over.
 *
 * Usage: window.createFrost(canvasElement, options) -> instance | null
 */
(function () {
  "use strict";

  var DEFAULTS = {
    frost: 0.05, strength: 0.7, contrast: 3, crispness: 1, highlight: 0.3,
    highlightStrength: 0.8, haze: 0.5,
    tintThin: [0.82, 0.86, 1.05], tintThick: [0.92, 0.96, 1.1],
    tintStrength: 0.3, saturation: 1.2, brightness: 0.85, refraction: 1,
    ior: 1.31, detail: 2, textureScale: 2, fresnel: 0.8, meltRadius: 0.25,
    meltNoise: 0.25, meltStrength: 0.75, refreeze: 2, edgeFade: 0.1,
    meltEdges: true, introDuration: 2.5, opacity: 0.6, shimmer: 0,
    quality: 1, fallbackAlpha: 0.85
  };

  var HEIGHT_RES = 512;
  var NOISE_RES = 1024;

  function pixelRatio(el, gl) {
    var scale = (window.visualViewport && window.visualViewport.scale) || 1;
    var requested = Math.min(window.devicePixelRatio || 1, 2) * scale;
    var w = Math.max(el.clientWidth, 1), h = Math.max(el.clientHeight, 1);
    var maxDim = Math.min(8192,
      gl.getParameter(gl.MAX_TEXTURE_SIZE),
      gl.getParameter(gl.MAX_RENDERBUFFER_SIZE));
    return Math.min(requested, maxDim / Math.max(w, h), Math.sqrt(16777216 / (w * h)));
  }

  var VERT = "#version 300 es\nprecision highp float;\nlayout(location = 0) in vec2 aPos;\nout vec2 vUv;\nvoid main () {\n  vUv = aPos * 0.5 + 0.5;\n  gl_Position = vec4(aPos, 0.0, 1.0);\n}";

  var NOISE_LIB = [
    "float prnd (vec2 n, float period) {",
    "  n = mod(n, period);",
    "  float dt = dot(n, vec2(0.129898, 0.78233));",
    "  return fract(sin(mod(dt, 3.14159265)) * 437.585453);",
    "}",
    "float pnoise (vec2 p, float period) {",
    "  vec2 i = floor(p);",
    "  vec2 f = fract(p);",
    "  vec2 u = f * f * (3.0 - 2.0 * f);",
    "  float a = prnd(i, period);",
    "  float b = prnd(i + vec2(1.0, 0.0), period);",
    "  float c = prnd(i + vec2(0.0, 1.0), period);",
    "  float d = prnd(i + vec2(1.0, 1.0), period);",
    "  return mix(mix(a, b, u.x), mix(c, d, u.x), u.y);",
    "}"
  ].join("\n");

  var FRAG_NOISE = [
    "#version 300 es", "precision highp float;", "in vec2 vUv;", "out vec4 outColor;",
    NOISE_LIB,
    "float pfbm (vec2 p, float period, int octaves) {",
    "  float v = 0.0; float a = 0.5;",
    "  for (int i = 0; i < 4; i++) {",
    "    if (i >= octaves) break;",
    "    v += a * pnoise(p, period);",
    "    p = p * 2.0 + vec2(17.0, 31.0);",
    "    period *= 2.0; a *= 0.5;",
    "  }",
    "  return v;",
    "}",
    "float pwarp (vec2 p, float period, float g) {",
    "  float val = 0.0;",
    "  for (int i = 0; i < 2; i++) {",
    "    val = pfbm(p + g * vec2(cos(6.28318 * val), sin(6.28318 * val)), period, 4);",
    "  }",
    "  return val;",
    "}",
    "void main () {",
    "  float pattern = pwarp(vUv * 20.0, 20.0, 4.0);",
    "  float mottle = pfbm(vUv * 26.0, 26.0, 3);",
    "  float sparkle = smoothstep(0.8, 0.95, pnoise(vUv * 200.0, 200.0)) * (0.35 + 0.65 * pnoise(vUv * 50.0, 50.0));",
    "  float meltEdge = pfbm(vUv * 9.0, 9.0, 3);",
    "  outColor = vec4(pattern, mottle, sparkle, meltEdge);",
    "}"
  ].join("\n");

  var FRAG_HEIGHT = [
    "#version 300 es", "precision highp float;", "in vec2 vUv;", "out vec4 outColor;",
    NOISE_LIB,
    "float pfbm (vec2 p, float period, int octaves) {",
    "  float v = 0.0; float a = 0.5;",
    "  for (int i = 0; i < 5; i++) {",
    "    if (i >= octaves) break;",
    "    v += a * pnoise(p, period);",
    "    p *= 2.0; period *= 2.0; a *= 0.5;",
    "  }",
    "  return v;",
    "}",
    "void main () {",
    "  float broad = pfbm(vUv * 6.0, 6.0, 4);",
    "  broad = broad * broad * 1.4;",
    "  float fine = pfbm(vUv * 28.0, 28.0, 3);",
    "  outColor = vec4(broad, fine, 0.0, 1.0);",
    "}"
  ].join("\n");

  var FRAG_POINTER = [
    "#version 300 es", "precision highp float;", "in vec2 vUv;", "out vec4 outColor;",
    "uniform sampler2D uBack;", "uniform sampler2D uNoise;",
    "uniform vec2 uPoint;", "uniform vec2 uPrevPoint;",
    "uniform float uAspect;", "uniform float uTextureScale;", "uniform float uDecay;",
    "uniform float uMeltNoise;", "uniform float uMeltStrength;", "uniform float uRadius;",
    "uniform float uEdgeFade;", "uniform float uTouching;",
    "float sdSegment (vec2 p, vec2 a, vec2 b) {",
    "  vec2 pa = p - a; vec2 ba = b - a;",
    "  float h = clamp(dot(pa, ba) / max(dot(ba, ba), 1e-6), 0.0, 1.0);",
    "  return length(pa - ba * h);",
    "}",
    "void main () {",
    "  float melt = clamp(texture(uBack, vUv).r - uDecay, 0.0, 1.0);",
    "  vec2 nUv = vUv * vec2(uAspect, 1.0) / max(uTextureScale, 0.05);",
    "  float n = texture(uNoise, nUv).a - 0.5;",
    "  vec2 p = vUv * vec2(uAspect, 1.0);",
    "  vec2 a = uPrevPoint * vec2(uAspect, 1.0);",
    "  vec2 b = uPoint * vec2(uAspect, 1.0);",
    "  float d = sdSegment(p, a, b) + n * uMeltNoise;",
    "  float m = (1.0 - smoothstep(uRadius * 0.35, uRadius, d)) * uMeltStrength;",
    "  vec2 dSide = min(vUv, 1.0 - vUv);",
    "  float side = smoothstep(0.0, max(uEdgeFade, 1e-4), min(dSide.x, dSide.y));",
    "  m *= mix(1.0, side, step(1e-3, uEdgeFade));",
    "  m *= uTouching;",
    "  melt = clamp(melt + m, 0.0, 1.0);",
    "  outColor = vec4(vec3(melt), 1.0);",
    "}"
  ].join("\n");

  // Overlay-mode frost: the content branch of the original shader is removed.
  var FRAG_FROST = [
    "#version 300 es", "precision highp float;", "in vec2 vUv;", "out vec4 outColor;",
    "uniform sampler2D uNoise;", "uniform sampler2D uPointer;",
    "uniform float uAspect;", "uniform float uTextureScale;", "uniform float uMeltEdges;",
    "uniform float uIntro;", "uniform float uHighlight;", "uniform float uStrength;",
    "uniform float uFrost;", "uniform float uContrast;", "uniform float uCrispness;",
    "uniform vec3 uTintThin;", "uniform vec3 uTintThick;", "uniform float uTintStrength;",
    "uniform float uHighlightStrength;", "uniform float uShimmer;", "uniform float uTime;",
    "uniform float uOpacity;",
    "float contrastFn (float x, float s) { return clamp((x - 0.5) * s + 0.5, 0.0, 1.0); }",
    "float rand2 (vec2 uv) {",
    "  uv = floor(uv * 5000.0) / 5000.0;",
    "  float a = dot(uv, vec2(92.0, 80.0));",
    "  float b = dot(uv, vec2(41.0, 62.0));",
    "  return fract(sin(a) + cos(b) * 51.0);",
    "}",
    "void main () {",
    "  vec2 nUv = vUv * vec2(uAspect, 1.0) / max(uTextureScale, 0.05);",
    "  vec4 noise = texture(uNoise, nUv);",
    "  float warpN = noise.r;",
    "  float meltRaw = texture(uPointer, vUv).r;",
    "  vec2 edgeDist = min(vUv, 1.0 - vUv);",
    "  float edgeBoost = (1.0 - smoothstep(0.0, 0.4, min(edgeDist.x, edgeDist.y))) * (1.0 - uMeltEdges * smoothstep(0.0, 0.5, meltRaw));",
    "  float strength = uStrength * (0.62 + 0.65 * edgeBoost);",
    "  float ed = min(edgeDist.x, edgeDist.y) + (0.5 - warpN) * 0.34 + (0.5 - noise.g) * 0.16;",
    "  float local = clamp((uIntro * 3.0 - ed * 2.0 - 0.3) / 1.1, 0.0, 1.0);",
    "  strength *= local;",
    "  float body = contrastFn(warpN * strength + uFrost * local, uContrast);",
    "  float h = rand2(vUv + warpN * 0.05);",
    "  float grain = h * warpN;",
    "  float glint = smoothstep(0.85, 1.0, h);",
    "  glint *= mix(1.0, 0.5 + 0.5 * sin(uTime * 2.4 + h * 6.28), clamp(uShimmer, 0.0, 1.0));",
    "  float micro = mix(grain, glint, uHighlight);",
    "  float m = clamp(meltRaw * (1.1 + (noise.a - 0.5) * 0.9), 0.0, 1.0);",
    "  float d = body - m * (0.9 + 0.35 * body);",
    "  float frozen = smoothstep(0.0, 0.22, d);",
    "  float cover = smoothstep(0.03, 0.35, body);",
    "  float ice = clamp(contrastFn(micro * cover * frozen + body, uCrispness), 0.0, 1.0);",
    "  float frostMask = ice * frozen;",
    "  vec3 icy = mix(uTintThin, uTintThick, body);",
    "  vec3 frostColor = mix(icy, vec3(1.0), glint * uHighlightStrength * step(0.001, uHighlight));",
    "  float op = clamp(uOpacity, 0.0, 1.0);",
    "  outColor = vec4(clamp(frostColor, 0.0, 1.0), frostMask * op);",
    "}"
  ].join("\n");

  var FRAG_OUTPUT = [
    "#version 300 es", "precision highp float;", "in vec2 vUv;", "out vec4 outColor;",
    "uniform sampler2D uFrost;", "uniform sampler2D uHeights;",
    "uniform float uIor;", "uniform float uRefraction;", "uniform float uDetail;",
    "uniform float uTextureScale;", "uniform float uFresnel;", "uniform float uFallbackAlpha;",
    "const float TEXEL = 1.0 / " + HEIGHT_RES + ".0;",
    "vec3 heightNormal (float channel, vec2 mapUv, float bump) {",
    "  vec2 hx = vec2(TEXEL, 0.0); vec2 hy = vec2(0.0, TEXEL);",
    "  vec2 c = texture(uHeights, mapUv).rg;",
    "  vec2 x = texture(uHeights, mapUv + hx).rg;",
    "  vec2 y = texture(uHeights, mapUv + hy).rg;",
    "  float dx = channel < 0.5 ? x.r - c.r : x.g - c.g;",
    "  float dy = channel < 0.5 ? y.r - c.r : y.g - c.g;",
    "  return normalize(vec3(-dx * bump, -dy * bump, 1.0));",
    "}",
    "void main () {",
    "  float frostMask = texture(uFrost, vUv).a;",
    "  vec3 V = vec3(0.0, 0.0, 1.0);",
    "  float mainScale = max(uTextureScale, 0.05) * 900.0;",
    "  float subScale = max(uTextureScale, 0.05) * 260.0;",
    "  vec2 mainUv = gl_FragCoord.xy / mainScale;",
    "  vec2 subUv = gl_FragCoord.xy / subScale;",
    "  vec3 nMain = heightNormal(0.0, mainUv, 14.0);",
    "  vec3 nSub = heightNormal(1.0, subUv, 8.0);",
    "  float heightW = smoothstep(0.1, 0.95, texture(uHeights, mainUv).r);",
    "  vec3 R1 = refract(-V, nMain, 1.0 / uIor);",
    "  vec3 R2 = refract(-V, nSub, 1.0 / uIor);",
    "  vec2 offset = (R1.xy * 0.3 + R2.xy * uDetail * heightW * 0.5) * uRefraction * 0.2;",
    "  vec2 refractedUv = clamp(vUv + offset, 0.0, 1.0);",
    "  vec4 baseColor = texture(uFrost, vUv);",
    "  vec4 refractedColor = texture(uFrost, refractedUv);",
    "  float cosTheta = clamp(dot(-V, nMain), 0.0, 1.0);",
    "  float F0 = pow((uIor - 1.0) / (uIor + 1.0), 2.0);",
    "  float fresnel = F0 + (1.0 - F0) * pow(1.0 - cosTheta, 5.0);",
    "  float refractionMix = clamp(frostMask * (1.0 + fresnel * uFresnel), 0.0, 1.0);",
    "  vec4 mixed = mix(baseColor, refractedColor, refractionMix);",
    "  float alpha = clamp(mixed.a * uFallbackAlpha, 0.0, 1.0);",
    "  outColor = vec4(mixed.rgb * alpha, alpha);",
    "}"
  ].join("\n");

  function createFrost(output, options) {
    var config = {};
    var k;
    for (k in DEFAULTS) config[k] = DEFAULTS[k];
    for (k in (options || {})) config[k] = options[k];

    var gl = output.getContext("webgl2", {
      alpha: true, depth: false, stencil: false, antialias: false, premultipliedAlpha: true
    });
    if (!gl || gl.isContextLost()) return null;

    var halfFloat = Boolean(gl.getExtension("EXT_color_buffer_float"));
    var shaders = [], programs = [];

    function compile(type, text) {
      var s = gl.createShader(type);
      gl.shaderSource(s, text);
      gl.compileShader(s);
      if (!gl.getShaderParameter(s, gl.COMPILE_STATUS)) {
        console.error("Frost shader error:", gl.getShaderInfoLog(s));
      }
      shaders.push(s);
      return s;
    }
    var vertexShader = compile(gl.VERTEX_SHADER, VERT);

    function createProgram(frag) {
      var program = gl.createProgram();
      gl.attachShader(program, vertexShader);
      gl.attachShader(program, compile(gl.FRAGMENT_SHADER, frag));
      gl.linkProgram(program);
      programs.push(program);
      var uniforms = {};
      var count = gl.getProgramParameter(program, gl.ACTIVE_UNIFORMS);
      for (var i = 0; i < count; i++) {
        var info = gl.getActiveUniform(program, i);
        uniforms[info.name] = gl.getUniformLocation(program, info.name);
      }
      return { program: program, uniforms: uniforms };
    }

    var noiseProgram = createProgram(FRAG_NOISE);
    var heightProgram = createProgram(FRAG_HEIGHT);
    var pointerProgram = createProgram(FRAG_POINTER);
    var frostProgram = createProgram(FRAG_FROST);
    var outputProgram = createProgram(FRAG_OUTPUT);

    var quad = gl.createBuffer();
    gl.bindBuffer(gl.ARRAY_BUFFER, quad);
    gl.bufferData(gl.ARRAY_BUFFER, new Float32Array([-1, -1, 1, -1, -1, 1, 1, 1]), gl.STATIC_DRAW);
    gl.enableVertexAttribArray(0);
    gl.vertexAttribPointer(0, 2, gl.FLOAT, false, 0, 0);

    function createTarget(width, height, useHalf, wrap) {
      var texture = gl.createTexture();
      gl.bindTexture(gl.TEXTURE_2D, texture);
      gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.LINEAR);
      gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, gl.LINEAR);
      gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, wrap);
      gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, wrap);
      gl.texImage2D(gl.TEXTURE_2D, 0, useHalf ? gl.RGBA16F : gl.RGBA8, width, height, 0,
        gl.RGBA, useHalf ? gl.HALF_FLOAT : gl.UNSIGNED_BYTE, null);
      var fbo = gl.createFramebuffer();
      gl.bindFramebuffer(gl.FRAMEBUFFER, fbo);
      gl.framebufferTexture2D(gl.FRAMEBUFFER, gl.COLOR_ATTACHMENT0, gl.TEXTURE_2D, texture, 0);
      gl.viewport(0, 0, width, height);
      gl.clearColor(0, 0, 0, 0);
      gl.clear(gl.COLOR_BUFFER_BIT);
      return { fbo: fbo, texture: texture, width: width, height: height };
    }
    function releaseTarget(t) {
      if (!t) return;
      gl.deleteFramebuffer(t.fbo);
      gl.deleteTexture(t.texture);
    }
    function createDoubleTarget(w, h, useHalf) {
      var read = createTarget(w, h, useHalf, gl.CLAMP_TO_EDGE);
      var write = createTarget(w, h, useHalf, gl.CLAMP_TO_EDGE);
      return {
        get read() { return read; },
        get write() { return write; },
        swap: function () { var t = read; read = write; write = t; }
      };
    }

    var frostTarget = null, pointer = null, targetsReady = false;
    var heightTarget = createTarget(HEIGHT_RES, HEIGHT_RES, false, gl.REPEAT);
    var noiseTarget = createTarget(NOISE_RES, NOISE_RES, false, gl.REPEAT);

    function blit(target) {
      if (target) {
        gl.bindFramebuffer(gl.FRAMEBUFFER, target.fbo);
        gl.viewport(0, 0, target.width, target.height);
      } else {
        gl.bindFramebuffer(gl.FRAMEBUFFER, null);
        gl.viewport(0, 0, output.width, output.height);
      }
      gl.drawArrays(gl.TRIANGLE_STRIP, 0, 4);
    }
    function bindTexture(texture, unit) {
      gl.activeTexture(gl.TEXTURE0 + unit);
      gl.bindTexture(gl.TEXTURE_2D, texture);
      return unit;
    }

    gl.useProgram(heightProgram.program); blit(heightTarget);
    gl.useProgram(noiseProgram.program); blit(noiseTarget);

    function rebuildTargets() {
      var w = Math.max(output.width, 1), h = Math.max(output.height, 1);
      releaseTarget(frostTarget);
      if (pointer) { releaseTarget(pointer.read); releaseTarget(pointer.write); }
      frostTarget = createTarget(w, h, false, gl.CLAMP_TO_EDGE);
      pointer = createDoubleTarget(Math.max(1, Math.round(w * 0.5)), Math.max(1, Math.round(h * 0.5)), halfFloat);
      targetsReady = true;
    }
    function syncCanvasSize() {
      var dpr = pixelRatio(output, gl);
      var w = Math.max(1, Math.round(output.clientWidth * dpr));
      var h = Math.max(1, Math.round(output.clientHeight * dpr));
      if (output.width !== w || output.height !== h) {
        output.width = w; output.height = h; rebuildTargets();
      } else if (!targetsReady) {
        rebuildTargets();
      }
    }
    syncCanvasSize();

    var pointerOn = false, pointerX = 0.5, pointerY = 0.5, prevX = 0.5, prevY = 0.5;

    function renderPointer() {
      if (!pointer) return;
      var u = pointerProgram.uniforms;
      gl.useProgram(pointerProgram.program);
      gl.uniform1i(u.uBack, bindTexture(pointer.read.texture, 0));
      gl.uniform1i(u.uNoise, bindTexture(noiseTarget.texture, 1));
      gl.uniform1f(u.uAspect, output.width / Math.max(output.height, 1));
      gl.uniform1f(u.uTextureScale, config.textureScale);
      gl.uniform1f(u.uDecay, config.refreeze * 0.001);
      gl.uniform1f(u.uMeltNoise, config.meltNoise);
      gl.uniform1f(u.uMeltStrength, config.meltStrength * 0.2);
      gl.uniform1f(u.uRadius, config.meltRadius);
      gl.uniform1f(u.uEdgeFade, config.meltEdges ? 0 : config.edgeFade);
      gl.uniform2f(u.uPoint, pointerX, 1 - pointerY);
      gl.uniform2f(u.uPrevPoint, prevX, 1 - prevY);
      gl.uniform1f(u.uTouching, pointerOn ? 1 : 0);
      blit(pointer.write);
      pointer.swap();
      prevX = pointerX; prevY = pointerY;
    }

    function renderFrost(now) {
      if (!frostTarget || !pointer) return;
      var u = frostProgram.uniforms;
      gl.useProgram(frostProgram.program);
      gl.uniform1i(u.uNoise, bindTexture(noiseTarget.texture, 2));
      gl.uniform1i(u.uPointer, bindTexture(pointer.read.texture, 3));
      gl.uniform1f(u.uAspect, output.width / Math.max(output.height, 1));
      gl.uniform1f(u.uTextureScale, config.textureScale);
      gl.uniform1f(u.uMeltEdges, config.meltEdges ? 1 : 0);
      gl.uniform1f(u.uIntro, introProgress(now));
      gl.uniform1f(u.uHighlight, config.highlight);
      gl.uniform1f(u.uStrength, config.strength);
      gl.uniform1f(u.uFrost, config.frost);
      gl.uniform1f(u.uContrast, config.contrast);
      gl.uniform1f(u.uCrispness, config.crispness);
      gl.uniform3f(u.uTintThin, config.tintThin[0], config.tintThin[1], config.tintThin[2]);
      gl.uniform3f(u.uTintThick, config.tintThick[0], config.tintThick[1], config.tintThick[2]);
      gl.uniform1f(u.uTintStrength, config.tintStrength);
      gl.uniform1f(u.uHighlightStrength, config.highlightStrength);
      gl.uniform1f(u.uShimmer, config.shimmer);
      gl.uniform1f(u.uTime, now / 1000);
      gl.uniform1f(u.uOpacity, Math.min(Math.max(config.opacity, 0), 1));
      blit(frostTarget);
    }

    function renderOutput() {
      if (!frostTarget) return;
      var u = outputProgram.uniforms;
      gl.useProgram(outputProgram.program);
      gl.uniform1i(u.uFrost, bindTexture(frostTarget.texture, 0));
      gl.uniform1i(u.uHeights, bindTexture(heightTarget.texture, 2));
      gl.uniform1f(u.uIor, Math.max(config.ior, 1.01));
      gl.uniform1f(u.uRefraction, config.refraction);
      gl.uniform1f(u.uDetail, config.detail);
      gl.uniform1f(u.uTextureScale, config.textureScale);
      gl.uniform1f(u.uFresnel, config.fresnel);
      gl.uniform1f(u.uFallbackAlpha, config.fallbackAlpha);
      blit(null);
    }

    var raf = 0, destroyed = false, running = false, visible = true, activeUntil = 0;
    var introStart = performance.now();
    var motionQuery = window.matchMedia("(prefers-reduced-motion: reduce)");
    var reducedMotion = motionQuery.matches;

    function introProgress(now) {
      var ms = Math.max(config.introDuration, 0) * 1000;
      if (ms <= 0 || reducedMotion) return 1;
      var t = Math.min(Math.max((now - introStart) / ms, 0), 1);
      return t * t * (3 - 2 * t);
    }
    function refreezeDelayMs() {
      var decay = Math.max(config.refreeze * 0.001, 1e-5);
      return (1 / decay / 60) * 1000 + 500;
    }
    function frame(now) {
      if (destroyed) return;
      if (!visible || document.hidden) { running = false; return; }
      gl.disable(gl.BLEND);
      renderPointer();
      renderFrost(now);
      renderOutput();
      var animating = pointerOn || now < activeUntil ||
        now < introStart + Math.max(config.introDuration, 0) * 1000 + 120 ||
        config.shimmer > 0.001;
      if (!animating) { running = false; return; }
      raf = requestAnimationFrame(frame);
    }
    function start() {
      if (destroyed || running || !visible || document.hidden) return;
      running = true;
      raf = requestAnimationFrame(frame);
    }
    function suspend() {
      cancelAnimationFrame(raf);
      running = false;
      pointerOn = false;
      prevX = pointerX; prevY = pointerY;
    }
    start();

    function onMotionChange() { reducedMotion = motionQuery.matches; if (!reducedMotion) start(); }
    motionQuery.addEventListener("change", onMotionChange);
    function onVisibility() { if (document.hidden) suspend(); else start(); }
    document.addEventListener("visibilitychange", onVisibility);

    // The canvas sits behind the page content, so listen on the whole window.
    function onPointerMove(e) {
      if (destroyed || reducedMotion || !visible || document.hidden) return;
      var r = output.getBoundingClientRect();
      pointerX = (e.clientX - r.left) / Math.max(r.width, 1);
      pointerY = (e.clientY - r.top) / Math.max(r.height, 1);
      pointerOn = true;
      activeUntil = performance.now() + refreezeDelayMs();
      start();
    }
    function onPointerLeave() {
      pointerOn = false;
      activeUntil = performance.now() + refreezeDelayMs();
      start();
    }
    window.addEventListener("pointermove", onPointerMove, { passive: true });
    window.addEventListener("pointerdown", onPointerMove, { passive: true });
    document.documentElement.addEventListener("pointerleave", onPointerLeave);
    window.addEventListener("pointercancel", onPointerLeave);

    var resizeFrame = 0;
    var ro = new ResizeObserver(function () {
      if (resizeFrame) return;
      resizeFrame = requestAnimationFrame(function () {
        resizeFrame = 0;
        if (destroyed) return;
        syncCanvasSize();
        activeUntil = Math.max(activeUntil, performance.now() + 100);
        start();
      });
    });
    ro.observe(output);

    var io = new IntersectionObserver(function (entries) {
      var last = entries[entries.length - 1];
      visible = last ? last.isIntersecting : true;
      if (destroyed) return;
      if (visible) start(); else suspend();
    });
    io.observe(output);

    return {
      setOptions: function (next) {
        for (var key in next) config[key] = next[key];
        activeUntil = Math.max(activeUntil, performance.now() + 100);
        start();
      },
      destroy: function () {
        if (destroyed) return;
        destroyed = true;
        suspend();
        ro.disconnect(); io.disconnect();
        motionQuery.removeEventListener("change", onMotionChange);
        document.removeEventListener("visibilitychange", onVisibility);
        window.removeEventListener("pointermove", onPointerMove);
        window.removeEventListener("pointerdown", onPointerMove);
        document.documentElement.removeEventListener("pointerleave", onPointerLeave);
        window.removeEventListener("pointercancel", onPointerLeave);
        releaseTarget(noiseTarget); releaseTarget(heightTarget); releaseTarget(frostTarget);
        if (pointer) { releaseTarget(pointer.read); releaseTarget(pointer.write); }
        programs.forEach(function (p) { gl.deleteProgram(p); });
        shaders.forEach(function (s) { gl.deleteShader(s); });
        gl.deleteBuffer(quad);
      }
    };
  }

  window.createFrost = createFrost;
})();
