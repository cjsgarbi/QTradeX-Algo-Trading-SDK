import numpy as np
import pandas as pd
import pandas_ta as ta
from qtradex.indicators.cache_decorator import cache, float_period

# -----------------------------------------------------------------------------
# Math / Numpy Wrappers
# -----------------------------------------------------------------------------
@cache
def abs(data):
    return np.abs(data)

@cache
def add(a, b):
    return np.add(a, b)

@cache
def sub(a, b):
    return np.subtract(a, b)

@cache
def mul(a, b):
    return np.multiply(a, b)

@cache
def div(a, b):
    return np.divide(a, b)

@cache
def sum(data, period):
    return pd.Series(data).rolling(window=int(period)).sum().to_numpy()

@cache
def max(data, period):
    return pd.Series(data).rolling(window=int(period)).max().to_numpy()

@cache
def min(data, period):
    return pd.Series(data).rolling(window=int(period)).min().to_numpy()

@cache
def floor(data):
    return np.floor(data)

@cache
def ceil(data):
    return np.ceil(data)

@cache
def round(data):
    return np.round(data)

@cache
def trunc(data):
    return np.trunc(data)

@cache
def sqrt(data):
    return np.sqrt(data)

@cache
def exp(data):
    return np.exp(data)

@cache
def ln(data):
    return np.log(data)

@cache
def log10(data):
    return np.log10(data)

@cache
def sin(data):
    return np.sin(data)

@cache
def cos(data):
    return np.cos(data)

@cache
def tan(data):
    return np.tan(data)

@cache
def asin(data):
    return np.arcsin(data)

@cache
def acos(data):
    return np.arccos(data)

@cache
def atan(data):
    return np.arctan(data)

@cache
def sinh(data):
    return np.sinh(data)

@cache
def cosh(data):
    return np.cosh(data)

@cache
def tanh(data):
    return np.tanh(data)

@cache
def todeg(data):
    return np.degrees(data)

@cache
def torad(data):
    return np.radians(data)

# -----------------------------------------------------------------------------
# Moving Averages & Trend
# -----------------------------------------------------------------------------
@cache
@float_period(1,)
def sma(data, period):
    return ta.sma(pd.Series(data), length=int(period)).to_numpy()

@cache
@float_period(1,)
def ema(data, period):
    return ta.ema(pd.Series(data), length=int(period)).to_numpy()

@cache
@float_period(1,)
def wma(data, period):
    return ta.wma(pd.Series(data), length=int(period)).to_numpy()

@cache
@float_period(1,)
def dema(data, period):
    return ta.dema(pd.Series(data), length=int(period)).to_numpy()

@cache
@float_period(1,)
def tema(data, period):
    return ta.tema(pd.Series(data), length=int(period)).to_numpy()

@cache
@float_period(1,)
def hma(data, period):
    return ta.hma(pd.Series(data), length=int(period)).to_numpy()

@cache
@float_period(1,)
def kama(data, period):
    return ta.kama(pd.Series(data), length=int(period)).to_numpy()

@cache
@float_period(1,)
def zlema(data, period):
    return ta.zlma(pd.Series(data), length=int(period)).to_numpy()

@cache
@float_period(1,)
def trima(data, period):
    return ta.trima(pd.Series(data), length=int(period)).to_numpy()

@cache
@float_period(1,)
def tsf(data, period):
    # Time Series Forecast roughly linreg forecast
    return ta.tsf(pd.Series(data), length=int(period)).to_numpy()

@cache
@float_period(1,)
def wilders(data, period):
    # Wilder's Smoothing aka RMA
    return ta.rma(pd.Series(data), length=int(period)).to_numpy()

@cache
@float_period(1,)
def linearreg(data, period):
    return ta.linreg(pd.Series(data), length=int(period)).to_numpy()

@cache
@float_period(1,)
def linreg(data, period):
    return ta.linreg(pd.Series(data), length=int(period)).to_numpy()

@cache
@float_period(1,)
def vwma(close, volume, period):
    return ta.vwma(pd.Series(close), pd.Series(volume), length=int(period)).to_numpy()

@cache
@float_period(4, 5)
def adosc(high, low, close, volume, fast_period, slow_period):
    df = ta.adosc(pd.Series(high), pd.Series(low), pd.Series(close), pd.Series(volume), fast=int(fast_period), slow=int(slow_period))
    if df is None: return np.zeros_like(close)
    return df.to_numpy()

@cache
@float_period(3,)
def adxr(high, low, close, period):
    adx_val = ta.adx(pd.Series(high), pd.Series(low), pd.Series(close), length=int(period))
    if adx_val is None: return np.zeros_like(close)
    adx_series = adx_val.iloc[:, 0]
    adxr_series = (adx_series + adx_series.shift(int(period))) / 2
    return adxr_series.fillna(0).to_numpy()

@cache
def ao(high, low):
    df = ta.ao(pd.Series(high), pd.Series(low))
    if df is None: return np.zeros_like(high)
    return df.to_numpy()

@cache
@float_period(1,)
def decay(data, period):
    d = np.array(data, dtype=float)
    res = np.zeros_like(d)
    step = 1.0 / period
    current = 0.0
    for i in range(len(d)):
        current = max(d[i], current - step)
        res[i] = current
    return res

@cache
@float_period(1,)
def edecay(data, period):
    d = np.array(data, dtype=float)
    res = np.zeros_like(d)
    decay_factor = np.exp(-1.0 / period)
    current = 0.0
    for i in range(len(d)):
        current = max(d[i], current * decay_factor)
        res[i] = current
    return res

@cache
@float_period(3,)
def di(high, low, close, period):
    df = ta.adx(pd.Series(high), pd.Series(low), pd.Series(close), length=int(period))
    if df is None: return np.zeros_like(close), np.zeros_like(close)
    return df.iloc[:, 1].to_numpy(), df.iloc[:, 2].to_numpy()

@cache
@float_period(2,)
def dm(high, low, period):
    df = ta.adx(pd.Series(high), pd.Series(low), pd.Series(pd.Series(high)), length=int(period))
    if df is None: return np.zeros_like(high), np.zeros_like(high)
    return df.iloc[:, 1].to_numpy(), df.iloc[:, 2].to_numpy()

@cache
@float_period(3,)
def dx(high, low, close, period):
    df = ta.adx(pd.Series(high), pd.Series(low), pd.Series(close), length=int(period))
    if df is None: return np.zeros_like(close)
    plus_di = df.iloc[:, 1]
    minus_di = df.iloc[:, 2]
    dx_val = (abs(plus_di - minus_di) / (plus_di + minus_di + 1e-9)) * 100
    return dx_val.fillna(0).to_numpy()

@cache
@float_period(1,)
def dpo(close, period):
    df = ta.dpo(pd.Series(close), length=int(period))
    if df is None: return np.zeros_like(close)
    return df.to_numpy()

@cache
@float_period(1,)
def linregintercept(data, period):
    y = pd.Series(data)
    slope = ta.slope(y, length=int(period))
    projection = ta.linreg(y, length=int(period))
    if slope is None or projection is None: return np.zeros_like(data)
    intercept = projection - slope * (int(period) - 1)
    return intercept.fillna(0).to_numpy()

@cache
@float_period(1,)
def linregslope(data, period):
    df = ta.slope(pd.Series(data), length=int(period))
    if df is None: return np.zeros_like(data)
    return df.to_numpy()

@cache
@float_period(2,)
def qstick(open, close, period):
    diff = pd.Series(close) - pd.Series(open)
    qs = ta.sma(diff, length=int(period))
    if qs is None: return np.zeros_like(close)
    return qs.fillna(0).to_numpy()

@cache
@float_period(1,)
def vhf(close, period):
    p = int(period)
    c = pd.Series(close)
    hcp = c.rolling(p).max()
    lcp = c.rolling(p).min()
    diff = abs(c.diff())
    den = diff.rolling(p).sum()
    vhf_val = (hcp - lcp) / den
    return vhf_val.fillna(0).to_numpy()

@cache
@float_period(1, 2)
def vidya(close, period, smooth_period):
    c = np.array(close)
    p = int(period)
    sp = int(smooth_period)
    cmo_val = ta.cmo(pd.Series(close), length=p)
    if cmo_val is None: return np.zeros_like(close)
    vi = abs(cmo_val.to_numpy()) / 100.0
    alpha = 2.0 / (sp + 1.0)
    res = np.zeros_like(c)
    current = c[0]
    for i in range(len(res)):
        if np.isnan(vi[i]):
            res[i] = current
        else:
            eff_alpha = alpha * vi[i]
            current = eff_alpha * c[i] + (1 - eff_alpha) * current
            res[i] = current
    return res

# -----------------------------------------------------------------------------
# Oscillators / Momentum
# -----------------------------------------------------------------------------
@cache
@float_period(1,)
def rsi(data, period):
    return ta.rsi(pd.Series(data), length=int(period)).to_numpy()

@cache
@float_period(1, 2, 3)
def macd(data, fast_period, slow_period, signal_period):
    # Pandas-TA returns DF: [MACD, HIST, SIGNAL]
    df = ta.macd(pd.Series(data), fast=int(fast_period), slow=int(slow_period), signal=int(signal_period))
    if df is None: return np.zeros_like(data), np.zeros_like(data), np.zeros_like(data)
    cols = df.columns
    # Usually: MACD_..., MACDh_..., MACDs_...
    return df[cols[0]].to_numpy(), df[cols[2]].to_numpy(), df[cols[1]].to_numpy()

@cache
@float_period(3, 4, 5)
def stoch(high, low, close, k_period, k_slow_period, d_period):
    # Pandas-TA: stoch(high, low, close, k=..., d=..., smooth_k=...)
    df = ta.stoch(pd.Series(high), pd.Series(low), pd.Series(close), k=int(k_period), d=int(d_period), smooth_k=int(k_slow_period))
    if df is None: return np.zeros_like(close), np.zeros_like(close)
    cols = df.columns # STOCHk_..., STOCHd_...
    return df[cols[0]].to_numpy(), df[cols[1]].to_numpy()

@cache
@float_period(1,)
def roc(data, period):
    return ta.roc(pd.Series(data), length=int(period)).to_numpy()

@cache
@float_period(1,)
def mom(data, period):
    return ta.mom(pd.Series(data), length=int(period)).to_numpy()

@cache
@float_period(1,)
def cci(high, low, close, period):
    return ta.cci(pd.Series(high), pd.Series(low), pd.Series(close), length=int(period)).to_numpy()

@cache
@float_period(3,)
def adx(high, low, close, period):
     # returns: adx
    df = ta.adx(pd.Series(high), pd.Series(low), pd.Series(close), length=int(period))
    if df is None: return np.zeros_like(close)
     # ADX_14, DMP_14, DMN_14
    return df.iloc[:, 0].to_numpy()

@cache
@float_period(3,)
def bbands(data, period, stddev):
    # Pandas-TA: BBL, BBM, BBU (Lower, Mid, Upper)
    df = ta.bbands(pd.Series(data), length=int(period), std=float(stddev))
    if df is None: return np.zeros_like(data), np.zeros_like(data), np.zeros_like(data)
    return df.iloc[:, 0].to_numpy(), df.iloc[:, 1].to_numpy(), df.iloc[:, 2].to_numpy()

@cache
@float_period(1,)
def bop(open, high, low, close):
    return ta.bop(pd.Series(open), pd.Series(high), pd.Series(low), pd.Series(close)).to_numpy()

@cache
@float_period(3,)
def willr(high, low, close, period):
    return ta.willr(pd.Series(high), pd.Series(low), pd.Series(close), length=int(period)).to_numpy()

@cache
@float_period(1,)
def cmo(data, period):
    return ta.cmo(pd.Series(data), length=int(period)).to_numpy()

@cache
@float_period(1, 2)
def apo(data, fast, slow):
    return ta.apo(pd.Series(data), fast=int(fast), slow=int(slow)).to_numpy()

@cache
@float_period(1, 2)
def ppo(data, fast, slow):
    return ta.ppo(pd.Series(data), fast=int(fast), slow=int(slow)).to_numpy()

@cache
@float_period(2,)
def fisher(high, low, period):
    df = ta.fisher(pd.Series(high), pd.Series(low), length=int(period))
    if df is None: return np.zeros_like(high), np.zeros_like(high)
    return df.iloc[:, 0].to_numpy(), df.iloc[:, 1].to_numpy()

@cache
@float_period(1,)
def fosc(close, period):
    tsf_val = ta.tsf(pd.Series(close), length=int(period))
    if tsf_val is None: return np.zeros_like(close)
    fosc_val = 100 * (pd.Series(close) - tsf_val) / pd.Series(close)
    return fosc_val.fillna(0).to_numpy()

@cache
@float_period(1,)
def rocr(data, period):
    s = pd.Series(data)
    res = s / s.shift(int(period))
    return res.fillna(0).to_numpy()

@cache
@float_period(1,)
def stochrsi(data, period):
    df = ta.stochrsi(pd.Series(data), length=int(period))
    if df is None: return np.zeros_like(data)
    return df.iloc[:, 0].to_numpy()

@cache
@float_period(3,)
def ultosc(high, low, close, time1, time2, time3):
    return ta.uo(pd.Series(high), pd.Series(low), pd.Series(close), p1=int(time1), p2=int(time2), p3=int(time3)).to_numpy()

@cache
@float_period(1,)
def trix(data, period):
    df = ta.trix(pd.Series(data), length=int(period))
    if df is None: return np.zeros_like(data)
    return df.iloc[:, 0].to_numpy()

# -----------------------------------------------------------------------------
# Volatility
# -----------------------------------------------------------------------------
@cache
@float_period(3,)
def atr(high, low, close, period):
    result = ta.atr(pd.Series(high), pd.Series(low), pd.Series(close), length=int(period))
    if result is None:
        return np.zeros_like(close)
    return result.to_numpy()

@cache
@float_period(3,)
def natr(high, low, close, period):
    result = ta.natr(pd.Series(high), pd.Series(low), pd.Series(close), length=int(period))
    if result is None:
        return np.zeros_like(close)
    return result.to_numpy()

@cache
@float_period(1,)
def stddev(data, period):
    return ta.stdev(pd.Series(data), length=int(period)).fillna(0).to_numpy()

@cache
@float_period(1,)
def stderr(data, period):
    std = ta.stdev(pd.Series(data), length=int(period))
    if std is None: return np.zeros_like(data)
    res = std / np.sqrt(int(period))
    return res.fillna(0).to_numpy()

@cache
@float_period(2,)
def cvi(high, low, period):
    hl = pd.Series(high) - pd.Series(low)
    ema_hl = ta.ema(hl, length=int(period))
    if ema_hl is None: return np.zeros_like(high)
    cvi_val = (ema_hl - ema_hl.shift(int(period))) / ema_hl.shift(int(period)) * 100
    return cvi_val.fillna(0).to_numpy()

@cache
@float_period(2,)
def mass(high, low, period):
    df = ta.massi(pd.Series(high), pd.Series(low), length=int(period))
    if df is None: return np.zeros_like(high)
    return df.to_numpy()

@cache
def tr(high, low, close):
    df = ta.true_range(pd.Series(high), pd.Series(low), pd.Series(close))
    if df is None: return np.zeros_like(close)
    return df.to_numpy()

@cache
@float_period(1,)
def var(data, period):
    df = pd.Series(data).rolling(int(period)).var()
    return df.fillna(0).to_numpy()

@cache
@float_period(1,)
def volatility(data, period):
    return ta.stdev(pd.Series(data), length=int(period)).fillna(0).to_numpy()

# -----------------------------------------------------------------------------
# Volume
# -----------------------------------------------------------------------------
@cache
def obv(close, volume):
    return ta.obv(pd.Series(close), pd.Series(volume)).to_numpy()

@cache
def ad(high, low, close, volume):
    return ta.ad(pd.Series(high), pd.Series(low), pd.Series(close), pd.Series(volume)).to_numpy()

@cache
@float_period(4,)
def mfi(high, low, close, volume, period):
    return ta.mfi(pd.Series(high), pd.Series(low), pd.Series(close), pd.Series(volume), length=int(period)).to_numpy()

@cache
def emv(high, low, volume):
    res = ta.eom(pd.Series(high), pd.Series(low), pd.Series(high), pd.Series(volume), length=14)
    if res is None: return np.zeros_like(high)
    return res.to_numpy()

@cache
@float_period(4, 5)
def kvo(high, low, close, volume, fast, slow):
    df = ta.kvo(pd.Series(high), pd.Series(low), pd.Series(close), pd.Series(volume), fast=int(fast), slow=int(slow))
    if df is None: return np.zeros_like(close)
    return df.iloc[:, 0].to_numpy()

@cache
def nvi(close, volume):
    df = ta.nvi(pd.Series(close), pd.Series(volume))
    if df is None: return np.zeros_like(close)
    return df.to_numpy()

@cache
def pvi(close, volume):
    df = ta.pvi(pd.Series(close), pd.Series(volume))
    if df is None: return np.zeros_like(close)
    return df.to_numpy()

@cache
@float_period(1, 2)
def vosc(volume, fast, slow):
    short_ma = ta.sma(pd.Series(volume), length=int(fast))
    long_ma = ta.sma(pd.Series(volume), length=int(slow))
    if short_ma is None or long_ma is None: return np.zeros_like(volume)
    res = (short_ma - long_ma) / long_ma * 100
    return res.fillna(0).to_numpy()

@cache
def wad(high, low, close):
    h = np.array(high)
    l = np.array(low)
    c = np.array(close)
    res = np.zeros_like(c)
    curr = 0.0
    for i in range(1, len(c)):
        prev_c = c[i-1]
        trh = max(prev_c, h[i])
        trl = min(prev_c, l[i])
        if c[i] > prev_c:
            curr += c[i] - trl
        elif c[i] < prev_c:
            curr += c[i] - trh
        res[i] = curr
    return res

# -----------------------------------------------------------------------------
# Other / Misc
# -----------------------------------------------------------------------------
@cache
def psar(high, low, accel_step, accel_max):
    df = ta.psar(pd.Series(high), pd.Series(low), af=float(accel_step), max_af=float(accel_max))
    res = df.iloc[:, 0].fillna(0) + df.iloc[:, 1].fillna(0)
    return res.to_numpy()

@cache
@float_period(2,)
def aroon(high, low, period):
    df = ta.aroon(pd.Series(high), pd.Series(low), length=int(period))
    if df is None: return np.zeros_like(high), np.zeros_like(high)
    return df.iloc[:, 0].to_numpy(), df.iloc[:, 1].to_numpy()

@cache
@float_period(2,)
def aroonosc(high, low, period):
    return ta.aroonosc(pd.Series(high), pd.Series(low), length=int(period)).to_numpy()

@cache
def crossany(a, b):
    s1 = pd.Series(a)
    s2 = pd.Series(b)
    cross = ((s1 > s2) & (s1.shift(1) <= s2.shift(1))) | ((s1 < s2) & (s1.shift(1) >= s2.shift(1)))
    return cross.astype(int).to_numpy()

@cache
def crossover(a, b):
    s1 = pd.Series(a)
    s2 = pd.Series(b)
    cross = (s1 > s2) & (s1.shift(1) <= s2.shift(1))
    return cross.astype(int).to_numpy()

@cache
@float_period(1,)
def lag(data, period):
    return pd.Series(data).shift(int(period)).fillna(0).to_numpy()

@cache
def avgprice(open, high, low, close):
    return (pd.Series(open) + pd.Series(high) + pd.Series(low) + pd.Series(close)).to_numpy() / 4.0

@cache
def marketfi(high, low, volume):
    mfi_val = (pd.Series(high) - pd.Series(low)) / pd.Series(volume)
    return mfi_val.fillna(0).to_numpy()

@cache
@float_period(1,)
def md(data, period):
    df = pd.Series(data).rolling(int(period)).apply(lambda x: np.mean(np.abs(x - np.mean(x))), raw=True)
    return df.fillna(0).to_numpy()

@cache
def medprice(high, low):
    return ((pd.Series(high) + pd.Series(low)) / 2.0).to_numpy()

@cache
@float_period(1,)
def msw(data, period):
    return np.zeros_like(data), np.zeros_like(data)    

@cache
def typprice(high, low, close):
    return ((pd.Series(high) + pd.Series(low) + pd.Series(close)) / 3.0).to_numpy()

@cache
def wcprice(high, low, close):
    return ((pd.Series(high) + pd.Series(low) + 2 * pd.Series(close)) / 4.0).to_numpy()
