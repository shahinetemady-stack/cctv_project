/* Atmosphere — the layer that makes a dashboard feel like an instrument you are
 * standing in front of, rather than a spreadsheet with rounded corners.
 *
 * Every effect here obeys the same three rules:
 *
 *   1. Colour comes from CSS tokens, read live. Nothing has a baked hex, so an
 *      effect follows the theme toggle instead of surviving it as a dark smear
 *      on a white page.
 *   2. Ink is spent below the content. These paint the ground; contrast for text
 *      is still the panel's job, so every effect keeps its alpha low and never
 *      competes with a number.
 *   3. They stop when nobody is looking — off-screen (IntersectionObserver),
 *      backgrounded (visibilitychange), or when the user asked for less motion.
 *      A dashboard is left open on a wall for hours; a background that burns a
 *      core forever is a bug, not a flourish.
 *
 * Each factory returns a handle: {stop(), start(), destroy(), el}. Kit.onTheme
 * wiring is automatic — the effects re-read tokens every frame, which is cheap
 * because getComputedStyle on :root is cached by the browser between reflows.
 */

const RM = matchMedia('(prefers-reduced-motion: reduce)');

export const tok = (() => {
  // getComputedStyle is only actually expensive when it forces layout; reading
  // custom properties off :root does not. Still, sixty reads a frame across six
  // effects adds up, so the values are cached and invalidated on theme change.
  let cache = {}, gen = 0;
  const bump = () => { cache = {}; gen++ };
  addEventListener('kit:theme', bump);
  new MutationObserver(bump).observe(document.documentElement, {attributes: true, attributeFilter: ['data-theme']});
  return name => cache[name] ?? (cache[name] = getComputedStyle(document.documentElement).getPropertyValue(name).trim());
})();

/** '#0af' | 'rgb(0,170,255)' | 'oklch(...)' → [r,g,b] 0-255. */
export function rgb(v) {
  if (!v) return [128, 128, 128];
  v = v.trim();
  if (v[0] === '#') {
    const h = v.length === 4 ? v.slice(1).split('').map(c => c + c).join('') : v.slice(1);
    return [0, 2, 4].map(i => parseInt(h.slice(i, i + 2), 16));
  }
  const n = (v.match(/[\d.]+/g) || []).map(Number);
  if (/^color\(|^oklch|^lab/.test(v)) {
    // Modern colour syntaxes need a round-trip through the engine to reach sRGB.
    const c = document.createElement('canvas').getContext('2d');
    c.fillStyle = v; return rgb(c.fillStyle);
  }
  return n.length >= 3 ? n.slice(0, 3) : [128, 128, 128];
}
export const rgba = (c, a) => `rgba(${c[0] | 0},${c[1] | 0},${c[2] | 0},${a})`;

/* A canvas sized to its parent in device pixels, with the run-loop plumbing that
   every effect below would otherwise repeat.
   `scale` shrinks the backing store below device resolution — worth it for soft,
   low-frequency grounds, where nobody can see the difference but the fragment
   count falls with the square. `fps` caps the redraw rate for effects whose
   motion is slow enough that 60 Hz buys nothing. */
function stage(host, draw, {alpha = true, gl = false, scale = 1, fps = 0} = {}) {
  const cv = document.createElement('canvas');
  cv.style.cssText = 'position:absolute;inset:0;width:100%;height:100%;display:block;pointer-events:none';
  host.appendChild(cv);
  if (getComputedStyle(host).position === 'static') host.style.position = 'relative';

  const ctx = gl ? (cv.getContext('webgl2', {alpha, antialias: false}) || cv.getContext('webgl', {alpha}))
                 : cv.getContext('2d', {alpha});
  if (!ctx) { cv.remove(); return null }

  let w = 0, h = 0, dpr = 1, raf = 0, t0 = performance.now(), live = false, seen = true, shown = true, lastT = 0, drawn = false;
  const size = () => {
    const r = host.getBoundingClientRect();
    const nw = Math.max(1, r.width), nh = Math.max(1, r.height);
    // ریسایز صرفاً‌ارتفاعی (مخفی/آشکار شدن نوار آدرس iOS هنگام اسکرول) نادیده
    // گرفته می‌شود — بازنویسی cv.width/height بکینگ‌استور را خالی می‌کند و تا
    // فریم بعدی (با سقف fps تا ~۶۶ms) فلیکر خاموش/روشن دیده می‌شود. کش‌آمدن
    // موقت بیت‌مپ در این زمینه‌های نرم محسوس نیست (همان راه‌حل BoardCanvas).
    if (drawn && Math.round(nw) === Math.round(w) && Math.round(nh) !== Math.round(h)) return;
    dpr = Math.min(devicePixelRatio || 1, 2) * scale;
    w = nw; h = nh;
    cv.width = w * dpr | 0; cv.height = h * dpr | 0;
    if (!gl) ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    else ctx.viewport(0, 0, cv.width, cv.height);
    api.w = w; api.h = h; api.dpr = dpr;
    if (api.onsize) api.onsize(w, h);
    // بازرسی فوری بعد از ریسایز واقعی — بکینگ‌استور خالی شده و نباید حتی یک
    // فریم خالی دیده شود
    if (drawn) draw(api, lastT);
  };
  const step = fps ? 1000 / fps - 1 : 0;   // -1ms so a 30fps cap doesn't alias to 20
  let last = -1e9;
  const frame = now => {
    raf = requestAnimationFrame(frame);
    if (now - last < step) return;
    last = now;
    lastT = (now - t0) / 1000;
    drawn = true;
    draw(api, lastT);
  };
  const api = {cv, ctx, w, h, dpr, host, tok, rgb, rgba,
    start() { if (!live && seen && shown) { live = true; t0 = performance.now() - api.t * 1000 || performance.now(); raf = requestAnimationFrame(frame) } },
    stop() { live = false; cancelAnimationFrame(raf) },
    t: 0,
    destroy() { api.stop(); ro.disconnect(); io.disconnect(); removeEventListener('visibilitychange', vis); cv.remove() },
    el: cv};

  const ro = new ResizeObserver(size); ro.observe(host);
  const io = new IntersectionObserver(e => { seen = e[0].isIntersecting; seen && shown ? api.start() : api.stop() }, {threshold: 0});
  io.observe(host);
  const vis = () => { shown = !document.hidden; shown && seen ? api.start() : api.stop() };
  addEventListener('visibilitychange', vis);

  size();
  if (RM.matches) { draw(api, 0); drawn = true }   // one static frame is still a background
  else api.start();
  return api;
}

/* ── aurora ────────────────────────────────────────────────────────────────
 * The shader ground. Three domain-warped fbm lobes in the page's own accent
 * and support colours, at very low amplitude, so it reads as light in a room
 * rather than as a graphic. This is the single highest-leverage effect here: it
 * costs one <canvas> and turns a flat page into a lit one.
 */
const AURORA_FS = `precision highp float;
uniform vec2 u_res; uniform float u_t, u_amp, u_scale;
uniform vec3 u_bg, u_a, u_b, u_c;
float hash(vec2 p){ return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453); }
float noise(vec2 p){
  vec2 i = floor(p), f = fract(p);
  vec2 u = f * f * (3.0 - 2.0 * f);
  return mix(mix(hash(i), hash(i + vec2(1,0)), u.x),
             mix(hash(i + vec2(0,1)), hash(i + vec2(1,1)), u.x), u.y);
}
float fbm(vec2 p){
  float v = 0.0, a = 0.5;
  for (int i = 0; i < 3; i++){ v += a * noise(p); p *= 2.02; a *= 0.5; }
  return v;
}
void main(){
  vec2 uv = gl_FragCoord.xy / u_res;
  vec2 p = (gl_FragCoord.xy - 0.5 * u_res) / min(u_res.x, u_res.y) * u_scale;
  // Domain warp: fbm of an fbm. One extra octave of cost, an order of magnitude
  // more organic than a plain gradient.
  vec2 q = vec2(fbm(p + vec2(0.0, u_t * 0.06)), fbm(p + vec2(3.4, -u_t * 0.05)));
  vec2 r = vec2(fbm(p + 2.0 * q + vec2(1.7, 9.2) + u_t * 0.04),
                fbm(p + 2.0 * q + vec2(8.3, 2.8) - u_t * 0.03));
  float f = fbm(p + 1.8 * r);
  vec3 col = u_bg;
  col = mix(col, u_a, clamp(f * f * 1.9, 0.0, 1.0) * u_amp);
  col = mix(col, u_b, clamp(length(q) * 0.85, 0.0, 1.0) * u_amp * 0.8);
  col = mix(col, u_c, clamp(r.x * r.x * 1.4, 0.0, 1.0) * u_amp * 0.6);
  // A held vignette keeps the eye in the middle of the screen where the data is.
  col *= 1.0 - 0.28 * length(uv - 0.5);
  // Ordered dither at 1/255 kills the banding that always shows up on a large
  // near-flat gradient in 8-bit.
  col += (hash(gl_FragCoord.xy) - 0.5) / 255.0;
  gl_FragColor = vec4(col, 1.0);
}`;

/* ── gas ───────────────────────────────────────────────────────────────────
 * A billowing gas / nebula ground. Where aurora is light in a room, this is
 * matter: five-octave fbm, double domain warp, and a slow upward drift, so the
 * clouds rise and fold over themselves like smoke that never quite leaves.
 * Density is shaped (f² for body, smoothstep for hot pockets, |q|·|r| for
 * filaments) so the colour comes from the gas itself, not from a gradient.
 */
const GAS_FS = `precision highp float;
uniform vec2 u_res; uniform float u_t, u_amp, u_scale;
uniform vec3 u_bg, u_a, u_b, u_c;
float hash(vec2 p){ return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453); }
float noise(vec2 p){
  vec2 i = floor(p), f = fract(p);
  vec2 u = f * f * (3.0 - 2.0 * f);
  return mix(mix(hash(i), hash(i + vec2(1,0)), u.x),
             mix(hash(i + vec2(0,1)), hash(i + vec2(1,1)), u.x), u.y);
}
float fbm(vec2 p){
  float v = 0.0, a = 0.5;
  for (int i = 0; i < 5; i++){ v += a * noise(p); p = p * 2.03 + vec2(11.3, 7.9); a *= 0.52; }
  return v;
}
void main(){
  vec2 uv = gl_FragCoord.xy / u_res;
  vec2 p = (gl_FragCoord.xy - 0.5 * u_res) / min(u_res.x, u_res.y) * u_scale;
  float t = u_t * 0.05;
  // Gas rises: the whole field drifts up and slightly sideways, very slowly.
  vec2 drift = vec2(t * 0.18, -t * 0.55);
  vec2 q = vec2(fbm(p + drift + vec2(0.0, t * 0.8)),
                fbm(p + drift + vec2(5.2, 1.3) - t * 0.6));
  vec2 r = vec2(fbm(p + 2.2 * q + vec2(1.7, 9.2) + t * 0.35),
                fbm(p + 2.2 * q + vec2(8.3, 2.8) - t * 0.28));
  float f = fbm(p + drift + 2.4 * r);
  // Body, hot pockets, filaments — three ways the same field spends colour.
  float body = f * f;
  float core = smoothstep(0.42, 0.95, f);
  float fila = clamp(length(q) * length(r), 0.0, 1.0);
  vec3 col = u_bg;
  col = mix(col, u_b, clamp(body * 1.7, 0.0, 1.0) * u_amp);
  col = mix(col, u_a, clamp(core * 1.15, 0.0, 1.0) * u_amp);
  col = mix(col, u_c, clamp(fila * fila * 1.3, 0.0, 1.0) * u_amp * 0.65);
  col *= 1.0 - 0.26 * length(uv - 0.5);
  col += (hash(gl_FragCoord.xy) - 0.5) / 255.0;
  gl_FragColor = vec4(col, 1.0);
}`;

function shader(host, fs, uniforms, opts = {}) {
  const s = stage(host, (a, t) => paint(a, t), {alpha: false, gl: true, ...opts});
  if (!s) return null;
  const gl = s.ctx;
  const sh = (type, src) => { const o = gl.createShader(type); gl.shaderSource(o, src); gl.compileShader(o);
    if (!gl.getShaderParameter(o, gl.COMPILE_STATUS)) { console.warn(gl.getShaderInfoLog(o)); } return o };
  const prog = gl.createProgram();
  gl.attachShader(prog, sh(gl.VERTEX_SHADER, 'attribute vec2 p;void main(){gl_Position=vec4(p,0.,1.);}'));
  gl.attachShader(prog, sh(gl.FRAGMENT_SHADER, fs));
  gl.linkProgram(prog); gl.useProgram(prog);
  const buf = gl.createBuffer();
  gl.bindBuffer(gl.ARRAY_BUFFER, buf);
  gl.bufferData(gl.ARRAY_BUFFER, new Float32Array([-1, -1, 3, -1, -1, 3]), gl.STATIC_DRAW);
  const loc = gl.getAttribLocation(prog, 'p');
  gl.enableVertexAttribArray(loc); gl.vertexAttribPointer(loc, 2, gl.FLOAT, false, 0, 0);
  const U = {}; const u = n => U[n] ?? (U[n] = gl.getUniformLocation(prog, n));

  function paint(a, t) {
    a.t = t;
    gl.uniform2f(u('u_res'), a.cv.width, a.cv.height);
    gl.uniform1f(u('u_t'), t);
    const vals = uniforms(a, t);
    for (const k in vals) {
      const v = vals[k];
      Array.isArray(v) ? gl['uniform' + v.length + 'fv'](u(k), v) : gl.uniform1f(u(k), v);
    }
    gl.drawArrays(gl.TRIANGLES, 0, 3);
  }
  return s;
}

/* The ground is a slow, soft gradient, so it is rendered at 40% of device
   resolution and at 30 Hz. Full-res 60 Hz cost ~4x the fragments for a
   difference nobody can see — and it was dropping the whole page to 30 fps,
   because a fullscreen fbm competes with everything else for the GPU. */
export function aurora(host, {amp = .5, scale = 2.2, res = .4, fps = 30,
                              keys = ['--fx-1', '--fx-2', '--fx-3']} = {}) {
  const n = c => rgb(c).map(v => v / 255);
  return shader(host, AURORA_FS, () => ({
    u_amp: amp, u_scale: scale,
    u_bg: n(tok('--fx-bg') || tok('--bg')),
    u_a: n(tok(keys[0]) || tok('--accent')),
    u_b: n(tok(keys[1]) || tok('--accent')),
    u_c: n(tok(keys[2]) || tok('--accent')),
  }), {scale: res, fps});
}

/* Gas runs heavier than aurora (five octaves, two warps), so it keeps the same
   40% / 30 Hz budget — the softness hides the resolution, the slowness hides
   the frame rate. Colours come from --gas-* tokens so the nebula follows the
   theme toggle instead of fighting it. */
export function gas(host, {amp = .6, scale = 2.4, res = .4, fps = 30,
                           keys = ['--gas-1', '--gas-2', '--gas-3']} = {}) {
  const n = c => rgb(c).map(v => v / 255);
  return shader(host, GAS_FS, () => ({
    u_amp: amp, u_scale: scale,
    u_bg: n(tok('--fx-bg') || tok('--bg')),
    u_a: n(tok(keys[0]) || tok('--fx-1') || tok('--accent')),
    u_b: n(tok(keys[1]) || tok('--fx-2') || tok('--accent')),
    u_c: n(tok(keys[2]) || tok('--fx-3') || tok('--accent')),
  }), {scale: res, fps});
}

/* ── constellation ─────────────────────────────────────────────────────────
 * Points drift, and any two closer than a threshold
 * are joined by a line whose alpha falls off with distance — so the structure
 * appears and dissolves on its own rather than being drawn.
 */
export function constellation(host, {count = 64, link = 132, speed = .24, alpha = .5, fps = 30} = {}) {
  let pts = [];
  const s = stage(host, (a, t) => {
    const {ctx: c, w, h} = a;
    if (!pts.length || pts.w !== w) {
      const n = Math.min(count, Math.round(w * h / 14000));
      pts = Array.from({length: n}, (_, i) => ({
        x: (Math.sin(i * 12.9898) * 43758.5453 % 1 + 1) % 1 * w,
        y: (Math.sin(i * 78.233) * 43758.5453 % 1 + 1) % 1 * h,
        a: (Math.sin(i * 3.1) * 0.5 + 0.5) * Math.PI * 2,
      }));
      pts.w = w;
    }
    c.clearRect(0, 0, w, h);
    const ink = rgb(tok('--ink')), acc = rgb(tok('--accent'));
    for (const p of pts) {
      p.x += Math.cos(p.a) * speed; p.y += Math.sin(p.a) * speed;
      p.a += Math.sin(t * .2 + p.x * .002) * .004;
      if (p.x < -20) p.x = w + 20; if (p.x > w + 20) p.x = -20;
      if (p.y < -20) p.y = h + 20; if (p.y > h + 20) p.y = -20;
    }
    c.lineWidth = 1;
    for (let i = 0; i < pts.length; i++) for (let j = i + 1; j < pts.length; j++) {
      const dx = pts[i].x - pts[j].x, dy = pts[i].y - pts[j].y, d = Math.hypot(dx, dy);
      if (d > link) continue;
      c.strokeStyle = rgba(ink, (1 - d / link) * .16 * alpha);
      c.beginPath(); c.moveTo(pts[i].x, pts[i].y); c.lineTo(pts[j].x, pts[j].y); c.stroke();
    }
    pts.forEach((p, i) => {
      const hot = i % 9 === 0;
      c.fillStyle = rgba(hot ? acc : ink, (hot ? .55 : .3) * alpha);
      c.beginPath(); c.arc(p.x, p.y, hot ? 1.9 : 1.2, 0, 7); c.fill();
    });
  }, {fps});
  return s;
}

/* ── radar ─────────────────────────────────────────────────────────────────
 * The sweep is a gradient wedge, and each blip is drawn with
 * alpha proportional to how long ago the beam passed it — the decay is the whole
 * effect, and it is what makes it read as live rather than as a spinning graphic.
 */
export function radar(host, {period = 4.2, blips = 9, rings = 4} = {}) {
  const seed = i => ((Math.sin(i * 127.1) * 43758.5453) % 1 + 1) % 1;
  const marks = Array.from({length: blips}, (_, i) => ({
    a: seed(i) * Math.PI * 2, r: .22 + seed(i + 40) * .72, seen: -9,
  }));
  return stage(host, (a, t) => {
    const {ctx: c, w, h} = a, cx = w / 2, cy = h / 2, R = Math.min(w, h) / 2 - 2;
    c.clearRect(0, 0, w, h);
    const ink = rgb(tok('--ink')), acc = rgb(tok('--accent'));
    c.strokeStyle = rgba(ink, .13); c.lineWidth = 1;
    for (let i = 1; i <= rings; i++) { c.beginPath(); c.arc(cx, cy, R * i / rings, 0, 7); c.stroke() }
    for (let i = 0; i < 8; i++) {
      const th = i * Math.PI / 4;
      c.beginPath(); c.moveTo(cx, cy); c.lineTo(cx + Math.cos(th) * R, cy + Math.sin(th) * R); c.stroke();
    }
    const beam = (t / period) * Math.PI * 2 % (Math.PI * 2);
    const g = c.createConicGradient ? c.createConicGradient(beam - .9, cx, cy) : null;
    if (g) {
      g.addColorStop(0, rgba(acc, 0)); g.addColorStop(.22, rgba(acc, .20)); g.addColorStop(.25, rgba(acc, 0));
      c.fillStyle = g; c.beginPath(); c.moveTo(cx, cy); c.arc(cx, cy, R, 0, 7); c.fill();
    }
    c.strokeStyle = rgba(acc, .7); c.lineWidth = 1.4;
    c.beginPath(); c.moveTo(cx, cy); c.lineTo(cx + Math.cos(beam) * R, cy + Math.sin(beam) * R); c.stroke();
    for (const m of marks) {
      const da = ((beam - m.a) % (Math.PI * 2) + Math.PI * 2) % (Math.PI * 2);
      if (da < .06) m.seen = t;
      const age = t - m.seen, k = Math.max(0, 1 - age / (period * .95));
      if (k <= 0) continue;
      const x = cx + Math.cos(m.a) * R * m.r, y = cy + Math.sin(m.a) * R * m.r;
      c.fillStyle = rgba(acc, k * .9);
      c.beginPath(); c.arc(x, y, 2.4, 0, 7); c.fill();
      c.strokeStyle = rgba(acc, k * .35); c.lineWidth = 1;
      c.beginPath(); c.arc(x, y, 3 + (1 - k) * 13, 0, 7); c.stroke();
    }
  });
}

/* ── topo ──────────────────────────────────────────────────────────────────
 * Marching-squares contours of a drifting noise field: the
 * lines look surveyed rather than drawn, and cost one pass over a coarse grid.
 */
export function topo(host, {step = 26, levels = 7, speed = .05, alpha = .5} = {}) {
  const hash = (x, y) => ((Math.sin(x * 127.1 + y * 311.7) * 43758.5453) % 1 + 1) % 1;
  const noise = (x, y) => {
    const xi = Math.floor(x), yi = Math.floor(y), xf = x - xi, yf = y - yi;
    const u = xf * xf * (3 - 2 * xf), v = yf * yf * (3 - 2 * yf);
    return (hash(xi, yi) * (1 - u) + hash(xi + 1, yi) * u) * (1 - v)
         + (hash(xi, yi + 1) * (1 - u) + hash(xi + 1, yi + 1) * u) * v;
  };
  return stage(host, (a, t) => {
    const {ctx: c, w, h} = a;
    c.clearRect(0, 0, w, h);
    const ink = rgb(tok('--ink')), acc = rgb(tok('--accent'));
    const cols = Math.ceil(w / step) + 1, rows = Math.ceil(h / step) + 1;
    const f = new Float32Array(cols * rows);
    for (let j = 0; j < rows; j++) for (let i = 0; i < cols; i++)
      f[j * cols + i] = noise(i * .19 + t * speed, j * .19 - t * speed * .6)
                      + noise(i * .41 - t * speed * .4, j * .41) * .5;
    c.lineWidth = 1;
    for (let L = 1; L <= levels; L++) {
      const iso = .35 + L * (1.05 / (levels + 1));
      c.strokeStyle = rgba(L === Math.ceil(levels / 2) ? acc : ink, (L % 2 ? .16 : .09) * alpha);
      c.beginPath();
      for (let j = 0; j < rows - 1; j++) for (let i = 0; i < cols - 1; i++) {
        const x = i * step, y = j * step;
        const v = [f[j * cols + i], f[j * cols + i + 1], f[(j + 1) * cols + i + 1], f[(j + 1) * cols + i]];
        const idx = (v[0] > iso ? 8 : 0) | (v[1] > iso ? 4 : 0) | (v[2] > iso ? 2 : 0) | (v[3] > iso ? 1 : 0);
        if (idx === 0 || idx === 15) continue;
        const lerp = (a1, b1) => (iso - a1) / (b1 - a1 || 1e-6);
        const T = [x + step * lerp(v[0], v[1]), y], R2 = [x + step, y + step * lerp(v[1], v[2])],
              B = [x + step * lerp(v[3], v[2]), y + step], L2 = [x, y + step * lerp(v[0], v[3])];
        const seg = {1: [L2, B], 2: [B, R2], 3: [L2, R2], 4: [T, R2], 5: [T, L2], 6: [T, B], 7: [T, L2],
                     8: [T, L2], 9: [T, B], 10: [T, R2], 11: [T, R2], 12: [L2, R2], 13: [B, R2], 14: [L2, B]}[idx];
        if (!seg) continue;
        c.moveTo(seg[0][0], seg[0][1]); c.lineTo(seg[1][0], seg[1][1]);
      }
      c.stroke();
    }
  });
}

/* ── ridgeline ─────────────────────────────────────────────────────────────
 * Stacked filled profiles scrolling at different rates —
 * the parallax does the work; each layer on its own is a single sine sum.
 */
export function ridgeline(host, {lines = 11, speed = .16, alpha = .6} = {}) {
  return stage(host, (a, t) => {
    const {ctx: c, w, h} = a;
    c.clearRect(0, 0, w, h);
    const ink = rgb(tok('--ink')), acc = rgb(tok('--accent')), bg = rgb(tok('--fx-bg') || tok('--bg'));
    for (let L = lines - 1; L >= 0; L--) {
      const k = L / (lines - 1), base = h * (.24 + k * .78), amp = h * (.05 + k * .11);
      c.beginPath(); c.moveTo(-4, h + 4);
      for (let x = -4; x <= w + 4; x += 7) {
        const p = x / w * 6.2, s = t * speed * (.4 + k);
        const y = base - (Math.sin(p + s) * .6 + Math.sin(p * 2.3 - s * .7) * .28
                        + Math.sin(p * 4.7 + s * 1.3) * .12) * amp;
        c.lineTo(x, y);
      }
      c.lineTo(w + 4, h + 4); c.closePath();
      c.fillStyle = rgba(bg, .92); c.fill();
      c.strokeStyle = rgba(k > .72 ? acc : ink, (.10 + k * .22) * alpha);
      c.lineWidth = 1; c.stroke();
    }
  });
}

/* ── hud grid ──────────────────────────────────────────────────────────────
 * A ground plane in perspective plus a horizon glow. Cheap, and it is the single
 * cue that says "control room" faster than anything else on this list.
 */
export function hudgrid(host, {speed = .18, alpha = .5, horizon = .42} = {}) {
  return stage(host, (a, t) => {
    const {ctx: c, w, h} = a, hz = h * horizon;
    c.clearRect(0, 0, w, h);
    const acc = rgb(tok('--accent')), ink = rgb(tok('--ink'));
    const g = c.createLinearGradient(0, hz - h * .12, 0, hz + h * .02);
    g.addColorStop(0, rgba(acc, 0)); g.addColorStop(1, rgba(acc, .13 * alpha));
    c.fillStyle = g; c.fillRect(0, hz - h * .12, w, h * .14);
    c.lineWidth = 1;
    // Rows: exponential spacing so they crowd at the horizon like real perspective.
    for (let i = 0; i < 26; i++) {
      const f = ((i + (t * speed) % 1) / 26) ** 2.6;
      const y = hz + f * (h - hz);
      c.strokeStyle = rgba(acc, (.05 + f * .2) * alpha);
      c.beginPath(); c.moveTo(0, y); c.lineTo(w, y); c.stroke();
    }
    for (let i = -14; i <= 14; i++) {
      c.strokeStyle = rgba(ink, .10 * alpha);
      c.beginPath(); c.moveTo(w / 2 + i * w * .012, hz); c.lineTo(w / 2 + i * w * .17, h); c.stroke();
    }
  });
}

/* ── radial gauge ──────────────────────────────────────────────────────────
 * A dial with a glow proportional to its own value, so a screen of them reads at
 * a glance from across a room — the actual job of a wall dashboard.
 */
export function gauge(host, {value = 0, max = 100, label = '', unit = '%', spring = .09} = {}) {
  let cur = 0, target = value;
  const s = stage(host, (a, t) => {
    const {ctx: c, w, h} = a, cx = w / 2, cy = h * .56, R = Math.min(w / 2, h / .95) * .78;
    cur += (target - cur) * (RM.matches ? 1 : spring);
    c.clearRect(0, 0, w, h);
    const acc = rgb(tok('--accent')), ink = rgb(tok('--ink')), muted = rgb(tok('--muted'));
    const A0 = Math.PI * .75, A1 = Math.PI * 2.25, k = Math.max(0, Math.min(1, cur / max));
    c.lineCap = 'round';
    c.strokeStyle = rgba(ink, .10); c.lineWidth = Math.max(5, R * .13);
    c.beginPath(); c.arc(cx, cy, R, A0, A1); c.stroke();
    c.save();
    c.shadowColor = rgba(acc, .55); c.shadowBlur = R * .35;
    c.strokeStyle = rgba(acc, .95);
    c.beginPath(); c.arc(cx, cy, R, A0, A0 + (A1 - A0) * k); c.stroke();
    c.restore();
    // Ticks read as calibration; without them a ring is just a progress bar.
    for (let i = 0; i <= 10; i++) {
      const th = A0 + (A1 - A0) * i / 10, r0 = R * 1.16, r1 = R * (i % 5 ? 1.22 : 1.28);
      c.strokeStyle = rgba(ink, i / 10 <= k ? .4 : .16); c.lineWidth = 1;
      c.beginPath(); c.moveTo(cx + Math.cos(th) * r0, cy + Math.sin(th) * r0);
      c.lineTo(cx + Math.cos(th) * r1, cy + Math.sin(th) * r1); c.stroke();
    }
    c.textAlign = 'center';
    c.fillStyle = rgba(ink, .96);
    c.font = `600 ${R * .52}px ${tok('--mono') || 'monospace'}`;
    c.fillText((cur).toFixed(cur < 10 ? 1 : 0), cx, cy + R * .16);
    c.font = `500 ${R * .2}px ${tok('--sans') || 'sans-serif'}`;
    c.fillStyle = rgba(muted, .9);
    c.fillText(unit, cx, cy + R * .44);
    if (label) c.fillText(label, cx, cy + R * .78);
  });
  if (s) s.set = v => { target = v; if (RM.matches) { cur = v } s.start() };
  return s;
}

/* ── sparkline ribbon ──────────────────────────────────────────────────────
 * A value trail that travels rather than redraws — for tickers and live rows
 * where an ECharts instance per cell would be absurd.
 */
export function trail(host, {points = 48, band = .5} = {}) {
  let vals = Array.from({length: points}, (_, i) => Math.sin(i * .3) * .4 + .5);
  const s = stage(host, (a) => {
    const {ctx: c, w, h} = a;
    c.clearRect(0, 0, w, h);
    const acc = rgb(tok('--accent'));
    const X = i => i / (vals.length - 1) * w, Y = v => h - 2 - v * (h - 4);
    const g = c.createLinearGradient(0, 0, 0, h);
    g.addColorStop(0, rgba(acc, .34 * band)); g.addColorStop(1, rgba(acc, 0));
    c.beginPath(); c.moveTo(0, h);
    vals.forEach((v, i) => c.lineTo(X(i), Y(v)));
    c.lineTo(w, h); c.closePath(); c.fillStyle = g; c.fill();
    c.beginPath(); vals.forEach((v, i) => i ? c.lineTo(X(i), Y(v)) : c.moveTo(X(i), Y(v)));
    c.strokeStyle = rgba(acc, .95); c.lineWidth = 1.5; c.stroke();
    c.fillStyle = rgba(acc, 1);
    c.beginPath(); c.arc(w, Y(vals[vals.length - 1]), 2.2, 0, 7); c.fill();
  });
  if (s) s.push = v => { vals.push(v); vals.shift() };
  return s;
}

/* ── circuit ───────────────────────────────────────────────────────────────
 * PCB traces under the content: manhattan lines on a coarse grid, a pad at
 * each end, and a slow current of amber pulses travelling the traces. This is
 * what makes the ground say "electronics" instead of just "dark with glow".
 */
/* ── circuit ─────────────────────────────────────────────────────────────
 * Routed PCB wiring: copper traces with 45° mitered corners hugging a
 * routing grid, branch junctions (solder blobs), annular vias at layer
 * changes, ringed pads at every endpoint, mixed trace widths, and a slow
 * current of amber electron pulses that travel the traces — tails hugging
 * the path segment by segment so they never cut across a corner.
 */
export function circuit(host, {step = 96, alpha = .5, fps = 24} = {}) {
  const seed = i => ((Math.sin(i * 127.1) * 43758.5453) % 1 + 1) % 1;
  let nets = [], pulses = [], vias = [], junctions = [];

  // turn 90° corners into 45° miters — the classic routed-trace look
  const miter = (pts, d0 = 26) => {
    if (pts.length < 3) return pts;
    const out = [pts[0]];
    for (let i = 1; i < pts.length - 1; i++) {
      const [ax, ay] = pts[i - 1], [px, py] = pts[i], [bx, by] = pts[i + 1];
      const d = Math.min(d0, Math.hypot(px - ax, py - ay) / 2, Math.hypot(bx - px, by - py) / 2);
      out.push([px - Math.sign(px - ax) * d, py - Math.sign(py - ay) * d]);
      out.push([px + Math.sign(bx - px) * d, py + Math.sign(by - py) * d]);
    }
    out.push(pts[pts.length - 1]);
    return out;
  };

  const build = (w, h) => {
    const cols = Math.ceil(w / step), rows = Math.ceil(h / step);
    nets = []; pulses = []; vias = []; junctions = [];
    const used = new Set();
    const n = Math.round(cols * rows * .15);
    for (let i = 0; i < n; i++) {
      let x = Math.round(seed(i * 3 + 1) * cols), y = Math.round(seed(i * 7 + 2) * rows);
      const raw = [[x, y]];
      let horiz = seed(i * 11) > .5;
      const segs = 3 + Math.floor(seed(i * 13) * 4);
      for (let s = 0; s < segs; s++) {
        const len = (1 + Math.floor(seed(i * 17 + s) * 4)) * (seed(i * 19 + s) > .5 ? 1 : -1);
        if (horiz) x = Math.max(0, Math.min(cols, x + len));
        else y = Math.max(0, Math.min(rows, y + len));
        raw.push([x, y]);
        horiz = !horiz;
      }
      if (raw.length < 3) continue;
      const pts = miter(raw.map(([gx, gy]) => [gx * step, gy * step]));
      const net = {
        pts,
        width: seed(i * 31) > .72 ? 2 : 1.1,         // power nets run wider
        acc: seed(i * 37) > .6,                      // some nets tinted copper-amber
        viaAt: seed(i * 41) > .5 ? 0 : raw.length - 1, // via at one end
      };
      nets.push(net);
      // annular via where the net changes layer
      const [vx, vy] = raw[net.viaAt];
      if (!used.has(vx + ':' + vy)) { used.add(vx + ':' + vy); vias.push([vx * step, vy * step]); }
      // mid-trace vias at some corners
      for (let k = 1; k < raw.length - 1; k++) {
        const key = raw[k][0] + ':' + raw[k][1];
        if (!used.has(key) && seed(i * 43 + k * 7) > .78) {
          used.add(key); vias.push([raw[k][0] * step, raw[k][1] * step]);
        }
      }
      // branch stub: a T-junction off a random mid point
      if (seed(i * 47) > .55) {
        const k = 1 + Math.floor(seed(i * 53) * (raw.length - 2));
        const [jx, jy] = raw[k];
        const dx = horiz ? 0 : (seed(i * 59) > .5 ? 1 : -1);
        const dy = horiz ? (seed(i * 59) > .5 ? 1 : -1) : 0;
        const blen = 1 + Math.floor(seed(i * 61) * 2);
        const ex = Math.max(0, Math.min(cols, jx + dx * blen));
        const ey = Math.max(0, Math.min(rows, jy + dy * blen));
        if (ex !== jx || ey !== jy) {
          junctions.push([jx * step, jy * step]);
          nets.push({
            pts: [[jx * step, jy * step], [ex * step, ey * step]],
            width: 1.1, acc: seed(i * 67) > .6, viaAt: -1,
          });
        }
      }
    }
    const pn = Math.min(9, nets.length);
    for (let i = 0; i < pn; i++)
      pulses.push({net: nets[Math.floor(seed(i * 23) * nets.length)],
                   t: seed(i * 29), sp: .0016 + seed(i * 67) * .0018});
  };

  const at = (pts, t) => {
    // point at fraction t along a polyline
    let total = 0; const lens = [];
    for (let i = 1; i < pts.length; i++) {
      const l = Math.hypot(pts[i][0] - pts[i - 1][0], pts[i][1] - pts[i - 1][1]);
      lens.push(l); total += l;
    }
    let d = t * total;
    for (let i = 1; i < pts.length; i++) {
      if (d <= lens[i - 1]) {
        const k = lens[i - 1] ? d / lens[i - 1] : 0;
        return [pts[i - 1][0] + (pts[i][0] - pts[i - 1][0]) * k, pts[i - 1][1] + (pts[i][1] - pts[i - 1][1]) * k];
      }
      d -= lens[i - 1];
    }
    return pts[pts.length - 1];
  };

  return stage(host, (a, t) => {
    const {ctx: c, w, h} = a;
    if (!nets.length || nets.w !== w || nets.h !== h) { build(w, h); nets.w = w; nets.h = h }
    c.clearRect(0, 0, w, h);
    const acc = rgb(tok('--accent')), ink = rgb(tok('--ink'));
    c.lineCap = 'round'; c.lineJoin = 'round';

    // copper traces
    for (const net of nets) {
      c.strokeStyle = net.acc ? rgba(acc, .14 * alpha) : rgba(ink, .13 * alpha);
      c.lineWidth = net.width;
      c.beginPath();
      net.pts.forEach(([x, y], i) => i ? c.lineTo(x, y) : c.moveTo(x, y));
      c.stroke();
      // ringed pad at each endpoint
      for (const [x, y] of [net.pts[0], net.pts[net.pts.length - 1]]) {
        c.strokeStyle = rgba(acc, .26 * alpha);
        c.lineWidth = 1;
        c.beginPath(); c.arc(x, y, 4.6, 0, 7); c.stroke();
        c.fillStyle = rgba(acc, .2 * alpha);
        c.beginPath(); c.arc(x, y, 1.9, 0, 7); c.fill();
      }
    }

    // solder blobs at T-junctions
    for (const [x, y] of junctions) {
      c.fillStyle = rgba(acc, .34 * alpha);
      c.beginPath(); c.arc(x, y, 2.6, 0, 7); c.fill();
    }

    // annular vias
    for (const [x, y] of vias) {
      c.strokeStyle = rgba(acc, .32 * alpha);
      c.lineWidth = 1;
      c.beginPath(); c.arc(x, y, 3.6, 0, 7); c.stroke();
      c.fillStyle = rgba(acc, .44 * alpha);
      c.beginPath(); c.arc(x, y, 1.1, 0, 7); c.fill();
    }

    // electron pulses: tail hugs the trace segment by segment
    for (const p of pulses) {
      p.t += p.sp;
      if (p.t > 1.06) { p.t = -.06; p.net = nets[Math.floor(Math.random() * nets.length)] }
      const fade = Math.sin(Math.min(1, Math.max(0, p.t)) * Math.PI);
      const T1 = Math.max(0, Math.min(1, p.t));
      const T0 = Math.max(0, Math.min(1, p.t - .06));
      if (T1 <= 0) continue;
      const STEPS = 9;
      let prev = at(p.net.pts, T0);
      c.lineWidth = 1.7;
      for (let s2 = 1; s2 <= STEPS; s2++) {
        const pt = at(p.net.pts, T0 + (T1 - T0) * s2 / STEPS);
        c.strokeStyle = rgba(acc, (s2 / STEPS) ** 1.7 * .8 * fade * alpha);
        c.beginPath(); c.moveTo(prev[0], prev[1]); c.lineTo(pt[0], pt[1]); c.stroke();
        prev = pt;
      }
      const [hx, hy] = at(p.net.pts, T1);
      c.save();
      c.shadowColor = rgba(acc, .9 * fade); c.shadowBlur = 12;
      c.fillStyle = rgba(acc, .95 * fade * alpha);
      c.beginPath(); c.arc(hx, hy, 2, 0, 7); c.fill();
      c.restore();
    }
  }, {fps});
}

export const Fx = {aurora, gas, constellation, radar, topo, ridgeline, hudgrid, gauge, trail, circuit, rgb, rgba, tok};
export default Fx;
