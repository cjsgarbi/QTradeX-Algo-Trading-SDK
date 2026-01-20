import time

from matplotlib import pyplot as plt
from qtradex.common.utilities import it, trace
from qtradex.core.backtest import backtest, trade
from qtradex.core.base_bot import Info
from qtradex.core.papertrade import print_trade
from qtradex.plot.utilities import unix_to_stamp
from qtradex.private.execution import Execution
from qtradex.private.signals import Buy, Sell, Thresholds
from qtradex.private.wallet import PaperWallet, Wallet
from qtradex.public.utilities import fetch_composite_data

# For dev/testing, place orders "wide" on the market;
# selling price is *2 buying price is /2
WIDE = False
BROADCAST = True


def live(
    bot,
    data,
    api_key,
    api_secret,
    dust,
    tick_size=60 * 15,
    tick_pause=60 * 15,
    cancel_pause=3600 * 2,
    **kwargs,
):
    """
    Simulate trading using a bot with live data updates, allowing for paper trading
    without executing real trades. This function continuously fetches new data,
    updates the bot's strategy, and prints trade suggestions and balance changes.

    Notes:
     - Anytime 'wallet' is passed to client side, a copy is used, since all
       wallet copies are PaperWallets.

     - All backtests are started with 1 of _both_ currency and assets so that the bot
       will warm up unbiased

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

    bot.info = Info({"mode": "live"})
    print("\033c")

    execution = Execution(data.exchange, data.asset, data.currency, api_key, api_secret)
    wallet = Wallet(execution.exchange)

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

    print("Fetching data...")
    # fetch new ten minute candle data with this exchange and pair
    data, raw_15m = fetch_composite_data(data, new_size=tick_size)
    bot.info._set("live_trades", execution.fetch_my_trades())
    bot.info._set("live_data", raw_15m)
    # make the matplotlib plot update live
    plt.ion()
    print("Running initial backtest...")
    _, raw_states, _ = backtest(
        bot,
        data,
        PaperWallet({data.asset: 1, data.currency: 1}),
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
    last_cancel = 0
    tick = 0
    while True:
        tick += 1
        now = int(time.time())

        # Fetch the latest data for this tick:
        # Because of the way the Data class works, if we ask for all the data we need
        # it will automagically use the cache for all but the latest candle, so there's
        # no need to to worry about popping old candles and appending new ones here.
        data.candle_size = data.base_size
        print("Fetching fresh data...")
        while True:
            try:
                data.update_candles(now - window, now)
                data, raw_15m = fetch_composite_data(data, new_size=tick_size)
                break
            except Exception as error:
                print(trace(error))
                print("Fetching data failed!  retrying in 5 seconds...")
                time.sleep(5)
        bot.info._set("live_trades", execution.fetch_my_trades())
        bot.info._set("live_data", raw_15m)

        # plot the latest data
        # technically, this runs the strategy at the current tick for us, so we could
        # just "execute" the most recent operation, but if the strategy relied on wallet
        # balances, we'd have to re-calculate the strategy anyway
        print("Running backtest...")
        backtest(
            bot,
            data,
            PaperWallet({data.asset: 1, data.currency: 1}),
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
        print("Calculating indicators for this tick")
        indicators = bot.indicators(data)

        # the current tick is inherently the last tick
        tick_data = {k: v[-1] for k, v in data.items()}

        print("Checking bot's decision")
        signal = bot.strategy(
            # Note that unlike in backtest, we don't pass indicators as part of
            # tick_data.  This is simply a consequence of how the data is handled; so
            # when writing botscripts, don't rely on having indicators in tick_data
            {
                "last_trade": last_trade,
                "unix": now,
                "wallet": wallet.copy(),
                **tick_data,
            },
            # pass the strategy this tick's indicators
            {k: v[-1] for k, v in indicators.items()},
        )
        print("Finding bot's execution")
        # get the bot's decision
        operation = bot.execution(signal, indicators, wallet.copy())
        if tick == 1 and operation is None:
            operation = last_trade
        # keep the last trade
        elif operation is not None:
            last_trade = operation

        if operation is not None:
            initial_balances = dict(wallet.items())

            if BROADCAST:
                if (time.time() - last_cancel) >= cancel_pause:
                    print("*** CANCELLING ORDERS ***")
                    print(execution.cancel_all_orders())
                    time.sleep(3)
                    wallet.refresh()
                    last_cancel = time.time()

                print("*** PLACING ORDERS ***")

                if isinstance(operation, Thresholds):
                    if WIDE:
                        operation.selling *= 2
                        operation.buying /= 2
                    if amount := wallet[data.currency]:
                        amount /= operation.buying
                        print(
                            execution.create_order(
                                "buy", "limit", amount, operation.buying
                            )
                        )
                    if amount := wallet[data.asset]:
                        print(
                            execution.create_order(
                                "sell", "limit", amount, operation.selling
                            )
                        )

                elif (
                    isinstance(operation, Buy)
                    and ((amount := wallet[data.currency]) * operation.price) > dust
                ):
                    if WIDE:
                        operation.price /= 2
                    amount /= operation.price
                    print(
                        execution.create_order("buy", "limit", amount, operation.price)
                    )

                elif (
                    isinstance(operation, Sell)
                    and (amount := wallet[data.asset]) > dust
                ):
                    if WIDE:
                        operation.price *= 2
                    print(
                        execution.create_order("sell", "limit", amount, operation.price)
                    )

            time.sleep(3)
            print("Refreshing balances")
            wallet.refresh()
            # print statistics
            new_balances = dict(wallet.items())

            print_trade(
                data, initial_balances, new_balances, operation, now, last_trade_time
            )

            # update the last trade time
            last_trade_time = now

        print("waiting for next tick")
        start = time.time()
        while time.time() - start < tick_pause:
            print(f"{tick_pause - (time.time() - start)} seconds left")
            plt.pause(max((tick_pause - (time.time() - start)) + 1, 0.1))
            print("Done pausing")
