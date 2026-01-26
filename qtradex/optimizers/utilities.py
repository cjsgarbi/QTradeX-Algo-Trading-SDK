import json
import math
import random
from copy import deepcopy

import matplotlib.pyplot as plt
import matplotlib.style as mplstyle
import numpy as np
import qtradex as qx
from qtradex.common.utilities import NdarrayEncoder

mplstyle.use("dark_background")
plt.rcParams["figure.raise_window"] = False


def bound_neurons(bot):
    def clamp(value, minv, maxv, strength):
        """
        clamp `value` between `minv` and `maxv` with `strength`
        if strength is one, value is hard clipped
        if strength is 0.5, value is returned as the mean of itself and any boundries it is outside of
        if strength is 0, it is returned as is

        this works for all values of strength between 0 and 1.
        If strength is > 1 (e.g. 5), it is internally capped at 1.0 to prevent
        mathematical reflection and negative parameters.
        """
        strength = min(1.0, max(0.0, strength))

        isint = isinstance(value, int)

        ret = None
        # if told not to tune or value is within range
        if not strength or minv <= value <= maxv:
            # don't touch
            ret = value
        # less than minimum
        elif value < minv:
            ret = (value * (1 - strength)) + (minv * strength)
        # more than maximum
        elif value > maxv:
            ret = (value * (1 - strength)) + (maxv * strength)
        
        # ABSOLUTE HARD CLAMP: Guarantee value is within bounds
        ret = max(minv, min(maxv, ret))
        
        return int(ret) if isint else ret

    def ndclamp(value, minv, maxv, strength):
        """
        Clamp `value` between `minv` and `maxv` with `strength`.
        If strength is one, value is hard clipped.
        If strength is 0.5, value is returned as the mean of itself and any boundaries it is outside of.
        If strength is 0, it is returned as is.

        This works for all values of strength between 0 and 1.
        If strength is > 1 (e.g. 5), it is internally capped at 1.0 to prevent
        mathematical reflection and negative parameters.
        """
        strength = min(1.0, max(0.0, strength))
        
        # Create a mask for values less than minv
        less_than_min = value < minv
        # Create a mask for values greater than maxv
        greater_than_max = value > maxv
        
        # Initialize the result with the original value
        ret = np.copy(value)
        
        # Apply clamping for values less than minv
        if np.any(less_than_min):
            ret[less_than_min] = (value[less_than_min] * (1 - strength)) + (minv * strength)
        
        # Apply clamping for values greater than maxv
        if np.any(greater_than_max):
            ret[greater_than_max] = (value[greater_than_max] * (1 - strength)) + (maxv * strength)
        
        # ABSOLUTE HARD CLAMP: Guarantee all values are within bounds
        ret = np.clip(ret, minv, maxv)
        
        # Return as int if the original value was an integer
        if np.issubdtype(value.dtype, np.integer):
            return ret.astype(int)
        
        return ret

    def ensure_scalar(val):
        """Garantir que valores escalares sejam tipos Python nativos (não numpy arrays)."""
        if isinstance(val, np.ndarray):
            if val.ndim == 0 or val.size == 1:
                return val.item()
        if isinstance(val, np.floating):
            return float(val)
        if isinstance(val, np.integer):
            return int(val)
        return val

    bot.tune = {
        key: ensure_scalar(
            ndclamp(bot.tune[key], minv, maxv, clamp_amt)
            if isinstance(bot.tune[key], np.ndarray) and bot.tune[key].ndim > 0 and bot.tune[key].size > 1
            else clamp(ensure_scalar(bot.tune[key]), minv, maxv, clamp_amt)
        )
        for key, (minv, _, maxv, clamp_amt) in bot.clamps.items()
    }

    bot.autorange()
    return bot


def print_tune(score, bot, render=False):
    msg = ""
    just = max(map(len, score))
    for k, s in score.items():
        # Exibe como percentual (×100) para facilitar leitura
        pct = s * 100
        msg += f"# {k}".ljust(just + 2) + f" {pct:.2f}%\n"

    msg += "self.tune = " + json.dumps(bot.tune, indent=4, cls=NdarrayEncoder)
    msg += "\n\n"
    if not render:
        print(msg)
    return msg


def end_optimization(best_bots, show, asset="UNKNOWN", currency="UNKNOWN", begin_ts=None, end_ts=None):
    """Salva apenas o BEST ROI (o mais importante)."""
    import time
    
    # Pega apenas o ROI (o mais importante)
    if 'roi' in best_bots:
        coord = 'roi'
        score, bot = best_bots[coord]
    else:
        # Fallback: pega o primeiro
        coord = list(best_bots.keys())[0]
        score, bot = best_bots[coord]
    
    name = f"BEST {coord.upper()} TUNE"
    
    # Monta o objeto no formato limpo
    tune_data = {
        "identifier": f"{name}_{time.ctime()}",
        "asset": asset,
        "currency": currency,
        "timeframe": getattr(bot, 'timeframe', 900),
        "tune": bot.tune.copy(),
        "results": score
    }
    
    # Salva no arquivo
    save_bot = deepcopy(bot)
    save_bot.tune = {"tune": bot.tune.copy(), "results": score}
    save_bot._tune_asset = asset
    save_bot._tune_currency = currency
    save_bot._tune_begin = begin_ts
    save_bot._tune_end = end_ts
    qx.core.tune_manager.save_tune(save_bot, name)
    
    # Exibe no terminal no mesmo formato JSON
    if show:
        msg = "\033c=== FINAL TUNE ===\n\n"
        msg += json.dumps(tune_data, indent=2, cls=NdarrayEncoder)
        print(msg)


def merge(tune1, tune2):
    tune3 = {}
    for k, v in tune1.items():
        value = (random.random() / 2) + 0.25
        if isinstance(v, int):
            tune3[k] = int(round((v * value) + (tune2[k] * (1 - value))))
        else:
            tune3[k] = (v * value) + (tune2[k] * (1 - value))
    return tune3


import gc  # AION v2025.15: Explicit Garbage Collection

def plot_scores(historical, historical_tests, cdx):
    """
    historical is a matrix like this:
    [
        (
            idx,
            [
                (score, bot),
                (score, bot),
                ...
            ]
        )
    ]
    """
    if not historical:
        return
        
    # AION v2025.15: Force Garbage Collection to prevent MemLeak
    gc.collect()
    
    plt.clf()
    n_coords = len(historical[0][1])
    coords = list(historical[0][1].keys())
    # initialize empty lists
    lines = [[] for _ in range(n_coords)]
    x_list = []
    
    # Extract data
    for mdx, moment in enumerate(historical):
        x_list.append(moment[0])
        if mdx:
            x_list.append(moment[0])
            for idx in range(n_coords):
                lines[idx].append(lines[idx][-1])

        for coord, (score, _) in moment[1].items():
            lines[coords.index(coord)].append(score[coord])
    x_list.append(cdx)
    for idx in range(n_coords):
        lines[idx].append(lines[idx][-1])
        
    # AION v2025.15: Downsample data for plotting (Max ~1000 points)
    # Plotting 50k points freezes Matplotlib. We slice it.
    step = 1
    total_points = len(x_list)
    if total_points > 1000:
        step = total_points // 1000
    
    sqrt = n_coords**0.5

    height = math.ceil(sqrt)
    width = height

    # Handle scatter points (tests) similarly or just plot last N?
    # Scatter is lighter than Line usually, but let's keep it safe.
    x_list_tests = [i[0] for i in historical_tests]
    
    for idx, coord in enumerate(coords):
        plt.subplot(width, height, idx + 1)
        plt.title(coord)
        
        # Plot Optimized Slices
        plt.plot(x_list[::step], lines[idx][::step], color="green")
        
        plt.xscale("log")
        plt.scatter(
            x_list_tests,
            [i[1][coord] for i in historical_tests],
            color="yellow",
            s=5 # Small size
        )
    plt.tight_layout()
    plt.pause(0.1)

