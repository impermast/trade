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
from .config import LoggingConfig, Config


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
            max_age_hours: Maximum age of log files in hours (defaults to LoggingConfig.CLEAN_LOGS_MAX_AGE_HOURS)
            cleanup_interval_hours: How often to run cleanup in hours
        """
        self.logs_dir = logs_dir or Config.LOGS_DIR
        self.max_age_hours = max_age_hours or LoggingConfig.CLEAN_LOGS_MAX_AGE_HOURS
        
        # Ensure logs directory exists
        os.makedirs(self.logs_dir, exist_ok=True)
    
    def _parse_log_timestamp(self, line: str) -> Optional[datetime]:
        """
        Parse timestamp from the beginning of a log line.
        
        Format: 'YYYY-MM-DD HH:MM:SS,ffffff'
        Returns naive datetime (local time) or None if parsing fails.
        
        Args:
            line: Log line to parse
            
        Returns:
            Parsed datetime or None
        """
        match = self._TS_REGEX.match(line)
        if not match:
            return None
        
        timestamp_str = match.group("ts")
        try:
            return datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S,%f")
        except ValueError:
            return None
    
    def _iter_trimmed_lines(self, lines: Iterable[str], cutoff_dt: datetime) -> Iterable[str]:
        """
        Filter log lines keeping only records (and their tails) with timestamp >= cutoff_dt.
        
        'Tail' refers to lines without timestamp that follow a saved record (e.g., traceback).
        
        Args:
            lines: Iterable of log lines
            cutoff_dt: Cutoff datetime for filtering
            
        Yields:
            Filtered log lines
        """
        keep_block = False
        for line in lines:
            dt = self._parse_log_timestamp(line)
            if dt is not None:
                keep_block = dt >= cutoff_dt
            if keep_block:
                yield line
    
    def _trim_log_file(self, file_path: str, cutoff_dt: datetime) -> Tuple[int, int]:
        """
        Trim a single .log file by timestamp.
        
        Uses streaming filtering without loading entire file into memory.
        Performs atomic file replacement for safety.
        
        Args:
            file_path: Path to the log file
            cutoff_dt: Cutoff datetime for filtering
            
        Returns:
            Tuple of (bytes_before, bytes_after)
        """
        try:
            # Read source file and write filtered content to temporary file
            with open(file_path, "r", encoding="utf-8", errors="replace") as src:
                tmp_path = file_path + ".tmp~"
                with open(tmp_path, "w", encoding="utf-8") as dst:
                    for out_line in self._iter_trimmed_lines(src, cutoff_dt):
                        dst.write(out_line)
            
            # Get file sizes
            before_size = os.path.getsize(file_path)
            after_size = os.path.getsize(tmp_path)
            
            # Atomic replacement
            os.replace(tmp_path, file_path)
            
            return before_size, after_size
            
        except FileNotFoundError:
            return (0, 0)
        except IsADirectoryError:
            return (0, 0)
        except Exception:
            # In case of error, don't touch the original file
            try:
                if os.path.exists(file_path + ".tmp~"):
                    os.remove(file_path + ".tmp~")
            except Exception:
                pass
            return (0, 0)
    
    def clean_old_logs(self) -> Dict[str, int]:
        """
        Clean old log files based on timestamp.
        
        Processes all *.log files in the logs directory, keeping only records
        from the last max_age_hours.
        
        Returns:
            Dictionary with cleanup statistics:
            - processed: Number of files processed
            - changed: Number of files modified
            - saved_bytes: Total bytes saved
        """
        if self.max_age_hours <= 0:
            return {"processed": 0, "changed": 0, "saved_bytes": 0}
        
        # Calculate cutoff time
        now_local = datetime.now()  # Log format is timezone-naive, assume local time
        cutoff = now_local - timedelta(hours=self.max_age_hours)
        
        processed = 0
        changed = 0
        saved_bytes = 0
        
        try:
            for entry in os.scandir(self.logs_dir):
                if not entry.is_file() or not entry.name.endswith(".log"):
                    continue
                
                processed += 1
                before_size, after_size = self._trim_log_file(entry.path, cutoff)
                
                if after_size > 0 and before_size >= after_size:
                    if before_size != after_size:
                        changed += 1
                        saved_bytes += (before_size - after_size)
                # If after_size == 0, file became empty, this is also a change
                elif after_size == 0 and before_size > 0:
                    changed += 1
                    saved_bytes += before_size
                    
        except FileNotFoundError:
            pass
        
        return {
            "processed": processed,
            "changed": changed,
            "saved_bytes": saved_bytes
        }
    
    def get_log_files(self) -> list[str]:
        """
        Get list of all log files in the logs directory.
        
        Returns:
            List of log file paths
        """
        log_files = []
        try:
            for entry in os.scandir(self.logs_dir):
                if entry.is_file() and entry.name.endswith(".log"):
                    log_files.append(entry.path)
        except FileNotFoundError:
            pass
        
        return log_files
    
    def get_log_stats(self) -> Dict[str, any]:
        """
        Get statistics about log files.
        
        Returns:
            Dictionary with log statistics:
            - total_files: Total number of log files
            - total_size: Total size of all log files in bytes
            - oldest_file: Oldest log file modification time
            - newest_file: Newest log file modification time
        """
        log_files = self.get_log_files()
        
        if not log_files:
            return {
                "total_files": 0,
                "total_size": 0,
                "oldest_file": None,
                "newest_file": None
            }
        
        total_size = 0
        oldest_time = None
        newest_time = None
        
        for file_path in log_files:
            try:
                stat = os.stat(file_path)
                total_size += stat.st_size
                
                mtime = datetime.fromtimestamp(stat.st_mtime)
                if oldest_time is None or mtime < oldest_time:
                    oldest_time = mtime
                if newest_time is None or mtime > newest_time:
                    newest_time = mtime
                    
            except OSError:
                continue
        
        return {
            "total_files": len(log_files),
            "total_size": total_size,
            "oldest_file": oldest_time,
            "newest_file": newest_time
        }
    
    def rotate_logs(self, max_size_mb: int = 100) -> Dict[str, int]:
        """
        Rotate log files that exceed maximum size.
        
        Args:
            max_size_mb: Maximum size in MB before rotation
            
        Returns:
            Dictionary with rotation statistics
        """
        max_size_bytes = max_size_mb * 1024 * 1024
        rotated = 0
        
        for file_path in self.get_log_files():
            try:
                if os.path.getsize(file_path) > max_size_bytes:
                    # Create backup filename with timestamp
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    backup_path = f"{file_path}.{timestamp}"
                    os.rename(file_path, backup_path)
                    rotated += 1
            except OSError:
                continue
        
        return {"rotated": rotated}
    
    def cleanup_temp_files(self) -> int:
        """
        Clean up temporary files left by failed operations.
        
        Returns:
            Number of temporary files removed
        """
        cleaned = 0
        
        try:
            for entry in os.scandir(self.logs_dir):
                if entry.is_file() and entry.name.endswith(".tmp~"):
                    try:
                        os.remove(entry.path)
                        cleaned += 1
                    except OSError:
                        pass
        except FileNotFoundError:
            pass
        
        return cleaned


# Convenience functions for backward compatibility
def clean_logs_by_age(logs_dir: str, max_age_hours: int) -> Dict[str, int]:
    """
    Convenience function for cleaning logs by age.
    
    Args:
        logs_dir: Directory containing log files
        max_age_hours: Maximum age of logs to keep
        
    Returns:
        Dictionary with cleanup statistics
    """
    log_manager = LogManager(logs_dir, max_age_hours)
    return log_manager.clean_old_logs()


def get_log_manager() -> LogManager:
    """
    Get default LogManager instance using configuration.
    
    Returns:
        LogManager instance with default settings
    """
    return LogManager()


def create_logger(name="ALL", tag="[ALL]", logfile="LOGS/general.log", console=False) -> Logger:
    """
    Create a new logger instance.
    
    Args:
        name: Name of the logger
        tag: Tag to prepend to log messages
        logfile: Path to the log file for this logger
        console: Whether to output to console
        
    Returns:
        Logger instance
    """
    return Logger(name, tag, logfile, console)
