"""
Centralized logging configuration for the Meme Coin Analyzer Bot
"""

import logging
import sys
from config.settings import LOG_LEVEL, LOG_FORMAT

def setup_logging(name: str = None, level: str = None) -> logging.Logger:
    """
    Setup logging configuration
    
    Args:
        name: Logger name (defaults to __name__)
        level: Log level (defaults to LOG_LEVEL from settings)
    
    Returns:
        Configured logger instance
    """
    if name is None:
        name = __name__
    
    if level is None:
        level = LOG_LEVEL
    
    # Create logger
    logger = logging.getLogger(name)
    
    # Set level
    logger.setLevel(getattr(logging, level.upper()))
    
    # Avoid duplicate handlers
    if not logger.handlers:
        # Create console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(getattr(logging, level.upper()))
        
        # Create formatter
        formatter = logging.Formatter(LOG_FORMAT)
        console_handler.setFormatter(formatter)
        
        # Add handler to logger
        logger.addHandler(console_handler)
    
    return logger

def get_logger(name: str = None) -> logging.Logger:
    """
    Get a configured logger instance
    
    Args:
        name: Logger name (defaults to __name__)
    
    Returns:
        Configured logger instance
    """
    return setup_logging(name)

# Create default logger
default_logger = get_logger(__name__)
