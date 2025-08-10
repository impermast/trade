# Crypto Trading Bot

A full-featured cryptocurrency trading bot with a built-in browser dashboard.  
Supports **any exchange** via a unified API interface (Bybit, Binance, Coinbase, MockAPI, etc.).  
Example strategy included: **RSI-based trading**.

---

## 🚀 Features
- Connect to any exchange via the unified `BirzaAPI` interface.
- Real-time trading with configurable strategies.
- Built-in **RSI strategy** example (+ easy to add your own).
- MockAPI for simulation with generated market data.
- Interactive web dashboard for monitoring balance, positions, trades, and charts.
- CSV logging of market data and strategy signals.

---

## 📦 Installation
```bash
# Clone the repository
git clone https://github.com/yourusername/trading-bot.git
cd trading-bot

# Create and activate a virtual environment (recommended)
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

---

## 🏁 Quick Start

### 1. Run with MockAPI (simulation)
```bash
python main.py
```

### 2. Run with a real exchange (example: Bybit)
Set your API keys in `.env`:
```env
BYBIT_TOKEN=your_api_key
BYBIT_SECRET=your_api_secret
```
Edit `main.py`:
```python
from API.bybit_api import BybitAPI
botapi = BybitAPI()
```
Run:
```bash
python main.py
```

---

## 📊 Dashboard
Once running, open in your browser:
```
http://127.0.0.1:5000
```
You can:
- View live candlestick charts
- See RSI signals on the chart
- Monitor balance and open positions
- Browse logs and CSV data

---

## 📂 Project Structure
```
API/         # Exchange integrations and dashboard server
BOTS/        # Indicators, analytics, and logging
CORE/        # Config, data validation, caching
DATA/        # Market data and analytics CSVs
LOGS/        # Application logs
STRATEGY/    # Trading strategies (RSI, XGB, etc.)
main.py      # Entry point
```

---

## 📈 Example: RSI Strategy
- Calculates **Relative Strength Index** over a given period (default: 14).
- **BUY** when RSI crosses above 30 from below.
- **SELL** when RSI crosses above 70 from below.
- Signals saved in `orders_rsi` column in analytics CSV.

---

## 📜 License
MIT License — feel free to use and modify.
