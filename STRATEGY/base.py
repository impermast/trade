# strategy/base.py

from abc import ABC, abstractmethod
import pandas as pd

class BaseStrategy(ABC):
    """
    Абстрактная стратегия, работающая с DataFrame OHLCV.
    """

    def __init__(self, name: str = "BaseStrategy", **params):
        self.name = name
        self.params = params  # сюда передаются настройки, например: threshold=0.01, rsi_period=14

    @abstractmethod
    def generate_signal(self, df: pd.DataFrame) -> int:
        """
        Возвращает сигнал:
        -1 = Продажа
         0 = Пропустить
         1 = Покупка
        """
        pass

    def __str__(self):
        return f"{self.name}(params={self.params})"
