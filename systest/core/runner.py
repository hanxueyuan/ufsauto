#!/usr/bin/env python3
"""
测试执行引擎 - Test Runner
负责调度执行测试脚本 (tests/t_*.py)，收集结果，生成报告。

架构说明:
    bin/systest run -s perf
        ↓
    core/runner.py (本模块)
        ↓ 扫描 tests/t_perf_*.py
        ↓ 依次执行每个脚本 (subprocess)
        ↓ 收集 exit code + 日志 + JSON 结果
        ↓
    tests/t_perf_SeqReadBurst_001.py
        ↓ 脚本自己做 Precondition (test_helpers)
        ↓ 脚本自己执行 FIO (test_helpers)
        ↓ 脚本自己做 Postcondition (test_helpers)
        ↓ 输出 PASS/FAIL

    core/reporter.py → 汇总报告
    core/analyzer.py → 失效分析

脚本命名规范:
    t_<模块缩写>_<驼峰名称>_<3位编号>.py
    模块缩写: perf / func / rel / scen / qos

套件与模块对应关系:
    performance → perf
    function    → func
    reliability → rel
    scenario    → scen
    qos         → qos
"""

import json
import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path


# 套件名 → 脚本前缀映射
SUITE_PREFIX_MAP = {
    "performance": "perf",
    "perf": "perf",
    "function": "func",
    "func": "func",
    "reliability": "rel",
    "rel": "rel",
    "scenario": "scen",
    "scen": "scen",
    "qos": "qos",
}


class TestRunner:
    """测试执行器 - 调度执行测试脚本"""

    def __init__(
        self,
        device="/dev/ufs0",
        output_dir="./results",
        config=None,
        config_file=None,
        verbose=False,
        mode=None,
        log_dir="./logs",
        check_precondition=True,
    ):
        self.device = device
        self.output_dir = Path(output_dir)
        self.log_dir = Path(log_dir)
        self.verbose = verbose
        self.check_precondition = check_precondition

        # 加载配置
        if config_file:
            self.config = self._load_config(config_file)
        else:
            self.config = config or {}

        self.mode = mode or self.config.get("mode", "development")

        # 从配置获取执行参数
        exec_config = self.config.get("execution", {})
        self.loop_count = exec_config.get("loop_count", 1)
        self.retry_count = exec_config.get("retry_count", 1)

        # 测试脚本目录
        self.tests_dir = Path(__file__).parent.parent / "tests"

        # 创建输出目录
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.log_dir.mkdir(parents=True, exist_ok=True)

    def _load_config(self, config_file):
        """加载配置文件"""
        config_path = Path(config_file)
        if not config_path.is_absolute():
            config_path = Path(__file__).parent.parent / config_file

        if config_path.exists():
            with open(config_path, "r", encoding="utf-8") as f:
                return json.load(f)
        else:
            if self.verbose:
                print(f"⚠️  配置文件不存在：{config_path}，使用默认配置")
            return {}

    # ============================================================
    # 脚本扫描与套件构建
    # ============================================================

    def scan_tests(self, suite=None):
        """
        扫描 tests/ 目录下的测试脚本，构建测试列表。

        Args:
            suite: 套件名称 (如 "perf", "performance", "func", "all")
                   None 或 "all" 返回全部

        Returns:
            list[dict]: 测试列表，每项包含 name, file, suite, description
        """
        tests = []

        if not self.tests_dir.exists():
            if self.verbose:
                print(f"⚠️  测试目录不存在：{self.tests_dir}")
            return tests

        # 确定过滤前缀
        prefix_filter = None
        if suite and suite != "all":
            prefix_filter = SUITE_PREFIX_MAP.get(suite, suite)

        for test_file in sorted(self.tests_dir.glob("t_*.py")):
            name = test_file.stem  # 如 t_perf_SeqReadBurst_001

            # 解析模块缩写
            parts = name.split("_", 2)  # ["t", "perf", "SeqReadBurst_001"]
            if len(parts) < 3:
                continue

            module = parts[1]  # perf, func, rel, scen, qos

            # 按套件过滤
            if prefix_filter and module != prefix_filter:
                continue

            # 提取描述 (从脚本 docstring 的第一行)
            description = self._extract_description(test_file)

            tests.append({
                "name": name,
                "file": str(test_file),
                "suite": module,
                "description": description,
            })

        return tests

    def _extract_description(self, test_file):
        """从脚本 docstring 中提取测试目的 (第一行)"""
        try:
            with open(test_file, "r", encoding="utf-8") as f:
                content = f.read(2000)  # 只读前 2000 字符

            # 查找 测试目的：
            import re
            match = re.search(r"测试目的[：:]\s*\n?\s*(.+?)(?:\n|$)", content)
            if match:
                return match.group(1).strip()

            # 备选：docstring 第一行
            match = re.search(r'"""(.+?)(?:\n|""")', content)
            if match:
                return match.group(1).strip()
        except Exception:
            pass

        return ""

    def list_suites(self):
        """
        列出所有可用的测试套件和用例。

        Returns:
            dict: {suite_name: [test_info, ...]}
        """
        all_tests = self.scan_tests(suite="all")
        suites = {}

        for test in all_tests:
            suite = test["suite"]
            if suite not in suites:
                suites[suite] = []
            suites[suite].append(test)

        return suites

    # ============================================================
    # 测试执行
    # ============================================================

    def run_test(self, test_name, test_id=None):
        """
        执行单个测试脚本。

        Args:
            test_name: 测试用例名称 (如 t_perf_SeqReadBurst_001)
            test_id: 测试 ID (自动生成)

        Returns:
            dict: 测试结果
        """
        test_id = test_id or datetime.now().strftime("%Y%m%d_%H%M%S")

        # 查找脚本文件
        test_file = self._find_test_file(test_name)
        if not test_file:
            raise ValueError(f"未找到测试脚本：{test_name}")

        print(f"▶️  执行测试：{test_name}")
        if self.verbose:
            print(f"   脚本路径：{test_file}")
            print(f"   设备：{self.device}")
            print(f"   模式：{self.mode}")

        # 执行脚本 (支持循环)
        results = []
        for i in range(self.loop_count):
            if self.loop_count > 1:
                print(f"   第 {i + 1}/{self.loop_count} 次执行...")

            result = self._execute_script(test_name, test_file, test_id)
            result["loop"] = i + 1
            results.append(result)

        # 单次执行直接返回
        if self.loop_count == 1:
            result = results[0]
            result["test_id"] = test_id
            result["timestamp"] = datetime.now().isoformat()
            return result

        # 多次执行，汇总结果
        summary = self._summarize_loops(results)
        summary["test_id"] = test_id
        summary["test_name"] = test_name
        summary["timestamp"] = datetime.now().isoformat()
        summary["loops"] = results
        return summary

    def run_suite(self, suite_name, test_id=None):
        """
        执行测试套件 (按模块执行所有脚本)。

        Args:
            suite_name: 套件名称 (perf, func, rel, scen, qos, all)
            test_id: 测试 ID

        Returns:
            dict: 套件测试结果
        """
        test_id = test_id or datetime.now().strftime("%Y%m%d_%H%M%S")
        tests = self.scan_tests(suite=suite_name)

        if not tests:
            raise ValueError(f"套件 '{suite_name}' 中没有找到测试脚本")

        print(f"\n📦 执行套件：{suite_name}")
        print(f"   测试项数：{len(tests)}")
        print(f"   设备：{self.device}")
        print(f"   模式：{self.mode}")
        print("-" * 60)

        results = {
            "test_id": test_id,
            "suite": suite_name,
            "timestamp": datetime.now().isoformat(),
            "device": self.device,
            "mode": self.mode,
            "test_cases": [],
        }

        for i, test in enumerate(tests, 1):
            print(f"\n[{i}/{len(tests)}] {test['name']}")
            if test["description"]:
                print(f"   {test['description']}")

            try:
                result = self._execute_script(test["name"], test["file"], test_id)
                result["test_name"] = test["name"]
                results["test_cases"].append(result)

                status_icon = "✅" if result.get("status") == "PASS" else "❌"
                print(f"   {status_icon} {result.get('status', 'UNKNOWN')}")

            except Exception as e:
                print(f"   ❌ ERROR: {e}")
                results["test_cases"].append({
                    "test_name": test["name"],
                    "status": "ERROR",
                    "error": str(e),
                })

        # 计算摘要
        results["summary"] = self._calculate_summary(results["test_cases"])

        print("\n" + "=" * 60)
        summary = results["summary"]
        print(f"📊 套件执行完成：{summary['passed']}/{summary['total']} 通过 ({summary['pass_rate']}%)")

        return results

    def _find_test_file(self, test_name):
        """查找测试脚本文件"""
        # 直接匹配文件名
        test_file = self.tests_dir / f"{test_name}.py"
        if test_file.exists():
            return str(test_file)

        # 模糊匹配 (兼容旧命名)
        for f in self.tests_dir.glob("t_*.py"):
            if test_name in f.stem:
                return str(f)

        return None

    def _execute_script(self, test_name, test_file, test_id):
        """
        执行测试脚本 (subprocess)。

        脚本通过命令行参数接收配置：
            --device /dev/ufs0
            --output-dir ./results/perf
            --log-dir ./logs
            --mode development

        脚本通过 exit code 报告结果：
            0 = PASS
            1 = FAIL
            其他 = ERROR

        Args:
            test_name: 测试名称
            test_file: 脚本文件路径
            test_id: 测试 ID

        Returns:
            dict: 执行结果
        """
        # 构建命令
        cmd = [
            sys.executable,  # python3
            test_file,
            "--device", self.device,
            "--output-dir", str(self.output_dir),
            "--log-dir", str(self.log_dir),
            "--mode", self.mode,
        ]

        if self.verbose:
            cmd.append("--verbose")

        # 确定超时时间 (默认 10 分钟，sustained 测试 30 分钟)
        timeout = 600
        if "sustained" in test_name.lower() or "stability" in test_name.lower():
            timeout = 1800
        if "reliability" in test_name.lower():
            timeout = 90000  # 25 小时

        # 执行脚本
        start_time = time.time()
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=str(Path(test_file).parent.parent),  # systest/ 目录
            )

            duration = time.time() - start_time
            exit_code = result.returncode

            # 保存脚本输出日志
            log_file = self.log_dir / f"{test_name}_{test_id}.log"
            with open(log_file, "w", encoding="utf-8") as f:
                f.write(f"=== {test_name} ===\n")
                f.write(f"时间: {datetime.now().isoformat()}\n")
                f.write(f"Exit Code: {exit_code}\n")
                f.write(f"Duration: {duration:.1f}s\n")
                f.write(f"\n=== STDOUT ===\n{result.stdout}\n")
                if result.stderr:
                    f.write(f"\n=== STDERR ===\n{result.stderr}\n")

            if self.verbose:
                print(f"   耗时: {duration:.1f}s")
                print(f"   日志: {log_file}")

            # 解析结果
            status = "PASS" if exit_code == 0 else "FAIL"

            # 尝试从日志目录读取 JSON 结果
            metrics = self._extract_metrics_from_log(result.stdout)

            return {
                "test_name": test_name,
                "status": status,
                "exit_code": exit_code,
                "duration": round(duration, 1),
                "metrics": metrics,
                "log_file": str(log_file),
                "stdout": result.stdout[-2000:] if result.stdout else "",  # 保留最后 2000 字符
                "stderr": result.stderr[-500:] if result.stderr else "",
            }

        except subprocess.TimeoutExpired:
            duration = time.time() - start_time
            return {
                "test_name": test_name,
                "status": "ERROR",
                "exit_code": -1,
                "duration": round(duration, 1),
                "error": f"脚本执行超时 ({timeout}s)",
            }

        except Exception as e:
            duration = time.time() - start_time
            return {
                "test_name": test_name,
                "status": "ERROR",
                "exit_code": -1,
                "duration": round(duration, 1),
                "error": str(e),
            }

    def _extract_metrics_from_log(self, stdout):
        """从脚本输出中提取性能指标"""
        import re
        metrics = {}

        if not stdout:
            return metrics

        # 提取带宽
        bw_match = re.search(r"(?:顺序读|顺序写|随机读|随机写|混合)带宽:\s*([\d.]+)\s*MB/s", stdout)
        if bw_match:
            metrics["bandwidth_mbs"] = float(bw_match.group(1))

        # 提取 IOPS
        iops_match = re.search(r"IOPS:\s*(\d+)", stdout)
        if iops_match:
            metrics["iops"] = int(iops_match.group(1))

        # 提取延迟
        lat_match = re.search(r"平均延迟:\s*([\d.]+)\s*μs", stdout)
        if lat_match:
            metrics["latency_avg_us"] = float(lat_match.group(1))

        # 提取验收结果
        verdict_match = re.search(r"验收标准:.*→\s*(PASS|FAIL)", stdout)
        if verdict_match:
            metrics["verdict"] = verdict_match.group(1)

        return metrics

    # ============================================================
    # 结果汇总
    # ============================================================

    def _summarize_loops(self, results):
        """汇总多次循环执行的结果"""
        summary = {"status": "PASS", "metrics": {}}

        for r in results:
            if r.get("status") != "PASS":
                summary["status"] = "FAIL"
                break

        # 计算指标平均值
        bw_values = [r.get("metrics", {}).get("bandwidth_mbs", 0) for r in results
                     if r.get("metrics", {}).get("bandwidth_mbs")]
        if bw_values:
            summary["metrics"]["bandwidth_mbs_avg"] = round(sum(bw_values) / len(bw_values), 2)
            summary["metrics"]["bandwidth_mbs_values"] = bw_values

        return summary

    def _calculate_summary(self, test_cases):
        """计算套件测试摘要"""
        total = len(test_cases)
        passed = sum(1 for tc in test_cases if tc.get("status") == "PASS")
        failed = sum(1 for tc in test_cases if tc.get("status") == "FAIL")
        errors = sum(1 for tc in test_cases if tc.get("status") == "ERROR")
        skipped = sum(1 for tc in test_cases if tc.get("status") == "SKIP")

        pass_rate = (passed / total * 100) if total > 0 else 0

        return {
            "total": total,
            "passed": passed,
            "failed": failed,
            "errors": errors,
            "skipped": skipped,
            "pass_rate": round(pass_rate, 1),
        }
