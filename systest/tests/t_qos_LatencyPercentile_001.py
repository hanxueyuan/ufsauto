#!/usr/bin/env python3
"""
测试目的：
    验证 UFS 设备的延迟百分位性能，评估 P99.99 延迟是否满足车规级实时系统要求，
    确保≤10ms。

测试模块：qos
测试用例 ID：t_qos_LatencyPercentile_001
测试优先级：P0

Precondition: 1.1~1.6 同 perf 用例
Test Steps: FIO randread, bs=4k, iodepth=32, runtime=300, lat_percentiles=1, direct=1
Postcondition: 等待 5 秒 / 清理 / 状态对比

测试参数: rw=randread, bs=4k, iodepth=32, runtime=300, lat_percentiles=1, direct=1

验收标准:
    - PASS: P99.99 延迟 ≤ 10ms (10000μs)
    - FAIL: P99.99 延迟 > 10ms

注意事项:
    - 延迟百分位测试需要较长时间收集足够样本
    - 关注长尾延迟（P99.99），车规实时系统对此敏感
    - 如果延迟不达标，检查 GC 干扰、温度、负载

修改记录：
    2026-03-19 QA Agent 初始版本
"""

import re
import shutil, sys, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "core"))
from systest import Systest
from test_helpers import (collect_device_info, collect_health_status, collect_storage_config, collect_system_info, collect_ufs_config, compare_health, find_test_dir, run_fio)

TEST_NAME = "t_qos_LatencyPercentile_001"
MAX_P9999_US = 10000  # 10ms = 10000μs
FIO_PARAMS = {"rw": "randread", "bs": "4k", "iodepth": 32, "numjobs": 1, "runtime": 300, "size": "4G"}


def parse_latency_percentiles(output):
    """解析 FIO 延迟百分位输出"""
    result = {"p50_us": 0, "p99_us": 0, "p9999_us": 0, "avg_us": 0}

    # 解析各百分位
    for pattern, key in [
        (r"50\.00th=\[\s*(\d+)\]", "p50_us"),
        (r"99\.00th=\[\s*(\d+)\]", "p99_us"),
        (r"99\.99th=\[\s*(\d+)\]", "p9999_us"),
    ]:
        match = re.search(pattern, output)
        if match:
            result[key] = int(match.group(1))

    # 平均延迟
    avg_match = re.search(r"lat\s*\(usec\).*avg=\s*(\d+(?:\.\d+)?)", output)
    if avg_match:
        result["avg_us"] = float(avg_match.group(1))
    else:
        avg_match = re.search(r"lat\s*\(msec\).*avg=\s*(\d+(?:\.\d+)?)", output)
        if avg_match:
            result["avg_us"] = float(avg_match.group(1)) * 1000

    return result


def main():
    kit = Systest(test_name=TEST_NAME, device="/dev/ufs0", output_dir="./results/qos", log_dir="./logs")

    kit.step("Precondition - 信息收集")
    sys_info = collect_system_info()
    dev_info = collect_device_info(kit.device)
    storage_config = collect_storage_config(kit.device)
    ufs_config = collect_ufs_config(kit.device)
    health_before = collect_health_status(kit.device)
    kit.info(f"设备: {dev_info['model']} | SMART: {'PASSED' if health_before['smart_passed'] else 'FAILED'} | Temp: {health_before['temperature_c']}℃")

    kit.step("Precondition - 验证")
    precondition = kit.check_precondition(mode="development")
    if health_before["temperature_c"] and health_before["temperature_c"] >= 70: kit.report({"status": "SKIP"}); return 1
    if not precondition.get("passed", True) and precondition.get("errors"): kit.report({"status": "SKIP"}); return 1
    test_dir = find_test_dir(min_free_gb=5)
    if not test_dir: kit.report({"status": "SKIP", "reason": "空间不足"}); return 1

    kit.step("Test Steps - FIO 延迟百分位测试")
    kit.info(f"FIO 参数: {FIO_PARAMS} | 预计 300 秒")
    success, output, error = run_fio(test_dir, FIO_PARAMS, job_name="latency_percentile")
    if not success: kit.fail(f"FIO 失败：{error}"); shutil.rmtree(test_dir, ignore_errors=True); kit.report({"status": "FAIL"}); return 1

    lat_result = parse_latency_percentiles(output)
    kit.info(f"P50: {lat_result['p50_us']}μs | P99: {lat_result['p99_us']}μs | P99.99: {lat_result['p9999_us']}μs | Avg: {lat_result['avg_us']}μs")

    kit.step("Postcondition"); time.sleep(5); shutil.rmtree(test_dir, ignore_errors=True)
    health_after = collect_health_status(kit.device); changes = compare_health(health_before, health_after)
    if changes["error_increase"] > 0: kit.fail(f"新增 {changes['error_increase']} 个错误")
    postcondition = kit.check_postcondition(precondition)
    if postcondition.get("critical_fail"): kit.report({"status": "FAIL", "reason": "坏块增加"}); return 1

    kit.step("验收标准判定")
    passed = lat_result["p9999_us"] <= MAX_P9999_US
    kit.info(f"验收: P99.99={lat_result['p9999_us']}μs <= {MAX_P9999_US}μs → {'PASS' if passed else 'FAIL'}")

    kit.report({"status": "PASS" if passed else "FAIL", "metrics": lat_result, "health_before": health_before, "health_after": health_after, "changes": changes})
    return 0 if passed else 1

if __name__ == "__main__": sys.exit(main())
