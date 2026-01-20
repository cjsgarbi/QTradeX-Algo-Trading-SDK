"""
QTradeX Strategy Template
=========================

IMPORTANTE: Este arquivo serve como template para criar novas estratégias.
Qualquer IA ou desenvolvedor deve seguir este padrão EXATAMENTE.

ESTRUTURA OBRIGATÓRIA:
----------------------
1. IMPORTS: Importar qtradex e numpy
2. TIMEFRAME: Variável global que define o tempo gráfico (em segundos)
3. CLASSE: Herdar de qx.BaseBot
   - __init__: Definir self.timeframe, self.tune e self.clamps
   - indicators: Calcular indicadores técnicos
   - strategy: Lógica de compra/venda
   - execution: Define preço de execução (obrigatório para Paper/Live)
   - plot: Visualização (opcional mas recomendado)
   - fitness: Métricas de otimização
4. MAIN: Função de entrada que configura Data e Dispatch

VALORES DE TIMEFRAME:
--------------------
- 60     = 1 minuto
- 300    = 5 minutos
- 900    = 15 minutos
- 3600   = 1 hora
- 14400  = 4 horas
- 86400  = 1 dia

SINAIS DE TRADING:
-----------------
- qx.Buy()                    : Compra a mercado
- qx.Buy(preco)               : Compra limite no preço especificado
- qx.Sell()                   : Venda a mercado
- qx.Sell(preco)              : Venda limite no preço especificado
- qx.Thresholds(buying, selling) : Ordens limite dinâmicas (compra e venda)
- qx.Hold()                   : Manter posição atual (não fazer nada)
- return None                 : Mesmo que Hold

INDICADORES DISPONÍVEIS (qx.ti):
-------------------------------
- qx.ti.ema(data, period)     : Média Móvel Exponencial
- qx.ti.sma(data, period)     : Média Móvel Simples
- qx.ti.rsi(data, period)     : Índice de Força Relativa
- qx.ti.macd(data, fast, slow, signal) : MACD
- qx.ti.bbands(data, period, std) : Bandas de Bollinger
- qx.ti.atr(high, low, close, period) : Average True Range
- qx.ti.stoch(high, low, close, period) : Estocástico
- E muitos outros...

DADOS DISPONÍVEIS em strategy():
-------------------------------
tick_info (dict):
  - "close"      : Preço de fechamento atual
  - "open"       : Preço de abertura
  - "high"       : Máxima do candle
  - "low"        : Mínima do candle
  - "volume"     : Volume
  - "unix"       : Timestamp Unix
  - "wallet"     : Objeto da carteira (somente leitura)
  - "last_trade" : Última operação (qx.Buy, qx.Sell ou None)

indicators (dict):
  - Contém os valores calculados no método indicators() para este tick
  - As chaves são as mesmas definidas no retorno de indicators()

REGRAS DE NOMENCLATURA:
----------------------
- Parâmetros com sufixo "_period" são automaticamente ajustados
  pelo SDK quando o timeframe muda (ex: rsi_period, ma_period)
- Use nomes descritivos em inglês para os parâmetros

CLAMPS (limites de otimização):
------------------------------
Formato: [min, default, max, step]
- min: Valor mínimo permitido
- default: Valor inicial para otimização
- max: Valor máximo permitido  
- step: Tamanho do passo (precisão). Valores típicos: 0.5, 1, 0.1

Exemplo:
    self.clamps = {
        "rsi_period": [5, 14, 30, 1],      # Inteiro de 5 a 30
        "threshold": [0.01, 0.05, 0.1, 0.01], # Float de 0.01 a 0.1
    }

USO:
----
1. Copie este arquivo: cp strategy_base.py minha_estrategia.py
2. Renomeie a classe: class MinhaEstrategia(qx.BaseBot)
3. Implemente sua lógica em indicators() e strategy()
4. Execute: python strategies/minha_estrategia.py
"""

import qtradex as qx
import numpy as np
from datetime import datetime
import time

class strategy_base(qx.BaseBot):
    """
    Classe base para estratégias QTradeX.
    
    Toda estratégia deve herdar de qx.BaseBot e implementar os métodos:
    - __init__: Configuração inicial
    - indicators: Cálculo de indicadores técnicos
    - strategy: Lógica de decisão de compra/venda
    - plot: Visualização (opcional)
    - fitness: Métricas para otimização
    """
    
    def __init__(self):
        """
        Inicialização da estratégia.
        
        OBRIGATÓRIO definir:
        - self.timeframe: Referência ao TIMEFRAME global
        - self.tune: Dicionário com parâmetros otimizáveis
        - self.clamps: Dicionário com limites de otimização
        """
        # ===================================================================
        # TIMEFRAME: Configura o timeframe preferido para os agentes lerem
        # ===================================================================
        self.timeframe = TIMEFRAME
        
        # ===================================================================
        # TUNE: Parâmetros que podem ser otimizados pelo algoritmo genético
        # ===================================================================
        # Dica: Use sufixo "_period" para períodos de indicadores
        # O SDK ajusta automaticamente esses valores para diferentes timeframes
        self.tune = {
            "period_fast": 12,       # Período da média rápida
            "period_slow": 26,       # Período da média lenta
            "rsi_period": 14,        # Período do RSI
            "rsi_threshold": 30,     # Limiar de sobrevendido
        }

        # ===================================================================
        # CLAMPS: Limites para o otimizador
        # Formato: (min, max) ou [min, default, max, step]
        # ===================================================================
        self.clamps = {
            # [min, default, max, step]
            "period_fast": [5, 12, 50, 1],
            "period_slow": [20, 26, 100, 1],
            "rsi_period": [5, 14, 30, 1],
            "rsi_threshold": [20, 30, 80, 1],
        }

    def indicators(self, data):
        """
        Calcula indicadores técnicos.
        
        Args:
            data (dict): Dados de mercado com as chaves:
                - "open": Array de preços de abertura
                - "high": Array de máximas
                - "low": Array de mínimas
                - "close": Array de preços de fechamento
                - "volume": Array de volumes
                - "unix": Array de timestamps
        
        Returns:
            dict: Dicionário com indicadores calculados.
                  As chaves definidas aqui estarão disponíveis em strategy()
        """
        return {
            "fast_ema": qx.ti.ema(data["close"], self.tune["period_fast"]),
            "slow_ema": qx.ti.ema(data["close"], self.tune["period_slow"]),
            "rsi": qx.ti.rsi(data["close"], self.tune["rsi_period"]),
        }

    def strategy(self, tick_info, indicators):
        """
        Lógica de decisão de trading. Chamado a cada candle/tick.
        
        Args:
            tick_info (dict): Informações do tick atual:
                - "close": Preço de fechamento
                - "open": Preço de abertura
                - "high": Máxima
                - "low": Mínima
                - "unix": Timestamp
                - "wallet": Carteira (somente leitura)
                - "last_trade": Última operação (Buy/Sell/None)
                
            indicators (dict): Valores dos indicadores para ESTE tick.
                               Chaves correspondem ao retorno de indicators()
        
        Returns:
            - qx.Buy(): Sinal de compra
            - qx.Buy(preco): Ordem limite de compra
            - qx.Sell(): Sinal de venda
            - qx.Sell(preco): Ordem limite de venda
            - qx.Thresholds(buying=X, selling=Y): Ordens dinâmicas
            - qx.Hold(): Manter posição
            - None: Mesmo que Hold
        """
        # Obtém valores dos indicadores para este tick
        fast = indicators["fast_ema"]
        slow = indicators["slow_ema"]
        rsi = indicators["rsi"]
        
        # --- REGRAS DE ENTRADA ---
        # Compra quando: EMA rápida cruza acima da lenta E RSI favorável
        if fast > slow and rsi < self.tune["rsi_threshold"]:
            return qx.Buy()
            
        # --- REGRAS DE SAÍDA ---
        # Vende quando: EMA rápida cruza abaixo da lenta
        elif fast < slow:
            return qx.Sell()
            
        # --- ALTERNATIVA: THRESHOLDS DINÂMICOS ---
        # Para estratégias de limite/stop, use:
        # return qx.Thresholds(buying=preco_compra, selling=preco_venda)
        
        # Default: Não fazer nada (manter posição atual)
        return None

    def execution(self, signal, indicators, wallet):
        """
        Executa ordens no preço de mercado atual.
        
        Este método é chamado APÓS strategy() para determinar o preço
        exato de execução da ordem.
        
        Args:
            signal: O sinal retornado por strategy() (Buy/Sell/Thresholds)
            indicators: Valores dos indicadores para este tick
            wallet: Carteira atual
        
        Returns:
            - O mesmo signal (Market Order)
            - Ou um novo signal modificado
        """
        if isinstance(signal, qx.Buy):
            return qx.Buy()
        elif isinstance(signal, qx.Sell):
            return qx.Sell()
        else:
            return signal

    def plot(self, *args):
        """
        Define a visualização no gráfico.
        
        O formato da tupla de indicadores é:
        (chave_indicador, label, cor, painel, grupo)
        
        - chave_indicador: Deve corresponder a uma chave de indicators()
        - label: Nome exibido na legenda
        - cor: "yellow", "cyan", "white", "green", "red", etc.
        - painel: 0 = gráfico principal, 1+ = painéis separados
        - grupo: Nome do grupo (para agrupar indicadores na legenda)
        """
        qx.plot(
            self.info,
            *args,
            (
                ("fast_ema", "Fast EMA", "yellow", 0, "EMA"),
                ("slow_ema", "Slow EMA", "cyan",   0, "EMA"),
                ("rsi",      "RSI",      "white",  1, "RSI"),  # Painel 1 = janela separada
            )
        )

    def fitness(self, states, raw_states, asset, currency):
        """
        Define as métricas usadas para avaliar e otimizar a estratégia.
        
        Métricas disponíveis:
        - "roi_assets": Retorno em ativos
        - "roi_currency": Retorno em moeda
        - "roi": Retorno geral
        - "cagr": Taxa de crescimento anual composta
        - "sortino": Índice Sortino (risco ajustado)
        - "sharpe": Índice Sharpe
        - "maximum_drawdown": Drawdown máximo
        - "trade_win_rate": Taxa de acerto
        - "profit_factor": Fator de lucro
        
        Returns:
            tuple: (lista_de_metricas, dict_customizado)
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
# CONFIGURAÇÃO GLOBAL DE TEMPO GRÁFICO
# ===========================================================================
# Esta variável controla o timeframe para TODOS os modos de operação:
# - Backtest: Define o tamanho dos candles históricos
# - Otimização: Usa o mesmo timeframe do backtest
# - Paper Trading: Define o intervalo entre cada tick de decisão
# - Live Trading: Define o intervalo entre cada tick de decisão real
#
# IMPORTANTE: Ao mudar este valor, todos os agentes se ajustam automaticamente.
# ===========================================================================

# --- CONFIGURACAO GLOBAL DE TEMPO GRAFICO ---
# Timeframe usado por todos os agentes (Backtest, Otimizadores, Paper, Live)

# 60=1m, 300=5m, 900=15m, 3600=1h, 14400=4h, 86400=1d
TIMEFRAME = 300 
# Taxa de corretagem (0.1 = 0.1%)
FEE       = 0.1 

# ===========================================================================
# FUNÇÃO MAIN - PONTO DE ENTRADA
# ===========================================================================
def main():
    """
    Configura e executa a estratégia.
    
    IMPORTANTE:
    - candle_size=TIMEFRAME: Obrigatório para Backtest/Otimização
    - tick_size=TIMEFRAME: Obrigatório para Paper/Live Trading
    """
    
    asset, currency = "BTC", "USDT"
    # IMPORTANTE: Começar com USDT evita taxas iniciais de venda e distorção do ROI
    wallet = qx.PaperWallet({asset: 0, currency: 10000}, fee=FEE)
    
    data = qx.Data(
        exchange="binance",
        asset=asset,
        currency=currency,
        begin="2026-01-01",
        end=int(time.time()),   # Dados até o segundo atual (Unix Timestamp)
        candle_size=TIMEFRAME,  # OBRIGATÓRIO: Define timeframe para Backtest
    )
    
    # Executa: python strategies/strategy_base.py   
    bot = strategy_base()
    
    # OBRIGATÓRIO: tick_size garante mesmo timeframe no Paper/Live
    qx.dispatch(bot, data, wallet)


if __name__ == "__main__":
    main()
