"""Measure the migration of the Médano Blanco barchan (Sechura, Peru) from Sentinel-2 L2A imagery.

Data: Copernicus Sentinel-2 L2A cloud-optimised GeoTIFFs on AWS (Earth Search STAC, Element 84), public, no login.
Method:
  1. Query every scene with < 4 % tile cloud cover since 2017 and keep those whose SCL mask shows no cloud or
     shadow inside a ~2 km window around the dune (up to MAX_SCENES, spread over time).
  2. Read the 10 m blue/green/red bands, build a brightness image and z-score it per scene.
  3. Displacement: normalised cross-correlation of the dune template (first scene, 800 m box) against each later
     scene, with a parabolic sub-pixel refinement of the correlation peak. This tracks the dune *shape*, so it is
     insensitive to the brightness threshold and to the loose-sand streaks around the barchan.
  4. Outline (for the cut-outs and the area): Otsu threshold on brightness, binary opening to drop streaks, and the
     connected component that contains the dune centre.
  5. Speed and bearing: linear fit of the cross-correlation shift against time; a leading-edge estimate is the
     maximum extent of the outline along the drift direction, also fitted against time.
Outputs: data/medano_blanco_migration.csv, data/medano_blanco_migration.json, data/sentinel/<date>.png.

Run:  .venv/Scripts/python.exe tools/sentinel_migration.py
"""
import csv
import json
import os
import sys
from datetime import datetime, timezone

import numpy as np
import rasterio
import requests
from PIL import Image
from rasterio.warp import transform, transform_bounds
from rasterio.windows import from_bounds
from scipy import ndimage, signal

STAC = "https://earth-search.aws.element84.com/v1/search"
LAT, LON = -5.5565, -80.7567          # centre of the dune body (MINAM position is at its NW foot: -5.554, -80.757)
HALF = 0.009                          # window half-size in degrees (~1 km)
BBOX = [LON - HALF, LAT - HALF, LON + HALF, LAT + HALF]
START = "2017-01-01"
END = datetime.now(timezone.utc).strftime("%Y-%m-%d")
MAX_TILE_CLOUD, MAX_LOCAL_CLOUD, MAX_SCENES = 4.0, 0.01, 45
TEMPLATE_HALF, SEARCH = 40, 25        # template 80 px (800 m) box; search ±25 px (±250 m)
OUT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
IMG_DIR = os.path.join(OUT_DIR, "sentinel")
os.makedirs(IMG_DIR, exist_ok=True)
ENV = dict(GDAL_DISABLE_READDIR_ON_OPEN="EMPTY_DIR", AWS_NO_SIGN_REQUEST="YES",
           CPL_VSIL_CURL_ALLOWED_EXTENSIONS=".tif", GDAL_HTTP_MULTIRANGE="YES", GDAL_HTTP_MAX_RETRY="3",
           GDAL_HTTP_RETRY_DELAY="2")


def search():
    body = {"collections": ["sentinel-2-l2a"], "bbox": BBOX, "datetime": f"{START}T00:00:00Z/{END}T23:59:59Z",
            "query": {"eo:cloud_cover": {"lt": MAX_TILE_CLOUD}}, "limit": 500}
    r = requests.post(STAC, json=body, timeout=90)
    r.raise_for_status()
    feats = sorted(r.json()["features"], key=lambda f: f["properties"]["datetime"])
    if len(feats) > MAX_SCENES:          # spread the budget over the whole period
        idx = np.round(np.linspace(0, len(feats) - 1, MAX_SCENES)).astype(int)
        feats = [feats[i] for i in idx]
    return feats


def read_window(href, out_shape=None):
    with rasterio.open(href) as src:
        b = transform_bounds("EPSG:4326", src.crs, *BBOX)
        win = from_bounds(*b, transform=src.transform).round_offsets().round_lengths()
        arr = src.read(1, window=win, out_shape=out_shape)
        return arr.astype(np.float32), src.window_transform(win), src.crs


def otsu(x):
    hist, edges = np.histogram(x, bins=256)
    hist = hist.astype(float)
    c = (edges[:-1] + edges[1:]) / 2
    w1 = np.cumsum(hist)
    w2 = hist.sum() - w1
    m1 = np.cumsum(hist * c) / np.maximum(w1, 1e-9)
    m2 = np.cumsum((hist * c)[::-1])[::-1] / np.maximum(w2, 1e-9)
    return c[np.argmax(w1 * w2 * (m1 - m2) ** 2)]


def load_scene(feat):
    a = feat["assets"]
    with rasterio.Env(**ENV):
        red, tr, crs = read_window(a["red"]["href"])
        green, _, _ = read_window(a["green"]["href"])
        blue, _, _ = read_window(a["blue"]["href"])
        scl, _, _ = read_window(a["scl"]["href"], out_shape=red.shape)
    cloudy = float(np.isin(scl, (3, 8, 9, 10)).mean())
    rgb = np.stack([red, green, blue], -1) / 10000.0
    return rgb, tr, crs, cloudy


def ncc_shift(template, image, mask):
    """Shift (drow, dcol) of the template inside image via *masked* normalised cross-correlation (only the dune
    pixels of the template count, so static ground around the barchan cannot anchor the match), sub-pixel refined."""
    th, tw = template.shape
    mt = template[mask]
    t = (mt - mt.mean()) / (mt.std() + 1e-9)
    H, Wd = image.shape
    corr = np.full((H - th + 1, Wd - tw + 1), -1.0)
    for r_ in range(corr.shape[0]):
        for c_ in range(corr.shape[1]):
            win = image[r_:r_ + th, c_:c_ + tw][mask]
            corr[r_, c_] = float(np.mean(t * (win - win.mean()) / (win.std() + 1e-9)))
    r, c = np.unravel_index(np.argmax(corr), corr.shape)
    peak = float(corr[r, c])

    def sub(axis_vals):
        y0, y1, y2 = axis_vals
        d = y0 - 2 * y1 + y2
        return 0.0 if d == 0 else 0.5 * (y0 - y2) / d

    dr = sub(corr[r - 1:r + 2, c]) if 0 < r < corr.shape[0] - 1 else 0.0
    dc = sub(corr[r, c - 1:c + 2]) if 0 < c < corr.shape[1] - 1 else 0.0
    # 'valid' correlation: offset (r, c) means the template sits at image[r:r+h, c:c+w]
    return r + dr, c + dc, peak


def outline(bright, row0, col0):
    mask = bright > otsu(bright)
    mask = ndimage.binary_opening(mask, structure=np.ones((5, 5)))
    lab, n = ndimage.label(mask)
    if n == 0 or lab[row0, col0] == 0:
        # dune centre not inside a component: take the largest component within 15 px of it
        best, bestd = 0, 1e9
        for i in range(1, n + 1):
            rr, cc = np.nonzero(lab == i)
            d = np.hypot(rr - row0, cc - col0).min()
            if d < bestd and len(rr) > 200:
                best, bestd = i, d
        if best == 0 or bestd > 15:
            return None
        comp = lab == best
    else:
        comp = lab == lab[row0, col0]
    return comp


def main():
    feats = search()
    print(f"{len(feats)} candidate scenes")
    ref = None
    rows = []
    for f in feats:
        date = f["properties"]["datetime"][:10]
        try:
            rgb, tr, crs, cloudy = load_scene(f)
        except Exception as e:
            print(f"  {date}: read error {type(e).__name__}")
            continue
        if cloudy > MAX_LOCAL_CLOUD:
            print(f"  {date}: local cloud {cloudy:.1%}, skipped")
            continue
        bright = rgb.mean(-1)
        px, py = transform("EPSG:4326", crs, [LON], [LAT])
        col0, row0 = (~tr) * (px[0], py[0])
        row0, col0 = int(round(row0)), int(round(col0))
        comp = outline(bright, row0, col0)
        if ref is None:
            if comp is None or comp.sum() < 800:        # need a clean outline (> 8 ha) to build the template
                print(f"  {date}: no clean dune outline, not usable as reference")
                continue
            sl = (slice(row0 - TEMPLATE_HALF, row0 + TEMPLATE_HALF), slice(col0 - TEMPLATE_HALF, col0 + TEMPLATE_HALF))
            tmask = ndimage.binary_dilation(comp, iterations=3)[sl]
            ref = dict(date=date, row0=row0, col0=col0, template=bright[sl], mask=tmask)
            drow = dcol = 0.0
            peak = 1.0
            print(f"  reference scene {date}: template {tmask.sum()} dune pixels")
        else:
            r0, c0 = ref["row0"] - TEMPLATE_HALF - SEARCH, ref["col0"] - TEMPLATE_HALF - SEARCH
            sub = bright[r0:r0 + 2 * (TEMPLATE_HALF + SEARCH), c0:c0 + 2 * (TEMPLATE_HALF + SEARCH)]
            r, c, peak = ncc_shift(ref["template"], sub, ref["mask"])
            drow, dcol = r - SEARCH, c - SEARCH          # pixels the dune moved since the reference scene
        area_ha = round(float(comp.sum()) * 100 / 1e4, 2) if comp is not None else np.nan
        rows.append(dict(date=date, scene=f["id"], tile_cloud_pct=round(f["properties"]["eo:cloud_cover"], 2),
                         local_cloud_pct=round(cloudy * 100, 2), ncc_peak=round(peak, 3),
                         shift_east_m=round(dcol * 10, 1), shift_north_m=round(-drow * 10, 1),
                         area_ha=area_ha, _comp=comp, _rgb=rgb, _tr=tr))
        print(f"  {date}: shift E {dcol * 10:6.1f} m, N {-drow * 10:6.1f} m, ncc {peak:.2f}, area {area_ha} ha")
    rows = [r for r in rows if r["ncc_peak"] >= 0.5]       # drop scenes where the dune was not recognised
    if len(rows) < 4:
        sys.exit("not enough usable scenes")

    t0 = datetime.fromisoformat(rows[0]["date"])
    t = np.array([(datetime.fromisoformat(r["date"]) - t0).days / 365.25 for r in rows])
    ex = np.array([r["shift_east_m"] for r in rows]); ny = np.array([r["shift_north_m"] for r in rows])
    vx, bx = np.polyfit(t, ex, 1); vy, by = np.polyfit(t, ny, 1)
    speed = float(np.hypot(vx, vy)); bearing = float((np.degrees(np.arctan2(vx, vy)) + 360) % 360)
    ux, uy = (vx / speed, vy / speed) if speed > 0 else (0.0, 1.0)
    resid = np.hypot(ex - (vx * t + bx), ny - (vy * t + by))
    for r, p in zip(rows, ex * ux + ny * uy):
        r["shift_along_drift_m"] = round(float(p), 1)
    # 1-sigma uncertainty of the fitted speed from the scatter about the line
    n = len(t)
    se_v = float(resid.std() / np.sqrt(((t - t.mean()) ** 2).sum())) if n > 2 else float("nan")

    # cut-outs
    for r in rows:
        img = np.clip((r["_rgb"] - 0.02) / 0.33, 0, 1)
        if r["_comp"] is not None:
            edge = r["_comp"] & ~ndimage.binary_erosion(r["_comp"])
            img[edge] = [0.78, 0.06, 0.18]
        Image.fromarray((img * 255).astype(np.uint8)).resize((img.shape[1] * 3, img.shape[0] * 3), Image.NEAREST) \
            .save(os.path.join(IMG_DIR, f"{r['date']}.png"))
        for k in ("_comp", "_rgb", "_tr"):
            r.pop(k)

    summary = {"site": "Médano Blanco (Sechura)", "lat": LAT, "lon": LON, "crs": "EPSG:32717", "n_scenes": len(rows),
               "first": rows[0]["date"], "last": rows[-1]["date"], "speed_m_per_yr": round(speed, 2),
               "speed_east_m_per_yr": round(float(vx), 2), "speed_north_m_per_yr": round(float(vy), 2),
               "bearing_deg": round(bearing, 1), "fit_rms_m": round(float(resid.std()), 1),
               "speed_sigma_m_per_yr": round(se_v, 2), "reference_scene": ref["date"],
               "method": "Sentinel-2 L2A 10 m; masked normalised cross-correlation of the dune pixels (reference "
                         "scene outline, dilated 30 m) with sub-pixel peak; linear fit of shift vs time",
               "generated": datetime.now(timezone.utc).strftime("%Y-%m-%d")}
    with open(os.path.join(OUT_DIR, "medano_blanco_migration.csv"), "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader(); w.writerows(rows)
    with open(os.path.join(OUT_DIR, "medano_blanco_migration.json"), "w", encoding="utf-8") as fh:
        json.dump(summary, fh, indent=2, ensure_ascii=False)
    print(json.dumps(summary, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
