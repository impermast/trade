# API/mock_api.py

import pandas as pd
import json
import os
from typing import Dict, Any, Optional, List
import datetime
import random

from API.birza_api import BirzaAPI

class MockAPI(BirzaAPI):
    """
    Mock API client for testing purposes.
    
    This class implements the BirzaAPI interface with simulated responses,
    allowing for testing without connecting to real exchanges.
    
    Attributes:
        data_dir: Directory containing mock data files
        mock_data: Dictionary containing preloaded mock data
        mock_balance: Dictionary containing mock balance data
        mock_orders: Dictionary containing mock order data
        mock_positions: Dictionary containing mock position data
    """
    
    def __init__(self, data_dir: str = "DATA/mock", 
                log_file: Optional[str] = "LOGS/mock_api.log", 
                console: bool = True):
        """
        Initialize the Mock API client.
        
        Args:
            data_dir: Directory containing mock data files
            log_file: Path to log file
            console: Whether to log to console
        """
        super().__init__(name="MockAPI", log_tag="[MOCK_API]", log_file=log_file, console=console)
        
        self.data_dir = data_dir
        self.mock_data = {}
        self.mock_balance = {
            "BTC": 1.0,
            "ETH": 10.0,
            "USDT": 10000.0,
            "USD": 10000.0
        }
        self.mock_orders = {}
        self.mock_positions = {}
        
        # Create data directory if it doesn't exist
        os.makedirs(data_dir, exist_ok=True)
        
        self.logger.info(f"Initialized MockAPI with data directory: {data_dir}")
    
    def _load_mock_data(self, symbol: str, timeframe: str = "1h") -> pd.DataFrame:
        """
        Load mock data for a symbol and timeframe.
        
        Args:
            symbol: Trading pair symbol (e.g., "BTC/USDT")
            timeframe: Candlestick timeframe (e.g., "1m", "5m", "1h", "1d")
            
        Returns:
            DataFrame containing mock OHLCV data
        """
        key = f"{symbol}_{timeframe}"
        
        # Return cached data if available
        if key in self.mock_data:
            return self.mock_data[key].copy()
        
        # Try to load data from file
        file_path = os.path.join(self.data_dir, f"{symbol.replace('/', '')}_{timeframe}.csv")
        if os.path.exists(file_path):
            self.logger.info(f"Loading mock data from file: {file_path}")
            df = pd.read_csv(file_path)
            if 'time' in df.columns:
                df['time'] = pd.to_datetime(df['time'])
            self.mock_data[key] = df
            return df.copy()
        
        # Generate mock data if file doesn't exist
        self.logger.info(f"Generating mock data for {symbol}, timeframe={timeframe}")
        df = self._generate_mock_data(symbol, timeframe)
        self.mock_data[key] = df
        return df.copy()
    
    def _generate_mock_data(self, symbol: str, timeframe: str = "1h", 
                           num_candles: int = 1000) -> pd.DataFrame:
        """
        Generate mock OHLCV data.
        
        Args:
            symbol: Trading pair symbol (e.g., "BTC/USDT")
            timeframe: Candlestick timeframe (e.g., "1m", "5m", "1h", "1d")
            num_candles: Number of candles to generate
            
        Returns:
            DataFrame containing generated mock OHLCV data
        """
        # Determine time delta based on timeframe
        if timeframe.endswith('m'):
            delta = datetime.timedelta(minutes=int(timeframe[:-1]))
        elif timeframe.endswith('h'):
            delta = datetime.timedelta(hours=int(timeframe[:-1]))
        elif timeframe.endswith('d'):
            delta = datetime.timedelta(days=int(timeframe[:-1]))
        else:
            delta = datetime.timedelta(hours=1)  # Default to 1h
        
        # Generate timestamps
        end_time = datetime.datetime.now()
        timestamps = [end_time - delta * i for i in range(num_candles)]
        timestamps.reverse()  # Oldest first
        
        # Determine starting price based on symbol
        if symbol.startswith("BTC"):
            base_price = 30000.0
            volatility = 0.02
        elif symbol.startswith("ETH"):
            base_price = 2000.0
            volatility = 0.03
        else:
            base_price = 100.0
            volatility = 0.05
        
        # Generate price data with random walk
        prices = [base_price]
        for i in range(1, num_candles):
            change = prices[-1] * random.uniform(-volatility, volatility)
            prices.append(max(0.01, prices[-1] + change))
        
        # Generate OHLCV data
        data = []
        for i, timestamp in enumerate(timestamps):
            price = prices[i]
            high = price * (1 + random.uniform(0, volatility/2))
            low = price * (1 - random.uniform(0, volatility/2))
            open_price = price * (1 + random.uniform(-volatility/4, volatility/4))
            close = price * (1 + random.uniform(-volatility/4, volatility/4))
            volume = price * random.uniform(10, 100)
            
            data.append({
                'time': timestamp,
                'open': open_price,
                'high': high,
                'low': low,
                'close': close,
                'volume': volume
            })
        
        df = pd.DataFrame(data)
        
        # Save to file
        file_path = os.path.join(self.data_dir, f"{symbol.replace('/', '')}_{timeframe}.csv")
        df.to_csv(file_path, index=False)
        self.logger.info(f"Saved generated mock data to: {file_path}")
        
        return df
    
    def get_ohlcv(self, symbol: str, timeframe: str = "1m", limit: int = 100) -> pd.DataFrame:
        """
        Fetch OHLCV candlestick data from mock data.
        
        Args:
            symbol: Trading pair symbol (e.g., "BTC/USDT")
            timeframe: Candlestick timeframe (e.g., "1m", "5m", "1h", "1d")
            limit: Maximum number of candles to fetch
            
        Returns:
            DataFrame containing OHLCV data
        """
        try:
            self.logger.info(f"Fetching mock OHLCV: symbol={symbol}, timeframe={timeframe}, limit={limit}")
            df = self._load_mock_data(symbol, timeframe)
            return df.tail(limit).reset_index(drop=True)
        except Exception as e:
            return self._handle_error(f"fetching mock OHLCV for {symbol}", e, pd.DataFrame())
    
    def place_order(self, symbol: str, side: str, qty: float,
                   order_type: str = "market", price: Optional[float] = None) -> Dict[str, Any]:
        """
        Place a mock trading order.
        
        Args:
            symbol: Trading pair symbol (e.g., "BTC/USDT")
            side: Order side ("buy" or "sell")
            qty: Order quantity
            order_type: Order type ("market", "limit", etc.)
            price: Order price (required for limit orders)
            
        Returns:
            Mock order information
        """
        try:
            self.logger.info(f"Creating mock order: {side.upper()} {qty} {symbol}, type={order_type.upper()}, price={price}")
            
            # Generate a random order ID
            order_id = f"mock_order_{len(self.mock_orders) + 1}_{int(datetime.datetime.now().timestamp())}"
            
            # Get current price from mock data
            df = self._load_mock_data(symbol, "1m")
            current_price = df.iloc[-1]['close'] if not df.empty else (price or 10000.0)
            
            # Create order object
            order = {
                "id": order_id,
                "symbol": symbol,
                "side": side.lower(),
                "type": order_type.lower(),
                "price": price if order_type.lower() == "limit" else current_price,
                "amount": qty,
                "cost": qty * (price if order_type.lower() == "limit" else current_price),
                "timestamp": datetime.datetime.now().timestamp() * 1000,
                "datetime": datetime.datetime.now().isoformat(),
                "status": "closed" if order_type.lower() == "market" else "open",
                "filled": qty if order_type.lower() == "market" else 0.0,
                "remaining": 0.0 if order_type.lower() == "market" else qty,
                "fee": {
                    "cost": qty * current_price * 0.001,
                    "currency": symbol.split('/')[1] if '/' in symbol else "USDT"
                }
            }
            
            # Store the order
            self.mock_orders[order_id] = order
            
            # Update balance for market orders
            if order_type.lower() == "market":
                self._update_balance_after_order(order)
            
            return order
        except Exception as e:
            return self._handle_error(f"placing mock {order_type} order for {symbol}", e, {})
    
    def _update_balance_after_order(self, order: Dict[str, Any]) -> None:
        """
        Update mock balance after an order is executed.
        
        Args:
            order: Order information
        """
        if '/' not in order['symbol']:
            self.logger.warning(f"Invalid symbol format: {order['symbol']}, expected format like 'BTC/USDT'")
            return
            
        base, quote = order['symbol'].split('/')
        
        if order['side'] == 'buy':
            # Deduct quote currency (e.g., USDT)
            self.mock_balance[quote] = self.mock_balance.get(quote, 0) - order['cost']
            # Add base currency (e.g., BTC)
            self.mock_balance[base] = self.mock_balance.get(base, 0) + order['amount']
        else:  # sell
            # Add quote currency (e.g., USDT)
            self.mock_balance[quote] = self.mock_balance.get(quote, 0) + order['cost']
            # Deduct base currency (e.g., BTC)
            self.mock_balance[base] = self.mock_balance.get(base, 0) - order['amount']
        
        # Deduct fee
        fee_currency = order['fee']['currency']
        self.mock_balance[fee_currency] = self.mock_balance.get(fee_currency, 0) - order['fee']['cost']
    
    def get_balance(self) -> Dict[str, Any]:
        """
        Fetch mock account balance information.
        
        Returns:
            Mock account balance information
        """
        try:
            self.logger.info("Fetching mock balance")
            return self.mock_balance.copy()
        except Exception as e:
            return self._handle_error("fetching mock balance", e, {})
    
    def get_positions(self, symbol: str) -> Dict[str, Any]:
        """
        Fetch mock positions for a specific symbol.
        
        Args:
            symbol: Trading pair symbol (e.g., "BTC/USDT")
            
        Returns:
            Mock position information
        """
        try:
            self.logger.info(f"Fetching mock positions for {symbol}")
            
            # Return existing position if available
            if symbol in self.mock_positions:
                return self.mock_positions[symbol].copy()
            
            # Create a mock position
            position = {
                "symbol": symbol,
                "size": 0.0,
                "side": "none",
                "entryPrice": 0.0,
                "markPrice": 0.0,
                "unrealizedPnl": 0.0,
                "leverage": 1.0,
                "marginType": "isolated",
                "liquidationPrice": 0.0,
                "timestamp": datetime.datetime.now().timestamp() * 1000,
                "datetime": datetime.datetime.now().isoformat()
            }
            
            self.mock_positions[symbol] = position
            return position.copy()
        except Exception as e:
            return self._handle_error(f"fetching mock positions for {symbol}", e, {})
    
    def get_order_status(self, order_id: str) -> Dict[str, Any]:
        """
        Fetch the status of a specific mock order.
        
        Args:
            order_id: Order ID to query
            
        Returns:
            Mock order status information
        """
        try:
            self.logger.info(f"Fetching status for mock order {order_id}")
            
            if order_id in self.mock_orders:
                return self.mock_orders[order_id].copy()
            
            raise ValueError(f"Order {order_id} not found")
        except Exception as e:
            return self._handle_error(f"checking status of mock order {order_id}", e, {})
    
    def download_candels_to_csv(self, symbol: str, start_date: str = "2023-01-01T00:00:00Z", 
                               timeframe: str = "1h", save_folder: str = "DATA") -> pd.DataFrame:
        """
        Download mock historical candle data and save to CSV.
        
        Args:
            symbol: Trading pair symbol (e.g., "BTC/USDT")
            start_date: Start date for historical data in ISO format
            timeframe: Candlestick timeframe (e.g., "1m", "5m", "1h", "1d")
            save_folder: Folder to save CSV file (None to not save)
            
        Returns:
            DataFrame containing the mock data
        """
        try:
            self.logger.info(f"Downloading mock historical data for {symbol} from {start_date}")
            
            # Generate or load mock data
            df = self._load_mock_data(symbol, timeframe)
            
            # Filter by start date if provided
            if start_date:
                start_datetime = pd.to_datetime(start_date)
                df = df[df['time'] >= start_datetime].reset_index(drop=True)
            
            # Save to the specified folder if requested
            if save_folder is not None and save_folder != self.data_dir:
                os.makedirs(save_folder, exist_ok=True)
                file_name = f'{symbol.replace("/", "")}_{timeframe}.csv'
                save_path = os.path.join(save_folder, file_name)
                df.to_csv(save_path, index=False)
                self.logger.info(f"Saved mock data to: {save_path}")
            
            return df
        except Exception as e:
            return self._handle_error(f"downloading mock data for {symbol}", e, pd.DataFrame())