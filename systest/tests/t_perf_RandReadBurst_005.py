#!/usr/bin/env python3
"""
测试目的：
    验证 UFS 设备的随机读 IOPS Burst 性能，评估设备在小文件随机读取场景下的峰值 IOPS，
    确保满足车规级 UFS 3.1 的≥200 KIOPS 要求。

测试模块：perf
测试用例 ID：t_perf_RandReadBurst_005
测试优先级：P0

Precondition:
    1.1 系统环境收集 - 读取 OS/CPU/内存/FIO 版本
    1.2 测试目标信息收集 - 设备路径/型号/固件/容量/可用空间
    1.3 存储设备配置检查 - Write Booster/省电模式状态
    1.4 UFS 器件配置检查 - UFS 版本/LUN 数量
    1.5 器件健康状况检查 - SMART/温度/错误计数
    1.6 前置条件验证 - SMART PASSED / 空间≥10GB / 温度<70℃ / 寿命>90%

Test Steps:
    1. 在可用空间≥5GB 的目录下创建临时测试目录
    2. 使用 FIO 发起随机读测试 (rw=randread, bs=4k, iodepth=32, runtime=60, direct=1)
    3. FIO 持续随机读取 60 秒，记录 IOPS 数据
    4. 解析 FIO 输出，提取平均 IOPS、延迟数据

Postcondition:
    - 设备恢复：等待 5 秒回到空闲
    - 数据清理：删除临时文件
    - 测试后状态检查：对比温度/错误计数变化

测试参数:
    - rw: randread（随机读）
    - bs: 4k（4KB，模拟小文件随机访问）
    - iodepth: 32（充分利用 NCQ 并行性）
    - numjobs: 1
    - runtime: 60（Burst）
    - direct: 1

验收标准:
    - PASS: 平均 IOPS ≥ 200 KIOPS（允许 5% 误差，即≥190 KIOPS）
    - FAIL: 平均 IOPS < 190 KIOPS

注意事项:
    - 4K 随机读模拟小文件读取场景
    - 队列深度 32 充分利用 NCQ 并行性
    - 如果 IOPS 不达标，检查队列深度配置
    - 建议重复测试 3 次取平均值

修改记录：
    2026-03-19 QA Agent 初始版本
"""

import shutil
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "core"))

from systest import Systest
from test_helpers import (
    collect_device_info, collect_health_status, collect_storage_config,
    collect_system_info, collect_ufs_config, compare_health,
    find_test_dir, parse_fio_output, run_fio,
)

TEST_NAME = "t_perf_RandReadBurst_005"
EXPECTED_IOPS_K = 200  # KIOPS
TOLERANCE = 0.05
FIO_PARAMS = {"rw": "randread", "bs": "4k", "iodepth": 32, "numjobs": 1, "runtime": 60, "size": "4G"}
RW_TYPE = "READ"


def main():
    kit = Systest(test_name=TEST_NAME, device="/dev/ufs0", output_dir="./results/perf", log_dir="./logs")

    kit.step("Precondition - 1.1 系统环境收集")
    sys_info = collect_system_info()
    kit.info(f"操作系统: {sys_info['os']} | CPU: {sys_info['cpu_model']} ({sys_info['cpu_cores']} cores) | 内存: {sys_info['mem_total_gb']} GB | FIO: {sys_info['fio_version']}")

    kit.step("Precondition - 1.2 测试目标信息收集")
    dev_info = collect_device_info(kit.device)
    kit.info(f"设备: {dev_info['device']} | 型号: {dev_info['model']} | 固件: {dev_info['firmware']} | 容量: {dev_info['capacity_gb']} GB")

    kit.step("Precondition - 1.3 存储设备配置检查")
    storage_config = collect_storage_config(kit.device)
    kit.info(f"Write Booster: {storage_config['write_booster']} | 省电模式: {storage_config['power_mode']}")

    kit.step("Precondition - 1.4 UFS 器件配置检查")
    ufs_config = collect_ufs_config(kit.device)
    kit.info(f"UFS 版本: {ufs_config['ufs_version']} | LUN 数量: {ufs_config['lun_count']}")

    kit.step("Precondition - 1.5 器件健康状况检查")
    health_before = collect_health_status(kit.device)
    kit.info(f"SMART: {'PASSED' if health_before['smart_passed'] else 'FAILED/UNKNOWN'} | 温度: {health_before['temperature_c']}℃ | UFS 错误: {health_before['ufs_error_count']}")

    kit.step("Precondition - 1.6 前置条件验证")
    precondition = kit.check_precondition(mode="development")
    if health_before["temperature_c"] and health_before["temperature_c"] >= 70:
        kit.fail("温度过高"); kit.report({"status": "SKIP", "reason": "温度过高"}); return 1
    if not precondition.get("passed", True) and precondition.get("errors"):
        kit.fail("Precondition 失败"); kit.report({"status": "SKIP"}); return 1

    test_dir = find_test_dir(min_free_gb=5)
    if not test_dir:
        kit.fail("空间不足"); kit.report({"status": "SKIP", "reason": "空间不足"}); return 1

    precondition_snapshot = {"sys_info": sys_info, "dev_info": dev_info, "storage_config": storage_config, "ufs_config": ufs_config, "health_before": health_before}

    kit.step("Test Steps - 执行 FIO 随机读 Burst 测试")
    kit.info(f"FIO 参数: {FIO_PARAMS}")
    success, output, error = run_fio(test_dir, FIO_PARAMS, job_name="rand_read_burst")
    if not success:
        kit.fail(f"FIO 失败：{error}"); shutil.rmtree(test_dir, ignore_errors=True)
        kit.report({"status": "FAIL", "reason": f"FIO 失败：{error}"}); return 1

    parsed_result = parse_fio_output(output, rw_type=RW_TYPE)
    actual_kiops = parsed_result["iops"] / 1000
    kit.info(f"随机读 IOPS: {parsed_result['iops']} ({actual_kiops:.1f} KIOPS) | 延迟: {parsed_result['latency_avg_us']} μs")

    # Postcondition
    kit.step("Postcondition")
    time.sleep(5)
    shutil.rmtree(test_dir, ignore_errors=True)
    health_after = collect_health_status(kit.device)
    changes = compare_health(health_before, health_after)
    kit.info(f"温度变化: {health_before.get('temperature_c', 'N/A')} → {health_after.get('temperature_c', 'N/A')}℃ | 错误变化: {changes['error_increase']}")
    if changes["error_increase"] > 0: kit.fail(f"新增 {changes['error_increase']} 个 UFS 错误")

    postcondition = kit.check_postcondition(precondition)
    if postcondition.get("critical_fail", False):
        kit.report({"status": "FAIL", "reason": "坏块增加"}); return 1

    kit.step("验收标准判定")
    min_iops_k = EXPECTED_IOPS_K * (1 - TOLERANCE)
    passed = actual_kiops >= min_iops_k
    kit.info(f"验收: {actual_kiops:.1f} KIOPS >= {min_iops_k} KIOPS → {'PASS' if passed else 'FAIL'}")

    kit.report({"status": "PASS" if passed else "FAIL", "metrics": parsed_result, "precondition_snapshot": precondition_snapshot,
                "health_before": health_before, "health_after": health_after, "changes": changes})
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
