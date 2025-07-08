# strategy/base.py

from abc import ABC, abstractmethod
import pandas as pd

class BaseStrategy(ABC):
    def __init__(self, name: str = "BaseStrategy", indicators = None, **params):
        self.name = name
        self.indicators = indicators or []

        # Объединяем default_params и пользовательские:
        self.params = self._merge_with_defaults(self.default_params(), params)

    @abstractmethod
    def get_signals(self, df: pd.DataFrame) -> int:
        pass

    @abstractmethod
    def default_params(self) -> dict:
        pass

    def _merge_with_defaults(self, defaults, overrides):
        merged = defaults.copy()
        for k, v in overrides.items():
            if isinstance(v, dict) and k in merged and isinstance(merged[k], dict):
                merged[k].update(v)
            else:
                merged[k] = v
        return merged

    def check_indicators(self):
        return [self.indicators, self.params]

    def __str__(self):
        return f"{self.name}(params={self.params})"
