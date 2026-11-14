import os
import time
import xml.etree.ElementTree as ET
import numpy as np
import pandas as pd
import requests
import folium
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from streamlit_folium import st_folium

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
BASE_SITES = [
    ("Sechura Desert", "Peru", "Hot coastal desert", -5.6, -80.8),
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
          "slope": "Slope", "altitude": "Altitude"}
DEFAULT_W = {
    "Mars": {"aridity": 0.30, "thermal": 0.25, "albedo": 0.20, "slope": 0.15, "altitude": 0.10},
    "Moon": {"aridity": 0.15, "thermal": 0.25, "albedo": 0.25, "slope": 0.20, "altitude": 0.15},
}
ALBEDO = {"Mars": 0.25, "Moon": 0.12}

# ------------------------------------------------------------
# 2. NASA DATA
# ------------------------------------------------------------
def get_climate(lat, lon):
    url = "https://power.larc.nasa.gov/api/temporal/climatology/point"
    params = {"parameters": "PRECTOTCORR,T2M_RANGE,ALLSKY_SRF_ALB", "community": "RE",
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

            return round(ann("PRECTOTCORR") * 365, 1), round(ann("T2M_RANGE"), 1), round(ann("ALLSKY_SRF_ALB"), 3)
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
        precip, trange, albedo = get_climate(lat, lon)
    except Exception:
        precip = trange = albedo = np.nan
        note.append("climate")
    try:
        alt, slope, rough = get_terrain(lat, lon)
    except Exception:
        alt = slope = rough = np.nan
        note.append("elevation")
    return precip, trange, albedo, alt, slope, rough, note


# ------------------------------------------------------------
# 3. INGEMMET (Peru Geological Survey) · GEOCATMIN services
# ------------------------------------------------------------
WMS_URL = "https://geocatmin.ingemmet.gob.pe/ArcGIS/services/SERV_GEOLOGIA/MapServer/WMSServer"
ING_SERVICES = {
    "Geology (1:1M)": ("https://geocatmin.ingemmet.gob.pe/arcgis/rest/services/SERV_GEOLOGIA/MapServer", 3, 0.2),
    "Monitored volcanoes": ("https://geocatminapp.ingemmet.gob.pe/arcgis/rest/services/SERV_VOLCANES/MapServer", 60, 0.5),
}


def in_peru(lat, lon):
    return -18.5 <= lat <= 0.1 and -81.5 <= lon <= -68.5


@st.cache_data(ttl=86400, show_spinner=False)
def wms_layer_names():
    try:
        r = requests.get(WMS_URL, params={"service": "WMS", "request": "GetCapabilities", "version": "1.1.1"},
                         timeout=25)
        r.raise_for_status()
        root = ET.fromstring(r.content)
        names = []
        for lay in root.iter("Layer"):
            n = lay.find("Name")
            if n is not None and n.text:
                names.append(n.text.strip())
        return names
    except Exception:
        return []


def add_ingemmet_wms(m, show=False):
    names = wms_layer_names()
    if not names:
        return False
    folium.WmsTileLayer(url=WMS_URL, layers=",".join(names[:12]), fmt="image/png", transparent=True,
                        version="1.1.1", name="INGEMMET geology 1:1M (Peru)", overlay=True,
                        control=True, show=show, opacity=0.65).add_to(m)
    return True


@st.cache_data(ttl=3600, show_spinner=False)
def ingemmet_identify(base, lat, lon, tol, d):
    params = {"geometry": f"{lon},{lat}", "geometryType": "esriGeometryPoint", "sr": 4326, "layers": "all",
              "tolerance": tol, "mapExtent": f"{lon - d},{lat - d},{lon + d},{lat + d}",
              "imageDisplay": "600,600,96", "returnGeometry": "false", "f": "json"}
    try:
        r = requests.get(base + "/identify", params=params, timeout=30)
        r.raise_for_status()
        js = r.json()
        if "error" in js:
            return None
        return [{"layer": x.get("layerName", "Layer"), "attributes": x.get("attributes", {})}
                for x in js.get("results", [])[:6]]
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
                 and k.lower() not in ("objectid", "fid")}
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

HAS_LOGO = os.path.exists("logo.jpg")
if HAS_LOGO:
    st.sidebar.image("logo.jpg", use_container_width=True)
st.sidebar.markdown("### MISSION CONTROL")
target = st.sidebar.radio("Mission target", ["Mars", "Moon"], horizontal=True)

W = {}
with st.sidebar.expander("Model parameters", expanded=False):
    for k, lab in LABELS.items():
        W[k] = st.slider(lab + " weight", 0.0, 1.0, DEFAULT_W[target][k], 0.05, key=f"w_{target}_{k}")
    slope_limit = st.slider("Operational slope limit (°)", 2, 25, 10)
    arid_scale = st.slider("Aridity scale (mm/yr)", 50, 500, 150, 10)
    albedo_t = st.slider(f"Target albedo ({target})", 0.05, 0.40, ALBEDO[target], 0.01)
P = {"slope_limit": slope_limit, "arid_scale": arid_scale}
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
st.sidebar.caption("Data: NASA POWER · SRTM/ASTER elevation · INGEMMET GEOCATMIN (Peru). "
                   "Thresholds and weights are documented assumptions (see Methodology).")

SITES = BASE_SITES + st.session_state.custom

# ------------------------------------------------------------
# 5. LOAD + SCORE
# ------------------------------------------------------------
rows, missing = [], []
bar = st.progress(0.0, text="Connecting to NASA data services…")
for i, (name, country, kind, lat, lon) in enumerate(SITES):
    bar.progress(i / len(SITES), text=f"Fetching NASA data: {name}")
    precip, trange, albedo, alt, slope, rough, note = load_site(lat, lon)
    if note:
        missing.append(f"{name}: {', '.join(note)}")
    rows.append({"site": name, "country": country, "type": kind, "lat": lat, "lon": lon,
                 "precip_mm": precip, "temp_range_c": trange, "albedo": albedo,
                 "altitude_m": alt, "slope_deg": slope, "roughness_m": rough})
bar.empty()
df = pd.DataFrame(rows)


def components(r, tgt):
    s = r.slope_deg
    slope_ok = 1.0 if s <= P["slope_limit"] else float(np.exp(-(s - P["slope_limit"]) / P["slope_limit"]))
    return {"aridity": float(np.exp(-r.precip_mm / P["arid_scale"])),
            "thermal": float(np.clip(r.temp_range_c / 25, 0, 1)),
            "albedo": float(np.exp(-((r.albedo - ALB[tgt]) / 0.1) ** 2)),
            "slope": slope_ok,
            "altitude": float(np.clip(r.altitude_m / 4000, 0, 1))}


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
    if HAS_LOGO:
        st.image("logo.jpg", width=130)
with hc2:
    st.markdown(f"""
    <p class="hero-title">ALTERGEA</p>
    <p class="hero-sub">Earth analog site intelligence for permanent Moon and Mars bases ·
    reading Earth to open the way to other worlds</p>
    <span class="pill red">NASA SPACE APPS 2026 · PIURA</span>
    <span class="pill">TARGET: {target.upper()}</span>
    <span class="pill">{len(res)} SITES</span>
    <span class="pill">NASA POWER · SRTM/ASTER · INGEMMET</span>
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

# ------------------------------------------------------------
# 7. TABS
# ------------------------------------------------------------
t_map, t_rank, t_site, t_peru, t_method = st.tabs(
    ["Mission Map", "Ranking & Compare", "Site Explorer", "Peru geology (INGEMMET)", "Methodology"])

with t_map:
    VIEWS = {"World": ([15, -40], 2), "South America": ([-15, -70], 3), "Peru": ([-9.5, -75.5], 5)}
    loc, zoom = VIEWS[view]
    topn = st.slider("Show top N sites", 3, len(valid), len(valid))
    m = folium.Map(location=loc, zoom_start=zoom, tiles=None)
    folium.TileLayer(
        tiles="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
        attr="Esri, Maxar, Earthstar Geographics", name="Satellite").add_to(m)
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
                f"Precip.: {r.precip_mm} mm/yr · Range: {r.temp_range_c} °C<br>"
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
    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("Score", f"{r.score}", r.tier)
    m2.metric("Precipitation", f"{r.precip_mm} mm/yr")
    m3.metric("Daily temp. range", f"{r.temp_range_c} °C")
    m4.metric("Altitude", f"{r.altitude_m:.0f} m")
    m5.metric("Mean slope", f"{r.slope_deg}°")
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
        folium.TileLayer(
            tiles="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
            attr="Esri, Maxar, Earthstar Geographics").add_to(ms)
        folium.CircleMarker([r.lat, r.lon], radius=9, color=color(r.score), fill=True, fill_opacity=0.9).add_to(ms)
        st_folium(ms, height=330, use_container_width=True, returned_objects=[], key="site_map")

with t_peru:
    st.markdown("**Geological context from INGEMMET (Peru Geological Survey, GEOCATMIN)** · "
                "complements the NASA-based score with local geology and monitored volcanoes.")
    peru = valid[[in_peru(a, b) for a, b in zip(valid.lat, valid.lon)]]
    if peru.empty:
        st.info("No analyzed site is inside Peru. Add one from the sidebar (Analyze your own site).")
    else:
        sel_p = st.selectbox("Peruvian site", list(peru.site), key="peru_site")
        rp = peru[peru.site == sel_p].iloc[0]
        pc1, pc2 = st.columns([1.2, 1])
        with pc1:
            mp = folium.Map(location=[rp.lat, rp.lon], zoom_start=8, tiles=None)
            folium.TileLayer(
                tiles="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
                attr="Esri, Maxar, Earthstar Geographics", name="Satellite").add_to(mp)
            ok = add_ingemmet_wms(mp, show=True)
            folium.CircleMarker([rp.lat, rp.lon], radius=9, color=color(rp.score), fill=True,
                                fill_opacity=0.95, tooltip=rp.site).add_to(mp)
            folium.LayerControl().add_to(mp)
            st_folium(mp, height=480, use_container_width=True, returned_objects=[], key="peru_map")
            if not ok:
                st.caption("The INGEMMET geology overlay is not available right now.")
            st.link_button("Open GEOCATMIN viewer", "https://geocatmin.ingemmet.gob.pe")
        with pc2:
            st.metric(f"{sel_p} · {target} score", f"{rp.score}", rp.tier)
            for title, (base, tol, d) in ING_SERVICES.items():
                show_identify(f"INGEMMET · {title}", ingemmet_identify(base, rp.lat, rp.lon, tol, d))

with t_method:
    st.markdown(f"""
### What ALTERGEA does
It ranks Earth locations by how closely their environment resembles the conditions expected at permanent
Moon and Mars base sites, to help choose training fields on Earth.

### Data used
- **NASA POWER** (power.larc.nasa.gov): precipitation (`PRECTOTCORR`), daily temperature range (`T2M_RANGE`)
  and surface albedo (`ALLSKY_SRF_ALB`), climatological means. These drive the similarity score.
- **SRTM** (NASA/NGA) elevation, with **ASTER GDEM** (NASA/METI) as fallback for polar sites, served by
  OpenTopoData: altitude and mean slope over a ~4 km window (5×5 grid, ~1 km spacing).
- **INGEMMET GEOCATMIN** (Peru Geological Survey, geocatmin.ingemmet.gob.pe): 1:1M geology map overlay and
  monitored volcanoes, queried live for sites in Peru. Used as **local geological context**; it is not yet part of the score.

### Similarity model (current parameters)
Each variable becomes a 0–1 similarity, combined with a weighted average.
- **Aridity:** exp(−precipitation / {arid_scale} mm).
- **Thermal range:** daily range / 25 °C, capped at 1 (relative closeness: no Earth site matches the Moon or Mars).
- **Albedo:** Gaussian closeness to the target value ({ALB[target]} for {target}).
- **Slope:** full score up to {slope_limit}°, penalized above.
- **Altitude:** altitude / 4000 m, a proxy for low atmospheric pressure.
- **Weights ({target}):** {", ".join(f"{LABELS[k]} {W[k]:.2f}" for k in LABELS)}.

### Limitations
- NASA POWER cells are ~50 km: values describe regional climate, not an exact point.
- Slope is a regional mean from ~1 km spacing, not meter-scale terrain.
- INGEMMET layers are queried at a point and shown as returned by the service; availability depends on their servers.
- Thresholds and weights are documented assumptions. Next step: calibrate with Mars (MOLA, MEDA/REMS)
  and Moon (LOLA, Diviner) reference sites, and add INGEMMET lithology to the score.

### Use of AI
Claude (Anthropic) was used as a coding assistant to write and debug the Python code. The idea, site selection,
model design and interpretation were done by the team.

### References
- NASA POWER Project, https://power.larc.nasa.gov
- SRTM (NASA/NGA) and ASTER GDEM (NASA/METI), served by OpenTopoData, https://www.opentopodata.org
- INGEMMET, GEOCATMIN: https://geocatmin.ingemmet.gob.pe
- Map: Folium / Leaflet; imagery: Esri, Maxar, Earthstar Geographics; OpenStreetMap contributors
""")