# api/bybit_api.py

import os
import sys
import ccxt
import ccxt.async_support as ccxt_async
import pandas as pd
from typing import Dict, Any, Optional
import asyncio
import ssl

sys.path.append(os.path.abspath("."))

from API.birza_api import BirzaAPI
from CORE.security import Security

class BybitAPI(BirzaAPI):
    """
    API client for the Bybit cryptocurrency exchange.

    This class implements the BirzaAPI interface for the Bybit exchange
    using the ccxt library.
    """

    def __init__(self, api_key: Optional[str] = None, api_secret: Optional[str] = None, 
              password: Optional[str] = None, testnet: bool = True):
        """
        Initialize the Bybit API client.

        Args:
            api_key: API key for authentication (None to load from secure storage)
            api_secret: API secret for authentication (None to load from secure storage)
            password: Password to decrypt API keys from secure storage
            testnet: Whether to use the testnet (sandbox) environment
        """
        super().__init__(name="bybitAPI", log_tag="[API]", log_file="LOGS/bybitAPI.log", console=True)

        # Load API keys from secure storage if not provided directly
        if (api_key is None or api_secret is None):
            try:
                from dotenv import load_dotenv
                load_dotenv()

                import os
                api_key = os.getenv("BYBIT_TOKEN")
                api_secret = os.getenv("BYBIT_SECRET")
            except Exception as e:
                self.logger.error(f"Failed to load API keys from env: {e}")

        # Initialize the ccxt exchange object (synchronous)
        self.exchange = ccxt.bybit({
            'apiKey': api_key,
            'secret': api_secret,
            'enableRateLimit': True,
            'rateLimit': 500,  # Enforce rate limiting (500ms between requests)
            # Enable SSL/TLS for secure communication
            'options': {
                'verify': True,
                'timeout': 30000,
            }
        })

        # Initialize the ccxt async exchange object
        self.async_exchange = ccxt_async.bybit({
            'apiKey': api_key,
            'secret': api_secret,
            'enableRateLimit': True,
            'rateLimit': 500,  # Enforce rate limiting (500ms between requests)
            # Enable SSL/TLS for secure communication
            'options': {
                'verify': True,
                'timeout': 30000,
            }
        })

        # Set sandbox mode if testnet is True
        if testnet:
            self.exchange.set_sandbox_mode(True)
            self.async_exchange.set_sandbox_mode(True)

        try:
            self.logger.info("Initializing connection to Bybit via ccxt...")
            assets = self.get_balance()
            self.logger.info(f"Connection established. Assets: {list(assets.keys())}")
        except Exception as e:
            self.logger.exception(f"Error initializing BybitAPI: {e}")
            raise

    def get_ohlcv(self, symbol: str, timeframe: str = "1m", limit: int = 100) -> pd.DataFrame:
        """
        Fetch OHLCV candlestick data from Bybit.

        Args:
            symbol: Trading pair symbol (e.g., "BTC/USDT")
            timeframe: Candlestick timeframe (e.g., "1m", "5m", "1h", "1d")
            limit: Maximum number of candles to fetch

        Returns:
            DataFrame containing OHLCV data
        """
        # Validate inputs
        if not Security.validate_symbol(symbol):
            self.logger.error(f"Invalid symbol format: {symbol}")
            return pd.DataFrame()

        valid_timeframes = ["1m", "3m", "5m", "15m", "30m", "1h", "2h", "4h", "6h", "12h", "1d", "1w", "1M"]
        if not Security.validate_input(timeframe, allowed_values=valid_timeframes):
            self.logger.error(f"Invalid timeframe: {timeframe}")
            return pd.DataFrame()

        if not Security.validate_input(limit, min_value=1, max_value=1000):
            self.logger.error(f"Invalid limit: {limit}")
            return pd.DataFrame()

        try:
            self.logger.info(f"Fetching OHLCV: symbol={symbol}, timeframe={timeframe}, limit={limit}")
            ohlcv = self.exchange.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit)
            df = pd.DataFrame(ohlcv, columns=["timestamp", "open", "high", "low", "close", "volume"])
            df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
            df.rename(columns={"timestamp": "time"}, inplace=True)
            return df
        except Exception as e:
            return self._handle_error(f"fetching OHLCV for {symbol}", e, pd.DataFrame())

    def place_order(self, symbol: str, side: str, qty: float, 
                   order_type: str = "market", price: Optional[float] = None) -> Dict[str, Any]:
        """
        Place a trading order on Bybit.

        Args:
            symbol: Trading pair symbol (e.g., "BTC/USDT")
            side: Order side ("buy" or "sell")
            qty: Order quantity
            order_type: Order type ("market", "limit", etc.)
            price: Order price (required for limit orders)

        Returns:
            Order information including order ID and status
        """
        # Validate order parameters
        if not Security.validate_order_params(symbol, side, qty, order_type, price):
            error_msg = f"Invalid order parameters: symbol={symbol}, side={side}, qty={qty}, type={order_type}, price={price}"
            self.logger.error(error_msg)
            return {"error": error_msg, "status": "rejected"}

        try:
            # Sanitize inputs
            symbol = Security.sanitize_input(symbol)
            side = Security.sanitize_input(side).lower()

            self.logger.info(f"Creating order: {side.upper()} {qty} {symbol}, type={order_type.upper()}, price={price}")
            params = {}

            if order_type == "market":
                return self.exchange.create_market_order(symbol, side, qty, params)
            elif order_type == "limit":
                if price is None or price <= 0:
                    error_msg = "Price is required for limit orders and must be greater than 0"
                    self.logger.error(error_msg)
                    return {"error": error_msg, "status": "rejected"}
                return self.exchange.create_limit_order(symbol, side, qty, price, params)
            else:
                raise ValueError("Invalid order type")
        except Exception as e:
            return self._handle_error(f"placing {order_type} order for {symbol}", e, {})

    def get_balance(self) -> Dict[str, Any]:
        """
        Fetch account balance information from Bybit.

        Returns:
            Account balance information for all assets
        """
        try:
            balance = self.exchange.fetch_balance()
            return balance['total']
        except Exception as e:
            return self._handle_error("fetching balance", e, {})

    def get_positions(self, symbol: str) -> Dict[str, Any]:
        """
        Fetch current positions for a specific symbol.

        Note: This method is not fully supported by ccxt for Bybit.

        Args:
            symbol: Trading pair symbol (e.g., "BTC/USDT")

        Returns:
            Position information (empty dict for now)
        """
        self.logger.warning("The get_positions method is not supported by ccxt for Bybit. Returning empty dict.")
        return {}

    def get_order_status(self, order_id: str) -> Dict[str, Any]:
        """
        Fetch the status of a specific order from Bybit.

        Args:
            order_id: Order ID to query

        Returns:
            Order status information
        """
        # Validate order_id
        if not order_id or not isinstance(order_id, str):
            error_msg = f"Invalid order_id: {order_id}"
            self.logger.error(error_msg)
            return {"error": error_msg, "status": "rejected"}

        # Sanitize input
        order_id = Security.sanitize_input(order_id)

        try:
            return self.exchange.fetch_order(order_id)
        except Exception as e:
            return self._handle_error(f"checking status of order {order_id}", e, {})

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
        # Validate inputs
        if not Security.validate_symbol(symbol):
            self.logger.error(f"Invalid symbol format: {symbol}")
            return pd.DataFrame()

        valid_timeframes = ["1m", "3m", "5m", "15m", "30m", "1h", "2h", "4h", "6h", "12h", "1d", "1w", "1M"]
        if not Security.validate_input(timeframe, allowed_values=valid_timeframes):
            self.logger.error(f"Invalid timeframe: {timeframe}")
            return pd.DataFrame()

        # Validate date format (ISO format)
        date_pattern = r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$'
        if not Security.validate_input(start_date, pattern=date_pattern):
            self.logger.error(f"Invalid date format: {start_date}. Expected format: YYYY-MM-DDThh:mm:ssZ")
            return pd.DataFrame()

        # Validate and sanitize save_folder
        if save_folder is not None:
            if not isinstance(save_folder, str):
                self.logger.error(f"Invalid save_folder: {save_folder}")
                return pd.DataFrame()

            # Sanitize folder path to prevent path traversal attacks
            save_folder = Security.sanitize_input(save_folder)

            # Ensure the folder doesn't contain path traversal attempts
            if '..' in save_folder:
                self.logger.error(f"Invalid save_folder path: {save_folder}")
                return pd.DataFrame()

        # Call the parent implementation with validated inputs
        return super().download_candels_to_csv(symbol, start_date, timeframe, save_folder)


    # Asynchronous API methods

    async def get_ohlcv_async(self, symbol: str, timeframe: str = "1m", limit: int = 100) -> pd.DataFrame:
        """
        Asynchronously fetch OHLCV candlestick data from Bybit.

        Args:
            symbol: Trading pair symbol (e.g., "BTC/USDT")
            timeframe: Candlestick timeframe (e.g., "1m", "5m", "1h", "1d")
            limit: Maximum number of candles to fetch

        Returns:
            DataFrame containing OHLCV data
        """
        try:
            self.logger.info(f"Asynchronously fetching OHLCV: symbol={symbol}, timeframe={timeframe}, limit={limit}")
            ohlcv = await self.async_exchange.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit)
            df = pd.DataFrame(ohlcv, columns=["timestamp", "open", "high", "low", "close", "volume"])
            df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
            df.rename(columns={"timestamp": "time"}, inplace=True)
            return df
        except Exception as e:
            return await self._handle_error_async(f"fetching OHLCV for {symbol}", e, pd.DataFrame())

    async def place_order_async(self, symbol: str, side: str, qty: float, 
                   order_type: str = "market", price: Optional[float] = None) -> Dict[str, Any]:
        """
        Asynchronously place a trading order on Bybit.

        Args:
            symbol: Trading pair symbol (e.g., "BTC/USDT")
            side: Order side ("buy" or "sell")
            qty: Order quantity
            order_type: Order type ("market", "limit", etc.)
            price: Order price (required for limit orders)

        Returns:
            Order information including order ID and status
        """
        try:
            self.logger.info(f"Asynchronously creating order: {side.upper()} {qty} {symbol}, type={order_type.upper()}, price={price}")
            params = {}

            if order_type == "market":
                return await self.async_exchange.create_market_order(symbol, side.lower(), qty, params)
            elif order_type == "limit":
                return await self.async_exchange.create_limit_order(symbol, side.lower(), qty, price, params)
            else:
                raise ValueError("Invalid order type")
        except Exception as e:
            return await self._handle_error_async(f"placing {order_type} order for {symbol}", e, {})

    async def get_balance_async(self) -> Dict[str, Any]:
        """
        Asynchronously fetch account balance information from Bybit.

        Returns:
            Account balance information for all assets
        """
        try:
            balance = await self.async_exchange.fetch_balance()
            return balance['total']
        except Exception as e:
            return await self._handle_error_async("fetching balance", e, {})

    async def get_positions_async(self, symbol: str) -> Dict[str, Any]:
        """
        Asynchronously fetch current positions for a specific symbol.

        Note: This method is not fully supported by ccxt for Bybit.

        Args:
            symbol: Trading pair symbol (e.g., "BTC/USDT")

        Returns:
            Position information (empty dict for now)
        """
        self.logger.warning("The get_positions_async method is not supported by ccxt for Bybit. Returning empty dict.")
        return {}

    async def get_order_status_async(self, order_id: str) -> Dict[str, Any]:
        """
        Asynchronously fetch the status of a specific order from Bybit.

        Args:
            order_id: Order ID to query

        Returns:
            Order status information
        """
        # Validate order_id
        if not order_id or not isinstance(order_id, str):
            error_msg = f"Invalid order_id: {order_id}"
            self.logger.error(error_msg)
            return {"error": error_msg, "status": "rejected"}

        # Sanitize input
        order_id = Security.sanitize_input(order_id)

        try:
            return await self.async_exchange.fetch_order(order_id)
        except Exception as e:
            return await self._handle_error_async(f"checking status of order {order_id}", e, {})

    async def download_candels_to_csv_async(self, symbol: str, start_date: str = "2023-01-01T00:00:00Z", 
                               timeframe: str = "1h", save_folder: str = "DATA") -> pd.DataFrame:
        """
        Asynchronously download historical candle data and save to CSV.

        Args:
            symbol: Trading pair symbol (e.g., "BTC/USDT")
            start_date: Start date for historical data in ISO format
            timeframe: Candlestick timeframe (e.g., "1m", "5m", "1h", "1d")
            save_folder: Folder to save CSV file (None to not save)

        Returns:
            DataFrame containing the downloaded data
        """
        # Validate inputs
        if not Security.validate_symbol(symbol):
            self.logger.error(f"Invalid symbol format: {symbol}")
            return pd.DataFrame()

        valid_timeframes = ["1m", "3m", "5m", "15m", "30m", "1h", "2h", "4h", "6h", "12h", "1d", "1w", "1M"]
        if not Security.validate_input(timeframe, allowed_values=valid_timeframes):
            self.logger.error(f"Invalid timeframe: {timeframe}")
            return pd.DataFrame()

        # Validate date format (ISO format)
        date_pattern = r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$'
        if not Security.validate_input(start_date, pattern=date_pattern):
            self.logger.error(f"Invalid date format: {start_date}. Expected format: YYYY-MM-DDThh:mm:ssZ")
            return pd.DataFrame()

        # Validate and sanitize save_folder
        if save_folder is not None:
            if not isinstance(save_folder, str):
                self.logger.error(f"Invalid save_folder: {save_folder}")
                return pd.DataFrame()

            # Sanitize folder path to prevent path traversal attacks
            save_folder = Security.sanitize_input(save_folder)

            # Ensure the folder doesn't contain path traversal attempts
            if '..' in save_folder:
                self.logger.error(f"Invalid save_folder path: {save_folder}")
                return pd.DataFrame()

        # Call the parent implementation with validated inputs
        return await super().download_candels_to_csv_async(symbol, start_date, timeframe, save_folder)

    async def close_async(self):
        """
        Close the async exchange connection.
        This method should be called when you're done using the async methods.
        """
        if self.async_exchange:
            await self.async_exchange.close()


if __name__ == "__main__":
    bot = BybitAPI(api_key=None, api_secret=None)
    bot.download_candels_to_csv("BTC/USDT", start_date="2025-05-05T00:00:00Z", timeframe="1h")
    df = bot.get_ohlcv("BTC/USDT")
