import numpy as np
import pandas as pd
import pytest
import core_xg_mask as t
from fpl_model import CORE_FEATURES

def test_tolerance_exact_boundary_and_above():
    x=pd.DataFrame({'x':[0.]});y=pd.DataFrame({'x':[1e-12]})
    assert t.tolerance_identity(x,y)['passed']
    y.iloc[0,0]=np.nextafter(1e-12,np.inf)
    assert not t.tolerance_identity(x,y)['passed']
    for value in (np.nan,np.inf,-np.inf):
        assert not t.tolerance_identity(x,y.assign(x=value))['passed']
        assert not t.tolerance_identity(x.assign(x=value),y)['passed']
    x=pd.DataFrame({'x':[100.]})
    assert t.tolerance_identity(x,x+9e-11)['passed']
    assert not t.tolerance_identity(x,x+1.1e-10)['passed']

def test_splice_retains_cached_bits_and_takes_masked():
    cache=pd.DataFrame(1.,index=[4,9],columns=t.COLUMNS)
    unmasked=cache.copy();unmasked.iloc[0,0]=np.nextafter(1.,np.inf)
    masked=unmasked.copy();masked.iloc[1,1]=.09
    spliced,changed=t.splice(cache,unmasked,masked)
    assert spliced.to_numpy()[~changed.to_numpy()].tobytes()==cache.to_numpy()[~changed.to_numpy()].tobytes()
    assert spliced.iloc[0,0]==1. and spliced.iloc[1,1]==.09
    assert changed.to_numpy().sum()==1
    x=np.ones((4,len(CORE_FEATURES)));z=x.copy()
    z[2,CORE_FEATURES.index(t.COLUMNS[1])]=.09
    assert t.correction_proof(x,z,['2020-21','2023-24','2022-23','2025-26'])['passed']
    z[0,CORE_FEATURES.index(t.COLUMNS[0])]=2.
    with pytest.raises(ValueError):t.correction_proof(x,z,['2020-21','2023-24','2022-23','2025-26'])
