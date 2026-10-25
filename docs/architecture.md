# Architecture

    OpenStreetMap (Overpass)      AWS Terrain Tiles
            |                            |
            +------------+---------------+
                         v
               src/data_loader.py
        (500 m grid + features per cell)
                         v
          data/sample/grid_features.csv, grid.geojson, sources.json
                         v
               src/risk_scoring.py
   (normalize -> heat proxy, flood susceptibility,
    exposure -> compound index -> priority -> stability)
                         v
          data/sample/risk_scores.csv
              |                        |
              v                        v
          app.py                 pages/1_Scenarios.py
   (map, ranking, explanation)   (uses src/scenarios.py to
                                  recompute under new assumptions)

Design choices
- Single Python application (Streamlit). No database or backend service.
- Plain CSV/GeoJSON files in data/sample so the app runs offline after cloning.
- Scoring is a transparent weighted index, because no reliable flood labels were available for supervised learning.
- Stability analysis shows sensitivity to weights, not to input-data errors.
