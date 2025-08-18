"""
JSON Field Helper for MySQL compatibility
Handles JSON data storage for both MySQL 5.7+ (native JSON) and older versions (TEXT)
"""

import json
from typing import Any, Optional, Dict, List, Union
from sqlalchemy import Column, Text
from flask import current_app

class JSONFieldHelper:
    """Helper class for handling JSON data in MySQL databases"""
    
    @staticmethod
    def serialize_json(data: Union[Dict, List, Any]) -> Optional[str]:
        """
        Serialize Python object to JSON string
        
        Args:
            data: Python object to serialize
            
        Returns:
            JSON string or None if data is None
        """
        if data is None:
            return None
            
        try:
            return json.dumps(data, ensure_ascii=False, separators=(',', ':'))
        except (TypeError, ValueError) as e:
            current_app.logger.error(f"Error serializing JSON: {e}")
            return None
    
    @staticmethod
    def deserialize_json(json_str: Optional[str]) -> Optional[Union[Dict, List]]:
        """
        Deserialize JSON string to Python object
        
        Args:
            json_str: JSON string to deserialize
            
        Returns:
            Python object or None if json_str is None/invalid
        """
        if not json_str:
            return None
            
        try:
            return json.loads(json_str)
        except (TypeError, ValueError, json.JSONDecodeError) as e:
            current_app.logger.error(f"Error deserializing JSON: {e}")
            return None
    
    @staticmethod
    def create_json_column(nullable: bool = True) -> Column:
        """
        Create a column for JSON data storage
        Uses TEXT column for maximum MySQL compatibility
        
        Args:
            nullable: Whether the column can be NULL
            
        Returns:
            SQLAlchemy Column configured for JSON storage
        """
        return Column(Text, nullable=nullable)
    
    @staticmethod
    def validate_json(data: Any) -> bool:
        """
        Validate that data can be serialized to JSON
        
        Args:
            data: Data to validate
            
        Returns:
            True if data is JSON serializable, False otherwise
        """
        try:
            json.dumps(data)
            return True
        except (TypeError, ValueError):
            return False

class JSONField:
    """
    Descriptor for handling JSON fields in SQLAlchemy models
    Automatically serializes/deserializes JSON data
    """
    
    def __init__(self, column_name: str):
        """
        Initialize JSON field descriptor
        
        Args:
            column_name: Name of the database column storing JSON data
        """
        self.column_name = column_name
    
    def __get__(self, instance, owner):
        """Get JSON data from instance"""
        if instance is None:
            return self
            
        json_str = getattr(instance, self.column_name)
        return JSONFieldHelper.deserialize_json(json_str)
    
    def __set__(self, instance, value):
        """Set JSON data on instance"""
        json_str = JSONFieldHelper.serialize_json(value)
        setattr(instance, self.column_name, json_str)

# Example usage in models:
"""
class ExampleModel(BaseModel):
    # Database column (TEXT for compatibility)
    _config_data = Column(Text, nullable=True)
    
    # JSON property using descriptor
    config_data = JSONField('_config_data')
    
    def set_config(self, key: str, value: Any):
        '''Set a configuration value'''
        config = self.config_data or {}
        config[key] = value
        self.config_data = config
    
    def get_config(self, key: str, default: Any = None):
        '''Get a configuration value'''
        config = self.config_data or {}
        return config.get(key, default)
"""
