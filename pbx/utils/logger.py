"""
Logging configuration for PBX system
"""
import logging
import os


class PBXLogger:
    """Centralized logging for PBX system"""

    _instance = None
    _sub_loggers = {}

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
            log_dir = os.path.dirname(log_file)
            if log_dir:  # Only create directory if path includes a directory
                os.makedirs(log_dir, exist_ok=True)
            file_handler = logging.FileHandler(log_file)
            file_handler.setFormatter(formatter)
            self.logger.addHandler(file_handler)

    def get_logger(self):
        """Get the logger instance"""
        if self.logger is None:
            self.setup()
        return self.logger

    def get_sub_logger(self, name, log_file=None, log_level=None, console=True):
        """
        Get or create a sub-logger with its own log file
        
        Args:
            name: Name of the sub-logger (e.g., 'VM_IVR')
            log_file: Optional separate log file for this logger
            log_level: Optional log level (defaults to parent logger level)
            console: Whether to also log to console (default: True)
        
        Returns:
            Logger instance
        """
        if name in self._sub_loggers:
            return self._sub_loggers[name]
        
        # Create sub-logger
        logger = logging.getLogger(f"PBX.{name}")
        
        # Set log level (inherit from parent if not specified)
        if log_level:
            logger.setLevel(getattr(logging, log_level))
        elif self.logger:
            logger.setLevel(self.logger.level)
        else:
            logger.setLevel(logging.INFO)
        
        # Don't propagate to parent logger to avoid duplicate logs
        logger.propagate = False
        
        # Format for log messages
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        # Console handler (if enabled)
        if console:
            console_handler = logging.StreamHandler()
            console_handler.setFormatter(formatter)
            logger.addHandler(console_handler)
        
        # File handler (if log_file specified)
        if log_file:
            log_dir = os.path.dirname(log_file)
            if log_dir:  # Only create directory if path includes a directory
                os.makedirs(log_dir, exist_ok=True)
            file_handler = logging.FileHandler(log_file)
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)
        
        # Cache the logger
        self._sub_loggers[name] = logger
        
        return logger


def get_logger():
    """Get PBX logger instance"""
    return PBXLogger().get_logger()


def get_vm_ivr_logger():
    """Get VM IVR logger instance with dedicated log file"""
    return PBXLogger().get_sub_logger(
        name='VM_IVR',
        log_file='logs/vm_ivr.log',
        console=True  # Also log to console for visibility
    )
