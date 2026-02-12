"""
Utility functions for NeuroRecon
"""

import yaml
import logging
import os
from datetime import datetime
from typing import Dict, Any


def load_config(config_path: str = 'config.yaml') -> Dict[str, Any]:
    """
    Load configuration from YAML file
    
    Args:
        config_path: Path to configuration file
        
    Returns:
        Configuration dictionary
        
    Raises:
        FileNotFoundError: If configuration file doesn't exist
    """
    try:
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        return config
    except FileNotFoundError:
        raise FileNotFoundError(
            f"Configuration file not found at {config_path}. "
            f"Please ensure config.yaml exists."
        )


def setup_logging(config: Dict[str, Any]) -> logging.Logger:
    """
    Setup logging configuration
    
    Args:
        config: Configuration dictionary
        
    Returns:
        Logger instance
    """
    log_config = config.get('logging', {})
    log_level = log_config.get('level', 'INFO')
    log_file = log_config.get('log_file', 'logs/neurorecon.log')
    log_format = log_config.get('format', '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    # Create logs directory if it doesn't exist
    os.makedirs(os.path.dirname(log_file), exist_ok=True)
    
    # Configure logging
    logging.basicConfig(
        level=getattr(logging, log_level),
        format=log_format,
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler()
        ]
    )
    
    return logging.getLogger('neurorecon')


def ensure_directories(config: Dict[str, Any]):
    """
    Ensure all required directories exist
    
    Args:
        config: Configuration dictionary
    """
    # Create data directories
    data_config = config.get('data_ingestion', {})
    output_path = data_config.get('output_path', 'data/output/')
    os.makedirs(output_path, exist_ok=True)
    
    # Create input directory
    os.makedirs('data/input/', exist_ok=True)
    
    # Create logs directory
    log_config = config.get('logging', {})
    log_file = log_config.get('log_file', 'logs/neurorecon.log')
    os.makedirs(os.path.dirname(log_file), exist_ok=True)


def format_currency(amount: float) -> str:
    """
    Format amount as currency string
    
    Args:
        amount: Numeric amount
        
    Returns:
        Formatted currency string
    """
    return f"${amount:,.2f}"


def format_percentage(value: float) -> str:
    """
    Format value as percentage string
    
    Args:
        value: Numeric value (0-100)
        
    Returns:
        Formatted percentage string
    """
    return f"{value:.2f}%"


def get_timestamp() -> str:
    """
    Get current timestamp as formatted string
    
    Returns:
        Timestamp string
    """
    return datetime.now().strftime('%Y-%m-%d %H:%M:%S')
