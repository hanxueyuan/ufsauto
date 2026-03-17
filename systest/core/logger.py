#!/usr/bin/env python3
"""
日志模块 - Logger
负责记录测试过程中的所有信息
"""

import logging
import os
import sys
from datetime import datetime
from pathlib import Path


class TestLogger:
    """测试日志记录器"""

    def __init__(self, test_name, output_dir="./logs", log_level=logging.INFO):
        """
        初始化日志记录器

        Args:
            test_name: 测试用例名称
            output_dir: 日志输出目录
            log_level: 日志级别
        """
        self.test_name = test_name
        self.output_dir = Path(output_dir)
        self.log_level = log_level

        # 创建日志目录
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # 生成日志文件名（包含时间戳）
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.log_file = self.output_dir / f"{test_name}_{timestamp}.log"

        # 配置日志记录器
        self.logger = logging.getLogger(test_name)
        self.logger.setLevel(log_level)

        # 清除已有的 handler
        self.logger.handlers.clear()

        # 创建文件 handler（记录所有级别的日志）
        file_handler = logging.FileHandler(self.log_file, encoding='utf-8')
        file_handler.setLevel(logging.DEBUG)
        file_formatter = logging.Formatter(
            '%(asctime)s | %(levelname)-8s | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(file_formatter)
        self.logger.addHandler(file_handler)

        # 创建控制台 handler（只记录 INFO 及以上级别）
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        console_formatter = logging.Formatter(
            '%(asctime)s | %(levelname)-8s | %(message)s',
            datefmt='%H:%M:%S'
        )
        console_handler.setFormatter(console_formatter)
        self.logger.addHandler(console_handler)

        # 记录测试开始
        self.info("=" * 80)
        self.info(f"测试用例：{test_name}")
        self.info(f"日志文件：{self.log_file}")
        self.info("=" * 80)

    def debug(self, message):
        """调试日志"""
        self.logger.debug(message)

    def info(self, message):
        """信息日志"""
        self.logger.info(message)

    def warning(self, message):
        """警告日志"""
        self.logger.warning(f"⚠️  {message}")

    def error(self, message):
        """错误日志"""
        self.logger.error(f"❌ {message}")

    def success(self, message):
        """成功日志"""
        self.logger.info(f"✅ {message}")

    def step(self, step_name, message=""):
        """步骤日志"""
        self.info("-" * 60)
        self.info(f"步骤：{step_name}")
        if message:
            self.info(f"  {message}")

    def result(self, metric_name, value, unit=""):
        """结果日志"""
        if unit:
            self.info(f"📊 {metric_name}: {value} {unit}")
        else:
            self.info(f"📊 {metric_name}: {value}")

    def precondition(self, check_name, status, message=""):
        """Precondition 检查日志"""
        if status == "PASS":
            self.success(f"Precondition: {check_name} - {message}")
        elif status == "WARN":
            self.warning(f"Precondition: {check_name} - {message}")
        elif status == "FAIL":
            self.error(f"Precondition: {check_name} - {message}")

    def postcondition(self, check_name, before, after, status):
        """Postcondition 检查日志"""
        if status == "PASS":
            self.success(f"Postcondition: {check_name} - {before} → {after}")
        elif status == "FAIL":
            self.error(f"Postcondition: {check_name} - {before} → {after} (FAIL)")

    def summary(self, result_dict):
        """测试总结日志"""
        self.info("=" * 80)
        self.info("测试总结")
        self.info("=" * 80)

        status = result_dict.get("status", "UNKNOWN")
        if status == "PASS":
            self.success(f"测试结果：PASS")
        elif status == "FAIL":
            self.error(f"测试结果：FAIL")
        else:
            self.info(f"测试结果：{status}")

        # 记录性能指标
        metrics = result_dict.get("metrics", {})
        if metrics:
            self.info("-" * 60)
            self.info("性能指标:")
            for key, value in metrics.items():
                self.info(f"  {key}: {value}")

        # 记录 Precondition 检查结果
        precondition = result_dict.get("precondition", {})
        if precondition:
            self.info("-" * 60)
            self.info("Precondition 检查:")
            for check_name, check_result in precondition.items():
                status_icon = "✅" if check_result.get("passed", False) else "❌"
                self.info(f"  {status_icon} {check_name}: {check_result.get('message', '')}")

        # 记录 Postcondition 检查结果
        postcondition = result_dict.get("postcondition", {})
        if postcondition:
            self.info("-" * 60)
            self.info("Postcondition 检查:")
            for check_name, check_result in postcondition.items():
                status_icon = "✅" if check_result.get("passed", False) else "❌"
                self.info(f"  {status_icon} {check_name}: {check_result.get('message', '')}")

        self.info("=" * 80)
        self.info(f"日志文件：{self.log_file}")
        self.info("=" * 80)

    def get_log_file(self):
        """获取日志文件路径"""
        return str(self.log_file)

    def close(self):
        """关闭日志记录器"""
        for handler in self.logger.handlers:
            handler.close()
        self.logger.handlers.clear()
