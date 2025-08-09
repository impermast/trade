# STRATEGY/rsi.py
import os
import sys
from typing import Any, Dict, Optional

import numpy as np
import pandas as pd

# allow local imports when running as a script
sys.path.append(os.path.abspath("."))

from STRATEGY.base import BaseStrategy  # type: ignore
# ВАЖНО: Analytic импортируем лениво внутри методов, чтобы избежать циклов.


class RSIonly_Strategy(BaseStrategy):
    """
    RSI-only:
      • SELL (-1) при пересечении ВВЕРХ уровня upper (например, 70) — снизу вверх;
      • BUY  (+1) при пересечении ВНИЗ уровня lower (например, 30) — сверху вниз;
      • При «телепорте» одновременно — приоритет SELL.

    Колонка RSI: 'rsi' при period=14, иначе 'rsi_{period}'.
    Если нужных колонок нет — стратегия сама запросит их расчёт у Analytic (как XGB).
    """

    def __init__(
        self,
        df: Optional[pd.DataFrame] = None,
        data_name: Optional[str] = None,
        output_file: str = "anal.csv",
        save_after_init: bool = True,
        **params: Any,
    ) -> None:
        # объявляем зависимость от RSI (Analytic знает, что считать)
        super().__init__(name="RSIOnly", indicators=["rsi"], **params)

        # Параметры для поведения "как у XGB"
        self._init_df = df
        self._init_data_name = data_name
        self._init_output_file = output_file
        self._save_after_init = bool(save_after_init)

        # Если передали df на вход — сразу обеспечим индикаторы
        if self._init_df is not None:
            self._ensure_indicators_and_save(self._init_df)

    def default_params(self) -> Dict[str, Dict[str, Any]]:
        return {"rsi": {"period": 14, "lower": 30.0, "upper": 70.0}}

    # ----- helpers -----
    @staticmethod
    def _rsi_col(period: int) -> str:
        # Имена согласованы с Indicators: rsi или rsi_{period}
        return "rsi" if int(period) == 14 else f"rsi_{int(period)}"

    @staticmethod
    def _ensure_orders_col(df: pd.DataFrame) -> None:
        if "orders_rsi" not in df.columns:
            df.insert(len(df.columns), "orders_rsi", pd.Series(index=df.index, dtype="float64"))

    def _resolve_data_name(self, df: pd.DataFrame) -> str:
        if self._init_data_name:
            return self._init_data_name
        # Пытаемся вытащить symbol/asset/ticker для корректного имени файла аналитики
        for col in ("symbol", "asset", "ticker"):
            if col in df.columns and isinstance(df[col].iloc[0], str):
                raw = str(df[col].iloc[0])
                token = raw.split("/")[0].split("-")[0]
                return token.upper()
        return "RSI"

    def _ensure_indicators_and_save(self, df: pd.DataFrame) -> None:
        """
        Полный путь как у XGB: берём (indicators, stratparams) из check_indicators()
        и просим Analytic посчитать необходимые индикаторы. При необходимости сохраняем CSV.
        """
        # ленивый импорт, чтобы не словить циклический
        from BOTS.analbot import Analytic  # type: ignore

        indicators, stratparams = self.check_indicators()
        data_name = self._resolve_data_name(df)
        anal = Analytic(df=df, data_name=data_name, output_file=self._init_output_file)
        # для RSI параллельность не критична, но оставим единообразно
        anal.make_calc(indicators=indicators, stratparams=stratparams, parallel=False)
        if self._save_after_init:
            # интерфейс Analytic не меняем; это внутренний метод сохранения
            anal._save_results_to_csv()  # noqa: SLF001

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
                print(f"[RSI] Failed to ensure indicators via Analytic: {e}")

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
    print("RSIonly_Strategy module OK")
