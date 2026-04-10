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
    """Console log formatter (with colors)
    
    格式：2024-08-26 21:04:50.123 [INFO] [base.py:156] 消息内容
    ERROR 级别自动附加堆栈信息
    """

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
        """Format colored log with millisecond timestamp and source location"""
        color = self.COLORS.get(record.levelname, self.COLORS['RESET'])
        reset = self.COLORS['RESET']

        # Timestamp with millisecond precision: 2024-08-26 21:04:50.123
        time_str = datetime.fromtimestamp(record.created).strftime('%Y-%m-%d %H:%M:%S')
        # Add milliseconds
        milliseconds = f"{int(record.msecs):03d}"
        time_str = f"{time_str}.{milliseconds}"

        # Log level (with color)
        level = f"{color}{record.levelname:<8}{reset}"

        # Source file and line number: [base.py:156]
        source = f"[{record.filename}:{record.lineno}]"

        # Message
        message = record.getMessage()

        # Build log line
        log_line = f"{time_str} {level} {source} {message}"

        # ERROR and CRITICAL levels automatically append stack trace
        if record.levelno >= logging.ERROR and record.exc_info:
            stack_trace = self.formatException(record.exc_info)
            log_line = f"{log_line}\n{stack_trace}"

        return log_line


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
        """Add file handler (with rotation)
        
        文件格式：2024-08-26 21:04:50.123 - logger_name - LEVEL - [filename:lineno] - message
        ERROR 级别自动记录堆栈信息
        """
        file_handler = RotatingFileHandler(
            self.log_file,
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding='utf-8'
        )
        file_handler.setLevel(level)
        # Custom formatter with millisecond precision and source location
        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s.%(msecs)03d - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        ))
        self.logger.addHandler(file_handler)

    def _add_error_handler(self, level: int, max_bytes: int, backup_count: int):
        """Add error file handler (only ERROR and above)
        
        文件格式：2024-08-26 21:04:50.123 - logger_name - ERROR - [filename:lineno] - message
        自动记录完整堆栈信息
        """
        error_handler = RotatingFileHandler(
            self.error_file,
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding='utf-8'
        )
        error_handler.setLevel(logging.ERROR)
        # Custom formatter with millisecond precision and source location
        error_handler.setFormatter(logging.Formatter(
            '%(asctime)s.%(msecs)03d - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s',
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

    def error(self, msg: str, exc_info: bool = True, **kwargs):
        """ERROR level log - automatically includes stack trace
        
        Args:
            msg: Error message
            exc_info: Whether to include exception info (default True for automatic stack trace)
            **kwargs: Extra data to log
        """
        self._log(logging.ERROR, msg, exc_info=exc_info, **kwargs)

    def critical(self, msg: str, **kwargs):
        """CRITICAL level log"""
        self._log(logging.CRITICAL, msg, **kwargs)

    def _log(self, level: int, msg: str, **kwargs):
        """Internal log method
        
        Args:
            level: Log level
            msg: Log message
            exc_info: Whether to include exception info (for ERROR level)
            **kwargs: Extra data to log
        """
        # Extract exc_info for ERROR level stack trace
        exc_info = kwargs.pop('exc_info', None)
        
        # Add extra data
        if kwargs:
            # Use standard logging extra parameter to pass extra data
            if exc_info is not None:
                self.logger.log(level, msg, extra={'extra_data': kwargs}, exc_info=exc_info)
            else:
                self.logger.log(level, msg, extra={'extra_data': kwargs})
        else:
            if exc_info is not None:
                self.logger.log(level, msg, exc_info=exc_info)
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
