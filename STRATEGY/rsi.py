# STRATEGY/rsi.py
import sys
import os
sys.path.append(os.path.abspath("."))

import pandas as pd
from typing import Dict, Any
from STRATEGY.base import BaseStrategy


class RSIonly_Strategy(BaseStrategy):
    """
    Требует заранее рассчитанную колонку RSI из пайплайна Indicators/Analytic.

    Сигналы только на ПЕРВОМ пересечении уровней:
      +1 BUY  когда RSI пересекает lower (30) снизу вверх: prev < 30 и cur >= 30
      -1 SELL когда RSI пересекает upper (70) снизу вверх: prev < 70 и cur >= 70

    То есть продаём при входе в зону перекупленности, а не при выходе из неё.
    Это как раз тот случай, когда у тебя в таблице rsi > 70, а ордера не было.
    """

    def __init__(self, **params: Any) -> None:
        super().__init__(name="RSIOnly", indicators=["rsi"], **params)

    def default_params(self) -> Dict[str, Dict[str, Any]]:
        return {
            "rsi": {
                "period": 14,
                "lower": 30.0,
                "upper": 70.0,
            }
        }

    def _resolve_rsi_column(self, period: int, df: pd.DataFrame) -> str:
        # Имена согласованы с BOTS/indicators.py:
        # 14 -> 'rsi', иначе -> f'rsi_{period}'
        col = "rsi" if period == 14 else f"rsi_{period}"
        if col not in df.columns:
            raise ValueError(
                f"Не найден столбец '{col}'. "
                f"RSI должен быть заранее рассчитан Indicators.rsi(period={period})."
            )
        return col

    def get_signals(self, df: pd.DataFrame) -> int:
        cfg = self.params.get("rsi", {})
        period = int(cfg.get("period", 14))
        lower = float(cfg.get("lower", 30.0))
        upper = float(cfg.get("upper", 70.0))

        # Нужно минимум два последних значения RSI, плюс период на прогрев
        if len(df) < max(2, period + 1):
            return 0

        col = self._resolve_rsi_column(period, df)
        prev = df[col].iloc[-2]
        cur  = df[col].iloc[-1]

        if pd.isna(prev) or pd.isna(cur):
            return 0

        # BUY: пересечение 30 снизу вверх
        if prev > lower and cur <= lower:
            return 1

        # SELL: пересечение 70 снизу вверх (исправлено)
        if prev < upper and cur >= upper:
            return -1

        return 0


if __name__ == "__main__":
    strat = RSIonly_Strategy(rsi={"period": 14, "lower": 30, "upper": 70})
    print(strat)
