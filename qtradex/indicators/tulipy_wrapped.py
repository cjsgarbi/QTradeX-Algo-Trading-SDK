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
# Moving Averages
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
    # Tulipy returns: (macd, signal, histogram)
    df = ta.macd(pd.Series(data), fast=int(fast_period), slow=int(slow_period), signal=int(signal_period))
    if df is None: return np.zeros_like(data), np.zeros_like(data), np.zeros_like(data)
    cols = df.columns
    # Usually: MACD_..., MACDh_..., MACDs_...
    return df[cols[0]].to_numpy(), df[cols[2]].to_numpy(), df[cols[1]].to_numpy()

@cache
@float_period(3, 4, 5)
def stoch(high, low, close, k_period, k_slow_period, d_period):
    # Tulipy: stoch(high, low, close, pct_k_period, pct_k_slow_period, pct_d_period) -> (stoch_k, stoch_d)
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
    # Tulipy returns: adx
    df = ta.adx(pd.Series(high), pd.Series(low), pd.Series(close), length=int(period))
    if df is None: return np.zeros_like(close)
    # ADX_14, DMP_14, DMN_14
    return df.iloc[:, 0].to_numpy()

@cache
@float_period(3,)
def bbands(data, period, stddev):
    # Tulipy: (lower, middle, upper)
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

# -----------------------------------------------------------------------------
# Volatility
# -----------------------------------------------------------------------------
@cache
@float_period(3,)
def atr(high, low, close, period):
    return ta.atr(pd.Series(high), pd.Series(low), pd.Series(close), length=int(period)).to_numpy()

@cache
@float_period(3,)
def natr(high, low, close, period):
    return ta.natr(pd.Series(high), pd.Series(low), pd.Series(close), length=int(period)).to_numpy()

@cache
@float_period(1,)
def stddev(data, period):
    return ta.stdev(pd.Series(data), length=int(period)).to_numpy()

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

# -----------------------------------------------------------------------------
# Other / Misc
# -----------------------------------------------------------------------------
@cache
def psar(high, low, accel_step, accel_max):
    # Tulipy: psar(high, low, af, max_af)
    df = ta.psar(pd.Series(high), pd.Series(low), af=float(accel_step), max_af=float(accel_max))
    # PSARl, PSARs, PSARaf, PSARr
    # Tulipy just returns PSAR values
    # Pandas-TA combines Long/Short, usually PSARl_... or PSARs_... depending on direction
    # Simple workaround: combine long and short columns where non-NaN
    res = df.iloc[:, 0].fillna(0) + df.iloc[:, 1].fillna(0)
    return res.to_numpy()

@cache
@float_period(2,)
def aroon(high, low, period):
    # Tulipy: (aroon_down, aroon_up)
    df = ta.aroon(pd.Series(high), pd.Series(low), length=int(period))
    if df is None: return np.zeros_like(high), np.zeros_like(high)
    # AROOND_14, AROONU_14
    return df.iloc[:, 0].to_numpy(), df.iloc[:, 1].to_numpy()

@cache
@float_period(2,)
def aroonosc(high, low, period):
    return ta.aroonosc(pd.Series(high), pd.Series(low), length=int(period)).to_numpy()

@cache
@float_period(3,)
def ultosc(high, low, close, time1, time2, time3):
    return ta.uo(pd.Series(high), pd.Series(low), pd.Series(close), p1=int(time1), p2=int(time2), p3=int(time3)).to_numpy()

@cache
@float_period(1,)
def trix(data, period):
    # Pandas-TA returns: [TRIX, TRIXs (signal)]
    # Tulipy returns: trix
    df = ta.trix(pd.Series(data), length=int(period))
    if df is None: return np.zeros_like(data)
    return df.iloc[:, 0].to_numpy()

@cache
def crossany(a, b):
    # Returns 1 if crossover, else 0
    s1 = pd.Series(a)
    s2 = pd.Series(b)
    cross = ((s1 > s2) & (s1.shift(1) <= s2.shift(1))) | ((s1 < s2) & (s1.shift(1) >= s2.shift(1)))
    return cross.astype(int).to_numpy()

@cache
def crossover(a, b):
    # Returns 1 if a crosses over b
    s1 = pd.Series(a)
    s2 = pd.Series(b)
    cross = (s1 > s2) & (s1.shift(1) <= s2.shift(1))
    return cross.astype(int).to_numpy()

@cache
@float_period(1,)
def lag(data, period):
    return pd.Series(data).shift(int(period)).fillna(0).to_numpy()
