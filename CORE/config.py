"""
Configuration management system for the Trade Project.

This module provides a centralized configuration system for the Trade Project.
It loads configuration values from environment variables or .env file and provides
default values for missing configurations.

Usage:
    from CORE.config import Config
    
    # Get configuration values
    api_key = Config.API_KEY
    testnet = Config.TESTNET
    
    # Get configuration with default value
    log_level = Config.get('LOG_LEVEL', 'INFO')
    
    # Get trading configuration
    symbol = Config.TRADING.SYMBOL
    timeframe = Config.TRADING.TIMEFRAME
"""

import os
import logging
from typing import Any, Dict, Optional
from pathlib import Path

# Try to import dotenv for .env file support
try:
    from dotenv import load_dotenv
    _has_dotenv = True
except ImportError:
    _has_dotenv = False
    logging.warning("python-dotenv not installed. Environment variables will be loaded from OS only.")
    logging.warning("To enable .env file support, install python-dotenv: pip install python-dotenv")


class _ConfigMeta(type):
    """Metaclass for Config to enable attribute-style access to configuration values."""
    
    def __getattr__(cls, name: str) -> Any:
        """Get configuration value by attribute name."""
        return cls.get(name)


class Config(metaclass=_ConfigMeta):
    """
    Configuration management system for the Trade Project.
    
    This class provides access to configuration values from environment variables
    or .env file with support for default values.
    """
    
    # Cache for configuration values
    _config_cache: Dict[str, Any] = {}
    
    # Flag indicating whether .env file has been loaded
    _env_loaded: bool = False
    
    # Base directories (defined once)
    DATA_DIR = "DATA"
    LOGS_DIR = "LOGS"
    STATIC_DIR = os.path.join(DATA_DIR, "static")
    
    @classmethod
    def _load_env(cls) -> None:
        """Load environment variables from .env file if available."""
        if cls._env_loaded:
            return
            
        if _has_dotenv:
            # Find the project root directory (where .env should be located)
            project_root = Path(__file__).parent.parent
            env_path = project_root / '.env'
            
            # Load .env file if it exists
            if env_path.exists():
                load_dotenv(dotenv_path=env_path)
                logging.info(f"Loaded environment variables from {env_path}")
            else:
                logging.warning(f".env file not found at {env_path}")
        
        cls._env_loaded = True
    
    @classmethod
    def get(cls, name: str, default: Any = None) -> Any:
        """
        Get configuration value by name.
        
        Args:
            name: Name of the configuration value
            default: Default value if configuration is not found
            
        Returns:
            Configuration value or default
        """
        # Check cache first
        if name in cls._config_cache:
            return cls._config_cache[name]
        
        # Load environment variables if not already loaded
        cls._load_env()
        
        # Get value from environment
        value = os.environ.get(name, default)
        
        # Convert boolean strings to actual booleans
        if isinstance(value, str):
            if value.lower() in ('true', 'yes', '1'):
                value = True
            elif value.lower() in ('false', 'no', '0'):
                value = False
        
        # Cache the value
        cls._config_cache[name] = value
        
        return value
    
    @classmethod
    def set(cls, name: str, value: Any) -> None:
        """
        Set configuration value.
        
        Args:
            name: Name of the configuration value
            value: Value to set
        """
        cls._config_cache[name] = value
    
    @classmethod
    def clear_cache(cls) -> None:
        """Clear the configuration cache."""
        cls._config_cache.clear()
        cls._env_loaded = False
    
    @classmethod
    def ensure_directories(cls) -> None:
        """Create necessary directories if they don't exist."""
        os.makedirs(cls.DATA_DIR, exist_ok=True)
        os.makedirs(cls.LOGS_DIR, exist_ok=True)
        os.makedirs(cls.STATIC_DIR, exist_ok=True)


class TradingConfig:
    """Configuration for trading operations."""
    
    # ==================== TRADING PARAMETERS ====================
    SYMBOL = "BTC/USDT"
    TIMEFRAME = "1m"
    UPDATE_INTERVAL = 10  # seconds between ticks for simulation
    
    # ==================== STRATEGY PARAMETERS ====================
    # RSI Strategy
    RSI_PERIOD = 14
    RSI_LOWER = 30.0
    RSI_UPPER = 70.0
    
    # MACD Strategy
    MACD_FAST = 12
    MACD_SLOW = 26
    MACD_SIGNAL = 9
    
    # Bollinger Bands Strategy
    BB_PERIOD = 20
    BB_STD_DEV = 2.0
    
    # Stochastic Strategy
    STOCH_K_PERIOD = 14
    STOCH_D_PERIOD = 3
    STOCH_OVERSOLD = 20.0
    STOCH_OVERBOUGHT = 80.0
    
    # Williams %R Strategy
    WILLIAMS_R_PERIOD = 14
    WILLIAMS_R_OVERSOLD = -80.0
    WILLIAMS_R_OVERBOUGHT = -20.0
    
    # ==================== RISK MANAGEMENT ====================
    TARGET_FRACTION = 0.25  # fraction of balance to use per trade
    MIN_QUANTITY = 0.001
    MAX_POSITION_SIZE = 0.5  # maximum position size as fraction of balance
    
    # ==================== TRADING RULES ====================
    MIN_SIGNALS_FOR_DECISION = 1  # minimum number of strategies that must agree
    CONFIDENCE_THRESHOLD = 0.6  # minimum confidence for trade execution
    
    @classmethod
    def get_symbol_name(cls) -> str:
        """Get symbol name without slash."""
        return cls.SYMBOL.replace("/", "")
    
    @classmethod
    def get_csv_paths(cls) -> Dict[str, str]:
        """Get CSV file paths for different data types."""
        symbol_name = cls.get_symbol_name()
        return {
            'raw': f"{Config.DATA_DIR}/{symbol_name}_{cls.TIMEFRAME}.csv",
            'anal': f"{Config.DATA_DIR}/{symbol_name}_{cls.TIMEFRAME}_anal.csv",
        }


class DashboardConfig:
    """Configuration for dashboard and web interface."""
    
    # ==================== FLASK SETTINGS ====================
    HOST = os.getenv("DASHBOARD_HOST", "127.0.0.1")
    PORT = int(os.getenv("DASHBOARD_PORT", "5000"))
    
    # ==================== FEATURES ====================
    USE_FLASK = True
    USE_PLOT = False
    AUTO_OPEN_BROWSER = True
    
    # ==================== TIMEOUTS ====================
    PORT_WAIT_TIMEOUT = 10  # seconds to wait for dashboard to start
    
    @classmethod
    def get_url(cls) -> str:
        """Get dashboard URL."""
        return f"http://{cls.HOST}:{cls.PORT}"


class LoggingConfig:
    """Configuration for logging system."""
    
    # ==================== LOG CLEANUP ====================
    CLEAN_LOGS_MAX_AGE_HOURS = int(os.getenv("CLEAN_LOGS_MAX_AGE_HOURS", "24"))
    
    # ==================== LOGGER NAMES ====================
    MAIN_LOGGER_NAME = "MainBot"
    MAIN_LOGGER_TAG = "[MAIN]"
    MAIN_LOGGER_FILE = os.path.join(Config.LOGS_DIR, "mainbot.log")
    
    # ==================== DASHBOARD LOGGING ====================
    DASHBOARD_LOG_FILE = os.path.join(Config.LOGS_DIR, "dashboard.out.log")
    
    # ==================== STATE FILE ====================
    STATE_PATH = os.path.join(Config.STATIC_DIR, "state.json")


class APIConfig:
    """Configuration for API connections."""
    
    # ==================== API SELECTION ====================
    # MockAPI is fastest for simulation and testing
    USE_MOCK_API = True
    USE_BYBIT_API = False
    USE_COINBASE_API = False
    USE_BINANCE_API = False
    
    # ==================== API CREDENTIALS ====================
    # Loaded from environment variables
    API_KEY = Config.get('API_KEY')
    API_SECRET = Config.get('API_SECRET')
    TESTNET = Config.get('TESTNET', True)
    
    # ==================== API SETTINGS ====================
    REQUEST_TIMEOUT = 30  # seconds
    MAX_RETRIES = 3
    RATE_LIMIT_DELAY = 0.1  # seconds between requests


class StrategyConfig:
    """Configuration for trading strategies."""
    
    # ==================== STRATEGY WEIGHTS ====================
    # Weights for weighted voting aggregator
    STRATEGY_WEIGHTS = {
        "RSI": 0.20,
        "XGB": 0.30,
        "MACD": 0.20,
        "BOLLINGER": 0.12,
        "STOCHASTIC": 0.10,
        "WILLIAMS_R": 0.08
    }
    
    # ==================== AGGREGATOR SETTINGS ====================
    DEFAULT_AGGREGATOR = "adaptive"  # "weighted", "consensus", "adaptive"
    MIN_CONSENSUS_RATIO = 0.7  # for consensus aggregator
    VOLATILITY_THRESHOLD = 0.02  # for adaptive aggregator
    
    # ==================== SIGNAL PROCESSING ====================
    MAX_HISTORY_SIZE = 1000  # maximum number of signals to keep in history
    SIGNAL_EXPIRY_HOURS = 24  # how long signals remain valid


class PerformanceConfig:
    """Configuration for performance monitoring."""
    
    # ==================== METRICS ====================
    TRACK_TRADE_PERFORMANCE = True
    TRACK_STRATEGY_PERFORMANCE = True
    TRACK_RISK_METRICS = True
    
    # ==================== REPORTING ====================
    GENERATE_DAILY_REPORTS = True
    GENERATE_WEEKLY_REPORTS = True
    GENERATE_MONTHLY_REPORTS = True
    
    # ==================== ALERTS ====================
    ENABLE_ALERTS = False
    ALERT_EMAIL = None
    ALERT_WEBHOOK = None


# ==================== DEFAULT CONFIGURATION ====================
DEFAULT_CONFIG = {
    'API_KEY': None,
    'API_SECRET': None,
    'TESTNET': True,
    'LOG_LEVEL': 'INFO',
    'DASHBOARD_HOST': '127.0.0.1',
    'DASHBOARD_PORT': '5000',
    'CLEAN_LOGS_MAX_AGE_HOURS': '24',
}

# Set default values in the config cache
for key, value in DEFAULT_CONFIG.items():
    if Config.get(key) is None:
        Config.set(key, value)

# Ensure directories exist on import
Config.ensure_directories()