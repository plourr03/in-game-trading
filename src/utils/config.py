"""Configuration management"""
import yaml
from pathlib import Path
from typing import Dict, Any


def load_config(config_path: str = "config.yaml") -> Dict[str, Any]:
    """
    Load configuration from YAML file.
    
    Args:
        config_path: Path to config file
        
    Returns:
        Configuration dictionary
    """
    config_file = Path(config_path)
    
    if not config_file.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")
    
    with open(config_file, 'r') as f:
        config = yaml.safe_load(f)
    
    return config


def get_db_config(config: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    Get database configuration.
    
    Args:
        config: Configuration dictionary (if None, will load from file)
        
    Returns:
        Database configuration
    """
    if config is None:
        config = load_config()
    
    return config.get('database', {})


def get_paths(config: Dict[str, Any] = None) -> Dict[str, str]:
    """
    Get path configuration.
    
    Args:
        config: Configuration dictionary (if None, will load from file)
        
    Returns:
        Paths dictionary
    """
    if config is None:
        config = load_config()
    
    return config.get('paths', {})

