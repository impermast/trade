# strategies/rsi_only.py
import sys
import os
sys.path.append(os.path.abspath("."))

import pandas as pd
from STRATEGY.base import BaseStrategy


class RSIonly_Strategy(BaseStrategy):
    def __init__(self, **params):
        # Пробрасываем вложенный словарь по индикаторам
        super().__init__(name="RSIOnly", indicators=["rsi"], **params)

    def default_params(self):
        return {
            "rsi": {
                "period": 14,
                "lower": 30,
                "upper": 70
            }
        }

    def get_signals(self, df: pd.DataFrame) -> int:
        rsi_cfg = self.params["rsi"]
        period = rsi_cfg["period"]
        lower = rsi_cfg["lower"]
        upper = rsi_cfg["upper"]

        if len(df) < period:
            return 0

        rsi = df["rsi"].iloc[-1]

        if rsi < lower:
            return 1
        elif rsi > upper:
            return -1
        return 0


if __name__ == "__main__":
    strat = RSIonly_Strategy(rsi={"period": 10, "lower": 25})
    print(strat)