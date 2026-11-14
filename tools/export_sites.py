"""Precompute the NASA POWER + SRTM/ASTER variables of the base sites for the static web build.
Writes web/data/sites.json and copies the Sentinel-2 results into web/data/.

Run:  .venv/Scripts/python.exe tools/export_sites.py
"""
import json
import os
import shutil
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from altergea_data import BASE_SITES, get_climate, get_terrain  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "web", "data")
os.makedirs(os.path.join(OUT, "sentinel"), exist_ok=True)


def nan_none(v):
    return None if v != v else v


def main():
    sites = []
    for name, country, kind, lat, lon in BASE_SITES:
        print(f"  {name}", end=": ", flush=True)
        try:
            precip, trange, albedo, ws, wsmax = get_climate(lat, lon)
        except Exception as e:
            print("climate failed", e, end="; ")
            precip = trange = albedo = ws = wsmax = float("nan")
        try:
            alt, slope, rough = get_terrain(lat, lon)
        except Exception as e:
            print("terrain failed", e, end="; ")
            alt = slope = rough = float("nan")
        print("ok")
        sites.append({"site": name, "country": country, "type": kind, "lat": lat, "lon": lon,
                      "precip_mm": nan_none(precip), "temp_range_c": nan_none(trange), "albedo": nan_none(albedo),
                      "wind10m_ms": nan_none(ws), "wind10m_max_ms": nan_none(wsmax), "altitude_m": nan_none(alt),
                      "slope_deg": nan_none(slope), "roughness_m": nan_none(rough)})
    out = {"generated": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
           "sources": {"climate": "NASA POWER climatology (PRECTOTCORR, T2M_RANGE, ALLSKY_SRF_ALB, WS10M, WS10M_MAX)",
                       "terrain": "SRTM 30 m (NASA/NGA), ASTER GDEM fallback, via OpenTopoData; 5x5 grid at ~1 km"},
           "sites": sites}
    with open(os.path.join(OUT, "sites.json"), "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=1, ensure_ascii=False)
    for f in ("medano_blanco_migration.json", "medano_blanco_migration.csv"):
        src = os.path.join(ROOT, "data", f)
        if os.path.exists(src):
            shutil.copy(src, os.path.join(OUT, f))
    sdir = os.path.join(ROOT, "data", "sentinel")
    if os.path.isdir(sdir):
        for f in os.listdir(sdir):
            shutil.copy(os.path.join(sdir, f), os.path.join(OUT, "sentinel", f))
    print(f"wrote {len(sites)} sites to web/data/sites.json")


if __name__ == "__main__":
    main()
