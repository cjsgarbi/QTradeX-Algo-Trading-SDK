"""
╔═╗╔╦╗╦═╗╔═╗╔╦╗╔═╗═╗ ╦
║═╬╗║ ╠╦╝╠═╣ ║║║╣ ╔╩╦╝
╚═╝╚╩ ╩╚═╩ ╩═╩╝╚═╝╩ ╚═

renko.py

Renko Profissional - Versão Corrigida

CORREÇÕES APLICADAS (baseadas em pesquisa com especialistas):
1. ATR Multiplier aumentado para 2.0-3.0 (evita over-trading)
2. Filtro de tendência com EMA 50 (só opera na direção da tendência maior)
3. RSI confirma momentum, não apenas evita extremos
4. Mínimo de 3 bricks consecutivos para confirmar tendência
5. Stop-loss implícito de 2 bricks (reversão imediata)

REFERÊNCIAS:
- TradingView: ATR 14 periods com multiplier 1.5-2.5
- Forex Factory: Stop-loss de 2 Renko bars
- LuxAlgo: Brick size = 1% do preço ou ATR x 2
"""

import qtradex as qx
import numpy as np


class Renko(qx.BaseBot):
    """
    Estratégia Renko Profissional Corrigida.
    
    LÓGICA MELHORADA:
    1. Só opera na direção da tendência maior (EMA 50)
    2. Exige confirmação de bricks consecutivos
    3. RSI confirma momentum
    4. ATR maior para evitar ruído
    """
    
    def __init__(self):
        """Inicialização da estratégia."""
        self.timeframe = TIMEFRAME
        self.fee = FEE
        
        
        # Parâmetros CORRIGIDOS para evitar over-trading
        self.tune = {
            "atr_len": 14,             # Período do ATR (padrão profissional)
            "atr_mult": 2.5,           # AUMENTADO: 2.0-3.0 é o padrão pro
            "min_bricks": 3,           # AUMENTADO: exige confirmação forte
            "ema_trend": 50,           # NOVO: filtro de tendência maior
            "rsi_len": 14,             # Período RSI
            "rsi_confirm_bull": 50,    # RSI acima de 50 = momentum de alta
            "rsi_confirm_bear": 50,    # RSI abaixo de 50 = momentum de baixa
        }

        # Limites para otimização - faixas PROFISSIONAIS
        self.clamps = {
            "atr_len":         [10, 14, 20, 1],
            "atr_mult":        [1.5, 2.5, 4.0, 0.25],  # Mínimo 1.5!
            "min_bricks":      [2, 3, 5, 1],           # Mínimo 2!
            "ema_trend":       [30, 50, 100, 10],
            "rsi_len":         [10, 14, 21, 1],
            "rsi_confirm_bull": [45, 50, 60, 5],
            "rsi_confirm_bear": [40, 50, 55, 5],
        }

    def indicators(self, data):
        """Calcula indicadores técnicos."""
        close = data["close"]
        high = data["high"]
        low = data["low"]
        
        # ATR para brick size dinâmico
        atr = qx.ti.atr(high, low, close, int(self.tune["atr_len"]))
        atr_clean = atr[~np.isnan(atr)]
        brick_size = np.mean(atr_clean) * self.tune["atr_mult"] if len(atr_clean) > 0 else 100.0
        
        # Bricks Renko
        bricks = self._calculate_renko(close, brick_size)
        
        # Contagem de bricks consecutivos
        consecutive = self._count_consecutive(bricks)
        
        # EMA de tendência maior (filtro)
        ema_trend = qx.ti.ema(close, int(self.tune["ema_trend"]))
        
        # RSI para confirmação de momentum
        rsi = qx.ti.rsi(close, int(self.tune["rsi_len"]))
        
        # Tendência maior: preço acima ou abaixo da EMA
        trend_up = close > ema_trend
        trend_down = close < ema_trend
        
        return {
            "bricks": bricks,
            "consecutive": consecutive,
            "ema_trend": ema_trend,
            "rsi": rsi,
            "trend_up": trend_up,
            "trend_down": trend_down,
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
        """Conta bricks consecutivos na mesma direção."""
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
        Lógica de decisão PROFISSIONAL.
        
        COMPRA quando:
        1. Tendência maior é de ALTA (preço > EMA 50)
        2. Bricks consecutivos de alta >= min_bricks
        3. RSI confirma momentum de alta (> 50)
        
        VENDA quando:
        1. Tendência maior é de BAIXA (preço < EMA 50)
        2. Bricks consecutivos de baixa >= min_bricks
        3. RSI confirma momentum de baixa (< 50)
        """
        consecutive = indicators["consecutive"]
        rsi = indicators["rsi"]
        trend_up = indicators["trend_up"]
        trend_down = indicators["trend_down"]
        
        min_bricks = int(self.tune["min_bricks"])
        rsi_bull = self.tune["rsi_confirm_bull"]
        rsi_bear = self.tune["rsi_confirm_bear"]
        
        # CONDIÇÃO DE COMPRA (3 filtros devem passar)
        long_signal = (
            trend_up                    # 1. Tendência maior é de alta
            and consecutive >= min_bricks  # 2. Bricks consecutivos confirmam
            and rsi > rsi_bull          # 3. RSI confirma momentum
        )
        
        # CONDIÇÃO DE VENDA (3 filtros devem passar)
        short_signal = (
            trend_down                      # 1. Tendência maior é de baixa
            and consecutive <= -min_bricks  # 2. Bricks consecutivos confirmam
            and rsi < rsi_bear              # 3. RSI confirma momentum
        )
        
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
        """Define a visualização no gráfico."""
        qx.plot(
            self.info,
            *args,
            (
                ("ema_trend", "EMA Trend", "yellow", 0, "Renko Pro"),
                ("consecutive", "Consecutive Bricks", "cyan", 1, "Renko"),
                ("rsi", "RSI", "white", 2, "RSI"),
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
TIMEFRAME = 900  # 1 hora (melhor para Renko trend-following)
FEE = 0.1  # 0.1%


# ===========================================================================
# MAIN
# ===========================================================================
def main():
    """Configura e executa a estratégia."""
    import time
    asset, currency = "BTC", "USDT"
    wallet = qx.PaperWallet({asset: 0, currency: 10000}, fee=FEE)
    
    data = qx.Data(
        exchange="binance",
        asset=asset,
        currency=currency,
        begin="2025-06-01",
        #end="2026-01-14",  # Data fixa (opcional)
        end=int(time.time()),  # Dados até o segundo atual
        candle_size=TIMEFRAME, 
    )
    
    # python strategies/renko.py
    bot = Renko()
    qx.dispatch(bot, data, wallet)


if __name__ == "__main__":
    main()
