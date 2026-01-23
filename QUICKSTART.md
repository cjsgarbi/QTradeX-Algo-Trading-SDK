# QX Framework: Writing a New Bot

The **QX Framework** is a powerful and flexible platform for creating and backtesting trading bots. In this guide, we'll walk you through the process of creating a new bot from scratch, detailing key concepts, configuration options, and strategies.

For examples on how to build bots for QX, see [this repository](https://github.com/squidKid-deluxe/qtradex-ai-agents).

## Table of Contents

1. [Introduction](#introduction)
2. [Prerequisites](#prerequisites)
3. [Creating a New Bot](#creating-a-new-bot)
    1. [Bot Structure](#bot-structure)
    2. [Configuring the Bot Parameters](#configuring-the-bot-parameters)
    3. [Defining Indicators](#defining-indicators)
    4. [Building a Strategy](#building-a-strategy)
4. [Testing and Backtesting](#testing-and-backtesting)
5. [Plotting and Visualization](#plotting-and-visualization)
6. [Optimizing the Bot](#optimizing-the-bot)
7. [Deployment](#deployment)
8. [Advanced Topics](#advanced-topics)
9. [Resources and Documentation](#resources-and-documentation)

---

## Introduction

The QX framework allows you to write sophisticated trading bots that interact with various cryptocurrency exchanges. By providing high-level abstractions for trading strategies, risk management, and data handling, QX simplifies the development process for algorithmic traders. This guide will help you create a bot, configure it, and deploy it to trade in various market conditions.

---

## Prerequisites

Before you begin, ensure you have the following:

1. **Python 3.9+**: The QX framework relies on Python, so make sure you have Python 3.9 or higher installed.
2. **QX Framework**: Install QX using pip:
   ```bash
   pip install qtradex
   ```
3. **Knowledge of Trading Concepts**: Familiarity with trading concepts (e.g., moving averages, stop loss, take profit, etc.) will be helpful.
4. **API Key for Exchange**: You'll need an API key from an exchange (e.g., Poloniex, Binance) for live trading or backtesting.

---

## Creating a New Bot

To create a new bot, you will subclass the `qx.core.BaseBot` class. This base class provides several methods and functionalities that can be customized to define your own trading logic.

### Bot Structure

A QX bot generally consists of the following components:

- **Initialization (`__init__`)**: Set up parameters and initial values.
- **Indicators**: Define the technical indicators that your bot will use to make decisions (e.g., moving averages, RSI, MACD).
- **Strategy**: Define the trading logic — the rules for buying, selling, and holding positions.
- **Fitness**: Define the performance metrics (e.g., ROI, Sortino ratio) used for evaluating the bot’s success.
- **Plotting**: Visualize the bot's trades and indicators.
- **Autorange**: Automatically adjust parameters based on market conditions.

#### Example Bot Template:

```python
import qtradex as qx
from qtradex.private.signals import Buy, Sell, Thresholds

class Bot(qx.core.BaseBot):
    def __init__(self):
        self.tune = {
            "ema": 14,
            "std": 14,
            "buy_factor": 1.05,
            "sell_factor": 0.95,
        }
        self.clamps = [
            [5, 100, 0.5],  # Clamps for period of EMA
            [1.0, 4.0, 0.5],  # Clamps for Standard Deviation
        ]

    def indicators(self, data):
        metrics = {}
        metrics["ema"] = qx.ti.ema(data["close"], self.tune["ema"])
        metrics["std"] = qx.ti.stddev(data["close"], self.tune["std"])
        return metrics

    def strategy(self, tick_info, indicators):
        price = tick_info["close"]
        ema = indicators["ema"]
        std = indicators["std"]

        # Example trading strategy
        if price < ema - std * self.tune["buy_factor"]:
            return Buy()
        elif price > ema + std * self.tune["sell_factor"]:
            return Sell()
        else:
            return Thresholds(buying=price, selling=price)

    def fitness(self, states, raw_states, asset, currency):
        return ["roi", "cagr", "sortino", "maximum_drawdown"], {}

```

---

### Configuring the Bot Parameters

The bot's behavior is largely controlled by the `tune` dictionary, which contains various parameters for the indicators, strategy coefficients, and other configurable values.

Example parameters:
- **EMA period**: The period for the Exponential Moving Average (EMA).
- **Standard Deviation (Std)**: Used for calculating Bollinger Bands or volatility channels.
- **Buy/Sell factors**: Adjust factors for buying or selling based on indicator thresholds.

These parameters can be manually configured in the bot, or they can be optimized automatically using QX's optimization features.

---

### Defining Indicators

Indicators are key to the decision-making process of your trading strategy. In QX, the library provides various built-in indicators like EMA, RSI, Bollinger Bands, and Parabolic SAR. You can also define custom indicators if needed.

#### Example Indicators:

```python
def indicators(self, data):
    metrics = {}
    metrics["ema"] = qx.ti.ema(data["close"], self.tune["ema"])
    metrics["std"] = qx.ti.stddev(data["close"], self.tune["std"])
    return metrics
```

In this example, we use the project's native technical indicators (`qx.ti`) to calculate the **Exponential Moving Average (EMA)** and **Standard Deviation (STD)** for the closing price.

---

### Building a Strategy

The `strategy` method defines the logic for deciding when to buy, sell, or hold. This logic is based on the indicators you've defined in the `indicators` method.

#### Example Strategy:

```python
def strategy(self, tick_info, indicators):
    price = tick_info["close"]
    ema = indicators["ema"]
    std = indicators["std"]

    # Buy when the price is lower than the lower band (EMA - STD)
    if price < ema - std * self.tune["buy_factor"]:
        return Buy()

    # Sell when the price is higher than the upper band (EMA + STD)
    elif price > ema + std * self.tune["sell_factor"]:
        return Sell()

    # Otherwise, hold
    return Thresholds(buying=price, selling=price)
```

The strategy uses the **EMA** and **Standard Deviation** to calculate an upper and lower band. The bot will buy if the price is below the lower band and sell if it’s above the upper band.

---

## Testing and Backtesting

Once your bot is ready, you can backtest it using historical data. QX provides the `qx.core.dispatch()` function, which runs the bot on the provided data.

#### Example Backtesting:

```python
def main():
    asset, currency = "BTC", "USDT"
    wallet = qx.private.PaperWallet({asset: 1, currency: 0})
    data = qx.public.Data(
        exchange="poloniex",
        asset=asset,
        currency=currency,
        begin="2021-01-01",
        end="2023-01-01",
    )
    bot = Bot()
    qx.core.dispatch(bot, data, wallet)
```

In this example, the bot runs on historical data from the **Poloniex** exchange between **2021-01-01** and **2023-01-01**.

---

## Plotting and Visualization

QX provides built-in plotting functionality for visualizing your trading strategy. You can plot indicators, price data, and trades on the same chart.

#### Example Plotting:

```python
def plot(self, data, states, indicators, block):
    axes = qx.plot.plot(
        data,
        states,
        indicators,
        False,
        (
            ("ema", "EMA", "cyan", 0, "Exponential Moving Average"),
        ),
    )
    qx.plot.plotmotion(block)
```

This example plots the **EMA** indicator along with the trading data.

---

## Optimizing the Bot

You can optimize the bot’s parameters (e.g., EMA period, buy/sell factors) to find the best values for a given market. The QX framework allows you to automate this optimization process using the `qx.core.QPSO(data, wallet).optimize(bot)` method or by navigation in the `qx.core.dispatch` menu.

---

## Deployment

After you’ve written, tested, and optimized your bot, you can deploy it to live markets using real API keys. The deployment process involves:

1. **Obtaining API keys**: Get your API keys from your exchange (e.g., Binance, Poloniex).
2. **Connecting to the exchange**: Use the QX library to connect to the exchange and place real orders.

---

## Advanced Topics

### Risk Management

Risk management is an essential part of any trading bot. You can integrate stop-loss, take-profit, and position-sizing logic into your strategy to manage risk effectively.

### Multi-Asset Strategies

You can create bots that trade multiple assets (e.g., BTC/USDT, ETH/USDT) simultaneously. The QX framework supports multi-asset strategies through multi-threading or asynchronous execution.

---

## Resources and Documentation

- **QX Documentation**: *todo*
- **QX GitHub Repository**: [QX GitHub](https://github.com/squidKid-deluxe/qtradex)
- **Trading Strategies**: Learn about various strategies like moving averages, momentum, mean reversion, etc.
- **Python Technical Analysis Libraries**: Explore libraries like `Pandas-TA` or `Numpy` for advanced technical analysis.

---

That's it! You now have a comprehensive understanding of how to create a trading bot with the **QX Framework**. Happy trading!

