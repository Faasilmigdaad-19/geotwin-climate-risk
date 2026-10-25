import pandas as pd


def test_grid_features_valid():
    d = pd.read_csv("data/sample/grid_features.csv")
    assert len(d) > 100
    for col in ["elev_mean_m", "water_frac", "green_frac", "building_density_km2"]:
        assert col in d.columns
        assert d[col].notna().all()
    assert d["water_frac"].between(0, 1).all()
