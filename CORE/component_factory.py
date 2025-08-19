"""
Component factory for the Trade Project.

This module provides factory methods for creating and configuring
various system components with proper dependency injection.
"""

from typing import Dict, Any, Optional, Type
import logging

from .config import Config
from .log_manager import Logger, LogManager
from .dashboard_manager import DashboardManager
from .trading_engine import TradingEngine, TradingEngineFactory
from .strategy_manager import StrategyManager


class ComponentFactory:
    """
    Factory class for creating and configuring system components.
    
    This class centralizes component creation logic and ensures
    proper dependency injection and configuration.
    """
    
    _instances: Dict[str, Any] = {}
    
    @classmethod
    def create_logger(
        cls, 
        name: str, 
        tag: str, 
        logfile: str, 
        console: bool = False
    ) -> Logger:
        """
        Create a logger instance.
        
        Args:
            name: Logger name
            tag: Logger tag
            logfile: Log file path
            console: Whether to output to console
            
        Returns:
            Configured Logger instance
        """
        key = f"logger_{name}"
        if key not in cls._instances:
            cls._instances[key] = Logger(name, tag, logfile, console)
        return cls._instances[key]
    
    @classmethod
    def create_log_manager(cls) -> LogManager:
        """
        Create a log manager instance.
        
        Returns:
            Configured LogManager instance
        """
        if "log_manager" not in cls._instances:
            cls._instances["log_manager"] = LogManager()
        return cls._instances["log_manager"]
    
    @classmethod
    def create_dashboard_manager(cls) -> DashboardManager:
        """
        Create a dashboard manager instance.
        
        Returns:
            Configured DashboardManager instance
        """
        if "dashboard_manager" not in cls._instances:
            cls._instances["dashboard_manager"] = DashboardManager()
        return cls._instances["dashboard_manager"]
    
    @classmethod
    def create_api_client(cls, logger: Logger) -> Any:
        """
        Create an API client based on configuration.
        
        Args:
            logger: Logger instance for logging
            
        Returns:
            Configured API client instance
        """
        if "api_client" not in cls._instances:
            if Config.API.USE_MOCK_API:
                logger.info("Creating MockAPI instance")
                from API.mock_api import MockAPI
                cls._instances["api_client"] = MockAPI()
            elif Config.API.USE_BYBIT_API:
                logger.info("Creating BybitAPI instance")
                from API.bybit_api import BybitAPI
                cls._instances["api_client"] = BybitAPI()
            elif Config.API.USE_COINBASE_API:
                logger.info("Creating CoinbaseAPI instance")
                # TODO: Implement CoinbaseAPI
                from API.mock_api import MockAPI
                cls._instances["api_client"] = MockAPI()  # fallback
            elif Config.API.USE_BINANCE_API:
                logger.info("Creating BinanceAPI instance")
                # TODO: Implement BinanceAPI
                from API.mock_api import MockAPI
                cls._instances["api_client"] = MockAPI()  # fallback
            else:
                logger.info("No specific API selected, creating MockAPI as fallback")
                from API.mock_api import MockAPI
                cls._instances["api_client"] = MockAPI()
        
        return cls._instances["api_client"]
    
    @classmethod
    def create_strategy_manager(cls, logger: Logger) -> StrategyManager:
        """
        Create a strategy manager instance.
        
        Args:
            logger: Logger instance for logging
            
        Returns:
            Configured StrategyManager instance
        """
        if "strategy_manager" not in cls._instances:
            cls._instances["strategy_manager"] = StrategyManager()
        return cls._instances["strategy_manager"]
    
    @classmethod
    def create_trading_engine(
        cls, 
        api_client: Any, 
        logger: Logger
    ) -> TradingEngine:
        """
        Create a trading engine instance.
        
        Args:
            api_client: API client instance
            logger: Logger instance for logging
            
        Returns:
            Configured TradingEngine instance
        """
        if "trading_engine" not in cls._instances:
            cls._instances["trading_engine"] = TradingEngineFactory.create_standard_engine(
                api_client, 
                logger
            )
        return cls._instances["trading_engine"]
    
    @classmethod
    def create_plot_bot(cls, logger: Logger) -> Optional[Any]:
        """
        Create a plot bot instance if enabled.
        
        Args:
            logger: Logger instance for logging
            
        Returns:
            PlotBot instance or None if disabled
        """
        if not Config.DASHBOARD.USE_PLOT:
            return None
        
        if "plot_bot" not in cls._instances:
            try:
                from BOTS.PLOTBOTS.plotbot import PlotBot
                cls._instances["plot_bot"] = PlotBot(
                    csv_file=Config.TRADING.get_csv_paths()['anal'],
                    refresh_interval=Config.TRADING.UPDATE_INTERVAL
                )
                logger.info("PlotBot instance created successfully")
            except Exception as e:
                logger.error(f"Failed to create PlotBot: {e}")
                return None
        
        return cls._instances["plot_bot"]
    
    @classmethod
    def get_component(cls, component_name: str) -> Optional[Any]:
        """
        Get an existing component instance.
        
        Args:
            component_name: Name of the component
            
        Returns:
            Component instance or None if not found
        """
        return cls._instances.get(component_name)
    
    @classmethod
    def clear_instances(cls) -> None:
        """Clear all component instances (useful for testing)."""
        cls._instances.clear()
    
    @classmethod
    def get_component_status(cls) -> Dict[str, str]:
        """
        Get the status of all components.
        
        Returns:
            Dictionary mapping component names to their status
        """
        status = {}
        for name, instance in cls._instances.items():
            if hasattr(instance, 'is_running'):
                status[name] = 'running' if instance.is_running else 'stopped'
            elif hasattr(instance, 'status'):
                status[name] = instance.status
            else:
                status[name] = 'initialized'
        return status
