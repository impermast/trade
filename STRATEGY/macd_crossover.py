# STRATEGY/macd_crossover.py
import os
import sys
from typing import Any, Dict, Optional

import numpy as np
import pandas as pd

# allow local imports when running as a script
sys.path.append(os.path.abspath("."))

from STRATEGY.base import BaseStrategy  # type: ignore


class MACDCrossoverStrategy(BaseStrategy):
    """
    Стратегия на основе пересечений MACD.
    
    Генерирует сигналы на покупку при пересечении MACD выше сигнальной линии снизу вверх,
    и сигналы на продажу при пересечении MACD ниже сигнальной линии сверху вниз.
    """
    
    def __init__(self, df: Optional[pd.DataFrame] = None, params: Optional[Dict[str, Any]] = None):
        super().__init__(df=df, params=params, name="MACD Crossover Strategy", indicators=["macd"])
        # Setup logger
        from CORE.log_manager import Logger
        self.logger = Logger(name="MACD", tag="[MACD]", logfile="LOGS/macd.log", console=False).get_logger()
    
    def default_params(self) -> Dict[str, Dict[str, Any]]:
        return {
            "macd": {
                "window_fast": 12,
                "window_slow": 26,
                "window_sign": 9
            }
        }
    
    def _ensure_orders_col(self, df: pd.DataFrame) -> None:
        """Создаем колонку для сигналов стратегии"""
        if "orders_macd" not in df.columns:
            df.insert(len(df.columns), "orders_macd", pd.Series(index=df.index, dtype="float64"))
    
    # ----- helpers -----
    @staticmethod
    def _macd_cols(fast: int, slow: int, signal: int) -> tuple[str, str, str]:
        """Имена колонок MACD согласованы с Indicators"""
        is_default = (fast == 12 and slow == 26 and signal == 9)
        if is_default:
            return "macd", "macd_signal", "macd_histogram"
        else:
            return (
                f"macd_{fast}_{slow}",
                f"macd_signal_{fast}_{slow}_{signal}",
                f"macd_histogram_{fast}_{slow}_{signal}"
            )
    
    def _ensure_required_macd(self, df: pd.DataFrame, fast: int, slow: int, signal: int) -> None:
        """Узко: если нужных колонок MACD нет — считаем через Analytic"""
        want_cols = self._macd_cols(fast, slow, signal)
        if all(col in df.columns for col in want_cols):
            return
        self._ensure_indicators_and_save(df)
    
    # ----- public -----
    def get_signals(self, df: pd.DataFrame) -> int:
        """Генерирует торговые сигналы на основе пересечений MACD"""
        cfg = self.params.get("macd", {})
        fast = int(cfg.get("window_fast", 12))
        slow = int(cfg.get("window_slow", 26))
        signal_period = int(cfg.get("window_sign", 9))
        
        # 1) Гарантируем наличие нужных индикаторов
        macd_col, signal_col, hist_col = self._macd_cols(fast, slow, signal_period)
        if not all(col in df.columns for col in [macd_col, signal_col]):
            try:
                self._ensure_required_macd(df, fast, slow, signal_period)
            except Exception as e:
                # не роняем пайплайн
                self.logger.error(f"[MACD] Failed to ensure indicators via Analytic: {e}")
        
        if not all(col in df.columns for col in [macd_col, signal_col]):
            # всё ещё нет — отдаём 0 и заполняем orders_macd нулями
            self._ensure_orders_col(df)
            df["orders_macd"] = 0.0
            return 0
        
        # Получаем значения MACD и сигнальной линии
        macd_line = pd.to_numeric(df[macd_col], errors="coerce")
        signal_line = pd.to_numeric(df[signal_col], errors="coerce")
        
        if len(macd_line) < max(2, slow + signal_period):
            self._ensure_orders_col(df)
            df["orders_macd"] = 0.0
            return 0
        
        # Предыдущие значения для определения пересечений
        prev_macd = macd_line.shift(1)
        prev_signal = signal_line.shift(1)
        
        # BUY: пересечение MACD выше сигнальной линии снизу вверх
        buy_cross = (prev_macd <= prev_signal) & (macd_line > signal_line)
        
        # SELL: пересечение MACD ниже сигнальной линии сверху вниз
        sell_cross = (prev_macd >= prev_signal) & (macd_line < signal_line)
        
        # Генерируем сигналы
        signals = np.zeros(len(df), dtype=int)
        
        # Приоритет SELL при одновременном пересечении
        sell_mask = sell_cross.fillna(False).to_numpy()
        buy_mask = buy_cross.fillna(False).to_numpy() & (~sell_mask)
        
        signals[sell_mask] = -1
        signals[buy_mask] = 1
        
        # Сохраняем сигналы в DataFrame
        self._ensure_orders_col(df)
        df["orders_macd"] = signals.astype(float)
        
        # Возвращаем последний сигнал
        last_sig = int(signals[-1]) if pd.notna(macd_line.iloc[-1]) and pd.notna(signal_line.iloc[-1]) else 0
        return last_sig


if __name__ == "__main__":
    from CORE.log_manager import Logger
    logger = Logger(name="MACD", tag="[MACD]", logfile="LOGS/macd.log", console=True).get_logger()
    logger.info("MACDCrossoverStrategy module OK")
