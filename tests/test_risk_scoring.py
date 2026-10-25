import numpy as np
import pandas as pd

from src.risk_scoring import (W_COMPOUND, W_FLOOD, W_HEAT, W_PRIORITY,
                              compute_scores, rank_stability)


def sample_df():
    # Test fixture only (not real data): high-risk, medium, low-risk cell.
    return pd.DataFrame({
        "building_density_km2": [2000, 1000, 0],
        "building_count": [500, 250, 0],
        "green_frac": [0.0, 0.1, 0.5],
        "water_frac": [0.0, 0.05, 0.0],
        "elev_mean_m": [1.0, 8.0, 15.0],
        "water_dist_m": [50.0, 700.0, 1500.0],
        "elev_range_m": [1.0, 8.0, 15.0],
    })


def test_weights_sum_to_one():
    for w in (W_HEAT, W_FLOOD, W_COMPOUND, W_PRIORITY):
        assert abs(sum(w.values()) - 1.0) < 1e-9


def test_scores_in_range_and_ordered():
    out = compute_scores(sample_df())
    assert out["compound_index"].between(0, 1).all()
    assert out["priority_score"].between(0, 1).all()
    assert out.loc[0, "compound_index"] > out.loc[2, "compound_index"]
    assert out.loc[0, "priority_rank"] == 1


def test_missing_water_distance_does_not_give_nan():
    df = sample_df()
    df.loc[1, "water_dist_m"] = np.nan
    out = compute_scores(df)
    assert out["compound_index"].notna().all()


def test_stability_in_range_and_repeatable():
    df = sample_df()
    s1 = rank_stability(df, n_runs=20)
    s2 = rank_stability(df, n_runs=20)
    assert s1.between(0, 1).all()
    assert (s1 == s2).all()
