"""Strict synthetic output selection, independent of directory enumeration order."""
import pytest
from promotion_groundwork_fixtures import forecast_output,parity_case


@pytest.mark.parametrize('latest',[True,False])
def test_output_with_and_without_latest(tmp_path,latest):
    if latest:(tmp_path/'LATEST').write_text('run\n')
    run=tmp_path/'run';run.mkdir()
    assert forecast_output(tmp_path)==run


@pytest.mark.parametrize('damage',['stray_file','multiple_runs','no_run','wrong_latest'])
def test_ambiguous_output_is_refused(tmp_path,damage):
    if damage!='no_run':(tmp_path/'run').mkdir()
    if damage=='stray_file':(tmp_path/'stray.txt').write_text('unexpected')
    elif damage=='multiple_runs':(tmp_path/'another').mkdir()
    elif damage=='wrong_latest':(tmp_path/'LATEST').write_text('another')
    with pytest.raises(ValueError,match='directory|Unexpected'):forecast_output(tmp_path)


def test_all_synthetic_reference_paths_complete(tmp_path):
    result=parity_case(tmp_path)
    assert result['horizon']==result['approved']
    assert result['mean_reproduction_max_abs_error']==0
    assert len(result['forecast']['fixture_predictions'])==30
