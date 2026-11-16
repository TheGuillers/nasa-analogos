/* ALTERGEA · language switch (English is the default, Spanish on demand), starfield and shared Plotly theme.
   Static text carries data-i="key" and English in the HTML; Spanish lives in ES below.
   Text built by app.js goes through tr(english, spanish). */
'use strict';

let LANG = 'en';
try {
  const q = new URLSearchParams(location.search).get('lang');
  LANG = (q === 'es' || q === 'en') ? q : (localStorage.getItem('altergea_lang') || 'en');
} catch (e) { LANG = 'en'; }
if (LANG !== 'es') LANG = 'en';

const tr = (en, es) => (LANG === 'es' && es != null) ? es : en;
const numLocale = () => LANG === 'es' ? 'es-PE' : 'en';

const ES = {
  // ---- hero, nav ----
  n_map: 'Mapa de misión', n_twin: 'Gemelo de Marte', n_method: 'Metodología',
  h_eyebrow: 'NASA Space Apps Challenge 2026 · Piura, Perú',
  h_title: 'Análogos terrestres de la <em>Luna</em> y de <em class="mars">Marte</em>',
  h_lead: 'Clasificamos lugares de la Tierra según cuánto se parecen a las bases lunares permanentes y a los sitios de exploración de Marte, con datos abiertos de la NASA, y proponemos un campo de pruebas insignia a 50 km de Piura: las dunas de Médano Blanco, gemelas de las dunas Bagnold de Curiosity.',
  h_cta1: 'Explorar el mapa de misión', h_cta2: 'Conocer al gemelo de Marte',
  k1: 'sitios evaluados', k2: 'en el Perú', k3: 'serie Sentinel-2', k4: 'fuentes de datos NASA',
  t_m2020: 'Cámaras de Mars 2020',
  m01: "Cámara",
  m02: "N.º",
  m03: "Ubicación",
  m04: "Resolución (px)",
  m05: "Campo de visión",
  m06: "Escala",
  m07: "Uso principal",
  m08: "Par estéreo en el mástil",
  m09: "Navegación y panoramas de 360° del sitio",
  m10: "Parte frontal del rover",
  m11: "Evitar peligros: terreno justo frente a las ruedas",
  m12: "Parte trasera del rover",
  m13: "Evitar peligros detrás del rover",
  m14: "Par estéreo con zoom en el mástil",
  m15: "Imágenes en color y multiespectrales (442–1022 nm), contexto 3D y geología a distancia",
  m16: "En el mástil",
  m17: "Acercamientos en escala de grises de objetivos y puntos láser",
  m18: "Dentro del cuerpo del rover",
  m19: "Inspecciona los tubos de muestra antes de sellarlos",
  m20: "Torreta del brazo robótico",
  m21: "Acercamientos tipo lupa de la textura y los granos de la roca",
  m22: "Torreta del brazo robótico",
  m23: "Contexto en escala de grises para el espectrómetro",
  m24: "Torreta del brazo robótico",
  m25: "Imagen de contexto para el mapeo por fluorescencia de rayos X",
  m26: "Cubierta del rover, mirando hacia arriba",
  m27: "Cielo, nubes y polvo para vigilar el clima",
  m28: "Cubierta de entrada, etapa de descenso y rover",
  m29: "Video de entrada, descenso y aterrizaje; dos siguen fotografiando la superficie",
  m30: "Esquina frontal izquierda del rover",
  m31: "Navegación relativa al terreno durante el aterrizaje (escala de grises)",
  m32: "Mirando hacia abajo desde Ingenuity",
  m33: "Posición y actitud del helicóptero (escala de grises)",
  m34: "Mirando de lado en Ingenuity",
  m35: "Fotos aéreas en color del terreno",
  m36: "<b>Mars 2020 · cámaras de Perseverance.</b> Fuente: <i>Mars 2020 Camera Data Products SIS</i> (JPL D-99960, v3.7, julio de 2025), el documento de referencia del PDS Geosciences Node de la NASA para cada imagen que devuelven el rover y el helicóptero Ingenuity. 25 cámaras en total; las cifras salen directamente de sus tablas de instrumentos.",
  m37: "La escala angular se convierte en escala sobre el terreno multiplicándola por la distancia: 0.33 mrad/px en una imagen Navcam equivale a unos 3.3 cm por píxel a 100 m. El zoom estrecho de Mastcam-Z llega a unos 0.13 mm/px a 2 m y 6.7 mm/px a 100 m.",
  m38: "Por qué importa para los sitios análogos",
  m39: "Comparar un sitio de la Tierra con Marte solo funciona a escala equivalente. Conocer el campo de visión y los píxeles por metro de cada cámara indica qué fotos de la Tierra (dron, terreno, recortes Sentinel-2) son comparables con una imagen de Perseverance.",
  m40: "Productos EDR y RDR",
  m41: "EDR (Experiment Data Record) es la imagen cruda tal como se recibe; RDR (Reduced Data Record) es calibrada o derivada: color, anaglifos estéreo, mapas de disparidad y distancia, mallas y mosaicos.",
  m42: "Cómo leer un nombre de archivo",
  m43: "Las dos primeras letras son el instrumento, la siguiente es una marca de color (E Bayer crudo, M monocromo), luego vienen las marcas de tiempo, el sitio y el tramo de conducción del rover, y el tipo de producto.",
  m44: "Códigos de instrumento en los nombres de archivo",
  m45: "Lee la especificación completa: <a href=\"https://pds-geosciences.wustl.edu/m2020/urn-nasa-pds-mars2020_mission/document_camera/Mars2020_Camera_SIS.pdf\" target=\"_blank\" rel=\"noopener\">Mars2020_Camera_SIS.pdf</a> (PDS Geosciences Node, unos 18 MB).",
  pl_earth: 'Tierra', pl_mars: 'Marte', pl_moon: 'Luna',
  p1t: 'Puntuar', p1: '14 sitios comparados con las condiciones de Marte y la Luna: aridez, rango térmico, albedo, pendiente, altitud y viento, con pesos ajustables.',
  p2t: 'Emparejar', p2: 'Médano Blanco (Sechura) frente a las dunas Bagnold del cráter Gale, lado a lado en imágenes Sentinel-2, Esri, CTX y HiRISE.',
  p3t: 'Medir', p3: 'Nuestra propia medición de la migración de la duna con ocho años de Sentinel-2, comparada con las cifras del MINAM y con HiRISE en Marte.',
  // ---- sidebar ----
  t001: 'Control de misión', t002: 'Controles', t003: 'Objetivo de la misión', t004: 'Marte', t005: 'Luna',
  t006: 'Mostrar solo Piura', t007: 'Fecha de imágenes NASA Worldview', t008: 'Parámetros del modelo',
  t009: 'Límite operativo de pendiente', t010: '°', t011: 'Escala de aridez', t012: 'mm/año',
  t013: 'Viento de transporte de arena a 10 m', t014: 'm/s', t015: 'Albedo objetivo',
  t016: 'Restablecer valores', t017: 'Analiza tu propio sitio', t018: 'Nombre', t019: 'Latitud', t020: 'Longitud',
  t021: 'Obtener datos NASA y agregar', t022: 'Borrar sitios propios',
  t023: 'Datos: NASA POWER · elevación SRTM/ASTER · NASA Mars Trek (CTX, HiRISE, MOLA) · NASA GIBS (MODIS) · Copernicus Sentinel-2 · INGEMMET GEOCATMIN · MINAM. Los umbrales y pesos son supuestos documentados (ver Metodología).',
  // ---- tabs and panels ----
  t027: 'Mapa de misión', t028: 'Ranking', t029: 'Explorador de similitud',
  t030: 'Gemelo de Marte: Médano Blanco ↔ Bagnold', t031: 'Geología del Perú (INGEMMET)', t032: 'Metodología',
  t033: 'Mostrar los N mejores sitios', t034: 'Enfocar un sitio (o haz clic en su marcador)',
  t036: 'Matriz de doble objetivo: ¿qué sitios sirven para ambos mundos?', t037: 'Todas las variables', t038: 'Descargar resultados (CSV)',
  t039: '<b>Análogo propuesto: Médano Blanco (Sechura, Piura) ↔ dunas Bagnold (cráter Gale, Marte).</b> Ambos son campos de dunas barjanes <i>activos</i> moldeados por un viento constante. Bagnold fue el primer campo de dunas activo estudiado in situ en otro planeta (Curiosity, 2015–2017).',
  t040: 'Qué hace fuerte la analogía',
  t041: 'Mismo relieve y mismo proceso: barjanes y dunas lineales activos formados por un régimen de viento persistente, arena suelta que atrapa las ruedas, caras de avalancha y ondulaciones métricas. La migración está medida en ambos cuerpos (Sentinel-2, MINAM; HiRISE).',
  t042: 'Dónde falla',
  t043: 'Composición (cuarzo frente a basalto y olivino), atmósfera (1 bar frente a 6 mbar: la arena en Marte se mueve rara vez), gravedad y la ausencia de vegetación en Marte. Médano Blanco es un sitio turístico protegido con restricciones de uso.',
  t044: 'Cómo ayuda a la exploración',
  t045: 'Un campo para movilidad de rovers y simulacros de rescate en trampas de arena (el modo de falla de Spirit), planificación de rutas entre dunas, métodos de detección de cambios en polvo y formas del terreno, y calibración de mediciones orbitales con verdad de campo, a 50 km de Piura.',
  t046: 'Tierra · Médano Blanco · −5.554, −80.757 · imágenes Esri, NASA GIBS, INGEMMET',
  t047: 'Marte · dunas Bagnold, Gale · duna Namib −4.680, 137.367 · teselas NASA Mars Trek',
  t048: 'Activa o desactiva capas (arriba a la derecha): mosaico CTX de Gale, mosaico HiRISE del sitio recorrido por Curiosity, DEM HiRISE de 1 m. Acércate a la franja oscura al suroeste del marcador para ver las dunas.',
  t049: 'Migración de dunas: Tierra frente a Marte (medida, no modelada)',
  t050: 'Tierra: MINAM / Expediciones al Desierto (2022), Google Earth 2006–2022 y la medición propia de ALTERGEA con Sentinel-2. Marte: Silvestro et al. (2013, HiRISE) según el resumen de Bridges et al. (2018); rango de ondulaciones de Baker et al. (2018).',
  t051: 'NASA Earthdata sobre Médano Blanco',
  t052: 'Sitios del Programa de Exploración de Marte en el archivo PDS',
  t053: '<b>Planteamiento honesto.</b> La analogía es morfológica y de procesos (barjanes, viento constante, arena suelta), no mineralógica: la arena de Bagnold es basáltica y rica en olivino, la de Médano Blanco es cuarzo (unidad INGEMMET Q-eo). Gale es un sitio de ciencia de rover, así que la propuesta es un <i>campo de entrenamiento para movilidad y operaciones sobre arena que cualquier base en Marte enfrentará</i>. Compara pendiente y rugosidad a resolución equivalente (DTM HiRISE remuestreado a 30 m frente a Copernicus 30 m), nunca MOLA 463 m frente a SRTM 30 m.',
  t054: '<b>Contexto geológico del INGEMMET (Instituto Geológico, Minero y Metalúrgico, GEOCATMIN)</b> · complementa el puntaje basado en NASA con geología y geomorfología a 1:100 000.',
  t055: 'Sitio peruano', t056: 'Abrir el visor GEOCATMIN',
  t057: 'Qué hace ALTERGEA',
  t058: 'Clasifica lugares de la Tierra según cuánto se parece su entorno a las condiciones esperadas en bases permanentes de la Luna y Marte, para ayudar a elegir campos de entrenamiento en la Tierra. El candidato insignia es el <b>campo de dunas Médano Blanco (Sechura, Piura)</b> como análogo de las <b>dunas Bagnold (cráter Gale)</b>.',
  t059: 'Datos utilizados',
  t060: '<b>NASA POWER</b>: precipitación (<code>PRECTOTCORR</code>), rango térmico diario (<code>T2M_RANGE</code>), albedo superficial (<code>ALLSKY_SRF_ALB</code>) y viento a 10 m, medio y máximo (<code>WS10M</code>, <code>WS10M_MAX</code>), medias climatológicas. Precalculado para los 14 sitios base; consultado en vivo para los sitios que agregues.',
  t061: '<b>Copernicus DEM GLO-30</b> (ESA) vía <b>Microsoft Planetary Computer</b> (API STAC con firma pública, sin cuenta): altitud, pendiente media a 30 m y rugosidad sin tendencia en una ventana de ~3 km. Es la pendiente que usa el modelo, a una resolución que el lado de Marte (DTM HiRISE remuestreado a 30 m) puede igualar. Precalculado para los sitios base.',
  t062: 'Elevación <b>SRTM</b> (NASA/NGA) y <b>ASTER GDEM</b> (NASA/METI) como respaldo en sitios polares, vía OpenTopoData: altitud y pendiente regional en una ventana de ~4 km (malla de 5×5, ~1 km de separación); se usa para los sitios que agregues aquí.',
  t063: 'Teselas WMTS de <b>NASA Mars Trek</b>: Viking MDIM 2.1, relieve sombreado de color MOLA (463 m), mosaico CTX de Gale (MRO), mosaico HiRISE del sitio recorrido por Curiosity, DEM HiRISE de 1 m de Gale.',
  t064: '<b>NASA GIBS / Worldview</b>: teselas de color real de MODIS Terra, VIIRS NOAA-21 y VIIRS SNPP como capas de la Tierra, con control de fecha en el panel lateral. <a href="https://worldview.earthdata.nasa.gov/index.html?v=-504.22662231419474,-190.8513647590744,359.77337768580526,219.7736352409256&amp;t=2026-09-07-T01%3A58%3A13Z" target="_blank" rel="noopener">Abrir NASA Worldview</a>.',
  t065: '<b>NASA Earthdata Search</b>: catálogo de conjuntos de datos de observación de la Tierra de la NASA. La API CMR se consulta en vivo para las colecciones y gránulos (MODIS, Harmonized Landsat/Sentinel-2) que cubren cada sitio. <a href="https://search.earthdata.nasa.gov/search?q=sechura&amp;lat=-5.940280099950111&amp;long=-80.54643451544943&amp;overlays=bordersRoads%2Ccoastlines%2CplaceLabels&amp;zoom=10.81509069402037" target="_blank" rel="noopener">Abrir la búsqueda de Sechura</a>.',
  t066: '<b>NASA PDS Geosciences Node, Programa de Exploración de Marte</b> (MSL Curiosity, MER Spirit y Opportunity, Mars 2020): el Orbital Data Explorer se consulta en vivo para DTM e imágenes HiRISE alrededor de cada sitio de rover (pestaña Gemelo de Marte). <a href="https://pds-geosciences.wustl.edu/missions/mep/index.htm" target="_blank" rel="noopener">Abrir el portal</a>.',
  t067: '<b>Copernicus Sentinel-2 L2A</b> vía Planetary Computer (Earth Search en AWS como catálogo de respaldo): escenas sin nubes 2017–2026 para medir la migración de la duna por correlación cruzada enmascarada (ver la pestaña Gemelo de Marte).',
  t068: '<b>INGEMMET GEOCATMIN</b>: geología y geomorfología integradas a 1:100 000, como capas WMS y consultas puntuales.',
  t069: '<b>MINAM / SINIA</b> (2022): diagnóstico de Médano Blanco: tipo de duna, área, migración 2006–2022, gestión.',
  t070: 'Modelo de similitud', t071: 'Limitaciones',
  t072: 'Las celdas de NASA POWER miden ~50 km: los valores describen el clima regional, no un punto exacto.',
  t073: 'La pendiente es un promedio regional con separación de ~1 km, no el terreno a escala métrica. Las comparaciones de pendiente o rugosidad Tierra–Marte deben usar resolución equivalente.',
  t074: 'La analogía Médano Blanco ↔ Bagnold es morfológica y de procesos, no mineralógica.',
  t075: 'Los umbrales y pesos son supuestos documentados. Siguiente paso: calibrar con sitios de referencia de Marte (MOLA, MEDA/REMS) y de la Luna (LOLA, Diviner), y añadir la litología del INGEMMET al puntaje.',
  t076: 'Uso de IA',
  t077: 'Claude (Anthropic) se usó como asistente de programación para escribir y depurar el código. La idea, la selección de sitios, el diseño del modelo y la interpretación fueron del equipo.',
  t078: 'Referencias',
  t091: 'Mapas: Leaflet; imágenes: Esri, Maxar, Earthstar Geographics; colaboradores de OpenStreetMap; gráficos: Plotly.',
  t079: 'NASA POWER Project, <a href="https://power.larc.nasa.gov">power.larc.nasa.gov</a> · NASA Mars Trek, <a href="https://trek.nasa.gov/mars">trek.nasa.gov/mars</a> · NASA GIBS, <a href="https://gibs.earthdata.nasa.gov">gibs.earthdata.nasa.gov</a>'
};
// entries whose Spanish equals the English markup (links, citations, names) simply stay as written in the HTML

function applyStatic() {
  document.documentElement.lang = LANG;
  document.querySelectorAll('[data-i]').forEach(el => {
    if (el.dataset.en === undefined) el.dataset.en = el.innerHTML;
    const k = el.dataset.i;
    el.innerHTML = (LANG === 'es' && ES[k] != null) ? ES[k] : el.dataset.en;
  });
  document.querySelectorAll('.lang button').forEach(b => { const on = b.dataset.lang === LANG; b.classList.toggle('is-on', on); b.setAttribute('aria-pressed', on); });
  document.title = tr('ALTERGEA · Earth analogues for the Moon and Mars', 'ALTERGEA · Análogos terrestres de la Luna y Marte');
  const md = document.querySelector('meta[name=description]');
  if (md) md.content = tr('Earth analog site intelligence for permanent Moon and Mars bases. NASA Space Apps 2026, Piura.',
    'Inteligencia de sitios análogos en la Tierra para bases permanentes en la Luna y Marte. NASA Space Apps 2026, Piura.');
  const tg = document.getElementById('side_toggle'); if (tg) tg.textContent = tr('Controls', 'Controles');
}
function setLang(l) {
  const next = l === 'es' ? 'es' : 'en'; if (next === LANG) return;
  try { localStorage.setItem('altergea_lang', next); sessionStorage.setItem('altergea_tab', window.__tab || 'map'); } catch (e) { /* private mode */ }
  const u = new URL(location.href); u.searchParams.delete('lang'); location.href = u.toString();   // rebuild maps, charts and tables in the new language
}

// ---------- Plotly: one dark theme for every chart ----------
(function themePlotly() {
  if (typeof Plotly === 'undefined') return;
  const grid = 'rgba(160,180,230,.14)', line = 'rgba(160,180,230,.28)';
  const ax = a => ({ gridcolor: grid, zerolinecolor: line, linecolor: line, tickfont: { color: '#aab6d6' }, ...a });
  const wrap = fn => (id, data, layout, cfg) => {
    const l = { ...(layout || {}) };
    l.xaxis = ax(l.xaxis); l.yaxis = ax(l.yaxis);
    if (l.polar) l.polar = { bgcolor: 'rgba(0,0,0,0)', ...l.polar, radialaxis: ax(l.polar.radialaxis), angularaxis: ax({ ...(l.polar.angularaxis || {}), tickfont: { color: '#dfe6f8' } }) };
    l.legend = { font: { color: '#dfe6f8' }, ...(l.legend || {}) };
    return fn.call(Plotly, id, data, l, cfg);
  };
  Plotly.react = wrap(Plotly.react);
})();

// ---------- starfield ----------
function drawStars() {
  const c = document.getElementById('stars'); if (!c) return;
  const w = c.width = c.offsetWidth, h = c.height = c.offsetHeight; const g = c.getContext('2d');
  g.clearRect(0, 0, w, h);
  let seed = 7; const rnd = () => (seed = (seed * 16807) % 2147483647) / 2147483647;
  const n = Math.round(w * h / 5200);
  for (let i = 0; i < n; i++) {
    const x = rnd() * w, y = rnd() * h, r = rnd() ** 3 * 1.5 + .25, a = .25 + rnd() * .75;
    g.fillStyle = rnd() > .85 ? `rgba(255,190,150,${a})` : `rgba(200,220,255,${a})`;
    g.beginPath(); g.arc(x, y, r, 0, 7); g.fill();
  }
}

document.addEventListener('DOMContentLoaded', () => {
  applyStatic(); drawStars();
  let rt; window.addEventListener('resize', () => { clearTimeout(rt); rt = setTimeout(drawStars, 200); });
  document.querySelectorAll('.lang button').forEach(b => b.addEventListener('click', () => setLang(b.dataset.lang)));
  document.querySelectorAll('[data-go]').forEach(b => b.addEventListener('click', e => {
    e.preventDefault(); if (typeof showTab === 'function') showTab(b.dataset.go);
    document.getElementById('app').scrollIntoView({ behavior: 'smooth', block: 'start' });
  }));
});
