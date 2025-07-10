# api/bybit_api.py

import os
import sys
import ccxt
import ccxt.async_support as ccxt_async
import pandas as pd
from typing import Dict, Any, Optional
import asyncio

sys.path.append(os.path.abspath("."))

from API.birza_api import BirzaAPI

class BybitAPI(BirzaAPI):
    """
    API client for the Bybit cryptocurrency exchange.

    This class implements the BirzaAPI interface for the Bybit exchange
    using the ccxt library.
    """

    def __init__(self, api_key: Optional[str], api_secret: Optional[str], testnet: bool = True):
        """
        Initialize the Bybit API client.

        Args:
            api_key: API key for authentication (None for public API only)
            api_secret: API secret for authentication (None for public API only)
            testnet: Whether to use the testnet (sandbox) environment
        """
        super().__init__(name="bybitAPI", log_tag="[API]", log_file="LOGS/bybitAPI.log", console=True)

        # Initialize the ccxt exchange object (synchronous)
        self.exchange = ccxt.bybit({
            'apiKey': api_key,
            'secret': api_secret,
            'enableRateLimit': True,
        })

        # Initialize the ccxt async exchange object
        self.async_exchange = ccxt_async.bybit({
            'apiKey': api_key,
            'secret': api_secret,
            'enableRateLimit': True,
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
        try:
            self.logger.info(f"Creating order: {side.upper()} {qty} {symbol}, type={order_type.upper()}, price={price}")
            params = {}

            if order_type == "market":
                return self.exchange.create_market_order(symbol, side.lower(), qty, params)
            elif order_type == "limit":
                return self.exchange.create_limit_order(symbol, side.lower(), qty, price, params)
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
        try:
            return self.exchange.fetch_order(order_id)
        except Exception as e:
            return self._handle_error(f"checking status of order {order_id}", e, {})


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
        try:
            return await self.async_exchange.fetch_order(order_id)
        except Exception as e:
            return await self._handle_error_async(f"checking status of order {order_id}", e, {})

    async def close_async(self):
        """
        Close the async exchange connection.
        This method should be called when you're done using the async methods.
        """
        if self.async_exchange:
            await self.async_exchange.close()


if __name__ == "__main__":
    bot = BybitAPI(api_key=None, api_secret=None)
    bot.download_candels_to_csv("BTC/USDT", start_date="2023-05-05T00:00:00Z", timeframe="1h")
    df = bot.get_ohlcv("BTC/USDT")
    # print(df.head)

    # Example of using async methods
    """
    async def test_async():
        bot = BybitAPI(api_key=None, api_secret=None)
        try:
            df = await bot.get_ohlcv_async("BTC/USDT")
            print(df.head())
        finally:
            await bot.close_async()

    # Run the async example
    import asyncio
    asyncio.run(test_async())
    """
