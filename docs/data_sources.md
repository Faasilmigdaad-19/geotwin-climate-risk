# Data sources
- Elevation: AWS Terrain Tiles (Terrarium), zoom 14. Derived from SRTM and other open DEMs. About 10 m pixels. Vertical accuracy is limited, so small negative values are approximate.
- Water, green cover, buildings: OpenStreetMap via Overpass API (ODbL licence). Only mapped ways are used. Relations (large multipolygon lakes and marshes) are skipped, so water cover is likely underestimated.
- Grid: 500 m cells, UTM 44N (EPSG:32644), Velachery-Pallikaranai, Chennai. 324 cells.
- Heat: no satellite land-surface temperature yet. A built-up heat proxy will be derived from building density and green/water cover.
- Population/exposure: not yet included; no verified dataset obtained.
Retrieval date is stored in data/sample/sources.json.
