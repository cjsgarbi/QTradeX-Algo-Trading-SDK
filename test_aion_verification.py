
import qtradex as qx
from strategies.ZigZagATR import ZigZagATR
from qtradex.optimizers.aion import AION, AIONoptions
import time
import json
import sys

# Ensure validation of the specific parameters through the optimizer context
def main():
    print("=== AION OPTIMIZER VERIFICATION ===")
    
    # 1. Setup specific parameters
    params = {
        "atr_period": 21,
        "atr_multiplier": 2.0,
        "lookback": 5,
        "lookahead": 1
    }
    print(f"Target Parameters: {params}")

    # 2. Setup Bot
    bot = ZigZagATR()
    
    # NOTE: We use the default bot parameters (defined in __init__) 
    # to ensure all keys like 'stop_atr_mult' are present correctly.

    
    # 3. Setup Data
    asset = "SOL"
    currency = "USDT"
    timeframe = 3600
    print(f"Asset: {asset}/{currency}, Timeframe: {timeframe}")
    
    wallet = qx.PaperWallet({asset: 0, currency: 10000}, fee=0.001)
    
    data = qx.Data(
        exchange="binance",
        asset=asset,
        currency=currency,
        begin="2025-06-01",
        end=int(time.time()),
        candle_size=timeframe, 
    )

    # 4. Initialize AION
    print("Initializing AION Optimizer...")
    opt = AION(data, wallet)
    
    # Configure options for a quick but real optimization run
    opt.options.epochs = 50           # Run 50 generations to let it find good params
    opt.options.show_terminal = True
    opt.options.print_tune = True
    
    # 5. Run Optimization
    # AION will start from default/random and EXPLORE the new 'stop_atr_mult' parameter
    print("\nStarting AION Optimization (Goal: High ROI + Low Drawdown)...")
    try:
        opt.optimize(bot)
    except Exception as e:
        print(f"\nCRITICAL ERROR during optimization: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
        
    print("\n=== AION VERIFICATION COMPLETE ===")

if __name__ == "__main__":
    main()
