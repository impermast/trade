import sys
import os
from pathlib import Path

# Add project root to sys.path to allow absolute imports
project_root = Path(__file__).parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

"""
Initialization of the strategy package and strategy manager.

This file contains:
1. A central registry (STRATEGY_REGISTRY) for all trading strategies.
"""

# --- Part 1: Strategy Registration ---

# 1.1. Import classes of all implemented strategies
from .bollinger_mean_reversion import BollingerMeanReversionStrategy
from .XGBstrategy import XGBStrategy
from .macd_crossover import MACDCrossoverStrategy
from .rsi import RSIonly_Strategy
from .stochastic_oscillator import StochasticOscillatorStrategy
from .williams_r import WilliamsRStrategy

from .manager import StrategyManager


# 1.2. Register strategies and their default parameters
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

# --- Part 2: Export ---

__all__ = [
    "STRATEGY_REGISTRY",
    "StrategyManager",
]
