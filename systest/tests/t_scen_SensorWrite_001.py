#!/usr/bin/env python3
"""
测试目的：
    模拟智驾传感器数据写入场景，验证 UFS 设备在多路传感器并发写入时的带宽性能，
    确保满足≥400 MB/s 的写入带宽要求。

测试模块：scen
测试用例 ID：t_scen_SensorWrite_001
测试优先级：P1

Precondition: 1.1~1.6 同 perf 用例
Test Steps: FIO write, bs=1M, iodepth=8, numjobs=4 (模拟 4 路传感器), runtime=300, direct=1
Postcondition: 等待 5 秒 / 清理 + fstrim / 状态对比

测试参数: rw=write, bs=1M, iodepth=8, numjobs=4, runtime=300, direct=1

验收标准:
    - PASS: 总带宽 ≥ 400 MB/s (允许 5% 误差，即≥380 MB/s)
    - FAIL: 总带宽 < 380 MB/s

注意事项:
    - 模拟 4 路传感器 (4 个摄像头) 同时写入
    - 1MB 块大小模拟视频帧写入
    - 关注各线程带宽均衡性

修改记录：
    2026-03-19 QA Agent 初始版本
"""

import shutil, sys, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "core"))
from systest import Systest
from test_helpers import (collect_device_info, collect_health_status, collect_storage_config, collect_system_info, collect_ufs_config, compare_health, find_test_dir, parse_fio_output, run_fio, try_fstrim)

TEST_NAME = "t_scen_SensorWrite_001"
EXPECTED_BW = 400  # MB/s
TOLERANCE = 0.05
FIO_PARAMS = {"rw": "write", "bs": "1M", "iodepth": 8, "numjobs": 4, "runtime": 300, "size": "2G"}
RW_TYPE = "WRITE"

def main():
    kit = Systest(test_name=TEST_NAME, device="/dev/ufs0", output_dir="./results/scen", log_dir="./logs")

    kit.step("Precondition")
    sys_info = collect_system_info(); dev_info = collect_device_info(kit.device)
    storage_config = collect_storage_config(kit.device); ufs_config = collect_ufs_config(kit.device)
    health_before = collect_health_status(kit.device)
    kit.info(f"设备: {dev_info['model']} | SMART: {'PASSED' if health_before['smart_passed'] else 'FAILED'} | Temp: {health_before['temperature_c']}℃")
    precondition = kit.check_precondition(mode="development")
    if health_before["temperature_c"] and health_before["temperature_c"] >= 70: kit.report({"status": "SKIP"}); return 1
    if not precondition.get("passed", True) and precondition.get("errors"): kit.report({"status": "SKIP"}); return 1
    test_dir = find_test_dir(min_free_gb=10)
    if not test_dir: kit.report({"status": "SKIP", "reason": "空间不足"}); return 1

    kit.step("Test Steps - 传感器写入场景测试")
    kit.info(f"FIO 参数: {FIO_PARAMS} | 模拟 4 路传感器并发写入")
    success, output, error = run_fio(test_dir, FIO_PARAMS, job_name="sensor_write")
    if not success: kit.fail(f"FIO 失败：{error}"); shutil.rmtree(test_dir, ignore_errors=True); kit.report({"status": "FAIL"}); return 1
    parsed_result = parse_fio_output(output, rw_type=RW_TYPE)
    kit.info(f"传感器写入带宽: {parsed_result['bandwidth_mbs']} MB/s | IOPS: {parsed_result['iops']}")

    kit.step("Postcondition"); time.sleep(5); shutil.rmtree(test_dir, ignore_errors=True); try_fstrim(test_dir)
    health_after = collect_health_status(kit.device); changes = compare_health(health_before, health_after)
    if changes["error_increase"] > 0: kit.fail(f"新增 {changes['error_increase']} 个错误")
    postcondition = kit.check_postcondition(precondition)
    if postcondition.get("critical_fail"): kit.report({"status": "FAIL", "reason": "坏块增加"}); return 1

    kit.step("验收标准判定")
    min_bw = EXPECTED_BW * (1 - TOLERANCE); passed = parsed_result["bandwidth_mbs"] >= min_bw
    kit.info(f"验收: {parsed_result['bandwidth_mbs']} MB/s >= {min_bw} MB/s → {'PASS' if passed else 'FAIL'}")
    kit.report({"status": "PASS" if passed else "FAIL", "metrics": parsed_result, "health_before": health_before, "health_after": health_after, "changes": changes})
    return 0 if passed else 1

if __name__ == "__main__": sys.exit(main())
