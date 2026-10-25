"""Scenario helpers for GeoTwin. Illustrative sensitivity analysis only,
not physically validated impact estimates."""
from src.risk_scoring import compute_scores


def rank_change_table(base, scen):
    """Compare baseline and scenario. rank_change > 0 means the cell moved UP in priority."""
    t = base[["cell_id", "priority_score", "priority_rank"]].merge(
        scen[["cell_id", "priority_score", "priority_rank"]],
        on="cell_id", suffixes=("_base", "_scenario"))
    t["score_change"] = t["priority_score_scenario"] - t["priority_score_base"]
    t["rank_change"] = t["priority_rank_base"] - t["priority_rank_scenario"]
    return t


def weight_scenario(df, w_comp, w_prio):
    return compute_scores(df, w_comp=w_comp, w_prio=w_prio)


def green_scenario(df, cell_ids, add_frac):
    """Hypothetically add `add_frac` (0-1) of green cover to the given cells."""
    d = df.copy()
    m = d["cell_id"].isin(list(cell_ids))
    d.loc[m, "green_frac"] = (d.loc[m, "green_frac"] + add_frac).clip(upper=1.0)
    return compute_scores(d)
