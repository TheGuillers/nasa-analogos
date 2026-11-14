import io
import os
import json
import time
from concurrent.futures import ThreadPoolExecutor
import numpy as np
from PIL import Image
from scipy import ndimage
import pandas as pd
import requests
import urllib3
import folium
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from streamlit_folium import st_folium

from altergea_data import BASE_SITES, get_climate, get_terrain

# geocatmin.ingemmet.gob.pe serves an incomplete certificate chain: Python cannot verify it (curl/browsers can).
# Only INGEMMET requests use verify=False; NASA services are verified normally.
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
UA = {"User-Agent": "Mozilla/5.0 (ALTERGEA analog-site tool)"}

LOGO = next((f for f in ("logo.jpg", "logo.jpeg", "logo.png") if os.path.exists(f)), None)
st.set_page_config(page_title="ALTERGEA · Analog Site Intelligence", page_icon=LOGO or "◆", layout="wide")

# Palette: navy carries text and primary data, sky is the interactive accent, red is reserved for Mars.
# Score ramp is single-hue (navy → light) so colour reads as "how strong", never as a rainbow.
NAVY, SKY, RED = "#0d1b5e", "#1fa2e8", "#c8102e"
INK, MUTED, RULE = "#1b2340", "#5f6b85", "#d9deea"
SCALE = ["#d6dce8", "#8fbfe3", "#2f7fc1", NAVY]          # Weak · Moderate · Strong · Prime
BRAND = [NAVY, "#2f7fc1", "#8fbfe3", RED, "#8a93ad"]

st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600&display=swap');
html, body, p, li, h1, h2, h3, label, .stMarkdown, .stDataFrame, .stTable, input, select, textarea,
div[data-testid="stMetricValue"], div[data-testid="stMetricLabel"], button[data-baseweb="tab"] p,
.stButton button p, .stDownloadButton button p, div[data-baseweb="select"] div {{
  font-family: "IBM Plex Sans", "Segoe UI", system-ui, sans-serif;
  font-variant-numeric: tabular-nums;
}}
span[data-testid="stIconMaterial"], .material-symbols-rounded, [class*="material-symbols"] {{
  font-family: "Material Symbols Rounded" !important;
}}
.mast p, p.meta {{ margin:0; }}
::selection {{ background:{SKY}33; color:{INK}; }}
.block-container {{ padding-top:3.4rem; max-width:1500px; }}
header[data-testid="stHeader"] {{ background:rgba(255,255,255,.85); }}
h1, h2, h3 {{ color:{INK}; letter-spacing:-0.01em; }}
.stMarkdown h3 {{ font-size:1.05rem; font-weight:600; margin-top:1.6rem; }}
p, li {{ color:{INK}; }}
.mast {{ display:flex; align-items:baseline; gap:14px; flex-wrap:wrap; }}
.mast .wordmark {{ font-size:1.5rem; font-weight:600; letter-spacing:.16em; color:{NAVY}; margin:0; }}
.mast .desc {{ font-size:.95rem; color:{MUTED}; margin:0; }}
.meta {{ font-size:.8rem; color:{MUTED}; margin:4px 0 0; letter-spacing:.01em; }}
.meta b {{ color:{INK}; font-weight:500; }}
.rule {{ height:1px; background:{RULE}; margin:12px 0 18px; }}
.stat {{ padding:2px 0 6px; border-right:1px solid {RULE}; margin-right:18px; }}
.stat:last-child {{ border-right:0; }}
.stat .l {{ font-size:.72rem; color:{MUTED}; letter-spacing:.04em; text-transform:uppercase; font-weight:500; }}
.stat .v {{ font-size:1.3rem; font-weight:600; color:{INK}; line-height:1.25; margin-top:2px; word-break:normal; }}
.stat .s {{ font-size:.8rem; color:{MUTED}; }}
.legend span {{ display:inline-block; margin-right:18px; font-size:.82rem; color:{MUTED}; }}
.dot {{ display:inline-block; width:10px; height:10px; border-radius:50%; margin-right:6px; vertical-align:-1px; }}
.note {{ border:1px solid {RULE}; border-radius:6px; padding:12px 16px; font-size:.9rem; color:{INK};
         background:#fff; margin:6px 0 10px; }}
.note b {{ font-weight:600; }}
section[data-testid="stSidebar"] {{ border-right:1px solid {RULE}; }}
section[data-testid="stSidebar"] h3 {{ font-size:.78rem; letter-spacing:.1em; text-transform:uppercase;
         color:{MUTED}; font-weight:600; }}
div[data-testid="stMetricLabel"] {{ color:{MUTED}; font-size:.78rem; }}
div[data-testid="stMetricValue"] {{ font-size:1.35rem; font-weight:600; color:{INK}; }}
button[data-baseweb="tab"] {{ font-weight:500; font-size:.92rem; }}
.stCaption, [data-testid="stCaptionContainer"] {{ color:{MUTED}; }}
a {{ color:#1f5fa8; text-underline-offset:3px; }}
</style>
""", unsafe_allow_html=True)

# ------------------------------------------------------------
# 1. SITES
# ------------------------------------------------------------
# Médano Blanco: barchan dune, Comunidad Campesina San Martín de Sechura. Position from the MINAM diagnostic
# (UTM 17M 526906 E / 9386090 S -> -5.554, -80.757), consistent with OpenStreetMap. Site list and NASA data
# access live in altergea_data.py, shared with tools/export_sites.py (static web build).
MB_LAT, MB_LON = BASE_SITES[0][3], BASE_SITES[0][4]

LABELS = {"aridity": "Aridity", "thermal": "Thermal range", "albedo": "Albedo match",
          "slope": "Slope", "altitude": "Altitude", "wind": "Wind (aeolian)"}
DEFAULT_W = {
    "Mars": {"aridity": 0.25, "thermal": 0.20, "albedo": 0.15, "slope": 0.15, "altitude": 0.10, "wind": 0.15},
    "Moon": {"aridity": 0.15, "thermal": 0.25, "albedo": 0.25, "slope": 0.20, "altitude": 0.15, "wind": 0.00},
}
ALBEDO = {"Mars": 0.25, "Moon": 0.12}

# Mars reference: Bagnold Dunes campaign, Gale crater (Curiosity). Namib Dune position = rover end-of-drive
# location on sol 1192 (Bridges et al. 2018, JGR Planets, Table 2). Landing site = Bradbury Landing.
NAMIB = (-4.67959, 137.36717)
BRADBURY = (-4.5895, 137.4417)
TREK = "https://trek.nasa.gov/tiles/Mars/EQ/{layer}/1.0.0/default/default028mm/{{z}}/{{y}}/{{x}}.{ext}"
TREK_LAYERS = [  # (label, product id, extension, max native zoom, shown by default)
    ("Viking MDIM 2.1 colour mosaic · 232 m (global)", "Mars_Viking_MDIM21_ClrMosaic_global_232m", "jpg", 8, True),
    ("MOLA colour hillshade · 463 m (global)", "Mars_MGS_MOLA_ClrShade_merge_global_463m", "jpg", 7, False),
    ("MRO CTX · Gale crater mosaic", "Gale_CTX_BlockAdj_dd", "png", 14, True),
    ("MRO HiRISE · Curiosity roving site mosaic", "curiosity_hirise_mosaic", "png", 18, True),
    ("MRO HiRISE · Gale DEM 1 m (hillshade)", "Gale_DEM_SMG_1m", "png", 16, False),
]
GIBS = ("https://gibs.earthdata.nasa.gov/wmts/epsg3857/best/MODIS_Terra_CorrectedReflectance_TrueColor/"
        "default/2025-08-15/GoogleMapsCompatible_Level9/{z}/{y}/{x}.jpg")
ESRI_IMG = "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"
ESRI_ATTR = "Esri, Maxar, Earthstar Geographics"


# ------------------------------------------------------------
# 2. NASA DATA
# ------------------------------------------------------------
@st.cache_data(ttl=3600, show_spinner=False)
def load_site(lat, lon):
    note = []
    try:
        precip, trange, albedo, ws, wsmax = get_climate(lat, lon)
    except Exception:
        precip = trange = albedo = ws = wsmax = np.nan
        note.append("climate")
    try:
        alt, slope, rough = get_terrain(lat, lon)
    except Exception:
        alt = slope = rough = np.nan
        note.append("elevation")
    return precip, trange, albedo, ws, wsmax, alt, slope, rough, note


# ------------------------------------------------------------
# 3. INGEMMET (Peru Geological Survey) · GEOCATMIN services
# ------------------------------------------------------------
ING_REST = "https://geocatmin.ingemmet.gob.pe/arcgis/rest/services/{svc}/MapServer"
ING_WMS = "https://geocatmin.ingemmet.gob.pe/arcgis/services/{svc}/MapServer/WMSServer"
ING_SERVICES = {  # label: (service, WMS layer, identify tolerance px, identify extent deg)
    "Geology 1:100k (integrated)": ("SERV_GEOLOGIA_100K_INTEGRADA", "6", 3, 0.2),
    "Geomorphology": ("SERV_GEOMORFOLOGIA", "Geomorfologia", 3, 0.2),
}


def in_peru(lat, lon):
    return -18.5 <= lat <= 0.1 and -81.5 <= lon <= -68.5


def add_ingemmet_wms(m, show=False):
    for label, (svc, layer, _, _) in ING_SERVICES.items():
        folium.WmsTileLayer(url=ING_WMS.format(svc=svc), layers=layer, fmt="image/png", transparent=True,
                            version="1.1.1", name=f"INGEMMET · {label}", overlay=True, control=True,
                            show=show, opacity=0.6).add_to(m)


@st.cache_data(ttl=3600, show_spinner=False)
def _ingemmet_identify_cached(svc, lat, lon, tol, d):
    # Raises on failure so that failed calls are NOT cached and are retried on the next rerun.
    params = {"geometry": f"{lon},{lat}", "geometryType": "esriGeometryPoint", "sr": 4326, "layers": "all",
              "tolerance": tol, "mapExtent": f"{lon - d},{lat - d},{lon + d},{lat + d}",
              "imageDisplay": "600,600,96", "returnGeometry": "false", "f": "json"}
    r = requests.get(ING_REST.format(svc=svc) + "/identify", params=params, timeout=40, headers=UA, verify=False)
    r.raise_for_status()
    js = r.json()
    if "error" in js:
        raise RuntimeError(js["error"])
    return [{"layer": x.get("layerName", "Layer"), "attributes": x.get("attributes", {})}
            for x in js.get("results", [])[:6]]


def ingemmet_identify(svc, lat, lon, tol, d):
    try:
        return _ingemmet_identify_cached(svc, lat, lon, tol, d)
    except Exception:
        return None


def show_identify(title, result):
    st.markdown(f"**{title}**")
    if result is None:
        st.caption("INGEMMET service did not respond right now. Try again later or open GEOCATMIN.")
        return
    if not result:
        st.caption("No mapped feature found at this point.")
        return
    for item in result:
        attrs = {k: v for k, v in item["attributes"].items()
                 if v not in (None, "", "Null") and "shape" not in k.lower()
                 and k.lower() not in ("objectid", "fid", "globalid")}
        with st.expander(item["layer"] or "Layer", expanded=True):
            if attrs:
                st.table(pd.DataFrame(list(attrs.items()), columns=["Field", "Value"]).astype(str))
            else:
                st.caption("Feature found, no readable attributes.")


# ------------------------------------------------------------
# 4. SIDEBAR
# ------------------------------------------------------------
if "custom" not in st.session_state:
    st.session_state.custom = []

if LOGO:
    st.sidebar.image(LOGO, width=150)
st.sidebar.markdown("### Mission control")
target = st.sidebar.radio("Mission target", ["Mars", "Moon"], horizontal=True)

W = {}
with st.sidebar.expander("Model parameters", expanded=False):
    for k, lab in LABELS.items():
        W[k] = st.slider(lab + " weight", 0.0, 1.0, DEFAULT_W[target][k], 0.05, key=f"w_{target}_{k}")
    slope_limit = st.slider("Operational slope limit (°)", 2, 25, 10)
    arid_scale = st.slider("Aridity scale (mm/yr)", 50, 500, 150, 10)
    wind_thr = st.slider("Sand-transport wind at 10 m (m/s)", 3.0, 10.0, 6.0, 0.5)
    albedo_t = st.slider(f"Target albedo ({target})", 0.05, 0.40, ALBEDO[target], 0.01)
P = {"slope_limit": slope_limit, "arid_scale": arid_scale, "wind_thr": wind_thr}
ALB = dict(ALBEDO)
ALB[target] = albedo_t

with st.sidebar.expander("Analyze your own site"):
    cname = st.text_input("Name", "My site")
    clat = st.number_input("Latitude", -90.0, 90.0, -5.0, 0.01, format="%.4f")
    clon = st.number_input("Longitude", -180.0, 180.0, -80.0, 0.01, format="%.4f")
    if st.button("Add site"):
        st.session_state.custom.append((cname, "Custom", "User-defined", clat, clon))
    if st.session_state.custom and st.button("Clear custom sites"):
        st.session_state.custom = []

view = st.sidebar.selectbox("Map view", ["World", "South America", "Peru"])
st.sidebar.caption("Data: NASA POWER · SRTM/ASTER elevation · NASA Mars Trek (CTX, HiRISE, MOLA) · "
                   "NASA GIBS (MODIS) · INGEMMET GEOCATMIN · MINAM. Thresholds and weights are documented "
                   "assumptions (see Methodology).")

SITES = BASE_SITES + st.session_state.custom

# ------------------------------------------------------------
# 5. LOAD + SCORE
# ------------------------------------------------------------
rows, missing = [], []
bar = st.progress(0.0, text="Connecting to NASA data services…")
for i, (name, country, kind, lat, lon) in enumerate(SITES):
    bar.progress(i / len(SITES), text=f"Fetching NASA data: {name}")
    precip, trange, albedo, ws, wsmax, alt, slope, rough, note = load_site(lat, lon)
    if note:
        missing.append(f"{name}: {', '.join(note)}")
    rows.append({"site": name, "country": country, "type": kind, "lat": lat, "lon": lon,
                 "precip_mm": precip, "temp_range_c": trange, "albedo": albedo, "wind10m_ms": ws,
                 "wind10m_max_ms": wsmax, "altitude_m": alt, "slope_deg": slope, "roughness_m": rough})
bar.empty()
df = pd.DataFrame(rows)


def components(r, tgt):
    s = r.slope_deg
    slope_ok = 1.0 if s <= P["slope_limit"] else float(np.exp(-(s - P["slope_limit"]) / P["slope_limit"]))
    return {"aridity": float(np.exp(-r.precip_mm / P["arid_scale"])),
            "thermal": float(np.clip(r.temp_range_c / 25, 0, 1)),
            "albedo": float(np.exp(-((r.albedo - ALB[tgt]) / 0.1) ** 2)),
            "slope": slope_ok,
            "altitude": float(np.clip(r.altitude_m / 4000, 0, 1)),
            "wind": float(np.clip(r.wind10m_ms / P["wind_thr"], 0, 1))}


def similarity(c, w):
    num = den = 0.0
    for k, wk in w.items():
        if not np.isnan(c[k]):
            num += wk * c[k]
            den += wk
    return round(num / den, 3) if den > 0 else np.nan


def tier(s):
    return "Prime analog" if s >= 0.75 else "Strong" if s >= 0.6 else "Moderate" if s >= 0.45 else "Weak"


def color(s):
    return SCALE[3] if s >= 0.75 else SCALE[2] if s >= 0.6 else SCALE[1] if s >= 0.45 else SCALE[0]


def mtext(s):
    return "#ffffff" if s >= 0.6 else NAVY


if sum(W.values()) == 0:
    st.sidebar.warning("All weights are zero: using default weights.")
    W = dict(DEFAULT_W[target])

comps = [components(r, target) for r in df.itertuples()]
res = pd.concat([df, pd.DataFrame(comps).add_prefix("sim_").round(3)], axis=1)
res["score"] = [similarity(c, W) for c in comps]
res["tier"] = [tier(s) if not np.isnan(s) else "No data" for s in res["score"]]
res = res.sort_values("score", ascending=False).reset_index(drop=True)
res["rank"] = np.arange(1, len(res) + 1)
res["score_mars"] = [similarity(components(r, "Mars"), W if target == "Mars" else DEFAULT_W["Mars"])
                     for r in res.itertuples()]
res["score_moon"] = [similarity(components(r, "Moon"), W if target == "Moon" else DEFAULT_W["Moon"])
                     for r in res.itertuples()]

# ------------------------------------------------------------
# 6. HEADER + KPIs
# ------------------------------------------------------------
st.markdown(f"""
<div class="mast"><p class="wordmark">ALTERGEA</p>
<p class="desc">Earth analog site intelligence for permanent Moon and Mars bases</p></div>
<p class="meta">NASA Space Apps 2026, Piura &nbsp;·&nbsp; Target <b>{target}</b> &nbsp;·&nbsp; <b>{len(res)}</b> sites
&nbsp;·&nbsp; NASA POWER, SRTM, Mars Trek, GIBS, INGEMMET, MINAM</p>
<div class="rule"></div>
""", unsafe_allow_html=True)


def kpi(label, value, sub, accent=None):
    return f'<div class="stat"><div class="l">{label}</div><div class="v">{value}</div><div class="s">{sub}</div></div>'


valid = res.dropna(subset=["score"])
if valid.empty:
    st.error("No NASA data could be downloaded. Check your connection and press Rerun.")
    st.stop()
best = valid.iloc[0]
k1, k2, k3, k4 = st.columns(4)
k1.markdown(kpi("Best analog", best.site, f"{best.country} · score {best.score}"), unsafe_allow_html=True)
k2.markdown(kpi("Mean score", f"{valid.score.mean():.2f}", f"across {len(valid)} sites with data"), unsafe_allow_html=True)
k3.markdown(kpi("Prime analogs", int((valid.score >= 0.75).sum()), "score ≥ 0.75"), unsafe_allow_html=True)
k4.markdown(kpi("Driest site", valid.sort_values("precip_mm").iloc[0].site,
                f"{valid.precip_mm.min():.0f} mm/yr"), unsafe_allow_html=True)
if missing:
    with st.expander("Data notes"):
        st.write("Some NASA services did not answer for: " + "; ".join(missing) +
                 ". Scores use the remaining variables. Press Rerun later to retry.")


def esri_base(m, name="Satellite"):
    folium.TileLayer(tiles=ESRI_IMG, attr=ESRI_ATTR, name=name).add_to(m)


# ---- Surface patches at matched scale: Earth (Esri imagery, z15 ≈ 4.8 m/px at 5° lat) vs Mars (HiRISE mosaic on
# ---- Mars Trek, z13 ≈ 5.1 m/px). 3×3 tiles = 768 px ≈ 3.7–3.9 km on both bodies.
MARS_REFS = {"Bagnold Dunes · Namib Dune (Gale)": NAMIB, "Bradbury Landing · plains (Gale)": BRADBURY}


@st.cache_data(ttl=86400, show_spinner=False)
def fetch_tile(url):
    r = requests.get(url, timeout=30, headers=UA)
    r.raise_for_status()
    return r.content


def mosaic(urls_3x3):
    tiles = []
    for row in urls_3x3:
        imgs = []
        for u in row:
            try:
                imgs.append(Image.open(io.BytesIO(fetch_tile(u))).convert("RGB"))
            except Exception:
                imgs.append(Image.new("RGB", (256, 256), (40, 40, 40)))
        tiles.append(imgs)
    out = Image.new("RGB", (768, 768))
    for i, row in enumerate(tiles):
        for j, im in enumerate(row):
            out.paste(im.resize((256, 256)), (j * 256, i * 256))
    return out


def earth_patch(lat, lon, z=15):
    n = 2 ** z
    x = int((lon + 180) / 360 * n)
    y = int((1 - np.log(np.tan(np.radians(lat)) + 1 / np.cos(np.radians(lat))) / np.pi) / 2 * n)
    urls = [[ESRI_IMG.format(z=z, x=x + dx, y=y + dy) for dx in (-1, 0, 1)] for dy in (-1, 0, 1)]
    return mosaic(urls), 156543.03 * np.cos(np.radians(lat)) / n


def mars_patch(lat, lon, layer="curiosity_hirise_mosaic", z=13):
    col = int((lon + 180) / 360 * 2 ** (z + 1))
    row = int((90 - lat) / 180 * 2 ** z)
    base = f"https://trek.nasa.gov/tiles/Mars/EQ/{layer}/1.0.0/default/default028mm/{z}"
    urls = [[f"{base}/{row + dy}/{col + dx}.png" for dx in (-1, 0, 1)] for dy in (-1, 0, 1)]
    return mosaic(urls), 180 / (256 * 2 ** z) * 59274.7      # metres per pixel (Mars: 1° ≈ 59.27 km)


def texture_stats(img):
    g = np.asarray(img.convert("L"), dtype=float) / 255.0
    return {"brightness": float(g.mean()), "contrast": float(g.std()),
            "texture": float(np.abs(ndimage.laplace(g)).mean())}


def visual_similarity(a, b):
    """0–100 closeness of two image patches on brightness, contrast and fine texture (log-ratio for the last two)."""
    sa, sb = texture_stats(a), texture_stats(b)
    s_bright = 100 * (1 - abs(sa["brightness"] - sb["brightness"]))
    s_contr = 100 * np.exp(-abs(np.log((sa["contrast"] + 1e-4) / (sb["contrast"] + 1e-4))))
    s_text = 100 * np.exp(-abs(np.log((sa["texture"] + 1e-4) / (sb["texture"] + 1e-4))))
    return {"Brightness": s_bright, "Contrast": s_contr, "Fine texture": s_text}, sa, sb


# ------------------------------------------------------------
# 7. TABS
# ------------------------------------------------------------
t_map, t_rank, t_sim, t_site, t_twin, t_peru, t_method = st.tabs(
    ["Mission Map", "Ranking", "Similarity explorer", "Site Explorer", "Mars twin: Médano Blanco ↔ Bagnold",
     "Peru geology (INGEMMET)", "Methodology"])

# Reference conditions shown next to each Earth value in the similarity explorer (what the 0-1 closeness is measured against).
REF = {
    "Mars": {"aridity": "0 mm/yr, no rain", "thermal": "≈ 70 °C diurnal (REMS, Gale)", "albedo": f"{ALB['Mars']} (regional)",
             "slope": f"≤ {slope_limit}° rover-safe", "altitude": "6–7 mbar surface pressure (altitude is the Earth proxy)",
             "wind": "5–10 m/s typical, gusts > 15 (REMS)"},
    "Moon": {"aridity": "no atmosphere", "thermal": "≈ 250 °C diurnal (Diviner, equator)", "albedo": f"{ALB['Moon']}",
             "slope": f"≤ {slope_limit}° lander-safe", "altitude": "vacuum (altitude is the Earth proxy)",
             "wind": "none: weight 0"},
}
FMT = {"aridity": lambda r: f"{r.precip_mm:.0f} mm/yr", "thermal": lambda r: f"{r.temp_range_c} °C",
       "albedo": lambda r: f"{r.albedo}", "slope": lambda r: f"{r.slope_deg}°",
       "altitude": lambda r: f"{r.altitude_m:.0f} m", "wind": lambda r: f"{r.wind10m_ms} m/s"}

with t_map:
    VIEWS = {"World": ([15, -40], 2), "South America": ([-15, -70], 3), "Peru": ([-9.5, -75.5], 5)}
    loc, zoom = VIEWS[view]
    focus = st.session_state.get("focus_site")
    if focus is not None and focus not in set(valid.site):
        focus = st.session_state["focus_site"] = None
    tc1, tc2 = st.columns([3, 1.3])
    topn = tc1.slider("Show top N sites", 3, len(valid), len(valid))
    opts = ["— none —"] + list(valid.site)
    chosen = tc2.selectbox("Focus on a site (or click its marker)", opts,
                           index=opts.index(focus) if focus in opts else 0, key="focus_select")
    if (chosen if chosen != "— none —" else None) != focus:
        st.session_state["focus_site"] = None if chosen == "— none —" else chosen
        st.rerun()
    if focus:
        fr = valid[valid.site == focus].iloc[0]
        loc, zoom = [fr.lat, fr.lon], 9
        if tc2.button("← All sites", help="Back to the overview", use_container_width=True):
            st.session_state["focus_site"] = None
            st.rerun()
    m = folium.Map(location=loc, zoom_start=zoom, tiles=None)
    esri_base(m)
    folium.TileLayer("OpenStreetMap", name="Street map").add_to(m)
    folium.TileLayer(
        tiles="https://server.arcgisonline.com/ArcGIS/rest/services/World_Topo_Map/MapServer/tile/{z}/{y}/{x}",
        attr="Esri", name="Topographic").add_to(m)
    folium.TileLayer(tiles=GIBS, attr="NASA GIBS / MODIS Terra", name="NASA MODIS true colour (GIBS)",
                     max_native_zoom=9, max_zoom=18, overlay=True, show=False, opacity=0.85).add_to(m)
    add_ingemmet_wms(m, show=False)
    for r in valid.head(topn).itertuples():
        size = 26 + int(r.score * 14)
        icon = folium.DivIcon(html=(
            f'<div style="width:{size}px;height:{size}px;border-radius:50%;background:{color(r.score)};'
            f'border:2px solid #fff;color:{mtext(r.score)};font-weight:700;font-size:12px;display:flex;'
            f'align-items:center;justify-content:center;margin:-{size // 2}px 0 0 -{size // 2}px;'
            f'box-shadow:0 2px 8px rgba(0,0,0,.45)">{r.rank}</div>'))
        html = (f"<b>#{r.rank} {r.site}</b> ({r.country})<br>{r.type}<br>"
                f"{target} similarity: <b>{r.score}</b> · {r.tier}<br>"
                f"Precip.: {r.precip_mm} mm/yr · Range: {r.temp_range_c} °C · Wind: {r.wind10m_ms} m/s<br>"
                f"Albedo: {r.albedo} · Alt.: {r.altitude_m:.0f} m · Slope: {r.slope_deg}°")
        folium.Marker([r.lat, r.lon], icon=icon, popup=folium.Popup(html, max_width=300),
                      tooltip=f"#{r.rank} {r.site}: {r.score}").add_to(m)
    folium.LayerControl().add_to(m)
    st.markdown('<div class="legend">'
                f'<span><i class="dot" style="background:{SCALE[3]}"></i>Prime ≥ 0.75</span>'
                f'<span><i class="dot" style="background:{SCALE[2]}"></i>Strong ≥ 0.60</span>'
                f'<span><i class="dot" style="background:{SCALE[1]}"></i>Moderate ≥ 0.45</span>'
                f'<span><i class="dot" style="background:{SCALE[0]}"></i>Weak</span></div>', unsafe_allow_html=True)
    c1, c2 = st.columns([3, 1.3])
    with c1:
        out = st_folium(m, height=560, use_container_width=True, returned_objects=["last_object_clicked"],
                        key="mission_map")
    with c2:
        st.markdown(f"**Top sites for {target}**")
        st.dataframe(valid[["rank", "site", "score"]].head(topn), hide_index=True, height=520,
                     column_config={"score": st.column_config.ProgressColumn("Score", min_value=0, max_value=1, format="%.3f")})
    clicked = (out or {}).get("last_object_clicked")
    if clicked and "lat" in clicked:
        dist = np.hypot(valid.lat - clicked["lat"], valid.lon - clicked["lng"])
        if dist.min() < 0.5:
            hit = valid.iloc[int(dist.argmin())].site
            if hit != st.session_state.get("focus_site"):
                st.session_state["focus_site"] = hit
                st.rerun()

    if focus:
        fr = valid[valid.site == focus].iloc[0]
        st.markdown(f"### Surface comparison · {focus} ↔ Mars")
        st.caption("Both patches cover about 3.8 km at ~5 m per pixel: Esri imagery on Earth, the MRO HiRISE mosaic "
                   "of the Curiosity roving site (NASA Mars Trek) on Mars. Slide to fade one surface into the other.")
        sc1, sc2 = st.columns([1.4, 1])
        ref_name = sc1.selectbox("Mars reference patch", list(MARS_REFS), key="mars_ref")
        alpha = sc2.slider("Earth ⟷ Mars blend", 0.0, 1.0, 0.5, 0.05, key="blend")
        with st.spinner("Fetching surface tiles…"):
            e_img, e_res = earth_patch(fr.lat, fr.lon)
            m_img, m_res = mars_patch(*MARS_REFS[ref_name])
        blend = Image.blend(e_img, m_img, alpha)
        p1, p2, p3 = st.columns(3)
        p1.image(e_img, caption=f"{focus} · Esri imagery · {e_res:.1f} m/px", use_container_width=True)
        p2.image(blend, caption=f"Blend · {int((1 - alpha) * 100)} % Earth / {int(alpha * 100)} % Mars",
                 use_container_width=True)
        p3.image(m_img, caption=f"{ref_name} · HiRISE (Mars Trek) · {m_res:.1f} m/px", use_container_width=True)
        vs, sa, sb = visual_similarity(e_img, m_img)
        comp_f = components(fr, target)
        v1, v2 = st.columns(2)
        with v1:
            st.markdown("**Visual similarity of the two patches** (imagery statistics, not a physical measurement)")
            vdf = pd.DataFrame({"Measure": list(vs), "Similarity %": [round(v, 1) for v in vs.values()],
                                "Earth": [f"{sa['brightness']:.2f}", f"{sa['contrast']:.3f}", f"{sa['texture']:.4f}"],
                                "Mars": [f"{sb['brightness']:.2f}", f"{sb['contrast']:.3f}", f"{sb['texture']:.4f}"]})
            st.dataframe(vdf, hide_index=True, use_container_width=True,
                         column_config={"Similarity %": st.column_config.ProgressColumn("Similarity %", min_value=0,
                                                                                        max_value=100, format="%.0f %%")})
            st.caption(f"Visual mean {np.mean(list(vs.values())):.0f} %. Brightness is the mean grey level, contrast its "
                       "standard deviation, fine texture the mean absolute Laplacian; colour and illumination differ "
                       "between the two sensors, so treat this as a qualitative cue.")
        with v2:
            st.markdown(f"**Environmental similarity to {target}, by variable**")
            edf = pd.DataFrame({"Variable": [LABELS[k] for k in LABELS], "Earth value": [FMT[k](fr) for k in LABELS],
                                "Similarity %": [None if np.isnan(comp_f[k]) else round(comp_f[k] * 100, 1) for k in LABELS],
                                "Weight": [round(W[k], 2) for k in LABELS]})
            st.dataframe(edf, hide_index=True, use_container_width=True,
                         column_config={"Similarity %": st.column_config.ProgressColumn("Similarity %", min_value=0,
                                                                                        max_value=100, format="%.0f %%")})
            st.caption(f"Weighted overall: {fr.score * 100:.0f} % ({fr.tier}). Open the Similarity explorer tab to "
                       "compare several sites variable by variable.")

with t_rank:
    a, b = st.columns(2)
    with a:
        st.markdown(f"**Similarity to {target}**")
        fig = px.bar(valid.sort_values("score"), x="score", y="site", orientation="h", color="score",
                     color_continuous_scale=SCALE, range_color=[0, 1], template="plotly_white")
        fig.update_layout(height=500, margin=dict(l=0, r=0, t=10, b=0), coloraxis_showscale=False, yaxis_title=None)
        st.plotly_chart(fig, use_container_width=True)
    with b:
        st.markdown("**Dual-target matrix: which sites serve both worlds?**")
        fig2 = px.scatter(valid, x="score_moon", y="score_mars", text="site", template="plotly_white",
                          color="score", color_continuous_scale=SCALE, range_color=[0, 1])
        fig2.update_traces(textposition="top center", marker=dict(size=12))
        fig2.update_layout(height=500, margin=dict(l=0, r=0, t=10, b=0), coloraxis_showscale=False,
                           xaxis_title="Moon similarity", yaxis_title="Mars similarity")
        st.plotly_chart(fig2, use_container_width=True)

    st.markdown("**Compare sites (radar)**")
    pick = st.multiselect("Sites", list(valid.site), default=list(valid.site[:3]))
    cats = list(LABELS.values())
    fig3 = go.Figure()
    for nm in pick:
        row = valid[valid.site == nm].iloc[0]
        vals = [row[f"sim_{k}"] for k in LABELS]
        fig3.add_trace(go.Scatterpolar(r=vals + vals[:1], theta=cats + cats[:1], fill="toself", name=nm))
    fig3.update_layout(template="plotly_white", height=450, colorway=BRAND,
                       polar=dict(radialaxis=dict(range=[0, 1])), margin=dict(l=40, r=40, t=20, b=20))
    st.plotly_chart(fig3, use_container_width=True)

    st.download_button("Download results (CSV)", res.to_csv(index=False).encode("utf-8"),
                       file_name=f"altergea_{target.lower()}_ranking.csv", mime="text/csv")
    st.dataframe(res.drop(columns=["lat", "lon"]), hide_index=True)

with t_sim:
    st.markdown(f"**How similar is each site to {target}, variable by variable?** Every variable is scored 0–100 % "
                f"against the {target} reference; the overall figure is the weighted mean of the variables you keep on. "
                "Weights come from the sidebar; switching a variable off here removes it from this comparison only.")
    default_pick = [s for s in valid.site if s.startswith("Médano")] + [s for s in valid.site if not s.startswith("Médano")][:2]
    pick_s = st.multiselect("Sites to compare (up to 5)", list(valid.site), default=default_pick[:3], max_selections=5,
                            key="sim_sites")
    vcols = st.columns(len(LABELS))
    active = {k: vcols[i].checkbox(LABELS[k], value=W[k] > 0, key=f"act_{k}") for i, k in enumerate(LABELS)}
    Wa = {k: (W[k] if active[k] else 0.0) for k in LABELS}
    if not pick_s:
        st.info("Pick at least one site.")
    elif sum(Wa.values()) == 0:
        st.info("Keep at least one variable with a non-zero weight on.")
    else:
        sel_rows = {s: valid[valid.site == s].iloc[0] for s in pick_s}
        comps_sel = {s: components(r, target) for s, r in sel_rows.items()}
        overall = {s: similarity(comps_sel[s], Wa) for s in pick_s}
        ocols = st.columns(len(pick_s))
        for col, s in zip(ocols, pick_s):
            o = overall[s]
            col.markdown(kpi(s, "n/a" if np.isnan(o) else f"{o * 100:.0f} %",
                             f"{sel_rows[s].country} · {sum(1 for k in LABELS if Wa[k] > 0)} variables"), unsafe_allow_html=True)
        long = []
        for s in pick_s:
            for k in LABELS:
                if Wa[k] <= 0:
                    continue
                v = comps_sel[s][k]
                long.append({"Variable": LABELS[k], "Site": s, "Earth value": FMT[k](sel_rows[s]),
                             f"{target} reference": REF[target][k],
                             "Similarity %": None if np.isnan(v) else round(v * 100, 1), "Weight": round(Wa[k], 2)})
        long = pd.DataFrame(long)
        b1, b2 = st.columns([1.3, 1])
        with b1:
            figv = px.bar(long, x="Variable", y="Similarity %", color="Site", barmode="group",
                          color_discrete_sequence=BRAND, template="plotly_white", range_y=[0, 100])
            figv.update_layout(height=360, margin=dict(l=0, r=0, t=10, b=0), xaxis_title=None,
                               legend=dict(orientation="h", y=1.12, title=None), font=dict(family="IBM Plex Sans"))
            st.plotly_chart(figv, use_container_width=True)
        with b2:
            figr = go.Figure()
            cats_on = [LABELS[k] for k in LABELS if Wa[k] > 0]
            for s in pick_s:
                vals = [0 if np.isnan(comps_sel[s][k]) else comps_sel[s][k] * 100 for k in LABELS if Wa[k] > 0]
                figr.add_trace(go.Scatterpolar(r=vals + vals[:1], theta=cats_on + cats_on[:1], fill="toself", name=s))
            figr.update_layout(template="plotly_white", height=360, colorway=BRAND, showlegend=False,
                               polar=dict(radialaxis=dict(range=[0, 100], ticksuffix=" %")),
                               margin=dict(l=30, r=30, t=20, b=20), font=dict(family="IBM Plex Sans"))
            st.plotly_chart(figr, use_container_width=True)
        st.dataframe(long, hide_index=True, use_container_width=True,
                     column_config={"Similarity %": st.column_config.ProgressColumn("Similarity %", min_value=0,
                                                                                    max_value=100, format="%.0f %%")})
        if len(pick_s) >= 2:
            st.markdown("**Head to head**")
            h1, h2 = st.columns(2)
            a_site = h1.selectbox("Site A", pick_s, index=0, key="h2h_a")
            b_site = h2.selectbox("Site B", pick_s, index=1, key="h2h_b")
            if a_site != b_site:
                diff = []
                for k in LABELS:
                    if Wa[k] <= 0:
                        continue
                    va, vb = comps_sel[a_site][k], comps_sel[b_site][k]
                    d = (va - vb) * 100 if not (np.isnan(va) or np.isnan(vb)) else np.nan
                    diff.append({"Variable": LABELS[k], f"{a_site}": FMT[k](sel_rows[a_site]), "A %": round(va * 100, 1),
                                 f"{b_site}": FMT[k](sel_rows[b_site]), "B %": round(vb * 100, 1),
                                 "Edge": "" if np.isnan(d) else (f"{a_site} +{d:.0f}" if d > 0 else f"{b_site} +{-d:.0f}")})
                st.dataframe(pd.DataFrame(diff), hide_index=True, use_container_width=True)
                oa, ob = overall[a_site], overall[b_site]
                st.caption(f"Overall for {target}: {a_site} {oa * 100:.0f} % vs {b_site} {ob * 100:.0f} %.")

with t_site:
    sel = st.selectbox("Select a site", list(valid.site))
    r = valid[valid.site == sel].iloc[0]
    m1, m2, m3, m4, m5, m6 = st.columns(6)
    m1.metric("Score", f"{r.score}", r.tier)
    m2.metric("Precipitation", f"{r.precip_mm} mm/yr")
    m3.metric("Daily temp. range", f"{r.temp_range_c} °C")
    m4.metric("Wind 10 m (mean / max)", f"{r.wind10m_ms} / {r.wind10m_max_ms} m/s")
    m5.metric("Altitude", f"{r.altitude_m:.0f} m")
    m6.metric("Mean slope", f"{r.slope_deg}°")
    left, right = st.columns([1, 1])
    with left:
        cvals = {LABELS[k]: r[f"sim_{k}"] for k in LABELS}
        figc = px.bar(x=list(cvals.values()), y=list(cvals.keys()), orientation="h", template="plotly_white",
                      range_x=[0, 1])
        figc.update_traces(marker_color=NAVY)
        figc.update_layout(height=320, margin=dict(l=0, r=0, t=10, b=0), xaxis_title="Similarity (0–1)", yaxis_title=None)
        st.plotly_chart(figc, use_container_width=True)
        cs = {k: r[f"sim_{k}"] for k in LABELS if not np.isnan(r[f"sim_{k}"])}
        strong = max(cs, key=cs.get)
        weak = min(cs, key=cs.get)
        st.info(f"**{sel}** ({r.type}, {r.country}) is rated **{r.tier.lower()}** for {target}. "
                f"Its strongest match is **{LABELS[strong].lower()}** ({cs[strong]:.2f}); "
                f"its weakest is **{LABELS[weak].lower()}** ({cs[weak]:.2f}).")
    with right:
        ms = folium.Map(location=[r.lat, r.lon], zoom_start=9, tiles=None)
        esri_base(ms)
        folium.CircleMarker([r.lat, r.lon], radius=9, color=color(r.score), fill=True, fill_opacity=0.9).add_to(ms)
        st_folium(ms, height=330, use_container_width=True, returned_objects=[], key="site_map")

with t_twin:
    st.markdown(
        "**Proposed analog: Médano Blanco (Sechura, Piura) ↔ Bagnold Dunes (Gale crater, Mars).** "
        "Both are *active* barchan dune fields shaped by steady wind. Bagnold was the first active dune field "
        "studied in situ on another planet (Curiosity, 2015–2017).")
    q1, q2, q3 = st.columns(3)
    q1.markdown("**What makes the analogy strong**  \nSame landform and process: active barchans and linear dunes "
                "built by a persistent wind regime, loose sand that traps wheels, slipfaces and metre-scale ripples. "
                "Measured migration on both bodies (MINAM, Sentinel-2; HiRISE).")
    q2.markdown("**Where it fails**  \nComposition (quartz vs basalt–olivine), atmosphere (1 bar vs 6 mbar: Mars "
                "sand moves rarely, ~10× slower), gravity, no vegetation on Mars. Médano Blanco is also a protected "
                "tourism site with use restrictions.")
    q3.markdown("**How it helps exploration**  \nA field for rover mobility and sand-trap recovery drills (the "
                "Spirit failure mode), dune-crossing path planning, dust and bedform change-detection methods, "
                "and for calibrating orbital measurements against ground truth, 50 km from Piura.")
    mb = res[res.site.str.startswith("Médano Blanco")]
    mb = mb.iloc[0] if not mb.empty else None

    e_col, m_col = st.columns(2)
    with e_col:
        st.markdown(f"**Earth · Médano Blanco** · {MB_LAT}, {MB_LON} · imagery Esri + NASA GIBS, geology INGEMMET")
        me = folium.Map(location=[MB_LAT, MB_LON], zoom_start=14, tiles=None)
        esri_base(me, "Satellite (Esri)")
        folium.TileLayer(tiles=GIBS, attr="NASA GIBS / MODIS Terra", name="NASA MODIS true colour (GIBS, 250 m)",
                         max_native_zoom=9, max_zoom=18, overlay=True, show=False, opacity=0.85).add_to(me)
        add_ingemmet_wms(me, show=False)
        folium.CircleMarker([MB_LAT, MB_LON], radius=8, color=NAVY, fill=True, fill_opacity=0.9,
                            tooltip="Médano Blanco (barchan, ~16.4 ha)").add_to(me)
        folium.LayerControl().add_to(me)
        st_folium(me, height=430, use_container_width=True, returned_objects=[], key="twin_earth")
    with m_col:
        st.markdown(f"**Mars · Bagnold Dunes, Gale** · Namib Dune {NAMIB[0]}, {NAMIB[1]} · NASA Mars Trek tiles")
        mm = folium.Map(location=list(NAMIB), zoom_start=13, crs="EPSG4326", tiles=None, max_zoom=18)
        for label, pid, ext, mz, show in TREK_LAYERS:
            folium.TileLayer(tiles=TREK.format(layer=pid, ext=ext), attr="NASA / JPL-Caltech / USGS / Mars Trek",
                             name=label, overlay=pid != "Mars_Viking_MDIM21_ClrMosaic_global_232m",
                             show=show, max_native_zoom=mz, max_zoom=18).add_to(mm)
        folium.CircleMarker(list(NAMIB), radius=8, color=RED, fill=True, fill_opacity=0.9,
                            tooltip="Namib Dune · Curiosity sol 1192").add_to(mm)
        folium.CircleMarker(list(BRADBURY), radius=6, color="#ffffff", fill=True, fill_opacity=0.9,
                            tooltip="Bradbury Landing · Curiosity, 2012").add_to(mm)
        folium.LayerControl().add_to(mm)
        st_folium(mm, height=430, use_container_width=True, returned_objects=[], key="twin_mars")
        st.caption("Toggle layers (top right): CTX mosaic of Gale, HiRISE mosaic of the Curiosity roving site, "
                   "HiRISE 1 m DEM. Zoom in on the dark band south-west of the marker to see the dunes.")

    # Our own Sentinel-2 measurement (tools/sentinel_migration.py), if it has been run.
    S2_JSON, S2_CSV, S2_IMG = "data/medano_blanco_migration.json", "data/medano_blanco_migration.csv", "data/sentinel"
    s2 = s2_rows = None
    if os.path.exists(S2_JSON) and os.path.exists(S2_CSV):
        with open(S2_JSON, encoding="utf-8") as fh:
            s2 = json.load(fh)
        s2_rows = pd.read_csv(S2_CSV)
        if "speed_m_per_yr" not in s2 or "shift_along_drift_m" not in s2_rows:
            s2 = s2_rows = None      # output of an older version of the script: ignore

    st.markdown("**Dune migration: Earth vs Mars (measured, not modelled)**")
    g1, g2 = st.columns([1.2, 1])
    with g1:
        mig_rows = [
            ("Médano Blanco, slipface 2006–16 · MINAM", 4.0, "Earth"),
            ("Médano Blanco, slipface 2016–22 · MINAM", 6.0, "Earth"),
            ("Bagnold dunes · HiRISE, Silvestro 2013", 0.4, "Mars"),
            ("Bagnold large ripples, max · HiRISE", 1.7, "Mars"),
        ]
        if s2:
            mig_rows.insert(2, (f"Médano Blanco, dune body {s2['first'][2:4]}–{s2['last'][2:4]} · Sentinel-2, ALTERGEA",
                                s2["speed_m_per_yr"], "Earth"))
        mig = pd.DataFrame(mig_rows, columns=["measurement", "m_per_yr", "world"])
        figm = px.bar(mig, x="m_per_yr", y="measurement", orientation="h", color="world",
                      color_discrete_map={"Earth": NAVY, "Mars": RED}, template="plotly_white", text="m_per_yr")
        figm.update_traces(texttemplate="%{text:.1f}", textposition="outside", cliponaxis=False)
        figm.update_layout(height=320, margin=dict(l=0, r=30, t=10, b=0), xaxis_title="Migration (m per Earth year)",
                           xaxis_range=[0, float(mig.m_per_yr.max()) * 1.2], yaxis_title=None, legend_title=None,
                           yaxis=dict(automargin=True, tickfont=dict(size=11)), font=dict(family="IBM Plex Sans"))
        st.plotly_chart(figm, use_container_width=True)
        st.caption("Earth: MINAM / Expediciones al Desierto (2022), Google Earth 2006–2022, and ALTERGEA's own "
                   "Sentinel-2 measurement below. Mars: Silvestro et al. (2013, HiRISE) as summarised by Bridges "
                   "et al. (2018); ripple range from Baker et al. (2018).")
    with g2:
        earth_alt = f"{mb.altitude_m:.0f} m (SRTM 30 m)" if mb is not None and not np.isnan(mb.altitude_m) else "n/a"
        earth_alb = f"{mb.albedo} (POWER, 50 km cell)" if mb is not None and not np.isnan(mb.albedo) else "n/a"
        earth_wind = (f"{mb.wind10m_ms} mean / {mb.wind10m_max_ms} max m/s (POWER)"
                      if mb is not None and not np.isnan(mb.wind10m_ms) else "n/a")
        earth_pr = f"{mb.precip_mm} mm/yr (POWER)" if mb is not None and not np.isnan(mb.precip_mm) else "n/a"
        cmp = pd.DataFrame([
            ("Dune type", "Barchan, active; ~16.4 ha", "Barchans + linear dunes, active"),
            ("Sand composition", "Quartz sand, light-toned: INGEMMET unit Q-eo 'Depósito eólico'",
             "Dark basaltic, olivine-bearing (ChemCam/APXS)"),
            ("Surface albedo", earth_alb, "Low (dark sand)"),
            ("Elevation", earth_alt, "−4,422 m MOLA datum (rover, sol 1192)"),
            ("Wind 10 m", earth_wind, "REMS in situ (not yet in app)"),
            ("Precipitation", earth_pr, "None"),
            ("Topography source", "SRTM/Copernicus 30 m", "HiRISE DTM 1 m (Gale_DEM_SMG_1m); MOLA 463 m is too coarse"),
            ("Imagery source", "Esri imagery; NASA MODIS (GIBS)", "CTX mosaic; HiRISE mosaic (Mars Trek)"),
            ("Site management", "MINAM: vulnerable to intensive tourism (sandboarding)", "Rover science site, not a base site"),
        ], columns=["Feature", "Médano Blanco", "Bagnold / Namib Dune"])
        st.dataframe(cmp, hide_index=True, height=360)

    if s2 is not None:
        st.markdown(f"**Sentinel-2 time series, {s2['first']} to {s2['last']}: {s2['n_scenes']} cloud-free scenes**")
        s1, s2c = st.columns([1.2, 1])
        with s1:
            ts = s2_rows.copy()
            ts["date"] = pd.to_datetime(ts["date"])
            yrs = (ts["date"] - ts["date"].iloc[0]).dt.days / 365.25
            figs = go.Figure()
            figs.add_trace(go.Scatter(x=ts["date"], y=ts["shift_along_drift_m"], mode="markers",
                                      name="Dune body (cross-correlation)", marker=dict(color=NAVY, size=7)))
            figs.add_trace(go.Scatter(x=ts["date"], y=yrs * s2["speed_m_per_yr"], mode="lines",
                                      name=f"Linear fit: {s2['speed_m_per_yr']} m/yr", line=dict(color=NAVY, width=1.5)))
            if "leading_edge_m" in ts and ts["leading_edge_m"].notna().sum() >= 3:
                figs.add_trace(go.Scatter(x=ts["date"], y=ts["leading_edge_m"], mode="markers",
                                          name="Leading edge (outline)", marker=dict(color="#8fbfe3", size=6)))
            figs.update_layout(template="plotly_white", height=300, margin=dict(l=0, r=0, t=10, b=0),
                               yaxis_title="Displacement along drift direction (m)", xaxis_title=None,
                               legend=dict(orientation="h", y=1.12), font=dict(family="IBM Plex Sans"))
            st.plotly_chart(figs, use_container_width=True)
            sig = s2.get("speed_sigma_m_per_yr")
            st.caption(f"{s2['speed_m_per_yr']}{f' ± {sig}' if sig is not None else ''} m/yr towards "
                       f"{s2['bearing_deg']}°, scatter about the fit {s2['fit_rms_m']} m, {s2['n_scenes']} scenes. "
                       f"Copernicus Sentinel-2 L2A, 10 m, via Earth Search (AWS). Method: {s2['method']}.")
            st.markdown(
                '<div class="note"><b>Reading the two Earth figures.</b> Our Sentinel-2 series tracks the whole dune '
                'body and finds it essentially stationary (below 1 m/yr, at the 10 m detection limit). The MINAM figure '
                'of 4–6 m/yr describes the slipface edge and the arms, where sandboarding and buggy traffic '
                'concentrate, measured on Google Earth imagery whose georeferencing can drift by metres between '
                'dates. In analog terms this brings Médano Blanco closer to Bagnold: both fields are active at the '
                'ripple and slipface scale while their dune bodies migrate well under 1 m/yr.</div>',
                unsafe_allow_html=True)
        with s2c:
            imgs = [(d, os.path.join(S2_IMG, f"{d}.png")) for d in s2_rows["date"]]
            imgs = [(d, p) for d, p in imgs if os.path.exists(p)]
            if imgs:
                pick_i = st.select_slider("Scene", options=[d for d, _ in imgs], value=imgs[-1][0])
                st.image(dict(imgs)[pick_i], caption=f"Sentinel-2 true colour, {pick_i}, ~2 km across. Red outline: "
                                                     "dune outline from the brightness threshold; the displacement is "
                                                     "measured by cross-correlating the dune pixels, not from this outline.",
                         use_container_width=True)
            st.dataframe(s2_rows[["date", "shift_east_m", "shift_north_m", "ncc_peak", "area_ha"]],
                         hide_index=True, height=220,
                         column_config={"ncc_peak": st.column_config.NumberColumn("match", format="%.2f")})
    else:
        st.caption("Sentinel-2 measurement not available: run tools/sentinel_migration.py to generate it.")

    st.markdown(
        '<div class="note"><b>Honest framing.</b> The analogy is morphological and process-based (barchans, steady '
        'wind, loose sand), not mineralogical: Bagnold sand is basaltic and olivine-rich, Médano Blanco is quartz sand. '
        'Gale is a rover science site, so the pitch is <i>training field for mobility and operations in sand that any '
        'Mars base will face</i>. Compare slope and roughness at matched resolution (HiRISE DTM resampled to 30 m vs '
        'Copernicus 30 m), never MOLA 463 m vs SRTM 30 m.</div>', unsafe_allow_html=True)

with t_peru:
    st.markdown("**Geological context from INGEMMET (Peru Geological Survey, GEOCATMIN)** · "
                "complements the NASA-based score with 1:100k geology and geomorphology.")
    peru = valid[[in_peru(a, b) for a, b in zip(valid.lat, valid.lon)]]
    if peru.empty:
        st.info("No analyzed site is inside Peru. Add one from the sidebar (Analyze your own site).")
    else:
        sel_p = st.selectbox("Peruvian site", list(peru.site), key="peru_site")
        rp = peru[peru.site == sel_p].iloc[0]
        pc1, pc2 = st.columns([1.2, 1])
        with pc1:
            mp = folium.Map(location=[rp.lat, rp.lon], zoom_start=10, tiles=None)
            esri_base(mp)
            add_ingemmet_wms(mp, show=True)
            folium.CircleMarker([rp.lat, rp.lon], radius=9, color=color(rp.score), fill=True,
                                fill_opacity=0.95, tooltip=rp.site).add_to(mp)
            folium.LayerControl().add_to(mp)
            st_folium(mp, height=480, use_container_width=True, returned_objects=[], key="peru_map")
            st.link_button("Open GEOCATMIN viewer", "https://geocatmin.ingemmet.gob.pe")
        with pc2:
            st.metric(f"{sel_p} · {target} score", f"{rp.score}", rp.tier)
            with st.spinner("Querying INGEMMET (their server takes ~30 s per layer)…"):
                with ThreadPoolExecutor(max_workers=len(ING_SERVICES)) as ex:
                    futs = {title: ex.submit(ingemmet_identify, svc, rp.lat, rp.lon, tol, d)
                            for title, (svc, _, tol, d) in ING_SERVICES.items()}
                    results = {title: f.result() for title, f in futs.items()}
            for title, result in results.items():
                show_identify(f"INGEMMET · {title}", result)

with t_method:
    st.markdown(f"""
### What ALTERGEA does
It ranks Earth locations by how closely their environment resembles the conditions expected at permanent
Moon and Mars base sites, to help choose training fields on Earth. The flagship candidate is the
**Médano Blanco dune field (Sechura, Piura)** as an analog of the **Bagnold Dunes (Gale crater)**.

### Data used
- **NASA POWER** (power.larc.nasa.gov): precipitation (`PRECTOTCORR`), daily temperature range (`T2M_RANGE`),
  surface albedo (`ALLSKY_SRF_ALB`) and 10 m wind, mean and max (`WS10M`, `WS10M_MAX`), climatological means.
- **SRTM** (NASA/NGA) elevation, with **ASTER GDEM** (NASA/METI) as fallback for polar sites, served by
  OpenTopoData: altitude and mean slope over a ~4 km window (5×5 grid, ~1 km spacing).
- **NASA Mars Trek** (trek.nasa.gov) WMTS tiles for the Mars side of the twin view: Viking MDIM 2.1 colour
  mosaic, MOLA colour hillshade (463 m), MRO CTX Gale crater mosaic, MRO HiRISE Curiosity roving-site mosaic and
  HiRISE 1 m DEM of Gale.
- **NASA GIBS / Worldview** (gibs.earthdata.nasa.gov): MODIS Terra true-colour tiles as an Earth base layer.
- **INGEMMET GEOCATMIN** (Peru Geological Survey): integrated 1:100k geology and geomorphology, as WMS overlays
  and point queries for sites in Peru. Used as **local geological context**; not part of the score.
- **MINAM / SINIA** (2022): *Diagnóstico y microzonificación de la duna Médano Blanco*: dune type, area,
  measured migration 2006–2022 and management constraints.
- Mars dune migration: Silvestro et al. (2013, HiRISE), Bridges et al. (2018), Baker et al. (2018).

### Similarity model (current parameters)
Each variable becomes a 0–1 similarity, combined with a weighted average.
- **Aridity:** exp(−precipitation / {arid_scale} mm).
- **Thermal range:** daily range / 25 °C, capped at 1 (relative closeness: no Earth site matches the Moon or Mars).
- **Albedo:** Gaussian closeness to the target value ({ALB[target]} for {target}).
- **Slope:** full score up to {slope_limit}°, penalized above.
- **Altitude:** altitude / 4000 m, a proxy for low atmospheric pressure.
- **Wind (aeolian activity):** mean 10 m wind / {wind_thr} m/s, capped at 1. Wind drives dune mobility and
  dust; the threshold is the order of magnitude needed to move sand on Earth. Weight 0 for the Moon (no atmosphere).
- **Weights ({target}):** {", ".join(f"{LABELS[k]} {W[k]:.2f}" for k in LABELS)}.

### Limitations
- NASA POWER cells are ~50 km: values describe regional climate, not an exact point (Médano Blanco and the
  whole Sechura coast share one cell).
- Slope is a regional mean from ~1 km spacing, not meter-scale terrain. Any Earth–Mars slope or roughness
  comparison must use matched resolution (HiRISE DTM resampled to 30 m vs Copernicus/SRTM 30 m).
- The Médano Blanco ↔ Bagnold analogy is morphological and process-based, not mineralogical.
- INGEMMET layers are shown as returned by the service; availability depends on their servers.
- Thresholds and weights are documented assumptions. Next step: calibrate with Mars (MOLA, MEDA/REMS)
  and Moon (LOLA, Diviner) reference sites, and add INGEMMET lithology to the score.

### Use of AI
Claude (Anthropic) was used as a coding assistant to write and debug the Python code. The idea, site selection,
model design and interpretation were done by the team.

### References
- NASA POWER Project, https://power.larc.nasa.gov
- NASA Mars Trek, https://trek.nasa.gov/mars · NASA GIBS, https://gibs.earthdata.nasa.gov
- SRTM (NASA/NGA) and ASTER GDEM (NASA/METI), served by OpenTopoData, https://www.opentopodata.org
- INGEMMET, GEOCATMIN: https://geocatmin.ingemmet.gob.pe
- MINAM / SINIA, Diagnóstico y microzonificación del ámbito de uso turístico de la duna Médano Blanco (2022),
  https://sinia.minam.gob.pe/documentos/diagnostico-microzonificacion-ambito-uso-turistico-duna-medano
- Bridges, N. T. et al. (2018). The MSL Bagnold Dunes Campaign, Phase I. *JGR Planets*, doi:10.1002/2017JE005401
- Silvestro, S. et al. (2013). Pervasive aeolian activity along rover Curiosity's traverse in Gale Crater. *Geology* 41, 483–486
- Baker, M. M. et al. (2018). The Bagnold Dunes in southern summer. *GRL*, doi:10.1029/2018GL079040
- Map: Folium / Leaflet; imagery: Esri, Maxar, Earthstar Geographics; OpenStreetMap contributors
""")
