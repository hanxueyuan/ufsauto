#!/usr/bin/env python3
"""
测试框架 - Test Framework
提供测试基础设施，不封装执行逻辑

功能：
- TestLogger：日志记录
- PreconditionChecker：Precondition 检查工具
- PostconditionChecker：Postcondition 检查工具
- ParamParser：参数解析
"""

import argparse
import sys
from pathlib import Path

from logger import TestLogger
from postcondition_checker import PostconditionChecker
from precondition_checker import PreconditionChecker


class TestFramework:
    """测试框架 - 提供基础设施工具箱"""

    def __init__(self, test_name, device="/dev/ufs0", output_dir="./results", log_dir="./logs"):
        """
        初始化测试框架

        Args:
            test_name: 测试用例名称
            device: 测试设备路径
            output_dir: 结果输出目录
            log_dir: 日志目录
        """
        self.test_name = test_name
        self.device = device
        self.output_dir = Path(output_dir)
        self.log_dir = Path(log_dir)

        # 创建目录
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.log_dir.mkdir(parents=True, exist_ok=True)

        # 初始化工具
        self.logger = TestLogger(test_name, output_dir=str(self.log_dir))
        self.precondition_checker = PreconditionChecker(verbose=True)
        self.postcondition_checker = PostconditionChecker(verbose=True)

        # 解析命令行参数
        self.params = self._parse_params()

        # 记录测试开始
        self.logger.info("=" * 80)
        self.logger.info(f"测试开始：{test_name}")
        self.logger.info(f"设备：{device}")
        self.logger.info("=" * 80)

    def _parse_params(self):
        """解析命令行参数"""
        parser = argparse.ArgumentParser(description=f"测试：{self.test_name}")
        parser.add_argument("--device", type=str, default=self.device, help="测试设备路径")
        parser.add_argument("--output-dir", type=str, default=str(self.output_dir), help="结果输出目录")
        parser.add_argument("--log-dir", type=str, default=str(self.log_dir), help="日志目录")
        parser.add_argument("--runtime", type=int, default=60, help="测试运行时间（秒）")
        parser.add_argument("--verbose", action="store_true", help="详细输出")

        args = parser.parse_args()
        return args

    def check_precondition(self, device=None, mode="development"):
        """
        检查 Precondition

        Args:
            device: 测试设备路径（默认使用初始化时的值）
            mode: 检查模式（development/production）

        Returns:
            dict: Precondition 检查结果
        """
        device = device or self.device
        self.logger.step("Precondition 检查")

        # 获取测试用例的 Precondition 配置（从注释中解析）
        # 这里简化处理，实际应该从测试用例文件中解析
        precondition_config = self._get_precondition_config()

        result = self.precondition_checker.check_all(precondition_config, device, mode=mode)

        # 记录检查结果
        for check in result.get("checks", []):
            status = "PASS" if check.get("passed", False) else "FAIL"
            self.logger.precondition(check.get("name", ""), status, check.get("message", ""))

        return result

    def _get_precondition_config(self):
        """获取 Precondition 配置（从测试用例注释中解析）"""
        # 简化实现，实际应该解析测试用例文件的文档字符串
        return {}

    def check_postcondition(self, before_state, device=None, mode="development"):
        """
        检查 Postcondition

        Args:
            before_state: 测试前状态（从 Precondition 获取）
            device: 测试设备路径
            mode: 检查模式

        Returns:
            dict: Postcondition 检查结果
        """
        device = device or self.device
        self.logger.step("Postcondition 检查")

        result = self.postcondition_checker.check_all(self.test_name, device, before_state=before_state, mode=mode)

        # 记录检查结果
        for check in result.get("checks", []):
            status = "PASS" if check.get("passed", False) else "FAIL"
            self.logger.info(f"  {status} {check.get('name', '')}: {check.get('message', '')}")

        # 显示状态变化
        changes = result.get("changes", {})
        if changes:
            self.logger.info("-" * 60)
            self.logger.info("状态变化:")
            if "bad_blocks_change" in changes:
                change = changes["bad_blocks_change"]
                icon = "⚠️" if change > 0 else "✅"
                self.logger.info(f"  {icon} 坏块变化：{change}")
            if "lifespan_degradation" in changes:
                degradation = changes["lifespan_degradation"]
                icon = "⚠️" if degradation >= 1 else "✅"
                self.logger.info(f"  {icon} 寿命衰减：{degradation}%")
            if "error_counts_change" in changes:
                change = changes["error_counts_change"]
                icon = "⚠️" if change > 0 else "✅"
                self.logger.info(f"  {icon} 错误计数变化：{change}")

        # 关键失败警告
        if result.get("critical_fail", False):
            self.logger.error("=" * 60)
            self.logger.error("⚠️ 关键失败：坏块数量增加！")
            self.logger.error("⚠️ 需立即停止测试并排查原因")
            self.logger.error("=" * 60)

        return result

    def report(self, result):
        """
        报告测试结果

        Args:
            result: 测试结果字典
        """
        self.logger.summary(result)
        self.logger.close()

    def success(self, message):
        """记录成功消息"""
        self.logger.success(message)

    def fail(self, message):
        """记录失败消息"""
        self.logger.error(message)

    def info(self, message):
        """记录信息消息"""
        self.logger.info(message)

    def step(self, step_name, message=""):
        """记录步骤"""
        self.logger.step(step_name, message)
