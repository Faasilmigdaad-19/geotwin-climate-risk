"""Transparent baseline compound heat-flood index for GeoTwin.

All weights are documented expert assumptions (NOT calibrated against observed
floods or measured temperatures). Heat is a built-up PROXY, not land-surface temperature.
Run:  python -m src.risk_scoring
"""
import numpy as np
import pandas as pd

W_HEAT = {"built": 0.5, "no_green": 0.3, "no_water": 0.2}
W_FLOOD = {"low_elev": 0.40, "near_water": 0.25, "flat": 0.15, "impervious": 0.20}
W_COMPOUND = {"heat": 0.3, "flood": 0.4, "interaction": 0.3}
W_PRIORITY = {"compound": 0.7, "exposure": 0.3}


def robust_norm(s, lo=5, hi=95):
    """Scale to 0-1 using the 5th-95th percentile range (limits outlier effect)."""
    s = pd.Series(s, dtype=float)
    a, b = np.nanpercentile(s, [lo, hi])
    if b == a:
        return pd.Series(0.0, index=s.index)
    return ((s - a) / (b - a)).clip(0, 1)


def compute_scores(df, w_heat=None, w_flood=None, w_comp=None, w_prio=None):
    w_heat = w_heat or W_HEAT
    w_flood = w_flood or W_FLOOD
    w_comp = w_comp or W_COMPOUND
    w_prio = w_prio or W_PRIORITY
    d = df.copy()
    # Missing distance-to-water: treat as farthest (no water mapped nearby).
    d["water_dist_m"] = d["water_dist_m"].fillna(d["water_dist_m"].max())

    n_built = robust_norm(d["building_density_km2"])
    n_green = robust_norm(d["green_frac"])
    n_water = robust_norm(d["water_frac"])
    n_elev = robust_norm(d["elev_mean_m"])
    n_wdist = robust_norm(d["water_dist_m"])
    n_range = robust_norm(d["elev_range_m"])

    d["heat_proxy"] = (w_heat["built"] * n_built
                       + w_heat["no_green"] * (1 - n_green)
                       + w_heat["no_water"] * (1 - n_water))
    d["flood_susceptibility"] = (w_flood["low_elev"] * (1 - n_elev)
                                 + w_flood["near_water"] * (1 - n_wdist)
                                 + w_flood["flat"] * (1 - n_range)
                                 + w_flood["impervious"] * n_built)
    d["exposure_proxy"] = robust_norm(d["building_count"])

    d["c_heat"] = w_comp["heat"] * d["heat_proxy"]
    d["c_flood"] = w_comp["flood"] * d["flood_susceptibility"]
    d["c_interaction"] = w_comp["interaction"] * d["heat_proxy"] * d["flood_susceptibility"]
    d["compound_index"] = d["c_heat"] + d["c_flood"] + d["c_interaction"]
    d["priority_score"] = (w_prio["compound"] * d["compound_index"]
                           + w_prio["exposure"] * d["exposure_proxy"])
    d["priority_rank"] = d["priority_score"].rank(ascending=False, method="min").astype(int)
    return d


def _perturb(weights, rng, sigma):
    vals = np.array(list(weights.values())) * rng.lognormal(0, sigma, len(weights))
    vals = vals / vals.sum()
    return dict(zip(weights.keys(), vals))


def rank_stability(df, n_runs=200, top_frac=0.10, sigma=0.3, seed=42):
    """Share of random weight perturbations in which each cell stays in the top group."""
    rng = np.random.default_rng(seed)
    k = max(1, int(round(len(df) * top_frac)))
    hits = np.zeros(len(df))
    for _ in range(n_runs):
        out = compute_scores(
            df,
            _perturb(W_HEAT, rng, sigma),
            _perturb(W_FLOOD, rng, sigma),
            _perturb(W_COMPOUND, rng, sigma),
            _perturb(W_PRIORITY, rng, sigma),
        )
        top = np.argsort(-out["priority_score"].values)[:k]
        hits[top] += 1
    return pd.Series(hits / n_runs, index=df.index)


def main():
    df = pd.read_csv("data/sample/grid_features.csv")
    out = compute_scores(df)
    out["top_group_stability"] = rank_stability(df).round(2)
    out.to_csv("data/sample/risk_scores.csv", index=False)
    cols = ["cell_id", "lat", "lon", "heat_proxy", "flood_susceptibility",
            "compound_index", "priority_score", "top_group_stability"]
    print(out.sort_values("priority_rank").head(10)[cols].round(3).to_string(index=False))
    print("\nSaved data/sample/risk_scores.csv")


if __name__ == "__main__":
    main()
