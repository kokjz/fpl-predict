"""Explicit, retrospective incumbent-method pilot; never updates a registry.

Pickles are executable: only an explicitly trusted, hash-verified local cache is
accepted. Reconstructed schedules do not certify historical deadline knowledge.
"""
import argparse
import datetime as dt
import hashlib
import json
from pathlib import Path
import platform

import numpy as np
import pandas as pd
import sklearn
from threadpoolctl import threadpool_limits

from benchmark_evaluation import paired_block_errors
from benchmark_metrics import point_scores
from experiment_runner import file_hash
from fpl_model import CORE_FEATURES, DC_FEATURES, candidate_mask, fit_estimator, sample_weights

POLICY = {
    "schema_version": 1, "method": "incumbent-method-full-score-reference-v1",
    "train_seasons": ["2020-21", "2021-22", "2022-23", "2023-24", "2024-25"],
    "evaluation_season": "2025-26", "train_last_gw": 19,
    "validation_gws": [20, 27], "test_gws": [28, 38],
    "estimator": "hgb7", "seed": 20260921, "refit_validation": False,
    "core_blend": 1.0, "dc_selection": "fixed hgb7; no validation selection",
    "weight_half_life_days": 730.5, "label_lag_hours": 3,
    "candidate": "n_history >= 3 and last5_minutes >= 45",
    "baselines": ["last5 core + lagged DC", "ew4 core + lagged DC"],
    "schedule": "reconstructed earliest kickoff minus 90 minutes",
    "benchmark_eligible": False, "promotion": False,
    "limitations": ["reused historical outcomes", "no archived schedule knowledge",
                    "cache audit is not independent feature reconstruction",
                    "no measured season-points or captaincy benefit"],
}


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, allow_nan=False).encode()).hexdigest()


def code_hashes():
    return {name: file_hash(Path(__file__).with_name(name)) for name in
            ("reference_pilot.py", "fpl_model.py", "benchmark_metrics.py", "benchmark_evaluation.py")}


def environment():
    return {"python": platform.python_version(), "numpy": np.__version__,
            "pandas": pd.__version__, "scikit_learn": sklearn.__version__}


def split_masks(d):
    season = d.season.eq(POLICY["evaluation_season"])
    return {"train": d.season.isin(POLICY["train_seasons"]) | (season & d.GW.le(19)),
            "validation": season & d.GW.between(20, 27),
            "test": season & d.GW.between(28, 38)}


def audit(d, x, players):
    """Fail closed on alignment, targets, identities and recorded source times.

    Source maxima must cover player, own-team AND opponent histories. This
    validates supplied evidence, not the truth of a third-party timestamp claim.
    """
    if not d.index.equals(x.index) or not d.index.is_unique:
        raise ValueError("History/feature indices must match uniquely in order")
    required = ["season", "GW", "element", "fixture", "pos", "ts", "cutoff",
                "total_points", "points_core", "dc_hit", "played", "minutes"]
    if set(required) - set(d) or set(CORE_FEATURES + DC_FEATURES + ["source_max_ts"]) - set(x):
        raise ValueError("Missing required cache columns")
    if d[required[:5]].isna().any().any() or d.duplicated(["season", "element", "fixture"]).any():
        raise ValueError("Missing or duplicate fixture identity")
    if not d.pos.isin([1, 2, 3, 4]).all() or not d.GW.between(1, 38).all():
        raise ValueError("Invalid position/gameweek")
    for column in ("GW", "element", "fixture"):
        if not np.isfinite(d[column]).all() or not d[column].gt(0).all() or not d[column].eq(d[column].round()).all():
            raise ValueError("Fixture identities must be positive integers")
    if not np.isfinite(d[["total_points", "points_core", "played", "minutes"]]).all().all():
        raise ValueError("Nonfinite target")
    if not d.played.eq(d.minutes.gt(0).astype(float)).all() or not d.minutes.between(0, 90).all():
        raise ValueError("Incoherent appearance target")
    if not d.dc_hit.dropna().isin([0, 1]).all() or d.loc[d.pos.eq(1), "dc_hit"].fillna(0).ne(0).any():
        raise ValueError("Invalid DC target")
    if not np.allclose(d.total_points, d.points_core + 2 * d.dc_hit.fillna(0)):
        raise ValueError("Core/full target mismatch")
    if d.loc[d.season.eq("2025-26"), "dc_hit"].isna().any():
        raise ValueError("Missing full-score DC history")
    values = x[list(dict.fromkeys(CORE_FEATURES + DC_FEATURES))].to_numpy(dtype=float)
    if np.isinf(values).any() or x[["n_history", "last5_minutes", "dc_rate4"]].isna().any().any():
        raise ValueError("Invalid feature/candidate values")
    ts = pd.to_datetime(d.ts, utc=True, errors="raise")
    cutoff = pd.to_datetime(d.cutoff, utc=True, errors="raise")
    sources = pd.to_datetime(x.source_max_ts, utc=True, errors="raise")
    if ts.isna().any() or cutoff.isna().any() or cutoff.ge(ts).any():
        raise ValueError("Missing or invalid fixture cutoffs")
    if (sources.notna() & sources.ge(cutoff - pd.Timedelta(hours=3))).any():
        raise ValueError("History source violates information cutoff")
    if (sources.isna() & x.n_history.gt(0)).any():
        raise ValueError("Missing source timestamp for observed history")
    grouped = d.assign(candidate=candidate_mask(x), deadline=cutoff).groupby(["season", "GW", "element"])
    if grouped.candidate.nunique().ne(1).any() or grouped.deadline.nunique().ne(1).any():
        raise ValueError("Player-GW candidate/deadline differs across fixtures")
    if set(["id", "code"]) - set(players) or players[["id", "code"]].isna().any().any():
        raise ValueError("Missing identity bridge")
    if players.id.duplicated().any() or players.code.duplicated().any():
        raise ValueError("Ambiguous identity bridge")
    for column in ("id", "code"):
        if not np.isfinite(players[column]).all() or not players[column].gt(0).all() or not players[column].eq(players[column].round()).all():
            raise ValueError("Invalid stable identity")
    masks = split_masks(d)
    if not pd.concat(masks, axis=1).sum(axis=1).eq(1).all() or not all(m.any() for m in masks.values()):
        raise ValueError("Unexpected/missing split rows")
    if not set(POLICY["train_seasons"]) <= set(d.season):
        raise ValueError("Missing required training season")
    for name, expected in (("validation", range(20, 28)), ("test", range(28, 39))):
        if set(d.loc[masks[name], "GW"]) != set(expected):
            raise ValueError("Incomplete declared gameweek window")
    if not set(d.loc[masks["test"], "element"]) <= set(players.id):
        raise ValueError("Incomplete test identity bridge")
    for earlier, later in (("train", "validation"), ("validation", "test")):
        if ts[masks[earlier]].max() + pd.Timedelta(hours=3) >= cutoff[masks[later]].min():
            raise ValueError("Labels not complete before next split")
    return {name: {"rows": int(mask.sum()), "keys_sha256": digest(
        d.loc[mask, ["season", "GW", "element", "fixture"]].to_dict("records")),
        "first_cutoff": cutoff[mask].min().isoformat(),
        "last_label_complete": (ts[mask].max() + pd.Timedelta(hours=3)).isoformat()}
        for name, mask in masks.items()}


def load_caches(inputs, trust_local_cache):
    # Verify ALL hashes before either pickle deserialisation.
    if not trust_local_cache:
        raise ValueError("Explicit --trust-local-cache required; never use untrusted pickles")
    for name in ("history", "features", "players"):
        entry = inputs[name]
        if file_hash(entry["path"]) != entry["sha256"]:
            raise ValueError("Input checksum mismatch")
    return (pd.read_pickle(inputs["history"]["path"]), pd.read_pickle(inputs["features"]["path"]),
            pd.read_csv(inputs["players"]["path"]))


def prepare(history, features, players, output, *, trust_local_cache=False):
    if Path(output).exists():
        raise ValueError("Manifest already exists")
    inputs = {name: {"path": str(Path(path).resolve()), "sha256": file_hash(path)}
              for name, path in (("history", history), ("features", features), ("players", players))}
    d, x, p = load_caches(inputs, trust_local_cache)
    manifest = {"policy": POLICY, "inputs": inputs, "code": code_hashes(), "environment": environment(),
                "splits": audit(d, x, p), "created_at": dt.datetime.now(dt.timezone.utc).isoformat()}
    with Path(output).open("x") as stream:
        json.dump(manifest, stream, indent=2, allow_nan=False)
    return manifest


def run(manifest_path, expected_sha256, directory, *, trust_local_cache=False):
    if file_hash(manifest_path) != expected_sha256:
        raise ValueError("Manifest checksum mismatch")
    spec = json.loads(Path(manifest_path).read_text())
    if spec["policy"] != POLICY or spec["code"] != code_hashes() or spec["environment"] != environment():
        raise ValueError("Policy/code/environment differs from frozen manifest")
    d, x, players = load_caches(spec["inputs"], trust_local_cache)
    if audit(d, x, players) != spec["splits"]:
        raise ValueError("Split audit changed")
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    if any((directory / name).exists() for name in ("predictions.csv", "results.json")):
        raise ValueError("Pilot output already exists")
    masks = split_masks(d); train = masks["train"]; test = masks["test"]
    dc_train = train & d.dc_hit.notna()
    if not dc_train.any():
        raise ValueError("No training DC observations")
    with threadpool_limits(limits=2):
        core = fit_estimator("hgb7", x.loc[train, CORE_FEATURES], d.loc[train, "points_core"], sample_weights(d[train]))
        played = fit_estimator("hgb7", x.loc[train, CORE_FEATURES], d.loc[train, "played"], sample_weights(d[train]))
        dc = fit_estimator("hgb7", x.loc[dc_train, DC_FEATURES], d.loc[dc_train, "dc_hit"], sample_weights(d[dc_train]))
        z = x[test]
        play = np.clip(played.predict(z[CORE_FEATURES]), 0, 1)
        contribution = np.where(d.loc[test, "pos"].eq(1), 0,
                                np.minimum(play, np.clip(dc.predict(z[DC_FEATURES]), 0, 1)))
        prediction = np.clip(core.predict(z[CORE_FEATURES]), 0, 20) + 2 * contribution
    out = d.loc[test, ["season", "GW", "element", "fixture", "pos", "total_points"]].copy()
    out = out.rename(columns={"GW": "gameweek", "total_points": "actual"})
    out["fpl_code"] = out.element.map(players.set_index("id").code).astype(int)
    out["candidate"] = candidate_mask(z)
    out["reference"] = prediction
    baseline_dc = np.where(out.pos.eq(1), 0, np.clip(z.dc_rate4, 0, 1)) * 2
    out["last5"] = z.last5_points.to_numpy() + baseline_dc
    out["ew4"] = z.ew4_points_core.to_numpy() + baseline_dc
    # Last5 points in the feature store are CORE points, not full FPL scores.
    group = out.groupby(["season", "gameweek", "fpl_code"])
    g = group.agg(actual=("actual", "sum"), candidate=("candidate", "first"),
                  reference=("reference", "sum"), last5=("last5", "sum"), ew4=("ew4", "sum")).reset_index()
    result = {"policy": POLICY, "manifest_sha256": expected_sha256, "splits": spec["splits"],
              "metrics": {}, "paired_candidate_errors": {}}
    for name in ("reference", "last5", "ew4"):
        result["metrics"][name] = {"candidate_player_gw": point_scores(g[g.candidate], name),
                                   "all_player_gw": point_scores(g, name)}
    for name in ("last5", "ew4"):
        result["paired_candidate_errors"][name] = paired_block_errors(g[g.candidate], "reference", name)
    out.to_csv(directory / "predictions.csv", index=False, mode="x")
    result["predictions_sha256"] = file_hash(directory / "predictions.csv")
    with (directory / "results.json").open("x") as stream:
        json.dump(result, stream, indent=2, allow_nan=False)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="action", required=True)
    p = sub.add_parser("prepare")
    for name in ("history", "features", "players", "output"):
        p.add_argument("--" + name, type=Path, required=True)
    p.add_argument("--trust-local-cache", action="store_true")
    p = sub.add_parser("run")
    p.add_argument("--manifest", type=Path, required=True)
    p.add_argument("--manifest-sha256", required=True)
    p.add_argument("--directory", type=Path, required=True)
    p.add_argument("--trust-local-cache", action="store_true")
    args = vars(parser.parse_args()); action = args.pop("action")
    try:
        if action == "prepare": prepare(**args)
        else: run(args.pop("manifest"), args.pop("manifest_sha256"), **args)
    except (ValueError, KeyError, OSError) as exc:
        parser.exit(2, f"Pilot rejected: {exc}\n")
    print("Retrospective pilot artifact saved; no promotion or verified historical deadline claim.")


if __name__ == "__main__":
    main()
