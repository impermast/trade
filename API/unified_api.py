# API/unified_api.py

import time
import random
from typing import Dict, Any, Optional, List, Union, Callable
import pandas as pd
from functools import wraps
import logging

from API.birza_api import BirzaAPI
from API.bybit_api import BybitAPI
from API.binance_api import BinanceAPI
from API.coinbase_api import CoinbaseAPI
from BOTS.loggerbot import Logger

def retry_with_backoff(max_retries: int = 3, initial_backoff: float = 1.0, 
                      max_backoff: float = 60.0, backoff_factor: float = 2.0):
    """
    Decorator for retrying API calls with exponential backoff.

    Args:
        max_retries: Maximum number of retry attempts
        initial_backoff: Initial backoff time in seconds
        max_backoff: Maximum backoff time in seconds
        backoff_factor: Factor to increase backoff time with each retry

    Returns:
        Decorated function with retry logic
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            retries = 0
            backoff = initial_backoff

            while True:
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    retries += 1
                    if retries > max_retries:
                        # If we've exceeded max retries, re-raise the exception
                        raise

                    # Add some jitter to avoid thundering herd problem
                    jitter = random.uniform(0.8, 1.2)
                    sleep_time = min(backoff * jitter, max_backoff)

                    # Get the instance (self) to access its logger
                    instance = args[0] if args else None
                    if hasattr(instance, 'logger'):
                        instance.logger.warning(
                            f"API call failed: {e}. Retrying in {sleep_time:.2f}s "
                            f"(attempt {retries}/{max_retries})"
                        )

                    time.sleep(sleep_time)
                    backoff = min(backoff * backoff_factor, max_backoff)

        return wrapper
    return decorator

def rate_limit(calls_per_second: float = 1.0):
    """
    Decorator for rate limiting API calls.

    Args:
        calls_per_second: Maximum number of calls allowed per second

    Returns:
        Decorated function with rate limiting
    """
    min_interval = 1.0 / calls_per_second
    last_call_time = {}

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Use function name as key for tracking last call time
            key = func.__name__

            # Calculate time since last call
            current_time = time.time()
            if key in last_call_time:
                elapsed = current_time - last_call_time[key]
                sleep_time = max(0, min_interval - elapsed)

                if sleep_time > 0:
                    # Get the instance (self) to access its logger
                    instance = args[0] if args else None
                    if hasattr(instance, 'logger'):
                        instance.logger.debug(f"Rate limiting: sleeping for {sleep_time:.4f}s")
                    time.sleep(sleep_time)

            # Update last call time
            last_call_time[key] = time.time()

            # Call the original function
            return func(*args, **kwargs)

        return wrapper
    return decorator

class UnifiedAPI:
    """
    Unified API interface for all supported cryptocurrency exchanges.

    This class provides a consistent interface for interacting with different
    cryptocurrency exchanges, abstracting away the differences between them.
    It also implements rate limiting and retry mechanisms for API calls.

    Attributes:
        exchange_api: The underlying exchange-specific API client
        logger: Logger instance for logging API operations
    """

    # Mapping of exchange names to their API classes
    EXCHANGE_APIS = {
        "bybit": BybitAPI,
        "binance": BinanceAPI,
        "coinbase": CoinbaseAPI,
    }

    def __init__(self, exchange: str, api_key: Optional[str] = None, 
                api_secret: Optional[str] = None, testnet: bool = True):
        """
        Initialize the unified API client.

        Args:
            exchange: Name of the exchange to use (e.g., "bybit", "binance")
            api_key: API key for authentication (None for public API only)
            api_secret: API secret for authentication (None for public API only)
            testnet: Whether to use the testnet (sandbox) environment

        Raises:
            ValueError: If the specified exchange is not supported
        """
        self.logger = Logger(
            name=f"UnifiedAPI_{exchange}", 
            tag="[UNIFIED_API]", 
            logfile=f"LOGS/unified_api_{exchange}.log", 
            console=True
        ).get_logger()

        if exchange.lower() not in self.EXCHANGE_APIS:
            supported = ", ".join(self.EXCHANGE_APIS.keys())
            raise ValueError(
                f"Exchange '{exchange}' is not supported. "
                f"Supported exchanges: {supported}"
            )

        # Initialize the exchange-specific API client
        api_class = self.EXCHANGE_APIS[exchange.lower()]
        self.exchange_api = api_class(api_key=api_key, api_secret=api_secret, testnet=testnet)
        self.exchange_name = exchange.lower()

        self.logger.info(f"Initialized UnifiedAPI for {exchange}")

    @retry_with_backoff()
    @rate_limit(calls_per_second=1.0)
    def get_ohlcv(self, symbol: str, timeframe: str = "1m", limit: int = 100) -> pd.DataFrame:
        """
        Fetch OHLCV (Open, High, Low, Close, Volume) candlestick data.

        Args:
            symbol: Trading pair symbol (e.g., "BTC/USDT")
            timeframe: Candlestick timeframe (e.g., "1m", "5m", "1h", "1d")
            limit: Maximum number of candles to fetch

        Returns:
            DataFrame containing OHLCV data with standardized columns
        """
        self.logger.info(f"Fetching OHLCV data for {symbol}, timeframe={timeframe}, limit={limit}")
        df = self.exchange_api.get_ohlcv(symbol, timeframe, limit)

        # Ensure consistent column names across exchanges
        if not df.empty:
            # Standardize column names if needed
            if 'time' not in df.columns and 'timestamp' in df.columns:
                df.rename(columns={'timestamp': 'time'}, inplace=True)

        return df

    @retry_with_backoff()
    @rate_limit(calls_per_second=0.5)  # More conservative rate limit for orders
    def place_order(self, symbol: str, side: str, qty: float,
                   order_type: str = "market", price: Optional[float] = None) -> Dict[str, Any]:
        """
        Place a trading order on the exchange.

        Args:
            symbol: Trading pair symbol (e.g., "BTC/USDT")
            side: Order side ("buy" or "sell")
            qty: Order quantity
            order_type: Order type ("market", "limit", etc.)
            price: Order price (required for limit orders)

        Returns:
            Order information including order ID and status
        """
        self.logger.info(
            f"Placing {order_type} order: {side.upper()} {qty} {symbol}"
            + (f" @ {price}" if price is not None else "")
        )
        return self.exchange_api.place_order(symbol, side, qty, order_type, price)

    @retry_with_backoff()
    @rate_limit()
    def get_balance(self) -> Dict[str, Any]:
        """
        Fetch account balance information.

        Returns:
            Account balance information for all assets
        """
        self.logger.info("Fetching account balance")
        return self.exchange_api.get_balance()

    @retry_with_backoff()
    @rate_limit()
    def get_positions(self, symbol: str) -> Dict[str, Any]:
        """
        Fetch current positions for a specific symbol.

        Args:
            symbol: Trading pair symbol (e.g., "BTC/USDT")

        Returns:
            Position information including size, entry price, etc.
        """
        self.logger.info(f"Fetching positions for {symbol}")
        return self.exchange_api.get_positions(symbol)

    @retry_with_backoff()
    @rate_limit()
    def get_order_status(self, order_id: str) -> Dict[str, Any]:
        """
        Fetch the status of a specific order.

        Args:
            order_id: Order ID to query

        Returns:
            Order status information
        """
        self.logger.info(f"Fetching status for order {order_id}")
        return self.exchange_api.get_order_status(order_id)

    @retry_with_backoff()
    @rate_limit()
    def download_candels_to_csv(self, symbol: str, start_date: str = "2023-01-01T00:00:00Z", 
                               timeframe: str = "1h", save_folder: str = "DATA") -> pd.DataFrame:
        """
        Download historical candle data and save to CSV.

        Args:
            symbol: Trading pair symbol (e.g., "BTC/USDT")
            start_date: Start date for historical data in ISO format
            timeframe: Candlestick timeframe (e.g., "1m", "5m", "1h", "1d")
            save_folder: Folder to save CSV file (None to not save)

        Returns:
            DataFrame containing the downloaded data
        """
        self.logger.info(f"Downloading historical data for {symbol} from {start_date}")
        return self.exchange_api.download_candels_to_csv(
            symbol, start_date, timeframe, save_folder
        )
