from abc import ABC, abstractmethod
import pandas as pd

class BirzaAPI(ABC):
    @abstractmethod
    def get_ohlcv(self, symbol: str, timeframe: str = "1m", limit: int = 200) -> pd.DataFrame:
        pass

    @abstractmethod
    def get_balance(self) -> dict:
        pass

    @abstractmethod
    def get_positions(self, symbol: str) -> dict:
        pass

    @abstractmethod
    def place_order(self, symbol: str, side: str, qty: float, order_type: str = "Market", price: float = None) -> dict:
        pass

    @abstractmethod
    def get_order_status(self, order_id: str) -> dict:
        pass
