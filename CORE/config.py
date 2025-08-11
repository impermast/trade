"""
Configuration management system for the Trade Project.

This module provides a centralized configuration system for the Trade Project.
It loads configuration values from environment variables or .env file and provides
default values for missing configurations.

Usage:
    from CORE.config import Config, TradingConfig, DashboardConfig
    
    # Get configuration values
    api_key = Config.API_KEY
    testnet = Config.TESTNET
    
    # Get configuration with default value
    log_level = Config.get('LOG_LEVEL', 'INFO')
    
    # Get trading configuration
    symbol = TradingConfig.SYMBOL
    timeframe = TradingConfig.TIMEFRAME
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
    print("python-dotenv not installed. Environment variables will be loaded from OS only.")
    print("To enable .env file support, install python-dotenv: pip install python-dotenv")


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


class TradingConfig:
    """Configuration for trading operations."""
    
    # Trading parameters
    SYMBOL = "BTC/USDT"
    TIMEFRAME = "1m"
    UPDATE_INTERVAL = 10  # seconds between ticks for simulation
    
    # Strategy parameters
    RSI_PERIOD = 14
    RSI_LOWER = 30.0
    RSI_UPPER = 70.0
    TARGET_FRACTION = 0.25  # fraction of balance to use per trade
    MIN_QUANTITY = 0.001
    
    @classmethod
    def get_symbol_name(cls) -> str:
        """Get symbol name without slash."""
        return cls.SYMBOL.replace("/", "")
    
    @classmethod
    def get_csv_paths(cls) -> Dict[str, str]:
        """Get CSV file paths for different data types."""
        symbol_name = cls.get_symbol_name()
        return {
            'raw': f"DATA/{symbol_name}_{cls.TIMEFRAME}.csv",
            'rsi_anal': f"DATA/{symbol_name}_{cls.TIMEFRAME}_anal.csv",
            'xgb_anal': f"DATA/{symbol_name}_{cls.TIMEFRAME}_xgb.csv"
        }


class DashboardConfig:
    """Configuration for dashboard and web interface."""
    
    # Flask settings
    HOST = os.getenv("DASHBOARD_HOST", "127.0.0.1")
    PORT = int(os.getenv("DASHBOARD_PORT", "5000"))
    
    # Features
    USE_FLASK = True
    USE_PLOT = False
    
    @classmethod
    def get_url(cls) -> str:
        """Get dashboard URL."""
        return f"http://{cls.HOST}:{cls.PORT}"


class PathConfig:
    """Configuration for file paths and directories."""
    
    # Base directories
    DATA_DIR = "DATA"
    LOGS_DIR = "LOGS"
    STATIC_DIR = os.path.join(DATA_DIR, "static")
    
    # State file
    STATE_PATH = os.path.join(STATIC_DIR, "state.json")
    
    @classmethod
    def ensure_directories(cls) -> None:
        """Create necessary directories if they don't exist."""
        os.makedirs(cls.DATA_DIR, exist_ok=True)
        os.makedirs(cls.LOGS_DIR, exist_ok=True)
        os.makedirs(cls.STATIC_DIR, exist_ok=True)


class LoggingConfig:
    """Configuration for logging system."""
    
    # Log cleanup settings
    CLEAN_LOGS_MAX_AGE_HOURS = int(os.getenv("CLEAN_LOGS_MAX_AGE_HOURS", "24"))
    
    # Logger names
    MAIN_LOGGER_NAME = "MainBot"
    MAIN_LOGGER_TAG = "[MAIN]"
    MAIN_LOGGER_FILE = os.path.join(PathConfig.LOGS_DIR, "mainbot.log")
    
    # Dashboard logging
    DASHBOARD_LOG_FILE = os.path.join(PathConfig.LOGS_DIR, "dashboard.out.log")


class APIConfig:
    """Configuration for API connections."""
    
    # API selection (MockAPI is fastest for simulation)
    USE_MOCK_API = True
    USE_BYBIT_API = False
    
    # API credentials (loaded from environment)
    API_KEY = Config.get('API_KEY')
    API_SECRET = Config.get('API_SECRET')
    TESTNET = Config.get('TESTNET', True)


# Default configuration values
DEFAULT_CONFIG = {
    'API_KEY': None,
    'API_SECRET': None,
    'TESTNET': True,
    'LOG_LEVEL': 'INFO',
    'DATA_DIR': 'DATA',
    'LOG_DIR': 'LOGS',
}

# Set default values in the config cache
for key, value in DEFAULT_CONFIG.items():
    if Config.get(key) is None:
        Config.set(key, value)

# Ensure directories exist on import
PathConfig.ensure_directories()