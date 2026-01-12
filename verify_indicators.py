import numpy as np
import qtradex.indicators.tulipy_wrapped as ti

try:
    data = np.arange(100.0)
    sma = ti.sma(data, 10)
    print(f"SMA Type: {type(sma)}")
    print(f"SMA Shape: {sma.shape}")
    print(f"SMA Sample: {sma[-5:]}")

    # Test RSI
    rsi = ti.rsi(data, 14)
    print(f"RSI Sample: {rsi[-5:]}")

    # Test MACD
    macd, macd_signal, macd_hist = ti.macd(data, 12, 26, 9)
    print(f"MACD Shape: {macd.shape}")

    print("SUCCESS: Wrapper is working!")
except Exception as e:
    print(f"FAILURE: {e}")
    import traceback
    traceback.print_exc()
