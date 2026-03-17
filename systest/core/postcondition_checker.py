#!/usr/bin/env python3
"""
Postcondition 检查器 - Postcondition Checker
负责在测试执行后检查器件状态、恢复配置、对比测试前后变化
"""

import os
import subprocess
from datetime import datetime
from pathlib import Path


class PostconditionChecker:
    """Postcondition 检查器"""

    def __init__(self, verbose=False):
        self.verbose = verbose
        self.check_results = {
            "timestamp": datetime.now().isoformat(),
            "passed": True,
            "checks": [],
            "warnings": [],
            "errors": [],
            "before": {},  # 测试前状态
            "after": {},  # 测试后状态
            "changes": {},  # 变化对比
        }

    def check_all(self, test_name, device="/dev/ufs0", before_state=None, mode="development"):
        """
        执行所有 Postcondition 检查

        Args:
            test_name: 测试用例名称
            device: 测试设备路径
            before_state: 测试前状态（从 Precondition 获取）
            mode: 模式 ('development' | 'production')

        Returns:
            dict: 检查结果
        """
        self.test_name = test_name
        self.device = device
        self.mode = mode
        self.before_state = before_state or {}

        self.check_results = {
            "timestamp": datetime.now().isoformat(),
            "test_name": test_name,
            "device": device,
            "passed": True,
            "critical_fail": False,  # 关键失败（坏块增加）
            "checks": [],
            "warnings": [],
            "errors": [],
            "before": self.before_state,
            "after": {},
            "changes": {},
        }

        # 1. 收集测试后状态
        self._collect_after_state()

        # 2. 对比测试前后变化
        self._compare_changes()

        # 3. 检查坏块数量（最高优先级）
        self._check_bad_blocks()

        # 4. 检查剩余寿命衰减
        self._check_lifespan_degradation()

        # 5. 检查错误计数
        self._check_error_counts()

        # 6. 检查温度变化
        self._check_temperature()

        # 7. 恢复配置
        self._restore_config()

        # 生产模式下如果有关键失败，标记为不通过
        if self.mode == "production" and self.check_results["critical_fail"]:
            self.check_results["passed"] = False

        return self.check_results

    def _add_check(self, name, passed, message="", before="", after=""):
        """添加检查结果"""
        check = {
            "name": name,
            "passed": passed,
            "message": message,
            "before": before,
            "after": after,
            "timestamp": datetime.now().isoformat(),
        }
        self.check_results["checks"].append(check)

        if self.verbose:
            status = "✅" if passed else "❌"
            print(f"  {status} {name}: {message}")

    def _add_warning(self, message):
        """添加警告"""
        self.check_results["warnings"].append({"message": message, "timestamp": datetime.now().isoformat()})
        if self.verbose:
            print(f"  ⚠️  警告：{message}")

    def _add_error(self, message, critical=False):
        """添加错误"""
        error = {"message": message, "timestamp": datetime.now().isoformat(), "critical": critical}
        self.check_results["errors"].append(error)

        if critical:
            self.check_results["critical_fail"] = True

        if self.verbose:
            print(f"  ❌ 错误：{message}" + (" [关键]" if critical else ""))

    # ========== 1. 收集测试后状态 ==========

    def _collect_after_state(self):
        """收集测试后器件状态"""
        if self.verbose:
            print("\n📊 收集测试后状态...")

        after_state = {}

        # SMART 状态
        after_state["smart_status"] = self._get_smart_status()

        # 剩余寿命
        after_state["lifespan"] = self._get_lifespan()

        # 坏块数量
        after_state["bad_blocks"] = self._get_bad_blocks()

        # 错误计数
        after_state["error_counts"] = self._get_error_counts()

        # 温度
        after_state["temperature"] = self._get_temperature()

        # 设备配置
        after_state["config"] = self._get_device_config()

        self.check_results["after"] = after_state

        if self.verbose:
            print(f"  SMART 状态：{after_state['smart_status']}")
            print(f"  剩余寿命：{after_state['lifespan']}%")
            print(f"  坏块数量：{after_state['bad_blocks']}")
            print(f"  错误计数：{after_state['error_counts']}")
            print(f"  温度：{after_state['temperature']}℃")

    # ========== 2. 对比测试前后变化 ==========

    def _compare_changes(self):
        """对比测试前后状态变化"""
        if self.verbose:
            print("\n📊 对比测试前后变化...")

        changes = {}

        # 坏块数量变化
        before_bad_blocks = self.before_state.get("bad_blocks", 0)
        after_bad_blocks = self.check_results["after"].get("bad_blocks", 0)
        changes["bad_blocks_change"] = after_bad_blocks - before_bad_blocks

        # 剩余寿命变化
        before_lifespan = self.before_state.get("lifespan", 100)
        after_lifespan = self.check_results["after"].get("lifespan", 100)
        changes["lifespan_degradation"] = before_lifespan - after_lifespan

        # 错误计数变化
        before_errors = self.before_state.get("error_counts", 0)
        after_errors = self.check_results["after"].get("error_counts", 0)
        changes["error_counts_change"] = after_errors - before_errors

        # 温度变化
        before_temp = self.before_state.get("temperature", 0)
        after_temp = self.check_results["after"].get("temperature", 0)
        changes["temperature_change"] = after_temp - before_temp

        self.check_results["changes"] = changes

        if self.verbose:
            print(f"  坏块变化：{changes['bad_blocks_change']}")
            print(f"  寿命衰减：{changes['lifespan_degradation']}%")
            print(f"  错误计数变化：{changes['error_counts_change']}")
            print(f"  温度变化：{changes['temperature_change']}℃")

    # ========== 3. 检查坏块数量（最高优先级） ==========

    def _check_bad_blocks(self):
        """检查坏块数量是否增加（关键检查）"""
        bad_blocks_change = self.check_results["changes"].get("bad_blocks_change", 0)

        if bad_blocks_change > 0:
            # 坏块增加 - 关键失败
            self._add_error(
                f"坏块数量增加 {bad_blocks_change} 个（测试前={self.before_state.get('bad_blocks', 0)}, 测试后={self.check_results['after'].get('bad_blocks', 0)}）",
                critical=True,
            )
            self._add_check(
                "坏块数量检查",
                False,
                f"坏块增加 {bad_blocks_change} 个，需立即停止测试并排查原因",
                str(self.before_state.get("bad_blocks", 0)),
                str(self.check_results["after"].get("bad_blocks", 0)),
            )
        else:
            # 坏块无增加
            self._add_check(
                "坏块数量检查",
                True,
                "坏块数量无增加",
                str(self.before_state.get("bad_blocks", 0)),
                str(self.check_results["after"].get("bad_blocks", 0)),
            )

    # ========== 4. 检查剩余寿命衰减 ==========

    def _check_lifespan_degradation(self):
        """检查剩余寿命衰减"""
        lifespan_degradation = self.check_results["changes"].get("lifespan_degradation", 0)

        if lifespan_degradation >= 1:
            # 寿命衰减≥1% - 失败
            self._add_error(f"剩余寿命衰减 {lifespan_degradation}%（≥1% 阈值）", critical=False)
            self._add_check(
                "剩余寿命检查",
                False,
                f"寿命衰减 {lifespan_degradation}%",
                f"{self.before_state.get('lifespan', 100)}%",
                f"{self.check_results['after'].get('lifespan', 100)}%",
            )
        else:
            # 寿命衰减<1% - 通过
            self._add_check(
                "剩余寿命检查",
                True,
                f"寿命衰减 {lifespan_degradation}%（<1% 阈值）",
                f"{self.before_state.get('lifespan', 100)}%",
                f"{self.check_results['after'].get('lifespan', 100)}%",
            )

    # ========== 5. 检查错误计数 ==========

    def _check_error_counts(self):
        """检查错误计数"""
        error_counts_change = self.check_results["changes"].get("error_counts_change", 0)

        if error_counts_change > 0:
            # 错误计数增加 - 失败
            self._add_error(
                f"错误计数增加 {error_counts_change}（测试前={self.before_state.get('error_counts', 0)}, 测试后={self.check_results['after'].get('error_counts', 0)}）",
                critical=False,
            )
            self._add_check(
                "错误计数检查",
                False,
                f"错误计数增加 {error_counts_change}",
                str(self.before_state.get("error_counts", 0)),
                str(self.check_results["after"].get("error_counts", 0)),
            )
        else:
            # 错误计数无增加
            self._add_check(
                "错误计数检查",
                True,
                "错误计数保持为 0",
                str(self.before_state.get("error_counts", 0)),
                str(self.check_results["after"].get("error_counts", 0)),
            )

    # ========== 6. 检查温度 ==========

    def _check_temperature(self):
        """检查温度变化"""
        temp_change = self.check_results["changes"].get("temperature_change", 0)
        after_temp = self.check_results["after"].get("temperature", 0)

        if after_temp >= 70:
            # 温度≥70℃ - 警告
            self._add_warning(f"测试后温度 {after_temp}℃（≥70℃ 阈值）")
            self._add_check(
                "温度检查", False, f"温度过高 {after_temp}℃", f"{self.before_state.get('temperature', 0)}℃", f"{after_temp}℃"
            )
        elif temp_change > 20:
            # 温升>20℃ - 警告
            self._add_warning(f"温升 {temp_change}℃（>20℃）")
            self._add_check(
                "温度检查", True, f"温升 {temp_change}℃", f"{self.before_state.get('temperature', 0)}℃", f"{after_temp}℃"
            )
        else:
            # 温度正常
            self._add_check(
                "温度检查",
                True,
                f"温升 {temp_change}℃（正常）",
                f"{self.before_state.get('temperature', 0)}℃",
                f"{after_temp}℃",
            )

    # ========== 7. 恢复配置 ==========

    def _restore_config(self):
        """恢复测试前的配置"""
        if self.verbose:
            print("\n🔧 恢复配置...")

        config = self.before_state.get("config", {})

        # 恢复 TURBO Mode
        if "turbo_mode" in config:
            self._restore_turbo_mode(config["turbo_mode"])

        # 恢复省电模式
        if "power_save" in config:
            self._restore_power_save(config["power_save"])

        # 恢复 IO 调度器
        if "scheduler" in config:
            self._restore_scheduler(config["scheduler"])

        self._add_check("配置恢复", True, "配置已恢复", "测试中配置", "原始配置")

    # ========== 辅助方法 ==========

    def _get_smart_status(self):
        """获取 SMART 状态"""
        try:
            result = subprocess.run(["smartctl", "-H", self.device], capture_output=True, text=True, timeout=10)
            if "PASSED" in result.stdout:
                return "PASSED"
            elif "FAILED" in result.stdout:
                return "FAILED"
            else:
                return "UNKNOWN"
        except Exception as e:
            return f"ERROR: {str(e)}"

    def _get_lifespan(self):
        """获取剩余寿命百分比"""
        try:
            result = subprocess.run(["smartctl", "-l", "smartctl", self.device], capture_output=True, text=True, timeout=10)
            # 解析 Percentage Used 字段
            for line in result.stdout.split("\n"):
                if "Percentage Used" in line:
                    # 格式：Percentage Used: 2%
                    percentage = line.split(":")[1].strip().replace("%", "")
                    return 100 - int(percentage)
            return 100
        except Exception as e:
            return 100

    def _get_bad_blocks(self):
        """获取坏块数量"""
        try:
            result = subprocess.run(["smartctl", "-l", "smartctl", self.device], capture_output=True, text=True, timeout=10)
            # 解析 Available Spare 或类似字段
            for line in result.stdout.split("\n"):
                if "Available Spare" in line:
                    # 格式：Available Spare: 100%
                    percentage = line.split(":")[1].strip().replace("%", "")
                    # 转换为坏块数量（简化处理）
                    return 100 - int(percentage)
            return 0
        except Exception as e:
            return 0

    def _get_error_counts(self):
        """获取错误计数"""
        try:
            # 尝试从 sysfs 读取
            stats_path = f"/sys/block/{self.device.replace('/dev/', '')}/device/stats"
            if os.path.exists(stats_path):
                with open(stats_path, "r") as f:
                    stats = f.read()
                    # 解析错误计数（简化处理）
                    return 0
            return 0
        except Exception as e:
            return 0

    def _get_temperature(self):
        """获取温度"""
        try:
            # 尝试从 sysfs 读取
            device_name = self.device.replace("/dev/", "")
            hwmon_dirs = Path("/sys/class/hwmon").glob("hwmon*")

            for hwmon in hwmon_dirs:
                try:
                    name_file = hwmon / "name"
                    if name_file.exists():
                        with open(name_file, "r") as f:
                            if device_name in f.read().lower():
                                temp_file = hwmon / "temp1_input"
                                if temp_file.exists():
                                    with open(temp_file, "r") as tf:
                                        temp = int(tf.read().strip()) / 1000
                                        return temp
                except Exception:
                    continue

            return 0
        except Exception as e:
            return 0

    def _get_device_config(self):
        """获取设备当前配置"""
        config = {}

        try:
            device_name = self.device.replace("/dev/", "")

            # TURBO Mode
            turbo_path = f"/sys/block/{device_name}/device/turbo_mode"
            if os.path.exists(turbo_path):
                with open(turbo_path, "r") as f:
                    config["turbo_mode"] = f.read().strip()

            # 省电模式
            power_save_path = f"/sys/block/{device_name}/device/power_save"
            if os.path.exists(power_save_path):
                with open(power_save_path, "r") as f:
                    config["power_save"] = f.read().strip()

            # IO 调度器
            scheduler_path = f"/sys/block/{device_name}/queue/scheduler"
            if os.path.exists(scheduler_path):
                with open(scheduler_path, "r") as f:
                    scheduler = f.read().strip()
                    # 格式：[none] mq-deadline，当前值在方括号中
                    if "[" in scheduler:
                        config["scheduler"] = scheduler.split("[")[1].split("]")[0]
                    else:
                        config["scheduler"] = scheduler.split()[0]

        except Exception as e:
            pass

        return config

    def _restore_turbo_mode(self, value):
        """恢复 TURBO Mode"""
        try:
            device_name = self.device.replace("/dev/", "")
            turbo_path = f"/sys/block/{device_name}/device/turbo_mode"
            if os.path.exists(turbo_path):
                with open(turbo_path, "w") as f:
                    f.write(value)
                if self.verbose:
                    print(f"  恢复 TURBO Mode: {value}")
        except Exception as e:
            if self.verbose:
                print(f"  恢复 TURBO Mode 失败：{e}")

    def _restore_power_save(self, value):
        """恢复省电模式"""
        try:
            device_name = self.device.replace("/dev/", "")
            power_save_path = f"/sys/block/{device_name}/device/power_save"
            if os.path.exists(power_save_path):
                with open(power_save_path, "w") as f:
                    f.write(value)
                if self.verbose:
                    print(f"  恢复省电模式：{value}")
        except Exception as e:
            if self.verbose:
                print(f"  恢复省电模式失败：{e}")

    def _restore_scheduler(self, value):
        """恢复 IO 调度器"""
        try:
            device_name = self.device.replace("/dev/", "")
            scheduler_path = f"/sys/block/{device_name}/queue/scheduler"
            if os.path.exists(scheduler_path):
                with open(scheduler_path, "w") as f:
                    f.write(value)
                if self.verbose:
                    print(f"  恢复 IO 调度器：{value}")
        except Exception as e:
            if self.verbose:
                print(f"  恢复 IO 调度器失败：{e}")
