"""
Configuration management system for the Trade Project.

This module loads configuration from environment variables and .env file.
"""

import os
import sys
import logging
from typing import Any, Dict, Optional, Union
from pathlib import Path
from dataclasses import dataclass, field
from functools import lru_cache

# --- Path setup ---
# Add project root to sys.path to allow absolute imports
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from STRATEGY import STRATEGY_REGISTRY
# --- Strategy Registry ---
# Import the central strategy registry. This allows the config to be aware of available strategies.


# --- Environment Initialization ---
# This block ensures environment is loaded before any config classes are defined.
def _initialize_environment():
    """
    Loads environment variables from a .env file if python-dotenv is installed
    and the file exists. This function is called once at the module level.
    """
    try:
        from dotenv import load_dotenv
        project_root = Path(__file__).parent.parent
        env_path = project_root / '.env'
        if env_path.exists():
            load_dotenv(dotenv_path=env_path)
            print(f"[Config] Loaded environment variables from {env_path}")
        else:
            print(f"[Config] .env file not found at {env_path}. Using OS environment variables only.")
    except ImportError:
        print("[Config] python-dotenv not installed. Using OS environment variables only.")

_initialize_environment()


# --- Helper Functions ---
def _parse_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).lower() in ('true', 'yes', '1', 'on')

def _get_env_list(key: str, default: str = ""):
    """Parses a comma-separated string from environment variables into a list of strings."""
    value = os.getenv(key, default)
    if not value:
        return []
    return [item.strip().upper() for item in value.split(',') if item.strip()]


# --- Configuration Classes ---

class APIConfig:
    """API configuration settings, loaded from environment variables."""
    def __init__(self):
        self.USE_MOCK_API: bool = _parse_bool(os.getenv('USE_MOCK_API', 'False'))
        self.USE_BYBIT_API: bool = _parse_bool(os.getenv('USE_BYBIT_API', 'False'))
        self.USE_COINBASE_API: bool = _parse_bool(os.getenv('USE_COINBASE_API', 'False'))
        self.USE_BINANCE_API: bool = _parse_bool(os.getenv('USE_BINANCE_API', 'False'))
        self.API_KEY: str | None = os.getenv('API_KEY')
        self.API_SECRET: str | None = os.getenv('API_SECRET')
        self.TESTNET: bool = _parse_bool(os.getenv('TESTNET', 'True'))

        self._validate()

    def _validate(self):
        api_selected = self.USE_MOCK_API or self.USE_BYBIT_API or self.USE_COINBASE_API or self.USE_BINANCE_API
        if not api_selected:
            # Default to MOCK API if nothing is selected
            self.USE_MOCK_API = True
            print("[Config] Warning: No API selected in .env. Defaulting to USE_MOCK_API=True.")

        is_real_exchange = self.USE_BYBIT_API or self.USE_COINBASE_API or self.USE_BINANCE_API
        if is_real_exchange and (not self.API_KEY or not self.API_SECRET):
            raise ValueError("API_KEY and API_SECRET must be set in your .env file when using a real exchange.")


class TradingConfig:
    """
    Trading configuration settings.
    Loads active strategies and their weights from environment variables.
    Strategy parameters are managed by the STRATEGY_REGISTRY.
    """
    def __init__(self):
        self.SYMBOL: str = os.getenv("TRADING_SYMBOL", "BTC/USDT")
        self.TIMEFRAME: str = os.getenv("TRADING_TIMEFRAME", "1m")
        self.UPDATE_INTERVAL: int = int(os.getenv("UPDATE_INTERVAL", 10))
        self.MIN_QUANTITY: float = float(os.getenv("MIN_QUANTITY", 0.0001))
        self.DEFAULT_ORDER_TYPE: str = os.getenv("DEFAULT_ORDER_TYPE", "market")
        self.LEVERAGE: int = int(os.getenv("LEVERAGE", 1))
        self.TRADE_FEE: float = float(os.getenv("TRADE_FEE", 0.00075))
        self.SLIPPAGE: float = float(os.getenv("SLIPPAGE", 0.001))
        
        # Загрузка стратегий и их весов из одной переменной .env
        self.STRATEGY_WEIGHTS: Dict[str, float] = self._load_strategy_config()

        # Если в .env ничего не найдено, используются значения по умолчанию
        if not self.STRATEGY_WEIGHTS:
            print("[Config] Warning: STRATEGY_CONFIG не найден в .env. Используются стратегии и веса по умолчанию.")
            self.STRATEGY_WEIGHTS = {
                "RSI": 0.20, "XGB": 0.30, "MACD": 0.20, "BOLLINGER": 0.12,
                "STOCHASTIC": 0.10, "WILLIAMS_R": 0.08
            }
        
        self.STRATEGIES: List[str] = list(self.STRATEGY_WEIGHTS.keys())
        self.TARGET_FRACTION: float = float(os.getenv("TARGET_FRACTION", 0.01))
        
        print(f"[Config] Загруженные стратегии: {self.STRATEGIES}")
        print(f"[Config] Загруженные веса: {self.STRATEGY_WEIGHTS}")

    def get_csv_paths(self) -> Dict[str, str]:
        """Get CSV file paths for different data types."""
        symbol_name = self.get_symbol_name()
        return {
            'raw': f"DATA/{symbol_name}_{self.TIMEFRAME}.csv",
            'anal': f"DATA/{symbol_name}_{self.TIMEFRAME}_anal.csv",
        }

    def get_symbol_name(self) -> str:
        """Get symbol name without slash."""
        return self.SYMBOL.replace("/", "")    
    def _load_strategy_config(self) -> Dict[str, float]:
        """
        Загружает конфигурацию стратегий из переменной окружения STRATEGY_CONFIG.
        Формат: "RSI:0.3,MACD:0.7".
        """
        config_str = os.getenv("STRATEGY_CONFIG")
        if not config_str:
            return {}
            
        weights = {}
        pairs = config_str.split(',')
        for pair in pairs:
            if ':' in pair:
                name, weight_str = pair.split(':', 1)
                try:
                    strategy_name = name.strip().upper()
                    # Проверка, что стратегия есть в реестре
                    if strategy_name in STRATEGY_REGISTRY:
                        weights[strategy_name] = float(weight_str.strip())
                    else:
                        print(f"[Config] Warning: Стратегия '{strategy_name}' из .env не найдена в STRATEGY_REGISTRY и будет проигнорирована.")
                except ValueError:
                    print(f"[Config] Warning: Неверный вес для стратегии '{name}'. Она будет проигнорирована.")
        return weights

@dataclass
class DashboardConfig:
    """Dashboard configuration settings."""
    
    # Flask Settings
    HOST: str = field(default="127.0.0.1")
    PORT: int = field(default=5000)
    
    # Features
    USE_FLASK: bool = field(default=True)
    USE_PLOT: bool = field(default=False)
    AUTO_OPEN_BROWSER: bool = field(default=True)
    
    # Timeouts
    PORT_WAIT_TIMEOUT: int = field(default=10)
    
    def __post_init__(self):
        """Load values from environment variables after initialization."""
        self.HOST = os.getenv('DASHBOARD_HOST', self.HOST)
        self.PORT = int(os.getenv('DASHBOARD_PORT', str(self.PORT)))
        self.USE_FLASK = _parse_bool(os.getenv('USE_FLASK', str(self.USE_FLASK)))
        self.USE_PLOT = _parse_bool(os.getenv('USE_PLOT', str(self.USE_PLOT)))
        
        print(f"[DEBUG] DashboardConfig - USE_FLASK: {self.USE_FLASK}, USE_PLOT: {self.USE_PLOT}")
    
    def get_url(self) -> str:
        """Get dashboard URL."""
        return f"http://{self.HOST}:{self.PORT}"
    



@dataclass
class LoggingConfig:
    """Logging configuration settings."""
    
    # Log Cleanup
    CLEAN_LOGS_MAX_AGE_HOURS: int = field(default=24)
    
    # Logger Names
    MAIN_LOGGER_NAME: str = field(default="MainBot")
    MAIN_LOGGER_TAG: str = field(default="[MAIN]")
    MAIN_LOGGER_FILE: str = field(default="LOGS/mainbot.log")
    
    # Dashboard Logging
    DASHBOARD_LOG_FILE: str = field(default="LOGS/dashboard.out.log")
    
    # State File
    STATE_PATH: str = field(default="DATA/static/state.json")
    
    def __post_init__(self):
        """Load values from environment variables after initialization."""
        self.CLEAN_LOGS_MAX_AGE_HOURS = int(
            os.getenv('CLEAN_LOGS_MAX_AGE_HOURS', str(self.CLEAN_LOGS_MAX_AGE_HOURS))
        )


@dataclass
class PerformanceConfig:
    """Performance monitoring configuration settings."""
    
    # Metrics
    TRACK_TRADE_PERFORMANCE: bool = field(default=True)
    TRACK_STRATEGY_PERFORMANCE: bool = field(default=True)
    TRACK_RISK_METRICS: bool = field(default=True)
    
    # Reporting
    GENERATE_DAILY_REPORTS: bool = field(default=True)
    GENERATE_WEEKLY_REPORTS: bool = field(default=True)
    GENERATE_MONTHLY_REPORTS: bool = field(default=True)
    
    # Alerts
    ENABLE_ALERTS: bool = field(default=False)
    ALERT_EMAIL: Optional[str] = field(default=None)
    ALERT_WEBHOOK: Optional[str] = field(default=None)
    
    def __post_init__(self):
        """Load values from environment variables after initialization."""
        self.ENABLE_ALERTS = self._parse_bool(os.getenv('ENABLE_ALERTS', str(self.ENABLE_ALERTS)))
        self.ALERT_EMAIL = os.getenv('ALERT_EMAIL', self.ALERT_EMAIL)
        self.ALERT_WEBHOOK = os.getenv('ALERT_WEBHOOK', self.ALERT_WEBHOOK)


@dataclass
class Config:
    """
    Unified configuration provider.
    Loads all settings from the environment during initialization.
    """
    def __init__(self):
        self.API = APIConfig()
        self.TRADING = TradingConfig()
        self.DASHBOARD = DashboardConfig()
        self.LOGGING = LoggingConfig()
        
        # Static directories
        self.DATA_DIR = "DATA"
        self.LOGS_DIR = "LOGS"
        self.STATIC_DIR = "DATA/static"
        
        self.ensure_directories()

    def ensure_directories(self):
        """Create necessary directories if they don't exist."""
        os.makedirs(self.DATA_DIR, exist_ok=True)
        os.makedirs(self.LOGS_DIR, exist_ok=True)
        os.makedirs(self.STATIC_DIR, exist_ok=True)

    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary."""
        return {
            'API': self.API.__dict__,
            'TRADING': self.TRADING.__dict__,
            'DASHBOARD': self.DASHBOARD.__dict__,
            'LOGGING': self.LOGGING.__dict__,
            # 'PERFORMANCE': self.PERFORMANCE.__dict__,
            'DATA_DIR': self.DATA_DIR,
            'LOGS_DIR': self.LOGS_DIR,
            'STATIC_DIR': self.STATIC_DIR,
        }
    
    def __str__(self):
        return str(self.to_dict())



# --- Global Singleton Instance ---
# This ensures the configuration is loaded only once.
_config_instance = None

def get_config():
    """Initializes and returns the global Config instance."""
    global _config_instance
    if _config_instance is None:
        _config_instance = Config()
    return _config_instance

# Create the global instance that the rest of the application will use
Config = get_config()

if __name__=="__main__":
    print(Config)
