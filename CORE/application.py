"""
Application lifecycle management for the Trade Project.

This module provides a centralized way to manage the application lifecycle,
including initialization, running, and graceful shutdown of all components.
"""

import asyncio
import logging
from typing import Optional, Dict, Any
from pathlib import Path

from .config import Config
from .dashboard_manager import DashboardManager
from .trading_engine import TradingEngine, TradingEngineFactory
from .log_manager import LogManager, Logger, clean_logs_by_age
from .dependency_injection import get_container, register_service, register_singleton
from STRATEGY import StrategyManager

class Application:
    """
    Main application class that manages the lifecycle of all components.
    
    Responsibilities:
    - Initialize all system components
    - Manage component lifecycle
    - Handle graceful shutdown
    - Coordinate between components
    """
    
    def __init__(self):
        """Initialize the Application instance."""
        self.logger: Optional[Logger] = None
        self.log_manager: Optional[LogManager] = None
        self.dashboard_manager: Optional[DashboardManager] = None
        self.trading_engine: Optional[TradingEngine] = None
        self.api_client: Optional[Any] = None
        self.dashboard_process: Optional[Any] = None
        
        # Application state
        self.is_running = False
        self.stop_event = asyncio.Event()
        
        # Component status
        self.component_status: Dict[str, str] = {}
        
        # Get dependency container
        self.container = get_container()
        
        # Register services
        self._register_services()
    
    def _register_services(self) -> None:
        """Register all application services in the DI container."""
        # Register core services
        register_service(LogManager, lambda: LogManager())
        register_service(DashboardManager, lambda: DashboardManager())
        
        # Register API client factory
        register_service('api_client', self._create_api_client)
        
        # Register strategy manager
        register_service(StrategyManager, lambda: StrategyManager())
        
        # Register trading engine factory
        register_service('trading_engine', self._create_trading_engine)
    
    def _create_api_client(self) -> Any:
        """Create API client based on configuration."""
        if Config.API.USE_MOCK_API:
            from API import MockAPI
            return MockAPI()
        elif Config.API.USE_BYBIT_API:
            from API import BybitAPI
            return BybitAPI()
        elif Config.API.USE_COINBASE_API:
            # TODO: Implement CoinbaseAPI
            from API import MockAPI
            return MockAPI()  # fallback
        elif Config.API.USE_BINANCE_API:
            # TODO: Implement BinanceAPI
            from API import MockAPI
            return MockAPI()  # fallback
        else:
            self.logger.warning("API not found!")
            return MockAPI()
    
    def _create_trading_engine(self) -> TradingEngine:
        """Create trading engine with dependencies."""
        api_client = self.container.get_service('api_client')
        return TradingEngineFactory.create_standard_engine(api_client, self.logger)
    
    async def initialize(self) -> None:
        """
        Initialize all application components.
        
        This method sets up the logging system, dashboard manager,
        trading engine, and API client in the correct order.
        """
        try:
            # 1. Initialize logging system first
            await self._initialize_logging()
            
            # 2. Initialize dashboard manager
            await self._initialize_dashboard_manager()
            
            # 3. Initialize API client
            await self._initialize_api_client()
            
            # 4. Initialize trading engine
            await self._initialize_trading_engine()
            
            self.logger.info("Application initialization completed successfully")
            
        except Exception as e:
            if self.logger:
                self.logger.error(f"Failed to initialize application: {e}", exc_info=True)
            else:
                print(f"Failed to initialize application: {e}")
            raise
    
    async def _initialize_logging(self) -> None:
        """Initialize the logging system."""
        self.log_manager = self.container.get_service(LogManager)
        
        # Clean old logs
        stats = self.log_manager.clean_old_logs()
        
        # Initialize main logger
        self.logger = Logger(
            name=Config.LOGGING.MAIN_LOGGER_NAME,
            tag=Config.LOGGING.MAIN_LOGGER_TAG,
            logfile=Config.LOGGING.MAIN_LOGGER_FILE,
            console=False
        ).get_logger()
        
        # Register logger as singleton
        register_singleton(Logger, self.logger)
        
        # Log initialization info
        self.logger.info(f"[INIT] Trim logs: processed={stats['processed']} changed={stats['changed']} "
                        f"saved_bytes={stats['saved_bytes']} (cutoff {Config.LOGGING.CLEAN_LOGS_MAX_AGE_HOURS}h)")
        
        self.component_status['logging'] = 'initialized'
    
    async def _initialize_dashboard_manager(self) -> None:
        """Initialize the dashboard manager."""
        self.dashboard_manager = self.container.get_service(DashboardManager)
        self.component_status['dashboard_manager'] = 'initialized'
    
    async def _initialize_api_client(self) -> None:
        """Initialize the appropriate API client based on configuration."""
        self.api_client = self.container.get_service('api_client')
        
        if Config.API.USE_MOCK_API:
            self.logger.info("MockAPI initialized for simulation")
        elif Config.API.USE_BYBIT_API:
            self.logger.info("BybitAPI initialized")
        elif Config.API.USE_COINBASE_API:
            self.logger.info("CoinbaseAPI initialized (fallback to MockAPI)")
        elif Config.API.USE_BINANCE_API:
            self.logger.info("BinanceAPI initialized (fallback to MockAPI)")
        else:
            self.logger.info("MockAPI initialized as fallback")
        
        self.component_status['api_client'] = 'initialized'
    
    async def _initialize_trading_engine(self) -> None:
        """Initialize the trading engine."""
        self.trading_engine = self.container.get_service('trading_engine')
        self.component_status['trading_engine'] = 'initialized'
    
    async def start_dashboard(self) -> Optional[Any]:
        """
        Start the web dashboard if enabled.
        
        Returns:
            Dashboard process object or None if disabled
        """
        if not Config.DASHBOARD.USE_FLASK:
            self.logger.info("Dashboard disabled in configuration")
            return None
        
        self.logger.info("Starting Flask dashboard")
        
        try:
            from API import run_flask_in_new_terminal, stop_flask
            
            # Start Flask in new terminal
            raw_popen = run_flask_in_new_terminal(
                host=Config.DASHBOARD.HOST,
                port=Config.DASHBOARD.PORT,
                log_path=Config.LOGGING.DASHBOARD_LOG_FILE
            )
            
            # Wait for dashboard to start
            ok = await self.dashboard_manager._wait_for_port(
                Config.DASHBOARD.HOST, 
                Config.DASHBOARD.PORT, 
                timeout=Config.DASHBOARD.PORT_WAIT_TIMEOUT
            )
            
            if not ok:
                self.logger.error(f"Dashboard failed to start on {Config.DASHBOARD.HOST}:{Config.DASHBOARD.PORT}")
                return raw_popen
            
            # Log success and open browser
            url = Config.DASHBOARD.get_url()
            self.logger.info(f"Dashboard available at {url}")
            
            if Config.DASHBOARD.AUTO_OPEN_BROWSER:
                try:
                    import webbrowser
                    webbrowser.open_new_tab(url)
                except Exception as e:
                    self.logger.warning(f"Failed to open browser: {e}")
            
            self.dashboard_process = raw_popen
            self.component_status['dashboard'] = 'running'
            return raw_popen
            
        except Exception as e:
            self.logger.error(f"Failed to start dashboard: {e}")
            return None
    
    async def start_trading(self) -> None:
        """Start the trading engine."""
        if not self.trading_engine:
            raise RuntimeError("Trading engine not initialized")
        
        self.logger.info("Starting trading engine")
        await self.trading_engine.start_trading_loop(self.stop_event)
        self.component_status['trading'] = 'running'
    
    async def start_plot_visualization(self) -> None:
        """Start plot visualization if enabled."""
        if not Config.DASHBOARD.USE_PLOT:
            return
        
        self.logger.info("Starting PlotBot visualization")
        
        try:
            from BOTS import PlotBot
            
            def _start():
                plotbot = PlotBot(
                    csv_file=Config.TRADING.get_csv_paths()['anal'], 
                    refresh_interval=Config.TRADING.UPDATE_INTERVAL
                )
                plotbot.start()
            
            # Run in executor to avoid blocking
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(None, _start)
            self.component_status['plot'] = 'running'
            
        except Exception as e:
            self.logger.error(f"Failed to start plot visualization: {e}")
    
    async def run(self) -> None:
        """
        Main application run method.
        
        This method coordinates all components and runs the main application loop.
        """
        self.logger.info("Starting Trade Project application")
        self.is_running = True
        
        try:
            # Start dashboard
            await self.start_dashboard()
            
            # Run main application tasks
            await asyncio.gather(
                self.start_trading(),
                self.start_plot_visualization(),
            )
            
        except KeyboardInterrupt:
            self.logger.warning("KeyboardInterrupt received, shutting down gracefully")
            self.stop_event.set()
        except Exception as e:
            self.logger.error(f"Critical error in main application: {e}", exc_info=True)
            self.stop_event.set()
        finally:
            await self.shutdown()
    
    async def shutdown(self) -> None:
        """Gracefully shutdown all application components."""
        self.logger.info("Starting application shutdown")
        self.is_running = False
        
        # Set stop event
        self.stop_event.set()
        
        # Wait a bit for components to stop
        await asyncio.sleep(0.5)
        
        # Stop dashboard
        if self.dashboard_process and Config.DASHBOARD.USE_FLASK:
            self.logger.info("Stopping dashboard")
            try:
                from API import stop_flask
                stop_flask(self.dashboard_process)
            except Exception as e:
                self.logger.error(f"Error stopping dashboard: {e}")
        
        # Update component status
        self.component_status.update({
            'dashboard': 'stopped',
            'trading': 'stopped',
            'plot': 'stopped'
        })
        
        self.logger.info("Application shutdown complete")
    
    def get_status(self) -> Dict[str, str]:
        """Get the current status of all components."""
        return {
            'application': 'running' if self.is_running else 'stopped',
            **self.component_status
        }
    
    def is_healthy(self) -> bool:
        """Check if all critical components are healthy."""
        critical_components = ['logging', 'api_client', 'trading_engine']
        return all(
            self.component_status.get(comp) in ['initialized', 'running'] 
            for comp in critical_components
        )
