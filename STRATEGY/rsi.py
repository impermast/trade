# STRATEGY/rsi.py
import os
import sys
from typing import Any, Dict, Optional

import numpy as np
import pandas as pd

# allow local imports when running as a script
sys.path.append(os.path.abspath("."))

from STRATEGY.base import BaseStrategy  # type: ignore


class RSIonly_Strategy(BaseStrategy):
    """
    Стратегия на основе RSI.
    
    Генерирует сигналы на покупку при перепроданности (RSI < 30),
    и сигналы на продажу при перекупленности (RSI > 70).
    """
    
    def __init__(self, df: Optional[pd.DataFrame] = None, params: Optional[Dict[str, Any]] = None):
        super().__init__(df=df, params=params, name="RSI Strategy", indicators=["rsi"])
        # Setup logger
        from CORE.log_manager import Logger
        self.logger = Logger(name="RSI", tag="[RSI]", logfile="LOGS/rsi.log", console=False).get_logger()

    def default_params(self) -> Dict[str, Dict[str, Any]]:
        return {"rsi": {"period": 14, "lower": 30.0, "upper": 70.0}}

    def _ensure_orders_col(self, df: pd.DataFrame) -> None:
        if "orders_rsi" not in df.columns:
            df.insert(len(df.columns), "orders_rsi", pd.Series(index=df.index, dtype="float64"))

    # ----- helpers -----
    @staticmethod
    def _rsi_col(period: int) -> str:
        # Имена согласованы с Indicators: rsi или rsi_{period}
        return "rsi" if int(period) == 14 else f"rsi_{int(period)}"

    def _ensure_required_rsi(self, df: pd.DataFrame, period: int) -> None:
        """
        Узко: если нужной колонки RSI нет — считаем через Analytic
        (используем общий механизм ensure_indicators).
        """
        want_col = self._rsi_col(period)
        if want_col in df.columns:
            return
        self._ensure_indicators_and_save(df)

    # ----- public -----
    def get_signals(self, df: pd.DataFrame) -> int:
        cfg = self.params.get("rsi", {})
        period = int(cfg.get("period", 14))
        lower = float(cfg.get("lower", 30.0))
        upper = float(cfg.get("upper", 70.0))

        # 1) Гарантируем наличие нужных индикаторов (как у XGB)
        want_col = self._rsi_col(period)
        if want_col not in df.columns:
            try:
                self._ensure_required_rsi(df, period)
            except Exception as e:
                # не роняем пайплайн
                self.logger.error(f"[RSI] Failed to ensure indicators via Analytic: {e}")

        if want_col not in df.columns:
            # всё ещё нет — отдаём 0 и заполняем orders_rsi нулями
            self._ensure_orders_col(df)
            df["orders_rsi"] = 0.0
            return 0

        r = pd.to_numeric(df[want_col], errors="coerce")
        if len(r) < max(2, period + 1):
            self._ensure_orders_col(df)
            df["orders_rsi"] = 0.0
            return 0

        prev = r.shift(1)

        # SELL: пересечение верхнего порога снизу вверх
        sell_cross = (prev < upper) & (r >= upper)
        # BUY: пересечение нижнего порога сверху вниз
        buy_cross = (prev > lower) & (r <= lower)

        signals = np.zeros(len(df), dtype=int)
        # приоритет SELL
        sell_mask = sell_cross.fillna(False).to_numpy()
        buy_mask = buy_cross.fillna(False).to_numpy() & (~sell_mask)

        signals[sell_mask] = -1
        signals[buy_mask] = 1

        self._ensure_orders_col(df)
        df["orders_rsi"] = signals.astype(float)

        last_sig = int(signals[-1]) if pd.notna(r.iloc[-1]) and pd.notna(r.iloc[-2]) else 0
        return last_sig


if __name__ == "__main__":
    from CORE.log_manager import Logger
    logger = Logger(name="RSI", tag="[RSI]", logfile="LOGS/rsi.log", console=True).get_logger()
    logger.info("RSIonly_Strategy module OK")
