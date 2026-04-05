#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试日志管理器 - Logger

功能:
- 统一日志配置（Console + File）
- 按测试 ID 分离日志文件
- 支持日志轮转（RotatingFileHandler）
- 结构化日志输出（JSON 格式可选）
- 多级别日志（DEBUG/INFO/WARNING/ERROR/CRITICAL）

Usage:
    from core.logger import get_logger
    
    logger = get_logger('test_seq_read', log_dir='logs/')
    logger.info('测试开始')
    logger.debug('详细信息', extra={'metric': 'value'})
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
    """结构化日志格式化器（JSON 格式）"""
    
    def format(self, record: logging.LogRecord) -> str:
        """格式化为 JSON 字符串"""
        log_data = {
            'timestamp': datetime.fromtimestamp(record.created).isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno
        }
        
        # 添加额外字段
        if hasattr(record, 'extra_data'):
            log_data['data'] = record.extra_data
        
        # 添加异常信息
        if record.exc_info:
            log_data['exception'] = self.formatException(record.exc_info)
        
        return json.dumps(log_data, ensure_ascii=False)


class ConsoleFormatter(logging.Formatter):
    """控制台日志格式化器（带颜色）"""
    
    # ANSI 颜色代码
    COLORS = {
        'DEBUG': '\033[36m',      # 青色
        'INFO': '\033[32m',       # 绿色
        'WARNING': '\033[33m',    # 黄色
        'ERROR': '\033[31m',      # 红色
        'CRITICAL': '\033[35m',   # 紫色
        'RESET': '\033[0m'        # 重置
    }
    
    def format(self, record: logging.LogRecord) -> str:
        """格式化带颜色的日志"""
        color = self.COLORS.get(record.levelname, self.COLORS['RESET'])
        reset = self.COLORS['RESET']
        
        # 时间戳
        time_str = datetime.fromtimestamp(record.created).strftime('%H:%M:%S')
        
        # 日志级别（带颜色）
        level = f"{color}{record.levelname:<8}{reset}"
        
        # 消息
        message = record.getMessage()
        
        # 模块信息（DEBUG 级别显示）
        if record.levelno <= logging.DEBUG:
            module = f"[{record.module}:{record.lineno}]"
            return f"{time_str} {level} {module} {message}"
        
        return f"{time_str} {level} {message}"


class TestLogger:
    """测试日志管理器"""
    
    def __init__(
        self,
        test_id: str,
        log_dir: str = 'logs',
        console_level: int = logging.INFO,
        file_level: int = logging.DEBUG,
        max_bytes: int = 10 * 1024 * 1024,  # 10MB
        backup_count: int = 5,
        enable_json: bool = False
    ):
        """
        初始化日志管理器
        
        Args:
            test_id: 测试 ID（用于日志文件名）
            log_dir: 日志目录
            console_level: 控制台日志级别
            file_level: 文件日志级别
            max_bytes: 单个日志文件最大大小
            backup_count: 保留的备份文件数量
            enable_json: 是否启用 JSON 格式日志
        """
        self.test_id = test_id
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        # 日志文件路径
        self.log_file = self.log_dir / f"{test_id}.log"
        self.error_file = self.log_dir / f"{test_id}_error.log"
        
        # 创建 logger
        self.logger = logging.getLogger(f"systest.{test_id}")
        self.logger.setLevel(logging.DEBUG)  # 文件日志记录所有级别
        
        # 清除已有 handler（避免重复）
        self.logger.handlers.clear()
        
        # 添加控制台 handler
        self._add_console_handler(console_level)
        
        # 添加文件 handler（轮转）
        self._add_file_handler(file_level, max_bytes, backup_count)
        
        # 添加错误文件 handler（只记录 ERROR 及以上）
        self._add_error_handler(file_level, max_bytes, backup_count)
        
        # JSON 格式化器（可选）
        self.json_formatter = StructuredFormatter() if enable_json else None
    
    def _add_console_handler(self, level: int):
        """添加控制台 handler"""
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(level)
        console_handler.setFormatter(ConsoleFormatter())
        self.logger.addHandler(console_handler)
    
    def _add_file_handler(self, level: int, max_bytes: int, backup_count: int):
        """添加文件 handler（轮转）"""
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
        """添加错误文件 handler"""
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
        """DEBUG 级别日志"""
        self._log(logging.DEBUG, msg, **kwargs)
    
    def info(self, msg: str, **kwargs):
        """INFO 级别日志"""
        self._log(logging.INFO, msg, **kwargs)
    
    def warning(self, msg: str, **kwargs):
        """WARNING 级别日志"""
        self._log(logging.WARNING, msg, **kwargs)
    
    def error(self, msg: str, **kwargs):
        """ERROR 级别日志"""
        self._log(logging.ERROR, msg, **kwargs)
    
    def critical(self, msg: str, **kwargs):
        """CRITICAL 级别日志"""
        self._log(logging.CRITICAL, msg, **kwargs)
    
    def _log(self, level: int, msg: str, **kwargs):
        """内部日志方法"""
        # 添加额外数据
        if kwargs:
            # 使用标准 logging 的 extra 参数传递额外数据
            self.logger.log(level, msg, extra={'extra_data': kwargs})
        else:
            self.logger.log(level, msg)
    
    def log_metric(self, metric_name: str, value: Any, unit: str = ''):
        """记录测试指标"""
        self.info(f"指标：{metric_name} = {value}{unit}", extra={'metric': metric_name, 'value': value, 'unit': unit})
    
    def log_step(self, step_num: int, step_desc: str):
        """记录测试步骤"""
        self.info(f"[步骤 {step_num}] {step_desc}", extra={'step': step_num, 'description': step_desc})
    
    def log_assertion(self, assertion: str, expected: Any, actual: Any, passed: bool):
        """记录断言结果"""
        status = '✅ PASS' if passed else '❌ FAIL'
        self.info(
            f"断言：{assertion} - {status}",
            extra={
                'assertion': assertion,
                'expected': expected,
                'actual': actual,
                'passed': passed
            }
        )
    
    def get_log_file(self) -> Path:
        """获取日志文件路径"""
        return self.log_file
    
    def get_error_file(self) -> Path:
        """获取错误日志文件路径"""
        return self.error_file
    
    def close(self):
        """关闭所有 handler"""
        for handler in self.logger.handlers[:]:
            handler.close()
            self.logger.removeHandler(handler)


# 全局日志实例缓存
_loggers: Dict[str, TestLogger] = {}


def get_logger(
    test_id: Optional[str] = None,
    log_dir: str = 'logs',
    **kwargs
) -> TestLogger:
    """
    获取日志实例
    
    Args:
        test_id: 测试 ID，不传则使用全局 logger
        log_dir: 日志目录
        **kwargs: 其他参数传递给 TestLogger
    
    Returns:
        TestLogger 实例
    """
    if test_id is None:
        test_id = 'global'
    
    if test_id not in _loggers:
        _loggers[test_id] = TestLogger(test_id, log_dir, **kwargs)
    
    return _loggers[test_id]


def close_all_loggers():
    """关闭所有日志实例"""
    for logger in _loggers.values():
        logger.close()
    _loggers.clear()
