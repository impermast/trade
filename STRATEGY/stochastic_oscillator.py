# STRATEGY/stochastic_oscillator.py
import os
import sys
from typing import Any, Dict, Optional

import numpy as np
import pandas as pd

# allow local imports when running as a script
sys.path.append(os.path.abspath("."))

from STRATEGY.base import BaseStrategy  # type: ignore


class StochasticOscillatorStrategy(BaseStrategy):
    """
    Стратегия на основе стохастического осциллятора.
    
    Генерирует сигналы на покупку при перепроданности (K < 20),
    и сигналы на продажу при перекупленности (K > 80).
    """
    
    def __init__(self, df: Optional[pd.DataFrame] = None, params: Optional[Dict[str, Any]] = None):
        super().__init__(df=df, params=params, name="Stochastic Oscillator Strategy", indicators=["stochastic_oscillator"])
        # Setup logger
        from CORE.log_manager import Logger
        self.logger = Logger(name="STOCHASTIC", tag="[STOCHASTIC]", logfile="LOGS/stochastic.log", console=False).get_logger()
    
    def default_params(self) -> Dict[str, Dict[str, Any]]:
        return {
            "stochastic_oscillator": {
                "k_period": 14,
                "d_period": 3,
                "oversold": 20.0,
                "overbought": 80.0
            }
        }
    
    def _ensure_orders_col(self, df: pd.DataFrame) -> None:
        """Создаем колонку для сигналов стратегии"""
        if "orders_stochastic" not in df.columns:
            df.insert(len(df.columns), "orders_stochastic", pd.Series(index=df.index, dtype="float64"))
    
    # ----- helpers -----
    @staticmethod
    def _stoch_cols(k_period: int, d_period: int) -> tuple[str, str]:
        """Имена колонок Stochastic Oscillator согласованы с Indicators"""
        is_default = (k_period == 14 and d_period == 3)
        if is_default:
            return "stoch_k", "stoch_d"
        else:
            return f"stoch_k_{k_period}_{d_period}", f"stoch_d_{k_period}_{d_period}"
    
    def _ensure_required_stochastic(self, df: pd.DataFrame, k_period: int, d_period: int) -> None:
        """Узко: если нужных колонок Stochastic нет — считаем через Analytic"""
        want_cols = self._stoch_cols(k_period, d_period)
        if all(col in df.columns for col in want_cols):
            return
        self._ensure_indicators_and_save(df)
    
    # ----- public -----
    def get_signals(self, df: pd.DataFrame) -> int:
        """Генерирует торговые сигналы на основе пересечений Stochastic Oscillator"""
        cfg = self.params.get("stochastic_oscillator", {})
        k_period = int(cfg.get("k_period", 14))
        d_period = int(cfg.get("d_period", 3))
        oversold = float(cfg.get("oversold", 20.0))
        overbought = float(cfg.get("overbought", 80.0))
        
        # 1) Гарантируем наличие нужных индикаторов
        stoch_k_col, stoch_d_col = self._stoch_cols(k_period, d_period)
        if not all(col in df.columns for col in [stoch_k_col, stoch_d_col]):
            try:
                self._ensure_required_stochastic(df, k_period, d_period)
            except Exception as e:
                # не роняем пайплайн
                self.logger.error(f"[STOCHASTIC] Failed to ensure indicators via Analytic: {e}")
        
        if not all(col in df.columns for col in [stoch_k_col, stoch_d_col]):
            # всё ещё нет — отдаём 0 и заполняем orders_stochastic нулями
            self._ensure_orders_col(df)
            df["orders_stochastic"] = 0.0
            return 0
        
        # Получаем значения %K и %D
        stoch_k = pd.to_numeric(df[stoch_k_col], errors="coerce")
        stoch_d = pd.to_numeric(df[stoch_d_col], errors="coerce")
        
        if len(stoch_k) < max(2, k_period + d_period):
            self._ensure_orders_col(df)
            df["orders_stochastic"] = 0.0
            return 0
        
        # Предыдущие значения для определения пересечений
        prev_k = stoch_k.shift(1)
        prev_d = stoch_d.shift(1)
        
        # BUY: %K пересекает %D снизу вверх в зоне перепроданности
        buy_cross = (prev_k <= prev_d) & (stoch_k > stoch_d) & (stoch_k < oversold)
        
        # SELL: %K пересекает %D сверху вниз в зоне перекупленности
        sell_cross = (prev_k >= prev_d) & (stoch_k < stoch_d) & (stoch_k > overbought)
        
        # Генерируем сигналы
        signals = np.zeros(len(df), dtype=int)
        
        # Приоритет SELL при одновременном пересечении
        sell_mask = sell_cross.fillna(False).to_numpy()
        buy_mask = buy_cross.fillna(False).to_numpy() & (~sell_mask)
        
        signals[sell_mask] = -1
        signals[buy_mask] = 1
        
        # Сохраняем сигналы в DataFrame
        self._ensure_orders_col(df)
        df["orders_stochastic"] = signals.astype(float)
        
        # Возвращаем последний сигнал
        last_sig = int(signals[-1]) if pd.notna(stoch_k.iloc[-1]) and pd.notna(stoch_d.iloc[-1]) else 0
        return last_sig


if __name__ == "__main__":
    from CORE.log_manager import Logger
    logger = Logger(name="STOCHASTIC", tag="[STOCHASTIC]", logfile="LOGS/stochastic.log", console=True).get_logger()
    logger.info("StochasticOscillatorStrategy module OK")
