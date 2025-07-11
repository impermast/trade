# BOTS/databot.py

import os
import pandas as pd
import sqlite3
from typing import Optional, List, Dict, Any, Union, Tuple, Callable
import datetime
import logging
from pathlib import Path

from sqlalchemy import create_engine, Column, Integer, Float, String, DateTime, ForeignKey, Index, func, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship, Session
from sqlalchemy.exc import SQLAlchemyError

from CORE.error_handling import with_error_handling, DataError, get_error_logger
from CORE.data_validation import DataValidator
from CORE.data_cache import DataCache, cached
from CORE.data_pipeline import DataPipeline
from CORE.data_versioning import DataVersioningSystem, DataVersion
from BOTS.loggerbot import Logger

# Define the base class for SQLAlchemy models
Base = declarative_base()

# Define the database models
class Exchange(Base):
    """Model for cryptocurrency exchanges."""
    __tablename__ = 'exchanges'

    id = Column(Integer, primary_key=True)
    name = Column(String(50), unique=True, nullable=False)

    # Relationships
    symbols = relationship("Symbol", back_populates="exchange")

    def __repr__(self):
        return f"<Exchange(name='{self.name}')>"


class Symbol(Base):
    """Model for trading pairs (symbols)."""
    __tablename__ = 'symbols'

    id = Column(Integer, primary_key=True)
    name = Column(String(20), nullable=False)
    base_currency = Column(String(10), nullable=False)
    quote_currency = Column(String(10), nullable=False)
    exchange_id = Column(Integer, ForeignKey('exchanges.id'), nullable=False)

    # Relationships
    exchange = relationship("Exchange", back_populates="symbols")
    candles = relationship("OHLCV", back_populates="symbol")

    # Constraints
    __table_args__ = (
        Index('idx_symbol_exchange', 'name', 'exchange_id', unique=True),
    )

    def __repr__(self):
        return f"<Symbol(name='{self.name}', exchange='{self.exchange.name}')>"


class Timeframe(Base):
    """Model for timeframes (1m, 5m, 1h, etc.)."""
    __tablename__ = 'timeframes'

    id = Column(Integer, primary_key=True)
    name = Column(String(10), unique=True, nullable=False)
    minutes = Column(Integer, nullable=False)  # Duration in minutes

    # Relationships
    candles = relationship("OHLCV", back_populates="timeframe")

    def __repr__(self):
        return f"<Timeframe(name='{self.name}', minutes={self.minutes})>"


class OHLCV(Base):
    """Model for OHLCV (Open, High, Low, Close, Volume) data."""
    __tablename__ = 'ohlcv'

    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime, nullable=False)
    open = Column(Float, nullable=False)
    high = Column(Float, nullable=False)
    low = Column(Float, nullable=False)
    close = Column(Float, nullable=False)
    volume = Column(Float, nullable=False)
    symbol_id = Column(Integer, ForeignKey('symbols.id'), nullable=False)
    timeframe_id = Column(Integer, ForeignKey('timeframes.id'), nullable=False)

    # Relationships
    symbol = relationship("Symbol", back_populates="candles")
    timeframe = relationship("Timeframe", back_populates="candles")

    # Constraints
    __table_args__ = (
        Index('idx_ohlcv_symbol_timeframe_timestamp', 'symbol_id', 'timeframe_id', 'timestamp', unique=True),
        Index('idx_ohlcv_timestamp', 'timestamp'),
    )

    def __repr__(self):
        return f"<OHLCV(symbol='{self.symbol.name}', timeframe='{self.timeframe.name}', timestamp='{self.timestamp}')>"


class DataManager:
    """
    Manager for storing and retrieving historical market data.

    This class provides an interface for storing OHLCV data in a SQLite database,
    as well as methods for retrieving and managing the data.

    Attributes:
        db_path: Path to the SQLite database file
        engine: SQLAlchemy engine
        Session: SQLAlchemy session factory
        logger: Logger instance
    """

    DEFAULT_DB_PATH = "DATA/market_data.db"

    def __init__(self, db_path: Optional[str] = None, echo: bool = False, 
                 cache_size: int = 100, cache_ttl: int = 3600, use_cache: bool = True):
        """
        Initialize the DataManager.

        Args:
            db_path: Path to the SQLite database file (None for default)
            echo: Whether to echo SQL statements (for debugging)
            cache_size: Maximum number of items to store in the cache
            cache_ttl: Time-to-live for cache entries in seconds
            use_cache: Whether to use caching
        """
        self.db_path = db_path or self.DEFAULT_DB_PATH
        self.logger = get_error_logger(name="DataManager", tag="[DATA]",
                                      logfile="LOGS/data_manager.log", console=True)

        # Initialize the data validator
        self.validator = DataValidator(logger=self.logger)

        # Initialize the data cache
        self.cache = DataCache(max_items=cache_size, ttl_seconds=cache_ttl, logger=self.logger)
        self.use_cache = use_cache

        # Initialize the data pipeline
        self.pipeline = DataPipeline(logger=self.logger)

        # Ensure the directory exists
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)

        # Create the database engine and session factory
        self.engine = create_engine(f"sqlite:///{self.db_path}", echo=echo)
        self.Session = sessionmaker(bind=self.engine)

        # Initialize the database
        self._initialize_database()

        self.logger.info(f"DataManager initialized with database at {self.db_path}")
        if use_cache:
            self.logger.info(f"Caching enabled with size={cache_size}, ttl={cache_ttl}s")
        else:
            self.logger.info("Caching disabled")

    @with_error_handling(reraise_as=DataError)
    def _initialize_database(self):
        """
        Initialize the database by creating tables and default data.

        This method creates the database tables if they don't exist and
        populates them with default data (timeframes, etc.).
        """
        # Create tables
        Base.metadata.create_all(self.engine)

        # Add default timeframes if they don't exist
        default_timeframes = [
            {"name": "1m", "minutes": 1},
            {"name": "5m", "minutes": 5},
            {"name": "15m", "minutes": 15},
            {"name": "30m", "minutes": 30},
            {"name": "1h", "minutes": 60},
            {"name": "4h", "minutes": 240},
            {"name": "1d", "minutes": 1440},
            {"name": "1w", "minutes": 10080},
        ]

        with self.Session() as session:
            for tf_data in default_timeframes:
                tf = session.query(Timeframe).filter_by(name=tf_data["name"]).first()
                if not tf:
                    tf = Timeframe(name=tf_data["name"], minutes=tf_data["minutes"])
                    session.add(tf)
            session.commit()

    @with_error_handling(reraise_as=DataError)
    def get_or_create_exchange(self, session: Session, exchange_name: str) -> Exchange:
        """
        Get or create an exchange record.

        Args:
            session: SQLAlchemy session
            exchange_name: Name of the exchange

        Returns:
            Exchange object
        """
        exchange = session.query(Exchange).filter_by(name=exchange_name).first()
        if not exchange:
            exchange = Exchange(name=exchange_name)
            session.add(exchange)
            session.flush()  # Flush to get the ID
        return exchange

    @with_error_handling(reraise_as=DataError)
    def get_or_create_symbol(self, session: Session, symbol_name: str, exchange_name: str) -> Symbol:
        """
        Get or create a symbol record.

        Args:
            session: SQLAlchemy session
            symbol_name: Name of the symbol (e.g., "BTC/USDT")
            exchange_name: Name of the exchange

        Returns:
            Symbol object
        """
        exchange = self.get_or_create_exchange(session, exchange_name)

        symbol = session.query(Symbol).join(Exchange).filter(
            Symbol.name == symbol_name,
            Exchange.name == exchange_name
        ).first()

        if not symbol:
            # Parse base and quote currencies from symbol name
            if '/' in symbol_name:
                base, quote = symbol_name.split('/')
            else:
                # Default parsing for symbols without separator
                # Common quote currencies
                common_quotes = ['USDT', 'USD', 'BTC', 'ETH', 'USDC', 'BUSD', 'EUR', 'GBP', 'JPY']

                # Try to find a matching quote currency
                found = False
                for quote_currency in common_quotes:
                    if symbol_name.endswith(quote_currency):
                        quote = quote_currency
                        base = symbol_name[:-len(quote_currency)]
                        found = True
                        break

                # If no match found, use a heuristic approach
                if not found:
                    # Assume the quote currency is 3-4 characters
                    quote_length = 4 if len(symbol_name) > 5 else 3
                    base = symbol_name[:-quote_length]
                    quote = symbol_name[-quote_length:]

            symbol = Symbol(
                name=symbol_name,
                base_currency=base,
                quote_currency=quote,
                exchange_id=exchange.id
            )
            session.add(symbol)
            session.flush()  # Flush to get the ID

        return symbol

    @with_error_handling(reraise_as=DataError)
    def get_timeframe(self, session: Session, timeframe_name: str) -> Timeframe:
        """
        Get a timeframe record.

        Args:
            session: SQLAlchemy session
            timeframe_name: Name of the timeframe (e.g., "1h")

        Returns:
            Timeframe object

        Raises:
            DataError: If the timeframe doesn't exist
        """
        timeframe = session.query(Timeframe).filter_by(name=timeframe_name).first()
        if not timeframe:
            raise DataError(f"Timeframe '{timeframe_name}' not found")
        return timeframe

    @with_error_handling(reraise_as=DataError)
    def store_ohlcv_data(self, df: pd.DataFrame, symbol_name: str, 
                        exchange_name: str, timeframe_name: str,
                        validate: bool = True, clean: bool = True) -> int:
        """
        Store OHLCV data in the database.

        Args:
            df: DataFrame containing OHLCV data
            symbol_name: Name of the symbol (e.g., "BTC/USDT")
            exchange_name: Name of the exchange
            timeframe_name: Name of the timeframe (e.g., "1h")
            validate: Whether to validate the data before storing
            clean: Whether to clean the data before storing

        Returns:
            Number of records stored

        Raises:
            DataError: If there's an error storing the data or validation fails
        """
        if df.empty:
            self.logger.warning(f"Empty DataFrame provided for {symbol_name} {timeframe_name}")
            return 0

        # Validate the data if requested
        if validate:
            is_valid, errors = self.validator.validate_ohlcv_dataframe(df)
            if not is_valid:
                error_msg = f"Data validation failed for {symbol_name} {timeframe_name}:"
                for err in errors:
                    error_msg += f"\n- {err}"
                raise DataError(error_msg)

        # Clean the data if requested
        if clean:
            self.logger.info(f"Cleaning data for {symbol_name} {timeframe_name}")
            df = self.validator.clean_ohlcv_dataframe(df)

        # Ensure the DataFrame has the required columns (even after validation)
        required_columns = ['timestamp', 'open', 'high', 'low', 'close', 'volume']
        if not all(col in df.columns for col in required_columns):
            missing = [col for col in required_columns if col not in df.columns]
            raise DataError(f"DataFrame missing required columns: {missing}")

        # Convert timestamp to datetime if it's not already
        if not pd.api.types.is_datetime64_any_dtype(df['timestamp']):
            df['timestamp'] = pd.to_datetime(df['timestamp'])

        with self.Session() as session:
            try:
                # Get or create symbol and timeframe
                symbol = self.get_or_create_symbol(session, symbol_name, exchange_name)
                timeframe = self.get_timeframe(session, timeframe_name)

                # Prepare data for bulk insert
                records_added = 0

                # Process in chunks to avoid memory issues with large DataFrames
                chunk_size = 1000
                for i in range(0, len(df), chunk_size):
                    chunk = df.iloc[i:i+chunk_size]

                    # Check for existing records to avoid duplicates
                    for _, row in chunk.iterrows():
                        timestamp = row['timestamp']

                        # Check if record already exists
                        existing = session.query(OHLCV).filter(
                            OHLCV.symbol_id == symbol.id,
                            OHLCV.timeframe_id == timeframe.id,
                            OHLCV.timestamp == timestamp
                        ).first()

                        if not existing:
                            # Create new record
                            ohlcv = OHLCV(
                                timestamp=timestamp,
                                open=row['open'],
                                high=row['high'],
                                low=row['low'],
                                close=row['close'],
                                volume=row['volume'],
                                symbol_id=symbol.id,
                                timeframe_id=timeframe.id
                            )
                            session.add(ohlcv)
                            records_added += 1

                session.commit()
                self.logger.info(f"Stored {records_added} new records for {symbol_name} {timeframe_name}")
                return records_added

            except Exception as e:
                session.rollback()
                raise DataError(f"Error storing OHLCV data: {str(e)}") from e

    @with_error_handling(reraise_as=DataError)
    def get_ohlcv_data(self, symbol_name: str, exchange_name: str, timeframe_name: str,
                      start_date: Optional[Union[str, datetime.datetime]] = None,
                      end_date: Optional[Union[str, datetime.datetime]] = None,
                      limit: Optional[int] = None,
                      preprocessing_steps: Optional[List[Dict[str, Any]]] = None) -> pd.DataFrame:
        """
        Retrieve OHLCV data from the database.

        Args:
            symbol_name: Name of the symbol (e.g., "BTC/USDT")
            exchange_name: Name of the exchange
            timeframe_name: Name of the timeframe (e.g., "1h")
            start_date: Start date for the data (None for no limit)
            end_date: End date for the data (None for no limit)
            limit: Maximum number of records to retrieve (None for no limit)
            preprocessing_steps: List of preprocessing steps to apply to the data (None for no preprocessing)

        Returns:
            DataFrame containing OHLCV data

        Raises:
            DataError: If there's an error retrieving the data
        """
        # Use cache if caching is enabled
        if self.use_cache:
            # Generate a cache key
            cache_key = f"{symbol_name}_{exchange_name}_{timeframe_name}"
            if start_date:
                cache_key += f"_from_{start_date}"
            if end_date:
                cache_key += f"_to_{end_date}"
            if limit:
                cache_key += f"_limit_{limit}"

            # Try to get from cache
            cached_result = self.cache.get(cache_key)
            if cached_result is not None and 'dataframe' in cached_result:
                df = cached_result['dataframe'].copy()
                self.logger.debug(f"Cache hit for {symbol_name} {timeframe_name}")
                return df

        # Convert string dates to datetime if needed
        if isinstance(start_date, str):
            start_date = pd.to_datetime(start_date)
        if isinstance(end_date, str):
            end_date = pd.to_datetime(end_date)

        with self.Session() as session:
            try:
                # Build the query
                query = session.query(OHLCV).join(Symbol).join(Exchange).join(Timeframe).filter(
                    Symbol.name == symbol_name,
                    Exchange.name == exchange_name,
                    Timeframe.name == timeframe_name
                )

                # Apply date filters if provided
                if start_date:
                    query = query.filter(OHLCV.timestamp >= start_date)
                if end_date:
                    query = query.filter(OHLCV.timestamp <= end_date)

                # Order by timestamp
                query = query.order_by(OHLCV.timestamp)

                # Apply limit if provided
                if limit:
                    query = query.limit(limit)

                # Execute the query and convert to DataFrame
                result = query.all()

                if not result:
                    self.logger.warning(f"No data found for {symbol_name} {timeframe_name}")
                    return pd.DataFrame(columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])

                data = []
                for row in result:
                    data.append({
                        'timestamp': row.timestamp,
                        'open': row.open,
                        'high': row.high,
                        'low': row.low,
                        'close': row.close,
                        'volume': row.volume
                    })

                df = pd.DataFrame(data)
                self.logger.info(f"Retrieved {len(df)} records for {symbol_name} {timeframe_name}")

                # Apply preprocessing if requested
                if preprocessing_steps:
                    df = self.preprocess_data(df, preprocessing_steps)
                    self.logger.info(f"Applied preprocessing to {symbol_name} {timeframe_name} data")

                # Cache the result if caching is enabled
                if self.use_cache:
                    self.cache.set(cache_key, {'dataframe': df})
                    self.logger.debug(f"Cached {len(df)} records for {symbol_name} {timeframe_name}")

                return df

            except Exception as e:
                raise DataError(f"Error retrieving OHLCV data: {str(e)}") from e

    @with_error_handling(reraise_as=DataError)
    def get_available_symbols(self, exchange_name: Optional[str] = None) -> List[Dict[str, str]]:
        """
        Get a list of available symbols in the database.

        Args:
            exchange_name: Filter by exchange name (None for all exchanges)

        Returns:
            List of dictionaries with symbol information
        """
        with self.Session() as session:
            query = session.query(Symbol).join(Exchange)

            if exchange_name:
                query = query.filter(Exchange.name == exchange_name)

            symbols = query.all()

            result = []
            for symbol in symbols:
                result.append({
                    'name': symbol.name,
                    'exchange': symbol.exchange.name,
                    'base_currency': symbol.base_currency,
                    'quote_currency': symbol.quote_currency
                })

            return result

    @with_error_handling(reraise_as=DataError)
    def get_available_timeframes(self) -> List[Dict[str, Union[str, int]]]:
        """
        Get a list of available timeframes in the database.

        Returns:
            List of dictionaries with timeframe information
        """
        with self.Session() as session:
            timeframes = session.query(Timeframe).all()

            result = []
            for tf in timeframes:
                result.append({
                    'name': tf.name,
                    'minutes': tf.minutes
                })

            return result

    @with_error_handling(reraise_as=DataError)
    def get_data_range(self, symbol_name: str, exchange_name: str, 
                      timeframe_name: str) -> Tuple[Optional[datetime.datetime], Optional[datetime.datetime]]:
        """
        Get the date range of available data for a symbol and timeframe.

        Args:
            symbol_name: Name of the symbol (e.g., "BTC/USDT")
            exchange_name: Name of the exchange
            timeframe_name: Name of the timeframe (e.g., "1h")

        Returns:
            Tuple of (start_date, end_date), or (None, None) if no data
        """
        with self.Session() as session:
            # Get the symbol and timeframe IDs
            symbol = session.query(Symbol).join(Exchange).filter(
                Symbol.name == symbol_name,
                Exchange.name == exchange_name
            ).first()

            if not symbol:
                return (None, None)

            timeframe = session.query(Timeframe).filter_by(name=timeframe_name).first()

            if not timeframe:
                return (None, None)

            # Get the min and max timestamps
            min_ts = session.query(func.min(OHLCV.timestamp)).filter(
                OHLCV.symbol_id == symbol.id,
                OHLCV.timeframe_id == timeframe.id
            ).scalar()

            max_ts = session.query(func.max(OHLCV.timestamp)).filter(
                OHLCV.symbol_id == symbol.id,
                OHLCV.timeframe_id == timeframe.id
            ).scalar()

            return (min_ts, max_ts)

    @with_error_handling(reraise_as=DataError)
    def preprocess_data(self, df: pd.DataFrame, steps: List[Dict[str, Any]]) -> pd.DataFrame:
        """
        Preprocess OHLCV data using the data pipeline.

        Args:
            df: DataFrame containing OHLCV data
            steps: List of preprocessing steps to apply

        Returns:
            Processed DataFrame

        Raises:
            DataError: If there's an error during preprocessing
        """
        if df.empty:
            self.logger.warning("Empty DataFrame provided for preprocessing")
            return df

        try:
            result_df = self.pipeline.process(df, steps)
            self.logger.info(f"Preprocessed data: {len(df)} rows in, {len(result_df)} rows out")
            return result_df
        except Exception as e:
            raise DataError(f"Error preprocessing data: {str(e)}") from e

    @with_error_handling(reraise_as=DataError)
    def create_pipeline(self, steps: List[Dict[str, Any]]) -> Callable[[pd.DataFrame], pd.DataFrame]:
        """
        Create a reusable pipeline function from a list of steps.

        Args:
            steps: List of preprocessing steps to apply

        Returns:
            Function that takes a DataFrame and returns a processed DataFrame
        """
        return self.pipeline.create_pipeline(steps)

    @with_error_handling(reraise_as=DataError)
    def export_to_csv(self, symbol_name: str, exchange_name: str, timeframe_name: str,
                     start_date: Optional[Union[str, datetime.datetime]] = None,
                     end_date: Optional[Union[str, datetime.datetime]] = None,
                     output_path: Optional[str] = None) -> str:
        """
        Export OHLCV data to a CSV file.

        Args:
            symbol_name: Name of the symbol (e.g., "BTC/USDT")
            exchange_name: Name of the exchange
            timeframe_name: Name of the timeframe (e.g., "1h")
            start_date: Start date for the data (None for no limit)
            end_date: End date for the data (None for no limit)
            output_path: Path to save the CSV file (None for default)

        Returns:
            Path to the saved CSV file

        Raises:
            DataError: If there's an error exporting the data
        """
        # Get the data
        df = self.get_ohlcv_data(
            symbol_name=symbol_name,
            exchange_name=exchange_name,
            timeframe_name=timeframe_name,
            start_date=start_date,
            end_date=end_date
        )

        if df.empty:
            raise DataError(f"No data to export for {symbol_name} {timeframe_name}")

        # Determine the output path
        if not output_path:
            clean_symbol = symbol_name.replace('/', '')
            output_path = f"DATA/{clean_symbol}_{timeframe_name}.csv"

        # Ensure the directory exists
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        # Save to CSV
        df.to_csv(output_path, index=False)
        self.logger.info(f"Exported {len(df)} records to {output_path}")

        return output_path

    @with_error_handling(reraise_as=DataError)
    def import_from_csv(self, csv_path: str, symbol_name: str, exchange_name: str, 
                       timeframe_name: str, validate: bool = True, clean: bool = True) -> int:
        """
        Import OHLCV data from a CSV file.

        Args:
            csv_path: Path to the CSV file
            symbol_name: Name of the symbol (e.g., "BTC/USDT")
            exchange_name: Name of the exchange
            timeframe_name: Name of the timeframe (e.g., "1h")
            validate: Whether to validate the data before storing
            clean: Whether to clean the data before storing

        Returns:
            Number of records imported

        Raises:
            DataError: If there's an error importing the data
        """
        # Check if the file exists
        if not os.path.exists(csv_path):
            raise DataError(f"CSV file not found: {csv_path}")

        # Load the CSV file
        try:
            df = pd.read_csv(csv_path)
            self.logger.info(f"Loaded {len(df)} rows from {csv_path}")
        except Exception as e:
            raise DataError(f"Error reading CSV file: {str(e)}") from e

        # Store the data with validation and cleaning
        return self.store_ohlcv_data(
            df=df,
            symbol_name=symbol_name,
            exchange_name=exchange_name,
            timeframe_name=timeframe_name,
            validate=validate,
            clean=clean
        )

    @with_error_handling(reraise_as=DataError)
    def delete_data(self, symbol_name: str, exchange_name: str, timeframe_name: str,
                   start_date: Optional[Union[str, datetime.datetime]] = None,
                   end_date: Optional[Union[str, datetime.datetime]] = None) -> int:
        """
        Delete OHLCV data from the database.

        Args:
            symbol_name: Name of the symbol (e.g., "BTC/USDT")
            exchange_name: Name of the exchange
            timeframe_name: Name of the timeframe (e.g., "1h")
            start_date: Start date for the data to delete (None for no limit)
            end_date: End date for the data to delete (None for no limit)

        Returns:
            Number of records deleted

        Raises:
            DataError: If there's an error deleting the data
        """
        # Convert string dates to datetime if needed
        if isinstance(start_date, str):
            start_date = pd.to_datetime(start_date)
        if isinstance(end_date, str):
            end_date = pd.to_datetime(end_date)

        with self.Session() as session:
            try:
                # Build the query
                query = session.query(OHLCV).join(Symbol).join(Exchange).join(Timeframe).filter(
                    Symbol.name == symbol_name,
                    Exchange.name == exchange_name,
                    Timeframe.name == timeframe_name
                )

                # Apply date filters if provided
                if start_date:
                    query = query.filter(OHLCV.timestamp >= start_date)
                if end_date:
                    query = query.filter(OHLCV.timestamp <= end_date)

                # Count the records to be deleted
                count = query.count()

                # Delete the records
                query.delete(synchronize_session=False)

                session.commit()
                self.logger.info(f"Deleted {count} records for {symbol_name} {timeframe_name}")
                return count

            except Exception as e:
                session.rollback()
                raise DataError(f"Error deleting OHLCV data: {str(e)}") from e


# Example usage
if __name__ == "__main__":
    # Initialize the data manager
    data_manager = DataManager()

    # Import data from existing CSV files
    data_dir = "DATA"
    for filename in os.listdir(data_dir):
        if filename.endswith(".csv") and not filename.endswith("_anal.csv"):
            # Parse symbol and timeframe from filename
            parts = filename.split("_")
            if len(parts) >= 2:
                symbol = parts[0]
                timeframe = parts[1].replace(".csv", "")

                # Import the data
                csv_path = os.path.join(data_dir, filename)
                try:
                    count = data_manager.import_from_csv(
                        csv_path=csv_path,
                        symbol_name=symbol,
                        exchange_name="bybit",  # Assuming Bybit for existing files
                        timeframe_name=timeframe,
                        validate=True,
                        clean=True
                    )
                    print(f"Imported {count} records from {filename}")
                except Exception as e:
                    print(f"Error importing {filename}: {str(e)}")

    # List available symbols
    symbols = data_manager.get_available_symbols()
    print(f"Available symbols: {symbols}")

    # List available timeframes
    timeframes = data_manager.get_available_timeframes()
    print(f"Available timeframes: {timeframes}")
