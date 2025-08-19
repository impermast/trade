"""
Log management system for the Trade Project.

This module provides centralized logging functionality with automatic log rotation,
cleanup, and formatting for different components of the trading system.
It combines the functionality of both loggerbot and log_manager.
"""

import os
import logging
import logging.handlers
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, Any, Iterable, Tuple
import json
import shutil
import re

# Import configuration
from .config import Config


class Logger:
    """
    Logger class for creating and configuring loggers with multiple handlers.
    
    This class provides a simple interface for creating loggers with file and console output,
    combining the functionality from the original loggerbot.
    """
    
    def __init__(self, name="ALL", tag="[ALL]", logfile="LOGS/general.log", console=False):
        """
        Initialize a new logger.
        
        Args:
            name: Name of the logger
            tag: Tag to prepend to log messages
            logfile: Path to the log file for this logger
            console: Whether to output to console
        """
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.INFO)

        formatter = logging.Formatter(f"%(asctime)s {tag} [%(levelname)s] %(message)s")

        if self.logger.hasHandlers():
            self.logger.handlers.clear()

        general_log = "LOGS/general.log"
        os.makedirs(os.path.dirname(logfile), exist_ok=True)
        os.makedirs(os.path.dirname(general_log), exist_ok=True)

        # Handler для модуля
        module_handler = logging.FileHandler(logfile, mode="a", encoding="utf-8")
        module_handler.setFormatter(formatter)
        self.logger.addHandler(module_handler)

        # Handler для общего лога
        general_handler = logging.FileHandler(general_log, mode="a", encoding="utf-8")
        general_handler.setFormatter(formatter)
        self.logger.addHandler(general_handler)

        # Handler для консоли
        if console:
            stream_handler = logging.StreamHandler()
            stream_handler.setFormatter(formatter)
            self.logger.addHandler(stream_handler)

    def get_logger(self):
        """Get the configured logger instance."""
        return self.logger


class LogManager:
    """
    Manages logging for the trading system.
    
    This class provides centralized logging functionality with automatic log rotation,
    cleanup, and formatting for different components of the trading system.
    """
    
    # Regex pattern for parsing log timestamps
    _TS_REGEX = re.compile(r"^(?P<ts>\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d+)\b")
    
    def __init__(self, 
                 logs_dir: str = None,
                 max_age_hours: int = None,
                 cleanup_interval_hours: int = 1):
        """
        Initialize the LogManager.
        
        Args:
            logs_dir: Directory containing log files (defaults to Config.LOGS_DIR)
            max_age_hours: Maximum age of log files in hours (defaults to Config.LOGGING.CLEAN_LOGS_MAX_AGE_HOURS)
            cleanup_interval_hours: How often to run cleanup in hours
        """
        self.logs_dir = logs_dir or Config.LOGS_DIR
        self.max_age_hours = max_age_hours or Config.LOGGING.CLEAN_LOGS_MAX_AGE_HOURS
        
        # Ensure logs directory exists
        os.makedirs(self.logs_dir, exist_ok=True)
        
        # Setup logger
        self.logger = logging.getLogger(__name__)
        
        # Set cleanup interval
        self.cleanup_interval_hours = cleanup_interval_hours
        
        # Last cleanup time
        self.last_cleanup = datetime.now()
        
        self.logger.info(f"LogManager initialized with logs_dir={self.logs_dir}, max_age_hours={self.max_age_hours}")
    
    def clean_old_logs(self) -> Dict[str, Any]:
        """
        Clean old log files based on age.
        
        Returns:
            Dictionary with cleanup statistics
        """
        try:
            # Check if cleanup is needed
            if (datetime.now() - self.last_cleanup).total_seconds() < self.cleanup_interval_hours * 3600:
                return {"processed": 0, "changed": 0, "saved_bytes": 0}
            
            self.last_cleanup = datetime.now()
            
            # Calculate cutoff time
            cutoff_time = datetime.now() - timedelta(hours=self.max_age_hours)
            
            processed = 0
            changed = 0
            saved_bytes = 0
            
            # Process each log file
            for log_file in self._get_log_files():
                file_stats = self._process_log_file(log_file, cutoff_time)
                processed += 1
                
                if file_stats["changed"]:
                    changed += 1
                    saved_bytes += file_stats["saved_bytes"]
            
            self.logger.info(f"Log cleanup completed: processed={processed}, changed={changed}, saved_bytes={saved_bytes}")
            
            return {
                "processed": processed,
                "changed": changed,
                "saved_bytes": saved_bytes
            }
            
        except Exception as e:
            self.logger.error(f"Error during log cleanup: {e}")
            return {"processed": 0, "changed": 0, "saved_bytes": 0}
    
    def _get_log_files(self) -> Iterable[Path]:
        """Get all log files in the logs directory."""
        logs_path = Path(self.logs_dir)
        if not logs_path.exists():
            return []
        
        return logs_path.glob("*.log")
    
    def _process_log_file(self, log_file: Path, cutoff_time: datetime) -> Dict[str, Any]:
        """
        Process a single log file for cleanup.
        
        Args:
            log_file: Path to the log file
            cutoff_time: Time cutoff for log entries
            
        Returns:
            Dictionary with processing results
        """
        try:
            if not log_file.exists():
                return {"changed": False, "saved_bytes": 0}
            
            # Read file content
            with open(log_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            original_size = len(lines)
            original_bytes = log_file.stat().st_size
            
            # Filter lines by timestamp
            filtered_lines = []
            for line in lines:
                timestamp = self._extract_timestamp(line)
                if timestamp and timestamp >= cutoff_time:
                    filtered_lines.append(line)
            
            # If no changes needed, return early
            if len(filtered_lines) == len(lines):
                return {"changed": False, "saved_bytes": 0}
            
            # Write filtered content back to file
            with open(log_file, 'w', encoding='utf-8') as f:
                f.writelines(filtered_lines)
            
            # Calculate saved bytes
            new_bytes = log_file.stat().st_size
            saved_bytes = original_bytes - new_bytes
            
            self.logger.debug(f"Cleaned {log_file.name}: removed {original_size - len(filtered_lines)} lines, saved {saved_bytes} bytes")
            
            return {
                "changed": True,
                "saved_bytes": saved_bytes
            }
            
        except Exception as e:
            self.logger.error(f"Error processing log file {log_file}: {e}")
            return {"changed": False, "saved_bytes": 0}
    
    def _extract_timestamp(self, line: str) -> Optional[datetime]:
        """
        Extract timestamp from a log line.
        
        Args:
            line: Log line to extract timestamp from
            
        Returns:
            Datetime object if timestamp found, None otherwise
        """
        match = self._TS_REGEX.match(line)
        if not match:
            return None
        
        try:
            timestamp_str = match.group('ts')
            return datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S,%f')
        except ValueError:
            return None
    
    def get_log_stats(self) -> Dict[str, Any]:
        """
        Get statistics about log files.
        
        Returns:
            Dictionary with log statistics
        """
        try:
            logs_path = Path(self.logs_dir)
            if not logs_path.exists():
                return {"total_files": 0, "total_size": 0, "oldest_file": None, "newest_file": None}
            
            log_files = list(logs_path.glob("*.log"))
            
            if not log_files:
                return {"total_files": 0, "total_size": 0, "oldest_file": None, "newest_file": None}
            
            # Calculate statistics
            total_size = sum(f.stat().st_size for f in log_files)
            file_times = [(f, f.stat().st_mtime) for f in log_files]
            
            oldest_file = min(file_times, key=lambda x: x[1])[0]
            newest_file = max(file_times, key=lambda x: x[1])[0]
            
            return {
                "total_files": len(log_files),
                "total_size": total_size,
                "oldest_file": oldest_file.name,
                "newest_file": newest_file.name,
                "max_age_hours": self.max_age_hours
            }
            
        except Exception as e:
            self.logger.error(f"Error getting log stats: {e}")
            return {"total_files": 0, "total_size": 0, "oldest_file": None, "newest_file": None}


# Utility functions for backward compatibility
def clean_logs_by_age(logs_dir: str = None, max_age_hours: int = None) -> Dict[str, Any]:
    """
    Clean old log files by age (utility function for backward compatibility).
    
    Args:
        logs_dir: Directory containing log files
        max_age_hours: Maximum age of log files in hours
        
    Returns:
        Dictionary with cleanup statistics
    """
    log_manager = LogManager(logs_dir=logs_dir, max_age_hours=max_age_hours)
    return log_manager.clean_old_logs()
