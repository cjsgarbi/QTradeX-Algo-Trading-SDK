
def calculate_metrics():
    # Trades extracted from Image 1
    # Format: (type, percentage)
    trades_pct = [
        ("LOSS", 0.42), ("WIN", 2.21), ("WIN", 0.11), ("LOSS", 1.33), ("WIN", 1.00),
        ("WIN", 8.03), ("WIN", 4.77), ("LOSS", 0.63), ("LOSS", 1.04), ("LOSS", 0.47),
        ("LOSS", 0.80), ("LOSS", 0.55), ("WIN", 1.75), ("LOSS", 0.16), ("LOSS", 1.01),
        ("LOSS", 0.29), ("LOSS", 0.81), ("WIN", 0.11), ("LOSS", 0.44), ("WIN", 1.41),
        ("WIN", 4.66), ("LOSS", 0.64), ("LOSS", 0.70), ("LOSS", 0.92), ("WIN", 0.55),
        ("LOSS", 0.75), ("WIN", 0.20), ("LOSS", 0.89), ("WIN", 1.17), ("LOSS", 1.07),
        ("LOSS", 0.96), ("LOSS", 0.60), ("WIN", 1.27), ("LOSS", 1.31), ("LOSS", 1.43),
        ("LOSS", 1.37), ("LOSS", 0.67), ("WIN", 0.96), ("LOSS", 0.01), ("WIN", 2.14),
        ("LOSS", 0.79), ("LOSS", 0.82), ("LOSS", 0.76), ("LOSS", 1.98), ("LOSS", 2.03),
        ("LOSS", 0.49), ("WIN", 0.89), ("LOSS", 0.66), ("LOSS", 0.66), ("WIN", 2.06),
        ("WIN", 1.60)
    ]

    wins = [p for t, p in trades_pct if t == "WIN"]
    losses = [p for t, p in trades_pct if t == "LOSS"]

    print(f"Counted Wins: {len(wins)}")
    print(f"Counted Losses: {len(losses)}")
    print(f"Total Closed: {len(trades_pct)}")
    
    win_rate = len(wins) / len(trades_pct)
    print(f"Win Rate: {win_rate*100:.2f}%")

    # Compounded ROI
    roi = 1.0
    for t, p in trades_pct:
        multiplier = 1 + (p/100) if t == "WIN" else 1 - (p/100)
        roi *= multiplier
    
    total_roi_pct = (roi - 1) * 100
    print(f"Compounded ROI: {total_roi_pct:.2f}%")

    # Additive ROI (sum of percentages)
    sum_roi = sum([(p if t == "WIN" else -p) for t, p in trades_pct])
    print(f"Additive ROI (Sum): {sum_roi:.2f}%")

if __name__ == "__main__":
    calculate_metrics()
