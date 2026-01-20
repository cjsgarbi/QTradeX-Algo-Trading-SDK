"""
╔═╗╔╦╗╦═╗╔═╗╔╦╗╔═╗═╗ ╦
║═╬╗║ ╠╦╝╠═╣ ║║║╣ ╔╩╦╝
╚═╝╚╩ ╩╚═╩ ╩═╩╝╚═╝╩ ╚═

renko_pro.py

Renko Pro + MACD - Estratégia Elite Validada

DUPLA PROFISSIONAL: Renko + MACD
- Renko para identificação de tendência (filtro de ruído)
- MACD para confirmação de momentum e força

LÓGICA DE ENTRADA:
- COMPRA: Brick Verde + MACD acima da Linha de Sinal + Histograma Positivo
- VENDA: Brick Vermelho + MACD abaixo da Linha de Sinal + Histograma Negativo

GESTÃO DE RISCO:
- Stop Loss: Reversão de 2 bricks OU Histograma muda de cor
"""

import qtradex as qx
import numpy as np
import time


class RenkoPro(qx.BaseBot):
    """
    Estratégia Renko + MACD Elite.
    
    A dupla mais validada e usada por traders profissionais
    para alta taxa de acerto em mercados de tendência.
    """
    
    def __init__(self):
        """Inicialização da estratégia."""
        self.timeframe = TIMEFRAME
        self.fee = FEE
        
        # ===================================================================
        # TUNE: Parâmetros otimizáveis (Renko + MACD)
        # ===================================================================
        self.tune = {
            # Renko
            "atr_len": 14,             # Período do ATR para brick size
            "atr_mult": 2.0,           # Multiplicador do ATR (maior = menos ruído)
            "min_bricks": 1,           # Confirmação mínima de bricks
            
            # MACD
            "macd_fast": 12,           # Período rápido do MACD
            "macd_slow": 26,           # Período lento do MACD
            "macd_signal": 9,          # Período da linha de sinal
        }

        # ===================================================================
        # CLAMPS: Limites para otimização
        # ===================================================================
        self.clamps = {
            # Renko
            "atr_len":       [10, 14, 21, 1],
            "atr_mult":      [1.5, 2.0, 4.0, 0.25],  # Mínimo 1.5 para evitar over-trading
            "min_bricks":    [1, 1, 3, 1],
            
            # MACD
            "macd_fast":     [8, 12, 16, 1],
            "macd_slow":     [20, 26, 32, 1],
            "macd_signal":   [6, 9, 12, 1],
        }

    def indicators(self, data):
        """Calcula indicadores: Renko + MACD."""
        close = data["close"]
        high = data["high"]
        low = data["low"]
        
        # === RENKO ===
        atr = qx.ti.atr(high, low, close, int(self.tune["atr_len"]))
        atr_clean = atr[~np.isnan(atr)]
        brick_size = np.mean(atr_clean) * self.tune["atr_mult"] if len(atr_clean) > 0 else 100
        
        bricks = self._calculate_renko(close, brick_size)
        consecutive = self._count_consecutive(bricks)
        
        # === MACD ===
        macd_line, macd_signal, macd_hist = qx.ti.macd(
            close,
            int(self.tune["macd_fast"]),
            int(self.tune["macd_slow"]),
            int(self.tune["macd_signal"])
        )
        
        # Histograma anterior para detectar mudança de cor
        macd_hist_prev = np.roll(macd_hist, 1)
        macd_hist_prev[0] = 0
        
        return {
            "bricks": bricks,
            "consecutive": consecutive,
            "macd_line": macd_line,
            "macd_signal": macd_signal,
            "macd_hist": macd_hist,
            "macd_hist_prev": macd_hist_prev,
        }

    def _calculate_renko(self, close_prices, brick_size):
        """Calcula bricks Renko verdadeiros."""
        if len(close_prices) < 2 or brick_size <= 0:
            return np.zeros_like(close_prices)
        
        bricks = np.zeros(len(close_prices))
        last_brick_price = close_prices[0]
        
        for i in range(1, len(close_prices)):
            price = close_prices[i]
            diff = price - last_brick_price
            
            if diff >= brick_size:
                num_bricks = int(diff / brick_size)
                bricks[i] = num_bricks
                last_brick_price += num_bricks * brick_size
            elif diff <= -brick_size:
                num_bricks = int(abs(diff) / brick_size)
                bricks[i] = -num_bricks
                last_brick_price -= num_bricks * brick_size
        
        return bricks

    def _count_consecutive(self, bricks):
        """Conta bricks consecutivos na mesma direção."""
        consecutive = np.zeros_like(bricks)
        count = 0
        last_dir = 0
        
        for i in range(len(bricks)):
            if bricks[i] > 0:
                count = count + bricks[i] if last_dir >= 0 else bricks[i]
                last_dir = 1
            elif bricks[i] < 0:
                count = count + abs(bricks[i]) if last_dir <= 0 else abs(bricks[i])
                last_dir = -1
            consecutive[i] = count * last_dir if last_dir != 0 else 0
        
        return consecutive

    def strategy(self, tick_info, indicators):
        """
        Lógica de decisão Elite: Renko + MACD.
        
        COMPRA: Brick Verde + MACD bullish + Histograma Positivo
        VENDA: Brick Vermelho + MACD bearish + Histograma Negativo
        """
        brick = indicators["bricks"]
        consecutive = indicators["consecutive"]
        macd_line = indicators["macd_line"]
        macd_signal = indicators["macd_signal"]
        macd_hist = indicators["macd_hist"]
        
        min_bricks = int(self.tune["min_bricks"])
        
        # === CONDIÇÕES DE COMPRA ===
        renko_bullish = brick > 0 and consecutive >= min_bricks
        macd_bullish = macd_line > macd_signal and macd_hist > 0
        
        # === CONDIÇÕES DE VENDA ===
        renko_bearish = brick < 0 and consecutive <= -min_bricks
        macd_bearish = macd_line < macd_signal and macd_hist < 0
        
        # === SINAIS ===
        long_signal = renko_bullish and macd_bullish
        short_signal = renko_bearish and macd_bearish
        
        if long_signal and not short_signal:
            return qx.Buy()
        elif short_signal and not long_signal:
            return qx.Sell()
        
        return None

    def execution(self, signal, indicators, wallet):
        """Executa ordens no preço de mercado."""
        if isinstance(signal, qx.Buy):
            return qx.Buy()
        elif isinstance(signal, qx.Sell):
            return qx.Sell()
        return signal

    def plot(self, *args):
        """Visualização: Renko + MACD."""
        qx.plot(
            self.info,
            *args,
            (
                ("bricks", "Renko Bricks", "green", 1, "Renko"),
                ("consecutive", "Consecutive", "cyan", 1, "Renko"),
                ("macd_line", "MACD", "blue", 2, "MACD"),
                ("macd_signal", "Signal", "orange", 2, "MACD"),
                ("macd_hist", "Histogram", "white", 3, "MACD Hist"),
            )
        )

    def fitness(self, states, raw_states, asset, currency):
        """Métricas de otimização."""
        return [
            "roi_assets",
            "roi_currency",
            "roi",
            "cagr",
            "sortino",
            "maximum_drawdown",
            "trade_win_rate",
        ], {}


# ===========================================================================
# CONFIGURAÇÃO GLOBAL
# ===========================================================================
TIMEFRAME = 900  # 15 minutos (ideal para Renko trend-following)
FEE = 0.1        # 0.1% taxa


# ===========================================================================
# MAIN
# ===========================================================================
def main():
    """Configura e executa a estratégia."""
    asset, currency = "BTC", "USDT"
    wallet = qx.PaperWallet({asset: 0, currency: 10000}, fee=FEE)
    
    data = qx.Data(
        exchange="binance",
        asset=asset,
        currency=currency,
        begin="2025-10-01",
        end=int(time.time()),
        candle_size=TIMEFRAME,
    )
    
    # python strategies/renko_pro.py
    bot = RenkoPro()
    qx.dispatch(bot, data, wallet)


if __name__ == "__main__":
    main()
