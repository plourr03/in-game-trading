"""Helper utility functions"""
import re
import logging
from typing import Optional


def parse_clock_string(clock_str: str) -> float:
    """
    Parse NBA clock string (e.g., 'PT11M50.00S') to minutes remaining.
    
    Args:
        clock_str: Clock string in format 'PT{M}M{S}S'
        
    Returns:
        Minutes remaining in period as float
        
    Examples:
        >>> parse_clock_string('PT11M50.00S')
        11.833333
        >>> parse_clock_string('PT00M15.50S')
        0.258333
    """
    if not clock_str or clock_str == '':
        return 0.0
        
    # Parse format like PT11M50.00S
    pattern = r'PT(?:(\d+)M)?(?:([\d.]+)S)?'
    match = re.match(pattern, clock_str)
    
    if not match:
        return 0.0
        
    minutes = float(match.group(1) or 0)
    seconds = float(match.group(2) or 0)
    
    return minutes + seconds / 60.0


def safe_divide(numerator: float, denominator: float, default: float = 0.0) -> float:
    """
    Safely divide two numbers, returning default if denominator is zero.
    
    Args:
        numerator: Numerator
        denominator: Denominator
        default: Default value to return if denominator is zero
        
    Returns:
        Result of division or default
    """
    if denominator == 0:
        return default
    return numerator / denominator


def get_logger(name: str, level: int = logging.INFO) -> logging.Logger:
    """
    Get a configured logger instance.
    
    Args:
        name: Logger name (typically __name__)
        level: Logging level
        
    Returns:
        Configured logger
    """
    logger = logging.getLogger(name)
    
    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(level)
    
    return logger

