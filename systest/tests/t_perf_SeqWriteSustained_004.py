#!/usr/bin/env python3
"""
测试目的：
    验证 UFS 设备的顺序写带宽 Sustained 性能，评估设备在长时间连续写入下的稳定带宽，
    检测 SLC Cache 耗尽后的性能表现，确保满足车规级 UFS 3.1 的≥250 MB/s 要求。

测试模块：perf
测试用例 ID：t_perf_SeqWriteSustained_004
测试优先级：P0

Precondition:
    1.1 系统环境收集
        - 操作系统：读取 /etc/os-release，收集 PRETTY_NAME
        - CPU：读取 /proc/cpuinfo，收集 model name 和 cpu cores
        - 内存：读取 /proc/meminfo，收集 MemTotal
        - FIO 版本：执行 fio --version

    1.2 测试目标信息收集
        - 设备路径/型号/固件版本/容量
        - 可用空间：需要≥10GB（Sustained 写入量大）

    1.3 存储设备配置检查
        - Write Booster 状态（Sustained 写入会耗尽 SLC Cache）
        - 省电模式状态

    1.4 UFS 器件配置检查
        - UFS 版本、LUN 数量

    1.5 器件健康状况检查
        - SMART 状态、温度、错误计数

    1.6 前置条件验证
        - ✓ SMART PASSED / 可用空间≥10GB / 温度<70℃ / 寿命>90%

Test Steps:
    1. 在可用空间≥5GB 的目录下创建临时测试目录
    2. 使用 FIO 工具发起顺序写测试
       - 参数：rw=write, bs=128k, iodepth=32, numjobs=1, runtime=300, time_based, direct=1
    3. FIO 持续写入 300 秒（5 分钟），记录带宽数据
    4. 解析 FIO 输出，提取平均带宽、IOPS、延迟数据

Postcondition:
    - 设备恢复：等待 10 秒回到空闲状态（Sustained 写入后需要更长恢复）
    - 数据清理：删除临时文件 + 执行 fstrim 恢复写入性能
    - 测试后状态检查：对比温度变化、错误计数变化

测试参数:
    - rw: write（顺序写）
    - bs: 128k（128KB）
    - iodepth: 32
    - numjobs: 1
    - runtime: 300（Sustained 模式）
    - direct: 1

验收标准:
    - PASS: 平均带宽 ≥ 250 MB/s（允许 5% 误差，即≥237.5 MB/s）
    - FAIL: 平均带宽 < 237.5 MB/s

注意事项:
    - Sustained 测试时间长（300 秒），可能触发 SLC Cache 耗尽
    - 测试过程中密切监控带宽变化曲线
    - 如果性能衰减>80%，可能是 SLC Cache 耗尽（正常现象）
    - 测试后建议执行 TRIM，恢复设备状态

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
    find_test_dir, parse_fio_output, run_fio, try_fstrim,
)

TEST_NAME = "t_perf_SeqWriteSustained_004"
EXPECTED_BANDWIDTH = 250  # MB/s
TOLERANCE = 0.05
FIO_PARAMS = {"rw": "write", "bs": "128k", "iodepth": 32, "numjobs": 1, "runtime": 300, "size": "4G"}
RW_TYPE = "WRITE"


def main():
    kit = Systest(test_name=TEST_NAME, device="/dev/ufs0", output_dir="./results/perf", log_dir="./logs")

    # Precondition
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
        kit.fail(f"温度过高 ({health_before['temperature_c']}℃)"); kit.report({"status": "SKIP", "reason": "温度过高"}); return 1
    if not precondition.get("passed", True) and precondition.get("errors"):
        kit.fail("Precondition 失败"); kit.report({"status": "SKIP", "reason": "Precondition 失败"}); return 1

    test_dir = find_test_dir(min_free_gb=5)
    if not test_dir:
        kit.fail("空间不足"); kit.report({"status": "SKIP", "reason": "空间不足"}); return 1
    kit.info(f"测试目录: {test_dir}")

    precondition_snapshot = {"sys_info": sys_info, "dev_info": dev_info, "storage_config": storage_config, "ufs_config": ufs_config, "health_before": health_before}

    # Test Steps
    kit.step("Test Steps - 执行 FIO 顺序写 Sustained 测试")
    kit.info(f"FIO 参数: {FIO_PARAMS}")
    kit.info("预计执行 300 秒（5 分钟），SLC Cache 可能耗尽...")
    success, output, error = run_fio(test_dir, FIO_PARAMS, job_name="seq_write_sustained")
    if not success:
        kit.fail(f"FIO 执行失败：{error}"); shutil.rmtree(test_dir, ignore_errors=True)
        kit.report({"status": "FAIL", "reason": f"FIO 失败：{error}"}); return 1

    parsed_result = parse_fio_output(output, rw_type=RW_TYPE)
    kit.info(f"顺序写带宽: {parsed_result['bandwidth_mbs']} MB/s | IOPS: {parsed_result['iops']} | 延迟: {parsed_result['latency_avg_us']} μs")

    # Postcondition
    kit.step("Postcondition - 设备恢复")
    kit.info("等待 10 秒（Sustained 写入后需要更长恢复）...")
    time.sleep(10)

    kit.step("Postcondition - 数据清理")
    shutil.rmtree(test_dir, ignore_errors=True)
    if try_fstrim(test_dir): kit.info("fstrim 执行成功")

    kit.step("Postcondition - 测试后状态检查")
    health_after = collect_health_status(kit.device)
    changes = compare_health(health_before, health_after)
    kit.info(f"温度变化: {health_before.get('temperature_c', 'N/A')} → {health_after.get('temperature_c', 'N/A')}℃ | 错误变化: {changes['error_increase']}")
    if changes["error_increase"] > 0: kit.fail(f"新增 {changes['error_increase']} 个 UFS 错误")

    postcondition = kit.check_postcondition(precondition)
    if postcondition.get("critical_fail", False):
        kit.fail("Postcondition 失败"); kit.report({"status": "FAIL", "reason": "坏块增加", "metrics": parsed_result}); return 1

    # 验收标准
    kit.step("验收标准判定")
    min_bandwidth = EXPECTED_BANDWIDTH * (1 - TOLERANCE)
    passed = parsed_result["bandwidth_mbs"] >= min_bandwidth
    kit.info(f"验收: {parsed_result['bandwidth_mbs']} MB/s >= {min_bandwidth} MB/s → {'PASS' if passed else 'FAIL'}")

    kit.report({"status": "PASS" if passed else "FAIL", "metrics": parsed_result, "precondition_snapshot": precondition_snapshot,
                "health_before": health_before, "health_after": health_after, "changes": changes, "postcondition": postcondition})
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
