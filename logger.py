import os
import logging
from logging.handlers import RotatingFileHandler
import sys

def setup_logger(name, log_file='bot.log', level=logging.INFO):
    """Set up logger with specified configuration.
    
    This logger only logs to file, not to console/stdout, to prevent
    overwhelming the console with log messages.
    """
    os.makedirs('logs', exist_ok=True)

    logger = logging.getLogger(name)
    
    # This prevents the logger from passing messages to the root logger
    # which would otherwise show up in the console
    logger.propagate = False

    log_level = os.environ.get('LOG_LEVEL', 'INFO').upper()
    level_dict = {
        'DEBUG': logging.DEBUG,
        'INFO': logging.INFO,
        'WARNING': logging.WARNING,
        'ERROR': logging.ERROR,
        'CRITICAL': logging.CRITICAL
    }
    logger.setLevel(level_dict.get(log_level, logging.INFO))

    # Create a file handler that rotates logs
    f_handler = RotatingFileHandler(
        os.path.join('logs', log_file),
        maxBytes=10*1024*1024,  # 10 MB
        backupCount=3
    )

    # Only log warnings and errors to the console
    c_handler = logging.StreamHandler()
    c_handler.setLevel(logging.WARNING)
    
    # Set the format for log messages
    log_format = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    f_handler.setFormatter(log_format)
    c_handler.setFormatter(log_format)

    # Add handlers to the logger
    logger.addHandler(f_handler)
    logger.addHandler(c_handler)
    
    return logger
