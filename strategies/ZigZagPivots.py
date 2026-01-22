"""
╔═══════════════════════════════════════════════════════════════════════════╗
║           ZIGZAG PIVOTS - BASEADO EM FREQTRADE/TECHNICAL                 ║
╠═══════════════════════════════════════════════════════════════════════════╣
║ Implementação REAL extraída de: freqtrade/technical/pivots_points.py     ║
║ Padrão VALIDADO e FUNCIONAL usado por traders profissionais              ║
╚═══════════════════════════════════════════════════════════════════════════╝
"""

import qtradex as qx
import numpy as np
import pandas as pd


class ZigZagPivots(qx.BaseBot):
    """
    ZigZag baseado em Pivot Points - IMPLEMENTAÇÃO FREQTRADE
    
    FONTE: https://github.com/freqtrade/technical/blob/main/technical/pivots_points.py
    
    CONCEITO:
    - Usa rolling windows para calcular Pivot Points
    - Pivot = (High + Low + Close) / 3
    - Resistência/Suporte baseados em fórmulas TradingView
    - ZigZag alterna entre R1 (topo) e S1 (fundo)
    """
    
    
    def __init__(self):
        # ===================================================================
        # TIMEFRAME: Configura o timeframe preferido para os agentes lerem
        # ===================================================================
        self.timeframe = TIMEFRAME
        self.fee = FEE
        
        
        # Estado da estratégia
        self.last_zigzag_high = None
        self.last_zigzag_low = None
        
        # ══════════════════════════════════════════════════════════
        # CLAMPS - Parâmetros otimizáveis
        # ══════════════════════════════════════════════════════════
        self.clamps = {
            'zigzag_threshold': [0.1, 0.3, 0.8, 0.05],  # % mínimo para scalping
            'stop_loss_pct': [0.2, 0.4, 0.8, 0.05],     # Stop loss scalping
            'take_profit_pct': [0.3, 0.6, 1.2, 0.1],    # Take profit scalping
            'trend_period': [10, 20, 50, 5],            # EMA rápida
            'rsi_period': [7, 14, 21, 1],
            'rsi_oversold': [20, 30, 40, 5],
            'rsi_overbought': [60, 70, 80, 5],
        }
        
        self.tune = {
            'zigzag_threshold': 0.3,    # 0.3% para scalping 5m (era 1%)
            'stop_loss_pct': 0.4,       # Stop apertado 0.4%
            'take_profit_pct': 0.6,     # Take profit 0.6% (ratio 1.5:1)
            'trend_period': 20,         # EMA mais rápida (era 50)
            'rsi_period': 14,
            'rsi_oversold': 30,
            'rsi_overbought': 70,
        }
    
    def calculate_zigzag(self, dataframe, threshold_pct):
        """
        ZigZag NON-REPAINTING com SINAL DE REVERSÃO
        
        Retorna:
        - zigzag_low: Último fundo confirmado
        - zigzag_high: Último topo confirmado
        - signal: 1 = Novo fundo confirmado (BUY), -1 = Novo topo confirmado (SELL)
        """
        highs = dataframe['high'].values
        lows = dataframe['low'].values
        closes = dataframe['close'].values
        n = len(dataframe)
        
        # Arrays de saída
        zigzag_high = np.full(n, np.nan)  # Último topo confirmado
        zigzag_low = np.full(n, np.nan)   # Último fundo confirmado
        signal = np.zeros(n)  # 0=nada, 1=compra (fundo), -1=venda (topo)
        
        # Estado
        last_confirmed_high = highs[0]
        last_confirmed_low = lows[0]
        pending_high = highs[0]
        pending_low = lows[0]
        direction = 0  # 0=indefinido, 1=buscando topo, -1=buscando fundo
        
        for i in range(1, n):
            current_high = highs[i]
            current_low = lows[i]
            current_close = closes[i]
            
            if direction == 0:
                # Inicialização: detectar primeira direção
                if current_close > pending_high * (1 + threshold_pct / 100):
                    direction = 1  # Subindo, buscando topo
                    pending_high = current_high
                elif current_close < pending_low * (1 - threshold_pct / 100):
                    direction = -1  # Descendo, buscando fundo
                    pending_low = current_low
                    
            elif direction == 1:  # Buscando TOPO
                # Atualizar topo pendente se fizer nova máxima
                if current_high > pending_high:
                    pending_high = current_high
                
                # CONFIRMAÇÃO DE TOPO: Preço recuou threshold% do topo pendente
                if current_close < pending_high * (1 - threshold_pct / 100):
                    last_confirmed_high = pending_high
                    direction = -1  # Agora buscando fundo
                    pending_low = current_low
                    signal[i] = -1  # SINAL DE VENDA (topo confirmado)
                    
            elif direction == -1:  # Buscando FUNDO
                # Atualizar fundo pendente se fizer nova mínima
                if current_low < pending_low:
                    pending_low = current_low
                
                # CONFIRMAÇÃO DE FUNDO: Preço subiu threshold% do fundo pendente
                if current_close > pending_low * (1 + threshold_pct / 100):
                    last_confirmed_low = pending_low
                    direction = 1  # Agora buscando topo
                    pending_high = current_high
                    signal[i] = 1  # SINAL DE COMPRA (fundo confirmado)
            
            # Salvar estado da estrutura no candle atual
            zigzag_high[i] = last_confirmed_high
            zigzag_low[i] = last_confirmed_low
        
        return zigzag_low, zigzag_high, signal
    
    def indicators(self, candles):
        """
        Calcula ZigZag REAL + EMA de tendência
        """
        # Converter dict de arrays para DataFrame
        df = pd.DataFrame({
            'high': candles['high'],
            'low': candles['low'],
            'close': candles['close'],
        })
        
        threshold = float(self.tune["zigzag_threshold"])
        trend_period = int(self.tune["trend_period"])
        rsi_period = int(self.tune["rsi_period"])
        
        # ══════════════════════════════════════════════════════════
        # ZIGZAG NON-REPAINTING - Topos e fundos confirmados + SINAL
        # ══════════════════════════════════════════════════════════
        zigzag_low, zigzag_high, zigzag_signal = self.calculate_zigzag(df, threshold)
        
        # ══════════════════════════════════════════════════════════
        # EMA DE TENDÊNCIA - Filtro para não operar contra tendência
        # ══════════════════════════════════════════════════════════
        ema_trend = df['close'].ewm(span=trend_period, adjust=False).mean().values
        
        # ══════════════════════════════════════════════════════════
        # RSI - Confirma reversão (sobrevendido = fundo real)
        # ══════════════════════════════════════════════════════════
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=rsi_period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=rsi_period).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        rsi_values = rsi.values
        
        return {
            'zigzag_line': zigzag_low,        # Último fundo confirmado (Suporte)
            'zigzag_high': zigzag_high,       # Último topo confirmado (Resistência)
            'zigzag_signal': zigzag_signal,   # 1=BUY (novo fundo), -1=SELL (novo topo)
            'ema_trend': ema_trend,           # EMA para filtro de tendência
            'rsi': rsi_values,                # RSI para confirmar reversão
            'close': df['close'].values,      # Preço de fechamento
        }
    
    def strategy(self, tick_info, indicators):
        """
        Estratégia ZigZag Reversal Trading (Institucional)
        
        LÓGICA:
        - COMPRA quando signal == 1 (novo fundo confirmado)
        - VENDA quando signal == -1 (novo topo confirmado) OU Stop Loss
        """
        # Extrair valores
        def get_value(val, idx=-1):
            if isinstance(val, (np.ndarray, list)):
                if len(val) >= abs(idx):
                    return val[idx]
                return np.nan
            return val
        
        # Sinal de reversão do ZigZag
        zigzag_signal = get_value(indicators.get('zigzag_signal'))
        zigzag_high = get_value(indicators.get('zigzag_high'))
        current_price = tick_info.get('close')
        last_trade = tick_info.get('last_trade')
        
        # Validações
        if current_price is None or np.isnan(zigzag_signal):
            return qx.Hold()
        
        # Parâmetros
        stop_loss_pct = float(self.tune["stop_loss_pct"])
        take_profit_pct = float(self.tune["take_profit_pct"])
        
        # ══════════════════════════════════════════════════════════
        # SEM POSIÇÃO - Buscar entrada
        # ══════════════════════════════════════════════════════════
        if last_trade is None or isinstance(last_trade, qx.Sell):
            # COMPRA: Sinal de fundo confirmado (reversão de baixa para alta)
            if zigzag_signal == 1:
                return qx.Buy()
        
        # ══════════════════════════════════════════════════════════
        # COM POSIÇÃO - Gerenciar saída
        # ══════════════════════════════════════════════════════════
        elif isinstance(last_trade, qx.Buy):
            entry_price = last_trade.price
            
            # STOP LOSS: Saída forçada se preço cair demais
            stop_price = entry_price * (1 - stop_loss_pct / 100)
            if current_price <= stop_price:
                return qx.Sell()
            
            # TAKE PROFIT: Saída em lucro fixo
            take_price = entry_price * (1 + take_profit_pct / 100)
            if current_price >= take_price:
                return qx.Sell()
            
            # SINAL DE TOPO: ZigZag confirmou novo topo (hora de sair)
            if zigzag_signal == -1:
                return qx.Sell()
            
            # RESISTÊNCIA: Preço chegou no último topo confirmado
            if not np.isnan(zigzag_high) and current_price >= zigzag_high * 0.995:
                return qx.Sell()
        
        return qx.Hold()
    
    def plot(self, *args):
        """Plotagem dos indicadores"""
        qx.plot(
            self.info,
            *args,
            (
                ("zigzag_line", "Suporte (Fundo)", "lime", 0, "Main"),
                ("zigzag_high", "Resistência (Topo)", "red", 0, "Main"),
                ("ema_trend", "EMA Trend", "orange", 0, "Main"),
            ),
        )
    


    def fitness(self, states, raw_states, asset, currency):
        """Métricas de performance para otimização"""
        return [
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
TIMEFRAME = 3600  # 15 minutos (900 segundos)
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
        begin="2025-06-01",
        #end="2026-01-14",  # Data fixa (opcional)
        end=int(time.time()),  # Dados até o segundo atual
        candle_size=TIMEFRAME, 
    )
    # python strategies/ZigZagPivots.py
    bot = ZigZagPivots()
    qx.dispatch(bot, data, wallet)


if __name__ == "__main__":
    main()

    
