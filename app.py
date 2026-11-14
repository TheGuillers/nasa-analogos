import os
import time
from concurrent.futures import ThreadPoolExecutor
import numpy as np
import pandas as pd
import requests
import urllib3
import folium
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from streamlit_folium import st_folium

# geocatmin.ingemmet.gob.pe serves an incomplete certificate chain: Python cannot verify it (curl/browsers can).
# Only INGEMMET requests use verify=False; NASA services are verified normally.
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
UA = {"User-Agent": "Mozilla/5.0 (ALTERGEA analog-site tool)"}

st.set_page_config(page_title="ALTERGEA · Analog Site Intelligence", page_icon="🔺", layout="wide")

NAVY, SKY, YEL, ORG, RED = "#0d1b5e", "#1fa2e8", "#fdb913", "#f08a00", "#e8212b"
SCALE = [RED, ORG, YEL, SKY]
BRAND = [NAVY, RED, YEL, SKY, ORG]

st.markdown(f"""
<style>
.block-container{{padding-top:1.4rem;max-width:1500px}}
.hero-title{{font-size:2.1rem;font-weight:800;letter-spacing:.18em;color:{NAVY};margin:0;line-height:1.1}}
.hero-sub{{color:#5a6488;margin:6px 0 10px;font-size:1rem}}
.bar{{height:5px;border-radius:4px;margin:10px 0 16px;
      background:linear-gradient(90deg,{SKY},{YEL},{ORG},{RED})}}
.pill{{display:inline-block;padding:2px 11px;border:1px solid #c9d0ea;border-radius:999px;background:#fff;
      font-size:.72rem;color:{NAVY};margin-right:6px;letter-spacing:.06em;font-weight:600}}
.pill.red{{border-color:{RED};color:{RED}}}
.kpi{{background:#fff;border:1px solid #e3e7f3;border-left:5px solid {SKY};border-radius:12px;
     padding:12px 16px;margin-bottom:8px;box-shadow:0 1px 4px rgba(13,27,94,.06)}}
.kpi .l{{font-size:.68rem;letter-spacing:.12em;color:#6b7597;text-transform:uppercase;font-weight:600}}
.kpi .v{{font-size:1.4rem;font-weight:800;color:{NAVY}}}
.kpi .s{{font-size:.8rem;color:#6b7597}}
.legend span{{display:inline-block;margin-right:16px;font-size:.85rem;color:{NAVY}}}
.dot{{display:inline-block;width:11px;height:11px;border-radius:50%;margin-right:6px}}
</style>
""", unsafe_allow_html=True)

# ------------------------------------------------------------
# 1. SITES
# ------------------------------------------------------------
# Médano Blanco: barchan dune, Comunidad Campesina San Martín de Sechura. Position from the MINAM diagnostic
# (UTM 17M 526906 E / 9386090 S -> -5.554, -80.757), consistent with OpenStreetMap.
MB_LAT, MB_LON = -5.554, -80.757
BASE_SITES = [
    ("Médano Blanco (Sechura)", "Peru", "Active barchan dune field", MB_LAT, MB_LON),
    ("Nazca Plains", "Peru", "Hyper-arid plateau", -14.8, -75.1),
    ("Ubinas Volcano", "Peru", "Active volcano", -16.35, -70.9),
    ("Misti Volcano", "Peru", "Active volcano", -16.29, -71.41),
    ("Sabancaya Volcano", "Peru", "Active volcano", -15.78, -71.85),
    ("Atacama Desert", "Chile", "Hyper-arid desert", -23.9, -69.2),
    ("Uyuni Salt Flat", "Bolivia", "Evaporite flat", -20.2, -67.5),
    ("Mt. Etna", "Italy", "Basaltic volcano", 37.75, 14.99),
    ("Mauna Kea", "USA", "Basaltic volcano", 19.82, -155.47),
    ("Rio Tinto", "Spain", "Acidic river basin", 37.72, -6.55),
    ("Death Valley", "USA", "Hot desert", 36.46, -116.87),
    ("Dallol", "Ethiopia", "Hydrothermal desert", 14.24, 40.30),
    ("Devon Island", "Canada", "Polar desert", 75.37, -89.68),
    ("Mojave Desert", "USA", "Hot desert", 35.0, -116.9),
]

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
def get_climate(lat, lon):
    url = "https://power.larc.nasa.gov/api/temporal/climatology/point"
    params = {"parameters": "PRECTOTCORR,T2M_RANGE,ALLSKY_SRF_ALB,WS10M,WS10M_MAX", "community": "RE",
              "longitude": lon, "latitude": lat, "format": "JSON"}
    err = None
    for _ in range(3):
        try:
            r = requests.get(url, params=params, timeout=45)
            r.raise_for_status()
            p = r.json()["properties"]["parameter"]

            def ann(k):
                v = p.get(k, {}).get("ANN")
                return np.nan if v is None or v <= -900 else float(v)

            return (round(ann("PRECTOTCORR") * 365, 1), round(ann("T2M_RANGE"), 1), round(ann("ALLSKY_SRF_ALB"), 3),
                    round(ann("WS10M"), 2), round(ann("WS10M_MAX"), 2))
        except Exception as e:
            err = e
            time.sleep(2)
    raise err


def get_terrain(lat, lon):
    step = 0.01
    off = np.arange(-2, 3) * step
    pts = "|".join(f"{la:.5f},{lo:.5f}" for la in lat + off for lo in lon + off)
    err = None
    for dataset in ("srtm30m", "aster30m"):  # SRTM covers +-60 deg; ASTER reaches polar sites
        for _ in range(2):
            try:
                r = requests.get(f"https://api.opentopodata.org/v1/{dataset}", params={"locations": pts}, timeout=45)
                r.raise_for_status()
                res = r.json()["results"]
                z = np.array([np.nan if x["elevation"] is None else x["elevation"] for x in res],
                             dtype=float).reshape(5, 5)
                if np.isnan(z).all():
                    raise ValueError("no elevation data")
                z = np.where(np.isnan(z), np.nanmean(z), z)
                dy = step * 111320.0
                dx = dy * np.cos(np.radians(lat))
                gy, gx = np.gradient(z, dy, dx)
                slope = np.degrees(np.arctan(np.sqrt(gx ** 2 + gy ** 2))).mean()
                time.sleep(1.1)
                return round(float(z[2, 2]), 0), round(float(slope), 2), round(float(z.std()), 1)
            except Exception as e:
                err = e
                time.sleep(2)
    raise err


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

LOGO = next((f for f in ("logo.jpg", "logo.jpeg", "logo.png") if os.path.exists(f)), None)
if LOGO:
    st.sidebar.image(LOGO, use_container_width=True)
st.sidebar.markdown("### MISSION CONTROL")
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
    return "#ffffff" if (s >= 0.75 or s < 0.45) else NAVY


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
hc1, hc2 = st.columns([1, 7])
with hc1:
    if LOGO:
        st.image(LOGO, width=130)
with hc2:
    st.markdown(f"""
    <p class="hero-title">ALTERGEA</p>
    <p class="hero-sub">Earth analog site intelligence for permanent Moon and Mars bases ·
    reading Earth to open the way to other worlds</p>
    <span class="pill red">NASA SPACE APPS 2026 · PIURA</span>
    <span class="pill">TARGET: {target.upper()}</span>
    <span class="pill">{len(res)} SITES</span>
    <span class="pill">NASA POWER · SRTM · MARS TREK · GIBS · INGEMMET</span>
    """, unsafe_allow_html=True)
st.markdown('<div class="bar"></div>', unsafe_allow_html=True)


def kpi(label, value, sub, accent):
    return (f'<div class="kpi" style="border-left-color:{accent}"><div class="l">{label}</div>'
            f'<div class="v">{value}</div><div class="s">{sub}</div></div>')


valid = res.dropna(subset=["score"])
if valid.empty:
    st.error("No NASA data could be downloaded. Check your connection and press Rerun.")
    st.stop()
best = valid.iloc[0]
k1, k2, k3, k4 = st.columns(4)
k1.markdown(kpi("Best analog", best.site, f"{best.country} · score {best.score}", SKY), unsafe_allow_html=True)
k2.markdown(kpi("Mean score", f"{valid.score.mean():.2f}", f"across {len(valid)} sites with data", YEL), unsafe_allow_html=True)
k3.markdown(kpi("Prime analogs", int((valid.score >= 0.75).sum()), "score ≥ 0.75", ORG), unsafe_allow_html=True)
k4.markdown(kpi("Driest site", valid.sort_values("precip_mm").iloc[0].site,
                f"{valid.precip_mm.min():.0f} mm/yr", RED), unsafe_allow_html=True)
if missing:
    with st.expander("Data notes"):
        st.write("Some NASA services did not answer for: " + "; ".join(missing) +
                 ". Scores use the remaining variables. Press Rerun later to retry.")


def esri_base(m, name="Satellite"):
    folium.TileLayer(tiles=ESRI_IMG, attr=ESRI_ATTR, name=name).add_to(m)


# ------------------------------------------------------------
# 7. TABS
# ------------------------------------------------------------
t_map, t_rank, t_site, t_twin, t_peru, t_method = st.tabs(
    ["Mission Map", "Ranking & Compare", "Site Explorer", "Mars twin: Médano Blanco ↔ Bagnold",
     "Peru geology (INGEMMET)", "Methodology"])

with t_map:
    VIEWS = {"World": ([15, -40], 2), "South America": ([-15, -70], 3), "Peru": ([-9.5, -75.5], 5)}
    loc, zoom = VIEWS[view]
    topn = st.slider("Show top N sites", 3, len(valid), len(valid))
    m = folium.Map(location=loc, zoom_start=zoom, tiles=None)
    esri_base(m)
    folium.TileLayer(tiles=GIBS, attr="NASA GIBS / MODIS Terra", name="NASA MODIS true colour (GIBS)",
                     max_native_zoom=9, max_zoom=18).add_to(m)
    folium.TileLayer("OpenStreetMap", name="Street map").add_to(m)
    folium.TileLayer(
        tiles="https://server.arcgisonline.com/ArcGIS/rest/services/World_Topo_Map/MapServer/tile/{z}/{y}/{x}",
        attr="Esri", name="Topographic").add_to(m)
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
        st_folium(m, height=560, use_container_width=True, returned_objects=[])
    with c2:
        st.markdown(f"**Top sites for {target}**")
        st.dataframe(valid[["rank", "site", "score"]].head(topn), hide_index=True, height=520,
                     column_config={"score": st.column_config.ProgressColumn("Score", min_value=0, max_value=1, format="%.3f")})

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
        "studied in situ on another planet (Curiosity, 2015–2017). Médano Blanco is an operational training field "
        "for rover mobility on loose sand, a documented mission risk (Spirit, 2009).")
    mb = res[res.site.str.startswith("Médano Blanco")]
    mb = mb.iloc[0] if not mb.empty else None

    e_col, m_col = st.columns(2)
    with e_col:
        st.markdown(f"**Earth · Médano Blanco** · {MB_LAT}, {MB_LON} · imagery Esri + NASA GIBS, geology INGEMMET")
        me = folium.Map(location=[MB_LAT, MB_LON], zoom_start=14, tiles=None)
        esri_base(me, "Satellite (Esri)")
        folium.TileLayer(tiles=GIBS, attr="NASA GIBS / MODIS Terra", name="NASA MODIS true colour (GIBS, 250 m)",
                         max_native_zoom=9, max_zoom=18).add_to(me)
        add_ingemmet_wms(me, show=False)
        folium.CircleMarker([MB_LAT, MB_LON], radius=8, color=RED, fill=True, fill_opacity=0.9,
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
        folium.CircleMarker(list(BRADBURY), radius=6, color=YEL, fill=True, fill_opacity=0.9,
                            tooltip="Bradbury Landing · Curiosity, 2012").add_to(mm)
        folium.LayerControl().add_to(mm)
        st_folium(mm, height=430, use_container_width=True, returned_objects=[], key="twin_mars")
        st.caption("Toggle layers (top right): CTX mosaic of Gale, HiRISE mosaic of the Curiosity roving site, "
                   "HiRISE 1 m DEM. Zoom in on the dark band south-west of the marker to see the dunes.")

    st.markdown("**Dune migration: Earth vs Mars (measured, not modelled)**")
    g1, g2 = st.columns([1.2, 1])
    with g1:
        mig = pd.DataFrame([
            ("Médano Blanco · slipface 2006–2016", 4.0, "Earth"),
            ("Médano Blanco · slipface 2016–2022", 6.0, "Earth"),
            ("Médano Blanco · stoss side 2016–2022", 2.0, "Earth"),
            ("Bagnold dunes (HiRISE)", 0.4, "Mars"),
            ("Bagnold large ripples, upper bound (HiRISE)", 1.7, "Mars"),
        ], columns=["measurement", "m_per_yr", "world"])
        figm = px.bar(mig, x="m_per_yr", y="measurement", orientation="h", color="world",
                      color_discrete_map={"Earth": SKY, "Mars": RED}, template="plotly_white", text="m_per_yr")
        figm.update_layout(height=300, margin=dict(l=0, r=0, t=10, b=0), xaxis_title="Migration (m per Earth year)",
                           yaxis_title=None, legend_title=None)
        st.plotly_chart(figm, use_container_width=True)
        st.caption("Earth: MINAM / Expediciones al Desierto (2022), Google Earth 2006–2022. Mars: Silvestro et al. "
                   "(2013, HiRISE) as summarised by Bridges et al. (2018); ripple range from Baker et al. (2018).")
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

    st.warning(
        "**Honest framing.** The analogy is morphological and process-based (barchans, steady wind, loose sand), "
        "not mineralogical: Bagnold sand is basaltic and olivine-rich, Médano Blanco is light-toned. Gale is a rover "
        "science site, so the pitch is *training field for mobility and operations in sand that any Mars base will "
        "face*. Compare slope and roughness at matched resolution (HiRISE DTM resampled to 30 m vs Copernicus 30 m), "
        "never MOLA 463 m vs SRTM 30 m. Next step: measure Médano Blanco migration from Sentinel-2 / Landsat "
        "multi-year imagery instead of Google Earth.")

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
