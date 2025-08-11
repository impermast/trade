# STRATEGY/williams_r.py
import os
import sys
from typing import Any, Dict, Optional

import numpy as np
import pandas as pd

# allow local imports when running as a script
sys.path.append(os.path.abspath("."))

from STRATEGY.base import BaseStrategy  # type: ignore


class WilliamsRStrategy(BaseStrategy):
    """
    Williams %R Strategy:
      • BUY  (+1) при выходе из зоны перепроданности (>-80);
      • SELL (-1) при входе в зону перекупленности (<-20);
      • При одновременном сигнале — приоритет SELL.
      
    Колонка Williams %R: 'williams_r' при стандартных параметрах,
    иначе 'williams_r_{period}'.
    """
    
    def __init__(self, **params: Any) -> None:
        super().__init__(
            name="WilliamsR", 
            indicators=["williams_r"], 
            **params
        )
    
    def default_params(self) -> Dict[str, Dict[str, Any]]:
        return {
            "williams_r": {
                "period": 14,
                "oversold": -80.0,
                "overbought": -20.0
            }
        }
    
    def _ensure_orders_col(self, df: pd.DataFrame) -> None:
        """Создаем колонку для сигналов стратегии"""
        if "orders_williams_r" not in df.columns:
            df.insert(len(df.columns), "orders_williams_r", pd.Series(index=df.index, dtype="float64"))
    
    # ----- helpers -----
    @staticmethod
    def _williams_r_col(period: int) -> str:
        """Имя колонки Williams %R согласовано с Indicators"""
        return "williams_r" if int(period) == 14 else f"williams_r_{int(period)}"
    
    def _ensure_required_williams_r(self, df: pd.DataFrame, period: int) -> None:
        """Узко: если нужной колонки Williams %R нет — считаем через Analytic"""
        want_col = self._williams_r_col(period)
        if want_col in df.columns:
            return
        self._ensure_indicators_and_save(df)
    
    # ----- public -----
    def get_signals(self, df: pd.DataFrame) -> int:
        """Генерирует торговые сигналы на основе Williams %R"""
        cfg = self.params.get("williams_r", {})
        period = int(cfg.get("period", 14))
        oversold = float(cfg.get("oversold", -80.0))
        overbought = float(cfg.get("overbought", -20.0))
        
        # 1) Гарантируем наличие нужных индикаторов
        want_col = self._williams_r_col(period)
        if want_col not in df.columns:
            try:
                self._ensure_required_williams_r(df, period)
            except Exception as e:
                # не роняем пайплайн
                print(f"[WILLIAMS_R] Failed to ensure indicators via Analytic: {e}")
        
        if want_col not in df.columns:
            # всё ещё нет — отдаём 0 и заполняем orders_williams_r нулями
            self._ensure_orders_col(df)
            df["orders_williams_r"] = 0.0
            return 0
        
        # Получаем значения Williams %R
        williams_r = pd.to_numeric(df[want_col], errors="coerce")
        
        if len(williams_r) < max(2, period + 1):
            self._ensure_orders_col(df)
            df["orders_williams_r"] = 0.0
            return 0
        
        # Предыдущие значения для определения изменений
        prev_williams_r = williams_r.shift(1)
        
        # BUY: выход из зоны перепроданности (пересечение уровня -80 снизу вверх)
        buy_signal = (prev_williams_r <= oversold) & (williams_r > oversold)
        
        # SELL: вход в зону перекупленности (пересечение уровня -20 сверху вниз)
        sell_signal = (prev_williams_r >= overbought) & (williams_r < overbought)
        
        # Генерируем сигналы
        signals = np.zeros(len(df), dtype=int)
        
        # Приоритет SELL при одновременном сигнале
        sell_mask = sell_signal.fillna(False).to_numpy()
        buy_mask = buy_signal.fillna(False).to_numpy() & (~sell_mask)
        
        signals[sell_mask] = -1
        signals[buy_mask] = 1
        
        # Сохраняем сигналы в DataFrame
        self._ensure_orders_col(df)
        df["orders_williams_r"] = signals.astype(float)
        
        # Возвращаем последний сигнал
        last_sig = int(signals[-1]) if pd.notna(williams_r.iloc[-1]) and pd.notna(prev_williams_r.iloc[-1]) else 0
        return last_sig


if __name__ == "__main__":
    print("WilliamsRStrategy module OK")
