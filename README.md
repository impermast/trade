# Trade Project

A comprehensive cryptocurrency trading framework for algorithmic trading, backtesting, and analysis.

## Overview

Trade Project is a modular Python framework designed for cryptocurrency trading. It provides tools for data collection, technical analysis, strategy development, backtesting, and live trading across multiple exchanges.

## Features

- **Exchange Integration**: Connect to cryptocurrency exchanges (currently supports Bybit)
- **Data Collection**: Download and manage historical price data
- **Technical Analysis**: Calculate various technical indicators (RSI, MACD, Bollinger Bands, etc.)
- **Strategy Development**: Create and test custom trading strategies
- **Backtesting**: Evaluate strategy performance on historical data
- **Logging**: Comprehensive logging system for debugging and analysis

## Installation

### Prerequisites

- Python 3.13 or higher
- pip package manager

### Setup

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/trade.git
   cd trade
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Create a `.env` file in the project root with your API credentials:
   ```
   API_KEY=your_api_key
   API_SECRET=your_api_secret
   TESTNET=True  # Set to False for production
   ```

## Usage Examples

### Configuration Management

```python
from CORE.config import Config

# Get configuration values
api_key = Config.API_KEY
api_secret = Config.API_SECRET
testnet = Config.TESTNET

# Get configuration with default value
log_level = Config.get('LOG_LEVEL', 'INFO')

# Set a configuration value
Config.set('DATA_DIR', 'custom_data_directory')
```

### Downloading Historical Data

```python
from API.bybit_api import BybitAPI
from CORE.config import Config

# Initialize API client with configuration
api = BybitAPI(api_key=Config.API_KEY, api_secret=Config.API_SECRET, testnet=Config.TESTNET)

# Download historical data
api.download_candels_to_csv("BTC/USDT", start_date="2023-01-01T00:00:00Z", timeframe="1h")
```

### Calculating Technical Indicators

```python
import pandas as pd
from BOTS.indicators import Indicators

# Load data
df = pd.read_csv("DATA/BTCUSDT_1h.csv")

# Initialize indicators
indicators = Indicators()

# Calculate RSI
df = indicators.calc_rsi(df, period=14)

# Calculate multiple indicators
df = indicators.calc_all(df, rsi={"period": 14}, sma={"period": 20}, macd={})

print(df.tail())
```

### Creating a Custom Strategy

```python
import pandas as pd
from STRATEGY.base import BaseStrategy

class MyCustomStrategy(BaseStrategy):
    def __init__(self, **params):
        super().__init__(name="MyStrategy", indicators=["rsi", "sma"], **params)

    def default_params(self):
        return {
            "rsi": {"period": 14, "lower": 30, "upper": 70},
            "sma": {"period": 20}
        }

    def get_signals(self, df):
        # Get parameters
        rsi_params = self.params["rsi"]
        sma_params = self.params["sma"]

        # Get latest values
        rsi = df["rsi"].iloc[-1]
        sma = df[f"sma_{sma_params['period']}"].iloc[-1]
        price = df["close"].iloc[-1]

        # Generate signals
        if rsi < rsi_params["lower"] and price < sma:
            return 1  # Buy signal
        elif rsi > rsi_params["upper"] and price > sma:
            return -1  # Sell signal
        return 0  # No action
```

### Running a Strategy

```python
import pandas as pd
from BOTS.analbot import Analytic
from STRATEGY.rsi import RSIonly_Strategy

# Load data
df = pd.read_csv("DATA/BTCUSDT_1h.csv")

# Initialize analysis tool
anal = Analytic(df, "BTCUSDT_1h")

# Run RSI strategy with custom parameters
result = anal.make_strategy(RSIonly_Strategy, rsi={"period": 14, "lower": 30, "upper": 70})

# Print results
print(result)
```

### Logging

```python
from BOTS.loggerbot import Logger

# Create a logger
logger = Logger(
    name="MyModule",
    tag="[CUSTOM]",
    logfile="LOGS/custom.log",
    console=True
).get_logger()

# Log messages
logger.info("This is an informational message")
logger.warning("This is a warning message")
logger.error("This is an error message")
logger.debug("This is a debug message")
```

## Project Structure

```
trade/
├── API/                           # Exchange API clients
│   ├── birza_api.py               # Abstract API base class
│   ├── bybit_api.py               # Bybit exchange implementation
│   └── data_parse.py              # Data fetching utilities
│
├── BOTS/                          # Trading and analysis bots
│   ├── analbot.py                 # Analysis and backtesting
│   ├── indicators.py              # Technical indicators
│   └── loggerbot.py               # Logging utilities
│
├── CORE/                          # Core functionality
│   └── config.py                  # Configuration management
│
├── DATA/                          # Historical price data
│   └── BTCUSDT_1h.csv             # Example data file
│
├── LOGS/                          # Log files
│
├── STRATEGY/                      # Trading strategies
│   ├── base.py                    # Base strategy class
│   ├── rsi.py                     # RSI-based strategy
│   └── XGBstrategy.py             # XGBoost-based strategy
│
├── docs/                          # Documentation
│   ├── plan.md                    # Project improvement plan
│   └── tasks.md                   # Task list
│
├── .env                           # API credentials (not in repo)
└── README.md                      # This file
```

## Available Strategies

### RSI Strategy (`STRATEGY/rsi.py`)

A simple strategy based on the Relative Strength Index (RSI) indicator.

**Logic:**
- Buy when RSI falls below the lower threshold (default: 30)
- Sell when RSI rises above the upper threshold (default: 70)
- Hold otherwise

**Parameters:**
- `period`: The period for RSI calculation (default: 14)
- `lower`: The lower threshold for buy signals (default: 30)
- `upper`: The upper threshold for sell signals (default: 70)

**Example:**
```python
from STRATEGY.rsi import RSIonly_Strategy

# Default parameters
strategy = RSIonly_Strategy()

# Custom parameters
strategy = RSIonly_Strategy(rsi={"period": 7, "lower": 20, "upper": 80})
```

### XGBoost Strategy (`STRATEGY/XGBstrategy.py`)

An advanced strategy using XGBoost machine learning model to predict price movements.

**Logic:**
- Uses a trained XGBoost model to predict price movements
- Generates buy/sell signals based on the model's predictions
- Incorporates multiple technical indicators as features

**Parameters:**
- `model_path`: Path to the trained XGBoost model file (default: uses built-in model)
- `threshold`: Confidence threshold for generating signals (default: 0.6)
- `indicators`: List of indicators to use as features (default: ["rsi", "macd", "bbands"])

**Example:**
```python
from STRATEGY.XGBstrategy import XGBoostStrategy

# Default parameters
strategy = XGBoostStrategy()

# Custom parameters
strategy = XGBoostStrategy(
    model_path="models/my_xgb_model.joblib",
    threshold=0.7,
    indicators=["rsi", "macd", "bbands", "atr"]
)
```

### Creating Custom Strategies

You can create your own strategies by inheriting from the `BaseStrategy` class and implementing the required methods:

1. `__init__`: Initialize the strategy with parameters
2. `default_params`: Define default parameters for the strategy
3. `get_signals`: Implement the signal generation logic

See the "Creating a Custom Strategy" example in the Usage Examples section for details.

## Troubleshooting Guide

### Common Issues and Solutions

#### Installation Issues

**Problem**: ImportError when importing modules
```
ImportError: No module named 'ccxt'
```

**Solution**: Make sure you've installed all dependencies
```bash
pip install -r requirements.txt
```

#### API Connection Issues

**Problem**: Error connecting to exchange API
```
Error initializing BybitAPI: HTTPError: 401 Client Error
```

**Solution**: Check your API credentials in the `.env` file and ensure they have the correct permissions.

#### Data Issues

**Problem**: Missing or incomplete data
```
ValueError: Колонка rsi не найдена в датафрейме.
```

**Solution**: Ensure you've calculated the required indicators before running a strategy:
```python
from BOTS.indicators import Indicators
df = Indicators().calc_rsi(df)
```

#### Strategy Issues

**Problem**: Strategy not generating expected signals

**Solution**: 
1. Check that your DataFrame has enough data points (at least as many as the indicator period)
2. Verify indicator column names match what the strategy expects
3. Print intermediate values to debug:
```python
print(f"RSI value: {df['rsi'].iloc[-1]}, threshold: {strategy.params['rsi']['lower']}")
```

#### Performance Issues

**Problem**: Slow data processing or analysis

**Solution**:
1. Use smaller datasets for testing
2. Implement caching for frequently used calculations
3. Consider using more efficient data structures

### Getting Help

If you encounter issues not covered in this guide:

1. Check the logs in the LOGS directory for error messages
2. Review the docstrings of the relevant classes and methods
3. Open an issue on the GitHub repository with:
   - A clear description of the problem
   - Steps to reproduce the issue
   - Relevant error messages and logs

## Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature-name`
3. Commit your changes: `git commit -am 'Add some feature'`
4. Push to the branch: `git push origin feature-name`
5. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.
