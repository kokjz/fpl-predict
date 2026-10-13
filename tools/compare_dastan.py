"""Read archived exports; compare identical scores/rows, never train or promote.

Parquet input requires an optional local pyarrow installation. Neither that
reader nor any third-party model is required by routine engine forecasting.
"""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import spearmanr
from sklearn.metrics import ndcg_score

KEYS = ["season", "gameweek", "fpl_code"]


def align(ours, external, mapping):
    # This comparison is deliberately restricted to the season whose original
    # frozen core predictions equal full scoring; adding a future-trained DC
    # model to later seasons would invalidate their historical comparison.
    e = external.copy()
    if set(e.season) != {"2024-25"} or e.duplicated(KEYS).any():
        raise ValueError("Expected unique 2024/25 external player-gameweeks")
    v = ours.loc[ours.season == "2024-25"].copy()
    if v.duplicated(["season", "element", "fixture"]).any():
        raise ValueError("Duplicate incumbent fixture predictions")
    if not (v.total_points == v.points_core).all():
        raise ValueError("Core/full scoring mismatch")
    if mapping.id.duplicated().any() or mapping.code.isna().any():
        raise ValueError("Invalid football ID mapping")
    v = v.merge(mapping[["id", "code"]], left_on="element", right_on="id",
                how="left", validate="many_to_one")
    if v.code.isna().any():
        raise ValueError("Unmapped incumbent football IDs")
    g = v.groupby(["season", "GW", "code"], as_index=False).agg(
        actual_v1=("total_points", "sum"), v1=("model", "sum"),
        last5=("last5", "sum"), ewm=("ewm", "sum"),
        candidate=("candidate", "min"), candidate_max=("candidate", "max"))
    if not (g.candidate == g.candidate_max).all():
        raise ValueError("Candidate predicate differs within a double gameweek")
    g = g.rename(columns={"GW": "gameweek", "code": "fpl_code"})
    paired = e.merge(g, on=KEYS, how="inner", validate="one_to_one")
    if paired.empty or not (paired.actual == paired.actual_v1).all():
        raise ValueError("No matched records or inconsistent realised scores")
    for col in ("actual", "v1", "dastan", "dastan_without_ep_next", "last5", "ewm"):
        if not np.isfinite(paired[col]).all():
            raise ValueError("Missing/nonfinite comparison values")
    return paired


def score(frame, column):
    error = frame[column] - frame.actual
    ranking = []
    for _, week in frame.groupby(["season", "gameweek"]):
        if len(week) < 2 or week.actual.nunique() < 2:
            continue
        rho = float(spearmanr(week.actual, week[column]).statistic) if week[column].nunique() > 1 else 0.
        ranking.append((rho, float(ndcg_score(np.maximum(week.actual.to_numpy(), 0)[None, :],
                       week[column].to_numpy()[None, :], k=min(10, len(week))))))
    return {"n": len(frame), "rmse": float(np.sqrt(np.mean(error ** 2))),
            "mae": float(np.mean(abs(error))), "bias": float(np.mean(error)),
            "mean_within_gw_spearman": float(np.mean([r[0] for r in ranking])) if ranking else None,
            "mean_within_gw_ndcg10": float(np.mean([r[1] for r in ranking])) if ranking else None}


def report(ours, external, mapping):
    paired = align(ours, external, mapping)
    cohorts = {"all_matched": paired,
               "predeadline_candidates": paired[paired.candidate.astype(bool)],
               "actual_60plus_diagnostic": paired[paired.minutes >= 60]}
    result = {"scope": "2024/25 archived retrospective comparison, not prospective",
              "external_rows": len(external), "matched_rows": len(paired),
              "unmatched_rows": len(external) - len(paired), "outcome_conflicts": 0,
              "cohorts": {name: {"rows": len(frame), "models": {col: score(frame, col)
                  for col in ("v1", "dastan", "dastan_without_ep_next", "last5", "ewm")}}
                  for name, frame in cohorts.items() if len(frame)}}
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ours", type=Path, required=True)
    parser.add_argument("--external", type=Path, required=True)
    parser.add_argument("--mapping", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = report(pd.read_json(args.ours, lines=True), pd.read_parquet(args.external),
                    pd.read_csv(args.mapping))
    result["input_sha256"] = {label: hashlib.sha256(path.read_bytes()).hexdigest()
                              for label, path in (("ours", args.ours), ("external", args.external), ("mapping", args.mapping))}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x") as stream:
        stream.write(json.dumps(result, indent=2) + "\n")
    print("Comparison saved; this is not an approved-model promotion or prospective trial.")


if __name__ == "__main__":
    main()
