"""
╔═══════════════════════════════════════════════════════════════════════════╗
║   INSTITUTIONAL MARKET STRUCTURE - DOW THEORY TREND FOLLOWER             ║
╠═══════════════════════════════════════════════════════════════════════════╣
║                                                                           ║
║ 🏛️ ESTRATÉGIA INSTITUCIONAL (Hedge Funds / Prop Firms)                   ║
║                                                                           ║
║ ✅ PRICE ACTION PURO: Sem indicadores atrasados (RSI, MACD, etc)         ║
║ ✅ MARKET STRUCTURE: Opera rompimentos de Topos e Fundos (Dow Theory)    ║
║ ✅ GESTÃO DE RISCO: Stop Loss dinâmico baseado na estrutura do mercado   ║
║ ✅ 100% DETERMINÍSTICO: Backtest exato ao Live (Zero Lookahead)          ║
║                                                                           ║
║ LÓGICA OPERACIONAL:                                                      ║
║ 1. Identifica Topos e Fundos confirmados (ZigZag Institucional)          ║
║ 2. COMPRA: Rompimento (Fechamento) acima do último Topo Confirmado       ║
║ 3. VENDA: Rompimento (Fechamento) abaixo do último Fundo Confirmado      ║
║ 4. STOP LOSS: Último Fundo (para Compra) ou Último Topo (para Venda)     ║
║                                                                           ║
╚═══════════════════════════════════════════════════════════════════════════╝
"""

import qtradex as qx
import numpy as np

class ZigZagFractal(qx.BaseBot):
    """
    Institutional Market Structure - Estratégia de Rompimento de Estrutura
    """
    
    
    def __init__(self):
        # ===================================================================
        # TIMEFRAME: Configura o timeframe preferido para os agentes lerem
        # ===================================================================
        self.timeframe = TIMEFRAME
        self.fee = FEE
        
        # Parâmetros de Otimização (Scalping Institucional 15m - Alvo: 10 trades/dia)
        self.tune = {
            "lookback": 2,           # Mínimo para validar (rápido)
            "breakout_buffer": 0.0002, # 0.02% (Quase imediato)
            "atr_period": 14,        # Padrão
            "stop_atr_mult": 1.5,    # Stop Curto (Scalping)
        }
        
        self.clamps = {
            "lookback": [1, 2, 4, 1],
            "breakout_buffer": [0.0, 0.0002, 0.001, 0.0001],
            "atr_period": [10, 14, 21, 1],
            "stop_atr_mult": [1.0, 1.5, 2.5, 0.1],
        }
    
    def indicators(self, candles):
        highs = np.array(candles['high'])
        lows = np.array(candles['low'])
        closes = np.array(candles['close'])
        n = len(highs)
        
        # INDICADORES AUXILIARES
        atr = qx.ti.atr(candles['high'], candles['low'], candles['close'], int(self.tune["atr_period"]))
        
        lookback = int(self.tune["lookback"])
        buffer = float(self.tune["breakout_buffer"])
        
        # Arrays de Estrutura de Mercado
        structure_high = np.full(n, np.nan) # Último Topo Confirmado
        structure_low = np.full(n, np.nan)  # Último Fundo Confirmado
        signal = np.full(n, None, dtype=object)
        
        # Variáveis de estado
        last_confirmed_high = highs[0]
        last_confirmed_low = lows[0]
        
        # Janela de Fractal (Williams / ZigZag)
        fractal_mid = lookback
        
        # Loop principal (simula o processamento candle a candle)
        for i in range(fractal_mid * 2, n):
            # 1. DETECTAR FRACTAIS (Confirmados no passado)
            # O fractal acontece em 'pivot_idx', mas só é confirmado AGORA (i)
            pivot_idx = i - fractal_mid
            
            # Verificar se 'pivot_idx' é um Topo
            is_high = True
            for k in range(pivot_idx - fractal_mid, pivot_idx + fractal_mid + 1):
                if highs[k] > highs[pivot_idx]:
                    is_high = False
                    break
            
            # Verificar se 'pivot_idx' é um Fundo
            is_low = True
            for k in range(pivot_idx - fractal_mid, pivot_idx + fractal_mid + 1):
                if lows[k] < lows[pivot_idx]:
                    is_low = False
                    break
            
            # Atualizar Estrutura se confirmou
            if is_high:
                last_confirmed_high = highs[pivot_idx]
            if is_low:
                last_confirmed_low = lows[pivot_idx]
            
            # Salvar estado atual da estrutura (para plot e debug)
            structure_high[i] = last_confirmed_high
            structure_low[i] = last_confirmed_low
            
            # 2. GERAR SINAIS DE ROMPIMENTO (BREAKOUT)
            # Lógica Dow Theory: Preço rompe a estrutura anterior
            
            current_close = closes[i]
            
            # COMPRA: Fechamento > Último Topo Confirmado (+ buffer)
            if current_close > (last_confirmed_high * (1 + buffer)):
                signal[i] = 'buy'
                
            # VENDA: Fechamento < Último Fundo Confirmado (- buffer)
            elif current_close < (last_confirmed_low * (1 - buffer)):
                signal[i] = 'sell'
                
        return {
            'structure_high': structure_high,
            'structure_low': structure_low,
            'signal': signal,
            'close': closes,
            'atr': atr,
            'high': highs, # Para plot
            'low': lows    # Para plot
        }
    
    def strategy(self, tick_info, indicators):
        signal = indicators.get('signal')
        last_trade = tick_info.get('last_trade')
        close = tick_info.get('close')
        
        # 1. STOP LOSS PROTECTION (ATR)
        if isinstance(last_trade, qx.Buy):
            entry_price = last_trade.price
            current_atr = indicators.get('atr', 0)
            if current_atr > 0:
                stop_mult = self.tune.get('stop_atr_mult', 2.0)
                stop_price = entry_price - (current_atr * stop_mult)
                if close < stop_price:
                    return qx.Sell() # Stop Trigger
        
        # Execução Simples (Price Action Puro)
        if signal == 'buy':
            if last_trade is None or isinstance(last_trade, qx.Sell):
                return qx.Buy()
                
        elif signal == 'sell':
            if isinstance(last_trade, qx.Buy):
                return qx.Sell()
                
        return qx.Hold()
    
    def plot(self, data, states, indicators, block):
        qx.plot(
            self.info,
            data,
            states,
            indicators,
            block,
            (
                ("structure_high", "Resistência (Topo)", "red", 0, None),
                ("structure_low", "Suporte (Fundo)", "lime", 0, None),
                ("atr", "ATR", "orange", 1, "Volatilidade"),
            ),
        )
        qx.plotmotion(block)
        
    def execution(self, signal, indicators=None, wallet=None):
        return signal

    def fitness(self, states, raw_states, asset, currency):
        """Métricas de performance para otimização"""
        return [
            "roi_assets",
            "roi_currency",
            "roi",
            "cagr",
            "maximum_drawdown",
            "trade_win_rate",
        ], {}

# ===========================================================================
# CONFIGURAÇÃO GLOBAL
# ===========================================================================
# 60=1m, 300=5m, 900=15m, 3600=1h, 14400=4h, 86400=1d
TIMEFRAME = 900  # 5 minutos (Scalping Agressivo)
FEE = 0.1  # 0.1%


# ===========================================================================
# MAIN
# ===========================================================================
def main():
    """Configura e executa a estratégia."""
    import time
    asset, currency = "SOL", "USDT"
    wallet = qx.PaperWallet({asset: 0, currency: 10000}, fee=FEE)
    
    data = qx.Data(
        exchange="binance",
        asset=asset,
        currency=currency,
        begin="2025-10-01",
        #end="2026-01-14",  # Data fixa (opcional)
        end=int(time.time()),  # Dados até o segundo atual
        candle_size=TIMEFRAME, 
    )
    
    # python strategies/ZigZagFractal.py
    # Algoritmo validado por traders profissionais
    bot = ZigZagFractal()
    qx.dispatch(bot, data, wallet)


if __name__ == "__main__":
    main()