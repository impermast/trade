# strategies/rsi_only.py
import sys
import os
sys.path.append(os.path.abspath("."))

import pandas as pd
from STRATEGY.base import BaseStrategy

class RSIonly_Strategy(BaseStrategy):
    def __init__(self, **params):
        super().__init__(name="RSIOnly", indicators=["rsi"], **params)

    def default_params(self):
        return {
            "rsi_period": 14,
            "rsi_lower": 30.0,
            "rsi_upper": 70.0
        }

    def get_signals(self, df: pd.DataFrame) -> int:
        if len(df) < self.params["rsi_period"]:
            return 0


        rsi = df["rsi"].iloc[-1]
        if rsi < self.params["rsi_lower"]:
            return 1
        elif rsi > self.params["rsi_upper"]:
            return -1
        return 0


if __name__ == "__main__":
    strat = RSIonly_Strategy()
    print(strat)