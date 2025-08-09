# STRATEGY/XGBstrategy.py

import os
import sys
import pandas as pd
import numpy as np
import joblib
import time
from functools import lru_cache
from xgboost import XGBRegressor
from typing import Dict, Any, List, Tuple, Optional

sys.path.append(os.path.abspath("."))
from STRATEGY.base import BaseStrategy
from BOTS.analbot import Analytic  # type: ignore


class XGBStrategy(BaseStrategy):
    """
    Стратегия на XGBoost, предсказывает (signal, amount).

    Важно: если при инициализации передать df и data_name, то стратегия СРАЗУ
    запросит у аналитики расчет недостающих индикаторов и сохранит результат
    в DATA/<data_name>_<output_file>.
    """

    _model_cache: Dict[str, Any] = {}
    _features_cache: Dict[str, List[str]] = {}

    def __init__(
        self,
        model_path: str = "STRATEGY/predicter/xgb_model_multi.joblib",
        features_path: str = "STRATEGY/predicter/xgb_model_features.joblib",
        slippage: float = 0.0005,
        batch_size: int = 100,
        prediction_cache_size: int = 1024,
        use_quantization: bool = False,
        # новенькое:
        df: Optional[pd.DataFrame] = None,          # если передан — сразу считаем индикаторы
        data_name: Optional[str] = None,            # имя для файла аналитики
        output_file: str = "anal.csv",              # суффикс файла аналитики
        save_after_init: bool = True,               # сохранять CSV после досчета
        **params: Dict[str, Any],
    ):
        # Индикаторы синхронизированы с BOTS/indicators.py
        super().__init__(
            name="XGBStrategy",
            indicators=["sma", "ema", "rsi", "macd", "bollinger_bands"],
            **params,
        )

        self.batch_size = batch_size
        self.prediction_cache_size = prediction_cache_size
        self.use_quantization = use_quantization
        self.slippage = slippage

        # где сохранять аналитику, если нас попросили это делать в __init__
        self._init_df: Optional[pd.DataFrame] = df
        self._init_data_name: Optional[str] = data_name
        self._init_output_file: str = output_file
        self._save_after_init: bool = save_after_init

        # Модель с кешем
        if model_path in self._model_cache:
            self.model = self._model_cache[model_path]
        else:
            start = time.time()
            self.model = joblib.load(model_path)
            if use_quantization:
                try:
                    model_json = self.model.get_booster().save_config()
                    self.model = XGBRegressor()
                    self.model.get_booster().load_config(model_json)
                    print(f"Model quantized in {time.time() - start:.2f}s")
                except Exception as e:
                    print(f"Quantization error: {e}")
            self._model_cache[model_path] = self.model
            print(f"Model loaded in {time.time() - start:.2f}s")

        # Список фич модели с кешем
        if features_path in self._features_cache:
            self.features = self._features_cache[features_path]
        else:
            self.features = joblib.load(features_path)
            self._features_cache[features_path] = self.features

        # Кеш предсказаний
        self._cached_predict = lru_cache(maxsize=prediction_cache_size)(self._predict)

        # Главное: если нам дали df на входе — сразу считаем и обновляем CSV аналитики
        if self._init_df is not None:
            self._ensure_indicators_and_save(self._init_df)

    def default_params(self) -> Dict[str, Any]:
        # дефолты под имена без суффиксов, которые обычно ждёт модель
        return {
            "rsi": {"period": 14},
            "ema": {"period": 10},
            "sma": {"period": 10},
            "macd": {"window_fast": 12, "window_slow": 26, "window_sign": 9},
            "bollinger_bands": {"period": 20, "window_dev": 2},
        }

    # ------------------------ Внутреннее ------------------------

    def _resolve_data_name(self, df: pd.DataFrame) -> str:
        if self._init_data_name:
            return self._init_data_name
        for col in ("symbol", "asset", "ticker"):
            if col in df.columns and isinstance(df[col].iloc[0], str):
                raw = str(df[col].iloc[0])
                token = raw.split("/")[0].split("-")[0]
                return token.upper()
        return "XGB"

    def _ensure_indicators_and_save(self, df: pd.DataFrame) -> None:
        """
        Досчитывает недостающие индикаторы через Analytic и при необходимости сохраняет CSV.
        """
        indicators, stratparams = self.check_indicators()
        data_name = self._resolve_data_name(df)

        anal = Analytic(df=df, data_name=data_name, output_file=self._init_output_file)
        # Считаем всё нужное; Indicators сам проверит, чего не хватает
        anal.make_calc(indicators, stratparams, parallel=True)

        if self._save_after_init:
            # приватный метод, да. переживем.
            anal._save_results_to_csv()  # noqa: SLF001

    def _ensure_signal_columns(self, df: pd.DataFrame) -> None:
        """
        Создаёт столбцы для вывода предсказаний, если их нет.
        Никаких кортежей, только отдельные колонки.
        """
        if "xgb_signal" not in df.columns:
            df.insert(len(df.columns), "xgb_signal", pd.Series(index=df.index, dtype="float64"))
        if "xgb_amount" not in df.columns:
            df.insert(len(df.columns), "xgb_amount", pd.Series(index=df.index, dtype="float64"))

    def _predict(self, feature_tuple: Tuple[float, ...]) -> Tuple[int, float]:
        X = np.array(feature_tuple).reshape(1, -1)
        y = self.model.predict(X)[0]
        if hasattr(y, "__len__") and len(y) >= 2:
            signal_raw, amount = float(y[0]), float(y[1])
        else:
            signal_raw, amount = float(y), 0.0
        signal = int(round(signal_raw))
        return signal, amount

    def _batch_predict(self, X: np.ndarray) -> List[Tuple[int, float]]:
        y = self.model.predict(X)
        out: List[Tuple[int, float]] = []
        for row in np.atleast_2d(y):
            if hasattr(row, "__len__") and len(row) >= 2:
                out.append((int(round(float(row[0]))), float(row[1])))
            else:
                out.append((int(round(float(row))), 0.0))
        return out

    # ------------------------ Публичное ------------------------

    def get_signals(self, df: pd.DataFrame) -> int:
        """
        Прогноз по последней свече. Здесь НИЧЕГО не считаем и не сохраняем:
        индикаторы должны быть уже посчитаны либо в __init__ (если передан df),
        либо раньше по твоему пайплайну.
        """
        if df.shape[0] < 2:
            return 0

        self._ensure_signal_columns(df)

        start = time.time()
        use_batch = df.shape[0] > self.batch_size

        if use_batch:
            for i in range(0, df.shape[0] - 1, self.batch_size):
                end = min(i + self.batch_size, df.shape[0] - 1)
                batch = df.iloc[i:end]

                valid_rows = []
                valid_idx = []
                for idx, row in batch.iterrows():
                    if all((f in row) and pd.notna(row[f]) for f in self.features):
                        valid_rows.append(tuple(float(row[f]) for f in self.features))
                        valid_idx.append(idx)
                if not valid_rows:
                    continue

                X = np.array(valid_rows, dtype=float)
                preds = self._batch_predict(X)
                for idx, (sig, amt) in zip(valid_idx, preds):
                    next_idx = idx + 1
                    if next_idx < len(df):
                        df.at[next_idx, "xgb_signal"] = int(sig)
                        df.at[next_idx, "xgb_amount"] = float(amt)

            last_sig = df.iloc[-1]["xgb_signal"]
            if pd.notna(last_sig):
                print(f"Batch prediction in {time.time() - start:.2f}s")
                return int(last_sig)
            print("No valid latest prediction")
            return 0

        # одиночный режим
        prev = df.iloc[-2]
        next_open = df.iloc[-1].get("open", np.nan)

        if not all((f in prev) and pd.notna(prev[f]) for f in self.features):
            missing = [f for f in self.features if (f not in prev) or pd.isna(prev[f])]
            print(f"Missing features for XGB: {missing}")
            return 0

        feature_tuple = tuple(float(prev[f]) for f in self.features)
        signal, amount = self._cached_predict(feature_tuple)

        _exec_price = (float(next_open) if pd.notna(next_open) else np.nan) * (1 + self.slippage)

        # пишем по отдельности, без кортежей
        df.at[df.index[-1], "xgb_signal"] = int(signal)
        df.at[df.index[-1], "xgb_amount"] = float(amount)

        print(f"Single prediction in {time.time() - start:.2f}s")
        return int(signal)


if __name__ == "__main__":
    # Никаких расчетов индикаторов здесь. Только сухая инициализация для проверки.
    strat = XGBStrategy(
        ema={"period": 10},
        sma={"period": 10},
        rsi={"period": 14},
        macd={"window_fast": 12, "window_slow": 26, "window_sign": 9},
        bollinger_bands={"period": 20, "window_dev": 2},
    )
    print(strat)

    df = pd.read_csv("DATA/BTCUSDT_1h.csv")
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    xgb = XGBStrategy(df=df, data_name="BTCUSDT_1h", output_file="anal.csv")
