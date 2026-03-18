#!/usr/bin/env python3
"""
测试目的：
    验证 UFS 设备的随机写 IOPS Burst 性能，评估设备在小文件随机写入场景下的峰值 IOPS，
    确保满足车规级 UFS 3.1 的≥330 KIOPS 要求。

测试模块：perf
测试用例 ID：t_perf_RandWriteBurst_007
测试优先级：P0

Precondition: 1.1~1.6 同其他 perf 用例
Test Steps: FIO randwrite, bs=4k, iodepth=32, runtime=60, direct=1
Postcondition: 等待 5 秒 / 清理 + fstrim / 状态对比

测试参数: rw=randwrite, bs=4k, iodepth=32, runtime=60, direct=1

验收标准:
    - PASS: ≥330 KIOPS (允许 5% 误差，即≥313.5 KIOPS)
    - FAIL: <313.5 KIOPS

注意事项:
    - 4K 随机写模拟小文件写入场景
    - 测试前建议执行 TRIM
    - 建议重复 3 次取平均

修改记录：
    2026-03-19 QA Agent 初始版本
"""

import shutil, sys, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "core"))
from systest import Systest
from test_helpers import (collect_device_info, collect_health_status, collect_storage_config, collect_system_info, collect_ufs_config, compare_health, find_test_dir, parse_fio_output, run_fio, try_fstrim)

TEST_NAME = "t_perf_RandWriteBurst_007"
EXPECTED_IOPS_K = 330
TOLERANCE = 0.05
FIO_PARAMS = {"rw": "randwrite", "bs": "4k", "iodepth": 32, "numjobs": 1, "runtime": 60, "size": "4G"}
RW_TYPE = "WRITE"

def main():
    kit = Systest(test_name=TEST_NAME, device="/dev/ufs0", output_dir="./results/perf", log_dir="./logs")
    kit.step("Precondition - 1.1 系统环境"); sys_info = collect_system_info()
    kit.info(f"OS: {sys_info['os']} | CPU: {sys_info['cpu_model']} | Mem: {sys_info['mem_total_gb']} GB | FIO: {sys_info['fio_version']}")
    kit.step("Precondition - 1.2 设备信息"); dev_info = collect_device_info(kit.device)
    kit.info(f"设备: {dev_info['device']} | 型号: {dev_info['model']} | 容量: {dev_info['capacity_gb']} GB")
    kit.step("Precondition - 1.3 存储配置"); storage_config = collect_storage_config(kit.device)
    kit.info(f"WB: {storage_config['write_booster']} | Power: {storage_config['power_mode']}")
    kit.step("Precondition - 1.4 UFS 配置"); ufs_config = collect_ufs_config(kit.device)
    kit.info(f"UFS: {ufs_config['ufs_version']} | LUN: {ufs_config['lun_count']}")
    kit.step("Precondition - 1.5 健康状况"); health_before = collect_health_status(kit.device)
    kit.info(f"SMART: {'PASSED' if health_before['smart_passed'] else 'FAILED/UNKNOWN'} | Temp: {health_before['temperature_c']}℃ | Errors: {health_before['ufs_error_count']}")
    kit.step("Precondition - 1.6 验证"); precondition = kit.check_precondition(mode="development")
    if health_before["temperature_c"] and health_before["temperature_c"] >= 70: kit.report({"status": "SKIP"}); return 1
    if not precondition.get("passed", True) and precondition.get("errors"): kit.report({"status": "SKIP"}); return 1
    test_dir = find_test_dir(min_free_gb=5)
    if not test_dir: kit.report({"status": "SKIP", "reason": "空间不足"}); return 1
    precondition_snapshot = {"sys_info": sys_info, "dev_info": dev_info, "storage_config": storage_config, "ufs_config": ufs_config, "health_before": health_before}

    kit.step("Test Steps - FIO 随机写 Burst")
    success, output, error = run_fio(test_dir, FIO_PARAMS, job_name="rand_write_burst")
    if not success: kit.fail(f"FIO 失败：{error}"); shutil.rmtree(test_dir, ignore_errors=True); kit.report({"status": "FAIL"}); return 1
    parsed_result = parse_fio_output(output, rw_type=RW_TYPE)
    actual_kiops = parsed_result["iops"] / 1000
    kit.info(f"随机写 IOPS: {parsed_result['iops']} ({actual_kiops:.1f} KIOPS) | 延迟: {parsed_result['latency_avg_us']} μs")

    kit.step("Postcondition"); time.sleep(5); shutil.rmtree(test_dir, ignore_errors=True); try_fstrim(test_dir)
    health_after = collect_health_status(kit.device); changes = compare_health(health_before, health_after)
    kit.info(f"Temp: {health_before.get('temperature_c', 'N/A')} → {health_after.get('temperature_c', 'N/A')}℃ | Errors: {changes['error_increase']}")
    if changes["error_increase"] > 0: kit.fail(f"新增 {changes['error_increase']} 个错误")
    postcondition = kit.check_postcondition(precondition)
    if postcondition.get("critical_fail"): kit.report({"status": "FAIL", "reason": "坏块增加"}); return 1

    kit.step("验收标准判定")
    min_iops_k = EXPECTED_IOPS_K * (1 - TOLERANCE); passed = actual_kiops >= min_iops_k
    kit.info(f"验收: {actual_kiops:.1f} KIOPS >= {min_iops_k} KIOPS → {'PASS' if passed else 'FAIL'}")
    kit.report({"status": "PASS" if passed else "FAIL", "metrics": parsed_result, "precondition_snapshot": precondition_snapshot, "health_before": health_before, "health_after": health_after, "changes": changes})
    return 0 if passed else 1

if __name__ == "__main__": sys.exit(main())
