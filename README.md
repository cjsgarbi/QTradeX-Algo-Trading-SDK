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

## 🧪 Strategy Development

We provide a **Standard Template** to help you build compatible strategies instantly.

1. **Locate the Template:**
   Go to the `strategies/` folder and find `strategy_base.py`.

2. **Create Your Strategy:**
   Duplicate the file (`strategies/my_strategy.py`), rename the class, and implement your logic.
   
   The template includes:
   - `__init__`: Define tunable parameters (for AI optimization).
   - `indicators`: Calculate Pandas-TA indicators.
   - `strategy`: Define your Buy/Sell logic.
   - `plot`: Configure charts.

3. **Run It:**
   Simply run the file directly. It comes with a built-in launcher.
   ```bash
   python strategies/strategy_base.py
   # or
   python strategies/my_strategy.py
   ```
   This will open the QTradeX interactive menu automatically.

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
