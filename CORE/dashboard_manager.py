"""
Dashboard manager for the Trade Project.

This module manages the web dashboard functionality, including
state management, data updates, and dashboard communication.
"""

import asyncio
import json
import logging
import os
import time
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
import pandas as pd

from .config import Config


class DashboardManager:
    """
    Manages the web dashboard functionality.
    
    This class handles:
    - Dashboard state management
    - Data updates and synchronization
    - Dashboard communication
    - State persistence
    """
    
    def __init__(self):
        """Initialize the DashboardManager."""
        self.logger = logging.getLogger(__name__)
        self.host = Config.DASHBOARD.HOST
        self.port = Config.DASHBOARD.PORT
        self.state_path = Config.LOGGING.STATE_PATH
        
        # Dashboard state
        self.state = {}
        self.last_update = None
        self.update_interval = 1.0  # seconds
        
        # Ensure state directory exists
        os.makedirs(os.path.dirname(self.state_path), exist_ok=True)
        
        # Load initial state
        self._load_state()
        
        self.logger.info(f"DashboardManager initialized for {self.host}:{self.port}")
    
    def _load_state(self) -> None:
        """Load dashboard state from file."""
        try:
            if os.path.exists(self.state_path):
                with open(self.state_path, 'r', encoding='utf-8') as f:
                    self.state = json.load(f)
                self.logger.info(f"Loaded dashboard state from {self.state_path}")
            else:
                self.state = self._get_default_state()
                self._save_state()
                self.logger.info("Created default dashboard state")
        except Exception as e:
            self.logger.error(f"Failed to load dashboard state: {e}")
            self.state = self._get_default_state()
    
    def _get_default_state(self) -> Dict[str, Any]:
        """Get default dashboard state."""
        return {
            'timestamp': datetime.now().isoformat(),
            'status': 'initializing',
            'components': {
                'trading_engine': 'stopped',
                'dashboard': 'stopped',
                'api_client': 'stopped',
                'plot_bot': 'stopped'
            },
            'trading': {
                'symbol': Config.TRADING.SYMBOL,
                'timeframe': Config.TRADING.TIMEFRAME,
                'position_size': 0.0,
                'last_action': 'none',
                'balance': 0.0,
                'equity': 0.0
            },
            'performance': {
                'total_trades': 0,
                'winning_trades': 0,
                'losing_trades': 0,
                'total_pnl': 0.0,
                'win_rate': 0.0
            },
            'last_update': datetime.now().isoformat()
        }
    
    def _save_state(self) -> None:
        """Save dashboard state to file."""
        try:
            self.state['last_update'] = datetime.now().isoformat()
            with open(self.state_path, 'w', encoding='utf-8') as f:
                json.dump(self.state, f, indent=2, ensure_ascii=False, default=str)
        except Exception as e:
            self.logger.error(f"Failed to save dashboard state: {e}")
    
    def update_component_status(self, component: str, status: str) -> None:
        """
        Update the status of a component.
        
        Args:
            component: Component name
            status: Component status
        """
        if 'components' not in self.state:
            self.state['components'] = {}
        
        self.state['components'][component] = status
        self._save_state()
        
        self.logger.debug(f"Updated component {component} status to {status}")
    
    def update_trading_info(self, trading_info: Dict[str, Any]) -> None:
        """
        Update trading information.
        
        Args:
            trading_info: Trading information dictionary
        """
        if 'trading' not in self.state:
            self.state['trading'] = {}
        
        self.state['trading'].update(trading_info)
        self._save_state()
        
        self.logger.debug("Updated trading information")
    
    def update_performance_info(self, performance_info: Dict[str, Any]) -> None:
        """
        Update performance information.
        
        Args:
            performance_info: Performance information dictionary
        """
        if 'performance' not in self.state:
            self.state['performance'] = {}
        
        self.state['performance'].update(performance_info)
        self._save_state()
        
        self.logger.debug("Updated performance information")
    
    def get_state(self) -> Dict[str, Any]:
        """Get current dashboard state."""
        return self.state.copy()
    
    async def _wait_for_port(self, host: str, port: int, timeout: int = 10) -> bool:
        """
        Wait for a port to become available.
        
        Args:
            host: Host to check
            port: Port to check
            timeout: Timeout in seconds
            
        Returns:
            True if port is available, False otherwise
        """
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            try:
                reader, writer = await asyncio.wait_for(
                    asyncio.open_connection(host, port),
                    timeout=1.0
                )
                writer.close()
                await writer.wait_closed()
                return True
            except (asyncio.TimeoutError, ConnectionRefusedError, OSError):
                await asyncio.sleep(0.1)
        
        return False
    
    async def start(self) -> None:
        """Start the dashboard manager."""
        self.logger.info("Starting dashboard manager")
        self.update_component_status('dashboard', 'running')
    
    async def stop(self) -> None:
        """Stop the dashboard manager."""
        self.logger.info("Stopping dashboard manager")
        self.update_component_status('dashboard', 'stopped')
        self._save_state()
    
    def is_running(self) -> bool:
        """Check if dashboard manager is running."""
        return self.state.get('components', {}).get('dashboard') == 'running'


# Fallback function for writing state
def write_state_fallback(state: Dict[str, Any], state_path: str) -> None:
    """
    Fallback function for writing state when dashboard manager is not available.
    
    Args:
        state: State to write
        state_path: Path to write state to
    """
    try:
        os.makedirs(os.path.dirname(state_path), exist_ok=True)
        with open(state_path, 'w', encoding='utf-8') as f:
            json.dump(state, f, indent=2, ensure_ascii=False, default=str)
    except Exception as e:
        logging.error(f"Failed to write state fallback: {e}")
