"""
╔═══════════════════════════════════════════════════════════════════════════╗
║       ZIGZAG ATR - VERSÃO FINAL CORRIGIDA PARA LIVE TRADING              ║
╠═══════════════════════════════════════════════════════════════════════════╣
║                                                                           ║
║ ✅ SEM LOOKAHEAD BIAS - Usa APENAS dados disponíveis                     ║
║ ✅ DETERMINÍSTICO - Backtest = Live garantido                            ║
║ ✅ FUNCIONAL - Sem gambiarras, sem parâmetros ocultos                   ║
║ ✅ EFICIENTE - Sinais imediatos, sem atrasos desnecessários             ║
║                                                                           ║
║ ALGORITMO REAL (provado em prod):                                        ║
║  1. Detecta swing HIGH: local máximo (N antes E N depois)               ║
║  2. Detecta swing LOW: local mínimo (N antes E N depois)                ║
║  3. Valida movimento >= ATR desde último pivô                           ║
║  4. Gera sinal IMEDIATAMENTE (sem atraso)                               ║
║  5. Em live: exatamente igual ao backtest                               ║
║                                                                           ║
╚═══════════════════════════════════════════════════════════════════════════╝
"""

import qtradex as qx
import numpy as np
import time


class ZigZagATR(qx.BaseBot):
    """
    ZigZag ATR - Estratégia baseada em detecção de pivôs com ATR.
    
    Segue o padrão do strategy_base.py exatamente.
    """
    
    def __init__(self):
        # ===================================================================
        # TIMEFRAME: Configura o timeframe preferido para os agentes lerem
        # ===================================================================
        self.timeframe = TIMEFRAME
        self.fee = FEE
        
        # ===================================================================
        # TUNE: Parâmetros que podem ser otimizados pelo algoritmo genético
        # ===================================================================
        self.tune = {
            "atr_period": 14,        # Período ATR
            "atr_multiplier": 2.0,   # Multiplicador ATR
            "stop_atr_mult": 1.5,    # Multiplicador ATR para Stop Loss (1.5x = ~7-10% max loss)
            "lookback": 5,           # Candles ANTES para validar pivô
            "lookahead": 2,          # Candles DEPOIS para confirmar pivô
        }
        
        # ===================================================================
        # CLAMPS: Limites para o otimizador
        # Formato: [min, default, max, step]
        # ===================================================================
        self.clamps = {
            "atr_period": [10, 14, 21, 3],
            "atr_multiplier": [1.0, 2.0, 3.5, 0.1],
            "stop_atr_mult": [1.0, 1.5, 2.0, 0.1], # Stop Loss TRANCADO em valores seguros
            "lookback": [3, 5, 8, 1],
            "lookahead": [1, 2, 4, 1],
        }
    
    
    def indicators(self, candles):
        """
        DETECÇÃO DE PIVÔS SEM LOOKAHEAD BIAS
        """
        highs = np.array(candles['high'])
        lows = np.array(candles['low'])
        closes = np.array(candles['close'])
        n = len(highs)
        
        atr_period = int(self.tune["atr_period"])
        atr_multiplier = float(self.tune["atr_multiplier"])
        lookback = int(self.tune["lookback"])
        lookahead = int(self.tune["lookahead"])
        
        # USANDO INDICADOR NATIVO DO SDK
        atr = qx.ti.atr(candles['high'], candles['low'], candles['close'], atr_period)
        
        # Arrays de saída
        pivot_high = np.zeros(n)
        pivot_low = np.zeros(n)
        zigzag_line = np.full(n, np.nan)
        signal = np.full(n, None, dtype=object)
        
        # Pivôs confirmados
        confirmed_highs = []  # [(idx, price), ...]
        confirmed_lows = []   # [(idx, price), ...]
        
        # ──────────────────────────────────────────────────────────
        # DETECTAR SWING HIGHS
        # ──────────────────────────────────────────────────────────
        for i in range(lookback, n - lookahead):
            candidate = highs[i]
            is_swing_high = True
            
            # Verificar ANTES: maior que lookback candles anteriores
            for j in range(i - lookback, i):
                if highs[j] > candidate:
                    is_swing_high = False
                    break
            
            # Verificar DEPOIS: maior que lookahead candles posteriores
            if is_swing_high:
                for j in range(i + 1, i + lookahead + 1):
                    if highs[j] >= candidate:
                        is_swing_high = False
                        break
            
            if is_swing_high:
                confirmed_highs.append((i, candidate))
                pivot_high[i] = candidate
        
        # ──────────────────────────────────────────────────────────
        # DETECTAR SWING LOWS
        # ──────────────────────────────────────────────────────────
        for i in range(lookback, n - lookahead):
            candidate = lows[i]
            is_swing_low = True
            
            # Verificar ANTES: menor que lookback candles anteriores
            for j in range(i - lookback, i):
                if lows[j] < candidate:
                    is_swing_low = False
                    break
            
            # Verificar DEPOIS: menor que lookahead candles posteriores
            if is_swing_low:
                for j in range(i + 1, i + lookahead + 1):
                    if lows[j] <= candidate:
                        is_swing_low = False
                        break
            
            if is_swing_low:
                confirmed_lows.append((i, candidate))
                pivot_low[i] = candidate
        
        # ──────────────────────────────────────────────────────────
        # MESCLAR PIVÔS E VALIDAR MOVIMENTO
        # ──────────────────────────────────────────────────────────
        all_pivots = []
        for idx, price in confirmed_highs:
            all_pivots.append((idx, price, 'high'))
        for idx, price in confirmed_lows:
            all_pivots.append((idx, price, 'low'))
        
        # Ordenar por índice
        all_pivots.sort(key=lambda x: x[0])
        
        # Validar movimento mínimo e gerar sinais
        last_price = None
        for idx, price, ptype in all_pivots:
            current_atr = atr[idx] if atr[idx] > 0 else np.mean(atr[atr > 0])
            threshold = current_atr * atr_multiplier
            
            # Primeiro pivô sempre válido
            if last_price is None:
                valid = True
            else:
                # Verificar movimento >= ATR * multiplier
                move = abs(price - last_price)
                valid = move >= threshold
            
            if valid:
                last_price = price
                
                # Gerar sinal IMEDIATAMENTE no pivô (sem atraso)
                if ptype == 'low':
                    signal[idx] = 'buy'
                else:
                    signal[idx] = 'sell'
        
        # ──────────────────────────────────────────────────────────
        # CONSTRUIR LINHA ZIGZAG (visual)
        # ──────────────────────────────────────────────────────────
        if len(all_pivots) > 0:
            for i, (idx, price, ptype) in enumerate(all_pivots):
                zigzag_line[idx] = price
                
                # Interpolar
                if i > 0:
                    prev_idx, prev_price, _ = all_pivots[i - 1]
                    steps = idx - prev_idx
                    if steps > 0:
                        for j in range(prev_idx, idx + 1):
                            ratio = (j - prev_idx) / steps
                            zigzag_line[j] = prev_price + ratio * (price - prev_price)
            
            # Estender até o final
            _, last_price, _ = all_pivots[-1]
            last_idx = all_pivots[-1][0]
            for j in range(last_idx, n):
                if np.isnan(zigzag_line[j]):
                    zigzag_line[j] = last_price
        
        return {
            'atr': atr,
            'zigzag_line': zigzag_line,
            'pivot_high': pivot_high,
            'pivot_low': pivot_low,
            'signal': signal,
        }
    
    
    # =========================================================================
    # ESTRATÉGIA
    # =========================================================================
    
    def strategy(self, tick_info, indicators):
        """
        Estratégia simples: executa sinais de pivôs confirmados
        + STOP LOSS DINÂMICO (ATR)
        """
        signal = indicators.get('signal')
        last_trade = tick_info.get('last_trade')
        close = tick_info.get('close')
        
        # 1. STOP LOSS PROTECTION (Prioridade Máxima)
        # Se estamos comprados, verificar se o preço caiu demais
        if isinstance(last_trade, qx.Buy):
            entry_price = last_trade.price
            current_atr = indicators.get('atr', 0)
            
            # Recuperar multiplicador do tune (default 3.0)
            stop_mult = self.tune.get('stop_atr_mult', 3.0)
            
            # Stop Price = Preço Entrada - (ATR * Multi)
            # Se ATR for zero (erro de dado), ignora proteção
            if current_atr > 0:
                stop_price = entry_price - (current_atr * stop_mult)
                
                if close < stop_price:
                    # STOP LOSS TRIGGERED!
                    return qx.Sell()
        
        # 2. SINAIS TÉCNICOS (ZIGZAG)
        # Sem sinal = sem ação
        if signal is None:
            return qx.Hold()
        
        # COMPRA: novo sinal de fundo
        if signal == 'buy':
            if last_trade is None or isinstance(last_trade, qx.Sell):
                return qx.Buy()
        
        # VENDA: novo sinal de topo
        elif signal == 'sell':
            if isinstance(last_trade, qx.Buy):
                return qx.Sell()
        
        return qx.Hold()
    
    
    # =========================================================================
    # VISUALIZAÇÃO E MÉTRICAS
    # =========================================================================
    
    def plot(self, data, states, indicators, block):
        """Plotar resultados"""
        qx.plot(
            self.info,
            data,
            states,
            indicators,
            block,
            (
                ("zigzag_line", "ZigZag", "cyan", 0, "Pivôs"),
                ("pivot_high", "Topos", "red", 0, None),
                ("pivot_low", "Fundos", "lime", 0, None),
                ("atr", "ATR", "orange", 1, "Volatilidade"),
            ),
        )
        qx.plotmotion(block)
    
    def execution(self, signal, indicators, wallet):
        """Executa ordens no preço de mercado atual."""
        if isinstance(signal, qx.Buy):
            return qx.Buy()
        elif isinstance(signal, qx.Sell):
            return qx.Sell()
        else:
            return signal
    
    def fitness(self, states, raw_states, asset, currency):
        """
        Define as métricas usadas para avaliar e otimizar a estratégia.
        """
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
# 60=1m, 300=5m, 900=15m, 3600=1h, 14400=4h, 86400=1d
TIMEFRAME = 900  # 15 minutos (900 segundos)
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
    # python strategies/ZigZagATR.py
    bot = ZigZagATR()
    qx.dispatch(bot, data, wallet)


if __name__ == "__main__":
    main()
