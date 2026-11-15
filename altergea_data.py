"""Shared data access for ALTERGEA: NASA POWER climatology, SRTM/ASTER terrain (via OpenTopoData) and
Copernicus DEM GLO-30 terrain (via Microsoft Planetary Computer).
Used by app.py (Streamlit) and tools/export_sites.py (static web build)."""
import time

import numpy as np
import requests

PC_STAC = "https://planetarycomputer.microsoft.com/api/stac/v1/search"
PC_SIGN = "https://planetarycomputer.microsoft.com/api/sas/v1/sign"

BASE_SITES = [
    ("Médano Blanco (Sechura)", "Peru", "Active barchan dune field", -5.554, -80.757),
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


def get_climate(lat, lon):
    """NASA POWER climatology: precipitation mm/yr, daily temperature range °C, albedo, wind 10 m mean and max m/s."""
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


def pc_sign(href):
    """Sign a Planetary Computer blob URL (public endpoint, no account needed)."""
    r = requests.get(PC_SIGN, params={"href": href}, timeout=30)
    r.raise_for_status()
    return r.json()["href"]


def get_terrain_copdem(lat, lon, half_km=1.5):
    """Copernicus DEM GLO-30 (ESA, via Microsoft Planetary Computer): centre altitude (m), mean slope (°) at 30 m and
    roughness (m, standard deviation of the detrended surface) over a ~3 km window. Needs rasterio."""
    import rasterio
    from rasterio.windows import from_bounds

    r = requests.post(PC_STAC, json={"collections": ["cop-dem-glo-30"], "intersects": {"type": "Point", "coordinates": [lon, lat]},
                                     "limit": 1}, timeout=60)
    r.raise_for_status()
    feats = r.json()["features"]
    if not feats:
        raise ValueError("no Copernicus DEM tile")
    href = pc_sign(feats[0]["assets"]["data"]["href"])
    dlat = half_km / 111.32
    dlon = dlat / max(np.cos(np.radians(lat)), 0.2)
    with rasterio.Env(GDAL_DISABLE_READDIR_ON_OPEN="EMPTY_DIR", CPL_VSIL_CURL_ALLOWED_EXTENSIONS=".tif"):
        with rasterio.open(href) as src:
            win = from_bounds(lon - dlon, lat - dlat, lon + dlon, lat + dlat, transform=src.transform).round_offsets().round_lengths()
            z = src.read(1, window=win, masked=True).astype(float).filled(np.nan)
            px_deg = abs(src.transform.a)
    if z.size < 100 or np.isnan(z).mean() > 0.5:
        raise ValueError("Copernicus DEM window empty")
    z = np.where(np.isnan(z), np.nanmean(z), z)
    dy = px_deg * 111320.0
    dx = dy * np.cos(np.radians(lat))
    gy, gx = np.gradient(z, dy, dx)
    slope = float(np.degrees(np.arctan(np.hypot(gx, gy))).mean())
    yy, xx = np.mgrid[0:z.shape[0], 0:z.shape[1]]
    A = np.c_[xx.ravel(), yy.ravel(), np.ones(z.size)]
    coef, *_ = np.linalg.lstsq(A, z.ravel(), rcond=None)
    rough = float((z.ravel() - A @ coef).std())
    cz = float(z[z.shape[0] // 2, z.shape[1] // 2])
    return round(cz, 0), round(slope, 2), round(rough, 1), round(float(dx), 1)


def get_terrain(lat, lon):
    """Altitude (m), mean slope (°) and roughness (m) over a 5×5 grid at ~1 km spacing, SRTM 30 m with ASTER fallback."""
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
