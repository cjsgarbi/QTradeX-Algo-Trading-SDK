import time
from datetime import datetime, timezone

from matplotlib import pyplot as plt
from qtradex.common.utilities import it
from qtradex.core.backtest import backtest, trade
from qtradex.core.base_bot import Info
from qtradex.plot.utilities import unix_to_stamp
from qtradex.private.signals import Thresholds
from qtradex.private.wallet import PaperWallet
from qtradex.public.utilities import fetch_composite_data


def print_trade(data, initial_balances, new_balances, operation, now, last_trade_time):
    """
    Print the details of a trade operation, including the initial and new balances,
    the type of operation (buy or sell), and the time since the last trade.

    Parameters:
    initial_balances (dict): A dictionary representing the wallet balances before the trade.
    new_balances (dict): A dictionary representing the wallet balances after the trade.
    operation (Union[Buy, Sell]): The operation performed, either a Buy or Sell signal.
    now (int): The current time in seconds since the epoch.
    last_trade_time (int): The time of the last trade in seconds since the epoch.

    Returns:
    None
    """
    print("\n\n")

    print("Open:  ", data["open"][-1])
    print("High:  ", data["high"][-1])
    print("Low :  ", data["low"][-1])
    print("Close: ", data["close"][-1])

    now = datetime.now(timezone.utc).timestamp()

    print("Data time:   ", datetime.fromtimestamp(data["unix"][-1]).strftime("%c"))
    print("Real time:   ", datetime.fromtimestamp(time.time()).strftime("%c"))
    print("Data latency:", now - data["unix"][-1])
    print()
    print(
        f"{operation.__class__.__name__.upper()} - "
        f"at {now-last_trade_time:.1f} seconds since last trade"
    )
    if isinstance(operation, Thresholds):
        print(
            it("green", f"BUYING: {operation.buying}"),
            " --- ",
            it("red", f"SELLING: {operation.selling}"),
        )
    elif hasattr(operation, "price") and operation.price is not None:
        print(f"Execution price: {operation.price}")
    print()
    print(
        "Balances before:",
        {k: initial_balances[k] for k in [data.asset, data.currency]},
    )
    print("Balances after: ", {k: new_balances[k] for k in [data.asset, data.currency]})
    print(
        "Balance delta:  ",
        {k: new_balances[k] - initial_balances[k] for k in [data.asset, data.currency]},
    )
    print("\n")


def papertrade(bot, data, wallet=None, tick_size=60 * 15, tick_pause=60 * 5, **kwargs):
    """
    Simulate trading using a bot with live data updates, allowing for paper trading
    without executing real trades. This function continuously fetches new data,
    updates the bot's strategy, and prints trade suggestions and balance changes.

    Parameters:
    bot (object): The trading bot that contains the strategy and execution logic.
    data (object): The data object containing market data and candle information.
    wallet (object): The wallet object representing the user's balance and assets.
    tick_size (int, optional): The time interval in seconds between each trading tick.
                                Defaults to 600 seconds (10 minutes).

    Returns:
    None
    """
    kwargs.pop("fine_data", None)
    
    # Se a estrategia tiver um timeframe definido, usamos ele como tick_size
    if hasattr(bot, "timeframe"):
        print(f"Using strategy timeframe: {bot.timeframe}s")
        tick_size = bot.timeframe
        
    bot.info = Info({"mode": "papertrade"})
    if wallet is None:
        wallet = PaperWallet({data.asset: 0, data.currency: 1})
    print("\033c")
    now = int(time.time())
    data.end = now
    bot.info._set("start", now)
    # we only need `bot.autorange` worth of (daily) candles
    # doubled for better accuracy on the `last_trade`
    # 86400 = segundos por dia (autorange retorna dias)
    window = (bot.autorange() * 86400) * 6
    data.begin = data.end - window

    # allow for different candle sizes whilst maintaining the type of the parameter
    for k, v in list(bot.tune.items()):
        if k.endswith("_period"):
            if isinstance(v, float):
                bot.tune[k] = v * (86400 / tick_size)
            else:
                bot.tune[k] = int(v * (86400 / tick_size))

    # fetch new ten minute candle data with this exchange and pair
    data, raw_15m = fetch_composite_data(data, new_size=tick_size)
    bot.info._set("live_data", raw_15m)

    # make the matplotlib plot update live
    plt.ion()
    _, raw_states, _ = backtest(
        bot,
        data,
        wallet,
        block=False,
        return_states=True,
        range_periods=False,
        fine_data=raw_15m,
        always_trade="smart",
        show=True,
        **kwargs,
    )

    # update the plot
    plt.pause(0.1)

    # attempt to get the last trade, defaulting if there wasn't one
    last_trade = raw_states["trades"][-1] if raw_states["trades"] else None
    last_trade_time = 0

    # main tick loop
    # note most of this is the same as the backtest loop, we're just doing it every
    # `tick_size` with fresh data and printing/plotting what the bot would do
    tick = 0
    while True:
        tick += 1
        now = int(time.time())

        # Fetch the latest data for this tick:
        # Because of the way the Data class works, if we ask for all the data we need
        # it will automagically use the cache for all but the latest candle, so there's
        # no need to to worry about popping old candles and appending new ones here.
        data.candle_size = data.base_size
        data.update_candles(now - window, now)
        data, raw_15m = fetch_composite_data(data, new_size=tick_size)
        bot.info._set("live_data", raw_15m)

        # plot the latest data
        # technically, this runs the strategy at the current tick for us, so we could
        # just "execute" the most recent operation, but if the strategy relied on wallet
        # balances, we'd have to re-calculate the strategy anyway
        backtest(
            bot,
            data,
            wallet.copy(),
            block=False,
            range_periods=False,
            fine_data=raw_15m,
            always_trade="smart",
            show=False,
        **kwargs,
        )
        plt.pause(0.1)

        # reset the bot
        bot.reset()

        # calculate indicators
        indicators = bot.indicators(data)

        # the current tick is inherently the last tick
        tick_data = {k: v[-1] for k, v in data.items()}

        # make the wallet read-only before passing it to the user
        # this is not fail-safe, just helpful to keep accidental modifications out
        wallet._protect()
        signal = bot.strategy(
            # Note that unlike in backtest, we don't pass indicators as part of
            # tick_data.  This is simply a consequence of how the data is handled; so
            # when writing botscripts, don't rely on having indicators in tick_data
            {"last_trade": last_trade, "unix": now, "wallet": wallet, **tick_data},
            # pass the strategy this tick's indicators
            {k: v[-1] for k, v in indicators.items()},
        )
        # get the bot's decision
        operation = bot.execution(signal, indicators, wallet)
        if tick == 1 and operation is None:
            operation = last_trade
        # keep the last trade
        elif operation is not None:
            last_trade = operation

        # since this is a papertrade, not a backtest, we'll print the trade
        # as well as before & after balances and a few other things
        if operation is not None:
            initial_balances = dict(wallet.items())
            # release write protection and trade (note this is NOT live trading)
            wallet._release()
            wallet, _ = trade(
                data.asset, data.currency, operation, wallet, tick_data, now
            )

            # print statistics
            new_balances = dict(wallet.items())
            print_trade(
                data, initial_balances, new_balances, operation, now, last_trade_time
            )

            # update the last trade time
            last_trade_time = now

        start = time.time()
        while time.time() - start < tick_pause:
            plt.pause(tick_pause - (time.time() - start))
