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
    Stochastic Oscillator Strategy:
      • BUY  (+1) при пересечении %K выше %D в зоне перепроданности (<20);
      • SELL (-1) при пересечении %K ниже %D в зоне перекупленности (>80);
      • При одновременном пересечении — приоритет SELL.
      
    Колонки Stochastic: 'stoch_k', 'stoch_d' при стандартных параметрах,
    иначе 'stoch_k_{k_period}_{d_period}', 'stoch_d_{k_period}_{d_period}'.
    """
    
    def __init__(
        self,
        df: Optional[pd.DataFrame] = None,
        data_name: Optional[str] = None,
        output_file: str = "anal.csv",
        save_after_init: bool = True,
        **params: Any,
    ) -> None:
        # объявляем зависимость от Stochastic Oscillator
        super().__init__(name="StochasticOscillator", indicators=["stochastic_oscillator"], **params)
        
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
            "stochastic_oscillator": {
                "k_period": 14,
                "d_period": 3,
                "oversold": 20.0,
                "overbought": 80.0
            }
        }
    
    # ----- helpers -----
    @staticmethod
    def _stoch_cols(k_period: int, d_period: int) -> tuple[str, str]:
        """Имена колонок Stochastic Oscillator согласованы с Indicators"""
        is_default = (k_period == 14 and d_period == 3)
        if is_default:
            return "stoch_k", "stoch_d"
        else:
            return f"stoch_k_{k_period}_{d_period}", f"stoch_d_{k_period}_{d_period}"
    
    @staticmethod
    def _ensure_orders_col(df: pd.DataFrame) -> None:
        """Создаем колонку для сигналов стратегии"""
        if "orders_stochastic" not in df.columns:
            df.insert(len(df.columns), "orders_stochastic", pd.Series(index=df.index, dtype="float64"))
    
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
        return "STOCHASTIC"
    
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
                print(f"[STOCHASTIC] Failed to ensure indicators via Analytic: {e}")
        
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
    print("StochasticOscillatorStrategy module OK")
