# Guia Técnico: Sistema de Relatório Universal de Trades (Round-Trips)

Este documento descreve detalhadamente como implementar o sistema de agrupamento de ordens para backtests, garantindo que o relatório seja intuitivo tanto para **Spot** quanto para **Futuros**.

## 1. Conceito Fundamental
Em vez de listar cada sinal isoladamente (Buy, Sell), o sistema identifica o **início** e o **fim** de uma operação. O lucro só é contabilizado no fechamento.

## 2. A Lógica de Pareamento (Core Logic)

Para implementar isso no `backtest.py`, usamos um sistema de "Memória de Entrada":

```python
open_trade = None  # Variável para guardar a entrada
pair_count = 0     # Contador de trades fechados

for op in states["detailed_trades"]:
    if open_trade is None:
        # Se não há nada aberto, este sinal é uma ENTRADA
        open_trade = op
        continue
    
    # Se já há uma entrada guardada, este sinal é uma SAÍDA
    # Realizamos o pareamento aqui
    entry_op = open_trade["object"]
    exit_op = op["object"]
    
    # Processamos o trade (calculamos lucro, preços e cores)
    ...
    
    # Resetamos a memória para o próximo trade
    open_trade = None
```

## 3. Diferenciando Spot e Futuros
O sistema detecta o tipo de operação baseando-se na primeira ordem do par:

| Tipo | Ordem de Entrada | Ordem de Saída | Lógica |
| :--- | :--- | :--- | :--- |
| **Spot / Long** | `Buy` | `Sell` | Ganha se Preço Saída > Preço Entrada |
| **Futures / Short** | `Sell` | `Buy` | Ganha se Preço Saída < Preço Entrada |

## 4. Estrutura Visual do Log
O log deve ser formatado para máxima clareza:

`[ID] [DATA_FECHAMENTO] AÇÃO_ENTRADA(Preço) -> AÇÃO_SAÍDA(Preço) | RESULTADO %`

### Exemplos do Novo Log Visual:

**Cenário Spot (Long):**
```text
[001] [Tue Jul 15 13:30:00 2025] BUY(60,000.00)  -> SELL(65,000.00) | WIN 8.33%  (Verde)
[003] [Thu Jul 17 15:30:00 2025] BUY(63,000.00)  -> SELL(62,000.00) | LOSS 1.59% (Vermelho)
```

**Cenário Futuros (Short):**
```text
[002] [Wed Jul 16 14:00:00 2025] SELL(65,000.00) -> BUY(61,000.00)  | WIN 6.15%  (Verde)
```

## 5. Ajuste de Métricas (Win Rate)
Para que o Win Rate seja honesto, ele deve ser calculado sobre os **trades fechados**:

`Win Rate = (Trades com Lucro / Total de Trades Fechados) * 100`

> [!IMPORTANT]
> Nunca use o número de sinais (Buy/Sell) para o Win Rate em estratégias de Spot, pois isso causa o erro de "vitória na compra" (Win no Buy).

## 6. Caso de Exceção: Operação Aberta
Sempre verifique se restou um `open_trade` ao final do loop. Se sim, informe ao usuário que existe uma operação pendente que não entrou no cálculo de lucro final.
