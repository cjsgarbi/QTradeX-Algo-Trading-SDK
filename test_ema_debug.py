
import qtradex as qx
import numpy as np
import pandas as pd
import time

def main():
    print("=== DEBUG EMA ===")
    
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
    
    print("Fetching data...")
    # Trigger data download by accessing it? 
    # Usually qx.Data lazy loads. We need to access it inside a bot context or force load.
    # qx.Data doesn't seemingly expose a direct load method publicly in snippets I saw.
    # But dispatch uses it.
    
    # I'll try to emulate what 'indicators' does
    # But qx.Data object itself is not a dict of candles.
    # It seems 'data' in 'indicators(self, candles)' IS a dict.
    
    # Let's verify via a Minimal Bot
    class EMABot(qx.BaseBot):
        def __init__(self):
            self.timeframe = 3600
            self.tune = {}
            self.clamps = {}
            
        def indicators(self, candles):
            print(f"Candles received: {len(candles['close'])}")
            print("Calculating EMA 200...")
            try:
                ema = qx.ti.ema(candles['close'], 200)
                print(f"EMA Result type: {type(ema)}")
                if ema is None:
                    print("EMA IS NONE!")
                else:
                    print(f"EMA Sample: {ema[-5:]}")
            except Exception as e:
                print(f"EMA Failed: {e}")
                
            return {}
            
        def strategy(self, tick, ind):
            return qx.Hold()
            
    bot = EMABot()
    qx.dispatch(bot, data, qx.PaperWallet({asset: 0, currency: 1000}, 0.1))

if __name__ == "__main__":
    main()
