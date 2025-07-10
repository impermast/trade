# CORE/data_cache.py

import pandas as pd
import time
from typing import Dict, Any, Optional, Tuple, List, Union
import logging
import datetime
import functools
import hashlib
import json

from CORE.error_handling import DataError


class DataCache:
    """
    Cache for OHLCV data to improve performance of repeated queries.
    
    This class provides a memory cache for OHLCV data to avoid repeated database
    queries for the same data. It implements a simple LRU (Least Recently Used)
    cache with configurable size limits and expiration times.
    
    Attributes:
        max_items: Maximum number of items to store in the cache
        ttl_seconds: Time-to-live for cache entries in seconds
        logger: Logger instance for logging cache operations
    """
    
    def __init__(self, max_items: int = 100, ttl_seconds: int = 3600, 
                logger: Optional[logging.Logger] = None):
        """
        Initialize the DataCache.
        
        Args:
            max_items: Maximum number of items to store in the cache
            ttl_seconds: Time-to-live for cache entries in seconds
            logger: Logger instance (None to create a new one)
        """
        self.max_items = max_items
        self.ttl_seconds = ttl_seconds
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._access_times: Dict[str, float] = {}
        
        if logger is None:
            from BOTS.loggerbot import Logger
            self.logger = Logger(
                name="DataCache", 
                tag="[CACHE]", 
                logfile="LOGS/data_cache.log", 
                console=True
            ).get_logger()
        else:
            self.logger = logger
            
        self.logger.info(f"Initialized DataCache with max_items={max_items}, ttl_seconds={ttl_seconds}")
    
    def _generate_key(self, *args, **kwargs) -> str:
        """
        Generate a cache key from the function arguments.
        
        Args:
            *args: Positional arguments
            **kwargs: Keyword arguments
            
        Returns:
            Cache key as a string
        """
        # Convert args and kwargs to a string representation
        key_dict = {
            'args': args,
            'kwargs': kwargs
        }
        
        # Convert to a JSON string and hash it
        key_str = json.dumps(key_dict, sort_keys=True, default=str)
        return hashlib.md5(key_str.encode()).hexdigest()
    
    def _is_expired(self, key: str) -> bool:
        """
        Check if a cache entry is expired.
        
        Args:
            key: Cache key
            
        Returns:
            True if the entry is expired, False otherwise
        """
        if key not in self._access_times:
            return True
        
        current_time = time.time()
        last_access_time = self._access_times[key]
        return (current_time - last_access_time) > self.ttl_seconds
    
    def _evict_if_needed(self):
        """
        Evict the least recently used cache entries if the cache is full.
        """
        # First, remove any expired entries
        expired_keys = [k for k in self._cache.keys() if self._is_expired(k)]
        for key in expired_keys:
            self._remove_entry(key)
            self.logger.debug(f"Removed expired cache entry: {key}")
        
        # If still over the limit, remove the least recently used entries
        if len(self._cache) >= self.max_items:
            # Sort by access time (oldest first)
            sorted_keys = sorted(self._access_times.items(), key=lambda x: x[1])
            # Remove the oldest entries until we're under the limit
            for key, _ in sorted_keys[:len(self._cache) - self.max_items + 1]:
                self._remove_entry(key)
                self.logger.debug(f"Evicted LRU cache entry: {key}")
    
    def _remove_entry(self, key: str):
        """
        Remove a cache entry.
        
        Args:
            key: Cache key
        """
        if key in self._cache:
            del self._cache[key]
        if key in self._access_times:
            del self._access_times[key]
    
    def get(self, key: str) -> Optional[Dict[str, Any]]:
        """
        Get a value from the cache.
        
        Args:
            key: Cache key
            
        Returns:
            Cached value or None if not found or expired
        """
        if key not in self._cache or self._is_expired(key):
            return None
        
        # Update access time
        self._access_times[key] = time.time()
        return self._cache[key]
    
    def set(self, key: str, value: Dict[str, Any]):
        """
        Set a value in the cache.
        
        Args:
            key: Cache key
            value: Value to cache
        """
        self._evict_if_needed()
        self._cache[key] = value
        self._access_times[key] = time.time()
    
    def clear(self):
        """
        Clear the cache.
        """
        self._cache.clear()
        self._access_times.clear()
        self.logger.info("Cache cleared")
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.
        
        Returns:
            Dictionary with cache statistics
        """
        return {
            'size': len(self._cache),
            'max_size': self.max_items,
            'ttl_seconds': self.ttl_seconds,
            'oldest_entry_age': max(time.time() - t for t in self._access_times.values()) if self._access_times else 0,
            'newest_entry_age': min(time.time() - t for t in self._access_times.values()) if self._access_times else 0
        }


def cached(cache_instance: DataCache):
    """
    Decorator for caching function results.
    
    Args:
        cache_instance: DataCache instance to use
        
    Returns:
        Decorated function with caching
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Skip caching if the first argument is 'self' and has a 'no_cache' attribute set to True
            if args and hasattr(args[0], 'no_cache') and args[0].no_cache:
                return func(*args, **kwargs)
            
            # Generate a cache key
            cache_key = cache_instance._generate_key(*args, **kwargs)
            
            # Try to get from cache
            cached_result = cache_instance.get(cache_key)
            if cached_result is not None:
                # If it's a DataFrame, return a copy to avoid modifying the cached version
                if 'dataframe' in cached_result:
                    result = cached_result['dataframe'].copy()
                    cache_instance.logger.debug(f"Cache hit for {func.__name__}")
                    return result
                return cached_result['result']
            
            # Not in cache, call the function
            result = func(*args, **kwargs)
            
            # Cache the result
            if isinstance(result, pd.DataFrame):
                cache_instance.set(cache_key, {'dataframe': result})
            else:
                cache_instance.set(cache_key, {'result': result})
            
            cache_instance.logger.debug(f"Cache miss for {func.__name__}, result cached")
            return result
        
        return wrapper
    
    return decorator


# Example usage
if __name__ == "__main__":
    # Create a cache
    cache = DataCache(max_items=10, ttl_seconds=60)
    
    # Define a function that will be cached
    @cached(cache)
    def expensive_calculation(x: int, y: int) -> int:
        print(f"Calculating {x} + {y}...")
        time.sleep(1)  # Simulate an expensive operation
        return x + y
    
    # Call the function multiple times with the same arguments
    print(expensive_calculation(1, 2))  # Should calculate
    print(expensive_calculation(1, 2))  # Should use cache
    print(expensive_calculation(3, 4))  # Should calculate
    print(expensive_calculation(3, 4))  # Should use cache
    
    # Print cache stats
    print(cache.get_stats())