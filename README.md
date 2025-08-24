# Crypto Trading Bot

A modular and extensible cryptocurrency trading bot featuring a web-based dashboard, multiple trading strategies, and a unified API for interacting with various exchanges.

---

## 🚀 Features

- **Unified Exchange API**: Easily connect to any supported exchange (Bybit, Binance, Coinbase, etc.) through a single interface. A `MockAPI` is included for safe testing and simulation.
- **Modular Strategy System**: Comes with a suite of built-in trading strategies (RSI, MACD, Bollinger Bands, and more). The system is designed for easy extension with your own custom strategies.
- **Centralized Configuration**: Manage all settings, from API keys to strategy parameters, in a single `config.ini` file and environment variables. No need to modify the source code for configuration changes.
- **Dependency Injection**: Built on a clean, decoupled architecture using a dependency injector and component factory, making the system robust, testable, and easy to maintain.
- **Interactive Dashboard**: A real-time web interface to monitor account balance, open positions, live charts, strategy signals, and application logs.
- **Data Logging**: Automatically logs market data, strategy signals, and trades to CSV files for later analysis.

---

## 📂 Project Architecture

The project is divided into several key modules:

- **`API/`**: Contains all exchange-specific API clients and the web dashboard server.
- **`BOTS/`**: Includes modules for technical indicators, analytics, and plotting.
- **`CORE/`**: The heart of the application. Manages configuration (`config.py`), application lifecycle (`application.py`), and dependency injection (`component_factory.py`, `dependency_injection.py`).
- **`STRATEGY/`**: Houses all trading strategies. Each strategy inherits from `base.py`. The `manager.py` and `__init__.py` discover and register all available strategies into the `STRATEGY_REGISTRY`.
- **`DATA/`**: Stores CSV logs of market data and analytics.
- **`LOGS/`**: Contains application logs.
- **`main.py`**: The entry point that assembles and runs the application.

---

## 📦 Installation

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/yourusername/trading-bot.git
    cd trading-bot
    ```

2.  **Create and activate a virtual environment:**
    ```bash
    python -m venv .venv
    # On Windows
    .venv\Scripts\activate
    # On macOS/Linux
    source .venv/bin/activate
    ```

3.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

---

## 🏁 Configuration and Quick Start

### 1. Set Up Configuration

Instead of hardcoding settings, the application uses a configuration file and environment variables.

-   Create a `.env` file for your secrets by copying the example:
    ```bash
    copy env_example.txt .env
    ```
-   Edit the `.env` file to add your API keys:
    ```
    BYBIT_API_KEY=your_api_key
    BYBIT_API_SECRET=your_api_secret
    ```
-   *Примечание: Если у вас нет файла `config.ini`, вам следует его создать для настройки основных параметров, таких как активная биржа и стратегия.*

### 2. Run the Bot

Once configured, start the application:

```bash
python main.py
```

The bot will launch using the exchange and strategies specified in your configuration. By default, it may use the `MockAPI` for simulation if no real exchange is configured.

---

## 📊 Dashboard

With the bot running, open your browser and navigate to:
**`http://127.0.0.1:5000`**

The dashboard allows you to:
- View live candlestick charts.
- See strategy signals overlaid on the chart.
- Monitor your account balance and open positions.
- Review application logs and browse CSV data.

---

## 📈 Strategies

The bot includes several pre-built strategies:
- **RSI**: Relative Strength Index
- **MACD Crossover**: Moving Average Convergence Divergence
- **Bollinger Bands**: Mean Reversion on Bollinger Bands
- **Stochastic Oscillator**
- **Williams %R**
- **XGBoost Strategy**: An example of a machine learning-based strategy.

### Creating a New Strategy

To add your own strategy:
1.  Create a new Python file in the `STRATEGY/` directory (e.g., `my_strategy.py`).
2.  Define a class that inherits from `BaseStrategy`.
3.  Implement the `generate_signals()` method.
4.  The `STRATEGY_REGISTRY` will automatically discover and register your new strategy, making it available for use in the configuration.

---

## 🔧 Troubleshooting

### Bybit API Error: `invalid request, please check your server timestamp`
This is a common error with the Bybit API and usually means the time on your local machine is out of sync with Bybit's servers. The bot attempts to handle this, but if the problem persists, ensure your system clock is synchronized with an NTP server. The allowed time difference (`recv_window`) can be configured in your settings if needed.

---

## 📜 License

MIT License — feel free to use and modify.