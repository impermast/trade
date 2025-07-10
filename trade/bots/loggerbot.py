# trade/bots/loggerbot.py

import logging
import os
from typing import Optional

class Logger:
    """
    Logger class for consistent logging across the application.
    
    This class sets up logging with multiple handlers:
    - Module-specific log file
    - General log file
    - Optional console output
    """
    
    def __init__(self, name: str = "ALL", tag: str = "[ALL]", 
                 logfile: str = "LOGS/general.log", console: bool = False) -> None:
        """
        Initialize the Logger with specified configuration.
        
        Args:
            name: Logger name
            tag: Tag to include in log messages
            logfile: Path to the module-specific log file
            console: Whether to log to console
        """
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.INFO)

        formatter = logging.Formatter(f"%(asctime)s {tag} [%(levelname)s] %(message)s")

        if self.logger.hasHandlers():
            self.logger.handlers.clear()

        general_log = "LOGS/general.log"
        os.makedirs(os.path.dirname(logfile), exist_ok=True)
        os.makedirs(os.path.dirname(general_log), exist_ok=True)

        # Module-specific handler
        module_handler = logging.FileHandler(logfile, mode="a", encoding="utf-8")
        module_handler.setFormatter(formatter)
        self.logger.addHandler(module_handler)

        # General log handler
        general_handler = logging.FileHandler(general_log, mode="a", encoding="utf-8")
        general_handler.setFormatter(formatter)
        self.logger.addHandler(general_handler)

        # Console handler (optional)
        if console:
            stream_handler = logging.StreamHandler()
            stream_handler.setFormatter(formatter)
            self.logger.addHandler(stream_handler)

    def get_logger(self) -> logging.Logger:
        """
        Get the configured logger instance.
        
        Returns:
            The configured logger instance
        """
        return self.logger