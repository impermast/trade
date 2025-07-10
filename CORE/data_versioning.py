# CORE/data_versioning.py

import os
import json
import hashlib
import pandas as pd
import datetime
from typing import Dict, List, Optional, Union, Any, Tuple
import logging
import shutil
from pathlib import Path

from CORE.error_handling import DataError


class DataVersion:
    """
    Represents a version of a dataset.
    
    Attributes:
        version_id: Unique identifier for the version
        dataset_id: Identifier for the dataset
        timestamp: When the version was created
        metadata: Additional information about the version
        hash: Hash of the data content
    """
    
    def __init__(self, version_id: str, dataset_id: str, timestamp: datetime.datetime,
                metadata: Dict[str, Any], hash_value: str):
        """
        Initialize a DataVersion.
        
        Args:
            version_id: Unique identifier for the version
            dataset_id: Identifier for the dataset
            timestamp: When the version was created
            metadata: Additional information about the version
            hash_value: Hash of the data content
        """
        self.version_id = version_id
        self.dataset_id = dataset_id
        self.timestamp = timestamp
        self.metadata = metadata
        self.hash = hash_value
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the version to a dictionary.
        
        Returns:
            Dictionary representation of the version
        """
        return {
            'version_id': self.version_id,
            'dataset_id': self.dataset_id,
            'timestamp': self.timestamp.isoformat(),
            'metadata': self.metadata,
            'hash': self.hash
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'DataVersion':
        """
        Create a DataVersion from a dictionary.
        
        Args:
            data: Dictionary representation of the version
            
        Returns:
            DataVersion instance
        """
        return cls(
            version_id=data['version_id'],
            dataset_id=data['dataset_id'],
            timestamp=datetime.datetime.fromisoformat(data['timestamp']),
            metadata=data['metadata'],
            hash_value=data['hash']
        )


class DataVersioningSystem:
    """
    System for versioning datasets.
    
    This class provides functionality for creating, retrieving, and managing
    versions of datasets. It stores version metadata in a JSON file and the
    actual data in separate files.
    
    Attributes:
        base_dir: Base directory for storing versioned data
        logger: Logger instance for logging versioning operations
    """
    
    def __init__(self, base_dir: str = "DATA/versions", logger: Optional[logging.Logger] = None):
        """
        Initialize the DataVersioningSystem.
        
        Args:
            base_dir: Base directory for storing versioned data
            logger: Logger instance (None to create a new one)
        """
        self.base_dir = base_dir
        
        if logger is None:
            from BOTS.loggerbot import Logger
            self.logger = Logger(
                name="DataVersioning", 
                tag="[VERSIONING]", 
                logfile="LOGS/data_versioning.log", 
                console=True
            ).get_logger()
        else:
            self.logger = logger
        
        # Create the base directory if it doesn't exist
        os.makedirs(self.base_dir, exist_ok=True)
        
        # Create the metadata directory if it doesn't exist
        os.makedirs(os.path.join(self.base_dir, "metadata"), exist_ok=True)
        
        # Create the data directory if it doesn't exist
        os.makedirs(os.path.join(self.base_dir, "data"), exist_ok=True)
        
        self.logger.info(f"Initialized DataVersioningSystem with base_dir={base_dir}")
    
    def _get_metadata_path(self, dataset_id: str) -> str:
        """
        Get the path to the metadata file for a dataset.
        
        Args:
            dataset_id: Identifier for the dataset
            
        Returns:
            Path to the metadata file
        """
        return os.path.join(self.base_dir, "metadata", f"{dataset_id}.json")
    
    def _get_data_path(self, version_id: str) -> str:
        """
        Get the path to the data file for a version.
        
        Args:
            version_id: Unique identifier for the version
            
        Returns:
            Path to the data file
        """
        return os.path.join(self.base_dir, "data", f"{version_id}.csv")
    
    def _load_metadata(self, dataset_id: str) -> List[Dict[str, Any]]:
        """
        Load metadata for a dataset.
        
        Args:
            dataset_id: Identifier for the dataset
            
        Returns:
            List of version metadata dictionaries
        """
        metadata_path = self._get_metadata_path(dataset_id)
        if not os.path.exists(metadata_path):
            return []
        
        try:
            with open(metadata_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            self.logger.error(f"Error loading metadata for {dataset_id}: {e}")
            return []
    
    def _save_metadata(self, dataset_id: str, versions: List[Dict[str, Any]]) -> bool:
        """
        Save metadata for a dataset.
        
        Args:
            dataset_id: Identifier for the dataset
            versions: List of version metadata dictionaries
            
        Returns:
            True if successful, False otherwise
        """
        metadata_path = self._get_metadata_path(dataset_id)
        try:
            with open(metadata_path, 'w') as f:
                json.dump(versions, f, indent=2)
            return True
        except Exception as e:
            self.logger.error(f"Error saving metadata for {dataset_id}: {e}")
            return False
    
    def _compute_hash(self, df: pd.DataFrame) -> str:
        """
        Compute a hash of a DataFrame.
        
        Args:
            df: DataFrame to hash
            
        Returns:
            Hash of the DataFrame
        """
        # Convert DataFrame to a string representation and hash it
        df_str = df.to_csv(index=False)
        return hashlib.md5(df_str.encode()).hexdigest()
    
    def create_version(self, dataset_id: str, df: pd.DataFrame, 
                      metadata: Optional[Dict[str, Any]] = None) -> Optional[DataVersion]:
        """
        Create a new version of a dataset.
        
        Args:
            dataset_id: Identifier for the dataset
            df: DataFrame containing the data
            metadata: Additional information about the version
            
        Returns:
            DataVersion instance if successful, None otherwise
        """
        if df.empty:
            self.logger.warning(f"Cannot create version for empty DataFrame: {dataset_id}")
            return None
        
        # Load existing versions
        versions = self._load_metadata(dataset_id)
        
        # Compute hash of the data
        hash_value = self._compute_hash(df)
        
        # Check if this exact data already exists
        for version in versions:
            if version['hash'] == hash_value:
                self.logger.info(f"Data already exists as version {version['version_id']} for {dataset_id}")
                return DataVersion.from_dict(version)
        
        # Generate a new version ID
        timestamp = datetime.datetime.now()
        version_id = f"{dataset_id}_{timestamp.strftime('%Y%m%d%H%M%S')}_{len(versions) + 1}"
        
        # Create metadata
        version_metadata = metadata or {}
        version_metadata.update({
            'rows': len(df),
            'columns': list(df.columns),
            'created_by': 'DataVersioningSystem'
        })
        
        # Create the version object
        version = DataVersion(
            version_id=version_id,
            dataset_id=dataset_id,
            timestamp=timestamp,
            metadata=version_metadata,
            hash_value=hash_value
        )
        
        # Save the data
        data_path = self._get_data_path(version_id)
        try:
            df.to_csv(data_path, index=False)
        except Exception as e:
            self.logger.error(f"Error saving data for {version_id}: {e}")
            return None
        
        # Update and save metadata
        versions.append(version.to_dict())
        if not self._save_metadata(dataset_id, versions):
            # If metadata save fails, delete the data file
            try:
                os.remove(data_path)
            except:
                pass
            return None
        
        self.logger.info(f"Created version {version_id} for {dataset_id}")
        return version
    
    def get_versions(self, dataset_id: str) -> List[DataVersion]:
        """
        Get all versions of a dataset.
        
        Args:
            dataset_id: Identifier for the dataset
            
        Returns:
            List of DataVersion instances
        """
        versions = self._load_metadata(dataset_id)
        return [DataVersion.from_dict(v) for v in versions]
    
    def get_latest_version(self, dataset_id: str) -> Optional[DataVersion]:
        """
        Get the latest version of a dataset.
        
        Args:
            dataset_id: Identifier for the dataset
            
        Returns:
            Latest DataVersion instance or None if no versions exist
        """
        versions = self.get_versions(dataset_id)
        if not versions:
            return None
        
        # Sort by timestamp (newest first)
        versions.sort(key=lambda v: v.timestamp, reverse=True)
        return versions[0]
    
    def get_version(self, version_id: str) -> Optional[DataVersion]:
        """
        Get a specific version by ID.
        
        Args:
            version_id: Unique identifier for the version
            
        Returns:
            DataVersion instance or None if not found
        """
        # Extract dataset_id from version_id
        parts = version_id.split('_')
        if len(parts) < 2:
            self.logger.error(f"Invalid version ID format: {version_id}")
            return None
        
        dataset_id = parts[0]
        versions = self.get_versions(dataset_id)
        
        for version in versions:
            if version.version_id == version_id:
                return version
        
        return None
    
    def load_version_data(self, version: Union[str, DataVersion]) -> Optional[pd.DataFrame]:
        """
        Load the data for a specific version.
        
        Args:
            version: Version ID or DataVersion instance
            
        Returns:
            DataFrame containing the version data or None if not found
        """
        if isinstance(version, str):
            version_obj = self.get_version(version)
            if not version_obj:
                self.logger.error(f"Version not found: {version}")
                return None
            version_id = version
        else:
            version_id = version.version_id
        
        data_path = self._get_data_path(version_id)
        if not os.path.exists(data_path):
            self.logger.error(f"Data file not found for version: {version_id}")
            return None
        
        try:
            df = pd.read_csv(data_path)
            self.logger.info(f"Loaded data for version {version_id}")
            return df
        except Exception as e:
            self.logger.error(f"Error loading data for version {version_id}: {e}")
            return None
    
    def delete_version(self, version: Union[str, DataVersion]) -> bool:
        """
        Delete a specific version.
        
        Args:
            version: Version ID or DataVersion instance
            
        Returns:
            True if successful, False otherwise
        """
        if isinstance(version, str):
            version_obj = self.get_version(version)
            if not version_obj:
                self.logger.error(f"Version not found: {version}")
                return False
            version_id = version
            dataset_id = version_obj.dataset_id
        else:
            version_id = version.version_id
            dataset_id = version.dataset_id
        
        # Load metadata
        versions = self._load_metadata(dataset_id)
        
        # Find and remove the version
        updated_versions = [v for v in versions if v['version_id'] != version_id]
        if len(updated_versions) == len(versions):
            self.logger.error(f"Version not found in metadata: {version_id}")
            return False
        
        # Save updated metadata
        if not self._save_metadata(dataset_id, updated_versions):
            return False
        
        # Delete the data file
        data_path = self._get_data_path(version_id)
        if os.path.exists(data_path):
            try:
                os.remove(data_path)
            except Exception as e:
                self.logger.error(f"Error deleting data file for {version_id}: {e}")
                return False
        
        self.logger.info(f"Deleted version {version_id}")
        return True
    
    def compare_versions(self, version1: Union[str, DataVersion], 
                        version2: Union[str, DataVersion]) -> Dict[str, Any]:
        """
        Compare two versions of a dataset.
        
        Args:
            version1: First version ID or DataVersion instance
            version2: Second version ID or DataVersion instance
            
        Returns:
            Dictionary with comparison results
        """
        # Load the data for both versions
        df1 = self.load_version_data(version1)
        df2 = self.load_version_data(version2)
        
        if df1 is None or df2 is None:
            return {'error': 'One or both versions could not be loaded'}
        
        # Get version objects
        if isinstance(version1, str):
            v1 = self.get_version(version1)
        else:
            v1 = version1
            
        if isinstance(version2, str):
            v2 = self.get_version(version2)
        else:
            v2 = version2
        
        # Basic comparison
        comparison = {
            'version1': v1.version_id,
            'version2': v2.version_id,
            'timestamp1': v1.timestamp.isoformat(),
            'timestamp2': v2.timestamp.isoformat(),
            'rows1': len(df1),
            'rows2': len(df2),
            'columns1': list(df1.columns),
            'columns2': list(df2.columns),
            'identical': df1.equals(df2)
        }
        
        # Column differences
        columns1 = set(df1.columns)
        columns2 = set(df2.columns)
        comparison['columns_only_in_1'] = list(columns1 - columns2)
        comparison['columns_only_in_2'] = list(columns2 - columns1)
        comparison['common_columns'] = list(columns1.intersection(columns2))
        
        # Row count difference
        comparison['row_count_diff'] = len(df1) - len(df2)
        
        return comparison


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
    
    # Create a versioning system
    versioning = DataVersioningSystem()
    
    # Create a version
    version = versioning.create_version("BTCUSDT_1h", df, {"source": "example"})
    print(f"Created version: {version.version_id}")
    
    # Get all versions
    versions = versioning.get_versions("BTCUSDT_1h")
    print(f"Number of versions: {len(versions)}")
    
    # Load the data for a version
    loaded_df = versioning.load_version_data(version)
    print(f"Loaded data shape: {loaded_df.shape}")
    
    # Create a modified version
    df2 = df.copy()
    df2.loc[0, 'close'] = 999  # Modify one value
    version2 = versioning.create_version("BTCUSDT_1h", df2, {"source": "modified"})
    print(f"Created modified version: {version2.version_id}")
    
    # Compare versions
    comparison = versioning.compare_versions(version, version2)
    print(f"Versions identical: {comparison['identical']}")