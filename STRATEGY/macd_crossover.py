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
    MACD Crossover Strategy:
      • BUY  (+1) при пересечении MACD линии ВВЕРХ сигнальной линии (снизу вверх);
      • SELL (-1) при пересечении MACD линии ВНИЗ сигнальной линии (сверху вниз);
      • При одновременном пересечении — приоритет SELL.
      
    Колонки MACD: 'macd', 'macd_signal', 'macd_histogram' при стандартных параметрах,
    иначе 'macd_{fast}_{slow}', 'macd_signal_{fast}_{slow}_{signal}', 'macd_histogram_{fast}_{slow}_{signal}'.
    """
    
    def __init__(
        self,
        df: Optional[pd.DataFrame] = None,
        data_name: Optional[str] = None,
        output_file: str = "anal.csv",
        save_after_init: bool = True,
        **params: Any,
    ) -> None:
        # объявляем зависимость от MACD
        super().__init__(name="MACDCrossover", indicators=["macd"], **params)
        
        # Параметры для поведения "как у других стратегий"
        self._init_df = df
        self._init_data_name = data_name
        self._init_output_file = output_file
        self._save_after_init = bool(save_after_init)
        
        # Если передали df на вход — сразу обеспечим индикаторы
        if self._init_df is not None:
            self._ensure_indicators_and_save(self._init_df)
    
    def default_params(self) -> Dict[str, Dict[str, Any]]:
        return {
            "macd": {
                "window_fast": 12,
                "window_slow": 26,
                "window_sign": 9
            }
        }
    
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
    
    @staticmethod
    def _ensure_orders_col(df: pd.DataFrame) -> None:
        """Создаем колонку для сигналов стратегии"""
        if "orders_macd" not in df.columns:
            df.insert(len(df.columns), "orders_macd", pd.Series(index=df.index, dtype="float64"))
    
    def _resolve_data_name(self, df: pd.DataFrame) -> str:
        """Определяем имя для файла аналитики"""
        if self._init_data_name:
            return self._init_data_name
        # Пытаемся вытащить symbol/asset/ticker для корректного имени файла
        for col in ("symbol", "asset", "ticker"):
            if col in df.columns and isinstance(df[col].iloc[0], str):
                raw = str(df[col].iloc[0])
                token = raw.split("/")[0].split("-")[0]
                return token.upper()
        return "MACD"
    
    def _ensure_indicators_and_save(self, df: pd.DataFrame) -> None:
        """Полный путь как у других стратегий: берём (indicators, stratparams) из check_indicators()
        и просим Analytic посчитать необходимые индикаторы. При необходимости сохраняем CSV."""
        # ленивый импорт, чтобы не словить циклический
        from BOTS.analbot import Analytic  # type: ignore
        
        indicators, stratparams = self.check_indicators()
        data_name = self._resolve_data_name(df)
        anal = Analytic(df=df, data_name=data_name, output_file=self._init_output_file)
        anal.make_calc(indicators=indicators, stratparams=stratparams, parallel=False)
        if self._save_after_init:
            anal._save_results_to_csv()  # noqa: SLF001
    
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
                print(f"[MACD] Failed to ensure indicators via Analytic: {e}")
        
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
    print("MACDCrossoverStrategy module OK")
