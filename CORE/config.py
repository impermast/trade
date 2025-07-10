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


# Default configuration values
DEFAULT_CONFIG = {
    'API_KEY': None,
    'API_SECRET': None,
    'TESTNET': True,
    'LOG_LEVEL': 'INFO',
    'DATA_DIR': 'DATA',
    'LOG_DIR': 'LOGS',
}

# Set default values in the cache
for key, value in DEFAULT_CONFIG.items():
    if Config.get(key) is None:
        Config.set(key, value)