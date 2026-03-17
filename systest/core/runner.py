#!/usr/bin/env python3
"""
测试执行引擎 - Test Runner
负责执行测试用例和测试套件
"""

import json
import logging
import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

from precondition_checker import PreconditionChecker
from logger import TestLogger


class TestRunner:
    """测试执行器"""

    def __init__(
        self,
        device="/dev/ufs0",
        output_dir="./results",
        config=None,
        config_file=None,
        verbose=False,
        check_precondition=True,
        mode=None,
        log_dir="./logs",
    ):
        self.device = device
        self.output_dir = Path(output_dir)
        self.log_dir = Path(log_dir)

        # 加载配置文件
        if config_file:
            self.config = self._load_config(config_file)
        else:
            self.config = config or {}

        # 如果没有指定 mode，从配置中获取
        if mode is None:
            self.mode = self.config.get("mode", "development")
        else:
            self.mode = mode

        self.verbose = verbose
        self.check_precondition = check_precondition

        # 从配置中获取执行参数
        exec_config = self.config.get("execution", {})
        self.loop_count = exec_config.get("loop_count", 1)

        # 加载测试套件
        self.suites = self._load_suites()

        # 初始化 Precondition 检查器
        self.precondition_checker = PreconditionChecker(verbose=verbose)

        # 初始化日志记录器（在 run_test 时创建）
        self.logger = None

    def _load_config(self, config_file):
        """加载配置文件"""
        config_path = Path(config_file)
        if not config_path.is_absolute():
            config_path = Path(__file__).parent.parent / config_file

        if config_path.exists():
            with open(config_path, "r", encoding="utf-8") as f:
                return json.load(f)
        else:
            print(f"⚠️  配置文件不存在：{config_path}，使用默认配置")
            return {}

    def _load_suites(self):
        """加载可用的测试套件"""
        suites = {}
        suites_dir = Path(__file__).parent.parent / "suites"

        if not suites_dir.exists():
            return self._get_default_suites()

        for suite_path in suites_dir.iterdir():
            if suite_path.is_dir() and not suite_path.name.startswith("_"):
                suite_name = suite_path.name
                tests = self._load_suite_tests(suite_path)
                if tests:
                    suites[suite_name] = tests

        return suites if suites else self._get_default_suites()

    def _get_default_suites(self):
        """获取默认测试套件定义"""
        return {
            "performance": [
                {"name": "seq_read_burst", "description": "顺序读带宽 (Burst)"},
                {"name": "seq_read_sustained", "description": "顺序读带宽 (Sustained)"},
                {"name": "seq_write_burst", "description": "顺序写带宽 (Burst)"},
                {"name": "seq_write_sustained", "description": "顺序写带宽 (Sustained)"},
                {"name": "rand_read_burst", "description": "随机读 IOPS (Burst)"},
                {"name": "rand_read_sustained", "description": "随机读 IOPS (Sustained)"},
                {"name": "rand_write_burst", "description": "随机写 IOPS (Burst)"},
                {"name": "rand_write_sustained", "description": "随机写 IOPS (Sustained)"},
                {"name": "mixed_rw", "description": "混合读写性能"},
            ],
            "qos": [
                {"name": "latency_percentile", "description": "延迟百分位测试"},
                {"name": "latency_jitter", "description": "延迟抖动测试"},
            ],
            "reliability": [
                {"name": "stability_test", "description": "长期稳定性测试"},
            ],
            "scenario": [
                {"name": "sensor_write", "description": "传感器数据写入"},
                {"name": "model_load", "description": "算法模型加载"},
            ],
        }

    def _load_suite_tests(self, suite_path):
        """加载套件中的测试用例"""
        tests = []

        # 优先从 tests.json 加载配置
        tests_json = suite_path / "tests.json"
        if tests_json.exists():
            try:
                with open(tests_json, "r", encoding="utf-8") as f:
                    config = json.load(f)
                    return config.get("tests", [])
            except Exception as e:
                if self.verbose:
                    print(f"  警告：加载 {tests_json} 失败：{e}")

        # 查找测试文件 (备用)
        for test_file in suite_path.glob("*.py"):
            if test_file.name.startswith("_"):
                continue

            # 从文件名推导测试名
            test_name = test_file.stem
            tests.append({"name": test_name, "description": test_name.replace("_", " ").title(), "file": str(test_file)})

        return tests

    def list_suites(self):
        """列出所有可用的测试套件"""
        return self.suites

    def run_test(self, test_name, test_id=None):
        """执行单个测试"""
        test_id = test_id or datetime.now().strftime("%Y%m%d_%H%M%S")

        # 初始化日志记录器
        self.logger = TestLogger(test_name, output_dir=self.log_dir)
        self.logger.step("测试初始化", f"测试 ID: {test_id}")

        # 查找测试
        test_info = self._find_test(test_name)
        if not test_info:
            self.logger.error(f"未找到测试项：{test_name}")
            raise ValueError(f"未找到测试项：{test_name}")

        # 检查 Precondition
        if self.check_precondition and "precondition" in test_info:
            self.logger.step("Precondition 检查")

            # 生产模式下严格检查
            precondition_mode = "production" if self.mode == "production" else "development"

            precondition_result = self.precondition_checker.check_all(
                test_info["precondition"], self.device, mode=precondition_mode
            )

            # 记录 Precondition 检查结果
            for check in precondition_result.get("checks", []):
                status = "PASS" if check.get("passed", False) else "FAIL"
                self.logger.precondition(check.get("name", ""), status, check.get("message", ""))

            # 开发模式下只记录问题，继续执行测试
            if self.mode == "development":
                if precondition_result["warnings"]:
                    self.logger.warning(f"发现 {len(precondition_result['warnings'])} 个问题，继续执行测试（开发模式）")
            # 生产模式下如果检查失败，抛出异常停止测试
            elif not precondition_result["passed"]:
                error_msg = f"Precondition 检查失败：{test_name}\n"
                if precondition_result["errors"]:
                    error_msg += "\n错误列表:\n"
                    for error in precondition_result["errors"]:
                        error_msg += f"  - {error['message']}\n"
                self.logger.error(error_msg)
                raise RuntimeError(error_msg)

        # 执行测试（支持循环执行）
        results = []
        for i in range(self.loop_count):
            if self.loop_count > 1:
                self.logger.step("循环执行", f"第 {i+1}/{self.loop_count} 次")

            self.logger.info(f"执行测试：{test_name}")
            result = self._execute_test(test_name, test_info, self.logger)
            result["loop"] = i + 1
            results.append(result)

        # 如果只执行 1 次，直接返回
        if self.loop_count == 1:
            result = results[0]
            result["test_id"] = test_id
            result["test_name"] = test_name
            result["timestamp"] = datetime.now().isoformat()
            
            # 记录测试总结
            self.logger.summary(result)
            self.logger.close()
            
            return result

        # 多次执行，计算平均值
        avg_result = self._calculate_average(results)
        avg_result["test_id"] = test_id
        avg_result["test_name"] = test_name
        avg_result["timestamp"] = datetime.now().isoformat()
        avg_result["loops"] = results
        avg_result["loop_count"] = self.loop_count

        # 记录测试总结
        self.logger.summary(avg_result)
        self.logger.close()

        return avg_result

    def _calculate_average(self, results):
        """计算多次执行的平均值"""
        if not results:
            return {}

        avg = {"status": "PASS", "metrics": {}, "loop_results": []}

        # 检查是否有失败
        for result in results:
            if result.get("status") == "FAIL":
                avg["status"] = "FAIL"
                break

        # 计算指标平均值
        metrics_keys = ["bandwidth", "iops", "latency_avg", "latency_stddev"]
        for key in metrics_keys:
            values = [r.get("metrics", {}).get(key, 0) for r in results if r.get("metrics", {}).get(key)]
            if values:
                avg["metrics"][key] = round(sum(values) / len(values), 2)
                avg["metrics"][f"{key}_loops"] = values

        return avg

    def run_suite(self, suite_name, test_id=None):
        """执行测试套件"""
        test_id = test_id or datetime.now().strftime("%Y%m%d_%H%M%S")

        if suite_name not in self.suites:
            raise ValueError(f"未找到测试套件：{suite_name}")

        tests = self.suites[suite_name]
        results = {
            "test_id": test_id,
            "suite": suite_name,
            "timestamp": datetime.now().isoformat(),
            "device": self.device,
            "test_cases": [],
        }

        print(f"\n📦 执行套件：{suite_name}")
        print(f"   测试项数：{len(tests)}")
        print("-" * 60)

        for i, test in enumerate(tests, 1):
            print(f"[{i}/{len(tests)}] 执行：{test['name']}")

            # 检查 Precondition
            if self.check_precondition and "precondition" in test:
                if self.verbose:
                    print(f"  🔍 检查 Precondition...")

                precondition_result = self.precondition_checker.check_all(test["precondition"], self.device, mode=self.mode)

                # 开发模式下只记录问题，继续执行测试
                if self.mode == "development":
                    if precondition_result["warnings"]:
                        print(f"  ⚠️  发现 {len(precondition_result['warnings'])} 个问题，继续执行测试（开发模式）")
                # 生产模式下如果检查失败，抛出异常停止测试
                elif not precondition_result["passed"]:
                    error_msg = f"Precondition 检查失败：{test['name']}\n"
                    if precondition_result["errors"]:
                        error_msg += "\n错误列表:\n"
                        for error in precondition_result["errors"]:
                            error_msg += f"  - {error['message']}\n"
                    raise RuntimeError(error_msg)

            try:
                result = self._execute_test(test["name"], test)
                result["test_name"] = test["name"]
                results["test_cases"].append(result)

                # 显示结果
                status = "✅ PASS" if result.get("status") == "PASS" else "❌ FAIL"
                print(f"   {status}")

            except Exception as e:
                print(f"   ❌ ERROR: {e}")
                results["test_cases"].append({"test_name": test["name"], "status": "ERROR", "error": str(e)})

        # 计算摘要
        results["summary"] = self._calculate_summary(results["test_cases"])

        return results

    def _find_test(self, test_name):
        """查找测试项"""
        for suite_name, tests in self.suites.items():
            for test in tests:
                if test["name"] == test_name:
                    return test
        return None

    def _execute_test(self, test_name, test_info):
        """执行测试"""
        # 优先使用测试配置中的 FIO 参数
        if "fio" in test_info:
            fio_config = test_info["fio"]
            runtime = fio_config.get("runtime", 60)
        else:
            # 向后兼容：使用默认配置
            runtime = self.config.get("execution", {}).get("default_runtime", 60)
            if "sustained" in test_name:
                runtime = self.config.get("execution", {}).get("sustained_runtime", 300)

        # 构建 FIO 命令
        fio_cmd = self._build_fio_command(test_name, runtime, test_info)

        if self.verbose:
            print(f"  FIO 命令：{' '.join(fio_cmd)}")

        # 执行 FIO
        start_time = time.time()
        result = self._run_fio(fio_cmd)
        duration = time.time() - start_time

        # 解析结果
        parsed = self._parse_fio_result(result, test_name)
        parsed["duration"] = duration
        parsed["runtime"] = runtime

        # 验证结果
        parsed["status"] = self._validate_result(parsed, test_name, test_info)

        return parsed

    def _build_fio_command(self, test_name, runtime, test_info=None):
        """构建 FIO 命令"""
        # 基础命令
        cmd = ["fio", "--name=test", "--filename=" + self.device]

        # 优先使用测试配置中的 FIO 参数
        if test_info and "fio" in test_info:
            fio_config = test_info["fio"]
            for key, value in fio_config.items():
                # 处理布尔值参数（如 time_based）
                if value is True:
                    cmd.append(f"--{key}")
                elif value is not None and value != "" and value is not False:
                    cmd.append(f"--{key}={value}")
                elif value is None or value == "":
                    cmd.append(f"--{key}")

            # 输出 JSON 格式
            if "--output-format=json" not in cmd:
                cmd.append("--output-format=json")

            return cmd

        # 向后兼容：使用硬编码配置
        test_configs = {
            "seq_read_burst": {
                "rw": "read",
                "bs": "128k",
                "iodepth": "32",
                "numjobs": "1",
                "runtime": str(min(runtime, 60)),
                "time_based": "",
            },
            "seq_read_sustained": {
                "rw": "read",
                "bs": "128k",
                "iodepth": "32",
                "numjobs": "1",
                "runtime": str(runtime),
                "time_based": "",
            },
            "seq_write_burst": {
                "rw": "write",
                "bs": "128k",
                "iodepth": "32",
                "numjobs": "1",
                "runtime": str(min(runtime, 60)),
                "time_based": "",
            },
            "seq_write_sustained": {
                "rw": "write",
                "bs": "128k",
                "iodepth": "32",
                "numjobs": "1",
                "runtime": str(runtime),
                "time_based": "",
            },
            "rand_read_burst": {
                "rw": "randread",
                "bs": "4k",
                "iodepth": "32",
                "numjobs": "1",
                "runtime": str(min(runtime, 60)),
                "time_based": "",
            },
            "rand_read_sustained": {
                "rw": "randread",
                "bs": "4k",
                "iodepth": "32",
                "numjobs": "1",
                "runtime": str(runtime),
                "time_based": "",
            },
            "rand_write_burst": {
                "rw": "randwrite",
                "bs": "4k",
                "iodepth": "32",
                "numjobs": "1",
                "runtime": str(min(runtime, 60)),
                "time_based": "",
            },
            "rand_write_sustained": {
                "rw": "randwrite",
                "bs": "4k",
                "iodepth": "32",
                "numjobs": "1",
                "runtime": str(runtime),
                "time_based": "",
            },
            "mixed_rw": {
                "rw": "rw",
                "rwmixread": "70",
                "bs": "4k",
                "iodepth": "16",
                "numjobs": "1",
                "runtime": str(runtime),
                "time_based": "",
            },
            "latency_percentile": {
                "rw": "randread",
                "bs": "4k",
                "iodepth": "32",
                "numjobs": "1",
                "runtime": str(runtime),
                "time_based": "",
                "lat_percentiles": "1",
            },
        }

        config = test_configs.get(test_name, test_configs.get("seq_read_burst", {}))

        # 添加参数
        for key, value in config.items():
            if value:
                cmd.append(f"--{key}={value}")
            else:
                cmd.append(f"--{key}")

        # 输出 JSON 格式
        cmd.append("--output-format=json")

        return cmd

    def _run_fio(self, cmd):
        """执行 FIO 命令"""
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)  # 10 分钟超时

            if result.returncode != 0:
                raise RuntimeError(f"FIO 执行失败：{result.stderr}")

            return result.stdout

        except subprocess.TimeoutExpired:
            raise RuntimeError("FIO 执行超时")
        except FileNotFoundError:
            raise RuntimeError("未找到 FIO 工具，请先安装：apt install fio")

    def _parse_fio_result(self, fio_output, test_name):
        """解析 FIO 输出"""
        try:
            data = json.loads(fio_output)
        except json.JSONDecodeError:
            return {"status": "ERROR", "error": "FIO 输出解析失败"}

        if not data.get("jobs"):
            return {"status": "ERROR", "error": "FIO 输出格式错误"}

        job = data["jobs"][0]
        metrics = {}

        # 根据测试类型提取指标
        if "read" in test_name:
            io_stats = job.get("read", {})
        elif "write" in test_name:
            io_stats = job.get("write", {})
        else:
            io_stats = job.get("read", {})  # 混合读写默认看读

        # 带宽 (MB/s)
        bw_bytes = io_stats.get("bw_bytes", 0)
        metrics["bandwidth"] = round(bw_bytes / 1024 / 1024, 2)

        # IOPS
        metrics["iops"] = round(io_stats.get("iops", 0) / 1000, 2)  # KIOPS

        # 延迟 (μs)
        lat_ns = io_stats.get("lat_ns", {})
        metrics["latency_avg"] = round(lat_ns.get("mean", 0) / 1000, 2)  # ns -> μs
        metrics["latency_stddev"] = round(lat_ns.get("stddev", 0) / 1000, 2)

        # 百分位延迟
        percentiles = lat_ns.get("percentile", {})
        metrics["latency_p50"] = round(float(percentiles.get("50.000000", 0)) / 1000, 2)
        metrics["latency_p99"] = round(float(percentiles.get("99.000000", 0)) / 1000, 2)
        metrics["latency_p99999"] = round(float(percentiles.get("99.999000", 0)) / 1000, 2)

        return {"status": "PASS", "metrics": metrics, "raw_data": data}  # 待验证

    def _validate_result(self, result, test_name, test_info=None):
        """验证测试结果是否达标"""
        if result.get("status") == "ERROR":
            return "FAIL"

        metrics = result.get("metrics", {})

        # 优先使用测试配置中的验收目标（从 tests.json 读取）
        if test_info and "target" in test_info:
            target_config = test_info["target"]
            test_type = test_info.get("type", "bandwidth")

            # 带宽测试
            if test_type == "bandwidth":
                target = target_config.get("value", 0)
                tolerance = target_config.get("tolerance", 0.95)
                actual = metrics.get("bandwidth", 0)
                if actual >= target * tolerance:
                    return "PASS"
                else:
                    return "FAIL"

            # IOPS 测试
            elif test_type == "iops":
                target = target_config.get("value", 0)
                tolerance = target_config.get("tolerance", 0.95)
                actual = metrics.get("iops", 0)
                if actual >= target * tolerance:
                    return "PASS"
                else:
                    return "FAIL"

            # 延迟测试
            elif test_type == "latency":
                # 检查各项延迟指标
                if "p9999" in target_config:
                    if metrics.get("latency_p99999", 0) > target_config["p9999"]:
                        return "FAIL"
                if "p999" in target_config:
                    if metrics.get("latency_p999", 0) > target_config["p999"]:
                        return "FAIL"
                if "p99" in target_config:
                    if metrics.get("latency_p99", 0) > target_config["p99"]:
                        return "FAIL"
                if "stddev" in target_config:
                    if metrics.get("latency_stddev", 0) > target_config["stddev"]:
                        return "FAIL"
                return "PASS"

            # 场景测试
            elif test_type == "scenario":
                if "total_bandwidth" in target_config:
                    actual = metrics.get("bandwidth", 0)
                    target = target_config["total_bandwidth"]
                    if actual < target * 0.95:
                        return "FAIL"
                if "read_bandwidth" in target_config:
                    actual = metrics.get("bandwidth", 0)
                    target = target_config["read_bandwidth"]
                    if actual < target * 0.95:
                        return "FAIL"
                return "PASS"

            # 可靠性测试
            elif test_type == "reliability":
                if "max_errors" in target_config:
                    # 检查错误计数 (需要从 raw_data 中提取)
                    pass
                if "max_performance_drop" in target_config:
                    # 检查性能衰减 (需要历史数据对比)
                    pass
                return "PASS"

        # 向后兼容：使用全局配置
        targets = self.config.get("targets", {})

        # 新命名规则的测试用例从 test_info 中获取目标值
        # 旧命名的测试用例使用以下映射
        target_map = {
            "seq_read_burst": targets.get("seq_read_burst", 2100),
            "seq_read_sustained": targets.get("seq_read_sustained", 1800),
            "seq_write_burst": targets.get("seq_write_burst", 1650),
            "seq_write_sustained": targets.get("seq_write_sustained", 250),
            "rand_read_burst": targets.get("rand_read_burst", 200),
            "rand_read_sustained": targets.get("rand_read_sustained", 105),
            "rand_write_burst": targets.get("rand_write_burst", 330),
            "rand_write_sustained": targets.get("rand_write_sustained", 60),
        }

        target = target_map.get(test_name)
        if not target:
            return "PASS"  # 无目标值，默认通过

        # 判断是带宽测试还是 IOPS 测试
        if "seq" in test_name:
            actual = metrics.get("bandwidth", 0)
        else:
            actual = metrics.get("iops", 0)

        # 允许 5% 的误差
        tolerance = 0.95
        if actual >= target * tolerance:
            return "PASS"
        else:
            return "FAIL"

    def _calculate_summary(self, test_cases):
        """计算测试摘要"""
        total = len(test_cases)
        passed = sum(1 for tc in test_cases if tc.get("status") == "PASS")
        failed = sum(1 for tc in test_cases if tc.get("status") == "FAIL")
        errors = sum(1 for tc in test_cases if tc.get("status") == "ERROR")

        pass_rate = (passed / total * 100) if total > 0 else 0

        return {"total": total, "passed": passed, "failed": failed, "errors": errors, "pass_rate": round(pass_rate, 1)}
