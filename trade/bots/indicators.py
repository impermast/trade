# trade/bots/indicators.py

import pandas as pd
from typing import Optional, Dict, Any

from ta.trend import SMAIndicator, EMAIndicator, MACD
from ta.momentum import RSIIndicator
from ta.volatility import BollingerBands

class Indicators:
    """
    Class for calculating technical indicators.

    This class contains methods for calculating various technical indicators
    like SMA, EMA, RSI, MACD, and Bollinger Bands.
    """

    def __init__(self, df: pd.DataFrame, logger) -> None:
        """
        Initialize the Indicators class.

        Args:
            df: DataFrame containing price data
            logger: Logger instance for logging
        """
        self.df: pd.DataFrame = df
        self.logger = logger

    def sma(self, period: int = 10, inplace: bool = True) -> Optional[pd.DataFrame]:
        """
        Calculate Simple Moving Average.

        Args:
            period: Period for the SMA calculation
            inplace: Whether to modify the DataFrame in place

        Returns:
            DataFrame with SMA values if inplace is False, None otherwise
        """
        self.logger.info("Calculating SMA.")
        df = self.df
        col_name = f"sma_{period}" if period != 10 else "sma"
        df[col_name] = SMAIndicator(df['close'], window=period).sma_indicator()
        if inplace:
            self.df[col_name] = df[col_name]
            return None
        else:
            return df[[col_name]].copy()

    def ema(self, period: int = 10, inplace: bool = True) -> Optional[pd.DataFrame]:
        """
        Calculate Exponential Moving Average.

        Args:
            period: Period for the EMA calculation
            inplace: Whether to modify the DataFrame in place

        Returns:
            DataFrame with EMA values if inplace is False, None otherwise
        """
        self.logger.info("Calculating EMA.")
        df = self.df
        col_name = f"ema_{period}" if period != 10 else "ema"
        df[col_name] = EMAIndicator(df['close'], window=period).ema_indicator()
        if inplace:
            self.df[col_name] = df[col_name]
            return None
        else:
            return df[[col_name]].copy()

    def rsi(self, period: int = 14, inplace: bool = True) -> Optional[pd.DataFrame]:
        """
        Calculate Relative Strength Index.

        Args:
            period: Period for the RSI calculation
            inplace: Whether to modify the DataFrame in place

        Returns:
            DataFrame with RSI values if inplace is False, None otherwise
        """
        self.logger.info("Calculating RSI.")
        df = self.df
        col_name = f"rsi_{period}" if period != 14 else "rsi"
        df[col_name] = RSIIndicator(df['close'], window=period).rsi()
        if inplace:
            self.df[col_name] = df[col_name]
            return None
        else:
            return df[[col_name]].copy()

    def macd(self, window_fast: int = 12, window_slow: int = 26, 
             window_sign: int = 9, inplace: bool = True) -> Optional[pd.DataFrame]:
        """
        Calculate Moving Average Convergence Divergence.

        Args:
            window_fast: Fast period for MACD calculation
            window_slow: Slow period for MACD calculation
            window_sign: Signal period for MACD calculation
            inplace: Whether to modify the DataFrame in place

        Returns:
            DataFrame with MACD values if inplace is False, None otherwise
        """
        self.logger.info("Calculating MACD.")
        df = self.df
        is_default = (window_fast == 12 and window_slow == 26)
        col_name = f"macd_{window_fast}_{window_slow}" if not is_default else "macd"
        df[col_name] = MACD(
            df['close'],
            window_slow=window_slow,
            window_fast=window_fast,
            window_sign=window_sign
        ).macd_diff()
        if inplace:
            self.df[col_name] = df[col_name]
            return None
        else:
            return df[[col_name]].copy()

    def bollinger_bands(self, period: int = 20, window_dev: float = 2, 
                       inplace: bool = True) -> Optional[pd.DataFrame]:
        """
        Calculate Bollinger Bands.

        Args:
            period: Period for the Bollinger Bands calculation
            window_dev: Number of standard deviations for the bands
            inplace: Whether to modify the DataFrame in place

        Returns:
            DataFrame with Bollinger Bands values if inplace is False, None otherwise
        """
        self.logger.info("Calculating Bollinger Bands.")
        df = self.df
        suffix = f"_{period}" if period != 20 else ""
        col_h = f"bb_h{suffix}"
        col_m = f"bb_m{suffix}"
        col_l = f"bb_l{suffix}"

        bb = BollingerBands(df['close'], window=period, window_dev=window_dev)
        df[col_h] = bb.bollinger_hband()
        df[col_m] = bb.bollinger_mavg()
        df[col_l] = bb.bollinger_lband()

        if inplace:
            self.df[col_h] = df[col_h]
            self.df[col_m] = df[col_m]
            self.df[col_l] = df[col_l]
            return None
        else:
            return df[[col_h, col_m, col_l]].copy()
