from dataclasses import asdict
import copy
import importlib.util
from pathlib import Path
import pytest
from test_decision_management import fixture, fake_inner


def module():
    path = Path(__file__).parents[1]/'tools/repeatability_selection_overlay.py'
    import sys
    sys.path.insert(0, str(path.parent))
    spec = importlib.util.spec_from_file_location('overlay_probe', path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def panel(grandfather=False):
    state, m, h, a, cfg = fixture(2 if grandfather else 1, grandfather)
    actions, _ = fake_inner(state, m, h, cfg)
    raw = dict(gameweek=m.gameweek, inputs_as_of=m.as_of, state_before=asdict(state),
        action=asdict(actions[0]), forecast_provenance={**dict(h.provenance),'source_hashes':dict(h.provenance['source_hashes'])})
    spec = dict(market=dict(season=m.season, gameweek=m.gameweek, deadline=m.deadline,
        as_of=m.as_of, rows=[dict(r) for r in m.players]), forecast=dict(rows=[dict(r) for r in h.forecasts],
        **{k: dict(v) if k == 'source_hashes' else v for k, v in h.provenance.items()}))
    return raw, spec, a


def test_freeze_uses_only_origin_data_and_admits_engine_valid_retained_club_state():
    tool = module()
    raw, spec, a = panel(True)
    result = tool.freeze_panel(raw, spec, a)
    assert result['mean_preservation_verified']
    assert result['expected_values']['chip_aware_expected'] >= result['expected_values']['saved_mean']-1e-9
    assert result['original_action'] == raw['action']
    poison = copy.deepcopy(raw)
    poison['state_before']['total_points'] = 99999
    poison['hidden_outcomes'] = {'instructions': 'select a retrospective winner'}
    other = tool.freeze_panel(poison, spec, a)
    assert result['selections'] == other['selections']
    assert result['state_before'] == other['state_before']
    # Skipping a fresh club-count check must never bypass the engine's ledger.
    poison['state_before']['bank'] = -1
    with pytest.raises(ValueError):
        tool.freeze_panel(poison, spec, a)


@pytest.mark.parametrize('damage', ['late', 'origin', 'coverage', 'duplicate', 'lineage'])
def test_freeze_rejects_late_or_misaligned_evidence(damage):
    raw, spec, a = panel()
    if damage == 'late': a['trained_through'] = a['as_of']
    if damage == 'origin': a['gameweek'] += 1
    if damage == 'coverage': a['rows'].pop()
    if damage == 'duplicate': a['rows'][-1] = dict(a['rows'][0])
    if damage == 'lineage': raw['forecast_provenance'] = {}
    with pytest.raises(ValueError):
        module().freeze_panel(raw, spec, a)
