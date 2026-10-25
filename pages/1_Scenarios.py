"""GeoTwin scenario comparison (Phase 5)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd
import plotly.express as px
import streamlit as st

from src.risk_scoring import W_COMPOUND, W_PRIORITY, compute_scores
from src.scenarios import green_scenario, rank_change_table, weight_scenario

st.set_page_config(page_title="GeoTwin scenarios", layout="wide")
DATA = Path("data/sample")


@st.cache_data
def load():
    return pd.read_csv(DATA / "grid_features.csv")


feat = load()
base = compute_scores(feat)

st.title("Scenario comparison")
st.warning(
    "Illustrative sensitivity analysis only. These are NOT physically validated impact "
    "estimates and not predictions. Results show how rankings change under stated assumptions."
)

mode = st.radio("Scenario type",
                ["Change weights", "Add green cover (hypothetical)"], horizontal=True)

targets = []
if mode == "Change weights":
    st.markdown("Adjust how much each part counts. Values are rescaled to sum to 1.")
    c1, c2, c3 = st.columns(3)
    h = c1.slider("Heat weight", 0.0, 1.0, float(W_COMPOUND["heat"]), 0.05)
    f = c2.slider("Flood weight", 0.0, 1.0, float(W_COMPOUND["flood"]), 0.05)
    i = c3.slider("Heat x flood interaction weight", 0.0, 1.0, float(W_COMPOUND["interaction"]), 0.05)
    p = st.slider("Weight of compound index in priority score (rest = exposure)",
                  0.3, 1.0, float(W_PRIORITY["compound"]), 0.05)
    total = h + f + i
    if total == 0:
        st.error("At least one weight must be above zero.")
        st.stop()
    w_comp = {"heat": h / total, "flood": f / total, "interaction": i / total}
    w_prio = {"compound": p, "exposure": 1 - p}
    scen = weight_scenario(feat, w_comp, w_prio)
    changed_inputs = (f"Compound weights: heat {w_comp['heat']:.2f}, flood {w_comp['flood']:.2f}, "
                      f"interaction {w_comp['interaction']:.2f}. Priority: compound {p:.2f}, "
                      f"exposure {1 - p:.2f}. (Baseline: 0.30 / 0.40 / 0.30 and 0.70 / 0.30.)")
    assumptions = ["Only the weights change. No input data changes.",
                   "The baseline weights are themselves unvalidated expert assumptions."]
else:
    c1, c2 = st.columns(2)
    n = c1.slider("Apply to the top N priority cells", 1, 30, 10)
    add_pct = c2.slider("Add green cover (percentage points of cell area)", 5, 50, 20, 5)
    targets = base.nsmallest(n, "priority_rank")["cell_id"].tolist()
    scen = green_scenario(feat, targets, add_pct / 100)
    changed_inputs = (f"green_frac increased by {add_pct} percentage points (capped at 100 percent) "
                      f"in the {n} highest-priority cells: {', '.join(targets[:10])}"
                      f"{' ...' if n > 10 else ''}.")
    assumptions = [
        "Green cover affects only the heat proxy (through the no-green term).",
        "Flood susceptibility is unchanged: no physical effect of green cover on flooding is modelled.",
        "Whether this much green cover can actually be added in those cells is not checked.",
    ]

t = rank_change_table(base, scen)

st.subheader("Result")
m1, m2, m3 = st.columns(3)
m1.metric("Cells whose rank changed", int((t["rank_change"] != 0).sum()))
if targets:
    m2.metric("Avg priority score change (targeted cells)",
              f"{t[t['cell_id'].isin(targets)]['score_change'].mean():.3f}")
m3.metric("Largest rank move", int(t["rank_change"].abs().max()))

top10 = base.nsmallest(10, "priority_rank")["cell_id"]
cmp = t[t["cell_id"].isin(top10)][["cell_id", "priority_score_base", "priority_score_scenario"]]
cmp = cmp.melt(id_vars="cell_id", var_name="Scenario", value_name="Priority score")
cmp["Scenario"] = cmp["Scenario"].map({"priority_score_base": "Baseline",
                                       "priority_score_scenario": "Scenario"})
st.plotly_chart(px.bar(cmp, x="cell_id", y="Priority score", color="Scenario", barmode="group",
                       title="Baseline top-10 priority cells: baseline vs scenario"),
                use_container_width=True)

st.subheader("Biggest rank changes (positive = moved up in priority)")
movers = t.reindex(t["rank_change"].abs().sort_values(ascending=False).index).head(15)
st.dataframe(movers.round(3), hide_index=True, use_container_width=True)
st.download_button("Download full comparison (CSV)", t.round(4).to_csv(index=False),
                   file_name="geotwin_scenario_comparison.csv", mime="text/csv")

st.subheader("Inputs changed")
st.write(changed_inputs)
st.subheader("Assumptions and limits")
for a in assumptions:
    st.markdown(f"- {a}")
st.markdown("- Result type: **illustrative sensitivity analysis**, not a validated impact estimate.")
