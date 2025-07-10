# strategy/xgb_strategy.py

import os
import sys
import pandas as pd
import numpy as np
import joblib
import time
from functools import lru_cache
from xgboost import XGBRegressor
from typing import Dict, Any, List, Tuple, Optional, Union, cast

sys.path.append(os.path.abspath("."))
from STRATEGY.base import BaseStrategy

class XGBStrategy(BaseStrategy):
    """
    Trading strategy based on XGBoost machine learning model.

    This strategy uses a pre-trained XGBoost model to predict trading signals
    based on various technical indicators. The model is expected to output
    both a signal value and a position size amount.

    Attributes:
        model: Trained XGBoost model loaded from file
        features: List of feature names the model expects
        slippage (float): Slippage factor to account for execution costs
        batch_size (int): Number of rows to process in a batch for prediction
        prediction_cache_size (int): Size of the LRU cache for model predictions
        use_quantization (bool): Whether to use quantized model for faster inference
    """

    # Class-level cache for model loading to avoid loading the same model multiple times
    _model_cache = {}
    _features_cache = {}

    def __init__(self, model_path: str = "xgb_model_multi.joblib", 
                 features_path: str = "xgb_model_features.joblib", 
                 slippage: float = 0.0005,
                 batch_size: int = 100,
                 prediction_cache_size: int = 1024,
                 use_quantization: bool = False,
                 **params):
        """
        Initialize the XGBoost strategy with model and parameters.

        Args:
            model_path (str): Path to the saved XGBoost model file
            features_path (str): Path to the saved features list file
            slippage (float): Slippage factor to account for execution costs
            batch_size (int): Number of rows to process in a batch for prediction
            prediction_cache_size (int): Size of the LRU cache for model predictions
            use_quantization (bool): Whether to use quantized model for faster inference
            **params: Additional parameters for indicators
        """
        super().__init__(
            name="XGBStrategy", 
            indicators=['rsi', 'ema', 'macd', 'boll_upper', 'boll_lower', 
                       'atr', 'ovb', 'return_1', 'return_3', 'return_6'], 
            **params
        )

        self.batch_size = batch_size
        self.prediction_cache_size = prediction_cache_size
        self.use_quantization = use_quantization
        self.slippage = slippage

        # Load model and features from cache if available, otherwise load from file
        if model_path in self._model_cache:
            self.model = self._model_cache[model_path]
        else:
            start_time = time.time()
            self.model = joblib.load(model_path)

            # Apply quantization if requested (reduces model size and speeds up inference)
            if use_quantization:
                try:
                    # Convert to JSON and back to apply quantization
                    model_json = self.model.get_booster().save_config()
                    self.model = XGBRegressor()
                    self.model.get_booster().load_config(model_json)
                    print(f"Model quantized in {time.time() - start_time:.2f} seconds")
                except Exception as e:
                    print(f"Error quantizing model: {e}")

            self._model_cache[model_path] = self.model
            print(f"Model loaded in {time.time() - start_time:.2f} seconds")

        if features_path in self._features_cache:
            self.features = self._features_cache[features_path]
        else:
            self.features = joblib.load(features_path)
            self._features_cache[features_path] = self.features

        # Create a cached version of the predict method
        self._cached_predict = lru_cache(maxsize=prediction_cache_size)(self._predict)

    def default_params(self) -> Dict[str, Any]:
        """
        Define default parameters for the strategy.

        Returns:
            Dict[str, Any]: Dictionary of parameter names and their default values
        """
        return {
            "rsi": {"period": 14},
            'ema': {"period": 10}
        }

    def _predict(self, feature_tuple: Tuple[float, ...]) -> Tuple[int, float]:
        """
        Make a prediction using the XGBoost model.

        This method is wrapped with lru_cache for efficient caching of predictions.

        Args:
            feature_tuple: Tuple of feature values

        Returns:
            Tuple of (signal, amount)
        """
        # Convert tuple to numpy array and reshape for prediction
        X = np.array(feature_tuple).reshape(1, -1)

        # Make prediction - model outputs [signal, amount]
        y_pred = self.model.predict(X)[0]
        signal = int(round(y_pred[0]))
        amount = float(y_pred[1])

        return signal, amount

    def _batch_predict(self, X: np.ndarray) -> List[Tuple[int, float]]:
        """
        Make predictions for a batch of data points.

        Args:
            X: 2D array of feature values

        Returns:
            List of (signal, amount) tuples
        """
        # Make predictions for the batch
        y_pred = self.model.predict(X)

        # Convert predictions to signal and amount tuples
        results = []
        for pred in y_pred:
            signal = int(round(pred[0]))
            amount = float(pred[1])
            results.append((signal, amount))

        return results

    def get_signals(self, df: pd.DataFrame) -> int:
        """
        Generate trading signals using the XGBoost model.

        The model predicts both a signal value and a position size amount.
        The signal is stored in the DataFrame for later analysis.

        Args:
            df (pd.DataFrame): DataFrame containing price and indicator data

        Returns:
            int: Signal value (1 for buy, -1 for sell, 0 for no action)
        """
        # Need at least 2 rows to make a prediction
        if df.shape[0] < 2:
            return 0

        # Measure performance
        start_time = time.time()

        # Determine if we should use batch prediction
        use_batch = df.shape[0] > self.batch_size

        if use_batch:
            # Process in batches for large datasets
            print(f"Using batch prediction for {df.shape[0]} rows")

            # Create a new column for signals if it doesn't exist
            if "xgb_signal" not in df.columns:
                df["xgb_signal"] = None

            # Process in batches
            batch_size = self.batch_size
            for i in range(0, df.shape[0] - 1, batch_size):
                end_idx = min(i + batch_size, df.shape[0] - 1)

                # Get rows for this batch
                batch_rows = df.iloc[i:end_idx]

                # Skip rows with missing features
                valid_rows = []
                valid_indices = []
                for j, (idx, row) in enumerate(batch_rows.iterrows()):
                    if all(f in row and not pd.isna(row[f]) for f in self.features):
                        # Convert row to feature tuple for prediction
                        feature_values = tuple(row[f] for f in self.features)
                        valid_rows.append(feature_values)
                        valid_indices.append(idx)

                if not valid_rows:
                    continue

                # Convert to numpy array for batch prediction
                X = np.array(valid_rows)

                # Make predictions for the batch
                predictions = self._batch_predict(X)

                # Store predictions in the DataFrame
                for idx, pred in zip(valid_indices, predictions):
                    next_idx = idx + 1
                    if next_idx < len(df):
                        df.at[next_idx, "xgb_signal"] = pred

            # Return the latest signal
            if df.iloc[-1]["xgb_signal"] is not None:
                signal, _ = df.iloc[-1]["xgb_signal"]
                print(f"Batch prediction completed in {time.time() - start_time:.2f} seconds")
                return signal
            else:
                print(f"No valid prediction for the latest row")
                return 0
        else:
            # For smaller datasets or single predictions, use cached prediction

            # Get the previous row for features and current open price
            row = df.iloc[-2] 
            next_open = df.iloc[-1]['open'] 

            # Check if all features are available
            if not all(f in row and not pd.isna(row[f]) for f in self.features):
                print(f"Missing features in row: {[f for f in self.features if f not in row or pd.isna(row[f])]}")
                return 0

            # Convert row to feature tuple for cached prediction
            feature_values = tuple(row[f] for f in self.features)

            # Make prediction using cached method
            signal, amount = self._cached_predict(feature_values)

            # Calculate execution price (accounting for slippage)
            # This is currently unused but kept for future implementation
            # of position sizing and risk management
            _ = next_open * (1 + self.slippage)

            # Store the signal and amount in the DataFrame for analysis
            df.at[df.index[-1], "xgb_signal"] = (signal, amount)

            print(f"Single prediction completed in {time.time() - start_time:.2f} seconds")
            return signal

if __name__ == "__main__":
    """
    Example usage of the XGBStrategy class.

    This demonstrates how to create an instance of the strategy with custom parameters
    and print its string representation.
    """
    # Create a strategy instance with custom RSI period
    strat = XGBStrategy(rsi={"period": 10})

    # Print the strategy name and parameters
    print(strat)
