# strategy/xgb_strategy.py

import os
import sys
import pandas as pd
import numpy as np
import joblib
from xgboost import XGBRegressor
from typing import Dict, Any

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
    """

    def __init__(self, model_path: str = "xgb_model_multi.joblib", 
                 features_path: str = "xgb_model_features.joblib", 
                 slippage: float = 0.0005, **params):
        """
        Initialize the XGBoost strategy with model and parameters.

        Args:
            model_path (str): Path to the saved XGBoost model file
            features_path (str): Path to the saved features list file
            slippage (float): Slippage factor to account for execution costs
            **params: Additional parameters for indicators
        """
        super().__init__(
            name="XGBStrategy", 
            indicators=['rsi', 'ema', 'macd', 'boll_upper', 'boll_lower', 
                       'atr', 'ovb', 'return_1', 'return_3', 'return_6'], 
            **params
        )
        self.model = joblib.load(model_path)
        self.features = joblib.load(features_path)
        self.slippage = slippage

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

        # Get the previous row for features and current open price
        row = df.iloc[-2] 
        next_open = df.iloc[-1]['open'] 

        # Prepare features for the model
        X = row[self.features].values.reshape(1, -1)

        # Make prediction - model outputs [signal, amount]
        y_pred = self.model.predict(X)[0]
        signal = int(round(y_pred[0]))
        amount = float(y_pred[1])

        # Calculate execution price (accounting for slippage)
        # This is currently unused but kept for future implementation
        # of position sizing and risk management
        _ = next_open * (1 + self.slippage)

        # Store the signal and amount in the DataFrame for analysis
        df.at[df.index[-1], "xgb_signal"] = (signal, amount)

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
