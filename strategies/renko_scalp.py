"""
╔═╗╔╦╗╦═╗╔═╗╔╦╗╔═╗═╗ ╦
║═╬╗║ ╠╦╝╠═╣ ║║║╣ ╔╩╦╝
╚═╝╚╩ ╩╚═╩ ╩═╩╝╚═╝╩ ╚═

renko_scalp.py

Renko Scalping - Alta Frequência (6+ trades/dia)

OBJETIVO: Lucros pequenos mas consistentes em alta frequência
- Timeframe: 5 minutos
- ATR pequeño para capturar movimentos menores
- Sem filtro de tendência (permite trades em qualquer direção)
- Confirmação rápida (1-2 bricks)
"""

import qtradex as qx
import numpy as np
from datetime import datetime
import time

class RenkoScalp(qx.BaseBot):
    """
    Estratégia Renko Scalping.
    
    LÓGICA:
    1. Bricks pequenos para capturar micro-movimentos
    2. Entrada rápida (1-2 bricks de confirmação)
    3. RSI para filtrar apenas os extremos perigosos
    4. Sem filtro de tendência (opera em qualquer direção)
    """
    
    def __init__(self):
        """Inicialização da estratégia."""
        self.timeframe = TIMEFRAME
        self.fee = FEE
        self.warmup = 90  # Quantidade de candles para aquecer indicadores
        
        # Parâmetros para SCALPING (alta frequência)
        self.tune = {
            "atr_len": 14,                # Mais estável
            "atr_mult": 3.0,              # Brick > Fees (0.2%)
            "min_bricks": 2,              # Confirmação robusta
            "rsi_len": 14,                # Padrão
            "rsi_oversold": 30,           
            "rsi_overbought": 70,         
        }

        # Limites para otimização - faixas SCALPING VIÁVEL
        self.clamps = {
            "atr_len":        [10, 20, 30, 1],
            "atr_mult":       [2.0, 4.0, 6.0, 0.2],   # Brick Grande!
            "min_bricks":     [2, 3, 5, 1],           # Evitar ruído
            "rsi_len":        [7, 14, 21, 1],
            "rsi_oversold":   [20, 30, 40, 1],        
            "rsi_overbought": [60, 70, 80, 1],        
        }

    def indicators(self, data):
        """Calcula indicadores técnicos."""
        close = data["close"]
        high = data["high"]
        low = data["low"]
        
        # ATR para brick size dinâmico
        atr = qx.ti.atr(high, low, close, int(self.tune["atr_len"]))
        atr_clean = atr[~np.isnan(atr)]
        brick_size = np.mean(atr_clean) * self.tune["atr_mult"] if len(atr_clean) > 0 else 50.0
        
        # Bricks Renko
        bricks = self._calculate_renko(close, brick_size)
        
        # Contagem de bricks consecutivos
        consecutive = self._count_consecutive(bricks)
        
        # RSI rápido
        rsi = qx.ti.rsi(close, int(self.tune["rsi_len"]))
        
        return {
            "bricks": bricks,
            "consecutive": consecutive,
            "rsi": rsi,
            "brick_size": np.full_like(close, brick_size),
        }

    def _calculate_renko(self, close_prices, brick_size):
        """Calcula bricks Renko verdadeiros."""
        if len(close_prices) < 2 or brick_size <= 0:
            return np.zeros_like(close_prices)
        
        bricks = np.zeros(len(close_prices))
        last_price = close_prices[0]
        
        for i in range(1, len(close_prices)):
            price = close_prices[i]
            diff = price - last_price
            
            if diff >= brick_size:
                count = int(diff / brick_size)
                bricks[i] = count
                last_price += count * brick_size
            elif diff <= -brick_size:
                count = int(abs(diff) / brick_size)
                bricks[i] = -count
                last_price -= count * brick_size
        
        return bricks

    def _count_consecutive(self, bricks):
        """Conta bricks consecutivos."""
        consecutive = np.zeros_like(bricks)
        count = 0
        current_dir = 0
        
        for i in range(len(bricks)):
            if bricks[i] > 0:
                if current_dir == 1:
                    count += bricks[i]
                else:
                    count = bricks[i]
                    current_dir = 1
            elif bricks[i] < 0:
                if current_dir == -1:
                    count += abs(bricks[i])
                else:
                    count = abs(bricks[i])
                    current_dir = -1
            
            consecutive[i] = count * current_dir
        
        return consecutive

    def strategy(self, tick_info, indicators):
        """
        Lógica de decisão SCALPING.
        
        COMPRA: Bricks de alta >= min_bricks E RSI não sobrecomprado
        VENDA: Bricks de baixa >= min_bricks E RSI não sobrevendido
        """
        # Extrair valores - funciona para arrays (papertrade) e escalares (backtest)
        def get_last(val):
            if hasattr(val, "__len__") and not isinstance(val, str):
                return val[-1] if len(val) > 0 else 0
            return val

        consecutive = get_last(indicators.get("consecutive", 0))
        rsi = get_last(indicators.get("rsi", 50))
        
        min_bricks = int(self.tune["min_bricks"])
        oversold = self.tune["rsi_oversold"]
        overbought = self.tune["rsi_overbought"]
        
        # COMPRA: Momentum de alta confirmado
        long_signal = (
            consecutive >= min_bricks
            and rsi < overbought  # Não comprar topo
        )
        
        # VENDA: Momentum de baixa confirmado
        short_signal = (
            consecutive <= -min_bricks
            and rsi > oversold  # Não vender fundo
        )
        
        if long_signal and not short_signal:
            return qx.Buy()
        elif short_signal and not long_signal:
            return qx.Sell()
        
        return qx.Hold()

    def execution(self, signal, indicators, wallet):
        """Executa ordens no preço de mercado."""
        if isinstance(signal, qx.Buy):
            return qx.Buy()
        elif isinstance(signal, qx.Sell):
            return qx.Sell()
        return signal

    def plot(self, *args):
        """Define a visualização no gráfico."""
        qx.plot(
            self.info,
            *args,
            (
                ("consecutive", "Consecutive Bricks", "cyan", 1, "Renko Scalp"),
                ("rsi", "RSI", "white", 2, "RSI"),
            )
        )

    def fitness(self, states, raw_states, asset, currency):
        """Métricas de otimização."""
        return [
            "roi_currency",
            "roi",
            "cagr",
            "sortino",
            "maximum_drawdown",
            "trade_win_rate",
        ], {}


# ===========================================================================
# CONFIGURAÇÃO GLOBAL - SCALPING
# ===========================================================================
# 60=1m, 300=5m, 900=15m, 3600=1h, 14400=4h, 86400=1d
TIMEFRAME = 300  # 5 minutos (Solitado pelo usuário)
FEE = 0.1  # 0.1%

# ===========================================================================
# MAIN
# ===========================================================================
def main():
    """Configura e executa a estratégia."""

    asset, currency = "BTC", "USDT"
    # Começar com USDT é melhor para estratégias de compra/venda, pois evita a taxa inicial de venda de todo o BTC
    wallet = qx.PaperWallet({asset: 0, currency: 10000}, fee=FEE)  
    
    data = qx.Data(
        exchange="binance",
        asset=asset,
        currency=currency,
        begin="2025-12-01",  # Período unificado para resgatar os 95% de ROI
        #end="2026-01-14",  # Data fixa (opcional)
        end=int(time.time()), # Dados até o segundo atual (Unix Timestamp)
        candle_size=TIMEFRAME,
    )

    
    # python strategies/renko_scalp.py
    bot = RenkoScalp()
    qx.dispatch(bot, data, wallet)


if __name__ == "__main__":
    main()

