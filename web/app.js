/* ALTERGEA · static web build. Runs the similarity model in the browser on precomputed NASA data (data/sites.json),
   and talks to NASA POWER, OpenTopoData, NASA Mars Trek, NASA GIBS and INGEMMET directly from the page. */
'use strict';

// ---------- constants ----------
const NAVY = '#0d1b5e', SKY = '#1fa2e8', RED = '#c8102e', MUTED = '#5f6b85';
const SCALE = ['#d6dce8', '#8fbfe3', '#2f7fc1', NAVY];              // Weak · Moderate · Strong · Prime
const BRAND = [NAVY, '#2f7fc1', '#8fbfe3', RED, '#8a93ad'];
const FONT = { family: 'IBM Plex Sans, Segoe UI, system-ui, sans-serif', color: '#1b2340' };
const LABELS = { aridity: 'Aridity', thermal: 'Thermal range', albedo: 'Albedo match', slope: 'Slope',
  altitude: 'Altitude', wind: 'Wind (aeolian)' };
const KEYS = Object.keys(LABELS);
const DEFAULT_W = {
  Mars: { aridity: .25, thermal: .20, albedo: .15, slope: .15, altitude: .10, wind: .15 },
  Moon: { aridity: .15, thermal: .25, albedo: .25, slope: .20, altitude: .15, wind: .00 } };
const ALBEDO = { Mars: .25, Moon: .12 };
const MB = [-5.554, -80.757], NAMIB = [-4.67959, 137.36717], BRADBURY = [-4.5895, 137.4417];
const MARS_REFS = { 'Bagnold Dunes · Namib Dune (Gale)': NAMIB, 'Bradbury Landing · plains (Gale)': BRADBURY };
const TREK = (layer, ext) => `https://trek.nasa.gov/tiles/Mars/EQ/${layer}/1.0.0/default/default028mm/{z}/{y}/{x}.${ext}`;
const TREK_LAYERS = [
  ['Viking MDIM 2.1 colour mosaic · 232 m (global)', 'Mars_Viking_MDIM21_ClrMosaic_global_232m', 'jpg', 8, true, true],
  ['MOLA colour hillshade · 463 m (global)', 'Mars_MGS_MOLA_ClrShade_merge_global_463m', 'jpg', 7, false, false],
  ['MRO CTX · Gale crater mosaic', 'Gale_CTX_BlockAdj_dd', 'png', 14, true, false],
  ['MRO HiRISE · Curiosity roving site mosaic', 'curiosity_hirise_mosaic', 'png', 18, true, false],
  ['MRO HiRISE · Gale DEM 1 m (hillshade)', 'Gale_DEM_SMG_1m', 'png', 16, false, false]];
const GIBS = 'https://gibs.earthdata.nasa.gov/wmts/epsg3857/best/MODIS_Terra_CorrectedReflectance_TrueColor/default/2025-08-15/GoogleMapsCompatible_Level9/{z}/{y}/{x}.jpg';
const ESRI_IMG = 'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}';
const ESRI_TOPO = 'https://server.arcgisonline.com/ArcGIS/rest/services/World_Topo_Map/MapServer/tile/{z}/{y}/{x}';
const ESRI_ATTR = 'Esri, Maxar, Earthstar Geographics';
const ING_WMS = svc => `https://geocatmin.ingemmet.gob.pe/arcgis/services/${svc}/MapServer/WMSServer`;
const ING_REST = svc => `https://geocatmin.ingemmet.gob.pe/arcgis/rest/services/${svc}/MapServer/identify`;
const ING_SERVICES = { 'Geology 1:100k (integrated)': ['SERV_GEOLOGIA_100K_INTEGRADA', '6'],
  'Geomorphology': ['SERV_GEOMORFOLOGIA', 'Geomorfologia'] };
const REF = {
  Mars: { aridity: '0 mm/yr, no rain', thermal: '≈ 70 °C diurnal (REMS, Gale)', albedo: t => `${t} (regional)`,
    slope: s => `≤ ${s}° rover-safe`, altitude: '6–7 mbar surface pressure (altitude is the Earth proxy)',
    wind: '5–10 m/s typical, gusts > 15 (REMS)' },
  Moon: { aridity: 'no atmosphere', thermal: '≈ 250 °C diurnal (Diviner, equator)', albedo: t => `${t}`,
    slope: s => `≤ ${s}° lander-safe`, altitude: 'vacuum (altitude is the Earth proxy)', wind: 'none: weight 0' } };
const FMT = { aridity: r => `${Math.round(r.precip_mm)} mm/yr`, thermal: r => `${r.temp_range_c} °C`,
  albedo: r => `${r.albedo}`, slope: r => isNum(r.slope30_deg) ? `${r.slope30_deg}° (30 m DEM)` : `${r.slope_deg}° (1 km SRTM)`,
  altitude: r => `${Math.round(r.altitude_m)} m`,
  wind: r => `${r.wind10m_ms} m/s` };

// ---------- state ----------
const S = { target: 'Mars', W: { ...DEFAULT_W.Mars }, P: { slope: 10, arid: 150, wind: 6 }, alb: { ...ALBEDO },
  base: [], custom: [], res: [], focus: null, topn: 14, exSites: [], exActive: {}, marsRef: Object.keys(MARS_REFS)[0],
  blend: 0.5, s2: null, s2rows: [], peru: null, piura: false };
try { S.custom = JSON.parse(localStorage.getItem('altergea_custom') || '[]'); } catch (e) { S.custom = []; }

const $ = s => document.querySelector(s);
const el = (tag, attrs = {}, html = '') => { const e = document.createElement(tag); Object.assign(e, attrs); e.innerHTML = html; return e; };
const isNum = v => typeof v === 'number' && isFinite(v);
const fmtRef = (k) => { const r = REF[S.target][k]; return typeof r === 'function' ? r(k === 'albedo' ? S.alb[S.target] : S.P.slope) : r; };

// ---------- model ----------
const slopeOf = r => isNum(r.slope30_deg) ? r.slope30_deg : r.slope_deg;   // Copernicus DEM 30 m, else 1 km SRTM
function components(r, tgt) {
  const s = slopeOf(r);
  const slopeOk = !isNum(s) ? NaN : (s <= S.P.slope ? 1 : Math.exp(-(s - S.P.slope) / S.P.slope));
  const clip = (v, a, b) => Math.min(b, Math.max(a, v));
  return {
    aridity: isNum(r.precip_mm) ? Math.exp(-r.precip_mm / S.P.arid) : NaN,
    thermal: isNum(r.temp_range_c) ? clip(r.temp_range_c / 25, 0, 1) : NaN,
    albedo: isNum(r.albedo) ? Math.exp(-(((r.albedo - S.alb[tgt]) / 0.1) ** 2)) : NaN,
    slope: slopeOk,
    altitude: isNum(r.altitude_m) ? clip(r.altitude_m / 4000, 0, 1) : NaN,
    wind: isNum(r.wind10m_ms) ? clip(r.wind10m_ms / S.P.wind, 0, 1) : NaN };
}
function similarity(c, w) {
  let num = 0, den = 0;
  for (const k of KEYS) if (!isNaN(c[k])) { num += w[k] * c[k]; den += w[k]; }
  return den > 0 ? Math.round(num / den * 1000) / 1000 : NaN;
}
const tier = s => s >= .75 ? 'Prime analog' : s >= .6 ? 'Strong' : s >= .45 ? 'Moderate' : 'Weak';
const color = s => s >= .75 ? SCALE[3] : s >= .6 ? SCALE[2] : s >= .45 ? SCALE[1] : SCALE[0];
const mtext = s => s >= .6 ? '#ffffff' : NAVY;

function compute() {
  const W = Object.values(S.W).reduce((a, b) => a + b, 0) > 0 ? S.W : DEFAULT_W[S.target];
  const rows = [...S.base, ...S.custom].filter(r => !S.piura || inPiura(r)).map(r => {
    const c = components(r, S.target);
    const other = S.target === 'Mars' ? 'Moon' : 'Mars';
    return { ...r, comps: c, score: similarity(c, W),
      score_mars: similarity(components(r, 'Mars'), S.target === 'Mars' ? W : DEFAULT_W.Mars),
      score_moon: similarity(components(r, 'Moon'), S.target === 'Moon' ? W : DEFAULT_W.Moon), other };
  });
  const valid = rows.filter(r => !isNaN(r.score)).sort((a, b) => b.score - a.score);
  valid.forEach((r, i) => { r.rank = i + 1; r.tier = tier(r.score); });
  S.res = valid;
}

// ---------- shared UI bits ----------
const stat = (l, v, s) => `<div class="stat"><div class="l">${l}</div><div class="v">${v}</div><div class="s">${s}</div></div>`;
const pbar = (pct, w = 90) => `<span class="bar-bg" style="width:${w}px"><span class="bar" style="width:${Math.max(0, Math.min(100, pct))}%"></span></span>`;
const pct = v => isNaN(v) ? '<span class="spin">n/a</span>' : `${pbar(v * 100)}${Math.round(v * 100)} %`;

function renderStats() {
  const v = S.res; if (!v.length) { $('#stats').innerHTML = '<p class="err">No site data.</p>'; return; }
  const best = v[0], mean = v.reduce((a, r) => a + r.score, 0) / v.length;
  const driest = [...v].sort((a, b) => a.precip_mm - b.precip_mm)[0];
  $('#stats').innerHTML = stat('Best analog', best.site, `${best.country} · score ${best.score.toFixed(3)}`) +
    stat('Mean score', mean.toFixed(2), `across ${v.length} sites with data`) +
    stat('Prime analogs', v.filter(r => r.score >= .75).length, 'score ≥ 0.75') +
    stat('Driest site', driest.site, `${Math.round(driest.precip_mm)} mm/yr`);
  $('#m_target').textContent = S.target; $('#m_n').textContent = v.length;
}

// ---------- sidebar ----------
function buildSidebar() {
  const wdiv = $('#weights'); wdiv.innerHTML = '';
  for (const k of KEYS) {
    const row = el('div', { className: 'w-row' });
    row.innerHTML = `<label class="lbl" style="margin:6px 0 0">${LABELS[k]} weight</label><output id="ow_${k}">${S.W[k].toFixed(2)}</output>
      <input type="range" id="w_${k}" min="0" max="1" step="0.05" value="${S.W[k]}" style="grid-column:1/3">`;
    wdiv.appendChild(row);
    row.querySelector('input').addEventListener('input', e => { S.W[k] = +e.target.value; $(`#ow_${k}`).textContent = S.W[k].toFixed(2); update(); });
  }
  const bind = (id, out, key, obj, fmt = v => v) => $(id).addEventListener('input', e => { obj[key] = +e.target.value; $(out).textContent = fmt(obj[key]); update(); });
  bind('#p_slope', '#o_slope', 'slope', S.P); bind('#p_arid', '#o_arid', 'arid', S.P);
  bind('#p_wind', '#o_wind', 'wind', S.P, v => v.toFixed(1));
  $('#p_alb').addEventListener('input', e => { S.alb[S.target] = +e.target.value; $('#o_alb').textContent = S.alb[S.target].toFixed(2); update(); });
  $('#reset_params').addEventListener('click', () => { setTarget(S.target, true); });
  $('#only_piura').addEventListener('change', e => { S.piura = e.target.checked; update(); setFocus(null); });
  document.querySelectorAll('.seg-btn').forEach(b => b.addEventListener('click', () => setTarget(b.dataset.target, true)));
  $('#add_site').addEventListener('click', addCustomSite);
  $('#clear_sites').addEventListener('click', () => { S.custom = []; persistCustom(); update(); });
  // small screens: the control panel collapses behind a "Controls" button
  const tg = $('#side_toggle');
  tg.addEventListener('click', () => { const open = !$('#side').classList.contains('is-open'); $('#side').classList.toggle('is-open', open); tg.setAttribute('aria-expanded', open); });
  let rt; window.addEventListener('resize', () => { clearTimeout(rt); rt = setTimeout(() => { Object.values(maps).forEach(m => m && m.invalidateSize && m.invalidateSize()); update(); }, 250); });
}
const isSmall = () => window.innerWidth < 1000;
const H = (desktop, small) => isSmall() ? small : desktop;   // chart heights per layout
function setTarget(t, resetW) {
  S.target = t;
  if (resetW) { S.W = { ...DEFAULT_W[t] }; S.P = { slope: 10, arid: 150, wind: 6 }; S.alb = { ...ALBEDO }; }
  document.querySelectorAll('.seg-btn').forEach(b => { const on = b.dataset.target === t; b.classList.toggle('is-on', on); b.setAttribute('aria-checked', on); });
  for (const k of KEYS) { $(`#w_${k}`).value = S.W[k]; $(`#ow_${k}`).textContent = S.W[k].toFixed(2); }
  $('#p_slope').value = S.P.slope; $('#o_slope').textContent = S.P.slope;
  $('#p_arid').value = S.P.arid; $('#o_arid').textContent = S.P.arid;
  $('#p_wind').value = S.P.wind; $('#o_wind').textContent = S.P.wind.toFixed(1);
  $('#p_alb').value = S.alb[t]; $('#o_alb').textContent = S.alb[t].toFixed(2);
  update();
}
function persistCustom() { try { localStorage.setItem('altergea_custom', JSON.stringify(S.custom)); } catch (e) { /* private mode */ } }

async function addCustomSite() {
  const name = $('#c_name').value.trim() || 'My site', lat = +$('#c_lat').value, lon = +$('#c_lon').value;
  const st = $('#add_status'); const btn = $('#add_site'); btn.disabled = true;
  st.textContent = 'Fetching NASA POWER climatology…';
  const row = { site: name, country: 'Custom', type: 'User-defined', lat, lon, precip_mm: NaN, temp_range_c: NaN, albedo: NaN,
    wind10m_ms: NaN, wind10m_max_ms: NaN, altitude_m: NaN, slope_deg: NaN, roughness_m: NaN };
  try {
    const u = `https://power.larc.nasa.gov/api/temporal/climatology/point?parameters=PRECTOTCORR,T2M_RANGE,ALLSKY_SRF_ALB,WS10M,WS10M_MAX&community=RE&longitude=${lon}&latitude=${lat}&format=JSON`;
    const p = (await (await fetch(u)).json()).properties.parameter;
    const ann = k => { const v = p[k] && p[k].ANN; return (v == null || v <= -900) ? NaN : v; };
    row.precip_mm = +(ann('PRECTOTCORR') * 365).toFixed(1); row.temp_range_c = +ann('T2M_RANGE').toFixed(1);
    row.albedo = +ann('ALLSKY_SRF_ALB').toFixed(3); row.wind10m_ms = +ann('WS10M').toFixed(2); row.wind10m_max_ms = +ann('WS10M_MAX').toFixed(2);
  } catch (e) { st.textContent = 'NASA POWER did not answer; climate left empty. '; }
  st.textContent += ' Fetching SRTM elevation…';
  try {
    const step = 0.01, off = [-2, -1, 0, 1, 2];
    const pts = off.flatMap(a => off.map(b => `${(lat + a * step).toFixed(5)},${(lon + b * step).toFixed(5)}`)).join('|');
    let res = null;
    for (const ds of ['srtm30m', 'aster30m']) {
      const js = await (await fetch(`https://api.opentopodata.org/v1/${ds}?locations=${pts}`)).json();
      if (js.results && js.results.some(x => x.elevation != null)) { res = js.results; break; }
    }
    if (res) {
      const z = res.map(x => x.elevation); const mean = z.filter(v => v != null).reduce((a, b) => a + b, 0) / z.filter(v => v != null).length;
      const g = z.map(v => v == null ? mean : v);
      const dy = step * 111320, dx = dy * Math.cos(lat * Math.PI / 180);
      let sl = 0; const Z = (i, j) => g[i * 5 + j];
      for (let i = 0; i < 5; i++) for (let j = 0; j < 5; j++) {
        const gy = i === 0 ? (Z(1, j) - Z(0, j)) / dy : i === 4 ? (Z(4, j) - Z(3, j)) / dy : (Z(i + 1, j) - Z(i - 1, j)) / (2 * dy);
        const gx = j === 0 ? (Z(i, 1) - Z(i, 0)) / dx : j === 4 ? (Z(i, 4) - Z(i, 3)) / dx : (Z(i, j + 1) - Z(i, j - 1)) / (2 * dx);
        sl += Math.atan(Math.hypot(gx, gy)) * 180 / Math.PI;
      }
      const sd = Math.sqrt(g.reduce((a, v) => a + (v - mean) ** 2, 0) / g.length);
      row.altitude_m = Math.round(Z(2, 2)); row.slope_deg = +(sl / 25).toFixed(2); row.roughness_m = +sd.toFixed(1);
    }
  } catch (e) { st.textContent += ' Elevation service did not answer.'; }
  S.custom = S.custom.filter(r => r.site !== name); S.custom.push(row); persistCustom();
  st.textContent = `${name} added.`; btn.disabled = false; update();
}

// ---------- tabs ----------
const maps = {};
function buildTabs() {
  document.querySelectorAll('.tab').forEach(t => t.addEventListener('click', () => showTab(t.dataset.tab)));
}
function showTab(name) {
  document.querySelectorAll('.tab').forEach(t => t.classList.toggle('is-on', t.dataset.tab === name));
  document.querySelectorAll('.panel').forEach(p => p.classList.toggle('is-on', p.id === `tab-${name}`));
  if (name === 'twin') { ensureTwin(); setTimeout(() => { maps.earth.invalidateSize(); maps.mars.invalidateSize(); }, 50); }
  if (name === 'peru') { ensurePeru(); setTimeout(() => maps.peru && maps.peru.invalidateSize(), 50); }
  if (name === 'map') setTimeout(() => maps.main.invalidateSize(), 50);
  if (name === 'rank') renderRank();
  if (name === 'explore') renderExplorer();
}

// ---------- mission map ----------
let markerLayer;
function buildMap() {
  const m = L.map('map', { center: [15, -40], zoom: 2, zoomControl: true, worldCopyJump: true });
  const sat = L.tileLayer(ESRI_IMG, { attribution: ESRI_ATTR, maxZoom: 19 }).addTo(m);
  const osm = L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', { attribution: '© OpenStreetMap contributors', maxZoom: 19 });
  const topo = L.tileLayer(ESRI_TOPO, { attribution: 'Esri', maxZoom: 19 });
  const gibs = L.tileLayer(GIBS, { attribution: 'NASA GIBS / MODIS Terra', maxNativeZoom: 9, maxZoom: 19, opacity: .85 });
  const overlays = { 'NASA MODIS true colour (GIBS)': gibs };
  for (const [label, [svc, layer]] of Object.entries(ING_SERVICES))
    overlays[`INGEMMET · ${label}`] = L.tileLayer.wms(ING_WMS(svc), { layers: layer, format: 'image/png', transparent: true, version: '1.1.1', opacity: .6 });
  L.control.layers({ 'Satellite': sat, 'Street map': osm, 'Topographic': topo }, overlays).addTo(m);
  markerLayer = L.layerGroup().addTo(m);
  maps.main = m;
  // "All sites" control: shown while a site is focused, returns to the overview in one click
  const Back = L.Control.extend({ onAdd() {
    const b = L.DomUtil.create('button', 'map-back'); b.type = 'button'; b.textContent = '← All sites';
    b.title = 'Back to the overview'; L.DomEvent.disableClickPropagation(b);
    L.DomEvent.on(b, 'click', e => { L.DomEvent.stop(e); setFocus(null); }); return b; } });
  maps.back = new Back({ position: 'topleft' }); maps.backOn = false;
  $('#topn').addEventListener('input', e => { S.topn = +e.target.value; $('#o_topn').textContent = S.topn; renderMap(); });
  $('#focus_sel').addEventListener('change', e => setFocus(e.target.value || null));
  $('#legend').innerHTML = [['Prime ≥ 0.75', SCALE[3]], ['Strong ≥ 0.60', SCALE[2]], ['Moderate ≥ 0.45', SCALE[1]], ['Weak', SCALE[0]]]
    .map(([t, c]) => `<span><i class="dot" style="background:${c}"></i>${t}</span>`).join('');
}
function renderMap() {
  const v = S.res; const n = Math.min(S.topn, v.length);
  $('#topn').max = Math.max(3, v.length); $('#o_topn').textContent = n;
  markerLayer.clearLayers();
  v.slice(0, n).forEach(r => {
    const size = 26 + Math.round(r.score * 14);
    const icon = L.divIcon({ className: '', iconSize: [size, size], iconAnchor: [size / 2, size / 2],
      html: `<div class="marker-pin" style="width:${size}px;height:${size}px;background:${color(r.score)};color:${mtext(r.score)}">${r.rank}</div>` });
    const mk = L.marker([r.lat, r.lon], { icon, title: `#${r.rank} ${r.site}: ${r.score}` }).addTo(markerLayer);
    mk.bindPopup(`<b>#${r.rank} ${r.site}</b> (${r.country})<br>${r.type}<br>${S.target} similarity: <b>${r.score}</b> · ${r.tier}<br>
      Precip.: ${r.precip_mm} mm/yr · Range: ${r.temp_range_c} °C · Wind: ${r.wind10m_ms} m/s<br>
      Albedo: ${r.albedo} · Alt.: ${Math.round(r.altitude_m)} m · Slope: ${slopeOf(r)}°`, { maxWidth: 300 });
    mk.on('click', () => setFocus(r.site));
  });
  const sel = $('#focus_sel'); const cur = S.focus || '';
  sel.innerHTML = '<option value="">— none —</option>' + v.map(r => `<option value="${r.site}" ${r.site === cur ? 'selected' : ''}>${r.site}</option>`).join('');
  $('#top_title').textContent = `Top sites for ${S.target}`;
  $('#top_table').innerHTML = '<tr><th>rank</th><th>site</th><th>score</th></tr>' +
    v.slice(0, n).map(r => `<tr data-s="${r.site}" class="${r.site === S.focus ? 'is-on' : ''}" title="Click to zoom to this site"><td>${r.rank}</td><td>${r.site}</td><td>${pbar(r.score * 100, 70)}${r.score.toFixed(3)}</td></tr>`).join('');
  $('#top_table').querySelectorAll('tr[data-s]').forEach(tr => tr.addEventListener('click', () => setFocus(tr.dataset.s === S.focus ? null : tr.dataset.s)));
}
function setFocus(site) {
  S.focus = site;
  const anim = !document.hidden;   // hidden tabs pause animations: jump instead of flying
  if (site) { const r = S.res.find(x => x.site === site); if (r) maps.main[anim ? 'flyTo' : 'setView']([r.lat, r.lon], 9, { duration: 1.2 }); }
  else { const b = L.latLngBounds(S.res.map(r => [r.lat, r.lon])).pad(0.1); maps.main[anim ? 'flyToBounds' : 'fitBounds'](b, { duration: .9, maxZoom: S.piura ? 9 : 3 }); }
  if (site && !maps.backOn) { maps.back.addTo(maps.main); maps.backOn = true; }
  if (!site && maps.backOn) { maps.back.remove(); maps.backOn = false; }
  $('#focus_sel').value = site || '';
  document.querySelectorAll('#top_table tr[data-s]').forEach(tr => tr.classList.toggle('is-on', tr.dataset.s === site));
  renderFocus();
  if (site && isSmall()) setTimeout(() => $('#focus').scrollIntoView({ behavior: anim ? 'smooth' : 'auto', block: 'start' }), 400);
}

// ---------- surface comparison (focus) ----------
const tileCache = new Map();
function loadImg(url) {
  if (tileCache.has(url)) return tileCache.get(url);
  const p = new Promise(res => { const im = new Image(); im.crossOrigin = 'anonymous'; im.onload = () => res(im); im.onerror = () => res(null); im.src = url; });
  tileCache.set(url, p); return p;
}
async function mosaic(urls) {
  const c = document.createElement('canvas'); c.width = c.height = 768; const ctx = c.getContext('2d');
  ctx.fillStyle = '#282828'; ctx.fillRect(0, 0, 768, 768);
  const imgs = await Promise.all(urls.flat().map(loadImg));
  imgs.forEach((im, i) => { if (im) ctx.drawImage(im, (i % 3) * 256, Math.floor(i / 3) * 256, 256, 256); });
  return c;
}
function earthUrls(lat, lon, z = 15) {
  const n = 2 ** z, x = Math.floor((lon + 180) / 360 * n);
  const y = Math.floor((1 - Math.log(Math.tan(lat * Math.PI / 180) + 1 / Math.cos(lat * Math.PI / 180)) / Math.PI) / 2 * n);
  return { urls: [-1, 0, 1].map(dy => [-1, 0, 1].map(dx => ESRI_IMG.replace('{z}', z).replace('{x}', x + dx).replace('{y}', y + dy))),
    res: 156543.03 * Math.cos(lat * Math.PI / 180) / n };
}
function marsUrls(lat, lon, layer = 'curiosity_hirise_mosaic', z = 13) {
  const col = Math.floor((lon + 180) / 360 * 2 ** (z + 1)), row = Math.floor((90 - lat) / 180 * 2 ** z);
  const base = `https://trek.nasa.gov/tiles/Mars/EQ/${layer}/1.0.0/default/default028mm/${z}`;
  return { urls: [-1, 0, 1].map(dy => [-1, 0, 1].map(dx => `${base}/${row + dy}/${col + dx}.png`)), res: 180 / (256 * 2 ** z) * 59274.7 };
}
function stats(canvas) {
  try {
    const d = canvas.getContext('2d').getImageData(0, 0, 768, 768).data; const n = 768 * 768; const g = new Float32Array(n);
    for (let i = 0; i < n; i++) g[i] = (d[i * 4] * .299 + d[i * 4 + 1] * .587 + d[i * 4 + 2] * .114) / 255;
    let mean = 0; for (let i = 0; i < n; i++) mean += g[i]; mean /= n;
    let v = 0; for (let i = 0; i < n; i++) v += (g[i] - mean) ** 2; const sd = Math.sqrt(v / n);
    let lap = 0, cnt = 0;
    for (let y = 1; y < 767; y++) for (let x = 1; x < 767; x++) { const i = y * 768 + x; lap += Math.abs(g[i - 1] + g[i + 1] + g[i - 768] + g[i + 768] - 4 * g[i]); cnt++; }
    return { brightness: mean, contrast: sd, texture: lap / cnt };
  } catch (e) { return null; }      // canvas tainted: tiles served without CORS
}
async function renderFocus() {
  const box = $('#focus'); if (!S.focus) { box.hidden = true; box.innerHTML = ''; return; }
  const r = S.res.find(x => x.site === S.focus); if (!r) { box.hidden = true; return; }
  box.hidden = false;
  box.innerHTML = `<h3 style="margin-top:0">Surface comparison · ${r.site} ↔ Mars <button class="btn-link" id="focus_back">← All sites</button></h3>
    <p class="hint">Both patches cover about 3.8 km at ~5 m per pixel: Esri imagery on Earth, the MRO HiRISE mosaic of the
    Curiosity roving site (NASA Mars Trek) on Mars. Slide to fade one surface into the other.</p>
    <div class="row"><div><label class="lbl" for="mars_ref">Mars reference patch</label><select id="mars_ref">${Object.keys(MARS_REFS).map(k => `<option ${k === S.marsRef ? 'selected' : ''}>${k}</option>`).join('')}</select></div>
    <div class="grow"><label class="lbl">Earth ⟷ Mars blend <output id="o_blend">${Math.round(S.blend * 100)} % Mars</output></label><input type="range" id="blend" min="0" max="1" step="0.05" value="${S.blend}"></div></div>
    <div class="patches"><div><canvas id="cv_e" width="768" height="768"></canvas><div class="cap" id="cap_e"></div></div>
    <div><canvas id="cv_b" width="768" height="768"></canvas><div class="cap" id="cap_b"></div></div>
    <div><canvas id="cv_m" width="768" height="768"></canvas><div class="cap" id="cap_m"></div></div></div>
    <div class="two"><div><p class="h">Visual similarity of the two patches <span class="hint">(imagery statistics, not a physical measurement)</span></p><div id="vis_tbl" class="spin">Computing…</div></div>
    <div><p class="h">Environmental similarity to ${S.target}, by variable</p><div class="tbl-wrap"><table class="data" id="env_tbl"></table></div>
    <p class="hint">Weighted overall: ${Math.round(r.score * 100)} % (${r.tier}). Open the Similarity explorer tab to compare several sites variable by variable.</p></div></div>`;
  $('#focus_back').addEventListener('click', () => { setFocus(null); window.scrollTo({ top: 0, behavior: 'smooth' }); });
  $('#env_tbl').innerHTML = '<tr><th>Variable</th><th>Earth value</th><th>Similarity %</th><th>Weight</th></tr>' +
    KEYS.map(k => `<tr><td>${LABELS[k]}</td><td>${FMT[k](r)}</td><td>${pct(r.comps[k])}</td><td>${S.W[k].toFixed(2)}</td></tr>`).join('');
  const e = earthUrls(r.lat, r.lon); const ref = MARS_REFS[S.marsRef]; const m = marsUrls(ref[0], ref[1]);
  const [ce, cm] = await Promise.all([mosaic(e.urls), mosaic(m.urls)]);
  if (S.focus !== r.site) return;
  const draw = () => {
    $('#cv_e').getContext('2d').drawImage(ce, 0, 0); $('#cv_m').getContext('2d').drawImage(cm, 0, 0);
    const cb = $('#cv_b').getContext('2d'); cb.globalAlpha = 1; cb.drawImage(ce, 0, 0); cb.globalAlpha = S.blend; cb.drawImage(cm, 0, 0); cb.globalAlpha = 1;
    $('#cap_b').textContent = `Blend · ${Math.round((1 - S.blend) * 100)} % Earth / ${Math.round(S.blend * 100)} % Mars`;
  };
  draw();
  $('#cap_e').textContent = `${r.site} · Esri imagery · ${e.res.toFixed(1)} m/px`;
  $('#cap_m').textContent = `${S.marsRef} · HiRISE (Mars Trek) · ${m.res.toFixed(1)} m/px`;
  $('#blend').addEventListener('input', ev => { S.blend = +ev.target.value; $('#o_blend').textContent = `${Math.round(S.blend * 100)} % Mars`; draw(); });
  $('#mars_ref').addEventListener('change', ev => { S.marsRef = ev.target.value; renderFocus(); });
  const sa = stats(ce), sb = stats(cm);
  if (!sa || !sb) { $('#vis_tbl').innerHTML = '<p class="hint">The tile server did not allow pixel access from the browser, so image statistics are not available here. The Python app computes them server-side.</p>'; return; }
  const sim = { Brightness: 100 * (1 - Math.abs(sa.brightness - sb.brightness)),
    Contrast: 100 * Math.exp(-Math.abs(Math.log((sa.contrast + 1e-4) / (sb.contrast + 1e-4)))),
    'Fine texture': 100 * Math.exp(-Math.abs(Math.log((sa.texture + 1e-4) / (sb.texture + 1e-4)))) };
  const vals = [[sa.brightness, sb.brightness, 2], [sa.contrast, sb.contrast, 3], [sa.texture, sb.texture, 4]];
  $('#vis_tbl').className = ''; $('#vis_tbl').innerHTML = `<table class="data"><tr><th>Measure</th><th>Similarity %</th><th>Earth</th><th>Mars</th></tr>` +
    Object.entries(sim).map(([k, v], i) => `<tr><td>${k}</td><td>${pbar(v)}${Math.round(v)} %</td><td>${vals[i][0].toFixed(vals[i][2])}</td><td>${vals[i][1].toFixed(vals[i][2])}</td></tr>`).join('') +
    `</table><p class="hint">Visual mean ${Math.round(Object.values(sim).reduce((a, b) => a + b) / 3)} %. Brightness is the mean grey level, contrast its standard deviation, fine texture the mean absolute Laplacian; colour and illumination differ between the two sensors, so treat this as a qualitative cue.</p>`;
}

// ---------- ranking ----------
const PL = { displayModeBar: false, responsive: true };
function renderRank() {
  const v = S.res; if (!v.length) return;
  $('#rank_title').textContent = `Similarity to ${S.target}`;
  const asc = [...v].sort((a, b) => a.score - b.score);
  Plotly.react('rank_bar', [{ type: 'bar', orientation: 'h', x: asc.map(r => r.score), y: asc.map(r => r.site),
    marker: { color: asc.map(r => r.score), colorscale: [[0, SCALE[0]], [.45, SCALE[1]], [.6, SCALE[2]], [1, SCALE[3]]], cmin: 0, cmax: 1 },
    hovertemplate: '%{y}: %{x:.3f}<extra></extra>' }],
    { height: H(500, 420), margin: { l: 0, r: 10, t: 10, b: 30 }, font: FONT, xaxis: { range: [0, 1], title: 'score' }, yaxis: { automargin: true }, paper_bgcolor: 'rgba(0,0,0,0)', plot_bgcolor: 'rgba(0,0,0,0)' }, PL);
  Plotly.react('rank_scatter', [{ type: 'scatter', mode: 'markers+text', x: v.map(r => r.score_moon), y: v.map(r => r.score_mars), text: v.map(r => r.site),
    textposition: 'top center', textfont: { size: 10, color: MUTED }, marker: { size: 12, color: v.map(r => r.score), colorscale: [[0, SCALE[0]], [.45, SCALE[1]], [.6, SCALE[2]], [1, SCALE[3]]], cmin: 0, cmax: 1 },
    hovertemplate: '%{text}<br>Moon %{x:.2f} · Mars %{y:.2f}<extra></extra>' }],
    { height: H(500, 380), margin: { l: 50, r: 10, t: 10, b: 40 }, font: FONT, xaxis: { title: 'Moon similarity' }, yaxis: { title: 'Mars similarity' }, paper_bgcolor: 'rgba(0,0,0,0)', plot_bgcolor: 'rgba(0,0,0,0)' }, PL);
  const cols = ['rank', 'site', 'country', 'type', 'score', 'tier', 'precip_mm', 'temp_range_c', 'albedo', 'wind10m_ms', 'wind10m_max_ms', 'altitude_m', 'slope30_deg', 'rough30_m', 'slope_deg', 'roughness_m', 'score_mars', 'score_moon'];
  $('#rank_table').innerHTML = '<tr>' + cols.map(c => `<th>${c}</th>`).join('') + '</tr>' +
    v.map(r => '<tr>' + cols.map(c => `<td>${isNum(r[c]) ? r[c] : (r[c] ?? '')}</td>`).join('') + '</tr>').join('');
  $('#dl_csv').onclick = () => {
    const csv = [cols.join(','), ...v.map(r => cols.map(c => JSON.stringify(r[c] ?? '')).join(','))].join('\n');
    const a = el('a', { href: URL.createObjectURL(new Blob([csv], { type: 'text/csv' })), download: `altergea_${S.target.toLowerCase()}_ranking.csv` }); a.click();
  };
}

// ---------- similarity explorer ----------
function renderExplorer() {
  const v = S.res; if (!v.length) return;
  const names = v.map(r => r.site);
  if (!S.exSites.length) S.exSites = [names.find(n => n.startsWith('Médano')), ...names.filter(n => !n.startsWith('Médano')).slice(0, 2)].filter(Boolean);
  S.exSites = S.exSites.filter(n => names.includes(n));
  for (const k of KEYS) if (!(k in S.exActive)) S.exActive[k] = S.W[k] > 0;
  $('#ex_intro').innerHTML = `<b>How similar is each site to ${S.target}, variable by variable?</b> Every variable is scored 0–100 % against the
    ${S.target} reference; the overall figure is the weighted mean of the variables you keep on. Weights come from the sidebar; switching a
    variable off here removes it from this comparison only. Pick up to 5 sites.`;
  $('#ex_sites').innerHTML = names.map(n => `<button class="chip ${S.exSites.includes(n) ? 'is-on' : ''}" data-s="${n}">${n}</button>`).join('');
  $('#ex_sites').querySelectorAll('.chip').forEach(c => c.addEventListener('click', () => {
    const n = c.dataset.s; if (S.exSites.includes(n)) S.exSites = S.exSites.filter(x => x !== n); else if (S.exSites.length < 5) S.exSites.push(n); renderExplorer(); }));
  $('#ex_vars').innerHTML = KEYS.map(k => `<label class="check"><input type="checkbox" data-k="${k}" ${S.exActive[k] ? 'checked' : ''}> ${LABELS[k]}</label>`).join('');
  $('#ex_vars').querySelectorAll('input').forEach(i => i.addEventListener('change', () => { S.exActive[i.dataset.k] = i.checked; renderExplorer(); }));
  const Wa = {}; for (const k of KEYS) Wa[k] = S.exActive[k] ? S.W[k] : 0;
  const on = KEYS.filter(k => Wa[k] > 0);
  if (!S.exSites.length || !on.length) { $('#ex_overall').innerHTML = '<p class="hint">Pick at least one site and keep one weighted variable on.</p>'; Plotly.purge('ex_bar'); Plotly.purge('ex_radar'); $('#ex_table').innerHTML = ''; $('#ex_h2h').innerHTML = ''; return; }
  const rows = S.exSites.map(n => v.find(r => r.site === n));
  const overall = rows.map(r => similarity(r.comps, Wa));
  $('#ex_overall').innerHTML = rows.map((r, i) => stat(r.site, isNaN(overall[i]) ? 'n/a' : `${Math.round(overall[i] * 100)} %`, `${r.country} · ${on.length} variables`)).join('');
  Plotly.react('ex_bar', rows.map((r, i) => ({ type: 'bar', name: r.site, x: on.map(k => LABELS[k]), y: on.map(k => isNaN(r.comps[k]) ? 0 : r.comps[k] * 100), marker: { color: BRAND[i % BRAND.length] },
    hovertemplate: '%{x}: %{y:.0f} %<extra>' + r.site + '</extra>' })),
    { barmode: 'group', height: H(360, 320), margin: { l: 40, r: 0, t: 10, b: 60 }, font: FONT, yaxis: { range: [0, 100], title: 'Similarity %' }, legend: { orientation: 'h', y: 1.18 }, paper_bgcolor: 'rgba(0,0,0,0)', plot_bgcolor: 'rgba(0,0,0,0)' }, PL);
  Plotly.react('ex_radar', rows.map((r, i) => { const vals = on.map(k => isNaN(r.comps[k]) ? 0 : r.comps[k] * 100); return { type: 'scatterpolar', name: r.site, r: [...vals, vals[0]], theta: [...on.map(k => LABELS[k]), LABELS[on[0]]], fill: 'toself', line: { color: BRAND[i % BRAND.length] }, fillcolor: BRAND[i % BRAND.length] + '33' }; }),
    { height: H(360, 320), margin: { l: 40, r: 40, t: 20, b: 20 }, font: FONT, showlegend: false, polar: { radialaxis: { range: [0, 100], ticksuffix: ' %' } }, paper_bgcolor: 'rgba(0,0,0,0)' }, PL);
  $('#ex_table').innerHTML = `<tr><th>Variable</th><th>Site</th><th>Earth value</th><th>${S.target} reference</th><th>Similarity %</th><th>Weight</th></tr>` +
    rows.flatMap(r => on.map(k => `<tr><td>${LABELS[k]}</td><td>${r.site}</td><td>${FMT[k](r)}</td><td>${fmtRef(k)}</td><td>${pct(r.comps[k])}</td><td>${Wa[k].toFixed(2)}</td></tr>`)).join('');
  if (rows.length >= 2) {
    const a = rows[0], b = rows[1];
    $('#ex_h2h').innerHTML = `<p class="h">Head to head · ${a.site} vs ${b.site} <span class="hint">(first two selected)</span></p><div class="tbl-wrap"><table class="data"><tr><th>Variable</th><th>${a.site}</th><th>A %</th><th>${b.site}</th><th>B %</th><th>Edge</th></tr>` +
      on.map(k => { const va = a.comps[k], vb = b.comps[k]; const d = (va - vb) * 100;
        return `<tr><td>${LABELS[k]}</td><td>${FMT[k](a)}</td><td>${Math.round(va * 100)}</td><td>${FMT[k](b)}</td><td>${Math.round(vb * 100)}</td><td>${isNaN(d) ? '' : d > 0 ? `${a.site} +${d.toFixed(0)}` : `${b.site} +${(-d).toFixed(0)}`}</td></tr>`; }).join('') +
      `</table></div><p class="hint">Overall for ${S.target}: ${a.site} ${Math.round(overall[0] * 100)} % vs ${b.site} ${Math.round(overall[1] * 100)} %.</p>`;
  } else $('#ex_h2h').innerHTML = '';
}

// ---------- Mars twin ----------
let twinBuilt = false;
function ensureTwin() {
  if (twinBuilt) { renderTwinData(); return; } twinBuilt = true;
  const me = L.map('map_earth', { center: MB, zoom: 14 });
  const sat = L.tileLayer(ESRI_IMG, { attribution: ESRI_ATTR, maxZoom: 19 }).addTo(me);
  const ov = { 'NASA MODIS true colour (GIBS, 250 m)': L.tileLayer(GIBS, { attribution: 'NASA GIBS / MODIS Terra', maxNativeZoom: 9, maxZoom: 19, opacity: .85 }) };
  for (const [label, [svc, layer]] of Object.entries(ING_SERVICES))
    ov[`INGEMMET · ${label}`] = L.tileLayer.wms(ING_WMS(svc), { layers: layer, format: 'image/png', transparent: true, version: '1.1.1', opacity: .6 });
  L.control.layers({ 'Satellite (Esri)': sat }, ov).addTo(me);
  L.circleMarker(MB, { radius: 8, color: NAVY, fillColor: NAVY, fillOpacity: .9 }).bindTooltip('Médano Blanco (barchan, ~16.4 ha)').addTo(me);
  maps.earth = me;
  const mm = L.map('map_mars', { crs: L.CRS.EPSG4326, center: NAMIB, zoom: 13, maxZoom: 18 });
  const bases = {}, overs = {};
  for (const [label, id, ext, mz, show, isBase] of TREK_LAYERS) {
    const t = L.tileLayer(TREK(id, ext), { attribution: 'NASA / JPL-Caltech / USGS / Mars Trek', maxNativeZoom: mz, maxZoom: 18, noWrap: true });
    if (isBase) { bases[label] = t; t.addTo(mm); } else { overs[label] = t; if (show) t.addTo(mm); }
  }
  L.control.layers(bases, overs).addTo(mm);
  L.circleMarker(NAMIB, { radius: 8, color: RED, fillColor: RED, fillOpacity: .9 }).bindTooltip('Namib Dune · Curiosity sol 1192').addTo(mm);
  L.circleMarker(BRADBURY, { radius: 6, color: '#fff', fillColor: '#fff', fillOpacity: .9 }).bindTooltip('Bradbury Landing · Curiosity, 2012').addTo(mm);
  maps.mars = mm;
  renderTwinData();
}
function renderTwinData() {
  const s2 = S.s2, mb = S.res.find(r => r.site.startsWith('Médano'));
  const mig = [['Médano Blanco, slipface 2006–16 · MINAM', 4.0, 'Earth'], ['Médano Blanco, slipface 2016–22 · MINAM', 6.0, 'Earth']];
  if (s2) mig.push([`Médano Blanco, dune body ${s2.first.slice(2, 4)}–${s2.last.slice(2, 4)} · Sentinel-2, ALTERGEA`, s2.speed_m_per_yr, 'Earth']);
  mig.push(['Bagnold dunes · HiRISE, Silvestro 2013', 0.4, 'Mars'], ['Bagnold large ripples, max · HiRISE', 1.7, 'Mars']);
  Plotly.react('mig_bar', ['Earth', 'Mars'].map(w => ({ type: 'bar', orientation: 'h', name: w, x: mig.filter(m => m[2] === w).map(m => m[1]), y: mig.filter(m => m[2] === w).map(m => m[0]),
    marker: { color: w === 'Earth' ? NAVY : RED }, text: mig.filter(m => m[2] === w).map(m => m[1].toFixed(1)), textposition: 'outside', cliponaxis: false, hovertemplate: '%{y}: %{x} m/yr<extra></extra>' })),
    { height: H(320, 340), margin: { l: 0, r: 30, t: 10, b: 40 }, font: FONT, xaxis: { title: 'Migration (m per Earth year)', range: [0, 7.5] }, yaxis: { automargin: true, tickfont: { size: isSmall() ? 10 : 11 }, categoryorder: 'array', categoryarray: mig.map(m => m[0]).reverse() }, legend: { orientation: 'h', y: 1.1 }, paper_bgcolor: 'rgba(0,0,0,0)', plot_bgcolor: 'rgba(0,0,0,0)' }, PL);
  const ev = (k, f) => mb && isNum(mb[k]) ? f(mb[k]) : 'n/a';
  const cmp = [['Dune type', 'Barchan, active; ~16.4 ha', 'Barchans + linear dunes, active'],
    ['Sand composition', "Quartz sand, light-toned: INGEMMET unit Q-eo 'Depósito eólico'", 'Dark basaltic, olivine-bearing (ChemCam/APXS)'],
    ['Surface albedo', ev('albedo', v => `${v} (POWER, 50 km cell)`), 'Low (dark sand)'],
    ['Elevation and relief', mb && isNum(mb.alt30_m) ? `${Math.round(mb.alt30_m)} m; slope ${mb.slope30_deg}°, roughness ${mb.rough30_m} m (Copernicus DEM 30 m)` : ev('altitude_m', v => `${Math.round(v)} m (SRTM 30 m)`), '−4,422 m MOLA datum (rover, sol 1192)'],
    ['Wind 10 m', mb ? `${mb.wind10m_ms} mean / ${mb.wind10m_max_ms} max m/s (POWER)` : 'n/a', 'REMS in situ (not yet in app)'],
    ['Precipitation', ev('precip_mm', v => `${v} mm/yr (POWER)`), 'None'],
    ['Topography source', 'Copernicus DEM GLO-30 (ESA, via Planetary Computer); SRTM 30 m', 'HiRISE DTM 1 m (Gale_DEM_SMG_1m); MOLA 463 m is too coarse'],
    ['Imagery source', 'Sentinel-2 10 m (Planetary Computer); Esri imagery; NASA MODIS (GIBS)', 'CTX mosaic; HiRISE mosaic (Mars Trek)'],
    ['Site management', 'MINAM: vulnerable to intensive tourism (sandboarding)', 'Rover science site, not a base site']];
  $('#cmp_table').innerHTML = '<tr><th>Feature</th><th>Médano Blanco</th><th>Bagnold / Namib Dune</th></tr>' + cmp.map(r => `<tr><td>${r[0]}</td><td>${r[1]}</td><td>${r[2]}</td></tr>`).join('');
  const blk = $('#s2_block');
  if (!s2 || !S.s2rows.length) { blk.innerHTML = '<p class="hint">Sentinel-2 measurement not available in this build.</p>'; return; }
  if (blk.dataset.done) return; blk.dataset.done = '1';
  const rows = S.s2rows;
  blk.innerHTML = `<p class="h">Sentinel-2 time series, ${s2.first} to ${s2.last}: ${s2.n_scenes} cloud-free scenes</p>
    <div class="two"><div><div id="s2_chart"></div>
    <p class="hint">${s2.speed_m_per_yr}${s2.speed_sigma_m_per_yr != null ? ` ± ${s2.speed_sigma_m_per_yr}` : ''} m/yr towards ${s2.bearing_deg}°, scatter about the fit ${s2.fit_rms_m} m, ${s2.n_scenes} scenes. Copernicus Sentinel-2 L2A, 10 m, via Earth Search (AWS). Method: ${s2.method}.</p>
    <div class="note"><b>Reading the two Earth figures.</b> Our Sentinel-2 series tracks the whole dune body and finds it essentially stationary (below 1 m/yr, at the 10 m detection limit). The MINAM figure of 4–6 m/yr describes the slipface edge and the arms, where sandboarding and buggy traffic concentrate, measured on Google Earth imagery whose georeferencing can drift by metres between dates. In analog terms this brings Médano Blanco closer to Bagnold: both fields are active at the ripple and slipface scale while their dune bodies migrate well under 1 m/yr.</div></div>
    <div><label class="lbl">Scene <output id="o_scene">${rows[rows.length - 1].date}</output></label><input type="range" id="scene" min="0" max="${rows.length - 1}" value="${rows.length - 1}">
    <img id="scene_img" src="data/sentinel/${rows[rows.length - 1].date}.png" alt="Sentinel-2 cut-out" style="width:100%;border-radius:4px;border:1px solid var(--rule)">
    <p class="hint">Sentinel-2 true colour, ~2 km across. Red outline: dune outline from the brightness threshold; the displacement is measured by cross-correlating the dune pixels, not from this outline.</p>
    <div class="tbl-wrap" style="max-height:220px;overflow:auto"><table class="data"><tr><th>date</th><th>shift E m</th><th>shift N m</th><th>match</th><th>area ha</th></tr>${rows.map(r => `<tr><td>${r.date}</td><td>${r.shift_east_m}</td><td>${r.shift_north_m}</td><td>${(+r.ncc_peak).toFixed(2)}</td><td>${r.area_ha}</td></tr>`).join('')}</table></div></div></div>`;
  const t0 = new Date(rows[0].date); const yrs = rows.map(r => (new Date(r.date) - t0) / 365.25 / 864e5);
  Plotly.react('s2_chart', [
    { type: 'scatter', mode: 'markers', name: 'Dune body (cross-correlation)', x: rows.map(r => r.date), y: rows.map(r => +r.shift_along_drift_m), marker: { color: NAVY, size: 7 } },
    { type: 'scatter', mode: 'lines', name: `Linear fit: ${s2.speed_m_per_yr} m/yr`, x: rows.map(r => r.date), y: yrs.map(y => y * s2.speed_m_per_yr), line: { color: NAVY, width: 1.5 } }],
    { height: 300, margin: { l: 50, r: 0, t: 10, b: 40 }, font: FONT, yaxis: { title: 'Displacement along drift (m)' }, legend: { orientation: 'h', y: 1.12 }, paper_bgcolor: 'rgba(0,0,0,0)', plot_bgcolor: 'rgba(0,0,0,0)' }, PL);
  $('#scene').addEventListener('input', e => { const r = rows[+e.target.value]; $('#o_scene').textContent = r.date; $('#scene_img').src = `data/sentinel/${r.date}.png`; });
}

// ---------- Peru geology ----------
// INGEMMET's ArcGIS REST sends no CORS header, but supports JSONP (callback=), so the query works from any static host.
let jsonpSeq = 0;
function jsonp(url, timeout = 45000) {
  return new Promise((resolve, reject) => {
    const cb = `__altergea_cb${++jsonpSeq}`; const s = document.createElement('script');
    const done = (fn, v) => { delete window[cb]; s.remove(); clearTimeout(t); fn(v); };
    const t = setTimeout(() => done(reject, new Error('timeout')), timeout);
    window[cb] = js => done(resolve, js);
    s.onerror = () => done(reject, new Error('script error'));
    s.src = `${url}&callback=${cb}`; document.head.appendChild(s);
  });
}
let peruBuilt = false;
const inPiura = r => r.lat >= -6.4 && r.lat <= -3.9 && r.lon >= -81.4 && r.lon <= -79.2;   // Piura region (bounding box)
const inPeru = r => r.lat >= -18.5 && r.lat <= 0.1 && r.lon >= -81.5 && r.lon <= -68.5;
function ensurePeru() {
  const sel = $('#peru_sel'); const peru = S.res.filter(inPeru);
  sel.innerHTML = peru.map(r => `<option ${r.site === S.peru ? 'selected' : ''}>${r.site}</option>`).join('');
  if (!peru.length) { $('#peru_info').innerHTML = '<p class="hint">No analyzed site is inside Peru. Add one from the sidebar.</p>'; return; }
  if (!S.peru || !peru.find(r => r.site === S.peru)) S.peru = peru[0].site;
  if (!peruBuilt) {
    peruBuilt = true;
    const mp = L.map('map_peru', { center: [peru[0].lat, peru[0].lon], zoom: 10 });
    L.tileLayer(ESRI_IMG, { attribution: ESRI_ATTR, maxZoom: 19 }).addTo(mp);
    const ov = {};
    for (const [label, [svc, layer]] of Object.entries(ING_SERVICES))
      ov[`INGEMMET · ${label}`] = L.tileLayer.wms(ING_WMS(svc), { layers: layer, format: 'image/png', transparent: true, version: '1.1.1', opacity: .6 }).addTo(mp);
    L.control.layers({}, ov).addTo(mp);
    maps.peru = mp; maps.peruMarker = L.circleMarker([0, 0], { radius: 9, fillOpacity: .95 }).addTo(mp);
    sel.addEventListener('change', e => { S.peru = e.target.value; renderPeru(); });
  }
  renderPeru();
}
async function renderPeru() {
  const r = S.res.find(x => x.site === S.peru); if (!r) return;
  maps.peru.setView([r.lat, r.lon], 10); maps.peruMarker.setLatLng([r.lat, r.lon]).setStyle({ color: color(r.score), fillColor: color(r.score) }).bindTooltip(r.site);
  const info = $('#peru_info');
  info.innerHTML = `<p class="h">${r.site} · ${S.target} score ${r.score} (${r.tier})</p><p class="spin">Querying INGEMMET (their server takes ~30 s per layer)…</p>`;
  const d = 0.2, tol = 3;
  const results = await Promise.all(Object.entries(ING_SERVICES).map(async ([label, [svc]]) => {
    const q = new URLSearchParams({ geometry: `${r.lon},${r.lat}`, geometryType: 'esriGeometryPoint', sr: 4326, layers: 'all', tolerance: tol,
      mapExtent: `${r.lon - d},${r.lat - d},${r.lon + d},${r.lat + d}`, imageDisplay: '600,600,96', returnGeometry: 'false', f: 'json' });
    try { const js = await jsonp(`${ING_REST(svc)}?${q}`, 60000); return [label, js.error ? null : (js.results || []).slice(0, 6)]; }
    catch (e) { return [label, null]; }
  }));
  if (S.peru !== r.site) return;
  info.innerHTML = `<p class="h">${r.site} · ${S.target} score ${r.score} (${r.tier})</p>` + results.map(([label, res]) => {
    let body;
    if (res === null) body = '<p class="hint">INGEMMET service did not respond right now. Try again later or open GEOCATMIN.</p>';
    else if (!res.length) body = '<p class="hint">No mapped feature found at this point.</p>';
    else body = res.map(x => { const attrs = Object.entries(x.attributes || {}).filter(([k, v]) => v != null && v !== '' && v !== 'Null' && !/shape|objectid|fid|globalid/i.test(k));
      return `<details open class="box"><summary>${x.layerName || 'Layer'}</summary><table class="data">${attrs.map(([k, v]) => `<tr><td>${k}</td><td>${v}</td></tr>`).join('')}</table></details>`; }).join('');
    return `<p class="h">INGEMMET · ${label}</p>${body}`; }).join('');
}

// ---------- methodology ----------
function renderMethod() {
  const W = S.W;
  $('#method_model').innerHTML = `Each variable becomes a 0–1 similarity, combined with a weighted average.<br>
    <b>Aridity:</b> exp(−precipitation / ${S.P.arid} mm). <b>Thermal range:</b> daily range / 25 °C, capped at 1.
    <b>Albedo:</b> Gaussian closeness to the target value (${S.alb[S.target]} for ${S.target}). <b>Slope:</b> mean slope at 30 m (Copernicus DEM via Planetary Computer) with full score up to ${S.P.slope}°, penalised above; the 1 km SRTM slope is used only where the 30 m read is missing (user-added sites).
    <b>Altitude:</b> altitude / 4000 m, a proxy for low atmospheric pressure. <b>Wind (aeolian activity):</b> mean 10 m wind / ${S.P.wind} m/s, capped at 1; weight 0 for the Moon.<br>
    <b>Weights (${S.target}):</b> ${KEYS.map(k => `${LABELS[k]} ${W[k].toFixed(2)}`).join(', ')}.`;
}

// ---------- main update ----------
function update() {
  compute(); renderStats(); renderMap(); renderFocus(); renderMethod();
  const active = document.querySelector('.tab.is-on').dataset.tab;
  if (active === 'rank') renderRank(); if (active === 'explore') renderExplorer();
  if (active === 'twin' && twinBuilt) renderTwinData(); if (active === 'peru') ensurePeru();
}

function parseCsv(text) {
  const lines = text.trim().split(/\r?\n/); const head = lines[0].split(',');
  return lines.slice(1).map(l => { const c = l.split(','); const o = {}; head.forEach((h, i) => o[h] = c[i]); return o; });
}

async function init() {
  buildSidebar(); buildTabs(); buildMap();
  const DATA_V = '?v=20261117';     // bump together with the script tag in index.html when data files change
  try {
    const js = await (await fetch('data/sites.json' + DATA_V, { cache: 'no-cache' })).json();
    S.base = js.sites.map(r => { for (const k in r) if (r[k] === null) r[k] = NaN; return r; });
  } catch (e) { $('#stats').innerHTML = '<p class="err">Could not load data/sites.json.</p>'; return; }
  try { S.s2 = await (await fetch('data/medano_blanco_migration.json' + DATA_V, { cache: 'no-cache' })).json(); S.s2rows = parseCsv(await (await fetch('data/medano_blanco_migration.csv' + DATA_V, { cache: 'no-cache' })).text()); } catch (e) { S.s2 = null; }
  setTarget('Mars', false);
}
init();
