/* Live NASA data sources used by the web app (all public, no keys, queried from the browser):
   - NASA GIBS / Worldview: true-colour layers (MODIS Terra, VIIRS NOAA-21, VIIRS SNPP) with a date control
   - NASA Earthdata CMR: collections and granules that cover a site, with links to Earthdata Search
   - NASA PDS Geosciences Node, Orbital Data Explorer (ODE): HiRISE products over Mars reference sites
     (Mars Exploration Program missions: MSL, MER, Mars 2020) */

// ---------- GIBS / Worldview ----------
const GIBS_LAYERS = [
  [tr('NASA Worldview · MODIS Terra true colour', 'NASA Worldview · MODIS Terra color real'), 'MODIS_Terra_CorrectedReflectance_TrueColor'],
  [tr('NASA Worldview · VIIRS NOAA-21 true colour', 'NASA Worldview · VIIRS NOAA-21 color real'), 'VIIRS_NOAA21_CorrectedReflectance_TrueColor'],
  [tr('NASA Worldview · VIIRS SNPP true colour', 'NASA Worldview · VIIRS SNPP color real'), 'VIIRS_SNPP_CorrectedReflectance_TrueColor']];
const NASA = { layers: [], date: (() => { const d = new Date(Date.now() - 2 * 864e5); return d.toISOString().slice(0, 10); })() };
const gibsUrl = (id, date) => `https://gibs.earthdata.nasa.gov/wmts/epsg3857/best/${id}/default/${date}/GoogleMapsCompatible_Level9/{z}/{y}/{x}.jpg`;
function gibsOverlays() {
  const o = {};
  for (const [label, id] of GIBS_LAYERS) {
    const l = L.tileLayer(gibsUrl(id, NASA.date), { attribution: 'NASA GIBS / Worldview', maxNativeZoom: 9, maxZoom: 19, opacity: .85 });
    l._gibsId = id; NASA.layers.push(l); o[label] = l;
  }
  return o;
}
function setGibsDate(date) {
  if (!/^\d{4}-\d{2}-\d{2}$/.test(date)) return;
  NASA.date = date;
  NASA.layers.forEach(l => l.setUrl(gibsUrl(l._gibsId, date)));
  document.querySelectorAll('.wv_link').forEach(a => { a.href = worldviewUrl(+a.dataset.lat, +a.dataset.lon); });
}
function worldviewUrl(lat, lon, span = 0.6) {
  return `https://worldview.earthdata.nasa.gov/?v=${(lon - span).toFixed(3)},${(lat - span * .6).toFixed(3)},${(lon + span).toFixed(3)},${(lat + span * .6).toFixed(3)}&t=${NASA.date}-T00%3A00%3A00Z`;
}
const earthdataSearchUrl = (lat, lon, q = '') =>
  `https://search.earthdata.nasa.gov/search?${q ? 'q=' + encodeURIComponent(q) + '&' : ''}lat=${lat}&long=${lon}&overlays=bordersRoads%2Ccoastlines%2CplaceLabels&zoom=10.8`;
function initNasaControls() {
  const i = $('#gibs_date'); if (!i) return;
  const today = new Date().toISOString().slice(0, 10);
  i.value = NASA.date; i.max = today; i.min = '2012-05-08';
  i.addEventListener('change', e => setGibsDate(e.target.value));
}

// ---------- Earthdata CMR ----------
const CMR = 'https://cmr.earthdata.nasa.gov/search';
const CMR_SETS = [['MOD09GA', '061', tr('MODIS Terra surface reflectance, daily 500 m', 'MODIS Terra reflectancia superficial, diaria 500 m')],
  ['HLSL30', '2.0', tr('Harmonized Landsat 30 m', 'Harmonized Landsat 30 m')], ['HLSS30', '2.0', 'Harmonized Sentinel-2 30 m']];
async function cmrGet(path) {
  const r = await fetch(`${CMR}/${path}`); if (!r.ok) throw new Error(r.status);
  return { hits: +r.headers.get('cmr-hits') || 0, entries: (await r.json()).feed.entry };
}
async function nasaDataBlock(lat, lon, el) {
  const d = 0.05, bb = `${(lon - d).toFixed(4)},${(lat - d).toFixed(4)},${(lon + d).toFixed(4)},${(lat + d).toFixed(4)}`;
  const links = `<a href="${earthdataSearchUrl(lat, lon)}" target="_blank" rel="noopener">${tr('Open in Earthdata Search', 'Abrir en Earthdata Search')}</a> ·
    <a class="wv_link" data-lat="${lat}" data-lon="${lon}" href="${worldviewUrl(lat, lon)}" target="_blank" rel="noopener">${tr('Open in Worldview', 'Abrir en Worldview')}</a>`;
  el.innerHTML = `<p class="hint">${tr('Querying NASA Earthdata (CMR)…', 'Consultando NASA Earthdata (CMR)…')}</p>`;
  try {
    const [col, ...gr] = await Promise.all([cmrGet(`collections.json?bounding_box=${bb}&page_size=1`),
      ...CMR_SETS.map(([sn, v]) => cmrGet(`granules.json?short_name=${sn}&version=${v}&bounding_box=${bb}&page_size=1&sort_key=-start_date`))]);
    const rows = CMR_SETS.map(([sn, v, label], i) => `<tr><td><b>${sn}</b> ${label}</td><td>${gr[i].hits.toLocaleString(numLocale())}</td>
      <td>${gr[i].entries[0] ? gr[i].entries[0].time_start.slice(0, 10) : tr('n/a', 'n/d')}</td></tr>`).join('');
    el.innerHTML = `<p class="h">${tr('NASA Earthdata over this site', 'NASA Earthdata sobre este sitio')} <span class="hint">${tr('(live, CMR)', '(en vivo, CMR)')}</span></p>
      <p class="hint">${col.hits.toLocaleString(numLocale())} ${tr('Earthdata collections intersect a ~11 km box around the site.', 'colecciones de Earthdata intersectan un recuadro de ~11 km alrededor del sitio.')} ${links}</p>
      <div class="tbl-wrap"><table class="data"><tr><th>${tr('Dataset', 'Conjunto de datos')}</th><th>${tr('Granules', 'Gránulos')}</th><th>${tr('Latest', 'Último')}</th></tr>${rows}</table></div>`;
  } catch (e) { el.innerHTML = `<p class="hint">${tr('Earthdata CMR did not answer.', 'Earthdata CMR no respondió.')} ${links}</p>`; }
}

// ---------- PDS Geosciences Node · Orbital Data Explorer ----------
const ODE = 'https://oderest.rsl.wustl.edu/live2/';
// Mars Exploration Program sites (lon in degrees east)
const MEP_SITES = [
  { name: 'Gale · Namib Dune (MSL Curiosity)', lat: -4.680, lon: 137.367 },
  { name: 'Meridiani Planum · Eagle crater (MER Opportunity)', lat: -1.946, lon: 354.473 },
  { name: 'Gusev · Columbia Memorial Station (MER Spirit)', lat: -14.572, lon: 175.479 },
  { name: 'Jezero · Octavia E. Butler landing (Mars 2020)', lat: 18.445, lon: 77.451 }];
const odeQuery = (iid, pt, s, h, extra) => `${ODE}?query=product&target=mars&ihid=MRO&iid=${iid}&pt=${pt}&loc=o&minlat=${s.lat - h}&maxlat=${s.lat + h}` +
  `&westernlon=${s.lon - h}&easternlon=${s.lon + h}&output=JSON${extra}`;
async function odeSite(s, h = 0.25) {
  const [dtm, cnt, rdr] = await Promise.all([
    fetch(odeQuery('HIRISE', 'DTM', s, h, '&results=mp&limit=3')).then(r => r.json()),
    fetch(odeQuery('HIRISE', 'DTM', s, h, '&results=c')).then(r => r.json()),
    fetch(odeQuery('HIRISE', 'RDRV11', s, h, '&results=c')).then(r => r.json())]);
  const list = dtm.ODEResults.Products ? [].concat(dtm.ODEResults.Products.Product) : [];
  return { dtm: +cnt.ODEResults.Count || 0, rdr: +rdr.ODEResults.Count || 0, list };
}
async function odeBlock(el) {
  el.innerHTML = `<p class="hint">${tr('Querying the PDS Orbital Data Explorer…', 'Consultando el PDS Orbital Data Explorer…')}</p>`;
  try {
    const res = await Promise.all(MEP_SITES.map(s => odeSite(s)));
    el.innerHTML = `<table class="data"><tr><th>${tr('Mars Exploration Program site', 'Sitio del Programa de Exploración de Marte')}</th><th>${tr('HiRISE DTMs', 'DTM HiRISE')}</th><th>${tr('HiRISE images', 'Imágenes HiRISE')}</th><th>${tr('Nearest DTMs (PDS)', 'DTM más cercanos (PDS)')}</th></tr>` +
      MEP_SITES.map((s, i) => `<tr><td>${s.name}<br><span class="hint">${s.lat}°, ${s.lon}°E</span></td><td>${res[i].dtm}</td><td>${res[i].rdr}</td>
        <td>${res[i].list.map(p => `<a href="${p.FilesURL}" target="_blank" rel="noopener">${(p.LabelFileName || '').replace(/\.img$/i, '').toUpperCase()}</a>`).join('<br>') || tr('none within ±0.25°', 'ninguno dentro de ±0.25°')}</td></tr>`).join('') +
      `</table><p class="hint">${tr(`Live from the PDS Geosciences Node (ODE REST), counts within ±0.25° of each site. A HiRISE DTM is what allows a Mars slope and
      roughness at the same ~30 m scale as the Earth side, so sites with DTMs are the ones the model can compare like for like.`, `En vivo desde el PDS Geosciences Node (ODE REST), conteos a ±0.25° de cada sitio. Un DTM HiRISE permite obtener pendiente y rugosidad de Marte a la misma escala de ~30 m que en la Tierra, así que los sitios con DTM son los que el modelo puede comparar en igualdad de condiciones.`)}</p>`;
  } catch (e) { el.innerHTML = `<p class="hint">${tr('The PDS Orbital Data Explorer did not answer. Try again later.', 'El PDS Orbital Data Explorer no respondió. Inténtalo más tarde.')}</p>`; }
}
function addMepMarkers(map) {
  MEP_SITES.forEach(s => {
    const lon = s.lon > 180 ? s.lon - 360 : s.lon;
    L.circleMarker([s.lat, lon], { radius: 5, color: '#fff', weight: 2, fillColor: RED, fillOpacity: .9 }).bindTooltip(s.name).addTo(map);
  });
}
