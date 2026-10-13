"""Comparable fixture and player-GW diagnostics from aligned historical arrays."""
import numpy as np
import pandas as pd
from scipy.stats import spearmanr
from sklearn.metrics import ndcg_score
from fpl_model import candidate_mask, metrics


def evaluate(rows, x, prediction):
    if not rows.index.equals(x.index) or len(rows) != len(prediction):
        raise ValueError("Ordered features, rows and predictions must align")
    p = np.asarray(prediction, dtype=float)
    if not np.isfinite(p).all():
        raise ValueError("Predictions must be finite")
    pool = candidate_mask(x).to_numpy()
    if not pool.any():
        raise ValueError("No pre-deadline candidate records")
    d = rows[["season", "GW", "element", "pos", "points_core", "minutes"]].copy()
    d["prediction"] = p
    d["candidate"] = pool
    # Both fixtures of a double contribute to the same decision. The candidate
    # predicate is deadline-based and must agree within that player's GW.
    groups = d.groupby(["season", "GW", "element"], sort=True)
    if (groups.candidate.nunique() != 1).any():
        raise ValueError("Candidate membership differs within a player-GW")
    g = groups.agg(actual=("points_core", "sum"),
                   prediction=("prediction", "sum"),
                   candidate=("candidate", "first"))
    c = g[g.candidate]
    ranking = []
    for _, week in c.groupby(level=[0, 1]):
        y = week.actual.to_numpy(); pp = week.prediction.to_numpy()
        if len(y) < 2 or np.ptp(y) == 0:
            continue
        rho = float(spearmanr(y, pp).statistic) if np.ptp(pp) else 0.
        gains = np.maximum(y, 0)
        ndcg = float(ndcg_score(gains[None, :], pp[None, :], k=min(10, len(y))))
        ranking.append((rho, ndcg))
    result = {"candidate_fixture": metrics(d.loc[pool, "points_core"], p[pool]),
              "all_fixture": metrics(d.points_core, p),
              "candidate_player_gw": metrics(c.actual, c.prediction),
              "all_player_gw": metrics(g.actual, g.prediction),
              "ranking_weeks": len(ranking),
              "mean_within_gw_spearman": float(np.mean([v[0] for v in ranking])) if ranking else None,
              "mean_within_gw_ndcg10": float(np.mean([v[1] for v in ranking])) if ranking else None,
              "position_candidate_fixture": {}}
    for pos in range(1, 5):
        mask = pool & (d.pos.to_numpy() == pos)
        if mask.any():
            result["position_candidate_fixture"][str(pos)] = metrics(d.loc[mask, "points_core"], p[mask])
    return result
