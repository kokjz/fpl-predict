"""The existing explicit minutes/availability sensitivity, shared by adapters."""
import math


def sensitivity_factor(values,override):
    factor=float(override.get('availability',1.))
    if not math.isfinite(factor) or not 0<=factor<=1:raise ValueError('availability must lie in [0,1]')
    if 'minutes' in override:
        minutes=float(override['minutes'])
        if not math.isfinite(minutes) or not 0<=minutes<=90:raise ValueError('minutes must lie in [0,90]')
        factor*=minutes/max(values['expected_minutes'],10.)
    return factor


def apply_sensitivity(values,override):
    """Scale unconditional forecasts illustratively; never infer probabilities."""
    result=dict(values);factor=sensitivity_factor(values,override)
    for key in result:result[key]*=factor
    result['p_play']=min(result['p_play'],1.);result['p60']=min(result['p60'],result['p_play'])
    result['expected_minutes']=min(result['expected_minutes'],90.)
    result['dc_xp']=min(result['dc_xp'],2*result['p_play'])
    result['expected_points']=result['core_xp']+result['dc_xp']
    return result
