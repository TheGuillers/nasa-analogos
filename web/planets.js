/* ALTERGEA · procedural planets for the hero (no image downloads).
   Each world gets an equirectangular texture built from 3D fractal noise (seamless on a sphere),
   then a small software renderer maps it onto a lit, slowly rotating disc. */
'use strict';
(function () {
  const TW = 768, TH = 384;

  // ---- seeded 3D value noise ----
  function makeNoise(seed) {
    const P = new Uint8Array(512); const base = [...Array(256).keys()];
    let r = seed; const rnd = () => (r = (r * 1664525 + 1013904223) >>> 0) / 4294967296;
    for (let i = 255; i > 0; i--) { const j = Math.floor(rnd() * (i + 1)); [base[i], base[j]] = [base[j], base[i]]; }
    for (let i = 0; i < 512; i++) P[i] = base[i & 255];
    const fade = t => t * t * (3 - 2 * t);
    const h = (x, y, z) => P[P[P[x & 255] + (y & 255)] + (z & 255)] / 255;
    const n3 = (x, y, z) => {
      const xi = Math.floor(x), yi = Math.floor(y), zi = Math.floor(z); const xf = fade(x - xi), yf = fade(y - yi), zf = fade(z - zi);
      const l = (a, b, t) => a + (b - a) * t;
      return l(l(l(h(xi, yi, zi), h(xi + 1, yi, zi), xf), l(h(xi, yi + 1, zi), h(xi + 1, yi + 1, zi), xf), yf),
        l(l(h(xi, yi, zi + 1), h(xi + 1, yi, zi + 1), xf), l(h(xi, yi + 1, zi + 1), h(xi + 1, yi + 1, zi + 1), xf), yf), zf);
    };
    return (x, y, z, oct = 5) => { let a = 0, amp = .5, f = 1, t = 0; for (let i = 0; i < oct; i++) { a += amp * n3(x * f, y * f, z * f); t += amp; amp *= .5; f *= 2.03; } return a / t; };
  }
  const mix = (a, b, t) => [a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t, a[2] + (b[2] - a[2]) * t];
  const sstep = (a, b, x) => { const t = Math.min(1, Math.max(0, (x - a) / (b - a))); return t * t * (3 - 2 * t); };

  // texture generators: return {col: Uint8ClampedArray(TW*TH*4), cloud?: Uint8Array, ocean?: Uint8Array}
  function eachPixel(fn) {
    for (let y = 0; y < TH; y++) {
      const lat = (y / (TH - 1) - .5) * Math.PI, cl = Math.cos(lat), sl = Math.sin(lat);
      for (let x = 0; x < TW; x++) { const lon = x / TW * Math.PI * 2; fn(x, y, cl * Math.cos(lon), sl, cl * Math.sin(lon), lat); }
    }
  }
  function earthTex() {
    const nz = makeNoise(11), nc = makeNoise(97); const col = new Uint8ClampedArray(TW * TH * 4), cloud = new Uint8Array(TW * TH), spec = new Uint8Array(TW * TH);
    eachPixel((x, y, px, py, pz, lat) => {
      const i = y * TW + x;
      const warp = nz(px * 1.3 + 9, py * 1.3, pz * 1.3, 3) * .35;
      const e = nz(px * 1.5 + warp, py * 1.5 + warp, pz * 1.5, 6);
      const sea = .52; let c;
      if (e < sea) { const d = sstep(.30, sea, e); c = mix([4, 22, 74], [24, 120, 190], d ** 1.6); spec[i] = 255; }
      else {
        const h = (e - sea) / (1 - sea); const dry = nz(px * 2.2 + 40, py * 2.2, pz * 2.2, 4);
        const lowland = mix([46, 112, 52], [150, 140, 78], sstep(.40, .68, dry)); c = mix(lowland, [118, 96, 72], sstep(.25, .6, h)); c = mix(c, [235, 238, 242], sstep(.62, .85, h)); spec[i] = 0;
      }
      const ice = sstep(1.08, 1.32, Math.abs(lat) + (nz(px * 5, py * 5, pz * 5, 3) - .5) * .25); c = mix(c, [240, 246, 252], ice);
      col[i * 4] = c[0]; col[i * 4 + 1] = c[1]; col[i * 4 + 2] = c[2]; col[i * 4 + 3] = 255;
      const w = nc(px * 2.1 + 3, py * 3.2, pz * 2.1, 5); cloud[i] = Math.round(sstep(.50, .74, w) * 235);
    });
    return { col, cloud, spec };
  }
  function marsTex() {
    const nz = makeNoise(5), nd = makeNoise(41); const col = new Uint8ClampedArray(TW * TH * 4);
    const craters = []; let r = 7; const rnd = () => (r = (r * 1664525 + 1013904223) >>> 0) / 4294967296;
    for (let k = 0; k < 90; k++) { const lo = rnd() * 6.283, la = Math.asin(rnd() * 1.6 - .8), rad = .02 + rnd() ** 3 * .09; craters.push([Math.cos(la) * Math.cos(lo), Math.sin(la), Math.cos(la) * Math.sin(lo), rad]); }
    eachPixel((x, y, px, py, pz, lat) => {
      const i = y * TW + x;
      const a = nz(px * 1.4, py * 1.4, pz * 1.4, 6), b = nd(px * 4, py * 4, pz * 4, 4);
      let c = mix([150, 62, 30], [226, 138, 84], a); c = mix(c, [74, 38, 28], sstep(.58, .78, nd(px * 1.7 + 5, py * 1.7, pz * 1.7, 4)) * .85);
      c = mix(c, [255, 200, 150], sstep(.55, .85, b) * .25);
      for (const q of craters) { const d = Math.acos(Math.min(1, px * q[0] + py * q[1] + pz * q[2])) / q[3];
        if (d < 1.25) { const f = d < .9 ? -.18 * (1 - d) : .22 * (1 - Math.abs(d - 1.05) / .2); c = [c[0] * (1 + f), c[1] * (1 + f), c[2] * (1 + f)]; } }
      const cap = sstep(1.25, 1.38, Math.abs(lat) + (b - .5) * .1); c = mix(c, [250, 245, 240], cap);
      col[i * 4] = c[0]; col[i * 4 + 1] = c[1]; col[i * 4 + 2] = c[2]; col[i * 4 + 3] = 255;
    });
    return { col };
  }
  function moonTex() {
    const nz = makeNoise(23), nm = makeNoise(63); const col = new Uint8ClampedArray(TW * TH * 4);
    const craters = []; let r = 19; const rnd = () => (r = (r * 1664525 + 1013904223) >>> 0) / 4294967296;
    for (let k = 0; k < 260; k++) { const lo = rnd() * 6.283, la = Math.asin(rnd() * 2 - 1), rad = .018 + rnd() ** 3 * .16; craters.push([Math.cos(la) * Math.cos(lo), Math.sin(la), Math.cos(la) * Math.sin(lo), rad]); }
    eachPixel((x, y, px, py, pz) => {
      const i = y * TW + x;
      const g = nz(px * 3, py * 3, pz * 3, 6), maria = sstep(.54, .62, nm(px * 1.2 + 2, py * 1.2, pz * 1.2, 4));
      let v = 150 + (g - .5) * 90; v = v * (1 - maria * .42);
      for (const q of craters) { const d = Math.acos(Math.min(1, px * q[0] + py * q[1] + pz * q[2])) / q[3];
        if (d < 1.4) { if (d < .85) v *= 1 - .22 * (1 - d * .6); else if (d < 1.2) v += 26 * (1 - Math.abs(d - 1) / .2) * (q[3] > .06 ? 1 : .7); else v += 8 * (1.4 - d); } }
      v = Math.max(40, Math.min(235, v));
      col[i * 4] = v; col[i * 4 + 1] = v * .985; col[i * 4 + 2] = v * .96; col[i * 4 + 3] = 255;
    });
    return { col };
  }

  // ---- renderer ----
  const L = (() => { const v = [-.6, .42, .68]; const m = Math.hypot(...v); return v.map(a => a / m); })();
  function makePlanet(cv, kind) {
    let tex = null, ang = kind === 'earth' ? 3.9 : kind === 'mars' ? 1.2 : 0.4;
    const speed = { earth: .0026, mars: .0017, moon: .0011 }[kind];
    function size() { const d = Math.min(window.devicePixelRatio || 1, 2); const s = Math.max(80, Math.round(cv.clientWidth * d)); if (cv.width !== s) { cv.width = cv.height = s; } }
    function draw() {
      if (!tex) return; size(); const S = cv.width, g = cv.getContext('2d'); const img = g.createImageData(S, S), D = img.data, R = S / 2;
      const cA = Math.cos(ang), sA = Math.sin(ang);
      for (let py = 0; py < S; py++) {
        for (let px = 0; px < S; px++) {
          const x = (px + .5 - R) / R, y = -(py + .5 - R) / R, d2 = x * x + y * y, o = (py * S + px) * 4;
          if (d2 > 1) { D[o + 3] = 0; continue; }
          const z = Math.sqrt(1 - d2);
          // rotate the sample point about the polar axis
          const rx = x * cA + z * sA, rz = -x * sA + z * cA;
          const lon = Math.atan2(rz, rx), lat = Math.asin(y);
          let u = lon / 6.2832; u -= Math.floor(u); const ti = Math.min(TH - 1, Math.floor((lat / Math.PI + .5) * TH)) * TW + Math.min(TW - 1, Math.floor(u * TW));
          let r = tex.col[ti * 4], gg = tex.col[ti * 4 + 1], b = tex.col[ti * 4 + 2];
          const dif = Math.max(0, x * L[0] + y * L[1] + z * L[2]);
          let lit = kind === 'moon' ? .04 + dif ** .9 * 1.02 : .05 + dif * 1.05;
          if (kind === 'earth') {
            const cl = tex.cloud[(Math.min(TH - 1, Math.floor((lat / Math.PI + .5) * TH))) * TW + Math.min(TW - 1, Math.floor(((((lon + ang * .35) / 6.2832) % 1 + 1) % 1) * TW))] / 255;
            r += (255 - r) * cl * .85; gg += (255 - gg) * cl * .85; b += (255 - b) * cl * .85;
            if (tex.spec[ti] && cl < .3) { const hv = [L[0] + 0, L[1], L[2] + 1]; const hm = Math.hypot(...hv); const sp = Math.max(0, (x * hv[0] + y * hv[1] + z * hv[2]) / hm) ** 40; r += sp * 160; gg += sp * 170; b += sp * 190; }
            // atmosphere rim
            const rim = (1 - z) ** 3 * 1.25; r += rim * 70 * (dif + .15); gg += rim * 140 * (dif + .15); b += rim * 255 * (dif + .15);
          } else if (kind === 'mars') { const rim = (1 - z) ** 4 * .6; r += rim * 255 * dif; gg += rim * 150 * dif; b += rim * 100 * dif; }
          D[o] = r * lit; D[o + 1] = gg * lit; D[o + 2] = b * lit; D[o + 3] = 255;
        }
      }
      g.putImageData(img, 0, 0);
    }
    return { build() { tex = { earth: earthTex, mars: marsTex, moon: moonTex }[kind](); draw(); requestAnimationFrame(() => cv.parentElement.classList.add('ready')); }, step() { ang += speed; draw(); }, draw };
  }

  function init() {
    const cvs = [...document.querySelectorAll('canvas[data-planet]')]; if (!cvs.length) return;
    const ps = cvs.map(c => makePlanet(c, c.dataset.planet));
    const reduce = window.matchMedia && matchMedia('(prefers-reduced-motion: reduce)').matches;
    let i = 0; const buildNext = () => { if (i < ps.length) { ps[i++].build(); setTimeout(buildNext, 20); } else if (!reduce) loop(); };
    const hero = document.getElementById('top'); let last = 0, vis = true;
    if (window.IntersectionObserver && hero) new IntersectionObserver(e => { vis = e[0].isIntersecting; }).observe(hero);
    function loop(t = 0) { requestAnimationFrame(loop); if (!vis || document.hidden || t - last < 50) return; last = t; ps.forEach(p => p.step()); }
    window.addEventListener('resize', () => ps.forEach(p => p.draw()));
    setTimeout(buildNext, 30);
  }
  document.addEventListener('DOMContentLoaded', init);
})();
