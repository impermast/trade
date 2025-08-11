# BOTS/indicators.py

import pandas as pd
import numpy as np
from typing import Optional, Dict, Any, List, Tuple, Union
from functools import lru_cache

from ta.trend import SMAIndicator, EMAIndicator, MACD
from ta.momentum import RSIIndicator, StochasticOscillator, WilliamsRIndicator
from ta.volatility import BollingerBands

class Indicators:
    """
    Class for calculating technical indicators.

    This class contains methods for calculating various technical indicators
    like SMA, EMA, RSI, MACD, and Bollinger Bands.

    Attributes:
        df: DataFrame containing price data
        logger: Logger instance for logging
        _cache: Dictionary to cache calculated indicators
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
        self._cache: Dict[str, Dict[Tuple, np.ndarray]] = {}

    def _get_column_name(self, indicator: str, params: Dict[str, Any]) -> str:
        """
        Get the column name for an indicator with specific parameters.

        Args:
            indicator: Name of the indicator
            params: Parameters for the indicator

        Returns:
            Column name for the indicator
        """
        if indicator == "sma":
            period = params.get("period", 10)
            return f"sma_{period}" if period != 10 else "sma"

        elif indicator == "ema":
            period = params.get("period", 10)
            return f"ema_{period}" if period != 10 else "ema"

        elif indicator == "rsi":
            period = params.get("period", 14)
            return f"rsi_{period}" if period != 14 else "rsi"

        elif indicator == "macd":
            window_fast = params.get("window_fast", 12)
            window_slow = params.get("window_slow", 26)
            is_default = (window_fast == 12 and window_slow == 26)
            return f"macd_{window_fast}_{window_slow}" if not is_default else "macd"

        elif indicator == "bollinger_bands":
            period = params.get("period", 20)
            suffix = f"_{period}" if period != 20 else ""
            return [f"bb_h{suffix}", f"bb_m{suffix}", f"bb_l{suffix}"]

        elif indicator == "williams_r":
            period = params.get("period", 14)
            return f"williams_r_{period}" if period != 14 else "williams_r"

        elif indicator == "stochastic_oscillator":
            k_period = params.get("k_period", 14)
            d_period = params.get("d_period", 3)
            is_default = (k_period == 14 and d_period == 3)
            if is_default:
                return ["stoch_k", "stoch_d"]
            else:
                return [f"stoch_k_{k_period}_{d_period}", f"stoch_d_{k_period}_{d_period}"]

        return indicator

    def _indicator_exists(self, column_name: Union[str, List[str]]) -> bool:
        """
        Check if an indicator already exists in the DataFrame.

        Args:
            column_name: Name of the column(s) to check

        Returns:
            True if the indicator exists, False otherwise
        """
        if isinstance(column_name, list):
            return all(col in self.df.columns for col in column_name)
        return column_name in self.df.columns

    def _get_cached_result(self, indicator: str, params_tuple: Tuple[Tuple[str, Any], ...]) -> Optional[np.ndarray]:
        """
        Get a cached result for an indicator calculation.

        Args:
            indicator: Name of the indicator
            params_tuple: Parameters for the indicator as a tuple of (key, value) pairs

        Returns:
            Cached result if available, None otherwise
        """
        if indicator in self._cache and params_tuple in self._cache[indicator]:
            return self._cache[indicator][params_tuple]
        return None

    def _cache_result(self, indicator: str, params_tuple: Tuple[Tuple[str, Any], ...], result: np.ndarray) -> None:
        """
        Cache the result of an indicator calculation.

        Args:
            indicator: Name of the indicator
            params_tuple: Parameters for the indicator as a tuple of (key, value) pairs
            result: Result to cache
        """
        if indicator not in self._cache:
            self._cache[indicator] = {}
        self._cache[indicator][params_tuple] = result

    def sma(self, period: int = 10, inplace: bool = True) -> Optional[pd.DataFrame]:
        """
        Calculate Simple Moving Average.

        Args:
            period: Period for the SMA calculation
            inplace: Whether to modify the DataFrame in place

        Returns:
            DataFrame with SMA values if inplace is False, None otherwise
        """
        # Get column name for this indicator
        params = {"period": period}
        col_name = self._get_column_name("sma", params)

        # Check if indicator already exists
        if self._indicator_exists(col_name):
            self.logger.info(f"SMA with period {period} already calculated, using existing values.")
            if not inplace:
                return self.df[[col_name]].copy()
            return None

        # Check if result is cached
        params_tuple = tuple(sorted(params.items()))
        cached_result = self._get_cached_result("sma", params_tuple)

        if cached_result is not None:
            self.logger.info(f"Using cached SMA with period {period}.")
            result = cached_result
        else:
            # Calculate the indicator
            self.logger.info(f"Calculating SMA with period {period}.")
            result = SMAIndicator(self.df['close'], window=period).sma_indicator().values

            # Cache the result
            self._cache_result("sma", params_tuple, result)

        # Update the DataFrame
        if inplace:
            self.df[col_name] = result
            return None
        else:
            # Create a new DataFrame with just the indicator column
            result_df = pd.DataFrame({col_name: result}, index=self.df.index)
            return result_df

    def ema(self, period: int = 10, inplace: bool = True) -> Optional[pd.DataFrame]:
        """
        Calculate Exponential Moving Average.

        Args:
            period: Period for the EMA calculation
            inplace: Whether to modify the DataFrame in place

        Returns:
            DataFrame with EMA values if inplace is False, None otherwise
        """
        # Get column name for this indicator
        params = {"period": period}
        col_name = self._get_column_name("ema", params)

        # Check if indicator already exists
        if self._indicator_exists(col_name):
            self.logger.info(f"EMA with period {period} already calculated, using existing values.")
            if not inplace:
                return self.df[[col_name]].copy()
            return None

        # Check if result is cached
        params_tuple = tuple(sorted(params.items()))
        cached_result = self._get_cached_result("ema", params_tuple)

        if cached_result is not None:
            self.logger.info(f"Using cached EMA with period {period}.")
            result = cached_result
        else:
            # Calculate the indicator
            self.logger.info(f"Calculating EMA with period {period}.")
            result = EMAIndicator(self.df['close'], window=period).ema_indicator().values

            # Cache the result
            self._cache_result("ema", params_tuple, result)

        # Update the DataFrame
        if inplace:
            self.df[col_name] = result
            return None
        else:
            # Create a new DataFrame with just the indicator column
            result_df = pd.DataFrame({col_name: result}, index=self.df.index)
            return result_df

    def rsi(self, period: int = 14, inplace: bool = True) -> Optional[pd.DataFrame]:
        """
        Calculate Relative Strength Index.

        Args:
            period: Period for the RSI calculation
            inplace: Whether to modify the DataFrame in place

        Returns:
            DataFrame with RSI values if inplace is False, None otherwise
        """
        # Get column name for this indicator
        params = {"period": period}
        col_name = self._get_column_name("rsi", params)

        # Check if indicator already exists
        if self._indicator_exists(col_name):
            self.logger.info(f"RSI with period {period} already calculated, using existing values.")
            if not inplace:
                return self.df[[col_name]].copy()
            return None

        # Check if result is cached
        params_tuple = tuple(sorted(params.items()))
        cached_result = self._get_cached_result("rsi", params_tuple)

        if cached_result is not None:
            self.logger.info(f"Using cached RSI with period {period}.")
            result = cached_result
        else:
            # Calculate the indicator
            self.logger.info(f"Calculating RSI with period {period}.")
            result = RSIIndicator(self.df['close'], window=period).rsi().values

            # Cache the result
            self._cache_result("rsi", params_tuple, result)

        # Update the DataFrame
        if inplace:
            self.df[col_name] = result
            return None
        else:
            # Create a new DataFrame with just the indicator column
            result_df = pd.DataFrame({col_name: result}, index=self.df.index)
            return result_df

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
        # Get column name for this indicator
        params = {
            "window_slow": window_slow,
            "window_fast": window_fast,
            "window_sign": window_sign
        }
        col_name = self._get_column_name("macd", params)

        # Check if indicator already exists
        if self._indicator_exists(col_name):
            self.logger.info(f"MACD with parameters {params} already calculated, using existing values.")
            if not inplace:
                return self.df[[col_name]].copy()
            return None

        # Check if result is cached
        params_tuple = tuple(sorted(params.items()))
        cached_result = self._get_cached_result("macd", params_tuple)

        if cached_result is not None:
            self.logger.info(f"Using cached MACD with parameters {params}.")
            result = cached_result
        else:
            # Calculate the indicator
            self.logger.info(f"Calculating MACD with parameters {params}.")
            result = MACD(
                self.df['close'],
                window_slow=window_slow,
                window_fast=window_fast,
                window_sign=window_sign
            ).macd_diff().values

            # Cache the result
            self._cache_result("macd", params_tuple, result)

        # Update the DataFrame
        if inplace:
            self.df[col_name] = result
            return None
        else:
            # Create a new DataFrame with just the indicator column
            result_df = pd.DataFrame({col_name: result}, index=self.df.index)
            return result_df

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
        # Get column names for this indicator
        params = {"period": period, "window_dev": window_dev}
        col_names = self._get_column_name("bollinger_bands", params)
        col_h, col_m, col_l = col_names

        # Check if indicator already exists
        if self._indicator_exists(col_names):
            self.logger.info(f"Bollinger Bands with period {period} already calculated, using existing values.")
            if not inplace:
                return self.df[col_names].copy()
            return None

        # Check if result is cached
        params_tuple = tuple(sorted(params.items()))
        cached_result = self._get_cached_result("bollinger_bands", params_tuple)

        if cached_result is not None:
            self.logger.info(f"Using cached Bollinger Bands with period {period}.")
            result_h, result_m, result_l = cached_result
        else:
            # Calculate the indicator
            self.logger.info(f"Calculating Bollinger Bands with period {period}.")
            bb = BollingerBands(self.df['close'], window=period, window_dev=window_dev)
            result_h = bb.bollinger_hband().values
            result_m = bb.bollinger_mavg().values
            result_l = bb.bollinger_lband().values

            # Cache the results as a tuple of arrays
            self._cache_result("bollinger_bands", params_tuple, (result_h, result_m, result_l))

        # Update the DataFrame
        if inplace:
            self.df[col_h] = result_h
            self.df[col_m] = result_m
            self.df[col_l] = result_l
            return None
        else:
            # Create a new DataFrame with just the indicator columns
            result_df = pd.DataFrame({
                col_h: result_h,
                col_m: result_m,
                col_l: result_l
            }, index=self.df.index)
            return result_df

    def williams_r(self, period: int = 14, inplace: bool = True) -> Optional[pd.DataFrame]:
        """
        Calculate Williams %R indicator.

        Args:
            period: Period for the Williams %R calculation
            inplace: Whether to modify the DataFrame in place

        Returns:
            DataFrame with Williams %R values if inplace is False, None otherwise
        """
        # Get column name for this indicator
        params = {"period": period}
        col_name = self._get_column_name("williams_r", params)

        # Check if indicator already exists
        if self._indicator_exists(col_name):
            self.logger.info(f"Williams %R with period {period} already calculated, using existing values.")
            if not inplace:
                return self.df[[col_name]].copy()
            return None

        # Check if result is cached
        params_tuple = tuple(sorted(params.items()))
        cached_result = self._get_cached_result("williams_r", params_tuple)

        if cached_result is not None:
            self.logger.info(f"Using cached Williams %R with period {period}.")
            result = cached_result
        else:
            # Calculate the indicator
            self.logger.info(f"Calculating Williams %R with period {period}.")
            williams_r = WilliamsRIndicator(
                high=self.df['high'],
                low=self.df['low'],
                close=self.df['close'],
                window=period
            )
            result = williams_r.williams_r().values

            # Cache the result
            self._cache_result("williams_r", params_tuple, result)

        # Update the DataFrame
        if inplace:
            self.df[col_name] = result
            return None
        else:
            # Create a new DataFrame with just the indicator column
            result_df = pd.DataFrame({col_name: result}, index=self.df.index)
            return result_df

    def stochastic_oscillator(self, k_period: int = 14, d_period: int = 3, 
                             inplace: bool = True) -> Optional[pd.DataFrame]:
        """
        Calculate Stochastic Oscillator (%K and %D).

        Args:
            k_period: Period for %K calculation
            d_period: Period for %D calculation (smoothing of %K)
            inplace: Whether to modify the DataFrame in place

        Returns:
            DataFrame with Stochastic Oscillator values if inplace is False, None otherwise
        """
        # Get column names for this indicator
        params = {"k_period": k_period, "d_period": d_period}
        col_names = self._get_column_name("stochastic_oscillator", params)
        col_k, col_d = col_names

        # Check if indicator already exists
        if self._indicator_exists(col_names):
            self.logger.info(f"Stochastic Oscillator with parameters {params} already calculated, using existing values.")
            if not inplace:
                return self.df[col_names].copy()
            return None

        # Check if result is cached
        params_tuple = tuple(sorted(params.items()))
        cached_result = self._get_cached_result("stochastic_oscillator", params_tuple)

        if cached_result is not None:
            self.logger.info(f"Using cached Stochastic Oscillator with parameters {params}.")
            result_k, result_d = cached_result
        else:
            # Calculate the indicator
            self.logger.info(f"Calculating Stochastic Oscillator with parameters {params}.")
            stoch = StochasticOscillator(
                high=self.df['high'],
                low=self.df['low'],
                close=self.df['close'],
                window=k_period,
                smooth_window=d_period
            )
            result_k = stoch.stoch().values
            result_d = stoch.stoch_signal().values

            # Cache the results as a tuple of arrays
            self._cache_result("stochastic_oscillator", params_tuple, (result_k, result_d))

        # Update the DataFrame
        if inplace:
            self.df[col_k] = result_k
            self.df[col_d] = result_d
            return None
        else:
            # Create a new DataFrame with just the indicator columns
            result_df = pd.DataFrame({
                col_k: result_k,
                col_d: result_d
            }, index=self.df.index)
            return result_df
