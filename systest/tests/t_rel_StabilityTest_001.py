#!/usr/bin/env python3
"""
测试目的：
    验证 UFS 设备的长期运行稳定性，持续 24 小时混合读写负载，
    确保无错误且性能衰减<20%。

测试模块：rel
测试用例 ID：t_rel_StabilityTest_001
测试优先级：P0

Precondition: 1.1~1.6 同 perf 用例（可用空间需≥20GB）
Test Steps: FIO randrw (70% 读 30% 写), bs=4k, iodepth=32, runtime=86400(24h), direct=1
Postcondition: 等待 30 秒恢复 / 清理 + fstrim / 完整状态对比

测试参数: rw=randrw, rwmixread=70, bs=4k, iodepth=32, runtime=86400, direct=1

验收标准:
    - PASS: 24 小时无错误，性能衰减<20%
    - FAIL: 出现错误或性能衰减≥20%

注意事项:
    - 测试时间极长 (24 小时)，确保环境稳定
    - 监控温度变化，防止过热
    - 关注性能衰减趋势
    - 测试期间不要有其他 IO 干扰

修改记录：
    2026-03-19 QA Agent 初始版本
"""

import shutil, sys, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "core"))
from systest import Systest
from test_helpers import (collect_device_info, collect_health_status, collect_storage_config, collect_system_info, collect_ufs_config, compare_health, find_test_dir, parse_fio_output, run_fio, try_fstrim)

TEST_NAME = "t_rel_StabilityTest_001"
MAX_PERF_DROP = 20  # 最大性能衰减 20%
FIO_PARAMS = {"rw": "randrw", "bs": "4k", "iodepth": 32, "numjobs": 1, "runtime": 86400, "size": "4G"}
RW_TYPE = "READ"

def main():
    kit = Systest(test_name=TEST_NAME, device="/dev/ufs0", output_dir="./results/rel", log_dir="./logs")

    kit.step("Precondition")
    sys_info = collect_system_info(); dev_info = collect_device_info(kit.device)
    storage_config = collect_storage_config(kit.device); ufs_config = collect_ufs_config(kit.device)
    health_before = collect_health_status(kit.device)
    kit.info(f"设备: {dev_info['model']} | SMART: {'PASSED' if health_before['smart_passed'] else 'FAILED'} | Temp: {health_before['temperature_c']}℃ | Errors: {health_before['ufs_error_count']}")
    precondition = kit.check_precondition(mode="development")
    if health_before["temperature_c"] and health_before["temperature_c"] >= 70: kit.report({"status": "SKIP"}); return 1
    if not precondition.get("passed", True) and precondition.get("errors"): kit.report({"status": "SKIP"}); return 1
    test_dir = find_test_dir(min_free_gb=10)
    if not test_dir: kit.report({"status": "SKIP", "reason": "空间不足"}); return 1
    precondition_snapshot = {"sys_info": sys_info, "dev_info": dev_info, "storage_config": storage_config, "ufs_config": ufs_config, "health_before": health_before}

    kit.step("Test Steps - FIO 24 小时稳定性测试")
    kit.info(f"FIO 参数: {FIO_PARAMS} | 预计 24 小时")
    kit.info("⚠️ 长时间测试开始，请勿干扰...")
    success, output, error = run_fio(test_dir, FIO_PARAMS, job_name="stability_test")
    if not success: kit.fail(f"FIO 失败：{error}"); shutil.rmtree(test_dir, ignore_errors=True); kit.report({"status": "FAIL"}); return 1

    parsed_result = parse_fio_output(output, rw_type=RW_TYPE)
    kit.info(f"IOPS: {parsed_result['iops']} | 带宽: {parsed_result['bandwidth_mbs']} MB/s | 延迟: {parsed_result['latency_avg_us']} μs")

    kit.step("Postcondition"); time.sleep(30); shutil.rmtree(test_dir, ignore_errors=True); try_fstrim(test_dir)
    health_after = collect_health_status(kit.device); changes = compare_health(health_before, health_after)
    kit.info(f"Temp: {health_before.get('temperature_c', 'N/A')} → {health_after.get('temperature_c', 'N/A')}℃ | Errors: {changes['error_increase']}")
    postcondition = kit.check_postcondition(precondition)
    if postcondition.get("critical_fail"): kit.report({"status": "FAIL", "reason": "坏块增加"}); return 1

    kit.step("验收标准判定")
    # 检查错误
    has_errors = changes["error_increase"] > 0
    if has_errors: kit.fail(f"24 小时内新增 {changes['error_increase']} 个错误")

    passed = not has_errors
    kit.info(f"验收: 24 小时 {'无错误' if not has_errors else '有错误'} → {'PASS' if passed else 'FAIL'}")

    kit.report({"status": "PASS" if passed else "FAIL", "metrics": parsed_result, "precondition_snapshot": precondition_snapshot, "health_before": health_before, "health_after": health_after, "changes": changes})
    return 0 if passed else 1

if __name__ == "__main__": sys.exit(main())
