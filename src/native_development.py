"""Predeclared I4 development-only ablations; no promotion or operational writes."""
import argparse
import datetime as dt
import json
from pathlib import Path
import time

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier
from threadpoolctl import threadpool_limits

from benchmark_evaluation import paired_block_errors
from benchmark_metrics import evaluate, point_scores
from experiment_runner import file_hash
from fpl_model import CORE_FEATURES, candidate_mask, estimator, sample_weights
from native_history import NativeHistory, FEATURES, SNAPSHOT_FEATURES
from native_reference import environment
from points_replay import make_squads, realised_points
from forecast import select_xi
from external_benchmark import _timestamp

KEYS = ["season", "gameweek", "fixture", "fpl_code"]
FOLDS = ["2022-23", "2023-24"]
METHODS = ["control", "fpl_windows", "rich_windows", "rich_participation"]
POSITION = [f"position_{i}" for i in range(1, 5)]
# No older snapshots/actions are reconstructed or silently substituted.
OMIT_PREFIX = ("ar_defensive_", "ar_cbit_", "ar_recoveries_", "ar_tackles_",
               "ar_dc_", "ar_opp_dc_", "ar_opp_tackles_")
RICH = [f for f in FEATURES if f not in SNAPSHOT_FEATURES and not f.startswith(OMIT_PREFIX)] + POSITION
US_NAMES = ("shots", "xg", "xgchain", "xgbuildup", "key_passes", "xa")
FPL = [f for f in RICH if not any(f.startswith(f"player_{n}_") for n in US_NAMES)
       and not any(f.startswith(f"{side}_{n}_") for side in ("team", "opp")
                   for n in ("xg", "xga", "deep", "deep_allowed", "ppda", "ppda_allowed"))]
POLICY = dict(schema_version=1, method="I4-native-development-v1", folds=FOLDS,
              methods=METHODS, features=dict(fpl_windows=FPL, rich_windows=RICH,
              rich_participation=RICH), seed=20260921, squads=20,
              max_later_season="2023-24", target="historical core=full points",
              primary="candidate player-GW RMSE", promotion=False,
              no_later_audits=True, missing_snapshots="excluded", raw_missing="NaN",
              training_half_life_days=730.5, threads=2, no_search=True,
              permitted_empty_gws={"2022-23": [7]},
              error_gain=.005, max_fold_or_mae_loss=.005,
              points_gate="pooled mean squad delta>=0", ranking_gate="pooled NDCG10>=control",
              limitations=["reused development data", "corrected provider statistics",
                           "reconstructed historical deadlines/schedule", "lagged price proxies",
                           "not external-system reproduction or full season-strategy gain"])


def code_hashes():
    return {n: file_hash(Path(__file__).with_name(n)) for n in
            ("native_development.py", "native_history.py", "fpl_model.py", "points_replay.py",
             "forecast.py", "benchmark_metrics.py", "benchmark_evaluation.py", "native_reference.py")}


def load(entries):
    for e in entries.values():
        if Path(e["path"]).stat().st_size > 200_000_000: raise ValueError("Input budget")
        if file_hash(e["path"]) != e["sha256"]: raise ValueError("Input checksum mismatch")
    p = pd.read_csv(entries["players"]["path"])
    t = pd.read_csv(entries["teams"]["path"])
    c = pd.read_csv(entries["control"]["path"]).rename(columns={"GW": "gameweek"})
    # Discard all later history BEFORE constructing any model features.
    p = p[p.season.le(POLICY["max_later_season"])].reset_index(drop=True)
    t = t[t.season.le(POLICY["max_later_season"])].reset_index(drop=True)
    if not 0 < len(p) <= 150000 or not set(p.season) == {"2020-21", "2021-22", *FOLDS}:
        raise ValueError("Missing/invalid development seasons")
    if set(c.season) != set(p.season): raise ValueError("Control includes missing/later seasons")
    for frame in (p, c):
        if frame[KEYS].isna().any().any() or frame.duplicated(KEYS).any():
            raise ValueError("Ambiguous development keys")
    index = pd.MultiIndex.from_frame(p[KEYS])
    indexed = c.set_index(KEYS)
    if len(indexed) != len(index) or set(indexed.index) != set(index):
        raise ValueError("Control coverage differs")
    c = indexed.reindex(index).reset_index()
    for frame, names in ((p, ["ts", "deadline"]), (t, ["ts"]), (c, ["ts", "cutoff", "source_max_ts"])):
        for name in names:
            frame.loc[frame[name].notna(), name].map(_timestamp)
            frame[name] = pd.to_datetime(frame[name], utc=True)
    if not (p.total_points.eq(c.points_core).all() and p.total_points.eq(c.total_points).all()
            and p.minutes.eq(c.minutes).all() and p.position.eq(c.pos).all()
            and p.ts.eq(c.ts).all() and p.deadline.eq(c.cutoff).all()):
        raise ValueError("Control targets/context differ")
    if not np.isfinite(c[[*CORE_FEATURES, "points_core", "minutes"]].to_numpy(dtype=float)).all():
        raise ValueError("Nonfinite control features/targets")
    if (c.source_max_ts.notna() & c.source_max_ts.ge(c.cutoff-pd.Timedelta(hours=3))).any():
        raise ValueError("Future control source")
    if (c.source_max_ts.isna() & c.n_history.gt(0)).any(): raise ValueError("Missing control source")
    us = ["us_shots", "us_xG", "us_xGChain", "us_xGBuildup", "us_key_passes", "us_xA"]
    if (p.minutes.gt(0) & p.understat_id.notna() & p[us].isna().any(axis=1)).any():
        raise ValueError("Mapped development source gap")
    NativeHistory(p, t)
    for fold in FOLDS:
        present = set(p.loc[p.season.eq(fold), "gameweek"])
        allowed = set(POLICY["permitted_empty_gws"].get(fold, []))
        if not present <= set(range(1, 39)) or set(range(1, 39))-present-allowed:
            raise ValueError("Incomplete development fold")
        if p.loc[p.season.lt(fold), "ts"].max()+pd.Timedelta(hours=3) >= p.loc[p.season.eq(fold), "deadline"].min():
            raise ValueError("Training labels cross fold")
    if p.deadline.ge(p.ts).any(): raise ValueError("Invalid deadline")
    return p, t, c


def panels(c):
    d = c.rename(columns={"gameweek": "GW"})
    result = {}
    for fold in FOLDS:
        squads, first = make_squads(d, d, fold, count=POLICY["squads"])
        result[fold] = dict(first_gw=int(first), squads=squads)
    return result


def prepare(paths, output):
    if Path(output).exists(): raise ValueError("Manifest exists")
    entries = {k: dict(path=str(Path(v).resolve()), sha256=file_hash(v)) for k, v in paths.items()}
    _, _, c = load(entries)
    spec = dict(policy=POLICY, inputs=entries, code=code_hashes(), environment=environment(),
                panels=panels(c), created_at=dt.datetime.now(dt.timezone.utc).isoformat())
    with Path(output).open("x") as f: json.dump(spec, f, indent=2, allow_nan=False)
    return spec


def fit_predict(kind, features, rows, train, valid, timing=None):
    if timing is None: timing = {}
    started = time.monotonic()
    weights = sample_weights(rows.loc[train])
    y = rows.loc[train, "total_points"]
    cols = CORE_FEATURES if kind == "control" else FPL if kind == "fpl_windows" else RICH
    a, b = features.loc[train, cols], features.loc[valid, cols]
    if kind != "rich_participation":
        model = estimator("hgb7"); model.fit(a, y, sample_weight=weights)
        timing["fit_seconds"] = time.monotonic()-started
        tick = time.monotonic(); result = np.clip(model.predict(b), 0, 20)
        timing["prediction_seconds"] = time.monotonic()-tick
        return result
    states = np.where(rows.loc[train, "minutes"].ge(60), 2,
                      np.where(rows.loc[train, "minutes"].gt(0), 1, 0))
    if set(states) != {0, 1, 2}: raise ValueError("Missing training participation state")
    params = estimator("hgb7").get_params()
    base = {n: params[n] for n in ("max_leaf_nodes", "max_iter", "learning_rate",
             "l2_regularization", "min_samples_leaf", "early_stopping", "random_state")}
    classifier = HistGradientBoostingClassifier(**base)
    classifier.fit(a, states, sample_weight=weights)
    models = {}
    for state in (1, 2):
        mask = states == state; model = estimator("hgb7")
        model.fit(a.loc[mask], y.loc[mask], sample_weight=weights[mask])
        models[state] = model
    timing["fit_seconds"] = time.monotonic()-started
    tick = time.monotonic(); probabilities = classifier.predict_proba(b); prediction = np.zeros(len(b))
    for state, model in models.items():
        prediction += probabilities[:, list(classifier.classes_).index(state)] * model.predict(b)
    timing["prediction_seconds"] = time.monotonic()-tick
    return np.clip(prediction, 0, 20)


def replay(frame, panel, methods):
    grouped = frame.groupby(["gameweek", "element"]).agg(
        {**{m: "sum" for m in methods}, "actual": "sum", "minutes": "sum"})
    points = {m: [] for m in methods}
    for squad in panel["squads"]:
        players = {p["id"]: p for p in squad}; sums = dict.fromkeys(methods, 0.)
        for gw in range(panel["first_gw"], 39):
            sub = grouped.xs(gw) if gw in grouped.index.get_level_values(0) else pd.DataFrame()
            actual = {i: float(sub.loc[i, "actual"]) if i in sub.index else 0. for i in players}
            played = {i: bool(sub.loc[i, "minutes"] > 0) if i in sub.index else False for i in players}
            for method in methods:
                choices = [{**p, "expected_points": float(sub.loc[p["id"], method]) if p["id"] in sub.index else 0.}
                           for p in squad]
                sums[method] += realised_points(select_xi(choices), players, actual, played)
        for method in methods: points[method].append(sums[method])
    return {m: dict(mean_total=float(np.mean(v)),
                   mean_delta=float(np.mean(np.asarray(v)-points["control"])),
                   minimum_delta=float(np.min(np.asarray(v)-points["control"])),
                   maximum_delta=float(np.max(np.asarray(v)-points["control"]))) for m, v in points.items()}


def gate(candidate, control, fold_candidate, fold_control, points):
    return bool(all(candidate[k]["rmse"] <= .995*control[k]["rmse"]
                    and candidate[k]["mae"] <= 1.005*control[k]["mae"] for k in ("player_gw", "fixture"))
                and all(fold_candidate[f][k]["rmse"] <= 1.005*fold_control[f][k]["rmse"]
                        for f in FOLDS for k in ("candidate_player_gw", "candidate_fixture"))
                and candidate["ndcg10"] >= control["ndcg10"] and points >= 0)


def run(manifest, expected, directory):
    if file_hash(manifest) != expected: raise ValueError("Manifest checksum mismatch")
    spec = json.loads(Path(manifest).read_text())
    if spec["policy"] != POLICY or spec["code"] != code_hashes() or spec["environment"] != environment():
        raise ValueError("Frozen policy/code/environment changed")
    out = Path(directory); out.mkdir(parents=True, exist_ok=True)
    if any((out/n).exists() for n in ("predictions.csv", "results.json")): raise ValueError("Output exists")
    start = time.monotonic(); p, t, c = load(spec["inputs"])
    if panels(c) != spec["panels"]: raise ValueError("Frozen panels changed")
    x, evidence = NativeHistory(p, t).transform(p, pd.DataFrame(columns=["season", "gameweek", "fpl_code", "captured_at", *SNAPSHOT_FEATURES]))
    for i, name in enumerate(POSITION, 1): x[name] = p.position.eq(i).astype(np.float32)
    if not evidence.candidate.eq(candidate_mask(c)).all(): raise ValueError("Candidate populations differ")
    result = dict(policy=POLICY, manifest_sha256=expected, preparation_seconds=time.monotonic()-start,
                  timings={}, folds={}, metrics={}, paired={}, points={}, eligible=[], finalist=None)
    exports = []
    with threadpool_limits(limits=2):
        for fold in FOLDS:
            train = p.season.lt(fold); valid = p.season.eq(fold)
            z = p.loc[valid, [*KEYS, "minutes"]].copy()
            z["actual"] = p.loc[valid, "total_points"]; z["candidate"] = evidence.loc[valid, "candidate"]
            z["element"] = c.loc[valid, "element"]; z["pos"] = c.loc[valid, "pos"]
            z["n_history"] = c.loc[valid, "n_history"]
            scores = {}; result["timings"][fold] = {}
            for method in METHODS:
                timing = {}
                z[method] = fit_predict(method, c if method == "control" else x, p, train, valid, timing)
                result["timings"][fold][method] = timing
                d = c.loc[valid].rename(columns={"gameweek": "GW"})
                scores[method] = evaluate(d, c.loc[valid], z[method].to_numpy())
            result["folds"][fold] = scores
            result["points"][fold] = replay(z, spec["panels"][fold], METHODS)
            exports.append(z)
    z = pd.concat(exports); g = z.groupby(["season", "gameweek", "fpl_code"]).agg(
        {**{m: "sum" for m in METHODS}, "actual": "sum", "candidate": "first"}).reset_index()
    for method in METHODS:
        result["metrics"][method] = dict(player_gw=point_scores(g[g.candidate], method),
             fixture=point_scores(z[z.candidate], method), all_player_gw=point_scores(g, method),
             ndcg10=point_scores(g[g.candidate], method)["mean_within_gw_ndcg10"],
             actual_minutes_diagnostics={str(lo)+"_"+str(hi): point_scores(z[z.minutes.between(lo, hi)], method)
                                         for lo, hi in ((0,0),(1,59),(60,90))},
             cold_start=point_scores(z[z.n_history.lt(3)], method))
        if method != "control":
            result["paired"][method] = paired_block_errors(g[g.candidate], method, "control")
            points = float(np.mean([result["points"][f][method]["mean_delta"] for f in FOLDS]))
            if gate(result["metrics"][method], result["metrics"]["control"],
                    {f: result["folds"][f][method] for f in FOLDS},
                    {f: result["folds"][f]["control"] for f in FOLDS}, points): result["eligible"].append(method)
    if result["eligible"]:
        result["finalist"] = min(result["eligible"], key=lambda m:(result["metrics"][m]["player_gw"]["rmse"], result["metrics"][m]["player_gw"]["mae"]))
    z.to_csv(out/"predictions.csv", index=False, mode="x")
    result["predictions_sha256"] = file_hash(out/"predictions.csv")
    with (out/"results.json").open("x") as f: json.dump(result, f, indent=2, allow_nan=False)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__); sub = parser.add_subparsers(dest="action", required=True)
    a = sub.add_parser("prepare")
    for n in ("players", "teams", "control", "provenance", "output"): a.add_argument("--"+n, type=Path, required=True)
    b = sub.add_parser("run")
    for n in ("manifest", "manifest-sha256", "directory"): b.add_argument("--"+n, required=True)
    args = vars(parser.parse_args()); action = args.pop("action")
    try:
        if action == "prepare": prepare({k:v for k,v in args.items() if k != "output"}, args["output"])
        else: run(args["manifest"], args["manifest_sha256"], args["directory"])
    except (ValueError, KeyError, OSError, TypeError) as exc: parser.exit(2, f"Development study rejected: {exc}\n")
    print("Development artifact saved; no promotion or later-audit scoring.")


if __name__ == "__main__": main()
