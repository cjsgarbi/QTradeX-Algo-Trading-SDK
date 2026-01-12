"""
QTradeX Strategy Template
-------------------------
Use this file as a starting point for your new strategies.
It is 100% compatible with the QTradeX flow.

Usage:
1. Copy this file to a new name (e.g., `my_strategy.py`).
2. Implement your logic in the methods below.
3. Run it!
"""

import qtradex as qx
import numpy as np

class MyCustomStrategy(qx.BaseBot):
    def __init__(self):
        # 1. TUNABLES: Define parameters that can be optimized (genetic algorithms)
        # These are your "knobs" to turn.
        self.tune = {
            "period_fast": 12,
            "period_slow": 26,
            "rsi_period": 14,
            "rsi_threshold": 30,
        }

    def indicators(self, data):
        # 2. INDICATORS: Calculate technical indicators using pandas-ta (qx.ti)
        # Returns a dictionary where keys exactly match what you need in 'strategy'
        return {
            "fast_ema": qx.ti.ema(data["close"], self.tune["period_fast"]),
            "slow_ema": qx.ti.ema(data["close"], self.tune["period_slow"]),
            "rsi": qx.ti.rsi(data["close"], self.tune["rsi_period"]),
        }

    def strategy(self, tick_info, indicators):
        # 3. LOGIC: The brain of the bot. Called for every candle.
        # Access indicators by the keys you defined above.
        
        fast = indicators["fast_ema"]
        slow = indicators["slow_ema"]
        rsi = indicators["rsi"]
        
        # --- ENTRY RULES ---
        # Example: Buy if Fast EMA crosses above Slow EMA AND RSI is healthy
        if fast > slow and rsi < 70:
            return qx.Buy()
            
        # --- EXIT RULES ---
        # Example: Sell if Fast EMA crosses below Slow EMA
        elif fast < slow:
            return qx.Sell()
            
        # --- THRESHOLDS (Dynamic Stop Loss / Take Profit) ---
        # Optional: Return numeric values for dynamic stops based on indicators
        # return qx.Thresholds(buying=0.98 * close, selling=1.02 * close)
        
        # Default: Do nothing (Hold)
        return None

    def plot(self, *args):
        # 4. VISUALIZATION: Define what to draw on the chart
        qx.plot(
            self.info,
            *args,
            (
                # (Indicator Name, Label, Color, Panel Index, Group Name)
                ("fast_ema", "Fast EMA", "yellow", 0, "EMA"),
                ("slow_ema", "Slow EMA", "cyan",   0, "EMA"),
                ("rsi",      "RSI",      "white",  1, "RSI"), # Panel 1 = separate window
            )
        )

# --- BOILERPLATE TO RUN THE BOT ---
if __name__ == "__main__":
    # Configure your data source
    data = qx.Data(
        exchange="binance",   # 'binance', 'mexc', 'bitshares', etc
        asset="BTC",
        currency="USDT",
        begin="2023-01-01",
        end="2023-06-01"
    )
    
    # Initialize and Run
    bot = MyCustomStrategy()
    qx.dispatch(bot, data)
