---
description: Ajustar parâmetros de estratégia para otimização em mercados voláteis (Cripto)
---
# Ajuste Padrão para Cripto Volátil

Aplica configuração otimizada para **cobertura ampla** em mercados de alta volatilidade como criptomoedas.

## Filosofia
- **Ranges AMPLOS**: O mercado cripto varia muito. Parâmetros estreitos limitam o AION.
- **Tune no MEIO**: Ponto de partida equilibrado para o otimizador explorar.
- **Steps moderados**: Granularidade suficiente sem explosão de combinações.

## Regras de Ajuste

### 1. self.tune (valores CENTRAIS)
```python
self.tune = {
    "parametro": (min + max) / 2,  # Sempre o centro do clamp
}
```

### 2. self.clamps (cobertura para VOLATILIDADE)
```python
# Formato: [min, padrão, max, step]
# Ranges devem cobrir desde condições calmas até explosões de volatilidade
```

## Ranges Padrão para Cripto

| Parâmetro | Min | Max | Step | Propósito |
|-----------|-----|-----|------|-----------|
| `atr_len` | 7 | 28 | 3 | Volatilidade curta (7) até longa (28) |
| `atr_mult` | 1.0 | 5.0 | 0.5 | Agressivo (1.0) até conservador (5.0) |
| `min_bricks` | 1 | 6 | 1 | Rápido (1) até confirmado (6) |
| `ema_trend` | 10 | 100 | 10 | Micro-trend (10) até macro (100) |
| `rsi_len` | 7 | 21 | 2 | Sensível (7) até suave (21) |
| `rsi_confirm_bull` | 50 | 75 | 3 | Momentum bull forte |
| `rsi_confirm_bear` | 25 | 50 | 3 | Momentum bear forte |

## Exemplo (Renko para Cripto)

```python
self.tune = {
    "atr_len": 14,
    "atr_mult": 2.5,
    "min_bricks": 3,
    "ema_trend": 50,
    "rsi_len": 14,
    "rsi_confirm_bull": 60,
    "rsi_confirm_bear": 40,
}

self.clamps = {
    "atr_len":          [7, 14, 28, 3],
    "atr_mult":         [1.0, 2.0, 5.0, 0.5],
    "min_bricks":       [1, 2, 6, 1],
    "ema_trend":        [10, 30, 100, 10],
    "rsi_len":          [7, 14, 21, 2],
    "rsi_confirm_bull": [50, 60, 75, 3],
    "rsi_confirm_bear": [25, 40, 50, 3],
}
```

## Como Usar
Diga: **"Aplique o /ajuste-scalp na estratégia [nome]"**

O agente irá:
1. Identificar os parâmetros da estratégia
2. Definir `self.tune` com valores CENTRAIS
3. Expandir `self.clamps` para cobrir alta volatilidade
4. Usar steps balanceados (eficiência + granularidade)
