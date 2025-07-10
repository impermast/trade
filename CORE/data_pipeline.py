# CORE/data_pipeline.py

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Union, Callable, Any, Tuple
import logging
from functools import partial

from CORE.error_handling import DataError
from CORE.data_validation import DataValidator


class DataPipeline:
    """
    Data pipeline for preprocessing OHLCV data.
    
    This class provides a pipeline for preprocessing OHLCV data before analysis
    or storage. It supports various preprocessing steps such as resampling,
    filling missing values, calculating technical indicators, and more.
    
    Attributes:
        logger: Logger instance for logging pipeline operations
        validator: DataValidator instance for validating data
    """
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        """
        Initialize the DataPipeline.
        
        Args:
            logger: Logger instance (None to create a new one)
        """
        if logger is None:
            from BOTS.loggerbot import Logger
            self.logger = Logger(
                name="DataPipeline", 
                tag="[PIPELINE]", 
                logfile="LOGS/data_pipeline.log", 
                console=True
            ).get_logger()
        else:
            self.logger = logger
            
        self.validator = DataValidator(logger=self.logger)
        self.logger.info("Initialized DataPipeline")
    
    def process(self, df: pd.DataFrame, steps: List[Dict[str, Any]]) -> pd.DataFrame:
        """
        Process a DataFrame through a series of preprocessing steps.
        
        Args:
            df: DataFrame to process
            steps: List of preprocessing steps to apply
            
        Returns:
            Processed DataFrame
            
        Raises:
            DataError: If there's an error during processing
        """
        if df.empty:
            self.logger.warning("Empty DataFrame provided for processing")
            return df
        
        # Make a copy to avoid modifying the original
        result_df = df.copy()
        
        # Apply each step in sequence
        for i, step in enumerate(steps):
            try:
                step_type = step.get('type')
                if not step_type:
                    raise DataError(f"Step {i} is missing 'type' field")
                
                self.logger.debug(f"Applying step {i}: {step_type}")
                
                if step_type == 'validate':
                    # Validate the DataFrame
                    strict = step.get('strict', False)
                    is_valid, errors = self.validator.validate_ohlcv_dataframe(result_df, strict=strict)
                    if not is_valid:
                        error_msg = f"Data validation failed:"
                        for err in errors:
                            error_msg += f"\n- {err}"
                        raise DataError(error_msg)
                
                elif step_type == 'clean':
                    # Clean the DataFrame
                    drop_duplicates = step.get('drop_duplicates', True)
                    fill_missing = step.get('fill_missing', True)
                    sort_timestamps = step.get('sort_timestamps', True)
                    result_df = self.validator.clean_ohlcv_dataframe(
                        result_df, 
                        drop_duplicates=drop_duplicates,
                        fill_missing=fill_missing,
                        sort_timestamps=sort_timestamps
                    )
                
                elif step_type == 'resample':
                    # Resample the DataFrame to a different timeframe
                    rule = step.get('rule')
                    if not rule:
                        raise DataError(f"Resample step {i} is missing 'rule' field")
                    
                    agg_dict = step.get('aggregation', {
                        'open': 'first',
                        'high': 'max',
                        'low': 'min',
                        'close': 'last',
                        'volume': 'sum'
                    })
                    
                    # Ensure timestamp is the index for resampling
                    if 'timestamp' in result_df.columns:
                        result_df = result_df.set_index('timestamp')
                    
                    # Resample
                    result_df = result_df.resample(rule).agg(agg_dict)
                    
                    # Reset index to get timestamp back as a column
                    result_df = result_df.reset_index()
                
                elif step_type == 'filter':
                    # Filter rows based on a condition
                    column = step.get('column')
                    if not column:
                        raise DataError(f"Filter step {i} is missing 'column' field")
                    
                    operator = step.get('operator', '>')
                    value = step.get('value')
                    if value is None:
                        raise DataError(f"Filter step {i} is missing 'value' field")
                    
                    # Apply the filter
                    if operator == '>':
                        result_df = result_df[result_df[column] > value]
                    elif operator == '>=':
                        result_df = result_df[result_df[column] >= value]
                    elif operator == '<':
                        result_df = result_df[result_df[column] < value]
                    elif operator == '<=':
                        result_df = result_df[result_df[column] <= value]
                    elif operator == '==':
                        result_df = result_df[result_df[column] == value]
                    elif operator == '!=':
                        result_df = result_df[result_df[column] != value]
                    else:
                        raise DataError(f"Filter step {i} has invalid operator: {operator}")
                
                elif step_type == 'add_indicator':
                    # Add a technical indicator
                    indicator = step.get('indicator')
                    if not indicator:
                        raise DataError(f"Add indicator step {i} is missing 'indicator' field")
                    
                    params = step.get('params', {})
                    
                    # Import indicators dynamically to avoid circular imports
                    from BOTS.indicators import Indicators
                    
                    # Create indicators instance
                    indicators = Indicators(result_df, self.logger)
                    
                    # Call the indicator method
                    if hasattr(indicators, indicator) and callable(getattr(indicators, indicator)):
                        method = getattr(indicators, indicator)
                        result_df = method(**params) or result_df
                    else:
                        raise DataError(f"Unknown indicator: {indicator}")
                
                elif step_type == 'drop_columns':
                    # Drop specified columns
                    columns = step.get('columns', [])
                    if not columns:
                        raise DataError(f"Drop columns step {i} is missing 'columns' field")
                    
                    # Drop only columns that exist
                    columns_to_drop = [col for col in columns if col in result_df.columns]
                    if columns_to_drop:
                        result_df = result_df.drop(columns=columns_to_drop)
                
                elif step_type == 'rename_columns':
                    # Rename columns
                    mapping = step.get('mapping', {})
                    if not mapping:
                        raise DataError(f"Rename columns step {i} is missing 'mapping' field")
                    
                    # Rename only columns that exist
                    columns_to_rename = {k: v for k, v in mapping.items() if k in result_df.columns}
                    if columns_to_rename:
                        result_df = result_df.rename(columns=columns_to_rename)
                
                elif step_type == 'custom':
                    # Apply a custom function
                    func = step.get('function')
                    if not func or not callable(func):
                        raise DataError(f"Custom step {i} is missing 'function' field or it's not callable")
                    
                    args = step.get('args', [])
                    kwargs = step.get('kwargs', {})
                    
                    # Apply the custom function
                    result_df = func(result_df, *args, **kwargs)
                
                else:
                    raise DataError(f"Unknown step type: {step_type}")
                
                # Check if the step produced an empty DataFrame
                if result_df.empty:
                    self.logger.warning(f"Step {i} ({step_type}) produced an empty DataFrame")
                    break
                
            except Exception as e:
                raise DataError(f"Error in preprocessing step {i} ({step_type}): {str(e)}") from e
        
        self.logger.info(f"Preprocessing complete: {len(steps)} steps applied")
        return result_df
    
    def create_pipeline(self, steps: List[Dict[str, Any]]) -> Callable[[pd.DataFrame], pd.DataFrame]:
        """
        Create a reusable pipeline function from a list of steps.
        
        Args:
            steps: List of preprocessing steps to apply
            
        Returns:
            Function that takes a DataFrame and returns a processed DataFrame
        """
        return partial(self.process, steps=steps)


# Example usage
if __name__ == "__main__":
    # Create a sample DataFrame
    data = {
        'timestamp': pd.date_range(start='2023-01-01', periods=10, freq='1H'),
        'open': [100, 101, 102, 103, 104, 105, 106, 107, 108, 109],
        'high': [102, 103, 104, 105, 106, 107, 108, 109, 110, 111],
        'low': [99, 100, 101, 102, 103, 104, 105, 106, 107, 108],
        'close': [101, 102, 103, 104, 105, 106, 107, 108, 109, 110],
        'volume': [1000, 1100, 1200, 1300, 1400, 1500, 1600, 1700, 1800, 1900]
    }
    df = pd.DataFrame(data)
    
    # Create a pipeline
    pipeline = DataPipeline()
    
    # Define preprocessing steps
    steps = [
        {'type': 'validate'},
        {'type': 'clean'},
        {'type': 'resample', 'rule': '2H'},
        {'type': 'add_indicator', 'indicator': 'sma', 'params': {'period': 3}}
    ]
    
    # Process the DataFrame
    result = pipeline.process(df, steps)
    print(result.head())
    
    # Create a reusable pipeline function
    process_func = pipeline.create_pipeline(steps)
    
    # Use the pipeline function
    result2 = process_func(df)
    print(result2.head())