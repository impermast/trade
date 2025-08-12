"""
Dashboard management system for the Trade Project.

This module provides a web-based dashboard for monitoring and controlling
the trading system, including real-time data visualization and system status.
"""

import os
import sys
import json
import logging
import threading
import time
import asyncio
import socket
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, Optional, List
import webbrowser
import subprocess

# Flask imports
try:
    from flask import Flask, render_template, jsonify, request, send_from_directory
    from flask_cors import CORS
    _has_flask = True
except ImportError:
    _has_flask = False
    logging.warning("Flask not installed. Dashboard will not be available.")
    logging.warning("To enable dashboard, install Flask: pip install flask flask-cors")

# Import configuration and other modules
from .config import DashboardConfig, LoggingConfig
from .log_manager import LogManager


class DashboardManager:
    """
    Centralized dashboard management system.
    
    Handles dashboard startup, shutdown, port management, and utility operations.
    """
    
    def __init__(self, trading_engine=None):
        """
        Initialize the DashboardManager.
        
        Args:
            trading_engine: Optional TradingEngine instance for real-time data
        """
        self.trading_engine = trading_engine
        self.app = None
        self.server_thread = None
        self.is_running = False
        
        # Configuration
        self.host = DashboardConfig.HOST
        self.port = DashboardConfig.PORT
        self.state_path = LoggingConfig.STATE_PATH
        
        # Dashboard process reference
        self._dashboard_process: Optional[object] = None
        self._is_running = False
        
        # Setup logger
        from .log_manager import Logger
        self.logger = Logger(name="Dashboard", tag="[DASH]", logfile="LOGS/dashboard.log", console=False).get_logger()
    
    def _is_port_open(self, host: str, port: int) -> bool:
        """
        Check if a port is open and accepting connections.
        
        Args:
            host: Host address to check
            port: Port number to check
            
        Returns:
            True if port is open, False otherwise
        """
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(0.25)
                s.connect((host, port))
                return True
        except OSError:
            return False
    
    async def _wait_for_port(self, host: str, port: int, timeout: float = 10.0) -> bool:
        """
        Wait for a port to become available.
        
        Args:
            host: Host address to wait for
            port: Port number to wait for
            timeout: Maximum time to wait in seconds
            
        Returns:
            True if port became available, False if timeout exceeded
        """
        loop = asyncio.get_event_loop()
        deadline = loop.time() + timeout
        
        while loop.time() < deadline:
            if self._is_port_open(host, port):
                return True
            await asyncio.sleep(0.2)
        
        return False
    
    async def start_dashboard(self) -> Optional[object]:
        """
        Start the dashboard application.
        
        Returns:
            Process object if successful, None otherwise
        """
        if not self.use_flask:
            return None
        
        try:
            # Import here to avoid circular imports
            from API.dashboard_api import run_flask_in_new_terminal
            
            # Start Flask in new terminal
            self._dashboard_process = run_flask_in_new_terminal(
                host=self.host,
                port=self.port,
                log_path=self.log_file
            )
            
            # Wait for port to become available
            port_available = await self._wait_for_port(self.host, self.port, timeout=10.0)
            
            if not port_available:
                self.logger.error(f"Dashboard failed to start on port {self.host}:{self.port}. Check {self.log_file}")
                return None
            
            self._is_running = True
            self.logger.info(f"Dashboard started successfully on {self.get_url()}")
            
            # Try to open browser
            try:
                webbrowser.open_new_tab(self.get_url())
            except Exception as e:
                self.logger.warning(f"Could not open browser: {e}")
            
            return self._dashboard_process
            
        except Exception as e:
            self.logger.error(f"Error starting dashboard: {e}")
            return None
    
    async def stop_dashboard(self) -> bool:
        """
        Stop the dashboard application.
        
        Returns:
            True if stopped successfully, False otherwise
        """
        if not self._dashboard_process or not self._is_running:
            return True
        
        try:
            # Import here to avoid circular imports
            from API.dashboard_api import stop_flask
            
            stop_flask(self._dashboard_process)
            self._is_running = False
            self._dashboard_process = None
            self.logger.info("Dashboard stopped successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Error stopping dashboard: {e}")
            return False
    
    def is_running(self) -> bool:
        """
        Check if dashboard is currently running.
        
        Returns:
            True if dashboard is running, False otherwise
        """
        if not self._is_running:
            return False
        
        # Double-check by testing the port
        return self._is_port_open(self.host, self.port)
    
    def get_url(self) -> str:
        """
        Get dashboard URL.
        
        Returns:
            Dashboard URL string
        """
        return f"http://{self.host}:{self.port}"
    
    def get_status(self) -> Dict[str, Any]:
        """
        Get current dashboard status.
        
        Returns:
            Dictionary with status information
        """
        return {
            "running": self.is_running(),
            "host": self.host,
            "port": self.port,
            "url": self.get_url(),
            "use_flask": self.use_flask,
            "log_file": self.log_file
        }
    
    async def write_state_fallback(self, state_path: Optional[str] = None) -> bool:
        """
        Write fallback state file for dashboard.
        
        Args:
            state_path: Path to state file (defaults to configured path)
            
        Returns:
            True if successful, False otherwise
        """
        if state_path is None:
            state_path = self.state_path
        
        try:
            data = {
                "balance": {"total": None, "currency": "USDT"},
                "positions": [],
                "updated": pd.Timestamp.utcnow().isoformat()
            }
            
            import json
            with open(state_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error writing fallback state: {e}")
            return False
    
    async def update_state(self, symbol: str, state_path: Optional[str] = None) -> bool:
        """
        Update dashboard state file.
        
        Args:
            symbol: Trading symbol
            state_path: Path to state file (defaults to configured path)
            
        Returns:
            True if successful, False otherwise
        """
        if state_path is None:
            state_path = self.state_path
        
        try:
            # Try to update state through bot if available
            # This would typically be called with a bot instance
            return True
            
        except Exception as e:
            self.logger.error(f"Error updating state: {e}")
            # Fallback to writing basic state
            return await self.write_state_fallback(state_path)
    
    async def health_check(self) -> Dict[str, Any]:
        """
        Perform health check on dashboard.
        
        Returns:
            Dictionary with health check results
        """
        port_open = self._is_port_open(self.host, self.port)
        running = self.is_running()
        
        return {
            "port_open": port_open,
            "dashboard_running": running,
            "status": "healthy" if running else "unhealthy",
            "timestamp": pd.Timestamp.utcnow().isoformat()
        }


# Utility functions for backward compatibility and standalone use
def is_port_open(host: str, port: int) -> bool:
    """
    Check if a port is open (standalone utility function).
    
    Args:
        host: Host address to check
        port: Port number to check
        
    Returns:
        True if port is open, False otherwise
    """
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(0.25)
            s.connect((host, port))
            return True
    except OSError:
        return False


async def wait_for_port(host: str, port: int, timeout: float = 10.0) -> bool:
    """
    Wait for a port to become available (standalone utility function).
    
    Args:
        host: Host address to wait for
        port: Port number to wait for
        timeout: Maximum time to wait in seconds
        
    Returns:
        True if port became available, False if timeout exceeded
    """
    loop = asyncio.get_running_loop()
    deadline = loop.time() + timeout
    
    while loop.time() < deadline:
        if is_port_open(host, port):
            return True
        await asyncio.sleep(0.2)
    
    return False


async def write_state_fallback(state_path: str) -> bool:
    """
    Write fallback state file (standalone utility function).
    
    Args:
        state_path: Path to state file
        
    Returns:
        True if successful, False otherwise
    """
    try:
        data = {
            "balance": {"total": None, "currency": "USDT"},
            "positions": [],
            "updated": pd.Timestamp.utcnow().isoformat()
        }
        
        import json
        with open(state_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        return True
        
    except Exception as e:
        logging.error(f"Error writing fallback state: {e}")
        return False


def get_dashboard_manager() -> DashboardManager:
    """
    Get default DashboardManager instance.
    
    Returns:
        DashboardManager instance with default configuration
    """
    return DashboardManager()
