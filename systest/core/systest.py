#!/usr/bin/env python3
"""
测试框架 - Systest (SysTest Framework)
提供测试基础设施，不封装执行逻辑

功能：
- TestLogger：日志记录
- PreconditionChecker：Precondition 检查工具
- PostconditionChecker：Postcondition 检查工具
- 配置管理
- 命令行参数解析
"""

import argparse
import sys
from pathlib import Path

try:
    import yaml

    YAML_AVAILABLE = True
except ImportError:
    YAML_AVAILABLE = False

from logger import TestLogger
from postcondition_checker import PostconditionChecker
from precondition_checker import PreconditionChecker


class Systest:
    """SysTest 框架 - 提供基础设施工具箱"""

    def __init__(self, test_name, device=None, output_dir=None, log_dir=None, config_file=None):
        """
        初始化 SysTest 框架

        Args:
            test_name: 测试用例名称
            device: 测试设备路径（可选，命令行优先）
            output_dir: 结果输出目录（可选，命令行优先）
            log_dir: 日志目录（可选，命令行优先）
            config_file: 配置文件路径（可选）
        """
        self.test_name = test_name

        # 加载配置
        self.config = self._load_config(config_file)

        # 解析命令行参数（优先级最高）
        self.args = self._parse_args()

        # 确定最终参数（命令行 > 参数 > 配置 > 默认值）
        self.device = self.args.device or device or self.config.get("test", {}).get("device", "/dev/ufs0")
        self.output_dir = Path(
            self.args.output_dir or output_dir or self.config.get("test", {}).get("output_dir", "./results")
        )
        self.log_dir = Path(self.args.log_dir or log_dir or self.config.get("test", {}).get("log_dir", "./logs"))
        self.mode = self.args.mode or self.config.get("test", {}).get("mode", "development")

        # 创建目录
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.log_dir.mkdir(parents=True, exist_ok=True)

        # 初始化工具
        self.logger = TestLogger(test_name, output_dir=str(self.log_dir))
        self.precondition_checker = PreconditionChecker(verbose=self.args.verbose)
        self.postcondition_checker = PostconditionChecker(verbose=self.args.verbose)

        # 记录测试开始
        self.logger.info("=" * 80)
        self.logger.info(f"SysTest 测试开始：{test_name}")
        self.logger.info(f"设备：{self.device}")
        self.logger.info(f"模式：{self.mode}")
        self.logger.info("=" * 80)

    def _load_config(self, config_file=None):
        """加载配置文件"""
        if not YAML_AVAILABLE:
            return {}

        # 优先级：参数指定 > 默认位置
        config_paths = []
        if config_file:
            config_paths.append(Path(config_file))
        config_paths.append(Path(__file__).parent.parent / "config.yaml")
        config_paths.append(Path("./config.yaml"))

        for config_path in config_paths:
            if config_path.exists():
                try:
                    with open(config_path, "r", encoding="utf-8") as f:
                        return yaml.safe_load(f) or {}
                except Exception as e:
                    pass

        return {}

    def _parse_args(self):
        """解析命令行参数"""
        parser = argparse.ArgumentParser(description=f"SysTest: {self.test_name}")
        parser.add_argument("--device", type=str, help="测试设备路径（如 /dev/ufs0）")
        parser.add_argument("--output-dir", type=str, help="结果输出目录")
        parser.add_argument("--log-dir", type=str, help="日志目录")
        parser.add_argument("--runtime", type=int, help="测试运行时间（秒）")
        parser.add_argument("--mode", type=str, choices=["development", "production"], help="测试模式")
        parser.add_argument("--verbose", action="store_true", help="详细输出")
        parser.add_argument("--config", type=str, help="配置文件路径")

        return parser.parse_args()

    def check_precondition(self, device=None, mode=None):
        """
        检查 Precondition（带错误处理）

        Args:
            device: 测试设备路径
            mode: 检查模式（development/production）

        Returns:
            dict: Precondition 检查结果
        """
        device = device or self.device
        mode = mode or self.mode

        self.logger.step("Precondition 检查")

        try:
            # 获取 Precondition 配置
            precondition_config = self._get_precondition_config()

            result = self.precondition_checker.check_all(precondition_config, device, mode=mode)

            # 记录检查结果
            for check in result.get("checks", []):
                status = "PASS" if check.get("passed", False) else "FAIL"
                self.logger.precondition(check.get("name", ""), status, check.get("message", ""))

            return result
        except Exception as e:
            self.logger.error(f"Precondition 检查异常：{e}")
            return {"passed": False, "errors": [{"message": str(e)}]}

    def _get_precondition_config(self):
        """获取 Precondition 配置"""
        # 从配置文件读取
        return self.config.get("precondition", {})

    def check_postcondition(self, before_state, device=None, mode=None):
        """
        检查 Postcondition

        Args:
            before_state: 测试前状态
            device: 测试设备路径
            mode: 检查模式

        Returns:
            dict: Postcondition 检查结果
        """
        device = device or self.device
        mode = mode or self.mode

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

    def get_config(self, key, default=None):
        """
        获取配置项

        Args:
            key: 配置键（支持点分隔，如 "fio.default_runtime"）
            default: 默认值

        Returns:
            配置值
        """
        keys = key.split(".")
        value = self.config
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        return value
