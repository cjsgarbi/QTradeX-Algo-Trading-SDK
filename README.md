# 🚀 QTradeX Core — Build, Backtest & Optimize AI-Powered Crypto Trading Bots

<p>
  <img src="https://img.shields.io/github/stars/squidKid-deluxe/QTradeX-Algo-Trading-SDK" />
  <img src="https://img.shields.io/github/contributors/squidKid-deluxe/QTradeX-Algo-Trading-SDK" />
  <img src="https://img.shields.io/github/last-commit/squidKid-deluxe/QTradeX-Algo-Trading-SDK" />
  <img src="https://visitor-badge.laobi.icu/badge?page_id=squidKid-deluxe.QTradeX-Algo-Trading-SDK" />
  <img src="https://img.shields.io/github/languages/count/squidKid-deluxe/QTradeX-Algo-Trading-SDK" />
  <img src="https://img.shields.io/github/languages/top/squidKid-deluxe/QTradeX-Algo-Trading-SDK" />
  <img src="https://img.shields.io/github/issues/squidKid-deluxe/QTradeX-Algo-Trading-SDK" />
  <img src="https://img.shields.io/github/issues-pr/squidKid-deluxe/QTradeX-Algo-Trading-SDK" />
</p>

<p align="center">
  <img src="screenshots/Screenshot from 2025-05-02 18-50-54.png" width="100%" alt="QTradeX Demo Screenshot">
</p>

> 📸 See [screenshots.md](screenshots.md) for more visuals  
> 📚 Read the core docs on [QTradeX SDK DeepWiki](https://deepwiki.com/squidKid-deluxe/QTradeX-Algo-Trading-SDK)  
> 🤖 Explore the bots at [QTradeX AI Agents DeepWiki](https://deepwiki.com/squidKid-deluxe/QTradeX-AI-Agents)  
> 💬 Join our [Telegram Group](https://t.me/qtradex_sdk) for discussion & support

---

## ⚡️ TL;DR
**QTradeX** is a lightning-fast Python framework for designing, backtesting, and deploying algorithmic trading bots, built for **crypto markets** with support for **100+ exchanges**, **AI-driven optimization**, and **blazing-fast vectorized execution**.

Like what we're doing?  Give us a ⭐!

---

## 🎯 Why QTradeX?

Whether you're exploring a simple EMA crossover or engineering a strategy with 20+ indicators and genetic optimization, QTradeX gives you:

✅ Modular Architecture  
✅ Tulip + CCXT Integration  
✅ Custom Bot Classes  
✅ Fast, Disk-Cached Market Data  
✅ Near-Instant Backtests (even on Raspberry Pi!)

---

## 🔍 Features at a Glance

- 🧠 **Bot Development**: Extend `BaseBot` to craft custom strategies
- 🔁 **Backtesting**: Plug-and-play CLI & code-based testing
- 🧬 **Optimization**: Use QPSO or LSGA to fine-tune parameters
- 📊 **Indicators**: **Pandas-TA** integration (Pure Python) - No C++ required!
- 🌐 **Data Sources**: Pull candles from 100+ CEXs/DEXs with CCXT & BitShares (Native)
- 📈 **Performance Metrics**: Evaluate bots with ROI, Sortino, Win Rate
- 🤖 **Speed**: Up to 50+ backtests/sec on low-end hardware

---

## ⚙️ Project Structure

```

qtradex/
├── core/             # Bot logic and backtesting
├── indicators/       # Technical indicators
├── optimizers/       # QPSO and LSGA
├── plot/             # Trade/metric visualization
├── private/          # Execution & paper wallets
├── public/           # Data feeds and utils
├── common/           # JSON RPC, BitShares nodes
└── setup.py          # Install script

```

---

## 🚀 Quickstart

### Install

**Now 100% Compatible with Windows, Linux & Mac (No C++ Build Tools Required)**

```bash
git clone https://github.com/squidKid-deluxe/QTradeX-Algo-Trading-SDK.git QTradeX
cd QTradeX

# Recommended: Use 'uv' for blazing fast installation
pip install uv
uv venv
# Windows
.venv\Scripts\activate
# Linux/Mac
source .venv/bin/activate

# Install (All dependencies are now pure Python wheels)
uv pip install -e .
```

### Configuration (New!)

You can now configure your API keys using a `.env` file instead of typing them every time.

1. Rename `.env.example` to `.env`.
2. Add your keys using the format `[EXCHANGE]_API_KEY`:
   ```ini
   BINANCE_API_KEY=your_key
   BINANCE_API_SECRET=your_secret
   ```
3. **Auto-Save:** If you don't have a `.env` file, the bot will ask you to enter keys and offer to save them automatically for next time!



---

## 🧪 Example Bot: EMA Crossover

```python
import qtradex as qx
import numpy as np


class EMACrossBot(qx.BaseBot):
    def __init__(self):
        self.tune = {"fast_ema": 10, "slow_ema": 50}

    def indicators(self, data):
        return {
            "fast_ema": qx.ti.ema(data["close"], self.tune["fast_ema"]),
            "slow_ema": qx.ti.ema(data["close"], self.tune["slow_ema"]),
        }

    def strategy(self, tick_info, indicators):
        fast = indicators["fast_ema"]
        slow = indicators["slow_ema"]
        if fast > slow:
            return qx.Buy()
        elif fast < slow:
            return qx.Sell()
        return qx.Thresholds(buying=0.5 * fast, selling=2 * fast)

    def plot(self, *args):
        qx.plot(
            self.info,
            *args,
            (
                # key name    label    color   axis idx   axis name
                ("fast_ema", "EMA 1", "white", 0,        "EMA Cross"),
                ("slow_ema", "EMA 2", "cyan",  0,        "EMA Cross"),
            )
        )


# Load data and run
data = qx.Data(
    exchange="kucoin",
    asset="BTC",
    currency="USDT",
    begin="2020-01-01",
    end="2023-01-01"
)
bot = EMACrossBot()
qx.dispatch(bot, data)
```

🔗 See more bots in [QTradeX AI Agents](https://github.com/squidKid-deluxe/QTradeX-AI-Agents)

---

## 🚦 Usage Guide

| Step | What to Do                                                      |
| ---- | --------------------------------------------------------------- |
| 1️⃣  | Build a bot with custom logic by subclassing `BaseBot`          |
| 2️⃣  | Backtest using `qx.core.dispatch` + historical data             |
| 3️⃣  | Optimize with `qpso.py` or `lsga.py` (tunes stored in `/tunes`) |
| 4️⃣  | Deploy live                                                     |

---

## 🧭 Roadmap

* 📈 More indicators (non-Tulip sources)
* 🏦 TradFi Connectors: Stocks, Forex, and Comex support

Want to help out?  Check out the [Issues](https://github.com/squidKid-deluxe/QTradeX-Algo-Trading-SDK/issues?q=is%3Aissue%20state%3Aopen%20label%3A%22help%20wanted%22) list for forseeable improvements and bugs.

---

## 📚 Resources

* 🧠 [QTradeX Algo Trading Strategies](https://github.com/squidKid-deluxe/qtradex-ai-agents)
* 📘 [Tulipy Docs](https://tulipindicators.org)
* 🌍 [CCXT Docs](https://docs.ccxt.com)

---

## 📜 License

**WTFPL** — Do what you want. Just be awesome about it 😎

---

## ⭐ Star History

<a href="https://www.star-history.com/#squidKid-deluxe/QTradeX-Algo-Trading-SDK&Date">
 <picture>
   <source media="(prefers-color-scheme: dark)" srcset="https://api.star-history.com/svg?repos=squidKid-deluxe/QTradeX-Algo-Trading-SDK&type=Date&theme=dark" />
   <source media="(prefers-color-scheme: light)" srcset="https://api.star-history.com/svg?repos=squidKid-deluxe/QTradeX-Algo-Trading-SDK&type=Date" />
   <img alt="Star History Chart" src="https://api.star-history.com/svg?repos=squidKid-deluxe/QTradeX-Algo-Trading-SDK&type=Date" />
 </picture>
</a>

---

✨ Ready to start? Clone the repo, run your first bot, and tune away.  Once tuned - LET THE EXECUTIONS BEGIN!
