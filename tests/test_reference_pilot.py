import json

import numpy as np
import pandas as pd
import pytest

import reference_pilot as pilot
from experiment_runner import file_hash
from fpl_model import CORE_FEATURES, DC_FEATURES


@pytest.fixture
def caches():
    records = []
    seasons = pilot.POLICY["train_seasons"]
    for season in [*seasons, "2025-26"]:
        weeks = [1] if season in seasons else [1, *range(20, 39)]
        for gw in weeks:
            ts = pd.Timestamp(f"{int(season[:4])+1}-01-01", tz="UTC") + pd.Timedelta(weeks=gw)
            for player in (1, 2):
                dc = float(player == 2) if season == "2025-26" else np.nan
                records.append(dict(season=season, GW=gw, element=player, fixture=gw,
                                    pos=2 if player == 1 else 4, ts=ts,
                                    cutoff=ts-pd.Timedelta(minutes=90), total_points=player+2*(dc or 0) if not np.isnan(dc) else player,
                                    points_core=float(player), dc_hit=dc, played=1., minutes=90.))
    d = pd.DataFrame(records)
    x = pd.DataFrame(1., index=d.index, columns=list(dict.fromkeys(CORE_FEATURES + DC_FEATURES)))
    x["n_history"] = 10; x["last5_minutes"] = 90
    x["dc_rate4"] = .1
    x["source_max_ts"] = d.cutoff - pd.Timedelta(days=7)
    return d, x, pd.DataFrame({"id": [1, 2], "code": [101, 102]})


def files(tmp_path, caches):
    d, x, p = caches
    d.to_pickle(tmp_path / "history.pkl"); x.to_pickle(tmp_path / "features.pkl")
    p.to_csv(tmp_path / "players.csv", index=False)
    return [tmp_path / f for f in ("history.pkl", "features.pkl", "players.csv")]


def test_audit_accepts_exact_splits(caches):
    result = pilot.audit(*caches)
    assert result["train"]["rows"] == 12
    assert result["validation"]["rows"] == 16
    assert result["test"]["rows"] == 22


@pytest.mark.parametrize("problem", ["source", "alignment", "bridge", "target", "appearance", "missing_week", "chronology", "candidate"])
def test_audit_rejects_leakage_and_incoherence(caches, problem):
    d, x, p = [v.copy() for v in caches]
    if problem == "source": x.loc[0, "source_max_ts"] = d.loc[0, "cutoff"] - pd.Timedelta(hours=3)
    if problem == "alignment": x = x.iloc[::-1]
    if problem == "bridge": p.loc[1, "code"] = 101
    if problem == "target": d.loc[0, "total_points"] = 99
    if problem == "appearance": d.loc[0, "played"] = 0
    if problem == "missing_week": d = d[~d.GW.eq(38)]; x = x.loc[d.index]
    if problem == "chronology": d.loc[0, "ts"] = d.ts.max()
    if problem == "candidate":
        # A second fixture with changed eligibility must not silently enter a DGW.
        d = pd.concat([d, d.iloc[[-1]]], ignore_index=True)
        x = pd.concat([x, x.iloc[[-1]]], ignore_index=True)
        d.loc[len(d)-1, "fixture"] = 99
        x.loc[len(x)-1, "n_history"] = 0
    with pytest.raises(ValueError): pilot.audit(d, x, p)


def test_hashes_and_explicit_trust_precede_deserialisation(tmp_path, caches, monkeypatch):
    paths = files(tmp_path, caches)
    with pytest.raises(ValueError, match="trust-local-cache"):
        pilot.prepare(*paths, tmp_path / "manifest.json")
    manifest = pilot.prepare(*paths, tmp_path / "manifest.json", trust_local_cache=True)
    paths[1].write_bytes(b"changed")
    monkeypatch.setattr(pd, "read_pickle", lambda _: pytest.fail("must verify every input first"))
    with pytest.raises(ValueError, match="checksum"):
        pilot.load_caches(manifest["inputs"], True)


def test_train_never_uses_validation_or_test_and_manifest_is_frozen(tmp_path, caches, monkeypatch):
    paths = files(tmp_path, caches); manifest = tmp_path / "manifest.json"
    pilot.prepare(*paths, manifest, trust_local_cache=True)
    calls = []
    class Constant:
        def __init__(self, target): self.value = float(target.mean())
        def predict(self, x): return np.full(len(x), self.value)
    def fit(name, x, y, weights):
        calls.append(set(x.index))
        return Constant(y)
    monkeypatch.setattr(pilot, "fit_estimator", fit)
    result = pilot.run(manifest, file_hash(manifest), tmp_path / "run", trust_local_cache=True)
    d = caches[0]; train = pilot.split_masks(d)["train"]
    assert len(calls) == 3 and all(indexes <= set(d.index[train]) for indexes in calls)
    assert result["metrics"]["reference"]["candidate_player_gw"]["n"] == 22
    assert not result["policy"]["benchmark_eligible"] and not result["policy"]["promotion"]
    with pytest.raises(ValueError, match="already exists"):
        pilot.run(manifest, file_hash(manifest), tmp_path / "run", trust_local_cache=True)
    spec = json.loads(manifest.read_text()); spec["policy"]["refit_validation"] = True
    manifest.write_text(json.dumps(spec))
    with pytest.raises(ValueError, match="Policy/code/environment"):
        pilot.run(manifest, file_hash(manifest), tmp_path / "other", trust_local_cache=True)


def test_policy_hash_rejects_modified_manifest(tmp_path, caches):
    paths = files(tmp_path, caches); manifest = tmp_path / "manifest.json"
    pilot.prepare(*paths, manifest, trust_local_cache=True)
    expected = file_hash(manifest); manifest.write_text(manifest.read_text() + " ")
    with pytest.raises(ValueError, match="Manifest checksum"):
        pilot.run(manifest, expected, tmp_path / "run", trust_local_cache=True)
