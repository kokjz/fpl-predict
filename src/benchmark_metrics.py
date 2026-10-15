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


def point_scores(frame, column):
    """Aggregate point/rank metrics on an already validated shared-row cohort."""
    if frame.empty:
        return {"n": 0, "rmse": None, "mae": None, "bias": None,
                "ranking_weeks": 0, "mean_within_gw_spearman": None,
                "mean_within_gw_ndcg10": None}
    actual = frame.actual.to_numpy(dtype=float)
    predicted = frame[column].to_numpy(dtype=float)
    if not np.isfinite(actual).all() or not np.isfinite(predicted).all():
        raise ValueError("Nonfinite comparison scores")
    error = predicted - actual
    ranking = []
    for _, week in frame.groupby(["season", "gameweek"], sort=True):
        if len(week) < 2 or week.actual.nunique() < 2:
            continue
        rho = float(spearmanr(week.actual, week[column]).statistic) if week[column].nunique() > 1 else 0.
        ranking.append((rho, float(ndcg_score(
            np.maximum(week.actual.to_numpy(), 0)[None, :],
            week[column].to_numpy()[None, :], k=min(10, len(week))))))
    return {"n": len(frame), "rmse": float(np.sqrt(np.mean(error ** 2))),
            "mae": float(np.mean(abs(error))), "bias": float(np.mean(error)),
            "ranking_weeks": len(ranking),
            "mean_within_gw_spearman": float(np.mean([r[0] for r in ranking])) if ranking else None,
            "mean_within_gw_ndcg10": float(np.mean([r[1] for r in ranking])) if ranking else None}
