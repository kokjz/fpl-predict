"""Local archive joins and benchmark contract preflight; never fit or rank models."""
import argparse
import json
from pathlib import Path

import pandas as pd

from external_benchmark import (KEYS, FIXTURE_KEYS, _identities, _numeric, _required,
                                normalise_forecast, prepare_outcomes, load_inputs)


def join_seasonal_bridge(predictions, bridge):
    """Join a reviewed, one-season element/GW export to explicit fixture/code keys.

    Does not guess names, aggregate doubles, infer cutoffs or certify lineage.
    Both exports must represent exactly the same unique element/gameweek rows.
    """
    _required(predictions, ["element", "gw", "openfpl_xpts", "actual_points"], "archive")
    _required(bridge, [*FIXTURE_KEYS, "element"], "bridge")
    b = bridge.copy(); p = predictions.copy()
    _identities(b, fixtures=True)
    if b.season.nunique() != 1:
        raise ValueError("An element/GW archive requires exactly one declared season")
    _numeric(b, ["element"], integer=True, minimum=1)
    _numeric(p, ["element", "gw"], integer=True, minimum=1)
    _numeric(p, ["openfpl_xpts", "actual_points"])
    if b.duplicated(["element", "gameweek"]).any() or p.duplicated(["element", "gw"]).any():
        raise ValueError("Ambiguous element/gameweek bridge; fixture-grain adapter required")
    if b.groupby("element").fpl_code.nunique().gt(1).any() or b.groupby("fpl_code").element.nunique().gt(1).any():
        raise ValueError("Conflicting seasonal player identities")
    joined = b.merge(p[["element", "gw", "openfpl_xpts", "actual_points"]],
                     left_on=["element", "gameweek"], right_on=["element", "gw"],
                     how="outer", validate="one_to_one", indicator=True)
    if not joined._merge.eq("both").all():
        raise ValueError("Archive and bridge key coverage differs")
    return joined[[*FIXTURE_KEYS, "openfpl_xpts", "actual_points"]].rename(
        columns={"openfpl_xpts": "prediction", "actual_points": "actual"})


def preflight(outcomes, exports):
    """Collect admission failures without scoring or selecting favourable rows."""
    truth = prepare_outcomes(outcomes)
    if not 2 <= len(exports) <= 12:
        raise ValueError("Supply between two and twelve exports")
    universe = truth[KEYS].drop_duplicates()
    models = []
    names = set()
    for frame, manifest in exports:
        name = manifest.get("model_id")
        if not isinstance(name, str) or name in names:
            raise ValueError("Missing or duplicate model ID")
        names.add(name)
        try:
            normal, timing = normalise_forecast(frame, manifest, truth)
        except (ValueError, TypeError, KeyError) as exc:
            models.append({"model_id": name, "contract_valid": False, "reason": str(exc)})
        else:
            models.append({"model_id": name, "contract_valid": True,
                           "player_gameweeks": len(normal), "coverage": len(normal) / len(universe),
                           "declared_timing_ranges": timing})
    return {"schema_version": 1, "scope": "structural preflight only; no accuracy scores",
            "all_contracts_valid": all(m["contract_valid"] for m in models),
            "independent_provenance_certified": False, "model_promotion": False,
            "models": models,
            "remaining_manual_checks": ["exporter/model lineage and permissions",
                "truth schedule completeness, finalisation and full-score semantics",
                "actual feature/training/selection cutoff evidence",
                "predeadline candidate construction and matched refit policy",
                "archive capture evidence or honest retrospective origin"]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--outcomes", type=Path, required=True)
    parser.add_argument("--outcomes-sha256", required=True)
    parser.add_argument("--manifest", type=Path, action="append", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        if args.output.exists():
            raise ValueError("Output already exists")
        truth, exports, hashes = load_inputs(args.outcomes, args.outcomes_sha256, args.manifest)
        result = {**preflight(truth, exports), **hashes}
        raw = json.dumps(result, indent=2, allow_nan=False) + "\n"
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with args.output.open("x") as stream: stream.write(raw)
    except (ValueError, TypeError, KeyError, OSError) as exc:
        parser.exit(2, f"Preflight rejected: {exc}\n")
    print("Preflight saved; provenance review remains mandatory.")


if __name__ == "__main__":
    main()
