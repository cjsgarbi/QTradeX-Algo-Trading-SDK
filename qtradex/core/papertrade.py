import time
from datetime import datetime, timezone

from matplotlib import pyplot as plt
from qtradex.common.utilities import it
from qtradex.core.backtest import backtest, trade
from qtradex.core.base_bot import Info
from qtradex.plot.utilities import unix_to_stamp
from qtradex.private.signals import Thresholds, Hold, Buy, Sell
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
    else:
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
    
    # 1. Calcular quantos candles precisamos para aquecer os indicadores
    # Prioridade: bot.warmup (definido pela estratégia) ou um default seguro (100)
    warmup_candles = int(getattr(bot, 'warmup', 100)) + 5
    
    window = warmup_candles * tick_size
    data.begin = now - window
    
    print(f"[{data.asset}/{data.currency}] Buscando {warmup_candles} candles para warmup...")

    # 2. Buscar os dados da exchange
    data, raw_15m = fetch_composite_data(data, new_size=tick_size)
    bot.info._set("live_data", raw_15m)
    
    print(f"[{data.asset}/{data.currency}] Dados carregados: {len(data['close'])} candles")

    # Inicializar o preço da wallet (necessário para wallet.value() funcionar)
    wallet.value((data.asset, data.currency), data['close'][-1])

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
    
    while True:
        now = int(time.time())
        # Sincronismo Natural: O candle atual no relógio do sistema
        current_candle_start = (now // tick_size) * tick_size

        # POLLING: Só entra no processamento se o candle do relógio for novo
        if current_candle_start > last_candle_unix:
            tick += 1
            
            # 1. Buscar dados atualizados usando a janela completa de warmup
            try:
                data.candle_size = data.base_size
                data.update_candles(now - window, now)
                data, raw_15m = fetch_composite_data(data, new_size=tick_size)
                last_candle_unix = current_candle_start
                bot.info._set("live_data", raw_15m)
            except Exception as e:
                print(f"Error fetching new candle: {e}. Retrying...")
                plt.pause(2)
                continue

            # the current tick is inherently the last tick
            tick_data = {k: v[-1] for k, v in data.items()}

            wallet._protect()
            signal = bot.strategy(
                {"last_trade": last_trade, "unix": now, "wallet": wallet, **tick_data},
                indicators := bot.indicators(data),
            )
            # get the bot's execution decision (Buy, Sell, Hold)
            operation = bot.execution(signal, indicators, wallet)

            # 3. Execução obediente do sinal
            if isinstance(operation, (Buy, Sell)):
                initial_balances = dict(wallet.items())
                wallet._release()
                wallet, executed_op = trade(
                    data.asset, data.currency, operation, wallet, tick_data, now
                )
                
                if executed_op is not None:
                    new_balances = dict(wallet.items())
                    print_trade(
                        data, initial_balances, new_balances, executed_op, now, last_trade_time
                    )
                    last_trade = executed_op
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

