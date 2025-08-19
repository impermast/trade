"""
Configuration management system for the Trade Project.

This module provides a centralized configuration system using dataclasses
for better type safety and validation. It loads configuration values from
environment variables or .env file and provides default values for missing configurations.

Usage:
    from CORE.config import Config
    
    # Get configuration values
    api_key = Config.API.API_KEY
    symbol = Config.TRADING.SYMBOL
    
    # Get configuration with default value
    log_level = Config.get('LOG_LEVEL', 'INFO')
"""

import os
import logging
from typing import Any, Dict, Optional, Union
from pathlib import Path
from dataclasses import dataclass, field
from functools import lru_cache

# Try to import dotenv for .env file support
try:
    from dotenv import load_dotenv
    _has_dotenv = True
except ImportError:
    _has_dotenv = False
    logging.warning("python-dotenv not installed. Environment variables will be loaded from OS only.")
    logging.warning("To enable .env file support, install python-dotenv: pip install python-dotenv")


@dataclass
class APIConfig:
    """API configuration settings."""
    
    # API Selection
    USE_MOCK_API: bool = field(default=True)
    USE_BYBIT_API: bool = field(default=False)
    USE_COINBASE_API: bool = field(default=False)
    USE_BINANCE_API: bool = field(default=False)
    
    # API Credentials (loaded from environment)
    API_KEY: Optional[str] = field(default=None)
    API_SECRET: Optional[str] = field(default=None)
    TESTNET: bool = field(default=True)
    
    # API Settings
    REQUEST_TIMEOUT: int = field(default=30)
    MAX_RETRIES: int = field(default=3)
    RATE_LIMIT_DELAY: float = field(default=0.1)
    
    def __post_init__(self):
        """Load values from environment variables after initialization."""
        self.API_KEY = os.getenv('API_KEY', self.API_KEY)
        self.API_SECRET = os.getenv('API_SECRET', self.API_SECRET)
        self.TESTNET = self._parse_bool(os.getenv('TESTNET', str(self.TESTNET)))
    
    @staticmethod
    def _parse_bool(value: str) -> bool:
        """Parse string to boolean."""
        if isinstance(value, bool):
            return value
        return value.lower() in ('true', 'yes', '1', 'on')


@dataclass
class TradingConfig:
    """Trading configuration settings."""
    
    # Trading Parameters
    SYMBOL: str = field(default="BTC/USDT")
    TIMEFRAME: str = field(default="1m")
    UPDATE_INTERVAL: int = field(default=10)
    
    # Strategy Parameters
    RSI_PERIOD: int = field(default=14)
    RSI_LOWER: float = field(default=30.0)
    RSI_UPPER: float = field(default=70.0)
    
    MACD_FAST: int = field(default=12)
    MACD_SLOW: int = field(default=26)
    MACD_SIGNAL: int = field(default=9)
    
    BB_PERIOD: int = field(default=20)
    BB_STD_DEV: float = field(default=2.0)
    
    STOCH_K_PERIOD: int = field(default=14)
    STOCH_D_PERIOD: int = field(default=3)
    STOCH_OVERSOLD: float = field(default=20.0)
    STOCH_OVERBOUGHT: float = field(default=80.0)
    
    WILLIAMS_R_PERIOD: int = field(default=14)
    WILLIAMS_R_OVERSOLD: float = field(default=-80.0)
    WILLIAMS_R_OVERBOUGHT: float = field(default=-20.0)
    
    # Risk Management
    TARGET_FRACTION: float = field(default=0.25)
    MIN_QUANTITY: float = field(default=0.001)
    MAX_POSITION_SIZE: float = field(default=0.5)
    
    # Trading Rules
    MIN_SIGNALS_FOR_DECISION: int = field(default=1)
    CONFIDENCE_THRESHOLD: float = field(default=0.6)
    
    # Strategy Weights
    STRATEGY_WEIGHTS: Dict[str, float] = field(default_factory=lambda: {
        "RSI": 0.20,
        "XGB": 0.30,
        "MACD": 0.20,
        "BOLLINGER": 0.12,
        "STOCHASTIC": 0.10,
        "WILLIAMS_R": 0.08
    })
    
    # Aggregator Settings
    DEFAULT_AGGREGATOR: str = field(default="adaptive")
    MIN_CONSENSUS_RATIO: float = field(default=0.7)
    VOLATILITY_THRESHOLD: float = field(default=0.02)
    
    # Signal Processing
    MAX_HISTORY_SIZE: int = field(default=1000)
    SIGNAL_EXPIRY_HOURS: int = field(default=24)
    
    def __post_init__(self):
        """Load values from environment variables after initialization."""
        self.SYMBOL = os.getenv('TRADING_SYMBOL', self.SYMBOL)
        self.TIMEFRAME = os.getenv('TRADING_TIMEFRAME', self.TIMEFRAME)
        self.UPDATE_INTERVAL = int(os.getenv('UPDATE_INTERVAL', str(self.UPDATE_INTERVAL)))
        self.TARGET_FRACTION = float(os.getenv('TARGET_FRACTION', str(self.TARGET_FRACTION)))
    
    def get_symbol_name(self) -> str:
        """Get symbol name without slash."""
        return self.SYMBOL.replace("/", "")
    
    def get_csv_paths(self) -> Dict[str, str]:
        """Get CSV file paths for different data types."""
        symbol_name = self.get_symbol_name()
        return {
            'raw': f"DATA/{symbol_name}_{self.TIMEFRAME}.csv",
            'anal': f"DATA/{symbol_name}_{self.TIMEFRAME}_anal.csv",
        }


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
        self.USE_FLASK = self._parse_bool(os.getenv('USE_FLASK', str(self.USE_FLASK)))
        self.USE_PLOT = self._parse_bool(os.getenv('USE_PLOT', str(self.USE_PLOT)))
    
    @staticmethod
    def _parse_bool(value: str) -> bool:
        """Parse string to boolean."""
        if isinstance(value, bool):
            return value
        return value.lower() in ('true', 'yes', '1', 'on')
    
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
    
    @staticmethod
    def _parse_bool(value: str) -> bool:
        """Parse string to boolean."""
        if isinstance(value, bool):
            return value
        return value.lower() in ('true', 'yes', '1', 'on')


@dataclass
class Config:
    """
    Main configuration class that combines all configuration sections.
    
    This class provides a unified interface to all configuration settings
    and handles loading from environment variables and .env files.
    """
    
    # Configuration sections
    API: APIConfig = field(default_factory=APIConfig)
    TRADING: TradingConfig = field(default_factory=TradingConfig)
    DASHBOARD: DashboardConfig = field(default_factory=DashboardConfig)
    LOGGING: LoggingConfig = field(default_factory=LoggingConfig)
    PERFORMANCE: PerformanceConfig = field(default_factory=PerformanceConfig)
    
    # Base directories
    DATA_DIR: str = field(default="DATA")
    LOGS_DIR: str = field(default="LOGS")
    STATIC_DIR: str = field(default="DATA/static")
    
    # Cache for configuration values
    _config_cache: Dict[str, Any] = field(default_factory=dict, repr=False)
    
    # Flag indicating whether .env file has been loaded
    _env_loaded: bool = field(default=False, repr=False)
    
    def __post_init__(self):
        """Load environment variables and ensure directories exist."""
        self._load_env()
        self.ensure_directories()
    
    def _load_env(self) -> None:
        """Load environment variables from .env file if available."""
        if self._env_loaded:
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
        
        self._env_loaded = True
    
    def get(self, name: str, default: Any = None) -> Any:
        """
        Get configuration value by name.
        
        Args:
            name: Name of the configuration value
            default: Default value if configuration is not found
            
        Returns:
            Configuration value or default
        """
        # Check cache first
        if name in self._config_cache:
            return self._config_cache[name]
        
        # Get value from environment
        value = os.environ.get(name, default)
        
        # Convert boolean strings to actual booleans
        if isinstance(value, str):
            if value.lower() in ('true', 'yes', '1', 'on'):
                value = True
            elif value.lower() in ('false', 'no', '0', 'off'):
                value = False
        
        # Cache the value
        self._config_cache[name] = value
        
        return value
    
    def set(self, name: str, value: Any) -> None:
        """
        Set configuration value.
        
        Args:
            name: Name of the configuration value
            value: Value to set
        """
        self._config_cache[name] = value
    
    def clear_cache(self) -> None:
        """Clear the configuration cache."""
        self._config_cache.clear()
        self._env_loaded = False
    
    def ensure_directories(self) -> None:
        """Create necessary directories if they don't exist."""
        os.makedirs(self.DATA_DIR, exist_ok=True)
        os.makedirs(self.LOGS_DIR, exist_ok=True)
        os.makedirs(self.STATIC_DIR, exist_ok=True)
    
    def validate(self) -> Dict[str, str]:
        """
        Validate configuration values.
        
        Returns:
            Dictionary of validation errors (empty if valid)
        """
        errors = {}
        
        # Validate trading configuration
        if self.TRADING.TARGET_FRACTION <= 0 or self.TRADING.TARGET_FRACTION > 1:
            errors['TARGET_FRACTION'] = "Must be between 0 and 1"
        
        if self.TRADING.UPDATE_INTERVAL < 1:
            errors['UPDATE_INTERVAL'] = "Must be at least 1 second"
        
        if self.TRADING.CONFIDENCE_THRESHOLD < 0 or self.TRADING.CONFIDENCE_THRESHOLD > 1:
            errors['CONFIDENCE_THRESHOLD'] = "Must be between 0 and 1"
        
        # Validate dashboard configuration
        if self.DASHBOARD.PORT < 1 or self.DASHBOARD.PORT > 65535:
            errors['DASHBOARD_PORT'] = "Must be between 1 and 65535"
        
        # Validate logging configuration
        if self.LOGGING.CLEAN_LOGS_MAX_AGE_HOURS < 1:
            errors['CLEAN_LOGS_MAX_AGE_HOURS'] = "Must be at least 1 hour"
        
        return errors
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary."""
        return {
            'API': self.API.__dict__,
            'TRADING': self.TRADING.__dict__,
            'DASHBOARD': self.DASHBOARD.__dict__,
            'LOGGING': self.LOGGING.__dict__,
            'PERFORMANCE': self.PERFORMANCE.__dict__,
            'DATA_DIR': self.DATA_DIR,
            'LOGS_DIR': self.LOGS_DIR,
            'STATIC_DIR': self.STATIC_DIR,
        }
    
    def update_from_dict(self, config_dict: Dict[str, Any]) -> None:
        """Update configuration from dictionary."""
        for section_name, section_data in config_dict.items():
            if hasattr(self, section_name):
                section = getattr(self, section_name)
                if hasattr(section, '__dict__'):
                    for key, value in section_data.items():
                        if hasattr(section, key):
                            setattr(section, key, value)


# Global configuration instance
@lru_cache(maxsize=1)
def get_config() -> Config:
    """Get the global configuration instance."""
    return Config()


# Convenience access to configuration
Config = get_config()

# Backward compatibility aliases
TradingConfig = Config.TRADING
DashboardConfig = Config.DASHBOARD
LoggingConfig = Config.LOGGING
APIConfig = Config.API
StrategyConfig = Config.TRADING  # Strategy config is now part of TradingConfig
PerformanceConfig = Config.PERFORMANCE