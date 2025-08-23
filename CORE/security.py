"""
Security utilities for the Trade Project.

This module provides security-related functionality for the Trade Project,
including secure storage for API keys, input validation, and other security measures.
"""

import os
import base64
import json
import logging
from typing import Dict, Any, Optional, Union
from pathlib import Path
import re

# Try to import cryptography for encryption support
try:
    from cryptography.fernet import Fernet
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
    _has_cryptography = True
except ImportError:
    _has_cryptography = False
    logging.warning("cryptography not installed. Secure storage will be disabled.")
    logging.warning("To enable secure storage, install cryptography: pip install cryptography")

from .config import Config


class Security:
    """
    Security utilities for the Trade Project.
    
    This class provides methods for secure storage of API keys, input validation,
    and other security measures.
    """
    
    # Default location for the secure storage file
    _SECURE_STORAGE_FILE = Path(Config.DATA_DIR) / '.secure_storage'
    
    # Default salt for key derivation
    _DEFAULT_SALT = b'trade_project_salt'
    
    @classmethod
    def _get_encryption_key(cls, password: str, salt: Optional[bytes] = None) -> bytes:
        """
        Derive an encryption key from a password.
        
        Args:
            password: Password to derive key from
            salt: Salt for key derivation (uses default if None)
            
        Returns:
            Derived encryption key
        """
        if not _has_cryptography:
            raise ImportError("cryptography package is required for secure storage")
            
        if salt is None:
            salt = cls._DEFAULT_SALT
            
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        
        return base64.urlsafe_b64encode(kdf.derive(password.encode()))
    
    @classmethod
    def store_api_keys(cls, api_key: str, api_secret: str, password: str) -> bool:
        """
        Securely store API keys.
        
        Args:
            api_key: API key to store
            api_secret: API secret to store
            password: Password to encrypt the keys
            
        Returns:
            True if successful, False otherwise
        """
        if not _has_cryptography:
            logging.error("Cannot store API keys securely: cryptography package not installed")
            return False
            
        try:
            # Create data directory if it doesn't exist
            data_dir = Path(Config.DATA_DIR)
            data_dir.mkdir(exist_ok=True)
            
            # Generate encryption key from password
            key = cls._get_encryption_key(password)
            fernet = Fernet(key)
            
            # Prepare data to encrypt
            data = {
                'api_key': api_key,
                'api_secret': api_secret
            }
            
            # Encrypt data
            encrypted_data = fernet.encrypt(json.dumps(data).encode())
            
            # Write to file
            with open(cls._SECURE_STORAGE_FILE, 'wb') as f:
                f.write(encrypted_data)
                
            logging.info("API keys stored securely")
            return True
            
        except Exception as e:
            logging.exception(f"Error storing API keys: {e}")
            return False
    
    @classmethod
    def load_api_keys(cls, password: str) -> Dict[str, str]:
        """
        Load securely stored API keys.
        
        Args:
            password: Password to decrypt the keys
            
        Returns:
            Dictionary containing 'api_key' and 'api_secret'
        """
        if not _has_cryptography:
            logging.error("Cannot load API keys securely: cryptography package not installed")
            return {'api_key': None, 'api_secret': None}
            
        try:
            # Check if secure storage file exists
            if not cls._SECURE_STORAGE_FILE.exists():
                logging.warning("Secure storage file not found")
                return {'api_key': None, 'api_secret': None}
                
            # Generate encryption key from password
            key = cls._get_encryption_key(password)
            fernet = Fernet(key)
            
            # Read and decrypt data
            with open(cls._SECURE_STORAGE_FILE, 'rb') as f:
                encrypted_data = f.read()
                
            decrypted_data = fernet.decrypt(encrypted_data)
            data = json.loads(decrypted_data.decode())
            
            logging.info("API keys loaded securely")
            return data
            
        except Exception as e:
            logging.exception(f"Error loading API keys: {e}")
            return {'api_key': None, 'api_secret': None}
    
    @staticmethod
    def validate_input(value: Any, pattern: Optional[str] = None, 
                      allowed_values: Optional[list] = None, 
                      min_value: Optional[Union[int, float]] = None,
                      max_value: Optional[Union[int, float]] = None) -> bool:
        """
        Validate input to prevent injection attacks.
        
        Args:
            value: Value to validate
            pattern: Regex pattern to match (for strings)
            allowed_values: List of allowed values
            min_value: Minimum allowed value (for numbers)
            max_value: Maximum allowed value (for numbers)
            
        Returns:
            True if valid, False otherwise
        """
        # Check if value is None
        if value is None:
            return False
            
        # Check against allowed values
        if allowed_values is not None and value not in allowed_values:
            return False
            
        # Type-specific validation
        if isinstance(value, (int, float)):
            if min_value is not None and value < min_value:
                return False
            if max_value is not None and value > max_value:
                return False
                
        elif isinstance(value, str):
            # Check against regex pattern
            if pattern is not None and not re.match(pattern, value):
                return False
                
        return True
    
    @staticmethod
    def sanitize_input(value: str) -> str:
        """
        Sanitize input to prevent injection attacks.
        
        Args:
            value: String value to sanitize
            
        Returns:
            Sanitized string
        """
        if not isinstance(value, str):
            return str(value)
            
        # Remove potentially dangerous characters
        sanitized = re.sub(r'[;<>&|]', '', value)
        
        return sanitized
    
    @staticmethod
    def validate_symbol(symbol: str) -> bool:
        """
        Validate trading symbol format.
        
        Args:
            symbol: Trading symbol to validate (e.g., "BTC/USDT")
            
        Returns:
            True if valid, False otherwise
        """
        # Trading symbols typically follow the format BASE/QUOTE
        pattern = r'^[A-Z0-9]+/[A-Z0-9]+$'
        return bool(re.match(pattern, symbol))
    
    @staticmethod
    def validate_order_params(symbol: str, side: str, qty: float, 
                             order_type: str = "market", 
                             price: Optional[float] = None) -> bool:
        """
        Validate order parameters.
        
        Args:
            symbol: Trading pair symbol (e.g., "BTC/USDT")
            side: Order side ("buy" or "sell")
            qty: Order quantity
            order_type: Order type ("market", "limit", etc.)
            price: Order price (required for limit orders)
            
        Returns:
            True if valid, False otherwise
        """
        # Validate symbol
        if not Security.validate_symbol(symbol):
            return False
            
        # Validate side
        if side not in ["buy", "sell"]:
            return False
            
        # Validate quantity
        if not isinstance(qty, (int, float)) or qty <= 0:
            return False
            
        # Validate order type
        if order_type not in ["market", "limit"]:
            return False
            
        # Validate price for limit orders
        if order_type == "limit" and (not isinstance(price, (int, float)) or price <= 0):
            return False
            
        return True