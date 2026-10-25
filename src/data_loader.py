"""Builds the 500 m grid and real feature data for the GeoTwin study area.
Sources: OpenStreetMap (Overpass API), AWS Terrain Tiles (Terrarium).
Run:  python -m src.data_loader
"""
import io
import json
import time
from datetime import date
from pathlib import Path

import geopandas as gpd
import numpy as np
import requests
from PIL import Image
from pyproj import Transformer
from shapely.geometry import LineString, Polygon, box

BBOX = (80.18, 12.92, 80.26, 13.00)  # west, south, east, north (Velachery-Pallikaranai)
CRS_M = "EPSG:32644"                 # UTM 44N, metres
CELL = 500                           # cell size in metres
OUT = Path("data/sample")
RAW = Path("data/raw")
HEADERS = {"User-Agent": "geotwin-student-project"}
OVERPASS_URLS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
]
TILE_URL = "https://s3.amazonaws.com/elevation-tiles-prod/terrarium/{z}/{x}/{y}.png"


def make_grid():
    w, s, e, n = BBOX
    area = gpd.GeoSeries([box(w, s, e, n)], crs="EPSG:4326").to_crs(CRS_M)
    x0, y0, x1, y1 = area.total_bounds
    cells, ids = [], []
    for i, x in enumerate(np.arange(x0, x1, CELL)):
        for j, y in enumerate(np.arange(y0, y1, CELL)):
            cells.append(box(x, y, x + CELL, y + CELL))
            ids.append(f"c{i:02d}_{j:02d}")
    return gpd.GeoDataFrame({"cell_id": ids}, geometry=cells, crs=CRS_M)


def overpass(name, body, out="geom"):
    """Run an Overpass query. Results are cached in data/raw so reruns are fast."""
    RAW.mkdir(parents=True, exist_ok=True)
    cache = RAW / (name + ".json")
    if cache.exists():
        return json.loads(cache.read_text())
    w, s, e, n = BBOX
    body = body.replace("{b}", f"{s},{w},{n},{e}")
    query = "[out:json][timeout:180];(" + body + ");out " + out + ";"
    last_err = None
    for url in OVERPASS_URLS:
        try:
            r = requests.post(url, data={"data": query}, headers=HEADERS, timeout=240)
            r.raise_for_status()
            elements = r.json()["elements"]
            cache.write_text(json.dumps(elements))
            time.sleep(3)
            return elements
        except Exception as err:  # try the next mirror
            last_err = err
    raise RuntimeError("Overpass failed for " + name + ": " + str(last_err))


def ways_to_gdf(elements):
    geoms = []
    for el in elements:
        pts = [(p["lon"], p["lat"]) for p in el.get("geometry", [])]
        if len(pts) < 2:
            continue
        if len(pts) >= 4 and pts[0] == pts[-1]:
            geoms.append(Polygon(pts).buffer(0))
        else:
            geoms.append(LineString(pts))
    return gpd.GeoDataFrame(geometry=geoms, crs="EPSG:4326").to_crs(CRS_M)


def area_fraction(grid, gdf):
    polys = gdf[gdf.geom_type.isin(["Polygon", "MultiPolygon"])]
    if polys.empty:
        return np.zeros(len(grid))
    union = polys.geometry.union_all()
    return grid.geometry.intersection(union).area.values / grid.geometry.area.values


def elevation_samples(lons, lats, z=14):
    n = 2 ** z
    px = (lons + 180) / 360 * n * 256
    py = (1 - np.arcsinh(np.tan(np.radians(lats))) / np.pi) / 2 * n * 256
    tx0, tx1 = int(px.min() // 256), int(px.max() // 256)
    ty0, ty1 = int(py.min() // 256), int(py.max() // 256)
    mosaic = np.zeros(((ty1 - ty0 + 1) * 256, (tx1 - tx0 + 1) * 256))
    for tx in range(tx0, tx1 + 1):
        for ty in range(ty0, ty1 + 1):
            r = requests.get(TILE_URL.format(z=z, x=tx, y=ty), headers=HEADERS, timeout=60)
            r.raise_for_status()
            a = np.array(Image.open(io.BytesIO(r.content)).convert("RGB"), dtype=float)
            elev = a[..., 0] * 256 + a[..., 1] + a[..., 2] / 256 - 32768
            mosaic[(ty - ty0) * 256:(ty - ty0 + 1) * 256,
                   (tx - tx0) * 256:(tx - tx0 + 1) * 256] = elev
    ix = (px - tx0 * 256).astype(int)
    iy = (py - ty0 * 256).astype(int)
    return mosaic[iy, ix]


def build():
    OUT.mkdir(parents=True, exist_ok=True)
    grid = make_grid()
    print(f"Grid: {len(grid)} cells of {CELL} m")

    # --- Elevation: 5x5 sample points per cell ---
    offs = (np.arange(5) + 0.5) * CELL / 5
    xs, ys = [], []
    for g in grid.geometry:
        x0, y0, _, _ = g.bounds
        for dx in offs:
            for dy in offs:
                xs.append(x0 + dx)
                ys.append(y0 + dy)
    to_ll = Transformer.from_crs(CRS_M, "EPSG:4326", always_xy=True)
    lons, lats = to_ll.transform(np.array(xs), np.array(ys))
    elev = elevation_samples(np.array(lons), np.array(lats)).reshape(len(grid), 25)
    grid["elev_mean_m"] = elev.mean(axis=1).round(2)
    grid["elev_min_m"] = elev.min(axis=1).round(2)
    grid["elev_range_m"] = (elev.max(axis=1) - elev.min(axis=1)).round(2)
    print("Elevation done")

    # --- Water ---
    water = ways_to_gdf(overpass(
        "water",
        'way["natural"~"water|wetland"]({b});'
        'way["waterway"~"river|canal|stream|drain"]({b});'))
    grid["water_frac"] = area_fraction(grid, water).round(4)
    if len(water):
        grid["water_dist_m"] = grid.geometry.centroid.distance(water.geometry.union_all()).round(0)
    else:
        grid["water_dist_m"] = np.nan
    print(f"Water done ({len(water)} features)")

    # --- Green cover ---
    green = ways_to_gdf(overpass(
        "green",
        'way["landuse"~"grass|forest|meadow|recreation_ground"]({b});'
        'way["natural"~"wood|scrub|grassland"]({b});'
        'way["leisure"~"park|garden"]({b});'))
    grid["green_frac"] = area_fraction(grid, green).round(4)
    print(f"Green done ({len(green)} features)")

    # --- Buildings (centre points, counted per cell) ---
    els = overpass("buildings", 'way["building"]({b});', out="center")
    pts = gpd.GeoDataFrame(
        geometry=gpd.points_from_xy([e["center"]["lon"] for e in els],
                                    [e["center"]["lat"] for e in els]),
        crs="EPSG:4326").to_crs(CRS_M)
    joined = gpd.sjoin(pts, grid[["cell_id", "geometry"]], predicate="within")
    counts = joined.groupby("cell_id").size()
    grid["building_count"] = grid["cell_id"].map(counts).fillna(0).astype(int)
    grid["building_density_km2"] = (grid["building_count"] / (CELL * CELL / 1e6)).round(1)
    print(f"Buildings done ({len(els)} mapped)")

    # --- Save ---
    c = grid.geometry.centroid.to_crs("EPSG:4326")
    grid["lon"], grid["lat"] = c.x.round(5), c.y.round(5)
    grid.drop(columns="geometry").to_csv(OUT / "grid_features.csv", index=False)
    grid.to_crs("EPSG:4326").to_file(OUT / "grid.geojson", driver="GeoJSON")
    (OUT / "sources.json").write_text(json.dumps({
        "retrieved": date.today().isoformat(),
        "bbox_wsen": BBOX, "cell_m": CELL, "crs": CRS_M,
        "elevation": "AWS Terrain Tiles (Terrarium), zoom 14, ~10 m pixels",
        "water_green_buildings": "OpenStreetMap via Overpass API (ODbL). Ways only; relations skipped.",
    }, indent=2))
    print("Saved to data/sample/")


if __name__ == "__main__":
    build()
