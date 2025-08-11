"""
Dashboard and utilities management system for the Trade Project.

This module provides centralized management of dashboard operations and utility functions:
- Dashboard startup/shutdown management
- Port checking and waiting utilities
- State management and fallback operations
- Browser integration utilities

Usage:
    from CORE.dashboard_manager import DashboardManager
    
    # Initialize dashboard manager
    dashboard = DashboardManager()
    
    # Start dashboard
    process = await dashboard.start_dashboard()
    
    # Check if dashboard is running
    if dashboard.is_running():
        print("Dashboard is active")
    
    # Stop dashboard
    await dashboard.stop_dashboard()
"""

import asyncio
import os
import socket
import webbrowser
from typing import Optional, Dict, Any
import pandas as pd

from .config import DashboardConfig, PathConfig, LoggingConfig


class DashboardManager:
    """
    Centralized dashboard management system.
    
    Handles dashboard startup, shutdown, port management, and utility operations.
    """
    
    def __init__(self):
        """Initialize DashboardManager with configuration."""
        self.host = DashboardConfig.HOST
        self.port = DashboardConfig.PORT
        self.use_flask = DashboardConfig.USE_FLASK
        self.log_file = LoggingConfig.DASHBOARD_LOG_FILE
        self.state_path = PathConfig.STATE_PATH
        
        # Dashboard process reference
        self._dashboard_process: Optional[object] = None
        self._is_running = False
    
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
                print(f"Dashboard failed to start on port {self.host}:{self.port}. Check {self.log_file}")
                return None
            
            self._is_running = True
            print(f"Dashboard started successfully on {self.get_url()}")
            
            # Try to open browser
            try:
                webbrowser.open_new_tab(self.get_url())
            except Exception as e:
                print(f"Warning: Could not open browser: {e}")
            
            return self._dashboard_process
            
        except Exception as e:
            print(f"Error starting dashboard: {e}")
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
            print("Dashboard stopped successfully")
            return True
            
        except Exception as e:
            print(f"Error stopping dashboard: {e}")
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
            print(f"Error writing fallback state: {e}")
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
            print(f"Error updating state: {e}")
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
        print(f"Error writing fallback state: {e}")
        return False


def get_dashboard_manager() -> DashboardManager:
    """
    Get default DashboardManager instance.
    
    Returns:
        DashboardManager instance with default configuration
    """
    return DashboardManager()
