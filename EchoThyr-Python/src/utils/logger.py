"""
Logging module for EchoThyr automation
Provides colored console output and file logging with rotation
"""

import logging
import colorlog
from pathlib import Path
from datetime import datetime
from typing import Optional


class EchoThyrLogger:
    """Custom logger with colored console and file output"""

    def __init__(self, log_dir: str = "C:\\EchoThyr\\logs", name: str = "echothyr"):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)

        # Daily log file
        log_file = self.log_dir / f"echothyr_python_{datetime.now().strftime('%Y-%m-%d')}.log"

        # Create logger
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.DEBUG)
        self.logger.handlers.clear()  # Clear existing handlers

        # Console handler with colors
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_formatter = colorlog.ColoredFormatter(
            '[%(asctime)s] [%(log_color)s%(levelname)-8s%(reset)s] %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S',
            log_colors={
                'DEBUG': 'cyan',
                'INFO': 'cyan',
                'WARNING': 'yellow',
                'ERROR': 'red',
                'CRITICAL': 'red,bg_white',
                'SUCCESS': 'green',
            }
        )
        console_handler.setFormatter(console_formatter)

        # File handler
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(logging.DEBUG)
        file_formatter = logging.Formatter(
            '[%(asctime)s] [%(levelname)-8s] %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(file_formatter)

        # Add handlers
        self.logger.addHandler(console_handler)
        self.logger.addHandler(file_handler)

        # Add custom SUCCESS level
        logging.SUCCESS = 25  # Between INFO and WARNING
        logging.addLevelName(logging.SUCCESS, 'SUCCESS')

    def debug(self, msg: str):
        """Log debug message (file only)"""
        self.logger.debug(msg)

    def info(self, msg: str):
        """Log info message"""
        self.logger.info(msg)

    def success(self, msg: str):
        """Log success message"""
        self.logger.log(logging.SUCCESS, msg)

    def warning(self, msg: str):
        """Log warning message"""
        self.logger.warning(msg)

    def error(self, msg: str, exc_info: Optional[Exception] = None):
        """Log error message with optional exception info"""
        self.logger.error(msg, exc_info=exc_info)


# Global logger instance
_logger: Optional[EchoThyrLogger] = None


def get_logger() -> EchoThyrLogger:
    """Get or create global logger instance"""
    global _logger
    if _logger is None:
        _logger = EchoThyrLogger()
    return _logger
