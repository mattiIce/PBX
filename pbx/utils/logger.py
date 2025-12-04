"""
Logging configuration for PBX system
"""
import logging
import os
from datetime import datetime


class PBXLogger:
    """Centralized logging for PBX system"""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self.logger = None

    def setup(self, log_level="INFO", log_file=None, console=True):
        """
        Setup logging configuration

        Args:
            log_level: Logging level (DEBUG, INFO, WARNING, ERROR)
            log_file: Path to log file
            console: Whether to log to console
        """
        self.logger = logging.getLogger("PBX")
        self.logger.setLevel(getattr(logging, log_level))

        # Clear existing handlers
        self.logger.handlers.clear()

        # Format for log messages
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )

        # Console handler
        if console:
            console_handler = logging.StreamHandler()
            console_handler.setFormatter(formatter)
            self.logger.addHandler(console_handler)

        # File handler
        if log_file:
            os.makedirs(os.path.dirname(log_file), exist_ok=True)
            file_handler = logging.FileHandler(log_file)
            file_handler.setFormatter(formatter)
            self.logger.addHandler(file_handler)

    def get_logger(self):
        """Get the logger instance"""
        if self.logger is None:
            self.setup()
        return self.logger


def get_logger():
    """Get PBX logger instance"""
    return PBXLogger().get_logger()
