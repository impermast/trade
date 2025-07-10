# trade/bots/analbot.py
import os
import sys
import inspect
import pandas as pd
from typing import Dict, List, Any, Optional, Union, Type, Callable, TypeVar, cast

from trade.bots.loggerbot import Logger
from trade.bots.indicators import Indicators
from trade.strategy.rsi import RSIonly_Strategy
from trade.strategy.base import BaseStrategy

# Type variable for strategy classes
T = TypeVar('T', bound=BaseStrategy)

class Analytic:
    def __init__(self, df: pd.DataFrame, data_name: str, output_file: str = "anal.csv") -> None:
        """
        Initialize the Analytic class with data and output settings.

        Args:
            df: DataFrame containing price data
            data_name: Name of the data (used for output file naming)
            output_file: Suffix for the output file name
        """
        self.df: pd.DataFrame = df
        self.logger = Logger(name="Analitic", tag="[ANAL]", logfile="LOGS/analitic.log", console=True).get_logger()
        self.indicators = Indicators(df, self.logger)
        self.output_file: str = output_file
        self.data_name: str = data_name
        self.output_path: str = f'DATA/{data_name}_{output_file}'

    @staticmethod
    def _get_expected_columns(name: str, params: Dict[str, Any]) -> List[str]:
        """
        Get the expected column names for a given indicator with specific parameters.

        Args:
            name: Name of the indicator
            params: Parameters for the indicator

        Returns:
            List of expected column names in the DataFrame
        """
        defaults: Dict[str, Dict[str, Any]] = {
            "sma": {"period": 10},
            "ema": {"period": 10},
            "rsi": {"period": 14},
            "macd": {"window_fast": 12, "window_slow": 26},
            "bollinger_bands": {"period": 20},
        }

        def is_default(param: str, value: Any) -> bool:
            return defaults.get(name, {}).get(param) == value

        if name == "sma":
            suffix = f"_{params['period']}" if not is_default("period", params.get("period")) else ""
            return [f"sma{suffix}"]

        elif name == "ema":
            suffix = f"_{params['period']}" if not is_default("period", params.get("period")) else ""
            return [f"ema{suffix}"]

        elif name == "rsi":
            suffix = f"_{params['period']}" if not is_default("period", params.get("period")) else ""
            return [f"rsi{suffix}"]

        elif name == "macd":
            fast = params.get("window_fast")
            slow = params.get("window_slow")
            is_def = is_default("window_fast", fast) and is_default("window_slow", slow)
            suffix = f"_{fast}_{slow}" if not is_def else ""
            return [f"macd{suffix}"]

        elif name == "bollinger_bands":
            p = params["period"]
            suffix = f"_{p}" if not is_default("period", p) else ""
            return [f"bb_h{suffix}", f"bb_m{suffix}", f"bb_l{suffix}"]

        return []

    def _calculate_single_indicator(self, indicator_name: str, params: Dict[str, Any]) -> bool:
        """
        Calculate a single indicator with the given parameters.

        Args:
            indicator_name: Name of the indicator to calculate
            params: Parameters for the indicator

        Returns:
            bool: True if the indicator was calculated, False otherwise
        """
        self.logger.info(f"Calculating indicator {indicator_name} with parameters {params}")

        # Get the method from the indicators class
        method = getattr(self.indicators, indicator_name, None)
        if method is None:
            self.logger.warning(f"Indicator {indicator_name} not found.")
            return False

        # Check if the indicator is already calculated
        expected_columns = self._get_expected_columns(indicator_name, params)
        missing = [col for col in expected_columns if col not in self.df.columns]
        if not missing:
            self.logger.info(f"Skipping {indicator_name} - already calculated.")
            return False

        # Filter only valid parameters for the method
        method_params = inspect.signature(method).parameters
        filtered_params = {k: v for k, v in params.items() if k in method_params}

        # Calculate the indicator
        try:
            method(inplace=True, **filtered_params)
            self.logger.info(f"Indicator {indicator_name} calculated successfully.")
            return True
        except Exception as e:
            self.logger.error(f"Error calculating {indicator_name}: {e}")
            return False

    def make_calc(self, indicators: List[str], stratparams: Dict[str, Dict[str, Any]]) -> None:
        """
        Calculate indicators based on strategy parameters.

        Args:
            indicators: List of indicator names to calculate
            stratparams: Dictionary of indicator parameters
        """
        self.logger.info(f"Calculating indicators: {stratparams}")

        for indicator_name in stratparams:
            params = stratparams.get(indicator_name, {})
            self._calculate_single_indicator(indicator_name, params)

    def _save_results_to_csv(self) -> bool:
        """
        Save the analysis results to a CSV file.

        Returns:
            bool: True if the save was successful, False otherwise
        """
        try:
            self.df.to_csv(self.output_path, index=False)
            self.logger.info(f"Analysis data saved to {self.output_path}")
            return True
        except Exception as e:
            self.logger.error(f"Error saving to {self.output_path}: {e}")
            return False

    def make_strategy(self, strategy_cls: Type[T], inplace: bool = True, **params) -> int:
        """
        Apply a trading strategy to the data.

        Args:
            strategy_cls: Strategy class to instantiate
            inplace: Whether to save results to file
            **params: Parameters to pass to the strategy

        Returns:
            Signal value from the strategy
        """
        # Create strategy instance
        strategy = strategy_cls(**params)
        self.logger.info(f"Starting calculation for strategy {strategy.name}")

        # Get required indicators and calculate them
        indicators, stratparams = strategy.check_indicators()
        self.make_calc(indicators, stratparams)

        # Generate signals using the strategy
        result = strategy.get_signals(self.df)

        # Save results if requested
        if inplace:
            self._save_results_to_csv()

        return result


if __name__ == "__main__":
    import pandas as pd
    # Get the path to the current file (equivalent to __file__)
    current_dir = os.path.dirname(os.path.abspath(__file__))

    # Path one level up to the DATA folder
    csv_path = os.path.join(os.path.dirname(current_dir), "..", "DATA", "BTCUSDT_1h.csv")
    csv_path = os.path.abspath(csv_path)  # absolute path (just to be safe)

    # Load the data
    df = pd.read_csv(csv_path)
    if 'timestamp' in df.columns:
        df['timestamp'] = pd.to_datetime(df['timestamp'])

    # Create an Analytic instance and run a strategy
    analyzer = Analytic(df, "BTCUSDT_1h")
    result = analyzer.make_strategy(RSIonly_Strategy, rsi={"period": 20, "lower": 20})
    print(result)