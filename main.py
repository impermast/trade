"""
Main entry point for the Trade Project.

This module initializes and runs the trading system with configurable components:
- Trading engine with multiple strategies
- Web dashboard for monitoring
- Plot visualization (optional)
- Logging and error handling

Configuration is centralized in CORE.config module.
"""

import asyncio
import os
import sys
import time
from datetime import datetime, timedelta
import json
import logging
from pathlib import Path
import webbrowser
from typing import Optional

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# ==================== CONFIGURATION IMPORTS ====================
from CORE.config import (
    TradingConfig, DashboardConfig, LoggingConfig, 
    APIConfig, StrategyConfig, PerformanceConfig
)

# ==================== CORE MODULES ====================
from CORE.dashboard_manager import DashboardManager, write_state_fallback
from CORE.trading_engine import TradingEngine, TradingEngineFactory
from CORE.log_manager import LogManager, Logger, clean_logs_by_age

# ==================== API MODULES ====================
from API.bybit_api import BybitAPI
from API.mock_api import MockAPI
from API.dashboard_api import run_flask_in_new_terminal, stop_flask

# ==================== VISUALIZATION ====================
from BOTS.PLOTBOTS.plotbot import PlotBot

# ==================== GLOBAL VARIABLES ====================
# Event for graceful shutdown
stop_event = asyncio.Event()

# Logger instance (will be initialized in __main__)
logger = None

# ==================== CONFIGURATION CONSTANTS ====================
# Get paths from configuration
STATE_PATH = LoggingConfig.STATE_PATH
CSV_ANAL_PATH = TradingConfig.get_csv_paths()['anal']

# ==================== API INITIALIZATION ====================
def initialize_api_client():
    """Initialize the appropriate API client based on configuration."""
    if APIConfig.USE_MOCK_API:
        logger.info("Initializing MockAPI for simulation")
        return MockAPI()
    elif APIConfig.USE_BYBIT_API:
        logger.info("Initializing BybitAPI")
        return BybitAPI()
    elif APIConfig.USE_COINBASE_API:
        logger.info("Initializing CoinbaseAPI")
        # TODO: Implement CoinbaseAPI
        return MockAPI()  # fallback
    elif APIConfig.USE_BINANCE_API:
        logger.info("Initializing BinanceAPI")
        # TODO: Implement BinanceAPI
        return MockAPI()  # fallback
    else:
        logger.info("No specific API selected, using MockAPI as fallback")
        return MockAPI()

# ==================== COMPONENT INITIALIZATION ====================
def initialize_components():
    """Initialize core system components."""
    global logger
    
    # Initialize log manager
    log_manager = LogManager()
    
    # Clean old logs
    stats = log_manager.clean_old_logs()
    
    # Initialize main logger
    logger = Logger(
        name=LoggingConfig.MAIN_LOGGER_NAME,
        tag=LoggingConfig.MAIN_LOGGER_TAG,
        logfile=LoggingConfig.MAIN_LOGGER_FILE,
        console=False
    ).get_logger()
    
    # Log initialization info
    logger.info(f"[INIT] Trim logs: processed={stats['processed']} changed={stats['changed']} "
                f"saved_bytes={stats['saved_bytes']} (cutoff {LoggingConfig.CLEAN_LOGS_MAX_AGE_HOURS}h)")
    
    # Initialize dashboard manager
    dashboard_manager = DashboardManager()
    
    return log_manager, dashboard_manager

# ==================== PLOT VISUALIZATION ====================
async def plot_loop(use_plot: bool) -> None:
    """Run plot visualization loop if enabled."""
    if not use_plot:
        return
        
    logger.info("Starting PlotBot visualization")
    
    def _start():
        plotbot = PlotBot(
            csv_file=CSV_ANAL_PATH, 
            refresh_interval=TradingConfig.UPDATE_INTERVAL
        )
        plotbot.start()
    
    # Run in executor to avoid blocking
    loop = asyncio.get_running_loop()
    await loop.run_in_executor(None, _start)

# ==================== TRADING ENGINE ====================
async def unified_trading_loop(api_client) -> None:
    """Main trading loop that coordinates all strategies."""
    logger.info(f"Starting unified trading loop with {type(api_client).__name__}")
    
    try:
        # Create trading engine with standard configuration
        trading_engine = TradingEngineFactory.create_standard_engine(api_client, logger)
        
        # Start the trading loop
        await trading_engine.start_trading_loop(stop_event)
        
    except asyncio.CancelledError:
        logger.info("Trading loop cancelled")
        raise
    except Exception as e:
        logger.error(f"Error in trading loop: {e}", exc_info=True)
        raise
    finally:
        logger.info("Trading loop finished")

# ==================== DASHBOARD MANAGEMENT ====================
async def start_dashboard(dashboard_manager) -> Optional[object]:
    """Start the web dashboard if enabled."""
    if not DashboardConfig.USE_FLASK:
        logger.info("Dashboard disabled in configuration")
        return None
    
    logger.info("Starting Flask dashboard")
    
    try:
        # Start Flask in new terminal
        raw_popen = run_flask_in_new_terminal(
            host=DashboardConfig.HOST,
            port=DashboardConfig.PORT,
            log_path=LoggingConfig.DASHBOARD_LOG_FILE
        )
        
        # Wait for dashboard to start
        ok = await dashboard_manager._wait_for_port(
            DashboardConfig.HOST, 
            DashboardConfig.PORT, 
            timeout=DashboardConfig.PORT_WAIT_TIMEOUT
        )
        
        if not ok:
            logger.error(f"Dashboard failed to start on {DashboardConfig.HOST}:{DashboardConfig.PORT}")
            return raw_popen
        
        # Log success and open browser
        url = DashboardConfig.get_url()
        logger.info(f"Dashboard available at {url}")
        
        if DashboardConfig.AUTO_OPEN_BROWSER:
            try:
                webbrowser.open_new_tab(url)
            except Exception as e:
                logger.warning(f"Failed to open browser: {e}")
        
        return raw_popen
        
    except Exception as e:
        logger.error(f"Failed to start dashboard: {e}")
        return None

# ==================== MAIN APPLICATION ====================
async def main() -> None:
    """Main application entry point."""
    logger.info("Starting Trade Project application")
    
    # Initialize components
    log_manager, dashboard_manager = initialize_components()
    
    # Initialize API client
    api_client = initialize_api_client()
    
    # Start dashboard
    dashboard_process = await start_dashboard(dashboard_manager)
    
    try:
        # Run main application tasks
        await asyncio.gather(
            unified_trading_loop(api_client),
            plot_loop(DashboardConfig.USE_PLOT),
        )
        
    except KeyboardInterrupt:
        logger.warning("KeyboardInterrupt received, shutting down gracefully")
        stop_event.set()
    except Exception as e:
        logger.error(f"Critical error in main application: {e}", exc_info=True)
        stop_event.set()
    finally:
        # Cleanup
        await asyncio.sleep(0.5)
        
        if dashboard_process and DashboardConfig.USE_FLASK:
            logger.info("Stopping dashboard")
            stop_flask(dashboard_process)
        
        logger.info("Application shutdown complete")

# ==================== ENTRY POINT ====================
if __name__ == "__main__":
    try:
        # Initialize components first
        log_manager, dashboard_manager = initialize_components()
        
        # Run main application
        asyncio.run(main())
        
    except KeyboardInterrupt:
        if logger:
            logger.warning("KeyboardInterrupt outside asyncio.run")
        else:
            print("KeyboardInterrupt received during initialization")
    except Exception as e:
        if logger:
            logger.error(f"Fatal error during initialization: {e}", exc_info=True)
        else:
            print(f"Fatal error during initialization: {e}")
            import traceback
            traceback.print_exc()
