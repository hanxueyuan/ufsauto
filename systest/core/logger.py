#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test Log Manager - Logger

Features:
- Unified logging configuration (Console + File)
- Log file separation by test ID
- Log rotation support (RotatingFileHandler)
- Structured log output (optional JSON format)
- Multi-level logging (DEBUG/INFO/WARNING/ERROR/CRITICAL)

Usage:
    from core.logger import get_logger

    logger = get_logger('test_seq_read', log_dir='logs/')
    logger.info('Test started')
    logger.debug('Detailed information', extra={'metric': 'value'})
"""

import logging
import os
import sys
import json
from pathlib import Path
from datetime import datetime
from logging.handlers import RotatingFileHandler, TimedRotatingFileHandler
from typing import Optional, Dict, Any


class StructuredFormatter(logging.Formatter):
    """Structured log formatter (JSON format)"""

    def format(self, record: logging.LogRecord) -> str:
        """Format as JSON string"""
        log_data = {
            'timestamp': datetime.fromtimestamp(record.created).isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno
        }

        # Add extra fields
        if hasattr(record, 'extra_data'):
            log_data['data'] = record.extra_data

        # Add exception info
        if record.exc_info:
            log_data['exception'] = self.formatException(record.exc_info)

        return json.dumps(log_data, ensure_ascii=False)


class ConsoleFormatter(logging.Formatter):
    """Console log formatter (with colors)"""

    # ANSI color codes
    COLORS = {
        'DEBUG': '\033[36m',      # Cyan
        'INFO': '\033[32m',       # Green
        'WARNING': '\033[33m',    # Yellow
        'ERROR': '\033[31m',      # Red
        'CRITICAL': '\033[35m',   # Purple
        'RESET': '\033[0m'        # Reset
    }

    def format(self, record: logging.LogRecord) -> str:
        """Format colored log"""
        color = self.COLORS.get(record.levelname, self.COLORS['RESET'])
        reset = self.COLORS['RESET']

        # Timestamp
        time_str = datetime.fromtimestamp(record.created).strftime('%H:%M:%S')

        # Log level (with color)
        level = f"{color}{record.levelname:<8}{reset}"

        # Message
        message = record.getMessage()

        # Module info (shown for DEBUG level)
        if record.levelno <= logging.DEBUG:
            module = f"[{record.module}:{record.lineno}]"
            return f"{time_str} {level} {module} {message}"

        return f"{time_str} {level} {message}"


class TestLogger:
    """Test log manager"""

    def __init__(
        self,
        test_id: str,
        log_dir: str = 'logs',
        console_level: int = logging.INFO,
        file_level: int = logging.DEBUG,
        max_bytes: int = 50 * 1024 * 1024,  # 50MB/file
        backup_count: int = 5,
        enable_json: bool = False
    ):
        """
        Initialize log manager

        Args:
            test_id: Test ID (used for log filename)
            log_dir: Log directory
            console_level: Console log level
            file_level: File log level
            max_bytes: Maximum size per log file
            backup_count: Number of backup files to keep
            enable_json: Whether to enable JSON format logging
        """
        self.test_id = test_id
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)

        # Log file paths
        self.log_file = self.log_dir / f"{test_id}.log"
        self.error_file = self.log_dir / f"{test_id}_error.log"

        # Create logger
        self.logger = logging.getLogger(f"systest.{test_id}")
        self.logger.setLevel(logging.DEBUG)  # File logger records all levels

        # Clear existing handlers (avoid duplicates)
        self.logger.handlers.clear()

        # Add console handler
        self._add_console_handler(console_level)

        # Add file handler (with rotation)
        self._add_file_handler(file_level, max_bytes, backup_count)

        # Add error file handler (only ERROR and above)
        self._add_error_handler(file_level, max_bytes, backup_count)

        # JSON formatter (optional)
        self.json_formatter = StructuredFormatter() if enable_json else None

    def _add_console_handler(self, level: int):
        """Add console handler"""
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(level)
        console_handler.setFormatter(ConsoleFormatter())
        self.logger.addHandler(console_handler)

    def _add_file_handler(self, level: int, max_bytes: int, backup_count: int):
        """Add file handler (with rotation)"""
        file_handler = RotatingFileHandler(
            self.log_file,
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding='utf-8'
        )
        file_handler.setLevel(level)
        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        ))
        self.logger.addHandler(file_handler)

    def _add_error_handler(self, level: int, max_bytes: int, backup_count: int):
        """Add error file handler"""
        error_handler = RotatingFileHandler(
            self.error_file,
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding='utf-8'
        )
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        ))
        self.logger.addHandler(error_handler)

    def debug(self, msg: str, **kwargs):
        """DEBUG level log"""
        self._log(logging.DEBUG, msg, **kwargs)

    def info(self, msg: str, **kwargs):
        """INFO level log"""
        self._log(logging.INFO, msg, **kwargs)

    def warning(self, msg: str, **kwargs):
        """WARNING level log"""
        self._log(logging.WARNING, msg, **kwargs)

    def error(self, msg: str, **kwargs):
        """ERROR level log"""
        self._log(logging.ERROR, msg, **kwargs)

    def critical(self, msg: str, **kwargs):
        """CRITICAL level log"""
        self._log(logging.CRITICAL, msg, **kwargs)

    def _log(self, level: int, msg: str, **kwargs):
        """Internal log method"""
        # Add extra data
        if kwargs:
            # Use standard logging extra parameter to pass extra data
            self.logger.log(level, msg, extra={'extra_data': kwargs})
        else:
            self.logger.log(level, msg)

    def log_metric(self, metric_name: str, value: Any, unit: str = ''):
        """Log test metric"""
        self.info(f"Metric: {metric_name} = {value}{unit}", extra={'metric': metric_name, 'value': value, 'unit': unit})

    def log_step(self, step_num: int, step_desc: str):
        """Log test step"""
        self.info(f"[Step {step_num}] {step_desc}", extra={'step': step_num, 'description': step_desc})

    def log_assertion(self, assertion: str, expected: Any, actual: Any, passed: bool):
        """Log assertion result"""
        status = 'PASS' if passed else 'FAIL'
        self.info(
            f"Assertion: {assertion} - {status}",
            extra={
                'assertion': assertion,
                'expected': expected,
                'actual': actual,
                'passed': passed
            }
        )

    def get_log_file(self) -> Path:
        """Get log file path"""
        return self.log_file

    def get_error_file(self) -> Path:
        """Get error log file path"""
        return self.error_file

    def close(self):
        """Close all handlers"""
        for handler in self.logger.handlers[:]:
            handler.close()
            self.logger.removeHandler(handler)


# Global logger instance cache
_loggers: Dict[str, TestLogger] = {}


def get_logger(
    test_id: Optional[str] = None,
    log_dir: str = 'logs',
    **kwargs
) -> TestLogger:
    """
    Get logger instance

    Args:
        test_id: Test ID, uses global logger if not provided
        log_dir: Log directory
        **kwargs: Other parameters passed to TestLogger

    Returns:
        TestLogger instance
    """
    if test_id is None:
        test_id = 'global'

    if test_id not in _loggers:
        _loggers[test_id] = TestLogger(test_id, log_dir, **kwargs)

    return _loggers[test_id]


def close_all_loggers():
    """Close all logger instances"""
    for logger in _loggers.values():
        logger.close()
    _loggers.clear()
