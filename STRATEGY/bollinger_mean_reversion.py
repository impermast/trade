# STRATEGY/bollinger_mean_reversion.py
import os
import sys
from typing import Any, Dict, Optional

import numpy as np
import pandas as pd

# allow local imports when running as a script
sys.path.append(os.path.abspath("."))

from STRATEGY.base import BaseStrategy  # type: ignore


class BollingerMeanReversionStrategy(BaseStrategy):
    """
    Стратегия на основе отскока от полос Боллинджера.
    
    Генерирует сигналы на покупку при касании нижней полосы (перепроданность),
    и сигналы на продажу при касании верхней полосы (перекупленность).
    """
    
    def __init__(self, df: Optional[pd.DataFrame] = None, params: Optional[Dict[str, Any]] = None):
        super().__init__(df=df, params=params, name="Bollinger Mean Reversion Strategy", indicators=["bollinger_bands"])
        # Setup logger
        from CORE.log_manager import Logger
        self.logger = Logger(name="BOLLINGER", tag="[BOLLINGER]", logfile="LOGS/bollinger.log", console=False).get_logger()
    
    def default_params(self) -> Dict[str, Dict[str, Any]]:
        return {
            "bollinger_bands": {
                "period": 20,
                "window_dev": 2.0
            }
        }
    
    def _ensure_orders_col(self, df: pd.DataFrame) -> None:
        """Создаем колонку для сигналов стратегии"""
        if "orders_bollinger" not in df.columns:
            df.insert(len(df.columns), "orders_bollinger", pd.Series(index=df.index, dtype="float64"))
    
    # ----- helpers -----
    @staticmethod
    def _bb_cols(period: int) -> tuple[str, str, str]:
        """Имена колонок Bollinger Bands согласованы с Indicators"""
        is_default = (period == 20)
        if is_default:
            return "bb_h", "bb_m", "bb_l"
        else:
            return f"bb_h_{period}", f"bb_m_{period}", f"bb_l_{period}"
    
    def _ensure_required_bollinger(self, df: pd.DataFrame, period: int) -> None:
        """Узко: если нужных колонок Bollinger Bands нет — считаем через Analytic"""
        want_cols = self._bb_cols(period)
        if all(col in df.columns for col in want_cols):
            return
        self._ensure_indicators_and_save(df)
    
    def _is_touching_band(self, price: float, band_value: float, tolerance: float = 0.001) -> bool:
        """Проверяет, касается ли цена полосы Боллинджера с заданной точностью"""
        return abs(price - band_value) <= tolerance
    
    def _is_below_band(self, price: float, band_value: float) -> bool:
        """Проверяет, находится ли цена ниже полосы Боллинджера"""
        return price <= band_value
    
    def _is_above_band(self, price: float, band_value: float) -> bool:
        """Проверяет, находится ли цена выше полосы Боллинджера"""
        return price >= band_value
    
    # ----- public -----
    def get_signals(self, df: pd.DataFrame) -> int:
        """Генерирует торговые сигналы на основе касаний полос Боллинджера"""
        cfg = self.params.get("bollinger_bands", {})
        period = int(cfg.get("period", 20))
        window_dev = float(cfg.get("window_dev", 2.0))
        
        # 1) Гарантируем наличие нужных индикаторов
        bb_h_col, bb_m_col, bb_l_col = self._bb_cols(period)
        if not all(col in df.columns for col in [bb_h_col, bb_m_col, bb_l_col]):
            try:
                self._ensure_required_bollinger(df, period)
            except Exception as e:
                # не роняем пайплайн
                self.logger.error(f"[BOLLINGER] Failed to ensure indicators via Analytic: {e}")
        
        if not all(col in df.columns for col in [bb_h_col, bb_m_col, bb_l_col]):
            # всё ещё нет — отдаём 0 и заполняем orders_bollinger нулями
            self._ensure_orders_col(df)
            df["orders_bollinger"] = 0.0
            return 0
        
        # Получаем значения полос Боллинджера
        bb_high = pd.to_numeric(df[bb_h_col], errors="coerce")
        bb_middle = pd.to_numeric(df[bb_m_col], errors="coerce")
        bb_low = pd.to_numeric(df[bb_l_col], errors="coerce")
        
        if len(bb_high) < max(2, period + 1):
            self._ensure_orders_col(df)
            df["orders_bollinger"] = 0.0
            return 0
        
        # Получаем цены (используем close, если есть, иначе high)
        if "close" in df.columns:
            prices = pd.to_numeric(df["close"], errors="coerce")
        elif "high" in df.columns:
            prices = pd.to_numeric(df["high"], errors="coerce")
        else:
            # Если нет цен, используем среднюю полосу как приближение
            prices = bb_middle
        
        if prices.isna().all():
            self._ensure_orders_col(df)
            df["orders_bollinger"] = 0.0
            return 0
        
        # Генерируем сигналы
        signals = np.zeros(len(df), dtype=int)
        
        for i in range(1, len(df)):  # Начинаем с 1, чтобы иметь предыдущие значения
            if pd.isna(prices.iloc[i]) or pd.isna(bb_high.iloc[i]) or pd.isna(bb_low.iloc[i]):
                continue
            
            current_price = prices.iloc[i]
            current_bb_high = bb_high.iloc[i]
            current_bb_low = bb_low.iloc[i]
            
            # BUY: цена касается или пробивает нижнюю полосу (перепроданность)
            buy_signal = self._is_below_band(current_price, current_bb_low)
            
            # SELL: цена касается или пробивает верхнюю полосу (перекупленность)
            sell_signal = self._is_above_band(current_price, current_bb_high)
            
            # Приоритет SELL при одновременном касании обеих полос
            if sell_signal:
                signals[i] = -1
            elif buy_signal:
                signals[i] = 1
        
        # Сохраняем сигналы в DataFrame
        self._ensure_orders_col(df)
        df["orders_bollinger"] = signals.astype(float)
        
        # Возвращаем последний сигнал
        last_sig = int(signals[-1]) if len(signals) > 0 else 0
        return last_sig


if __name__ == "__main__":
    from CORE.log_manager import Logger
    logger = Logger(name="BOLLINGER", tag="[BOLLINGER]", logfile="LOGS/bollinger.log", console=True).get_logger()
    logger.info("BollingerMeanReversionStrategy module OK")
