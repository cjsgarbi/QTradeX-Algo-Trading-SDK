
import qtradex as qx
from strategies.ZigZagATR import ZigZagATR
import time
import sys

def main():
    print("=== DEBUG ZIGZAG STOP LOSS ===")
    
    # 1. Setup specific parameters with TIGHT STOP
    params = {
        "atr_period": 21,
        "atr_multiplier": 2.0,
        "lookback": 5,
        "lookahead": 1,
        "stop_atr_mult": 1.5 # Forced tight
    }
    
    bot = ZigZagATR()
    bot.tune = params
    
    asset = "SOL"
    currency = "USDT"
    timeframe = 3600
    
    data = qx.Data(
        exchange="binance",
        asset=asset,
        currency=currency,
        begin="2025-06-01",
        end=int(time.time()),
        candle_size=timeframe, 
    )
    
    print("Running Backtest...")
    qx.dispatch(bot, data, qx.PaperWallet({asset: 0, currency: 10000}, fee=0.001))

if __name__ == "__main__":
    main()
