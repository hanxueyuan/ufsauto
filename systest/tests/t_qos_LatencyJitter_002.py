#!/usr/bin/env python3
"""
测试目的：
    验证 UFS 设备的延迟抖动（Jitter）性能，评估延迟标准差是否满足车规级实时系统要求，
    确保 stddev ≤ 500μs。

测试模块：qos
测试用例 ID：t_qos_LatencyJitter_002
测试优先级：P0

Precondition: 1.1~1.6 同 perf 用例
Test Steps: FIO randread, bs=4k, iodepth=32, runtime=300, direct=1
Postcondition: 等待 5 秒 / 清理 / 状态对比

测试参数: rw=randread, bs=4k, iodepth=32, runtime=300, direct=1

验收标准:
    - PASS: 延迟 stddev ≤ 500μs
    - FAIL: 延迟 stddev > 500μs

注意事项:
    - 延迟抖动反映设备的一致性
    - 车规实时系统对抖动非常敏感
    - 如果抖动过大，检查 GC/WL 后台操作

修改记录：
    2026-03-19 QA Agent 初始版本
"""

import re
import shutil, sys, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "core"))
from systest import Systest
from test_helpers import (collect_device_info, collect_health_status, collect_storage_config, collect_system_info, collect_ufs_config, compare_health, find_test_dir, run_fio)

TEST_NAME = "t_qos_LatencyJitter_002"
MAX_STDDEV_US = 500
FIO_PARAMS = {"rw": "randread", "bs": "4k", "iodepth": 32, "numjobs": 1, "runtime": 300, "size": "4G"}


def parse_latency_stddev(output):
    """解析 FIO 延迟标准差"""
    result = {"avg_us": 0, "stddev_us": 0}

    avg_match = re.search(r"lat\s*\(usec\).*avg=\s*(\d+(?:\.\d+)?)", output)
    if avg_match:
        result["avg_us"] = float(avg_match.group(1))

    stddev_match = re.search(r"lat\s*\(usec\).*stdev=\s*(\d+(?:\.\d+)?)", output)
    if stddev_match:
        result["stddev_us"] = float(stddev_match.group(1))
    else:
        # msec
        stddev_match = re.search(r"lat\s*\(msec\).*stdev=\s*(\d+(?:\.\d+)?)", output)
        if stddev_match:
            result["stddev_us"] = float(stddev_match.group(1)) * 1000

    return result


def main():
    kit = Systest(test_name=TEST_NAME, device="/dev/ufs0", output_dir="./results/qos", log_dir="./logs")

    kit.step("Precondition")
    sys_info = collect_system_info(); dev_info = collect_device_info(kit.device)
    storage_config = collect_storage_config(kit.device); ufs_config = collect_ufs_config(kit.device)
    health_before = collect_health_status(kit.device)
    kit.info(f"设备: {dev_info['model']} | SMART: {'PASSED' if health_before['smart_passed'] else 'FAILED'} | Temp: {health_before['temperature_c']}℃")
    precondition = kit.check_precondition(mode="development")
    if health_before["temperature_c"] and health_before["temperature_c"] >= 70: kit.report({"status": "SKIP"}); return 1
    if not precondition.get("passed", True) and precondition.get("errors"): kit.report({"status": "SKIP"}); return 1
    test_dir = find_test_dir(min_free_gb=5)
    if not test_dir: kit.report({"status": "SKIP", "reason": "空间不足"}); return 1

    kit.step("Test Steps - FIO 延迟抖动测试")
    kit.info(f"FIO 参数: {FIO_PARAMS} | 预计 300 秒")
    success, output, error = run_fio(test_dir, FIO_PARAMS, job_name="latency_jitter")
    if not success: kit.fail(f"FIO 失败：{error}"); shutil.rmtree(test_dir, ignore_errors=True); kit.report({"status": "FAIL"}); return 1

    jitter_result = parse_latency_stddev(output)
    kit.info(f"平均延迟: {jitter_result['avg_us']}μs | 标准差: {jitter_result['stddev_us']}μs")

    kit.step("Postcondition"); time.sleep(5); shutil.rmtree(test_dir, ignore_errors=True)
    health_after = collect_health_status(kit.device); changes = compare_health(health_before, health_after)
    if changes["error_increase"] > 0: kit.fail(f"新增 {changes['error_increase']} 个错误")
    postcondition = kit.check_postcondition(precondition)
    if postcondition.get("critical_fail"): kit.report({"status": "FAIL", "reason": "坏块增加"}); return 1

    kit.step("验收标准判定")
    passed = jitter_result["stddev_us"] <= MAX_STDDEV_US
    kit.info(f"验收: stddev={jitter_result['stddev_us']}μs <= {MAX_STDDEV_US}μs → {'PASS' if passed else 'FAIL'}")

    kit.report({"status": "PASS" if passed else "FAIL", "metrics": jitter_result, "health_before": health_before, "health_after": health_after, "changes": changes})
    return 0 if passed else 1

if __name__ == "__main__": sys.exit(main())
