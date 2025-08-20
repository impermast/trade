# STRATEGY/XGBstrategy.py
import os
import sys
import time
from functools import lru_cache
from typing import Any, Dict, List, Optional, Tuple

import joblib
import numpy as np
import pandas as pd

# allow local imports when running as a script
sys.path.append(os.path.abspath("."))

from STRATEGY.base import BaseStrategy  # type: ignore


class XGBStrategy(BaseStrategy):
    """
    XGBoost-based trading strategy.
    
    Uses machine learning model to predict price movements and generate trading signals.
    """
    
    def __init__(self, df: Optional[pd.DataFrame] = None, params: Optional[Dict[str, Any]] = None):
        super().__init__(df=df, params=params, name="XGB Strategy", 
                        indicators=["rsi", "ema", "sma", "macd", "bollinger_bands"])
        # Setup logger
        from CORE.log_manager import Logger
        self.logger = Logger(name="XGB", tag="[XGB]", logfile="LOGS/xgb.log", console=False).get_logger()
        
        # Define features and batch size
        self.features = ["rsi", "ema", "sma", "macd", "bb_h", "bb_l"]
        self.batch_size = 100
        
        # Load XGB model and features
        self.model = self._load_model()
        self.model_features = self._load_features()

    def _load_model(self):
        """Загружает обученную XGB модель"""
        try:
            model_path = os.path.join("STRATEGY", "predicter", "xgb_model_multi.joblib")
            if os.path.exists(model_path):
                model = joblib.load(model_path)
                self.logger.info(f"[XGB] Модель успешно загружена из {model_path}")
                return model
            else:
                self.logger.error(f"[XGB] Файл модели не найден: {model_path}")
                return None
        except Exception as e:
            self.logger.error(f"[XGB] Ошибка загрузки модели: {e}")
            return None

    def _load_features(self):
        """Загружает список признаков модели"""
        try:
            features_path = os.path.join("STRATEGY", "predicter", "xgb_model_features.joblib")
            if os.path.exists(features_path):
                features = joblib.load(features_path)
                self.logger.info(f"[XGB] Признаки модели загружены: {features}")
                # Обновляем self.features для совместимости
                if isinstance(features, list) and len(features) > 0:
                    self.features = features
                return features
            else:
                self.logger.warning(f"[XGB] Файл признаков не найден: {features_path}")
                return self.features  # возвращаем значения по умолчанию
        except Exception as e:
            self.logger.error(f"[XGB] Ошибка загрузки признаков: {e}")
            return self.features  # возвращаем значения по умолчанию

    # ----- BaseStrategy required -----
    def default_params(self) -> Dict[str, Dict[str, Any]]:
        return {
            "rsi": {"period": 14},
            "ema": {"period": 10},
            "sma": {"period": 10},
            "macd": {"window_fast": 12, "window_slow": 26, "window_sign": 9},
            "bollinger_bands": {"period": 20, "window_dev": 2},
        }

    def _ensure_orders_col(self, df: pd.DataFrame) -> None:
        """Ensure signal columns exist for this strategy."""
        if "orders_xgb" not in df.columns:
            df.insert(len(df.columns), "orders_xgb", pd.Series(index=df.index, dtype="float64"))
        if "xgb_amount" not in df.columns:
            df.insert(len(df.columns), "xgb_amount", pd.Series(index=df.index, dtype="float64"))
        if "xgb_signal" not in df.columns:  # legacy alias for UI/backward-compat
            df.insert(len(df.columns), "xgb_signal", pd.Series(index=df.index, dtype="float64"))

    # ----- helpers -----
    def _have_all_features(self, row: pd.Series) -> bool:
        return all((f in row) and pd.notna(row[f]) for f in self.features)

    def _map_features(self, row: pd.Series) -> Tuple[float, ...]:
        """Преобразует признаки из DataFrame в правильный формат для модели"""
        feature_values = []
        
        for feature in self.features:
            if feature in row and pd.notna(row[feature]):
                feature_values.append(float(row[feature]))
            elif feature == "bb_h" and "BBU_20_2.0" in row:
                # Bollinger Upper Band
                feature_values.append(float(row["BBU_20_2.0"]))
            elif feature == "bb_l" and "BBL_20_2.0" in row:
                # Bollinger Lower Band
                feature_values.append(float(row["BBL_20_2.0"]))
            elif feature == "rsi" and "RSI_14" in row:
                # RSI with different period naming
                feature_values.append(float(row["RSI_14"]))
            elif feature == "ema" and "EMA_10" in row:
                # EMA with different period naming
                feature_values.append(float(row["EMA_10"]))
            elif feature == "sma" and "SMA_10" in row:
                # SMA with different period naming
                feature_values.append(float(row["SMA_10"]))
            elif feature == "macd" and "MACD_12_26_9" in row:
                # MACD with specific parameters
                feature_values.append(float(row["MACD_12_26_9"]))
            else:
                # Если признак не найден, используем 0.0
                self.logger.warning(f"[XGB] Признак {feature} не найден в данных, используем 0.0")
                feature_values.append(0.0)
        
        return tuple(feature_values)

    def _have_all_features_mapped(self, row: pd.Series) -> bool:
        """Проверяет наличие всех признаков с учётом mapping"""
        try:
            mapped_features = self._map_features(row)
            # Проверяем, что все значения не NaN и не inf
            return all(isinstance(val, (int, float)) and not (np.isnan(val) or np.isinf(val)) 
                      for val in mapped_features)
        except Exception:
            return False

    def _predict(self, feature_tuple: Tuple[float, ...]) -> Tuple[int, float]:
        """Return (signal, amount). Signal in {-1,0,1}."""
        try:
            X = np.array(feature_tuple, dtype=float).reshape(1, -1)
            y = self.model.predict(X)

            # classifier
            if hasattr(self.model, "classes_") or hasattr(self.model, "n_classes_"):
                cls = int(np.atleast_1d(y)[0])
                # Исправленный mapping: учитываем, что в bdt.py используется 1=buy, 2=sell
                if cls == 1:
                    return 1, 0.0  # BUY
                elif cls == 2:
                    return -1, 0.0  # SELL (исправлено с 2 на -1)
                else:
                    return 0, 0.0  # HOLD

            # regressor - многомерный выход [signal, amount]
            y0 = np.atleast_2d(y)[0]
            if len(y0) >= 2:
                signal_raw, amount = float(y0[0]), float(y0[1])
                
                # Преобразуем сигнал в дискретные значения
                if signal_raw > 0.5:
                    sig = 1  # BUY
                elif signal_raw < -0.5:
                    sig = -1  # SELL
                else:
                    sig = 0  # HOLD
                    
                return sig, max(0.0, float(amount))
            else:
                # Одномерный выход - только сигнал
                signal_raw = float(y0[0])
                if signal_raw > 0.5:
                    return 1, 0.0  # BUY
                elif signal_raw < -0.5:
                    return -1, 0.0  # SELL
                else:
                    return 0, 0.0  # HOLD
                    
        except Exception as e:
            self.logger.error(f"[XGB] Ошибка предсказания: {e}")
            return 0, 0.0  # Возвращаем HOLD в случае ошибки

    def _batch_predict(self, X: np.ndarray) -> List[Tuple[int, float]]:
        try:
            y = self.model.predict(X)
            out: List[Tuple[int, float]] = []
            
            # classifier
            if hasattr(self.model, "classes_") or hasattr(self.model, "n_classes_"):
                arr = np.atleast_1d(y)
                for cls in arr:
                    cls = int(cls)
                    # Исправленный mapping: 1=buy, 2=sell -> 1, -1
                    if cls == 1:
                        out.append((-1, 0.0))  # BUY
                    elif cls == 2:
                        out.append((1, 0.0))  # SELL
                    else:
                        out.append((0, 0.0))  # HOLD
                return out
                
            # regressor
            arr2d = np.atleast_2d(y)
            for row in arr2d:
                if hasattr(row, "__len__") and len(row) >= 2:
                    signal_raw = float(row[0])
                    amount = float(row[1])
                    
                    # Преобразуем в дискретные сигналы
                    if signal_raw > 0.5:
                        sig = 1  # BUY
                    elif signal_raw < -0.5:
                        sig = -1  # SELL
                    else:
                        sig = 0  # HOLD
                        
                    out.append((sig, max(0.0, amount)))
                else:
                    signal_raw = float(row[0])
                    if signal_raw > 0.5:
                        out.append((1, 0.0))  # BUY
                    elif signal_raw < -0.5:
                        out.append((-1, 0.0))  # SELL
                    else:
                        out.append((0, 0.0))  # HOLD
            return out
            
        except Exception as e:
            self.logger.error(f"[XGB] Ошибка batch предсказания: {e}")
            return [(0, 0.0)] * len(X)  # Возвращаем HOLD для всех записей

    def _cached_predict(self, feature_tuple: Tuple[float, ...]) -> Tuple[int, float]:
        """Cached prediction for single feature tuple."""
        if self.model is None:
            # Return default values if model is not loaded
            return 0, 0.0
        return self._predict(feature_tuple)

    def _try_ensure_features(self, df: pd.DataFrame) -> None:
        """If features are missing on prev bar, recalc via Analytic."""
        if len(df) < 2:
            return
        prev = df.iloc[-2]
        if self._have_all_features(prev):
            return
        missing = [f for f in self.features if (f not in prev) or pd.isna(prev[f])]
        self.logger.warning(f"[XGB] Missing features on prev bar, recalculating via Analytic: {missing}")
        self._ensure_indicators_and_save(df)

    def _set_signal(self, df: pd.DataFrame, idx: int, sig: int, amt: float, overwrite: bool = False) -> None:
        """Unified write path to avoid history overwrite."""
        self._ensure_orders_col(df)
        if not overwrite and idx in df.index:
            # do not overwrite non-NaN history
            existing = df.at[idx, "orders_xgb"]
            if pd.notna(existing):
                return
        df.at[idx, "orders_xgb"] = int(sig)
        df.at[idx, "xgb_signal"] = int(sig)  # legacy alias
        df.at[idx, "xgb_amount"] = float(amt)

    # ----- public -----
    def get_signals(self, df: pd.DataFrame) -> int:
        """
        Возвращает сигнал для последнего бара.
        Историю не перезаписывает; последний бар всегда обновляет.
        """
        if df.shape[0] < 2:
            return 0

        self._ensure_orders_col(df)

        # Ensure features (используем новый метод с mapping)
        if not self._have_all_features_mapped(df.iloc[-2]):
            self._try_ensure_features(df)
        if not self._have_all_features_mapped(df.iloc[-2]):
            # still missing
            self.logger.warning("[XGB] Не удалось получить все необходимые признаки")
            return 0

        t0 = time.time()
        # Fill history in batches without overwriting
        n = df.shape[0]
        if n - 1 > self.batch_size:
            # up to the penultimate bar
            start_idx = 0
            end_idx_exclusive = n - 1
            i = start_idx
            while i < end_idx_exclusive:
                j = min(i + self.batch_size, end_idx_exclusive)
                batch = df.iloc[i:j]
                valid_rows: List[Tuple[float, ...]] = []
                valid_idx: List[int] = []
                for ridx, row in batch.iterrows():
                    if self._have_all_features_mapped(row):
                        valid_rows.append(self._map_features(row))
                        valid_idx.append(ridx)
                if valid_rows:
                    X = np.array(valid_rows, dtype=float)
                    preds = self._batch_predict(X)
                    for ridx, (sig, amt) in zip(valid_idx, preds):
                        next_i = ridx + 1
                        if next_i < n:
                            self._set_signal(df, next_i, int(sig), float(amt), overwrite=False)
                i = j
            # if last already predicted, use it
            last_val = df.iloc[-1].get("orders_xgb", np.nan)
            if pd.notna(last_val):
                self.logger.info(f"[XGB] batch filled in {time.time()-t0:.2f}s")
                return int(last_val)

        # Single-step latest prediction from prev bar into last bar
        prev = df.iloc[-2]
        feature_tuple = self._map_features(prev)
        signal, amount = self._cached_predict(feature_tuple)
        self._set_signal(df, df.index[-1], int(signal), float(amount), overwrite=True)
        self.logger.info(f"[XGB] single prediction in {time.time()-t0:.2f}s, signal={signal}")
        return int(signal)


if __name__ == "__main__":
    # basic smoke-test
    from CORE.log_manager import Logger
    logger = Logger(name="XGB", tag="[XGB]", logfile="LOGS/xgb.log", console=True).get_logger()
    logger.info("XGBStrategy module OK")
