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
        
        # Initialize model (placeholder for now)
        self.model = None

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

    def _predict(self, feature_tuple: Tuple[float, ...]) -> Tuple[int, float]:
        """Return (signal, amount). Signal in {-1,0,1}."""
        X = np.array(feature_tuple, dtype=float).reshape(1, -1)
        y = self.model.predict(X)

        # classifier
        if hasattr(self.model, "classes_") or hasattr(self.model, "n_classes_"):
            cls = int(np.atleast_1d(y)[0])
            # normalize {0,1,2} -> {-1,0,1}
            if cls in (0, 1, 2):
                mapping = {0: -1, 1: 0, 2: 1}
                return mapping.get(cls, 0), 0.0
            # otherwise sign
            return 1 if cls > 0 else (-1 if cls < 0 else 0), 0.0

        # regressor
        y0 = np.atleast_2d(y)[0]
        if len(y0) >= 2:
            signal_raw, amount = float(y0[0]), float(y0[1])
        else:
            signal_raw, amount = float(y0[0]), 0.0
        sig = int(round(signal_raw))
        sig = 1 if sig > 0 else (-1 if sig < 0 else 0)
        return sig, float(amount)

    def _batch_predict(self, X: np.ndarray) -> List[Tuple[int, float]]:
        y = self.model.predict(X)
        out: List[Tuple[int, float]] = []
        # classifier
        if hasattr(self.model, "classes_") or hasattr(self.model, "n_classes_"):
            arr = np.atleast_1d(y)
            for cls in arr:
                cls = int(cls)
                mapping = {0: -1, 1: 0, 2: 1}
                out.append((mapping.get(cls, 0), 0.0))
            return out
        # regressor
        arr2d = np.atleast_2d(y)
        for row in arr2d:
            if hasattr(row, "__len__") and len(row) >= 2:
                s = int(round(float(row[0])))
                s = 1 if s > 0 else (-1 if s < 0 else 0)
                out.append((s, float(row[1])))
            else:
                s = int(round(float(row[0])))
                s = 1 if s > 0 else (-1 if s < 0 else 0)
                out.append((s, 0.0))
        return out

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

        # Ensure features
        if not self._have_all_features(df.iloc[-2]):
            self._try_ensure_features(df)
        if not self._have_all_features(df.iloc[-2]):
            # still missing
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
                    if self._have_all_features(row):
                        valid_rows.append(tuple(float(row[f]) for f in self.features))
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
        feature_tuple = tuple(float(prev[f]) for f in self.features)
        signal, amount = self._cached_predict(feature_tuple)
        self._set_signal(df, df.index[-1], int(signal), float(amount), overwrite=True)
        self.logger.info(f"[XGB] single prediction in {time.time()-t0:.2f}s")
        return int(signal)


if __name__ == "__main__":
    # basic smoke-test
    from CORE.log_manager import Logger
    logger = Logger(name="XGB", tag="[XGB]", logfile="LOGS/xgb.log", console=True).get_logger()
    logger.info("XGBStrategy module OK")
