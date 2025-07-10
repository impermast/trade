# trade/strategy/rsi.py

import pandas as pd
from typing import Dict, Any, Optional
from trade.strategy.base import BaseStrategy


class RSIonly_Strategy(BaseStrategy):
    """
    A trading strategy based on the Relative Strength Index (RSI) indicator.

    This strategy generates buy signals when RSI falls below a lower threshold
    and sell signals when RSI rises above an upper threshold.
    """

    def __init__(self, **params: Any) -> None:
        """
        Initialize the RSI strategy with the given parameters.

        Args:
            **params: Strategy parameters including RSI settings
        """
        # Initialize with RSI indicator
        super().__init__(name="RSIOnly", indicators=["rsi"], **params)

    def default_params(self) -> Dict[str, Dict[str, Any]]:
        """
        Define default parameters for the RSI strategy.

        Returns:
            Dictionary containing default RSI parameters:
            - period: The period for RSI calculation (default: 14)
            - lower: The lower threshold for buy signals (default: 30)
            - upper: The upper threshold for sell signals (default: 70)
        """
        return {
            "rsi": {
                "period": 14,
                "lower": 30,
                "upper": 70
            }
        }

    def get_signals(self, df: pd.DataFrame) -> int:
        """
        Generate trading signals based on RSI values.

        Args:
            df: DataFrame containing price data and RSI indicator values
                Must include a column named 'rsi' for default period (14)
                or 'rsi_X' for custom period X

        Returns:
            1 for buy signal (RSI below lower threshold)
            -1 for sell signal (RSI above upper threshold)
            0 for no action (RSI between thresholds or insufficient data)

        Raises:
            ValueError: If the required RSI column is not found in the DataFrame
        """
        rsi_cfg = self.params["rsi"]
        period = rsi_cfg["period"]
        lower = rsi_cfg["lower"]
        upper = rsi_cfg["upper"]

        if len(df) < period:
            return 0

        col = "rsi" if period == 14 else f"rsi_{period}"

        if col not in df.columns:
            raise ValueError(f"Column {col} not found in the DataFrame.")

        rsi = df[col].iloc[-1]

        if rsi < lower:
            return 1
        elif rsi > upper:
            return -1
        return 0


if __name__ == "__main__":
    strat = RSIonly_Strategy(rsi={"period": 10, "lower": 25})
    print(strat)