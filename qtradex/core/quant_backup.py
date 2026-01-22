import math

import numpy as np


def slice_candles(now, data, candle, depth):
    """
    Efficiently selects the candles for which:
    now <= timestamp < now + candle
    and then slices the historical data using the last matching index.

    Code

    Assumptions:
      • data["unix"] is sorted in ascending order.
      • data is a dict with keys "unix", "high", "low", "open", "close".

    Returns:
      A dict with keys "high", "low", "open", "close", where each entry is a
      NumPy array obtained by taking the slice from max(0, last_index - depth + 1)
      to last_index (inclusive) and reversing the order.

    If no timestamp falls in [now, now+candle), returns empty arrays.
    """
    keys = [k for k in data.keys() if k != "unix"]
    # Convert unix timestamps to a numpy array if necessary.
    unix = (
        data["unix"] if isinstance(data["unix"], np.ndarray) else np.array(data["unix"])
    )

    # Find the start (left) and end (right) indices for the desired window.
    # Since unix is sorted, we use binary search.
    left = np.searchsorted(unix, now, side="left")
    right = np.searchsorted(unix, now + candle, side="left")

    # If nothing falls in the window, return empty arrays.
    if left == right:
        return {k: np.array([]) for k in keys}

    # Determine the index to use (the last matching timestamp)
    last_idx = right - 1
    start_idx = max(0, last_idx - depth + 1)

    # Slice each of the arrays from start_idx to last_idx (inclusive) and reverse the order.
    result = {}
    for key in keys:
        # Convert to numpy array if not already; slice and then reverse.
        series = data[key] if isinstance(data[key], np.ndarray) else np.array(data[key])
        result[key] = series[start_idx : last_idx + 1]

    return result


def filter_glitches(days, tune):
    """
    Early datasets sometimes contain wild irregular data
    FIXME: is this even used, and if so, is it still useful?
    """
    glitch_days = {
        "BTS": {"BITCNY": 200, "default": 250},
        "DASH": 360,
        "NXT": 300,
        "default": 100,
    }

    asset_glitch_days = glitch_days.get(tune["asset"], glitch_days["default"])
    if isinstance(asset_glitch_days, dict):
        days -= asset_glitch_days.get(tune["currency"], asset_glitch_days["default"])
    else:
        days -= asset_glitch_days

    return days


def preprocess_states(states, pair):
    new_states = {}
    new_states["wins"] = []
    new_states["losses"] = []
    new_states["detailed_wins"] = []
    new_states["detailed_losses"] = []

    for trade in states["trades"][1:]:
        data_dict = {"roi": trade.profit, "unix": trade.unix, "price": trade.price, "object":trade}
        if trade.profit >= 1:
            key = "wins"
        else:
            key = "losses"
        new_states[f"{key}"].append(trade.profit)
        new_states[f"detailed_{key}"].append(data_dict)

    new_states["balance_states"] = [
        i.value(pair, close) for i, close in zip(states["balances"], states["close"])
    ]

    inital_value = states["balances"][0].value(pair, states["close"][0])

    new_states["hold"] = (
        states["balances"][-1].value(pair, states["close"][-1]) / inital_value
    )
    new_states["hold_states"] = [
        states["balances"][0].value(pair, close) / inital_value
        for close in states["close"]
    ]
    new_states["balance_values"] = [
        balance.value(pair, close) / inital_value
        for close, balance in zip(states["close"], states["balances"])
    ]

    new_states["trades"] = new_states["wins"] + new_states["losses"]
    new_states["detailed_trades"] = sorted(
        new_states["detailed_wins"] + new_states["detailed_losses"],
        key=lambda x: x["unix"],
    )

    return new_states