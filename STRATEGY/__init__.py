# STRATEGY/__init__.py
"""
Инициализация пакета стратегий.

Этот файл содержит центральный реестр (STRATEGY_REGISTRY), который позволяет
легко добавлять и управлять всеми доступными торговыми стратегиями в проекте.

Для добавления новой стратегии:
1. Импортируйте класс вашей новой стратегии из ее файла.
   (например, from .my_new_strategy import MyNewStrategy)
2. Добавьте новую запись в словарь STRATEGY_REGISTRY.
   - Ключ: Короткое, уникальное имя для использования в .env (например, "MY_NEW_STRATEGY").
   - Значение: Словарь, содержащий:
     - "class": Ссылка на класс вашей стратегии (например, MyNewStrategy).
     - "params": Словарь с параметрами по умолчанию для этой стратегии.
"""

# 1. Импорт классов всех реализованных стратегий
from .bollinger_mean_reversion import BollingerMeanReversionStrategy
from .XGBstrategy import XGBStrategy
from .macd_crossover import MACDCrossoverStrategy
from .rsi import RSIonly_Strategy
from .stochastic_oscillator import StochasticOscillatorStrategy
from .williams_r import WilliamsRStrategy

# 2. Регистрация стратегий и их параметров по умолчанию
STRATEGY_REGISTRY = {
    "BOLLINGER": {
        "class": BollingerMeanReversionStrategy,
        "params": {
            "bollinger_bands": {"period": 20, "window_dev": 2.0}
        }
    },
    "XGB": {
        "class": XGBStrategy,
        "params": {
            "rsi": {"period": 14},
            "ema": {"period": 10},
            "sma": {"period": 10},
            "macd": {"window_fast": 12, "window_slow": 26, "window_sign": 9},
            "bollinger_bands": {"period": 20, "window_dev": 2},
        }
    },
    "MACD": {
        "class": MACDCrossoverStrategy,
        "params": {
            "macd": {"window_fast": 12, "window_slow": 26, "window_sign": 9}
        }
    },
    "RSI": {
        "class": RSIonly_Strategy,
        "params": {
            "rsi": {"period": 14, "lower": 30.0, "upper": 70.0}
        }
    },
    "STOCHASTIC": {
        "class": StochasticOscillatorStrategy,
        "params": {
            "stochastic_oscillator": {"k_period": 14, "d_period": 3, "oversold": 20.0, "overbought": 80.0}
        }
    },
    "WILLIAMS_R": {
        "class": WilliamsRStrategy,
        "params": {
            "williams_r": {"period": 14, "oversold": -80.0, "overbought": -20.0}
        }
    },
}

# Это позволяет импортировать реестр напрямую из пакета: from STRATEGY import STRATEGY_REGISTRY
__all__ = ["STRATEGY_REGISTRY"]
