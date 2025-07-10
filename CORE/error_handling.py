# CORE/error_handling.py

import logging
import traceback
import functools
import sys
from typing import Any, Callable, Dict, Optional, Type, Union, TypeVar, cast

from BOTS.loggerbot import Logger

# Type variables for function decorators
F = TypeVar('F', bound=Callable[..., Any])
R = TypeVar('R')  # Return type

class TradeError(Exception):
    """Base exception class for all trade-related errors."""
    
    def __init__(self, message: str, error_code: Optional[str] = None, 
                original_error: Optional[Exception] = None):
        """
        Initialize a TradeError.
        
        Args:
            message: Error message
            error_code: Optional error code for categorization
            original_error: Original exception that caused this error
        """
        self.message = message
        self.error_code = error_code
        self.original_error = original_error
        
        # Include original error info in the message if available
        if original_error:
            message = f"{message} - Original error: {str(original_error)}"
        
        super().__init__(message)


class APIError(TradeError):
    """Exception raised for errors in API operations."""
    pass


class DataError(TradeError):
    """Exception raised for errors in data handling."""
    pass


class ConfigError(TradeError):
    """Exception raised for errors in configuration."""
    pass


class StrategyError(TradeError):
    """Exception raised for errors in trading strategies."""
    pass


class ValidationError(TradeError):
    """Exception raised for validation errors."""
    pass


def get_error_logger(name: str = "error_handler", 
                    tag: str = "[ERROR]", 
                    logfile: Optional[str] = "LOGS/errors.log", 
                    console: bool = True) -> logging.Logger:
    """
    Get a logger configured for error handling.
    
    Args:
        name: Logger name
        tag: Tag to prepend to log messages
        logfile: Path to log file (None for no file logging)
        console: Whether to log to console
        
    Returns:
        Configured logger instance
    """
    return Logger(name=name, tag=tag, logfile=logfile, console=console).get_logger()


# Default error logger
DEFAULT_ERROR_LOGGER = get_error_logger()


def log_error(error: Exception, logger: Optional[logging.Logger] = None, 
             level: int = logging.ERROR, include_traceback: bool = True,
             additional_info: Optional[Dict[str, Any]] = None) -> None:
    """
    Log an error with consistent formatting.
    
    Args:
        error: The exception to log
        logger: Logger to use (defaults to DEFAULT_ERROR_LOGGER)
        level: Logging level (default: ERROR)
        include_traceback: Whether to include the traceback in the log
        additional_info: Additional information to include in the log
    """
    logger = logger or DEFAULT_ERROR_LOGGER
    
    # Format the error message
    error_type = type(error).__name__
    error_msg = str(error)
    
    # Include additional info if provided
    info_str = ""
    if additional_info:
        info_str = " - " + ", ".join(f"{k}={v}" for k, v in additional_info.items())
    
    # Log the basic error info
    logger.log(level, f"{error_type}: {error_msg}{info_str}")
    
    # Log the traceback if requested
    if include_traceback:
        tb_str = "".join(traceback.format_exception(type(error), error, error.__traceback__))
        logger.log(level, f"Traceback:\n{tb_str}")
    
    # Log original error if it's a TradeError with an original_error
    if isinstance(error, TradeError) and error.original_error:
        logger.log(level, f"Original error: {type(error.original_error).__name__}: {str(error.original_error)}")


def handle_error(error: Exception, 
                default_return: Optional[Any] = None,
                logger: Optional[logging.Logger] = None,
                level: int = logging.ERROR,
                include_traceback: bool = True,
                additional_info: Optional[Dict[str, Any]] = None,
                reraise: bool = False,
                reraise_as: Optional[Type[Exception]] = None) -> Any:
    """
    Handle an error with consistent logging and optional reraising.
    
    Args:
        error: The exception to handle
        default_return: Value to return if not reraising
        logger: Logger to use (defaults to DEFAULT_ERROR_LOGGER)
        level: Logging level (default: ERROR)
        include_traceback: Whether to include the traceback in the log
        additional_info: Additional information to include in the log
        reraise: Whether to reraise the exception
        reraise_as: Exception type to reraise as (None to use original)
        
    Returns:
        default_return if not reraising
        
    Raises:
        The original exception or a new exception of type reraise_as
    """
    # Log the error
    log_error(error, logger, level, include_traceback, additional_info)
    
    # Reraise if requested
    if reraise:
        if reraise_as:
            if issubclass(reraise_as, TradeError):
                raise reraise_as(str(error), original_error=error)
            else:
                raise reraise_as(str(error))
        else:
            raise
    
    # Return the default value if not reraising
    return default_return


def with_error_handling(default_return: Optional[Any] = None,
                       logger: Optional[logging.Logger] = None,
                       level: int = logging.ERROR,
                       include_traceback: bool = True,
                       reraise: bool = False,
                       reraise_as: Optional[Type[Exception]] = None) -> Callable[[F], F]:
    """
    Decorator for handling errors in functions.
    
    Args:
        default_return: Value to return on error if not reraising
        logger: Logger to use (defaults to DEFAULT_ERROR_LOGGER)
        level: Logging level (default: ERROR)
        include_traceback: Whether to include the traceback in the log
        reraise: Whether to reraise the exception
        reraise_as: Exception type to reraise as (None to use original)
        
    Returns:
        Decorated function with error handling
    """
    def decorator(func: F) -> F:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            try:
                return func(*args, **kwargs)
            except Exception as e:
                # Get function info for logging
                additional_info = {
                    "function": func.__name__,
                    "module": func.__module__
                }
                
                # Handle the error
                return handle_error(
                    error=e,
                    default_return=default_return,
                    logger=logger,
                    level=level,
                    include_traceback=include_traceback,
                    additional_info=additional_info,
                    reraise=reraise,
                    reraise_as=reraise_as
                )
        
        return cast(F, wrapper)
    
    return decorator


def validate_input(validation_func: Callable[..., bool], 
                  error_message: str = "Validation failed",
                  error_type: Type[Exception] = ValidationError) -> Callable[[F], F]:
    """
    Decorator for validating function inputs.
    
    Args:
        validation_func: Function that takes the same arguments as the decorated function
                        and returns True if validation passes, False otherwise
        error_message: Error message to use if validation fails
        error_type: Exception type to raise if validation fails
        
    Returns:
        Decorated function with input validation
    """
    def decorator(func: F) -> F:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            if not validation_func(*args, **kwargs):
                raise error_type(error_message)
            return func(*args, **kwargs)
        
        return cast(F, wrapper)
    
    return decorator


def safe_execute(func: Callable[..., R], 
                *args: Any, 
                default_return: Optional[R] = None, 
                **kwargs: Any) -> Optional[R]:
    """
    Safely execute a function, catching any exceptions.
    
    Args:
        func: Function to execute
        *args: Arguments to pass to the function
        default_return: Value to return if an exception occurs
        **kwargs: Keyword arguments to pass to the function
        
    Returns:
        Function result or default_return if an exception occurs
    """
    try:
        return func(*args, **kwargs)
    except Exception as e:
        log_error(e)
        return default_return