# CORE/data_validation.py

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Union, Tuple, Any
import logging

from CORE.error_handling import DataError


class DataValidator:
    """
    Data validation class for OHLCV (Open, High, Low, Close, Volume) data.
    
    This class provides methods for validating OHLCV data to ensure it meets
    the requirements for storage and analysis.
    
    Attributes:
        logger: Logger instance for logging validation results
    """
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        """
        Initialize the DataValidator.
        
        Args:
            logger: Logger instance (None to create a new one)
        """
        if logger is None:
            from BOTS.loggerbot import Logger
            self.logger = Logger(
                name="DataValidator", 
                tag="[VALIDATION]", 
                logfile="LOGS/data_validation.log", 
                console=True
            ).get_logger()
        else:
            self.logger = logger
    
    def validate_ohlcv_dataframe(self, df: pd.DataFrame, 
                                strict: bool = False) -> Tuple[bool, List[str]]:
        """
        Validate an OHLCV DataFrame.
        
        Args:
            df: DataFrame to validate
            strict: Whether to apply strict validation rules
            
        Returns:
            Tuple of (is_valid, error_messages)
        """
        errors = []
        
        # Check if DataFrame is empty
        if df.empty:
            errors.append("DataFrame is empty")
            return False, errors
        
        # Check for required columns
        required_columns = ['timestamp', 'open', 'high', 'low', 'close', 'volume']
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            errors.append(f"Missing required columns: {missing_columns}")
            return False, errors
        
        # Check data types
        if not pd.api.types.is_datetime64_any_dtype(df['timestamp']):
            try:
                # Try to convert to datetime
                df['timestamp'] = pd.to_datetime(df['timestamp'])
            except Exception as e:
                errors.append(f"Invalid timestamp format: {str(e)}")
        
        # Check for numeric price and volume columns
        numeric_columns = ['open', 'high', 'low', 'close', 'volume']
        for col in numeric_columns:
            if not pd.api.types.is_numeric_dtype(df[col]):
                errors.append(f"Column '{col}' is not numeric")
        
        if errors:
            return False, errors
        
        # Check for missing values
        for col in required_columns:
            if df[col].isnull().any():
                missing_count = df[col].isnull().sum()
                errors.append(f"Column '{col}' has {missing_count} missing values")
        
        # Check for negative prices
        for col in ['open', 'high', 'low', 'close']:
            if (df[col] < 0).any():
                neg_count = (df[col] < 0).sum()
                errors.append(f"Column '{col}' has {neg_count} negative values")
        
        # Check for negative volume (some exchanges report negative volume for special cases)
        if strict and (df['volume'] < 0).any():
            neg_count = (df['volume'] < 0).sum()
            errors.append(f"Column 'volume' has {neg_count} negative values")
        
        # Check high >= low
        if (df['high'] < df['low']).any():
            invalid_count = (df['high'] < df['low']).sum()
            errors.append(f"Found {invalid_count} rows where high < low")
        
        # Check high >= open and high >= close
        if (df['high'] < df['open']).any():
            invalid_count = (df['high'] < df['open']).sum()
            errors.append(f"Found {invalid_count} rows where high < open")
        
        if (df['high'] < df['close']).any():
            invalid_count = (df['high'] < df['close']).sum()
            errors.append(f"Found {invalid_count} rows where high < close")
        
        # Check low <= open and low <= close
        if (df['low'] > df['open']).any():
            invalid_count = (df['low'] > df['open']).sum()
            errors.append(f"Found {invalid_count} rows where low > open")
        
        if (df['low'] > df['close']).any():
            invalid_count = (df['low'] > df['close']).sum()
            errors.append(f"Found {invalid_count} rows where low > close")
        
        # Check for duplicate timestamps
        if df['timestamp'].duplicated().any():
            dup_count = df['timestamp'].duplicated().sum()
            errors.append(f"Found {dup_count} duplicate timestamps")
        
        # Check for sorted timestamps
        if not df['timestamp'].equals(df['timestamp'].sort_values()):
            errors.append("Timestamps are not sorted in ascending order")
        
        # Check for outliers in price data if strict mode is enabled
        if strict:
            for col in ['open', 'high', 'low', 'close']:
                # Use IQR method to detect outliers
                Q1 = df[col].quantile(0.25)
                Q3 = df[col].quantile(0.75)
                IQR = Q3 - Q1
                lower_bound = Q1 - 1.5 * IQR
                upper_bound = Q3 + 1.5 * IQR
                
                outliers = df[(df[col] < lower_bound) | (df[col] > upper_bound)]
                if not outliers.empty:
                    errors.append(f"Found {len(outliers)} potential outliers in '{col}'")
        
        # Return validation result
        is_valid = len(errors) == 0
        return is_valid, errors
    
    def clean_ohlcv_dataframe(self, df: pd.DataFrame, 
                             drop_duplicates: bool = True,
                             fill_missing: bool = True,
                             sort_timestamps: bool = True) -> pd.DataFrame:
        """
        Clean an OHLCV DataFrame by fixing common issues.
        
        Args:
            df: DataFrame to clean
            drop_duplicates: Whether to drop duplicate timestamps
            fill_missing: Whether to fill missing values
            sort_timestamps: Whether to sort by timestamp
            
        Returns:
            Cleaned DataFrame
        """
        if df.empty:
            return df
        
        # Make a copy to avoid modifying the original
        cleaned_df = df.copy()
        
        # Convert timestamp to datetime if needed
        if not pd.api.types.is_datetime64_any_dtype(cleaned_df['timestamp']):
            try:
                cleaned_df['timestamp'] = pd.to_datetime(cleaned_df['timestamp'])
            except Exception as e:
                self.logger.warning(f"Could not convert timestamps to datetime: {str(e)}")
        
        # Sort by timestamp if requested
        if sort_timestamps:
            cleaned_df = cleaned_df.sort_values('timestamp')
        
        # Drop duplicate timestamps if requested
        if drop_duplicates:
            original_len = len(cleaned_df)
            cleaned_df = cleaned_df.drop_duplicates(subset=['timestamp'])
            dropped = original_len - len(cleaned_df)
            if dropped > 0:
                self.logger.info(f"Dropped {dropped} duplicate timestamps")
        
        # Fill missing values if requested
        if fill_missing:
            # For price columns, forward fill then backward fill
            for col in ['open', 'high', 'low', 'close']:
                if cleaned_df[col].isnull().any():
                    missing_count = cleaned_df[col].isnull().sum()
                    cleaned_df[col] = cleaned_df[col].fillna(method='ffill').fillna(method='bfill')
                    self.logger.info(f"Filled {missing_count} missing values in '{col}'")
            
            # For volume, fill with 0
            if cleaned_df['volume'].isnull().any():
                missing_count = cleaned_df['volume'].isnull().sum()
                cleaned_df['volume'] = cleaned_df['volume'].fillna(0)
                self.logger.info(f"Filled {missing_count} missing volume values with 0")
        
        # Fix high/low inconsistencies
        # Ensure high is the maximum of open, high, close
        # Ensure low is the minimum of open, low, close
        cleaned_df['high'] = cleaned_df[['open', 'high', 'close']].max(axis=1)
        cleaned_df['low'] = cleaned_df[['open', 'low', 'close']].min(axis=1)
        
        return cleaned_df
    
    def detect_gaps(self, df: pd.DataFrame, timeframe_minutes: int) -> List[Tuple[pd.Timestamp, pd.Timestamp]]:
        """
        Detect gaps in the timestamp sequence.
        
        Args:
            df: DataFrame containing OHLCV data
            timeframe_minutes: Expected time difference between consecutive candles in minutes
            
        Returns:
            List of (start_time, end_time) tuples representing gaps
        """
        if df.empty or len(df) < 2:
            return []
        
        # Ensure DataFrame is sorted by timestamp
        sorted_df = df.sort_values('timestamp')
        
        # Calculate expected time delta
        expected_delta = pd.Timedelta(minutes=timeframe_minutes)
        
        # Calculate actual time deltas
        timestamps = sorted_df['timestamp'].values
        gaps = []
        
        for i in range(1, len(timestamps)):
            actual_delta = timestamps[i] - timestamps[i-1]
            if actual_delta > expected_delta * 1.5:  # Allow some tolerance
                gaps.append((timestamps[i-1], timestamps[i]))
        
        return gaps


# Example usage
if __name__ == "__main__":
    # Create a sample DataFrame with some issues
    data = {
        'timestamp': pd.date_range(start='2023-01-01', periods=10, freq='1H'),
        'open': [100, 101, 102, 103, 104, 105, 106, 107, 108, 109],
        'high': [102, 103, 104, 105, 106, 107, 108, 109, 110, 111],
        'low': [99, 100, 101, 102, 103, 104, 105, 106, 107, 108],
        'close': [101, 102, 103, 104, 105, 106, 107, 108, 109, 110],
        'volume': [1000, 1100, 1200, 1300, 1400, 1500, 1600, 1700, 1800, 1900]
    }
    df = pd.DataFrame(data)
    
    # Create a validator and validate the DataFrame
    validator = DataValidator()
    is_valid, errors = validator.validate_ohlcv_dataframe(df)
    
    print(f"DataFrame is valid: {is_valid}")
    if not is_valid:
        for error in errors:
            print(f"- {error}")
    
    # Clean the DataFrame
    cleaned_df = validator.clean_ohlcv_dataframe(df)
    
    # Detect gaps
    gaps = validator.detect_gaps(df, timeframe_minutes=60)
    if gaps:
        print(f"Found {len(gaps)} gaps in the data:")
        for start, end in gaps:
            print(f"- Gap from {start} to {end}")