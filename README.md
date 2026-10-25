# GeoTwin

Explainable AI and GIS prototype for compound urban heat and flood-risk prioritization.
Study area: Velachery-Pallikaranai, Chennai, India (500 m grid, 324 cells).

Built for Hack for Social Cause (HSC), Viksit Bharat Young Leaders Dialogue 2027. Theme: AI, GIS & Emerging Technologies.

**This is a decision-support prototype. It is not a flood warning, forecast or engineering assessment.**

## What it does
- Maps a heat proxy, a flood-susceptibility score and an exposure proxy on a 500 m grid.
- Combines them into a compound index and a priority ranking of cells.
- Explains each cell's score (which factors contribute) and shows how stable its rank is when the weights change.
- Compares scenarios (changed weights, hypothetical added green cover) as illustrative sensitivity analysis.
- Shows data sources and limitations inside the app.

## Quick start (Linux)
    git clone https://github.com/Faasilmigdaad-19/geotwin-climate-risk.git
    cd geotwin-climate-risk
    python3 -m venv .venv
    source .venv/bin/activate
    pip install -r requirements.txt
    streamlit run app.py

Run the tests:

    pytest -q

Optional: rebuild the data (needs internet) and the scores:

    python -m src.data_loader
    python -m src.risk_scoring

Sample data is already included in data/sample, so the app runs without downloading anything.

## Project structure
    app.py                 Streamlit dashboard (map, ranking, explanation panel)
    pages/1_Scenarios.py   Scenario comparison page
    src/data_loader.py     Builds grid and features (OpenStreetMap, terrain tiles)
    src/risk_scoring.py    Heat proxy, flood susceptibility, compound index, stability
    src/scenarios.py       Scenario helpers
    tests/                 Unit tests
    data/sample/           Sample data and scores
    docs/                  Architecture, methodology, data sources, limitations, AI usage

## Method in brief
- Heat proxy = built-up density, low green cover, low water cover (NOT measured temperature).
- Flood susceptibility = low elevation, closeness to water, flat terrain, built-up density (relative score, NOT a flood probability).
- Compound index C = 0.3H + 0.4F + 0.3HF. Priority = 0.7C + 0.3 exposure proxy.
- Stability = share of 200 random weight perturbations in which a cell stays in the top 10 percent.
Details: docs/methodology.md

## Data
- Elevation: AWS Terrain Tiles (Terrarium).
- Water, green cover, buildings: OpenStreetMap contributors (ODbL), via Overpass API.
See docs/data_sources.md.

## Limitations
Weights are expert assumptions and are not calibrated. No validation against observed floods has been done. Heat is a proxy, OpenStreetMap water is incomplete, and exposure is building count, not population. See docs/limitations.md.

## AI disclosure
AI assistance (Claude by Anthropic) was used for planning, code drafting and documentation. See docs/ai_usage.md.

## License
MIT. See LICENSE.
