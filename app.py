"""GeoTwin dashboard (Phase 4). Run: streamlit run app.py"""
import json
from pathlib import Path

import folium
import geopandas as gpd
import pandas as pd
import plotly.express as px
import streamlit as st
from branca.colormap import linear
from folium.features import GeoJsonTooltip
from streamlit_folium import st_folium

st.set_page_config(page_title="GeoTwin", layout="wide")
DATA = Path("data/sample")

LAYERS = {
    "Priority score": "priority_score",
    "Compound index (heat + flood)": "compound_index",
    "Heat proxy (built-up)": "heat_proxy",
    "Flood susceptibility": "flood_susceptibility",
    "Exposure proxy (buildings)": "exposure_proxy",
}
INPUTS = {
    "building_density_km2": "Buildings per km2",
    "green_frac": "Green cover (fraction)",
    "water_frac": "Water cover (fraction)",
    "elev_mean_m": "Mean elevation (m)",
    "water_dist_m": "Distance to water (m)",
    "elev_range_m": "Elevation range in cell (m)",
}


@st.cache_data
def load():
    if not (DATA / "risk_scores.csv").exists():
        return None, None, None
    scores = pd.read_csv(DATA / "risk_scores.csv")
    geo = gpd.read_file(DATA / "grid.geojson")[["cell_id", "geometry"]]
    gdf = geo.merge(scores, on="cell_id")
    src = json.loads((DATA / "sources.json").read_text())
    return gdf, scores, src


gdf, scores, src = load()
if gdf is None:
    st.error("Scores not found. Run this in the terminal first: python -m src.risk_scoring")
    st.stop()

st.title("GeoTwin: compound heat and flood-risk prioritization")
st.caption(
    "Velachery-Pallikaranai, Chennai | 500 m cells | Decision-support prototype, "
    "not a flood warning or forecast. Heat is a built-up proxy, not measured temperature."
)

# ---- Sidebar ----
layer_label = st.sidebar.selectbox("Map layer", list(LAYERS))
col = LAYERS[layer_label]
top_n = st.sidebar.slider("Rows in ranked table", 5, 50, 15)
ranked = scores.sort_values("priority_rank")
rank_map = dict(zip(scores["cell_id"], scores["priority_rank"]))
sel = st.sidebar.selectbox(
    "Inspect cell (sorted by priority rank)",
    ranked["cell_id"].tolist(),
    format_func=lambda c: f"{c} (rank {int(rank_map[c])})",
)

# ---- Map + explanation ----
left, right = st.columns([3, 2])

with left:
    map_cols = ["cell_id", "priority_rank", "priority_score", "compound_index",
                "heat_proxy", "flood_susceptibility", "exposure_proxy"]
    mg = gdf[map_cols + ["geometry"]].copy()
    mg[map_cols[2:]] = mg[map_cols[2:]].round(3)
    minx, miny, maxx, maxy = mg.total_bounds
    m = folium.Map(location=[(miny + maxy) / 2, (minx + maxx) / 2],
                   zoom_start=13, tiles="CartoDB positron")
    cmap = linear.YlOrRd_09.scale(float(mg[col].min()), float(mg[col].max()))
    cmap.caption = layer_label

    def style(feature, col=col):
        return {"fillColor": cmap(feature["properties"][col]), "color": "#444",
                "weight": 0.4, "fillOpacity": 0.7}

    folium.GeoJson(
        mg, style_function=style,
        tooltip=GeoJsonTooltip(
            fields=["cell_id", "priority_rank", "priority_score", "compound_index",
                    "heat_proxy", "flood_susceptibility"],
            aliases=["Cell", "Priority rank", "Priority score", "Compound index",
                     "Heat proxy", "Flood susceptibility"]),
    ).add_to(m)
    folium.GeoJson(
        mg[mg["cell_id"] == sel],
        style_function=lambda f: {"fillOpacity": 0, "color": "#0044ff", "weight": 3},
    ).add_to(m)
    cmap.add_to(m)
    st_folium(m, height=520, use_container_width=True, returned_objects=[])

with right:
    r = scores[scores["cell_id"] == sel].iloc[0]
    st.subheader(f"Cell {sel}")
    c1, c2, c3 = st.columns(3)
    c1.metric("Priority rank", f"{int(r['priority_rank'])} / {len(scores)}")
    c2.metric("Compound index", f"{r['compound_index']:.2f}")
    c3.metric("In top 10% (stability)", f"{r['top_group_stability']:.0%}")
    st.caption("Stability = share of 200 random weight perturbations in which this cell stays "
               "in the top 10% of priority scores. Low means the rank depends on assumed weights.")

    contrib = pd.DataFrame({
        "Component": ["Heat proxy", "Flood susceptibility", "Heat x flood interaction"],
        "Contribution": [r["c_heat"], r["c_flood"], r["c_interaction"]],
    })
    fig = px.bar(contrib, x="Component", y="Contribution",
                 title="What drives this cell's compound index")
    st.plotly_chart(fig, use_container_width=True)

    inputs = pd.DataFrame({"Input": list(INPUTS.values()),
                           "Value": [round(float(r[k]), 3) for k in INPUTS]})
    st.table(inputs)

# ---- Ranked table ----
st.subheader("Ranked cells")
cols = ["cell_id", "priority_rank", "priority_score", "compound_index", "heat_proxy",
        "flood_susceptibility", "exposure_proxy", "top_group_stability"]
st.dataframe(ranked[cols].head(top_n).round(3), hide_index=True, use_container_width=True)
st.download_button("Download full ranking (CSV)", ranked[cols].round(3).to_csv(index=False),
                   file_name="geotwin_ranking.csv", mime="text/csv")

# ---- Provenance and limitations ----
with st.expander("Data sources and limitations"):
    st.json(src)
    st.markdown(Path("docs/limitations.md").read_text())
