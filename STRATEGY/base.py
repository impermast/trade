# strategy/base.py

from abc import ABC, abstractmethod
import pandas as pd
from typing import Dict, List, Any, Optional, Union, Tuple

class BaseStrategy(ABC):
    """
    Base class for all trading strategies.

    This abstract class defines the interface that all strategy implementations must follow.
    It handles parameter management with validation and provides a consistent interface
    for strategy execution.

    Attributes:
        name (str): Name of the strategy
        indicators (List[str]): List of indicators required by the strategy
        params (Dict[str, Any]): Strategy parameters with their values
    """

    def __init__(self, df: Optional[pd.DataFrame] = None, params: Optional[Dict[str, Any]] = None, 
                 name: str = "BaseStrategy", indicators: Optional[List[str]] = None,
                 data_name: Optional[str] = None,
                 output_file: str = "DATA/BTCUSDT_1m_anal.csv", save_after_init: bool = True, **kwargs):
        """
        Initialize a strategy with name, required indicators, and parameters.

        Args:
            df (Optional[pd.DataFrame]): DataFrame to initialize with
            params (Optional[Dict[str, Any]]): Strategy-specific parameters
            name (str): Name of the strategy
            indicators (Optional[List[str]]): List of indicators required by the strategy
            data_name (Optional[str]): Name for the data
            output_file (str): Output file path
            save_after_init (bool): Whether to save after initialization
            **kwargs: Additional parameters that override default values

        Raises:
            ValueError: If invalid parameters are provided
        """
        self.name = name
        self.indicators = indicators or []

        # Get default parameters and validate user-provided parameters
        default_params = self.default_params()
        user_params = params or {}
        user_params.update(kwargs)
        self._validate_params(default_params, user_params)

        # Merge default parameters with user-provided parameters
        self.params = self._merge_with_defaults(default_params, user_params)
        
        # Common initialization parameters
        self._init_df = df
        self._init_data_name = data_name
        self._init_output_file = output_file
        self._save_after_init = bool(save_after_init)
        
        # If dataframe is provided, ensure indicators now
        if self._init_df is not None:
            self._ensure_indicators_and_save(self._init_df)

    @abstractmethod
    def get_signals(self, df: pd.DataFrame) -> int:
        """
        Generate trading signals based on the input data.

        Args:
            df (pd.DataFrame): DataFrame containing price and indicator data

        Returns:
            int: Signal value (1 for buy, -1 for sell, 0 for no action)
        """
        pass

    @abstractmethod
    def default_params(self) -> Dict[str, Any]:
        """
        Define default parameters for the strategy.

        Returns:
            Dict[str, Any]: Dictionary of parameter names and their default values
        """
        pass

    @abstractmethod
    def _ensure_orders_col(self, df: pd.DataFrame) -> None:
        """
        Ensure the orders column exists for this strategy.
        
        Args:
            df (pd.DataFrame): DataFrame to add orders column to
        """
        pass

    def _validate_params(self, defaults: Dict[str, Any], params: Dict[str, Any]) -> None:
        """
        Validate that user-provided parameters are valid for this strategy.

        Args:
            defaults (Dict[str, Any]): Default parameters dictionary
            params (Dict[str, Any]): User-provided parameters dictionary

        Raises:
            ValueError: If invalid parameters are provided
        """
        # Check for unknown parameters
        unknown_params = [k for k in params if k not in defaults and not isinstance(params[k], dict)]
        if unknown_params:
            raise ValueError(f"Unknown parameters for {self.name}: {', '.join(unknown_params)}")

        # For nested dictionaries, check that the keys exist in defaults
        for k, v in params.items():
            if isinstance(v, dict) and k in defaults and isinstance(defaults[k], dict):
                unknown_nested = [nk for nk in v if nk not in defaults[k]]
                if unknown_nested:
                    raise ValueError(f"Unknown nested parameters for {self.name}.{k}: {', '.join(unknown_nested)}")

    def _merge_with_defaults(self, defaults: Dict[str, Any], overrides: Dict[str, Any]) -> Dict[str, Any]:
        """
        Merge default parameters with user-provided overrides.

        Args:
            defaults (Dict[str, Any]): Default parameters dictionary
            overrides (Dict[str, Any]): User-provided parameters dictionary

        Returns:
            Dict[str, Any]: Merged parameters dictionary
        """
        merged = defaults.copy()
        for k, v in overrides.items():
            if isinstance(v, dict) and k in merged and isinstance(merged[k], dict):
                merged[k].update(v)
            else:
                merged[k] = v
        return merged

    def check_indicators(self) -> Tuple[List[str], Dict[str, Any]]:
        """
        Get the required indicators and their parameters.

        Returns:
            Tuple[List[str], Dict[str, Any]]: Tuple containing indicators and parameters
        """
        return (self.indicators, self.params)

    def _resolve_data_name(self, df: pd.DataFrame) -> str:
        """
        Resolve data name for analytics file.
        
        Args:
            df (pd.DataFrame): DataFrame to extract name from
            
        Returns:
            str: Resolved data name
        """
        if self._init_data_name:
            return self._init_data_name
        # Try to extract symbol/asset/ticker for correct filename
        for col in ("symbol", "asset", "ticker"):
            if col in df.columns and isinstance(df[col].iloc[0], str):
                raw = str(df[col].iloc[0])
                token = raw.split("/")[0].split("-")[0]
                return token.upper()
        # Return simple name instead of strategy name to avoid complex paths
        return "DATA"

    def _validate_dataframe(self, df: pd.DataFrame) -> bool:
        """
        Validate input DataFrame for basic requirements.
        
        Args:
            df (pd.DataFrame): DataFrame to validate
            
        Returns:
            bool: True if valid, False otherwise
        """
        if df.empty:
            return False
            
        # Check for required columns (at least one price column)
        price_columns = ['close', 'high', 'low', 'open']
        if not any(col in df.columns for col in price_columns):
            return False
            
        # Check for excessive NaN values
        for col in price_columns:
            if col in df.columns:
                nan_ratio = df[col].isna().sum() / len(df)
                if nan_ratio > 0.1:  # More than 10% NaN values
                    return False
                    
        return True

    def _ensure_indicators_and_save(self, df: pd.DataFrame) -> None:
        """
        Ensure required indicators are calculated via Analytic.
        
        Args:
            df (pd.DataFrame): DataFrame to calculate indicators for
        """
        # Validate input data first
        if not self._validate_dataframe(df):
            raise ValueError(f"[{self.name}] Invalid DataFrame: missing price columns or too many NaN values")
            
        # Lazy import to avoid circular dependencies
        from BOTS.analbot import Analytic  # type: ignore
        
        indicators, stratparams = self.check_indicators()
        # Используем более гибкое имя для файла
        data_name = self._resolve_data_name(df)
        anal = Analytic(df=df, data_name=data_name, output_file="1m_anal.csv", create_cache_dir=False)
        anal.make_calc(indicators=indicators, stratparams=stratparams, parallel=False)
        if self._save_after_init:
            anal._save_results_to_csv()  # noqa: SLF001

    def __str__(self) -> str:
        """
        String representation of the strategy.

        Returns:
            str: String representation including name and parameters
        """
        return f"{self.name}(params={self.params})"
