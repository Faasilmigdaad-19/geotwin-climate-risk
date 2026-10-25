import pandas as pd

from src.risk_scoring import compute_scores
from src.scenarios import green_scenario, rank_change_table, weight_scenario
from src.risk_scoring import W_COMPOUND, W_PRIORITY


def sample_df():
    # Test fixture only (not real data).
    return pd.DataFrame({
        "cell_id": ["a", "b", "c"],
        "building_density_km2": [2000, 1000, 0],
        "building_count": [500, 250, 0],
        "green_frac": [0.0, 0.1, 0.5],
        "water_frac": [0.0, 0.05, 0.0],
        "elev_mean_m": [1.0, 8.0, 15.0],
        "water_dist_m": [50.0, 700.0, 1500.0],
        "elev_range_m": [1.0, 8.0, 15.0],
    })


def test_same_weights_give_no_rank_change():
    df = sample_df()
    t = rank_change_table(compute_scores(df), weight_scenario(df, W_COMPOUND, W_PRIORITY))
    assert (t["rank_change"] == 0).all()


def test_green_cover_lowers_heat_proxy_of_target_cell():
    df = sample_df()
    base = compute_scores(df)
    scen = green_scenario(df, ["a"], 0.3)
    assert scen.loc[0, "heat_proxy"] < base.loc[0, "heat_proxy"]
    assert scen.loc[0, "flood_susceptibility"] == base.loc[0, "flood_susceptibility"]
