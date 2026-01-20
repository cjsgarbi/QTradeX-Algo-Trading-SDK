import time
from copy import deepcopy

import numpy as np
from matplotlib import pyplot as plt
from qtradex.common.utilities import it, rotate, sigfig
from qtradex.core.backtest import backtest
from qtradex.core.base_bot import Info
from qtradex.private.execution import Execution
from qtradex.private.signals import Buy, Sell
from qtradex.private.wallet import PaperWallet
from qtradex.public.utilities import fetch_composite_data


def filltest(bot, data, api_key, api_secret, tick_size=60 * 60 * 2):
    """
    Simulates trading based on historical fills and updates the bot's state accordingly.

    Parameters:
    - bot: The trading bot instance.
    - data: The data object containing asset, currency, and candle size.
    - api_key: API key for authentication.
    - api_secret: API secret for authentication.
    - tick_size: The size of the tick in seconds (default is 2 hours).
    """
    # Se a estrategia tiver um timeframe definido, usamos ele como tick_size
    if hasattr(bot, "timeframe"):
        print(f"Using strategy timeframe: {bot.timeframe}s")
        tick_size = bot.timeframe

    bot.info = Info({"mode": "fill test"})
    print("\033c")  # Clear the console
    asset, currency, candle_size = data.asset, data.currency, data.candle_size

    # Initialize execution and wallet
    execution = Execution(data.exchange, asset, currency, api_key, api_secret)
    wallet = PaperWallet(execution.exchange)
    wallet.balances = execution.exchange.fetch_balance()["total"]
    wallet.balances = {
        k: v for k, v in wallet.balances.items() if k in [asset, currency]
    }

    now = int(time.time())
    data.end = now
    bot.info._set("start", now)

    # Fetch historical trades
    fills = execution.fetch_my_trades()
    # FIXME: exactly why do i have to add tick size here?
    fills = [
        {**trade, "unix": (trade["timestamp"] / 1000) + tick_size} for trade in fills
    ]

    # Adjust the beginning of the data range
    # 86400 = segundos por dia (converte autorange de dias para segundos)
    data.begin = (
        max(data.begin, min([trade["unix"] for trade in fills]))
        - (bot.autorange()-1) * 86400
        - tick_size * 2
    )
    fills = [trade for trade in fills if trade["unix"] > data.begin]

    # Adjust tuning parameters based on tick size
    for key, value in list(bot.tune.items()):
        if key.endswith("_period"):
            bot.tune[key] = (
                value * (86400 / tick_size)
                if isinstance(value, float)
                else int(value * (86400 / tick_size))
            )

    print("Fetching data...")
    # Fetch new candle data
    data, raw_15m = fetch_composite_data(data, new_size=tick_size)
    bot.info._set("live_data", raw_15m)

    data.raw_candles = raw_15m
    candle_size = tick_size

    # Calculate indicators
    indicators = bot.indicators(data)

    # Ensure all indicators are of the same length
    min_length = min(map(len, indicators.values()))
    indicators = {key: value[-min_length:] for key, value in indicators.items()}
    indicated_data = {"indicators": rotate(indicators)}
    indicated_data.update({key: value[-min_length:] for key, value in data.items()})

    wallet.value((asset, currency), indicated_data["close"][-1])

    print("Calculating historical balances based on past trades...")

    states = []
    indicator_states = []

    new_value = None

    now = data.end
    while now > data.begin:
        tick_index = np.searchsorted(indicated_data["unix"], now, side="left")
        try:
            tick_data = {
                key: value[tick_index] for key, value in indicated_data.items()
            }
            if abs(tick_data["unix"] - now) > candle_size:
                now -= candle_size
                continue
        except IndexError:
            now -= candle_size
            continue

        operation = None

        fill_index = np.searchsorted(
            [trade["unix"] for trade in fills], now, side="left"
        )
        if (
            fill_index < len(fills)
            and abs(fills[fill_index]["unix"] - now) < candle_size
        ):
            fill = fills[fill_index]

            # REMEMBER: this is intentionally backwards!
            if fill["side"] == "sell":
                wallet[asset] = fill["amount"]  # -= fill["amount"]
                wallet[currency] = 0
                operation = Sell()
            else:  # Buy
                wallet[asset] = 0
                wallet[currency] = fill["cost"]  # -= fill["cost"]
                operation = Buy()


            operation.price = fill["price"]
            operation.unix = now
            if new_value is None:
                new_value = wallet.value((asset, currency), fill["price"])
            operation.profit = new_value / wallet.value(
                (asset, currency), fill["price"]
            )
            new_value = wallet.value((asset, currency), fill["price"])
            operation.is_override = False

        # Store the current state
        states.append(
            {
                "trades": operation,
                "balances": wallet.copy(),
                "unix": now,
                **tick_data,
            }
        )
        indicator_states.append(tick_data["indicators"])
        now -= candle_size

    # Reverse the states to maintain chronological order
    states.reverse()
    indicator_states.reverse()

    # Rotate the states for further processing
    states = rotate(states)
    states["trades"] = [trade for trade in states["trades"] if trade is not None]

    # FIXME: For lack of a better method, I'm "rotating" the profits on the trades like
    #        a circular buffer to get them in the right spot.  There has to be a better
    #        way, but I can't find it.
    for idx, trade in enumerate(deepcopy(states["trades"])):
        states["trades"][(idx+1)%(len(states["trades"])-1)].profit = trade.profit

    # Print trade details
    for trade in states["trades"]:
        print(trade)

    # Extract trade times and prices for analysis
    if states["trades"]:
        states["trade_times"], states["trade_prices"] = list(
            zip(*[[op.unix, op.price] for op in states["trades"]])
        )
    else:
        states["trade_times"], states["trade_prices"] = [], []

    # Assign colors based on trade type
    states["trade_colors"] = [
        "green" if isinstance(trade, Buy) else "red" for trade in states["trades"]
    ]

    # Plot the results
    bot.plot(
        data,
        states,
        rotate(indicator_states),
        True,
    )
