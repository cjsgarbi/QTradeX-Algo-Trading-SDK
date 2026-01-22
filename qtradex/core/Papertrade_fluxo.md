# 🛰️ QTradeX Engine: Especificações de Alta Performance (v2025.14)

Este documento define as responsabilidades fundamentais dos motores de execução (`papertrade.py` e `live.py`) para garantir operações de nível institucional com "Execução Relâmpago".

---

## 🏗️ As 4 Responsabilidades do Motor

### 1. Sincronismo de Eventos (Sensor de Candle) 🕒
O motor é o guardião do tempo. Ele não opera em intervalos fixos hardcoded, mas em **Eventos de Fechamento** definidos pelo `bot.timeframe`.
- **Ação**: Realiza polling de alta frequência no relógio do sistema.
- **Gatilho**: Identifica o exato milissegundo em que um candle é finalizado (seja 1min, 5min, 1h, 1d, etc.).
- **Objetivo**: Garantir que o robô tome decisões com dados 100% fechados e selados, independente do timeframe.

### 2. Gestão de Fluxo de Dados 🧠

#### 🟢 IMPLEMENTAÇÃO ATUAL (Segura)
O motor atua como um gerenciador de dados confiável, priorizando **integridade sobre velocidade**.
- **Método**: `update_candles()` - recria dados da janela completa a cada tick
- **Segurança**: Dados sempre consistentes, sem risco de dessincronização
- **Performance**: ~500ms por tick - adequado para timeframes de 1min ou maiores

#### 🔵 VERSÃO IDEAL (HFT - Não Implementada)
Para HFT (<1s), o motor deveria usar Rolling Buffer em RAM:
- **Método**: `stream_update()` - mantém buffer circular em RAM
- **Ação**: Ao receber candle `N+1`, apaga o candle `1` e anexa o novo
- **Performance**: <10ms por tick
- **Status**: Requer refatoração para garantir segurança

### 3. Garantia de Warmup (Aquecimento de Dados) 🔥
O motor assegura que o cérebro (estratégia) nunca sofra de "amnésia".
- **Ação**: Garante que em cada tick, a estratégia receba exatamente o histórico configurado em `bot.warmup` + o dado atual.
- **Objetivo**: Estabilidade absoluta no cálculo de indicadores técnicos sensíveis ao histórico (EMA, RSI, ATR).

### 4. Execução Agnóstica de Sinais 🎯
O motor é um executor cego e fiel. Ele não questiona a estratégia.
- **Ação**: Recebe o objeto de sinal (`Buy`, `Sell`, `Hold`) emitido por `bot.strategy()`.
- **Processamento**:
    - **Buy/Sell**: Executa ordens, atualiza a carteira e registra logs.
    - **Hold**: Reconhece o estado de "manutenção", registra o pulso e volta para o modo vigilância.
- **Objetivo**: Separação total entre a lógica de trading (Bot) e a infraestrutura de execução (Motor).

---

## ⚡ Filosofia "Segurança em Primeiro Lugar"
Para garantir que o trading **nunca falhe**, o motor prioriza integridade dos dados sobre velocidade extrema. Para timeframes de 1min ou maiores, a latência de ~500ms é imperceptível e garante dados sempre corretos.

---
**Guia Referência para Desenvolvedores QTradeX**
