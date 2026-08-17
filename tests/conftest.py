import numpy as np
import pandas as pd
import pytest

@pytest.fixture
def candles():
    n=260
    t=pd.date_range('2024-01-01',periods=n,freq='D',tz='UTC')
    base=np.linspace(100,160,n)+4*np.sin(np.arange(n)/7)
    close=base+0.3*np.sin(np.arange(n))
    open_=close+0.2*np.cos(np.arange(n))
    high=np.maximum(open_,close)+1.2
    low=np.minimum(open_,close)-1.2
    volume=1000+100*np.sin(np.arange(n)/5)+np.arange(n)
    return pd.DataFrame({'time':t,'open':open_,'high':high,'low':low,'close':close,'volume':volume})
