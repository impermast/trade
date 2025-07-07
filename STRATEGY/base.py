# strategy/base.py

from abc import ABC, abstractmethod
import pandas as pd


class BaseStrategy(ABC):
    """
    Абстрактная стратегия, работающая с DataFrame OHLCV.
    """

    def __init__(self, name:str, indicators = None, **params):
        self.name = name
        default_params = self.default_params()
        self.params = {**default_params, **params}
        self.indicators = indicators or []

    @abstractmethod
    def get_signals(self, df: pd.DataFrame) -> int:
        """
        Возвращает сигнал:
        -1 = Продажа
         0 = Пропустить
         1 = Покупка
        """
        pass
    
    
    @abstractmethod
    def default_params(self) -> dict:
        """Определяет список нужных параметров и их дефолты"""
        pass
    
    
    def check_indicators(self) -> list:
        """
        Возвращает список используемых индикаторов (строками),
        например: ["rsi", "macd", "macd_signal", "sma"]
        """
        return self.indicators


    def __str__(self):
        return f"Strategy = {self.name}  (params = {self.params})"
