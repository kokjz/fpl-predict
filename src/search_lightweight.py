"""Bounded I3 search. Runs only on explicit invocation, never promotes a model."""
import argparse
import hashlib
import json
from pathlib import Path
import platform
import resource
import time

import joblib
import numpy as np
import pandas as pd
import sklearn
from threadpoolctl import threadpool_limits

from benchmark_metrics import evaluate
from fpl_model import candidate_mask, metrics
from lightweight_candidates import LightweightCore
from runtime import workspace_root

FOLDS = ("2022-23", "2023-24")
KINDS = ("incumbent", "position", "minutes_mixture", "extra_trees")


def digest(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def peak_gib():
    rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return rss / (1024 ** 3 if platform.system() == "Darwin" else 1024 ** 2)


def development_data(root):
    d = pd.read_pickle(root / "artifacts/history.pkl")
    x = pd.read_pickle(root / "artifacts/features.pkl")
    if not d.index.equals(x.index) or d.duplicated(["season", "element", "fixture"]).any():
        raise ValueError("Invalid historical cache alignment or duplicate fixture keys")
    keep = d.season <= FOLDS[-1]
    d, x = d.loc[keep].copy(), x.loc[keep].copy()
    if not ((x.source_max_ts.isna()) |
            (x.source_max_ts < d.cutoff - pd.Timedelta(hours=3))).all():
        raise ValueError("Historical feature sources cross the deadline boundary")
    for fold in FOLDS:
        if not (d.season == fold).any() or not (d.season < fold).any():
            raise ValueError("Missing predeclared development fold")
        if d.loc[d.season < fold, "ts"].max() >= d.loc[d.season == fold, "cutoff"].min():
            raise ValueError("Training crosses validation time boundary")
    return d, x


def eligible(record, incumbent):
    return (record["pooled"]["rmse"] <= .995 * incumbent["pooled"]["rmse"]
            and record["pooled"]["mae"] <= 1.005 * incumbent["pooled"]["mae"]
            and all(record["folds"][f]["candidate_fixture"]["rmse"] <=
                    1.005 * incumbent["folds"][f]["candidate_fixture"]["rmse"] for f in FOLDS)
            and all(v["inference_1000_seconds"] <= 1. for v in record.get("timing", {}).values()))


def run(root, output):
    output.mkdir(parents=True, exist_ok=False)
    started = time.perf_counter()
    protocol = Path(__file__).resolve().parent.parent / "docs/I3_PROTOCOL.md"
    # Use the packaged copy when installed from a wheel.
    if not protocol.exists():
        from importlib.resources import files
        protocol = files("fpl_predict_resources").joinpath("I3_PROTOCOL.md")
    lock = {"protocol_sha256": hashlib.sha256(protocol.read_bytes()).hexdigest(),
            "input_sha256": {name: digest(root / "artifacts" / name)
                             for name in ("history.pkl", "features.pkl")},
            "source_sha256": {name: digest(Path(__file__).with_name(name)) for name in
                              ("search_lightweight.py", "lightweight_candidates.py", "benchmark_metrics.py", "fpl_model.py")},
            "versions": {"python": platform.python_version(), "numpy": np.__version__,
                         "pandas": pd.__version__, "sklearn": sklearn.__version__},
            "folds": list(FOLDS), "threads": 2, "audits_consulted": False,
            "current_season_scored": False, "promoted": False}
    (output / "protocol_lock.json").write_text(json.dumps(lock, indent=2) + "\n")
    records = []; predictions = {}

    def save():
        (output / "development_trials.json").write_text(json.dumps(records, indent=2) + "\n")

    def check_budget():
        if time.perf_counter() - started > 600 or peak_gib() > 2:
            raise RuntimeError("I3 soft resource budget exceeded; run incomplete, no promotion")

    def record(name, preds, timing):
        yy, pp = [], []; scores = {}
        for fold in FOLDS:
            va = d.season == fold; pool = candidate_mask(x.loc[va]).to_numpy()
            scores[fold] = evaluate(d.loc[va], x.loc[va], preds[fold])
            yy.extend(d.loc[va, "points_core"].to_numpy()[pool]); pp.extend(preds[fold][pool])
        rec = {"name": name, "pooled": metrics(yy, pp), "folds": scores, "timing": timing}
        records.append(rec); predictions[name] = preds; save()
        print(name, round(rec["pooled"]["rmse"], 6), flush=True)
        return rec

    try:
        d, x = development_data(root)
        with threadpool_limits(limits=2):
            for kind in KINDS:
                preds = {}; timing = {}
                for fold in FOLDS:
                    check_budget(); tr = d.season < fold; va = d.season == fold
                    t = time.perf_counter()
                    model = LightweightCore(kind).fit(x.loc[tr], d.loc[tr])
                    fit_seconds = time.perf_counter() - t
                    preds[fold] = model.predict(x.loc[va])
                    batch = x.loc[va].iloc[:1000]
                    model.predict(batch)  # warm-up, outside recorded inference
                    t = time.perf_counter(); model.predict(batch)
                    timing[fold] = {"fit_seconds": fit_seconds,
                                   "inference_1000_seconds": time.perf_counter() - t}
                    del model
                    check_budget()
                record(kind, preds, timing)
            for kind in KINDS[1:]:
                timing = {fold: {"inference_1000_seconds":
                    records[0]["timing"][fold]["inference_1000_seconds"] +
                    next(r for r in records if r["name"] == kind)["timing"][fold]["inference_1000_seconds"]}
                    for fold in FOLDS}
                record(kind + "_blend50", {f: .5 * predictions[kind][f] +
                       .5 * predictions["incumbent"][f] for f in FOLDS}, timing)
            candidates = [r for r in records[1:] if eligible(r, records[0])]
            finalist = min(candidates, key=lambda r: (r["pooled"]["rmse"], r["pooled"]["mae"])) if candidates else None
            if finalist:
                kind = finalist["name"].removesuffix("_blend50")
                seed_records = [finalist]
                for seed in (7, 2026):
                    preds = {}; timing = {}
                    for fold in FOLDS:
                        check_budget(); tr = d.season < fold; va = d.season == fold
                        t = time.perf_counter(); model = LightweightCore(kind, seed).fit(x.loc[tr], d.loc[tr])
                        preds[fold] = model.predict(x.loc[va])
                        if finalist["name"].endswith("_blend50"):
                            preds[fold] = .5 * preds[fold] + .5 * predictions["incumbent"][fold]
                        timing[fold] = {"fit_seconds": time.perf_counter() - t}
                        del model
                    seed_records.append(record(finalist["name"] + "_seed" + str(seed), preds, timing))
                if np.mean([r["pooled"]["rmse"] for r in seed_records]) > .995 * records[0]["pooled"]["rmse"]:
                    finalist = None
            check_budget()
        lock.update(status="development_complete", finalist=finalist,
                    candidate_count=6, seconds=time.perf_counter() - started, peak_rss_gib=peak_gib(),
                    next_step="single locked promotion audit" if finalist else "stop; retain approved champion")
        joblib.dump({"predictions": predictions}, output / "development_predictions.joblib")
    except Exception as error:
        lock.update(status="incomplete", error=type(error).__name__ + ": " + str(error),
                    seconds=time.perf_counter() - started, peak_rss_gib=peak_gib(), finalist=None)
        (output / "finalist_lock.json").write_text(json.dumps(lock, indent=2) + "\n")
        raise
    (output / "finalist_lock.json").write_text(json.dumps(lock, indent=2) + "\n")
    return lock


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    result = run(workspace_root(), args.output_dir)
    print(json.dumps({k: result[k] for k in ("status", "seconds", "peak_rss_gib", "next_step")}, indent=2))


if __name__ == "__main__":
    main()
