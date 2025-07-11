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

    def __init__(self, name: str = "BaseStrategy", indicators: Optional[List[str]] = None, **params):
        """
        Initialize a strategy with name, required indicators, and parameters.

        Args:
            name (str): Name of the strategy
            indicators (Optional[List[str]]): List of indicators required by the strategy
            **params: Strategy-specific parameters that override default values

        Raises:
            ValueError: If invalid parameters are provided
        """
        self.name = name
        self.indicators = indicators or []

        # Get default parameters and validate user-provided parameters
        default_params = self.default_params()
        self._validate_params(default_params, params)

        # Merge default parameters with user-provided parameters
        self.params = self._merge_with_defaults(default_params, params)

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

    def __str__(self) -> str:
        """
        String representation of the strategy.

        Returns:
            str: String representation including name and parameters
        """
        return f"{self.name}(params={self.params})"
