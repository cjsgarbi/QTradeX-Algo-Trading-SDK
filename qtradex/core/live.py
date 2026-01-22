import time

from matplotlib import pyplot as plt
from qtradex.common.utilities import it, trace
from qtradex.core.backtest import backtest, trade
from qtradex.core.base_bot import Info
from qtradex.core.papertrade import print_trade
from qtradex.plot.utilities import unix_to_stamp
from qtradex.private.execution import Execution
from qtradex.private.signals import Buy, Sell, Thresholds, Hold
from qtradex.private.wallet import PaperWallet, Wallet
from qtradex.public.data import Data
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
    
    # 1. Calcular quantos candles precisamos para aquecer os indicadores
    # Prioridade: bot.warmup (definido pela estratégia) ou um default seguro (100)
    warmup_candles = int(getattr(bot, 'warmup', 100)) + 5
    
    window = warmup_candles * tick_size
    data.begin = now - window
    
    print(f"[{data.asset}/{data.currency}] Buscando {warmup_candles} candles para warmup...")

    # 2. Buscar os dados da exchange
    data, raw_15m = fetch_composite_data(data, new_size=tick_size)
    bot.info._set("live_trades", execution.fetch_my_trades())
    bot.info._set("live_data", raw_15m)
    
    print(f"[{data.asset}/{data.currency}] Dados carregados: {len(data['close'])} candles")

    # 3. Calcular indicadores para aquecer
    print(f"[{data.asset}/{data.currency}] Aquecendo indicadores...")
    indicators = bot.indicators(data)
    
    # 4. Inicializar estado como Neutro
    last_trade = None
    last_trade_time = 0
    bot.reset()
    
    print(f"[{data.asset}/{data.currency}] Iniciando trade em tempo real...")
    print("-" * 50)
    
    plt.ion()


    # main tick loop
    tick = 0
    # O buffer inicial define o tamanho da nossa janela de warmup constante em RAM
    max_len = len(data["unix"])
    # CORREÇÃO: Inicializa com o candle ATUAL do relógio, não o último dos dados
    # Isso garante que o primeiro tick só dispare no PRÓXIMO fechamento
    last_candle_unix = (int(time.time()) // tick_size) * tick_size
    last_cancel = 0

    while True:
        now = int(time.time())
        # Sincronismo Natural: O candle atual no relógio do sistema
        current_candle_start = (now // tick_size) * tick_size

        # POLLING: Só entra no processamento se o candle do relógio for novo
        if current_candle_start > last_candle_unix:
            tick += 1
            
            # 1. Buscar dados atualizados usando a janela completa de warmup (SEGURO)
            try:
                data.candle_size = data.base_size
                data.update_candles(now - window, now)
                data, raw_15m = fetch_composite_data(data, new_size=tick_size)
                last_candle_unix = current_candle_start
                bot.info._set("live_trades", execution.fetch_my_trades())
                bot.info._set("live_data", raw_15m)
            except Exception as error:
                print(f"[{time.strftime('%H:%M:%S')}] Fetching data failed! retrying in 5 seconds...")
                plt.pause(5)
                continue

            # the current tick is inherently the last tick
            tick_data = {k: v[-1] for k, v in data.items()}

            print("Checking bot's decision")
            signal = bot.strategy(
                {
                    "last_trade": last_trade,
                    "unix": now,
                    "wallet": wallet.copy(),
                    **tick_data,
                },
                indicators := bot.indicators(data),
            )
            print("Finding bot's execution")
            # get the bot's decision (Buy, Sell, Hold)
            operation = bot.execution(signal, indicators, wallet.copy())

            # 3. Execução obediente do sinal em conta Real
            if isinstance(operation, (Buy, Sell)):
                initial_balances = dict(wallet.items())
                last_trade = operation

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
                        and (amount := wallet[data.currency]) > dust
                    ):
                        order_type = "market" if operation.price is None else "limit"
                        if order_type == "limit" and WIDE:
                            operation.price /= 2
                        
                        exec_amount = amount / (operation.price if operation.price else tick_data['close'])
                        print(f"*** PLACING {order_type.upper()} BUY ORDER ***")
                        print(
                            execution.create_order("buy", order_type, exec_amount, operation.price)
                        )

                    elif (
                        isinstance(operation, Sell)
                        and (amount := wallet[data.asset]) > dust
                    ):
                        order_type = "market" if operation.price is None else "limit"
                        if order_type == "limit" and WIDE:
                            operation.price *= 2
                        
                        print(f"*** PLACING {order_type.upper()} SELL ORDER ***")
                        print(
                            execution.create_order("sell", order_type, amount, operation.price)
                        )

                time.sleep(3)
                print("Refreshing balances")
                wallet.refresh()
                new_balances = dict(wallet.items())

                print_trade(
                    data, initial_balances, new_balances, operation, now, last_trade_time
                )
                last_trade_time = now
            
            elif isinstance(operation, Hold) or operation is None:
                # Estratégia decidiu manter posição
                pass

            # Heartbeat informativo
            status_signal = type(signal).__name__ if signal else "Hold"
            time_str = time.strftime("%H:%M:%S", time.localtime(now))
            print(f"[{time_str}] [{data.asset}/{data.currency}] Tick {tick:03d} | Price: {tick_data['close']:.2f} | Signal: {status_signal}")
            print("-" * 50)

        # Polling de alta frequência: Checa a cada 0.1s a virada do relógio
        plt.pause(0.1)
