#!/usr/bin/env python3
"""
测试目的：
    验证 UFS 设备的顺序写带宽 Burst 性能，评估设备在短时间内能达到的最大写入带宽，
    确保满足车规级 UFS 3.1 的≥1650 MB/s 要求。

测试模块：perf
测试用例 ID：t_perf_SeqWriteBurst_003
测试优先级：P0

Precondition:
    1.1 系统环境收集
        - 操作系统：读取 /etc/os-release，收集 PRETTY_NAME 字段
        - CPU：读取 /proc/cpuinfo，收集 model name 和 cpu cores
        - 内存：读取 /proc/meminfo，收集 MemTotal
        - FIO 版本：执行 fio --version，收集版本号

    1.2 测试目标信息收集
        - 设备路径：检查 /dev/ufs0 或 /dev/sda 是否存在
        - 设备型号/固件版本/容量/可用空间

    1.3 存储设备配置检查
        - Write Booster 状态：对写入 Burst 性能影响显著，需特别关注
        - 省电模式状态
        - 记录当前配置快照

    1.4 UFS 器件配置检查
        - UFS 版本、LUN 数量

    1.5 器件健康状况检查
        - SMART 状态、温度、错误计数

    1.6 前置条件验证
        - ✓ SMART PASSED / 可用空间≥10GB / 温度<70℃ / 寿命>90%

Test Steps:
    1. 在可用空间≥5GB 的目录下创建临时测试目录
    2. 使用 FIO 工具发起顺序写测试
       - 参数：rw=write, bs=128k, iodepth=32, numjobs=1, runtime=60, time_based, direct=1
    3. FIO 持续写入 60 秒，记录带宽数据
    4. 解析 FIO 输出，提取平均带宽、IOPS、延迟数据

Postcondition:
    - 设备恢复：等待 5 秒回到空闲状态
    - 数据清理：删除临时文件 + 执行 fstrim 清理未使用块
    - 测试后状态检查：对比温度变化、错误计数变化

测试参数:
    - rw: write（顺序写）
    - bs: 128k（128KB）
    - iodepth: 32
    - numjobs: 1
    - runtime: 60（Burst 模式）
    - direct: 1

验收标准:
    - PASS: 平均带宽 ≥ 1650 MB/s（允许 5% 误差，即≥1567.5 MB/s）
    - FAIL: 平均带宽 < 1567.5 MB/s

注意事项:
    - Write Booster (SLC Cache) 对 Burst 写入性能影响极大
    - 测试前建议执行 TRIM，确保设备处于最佳状态
    - 如果测试失败，检查 SLC Cache 状态、温度、Write Booster 是否启用
    - 建议重复测试 3 次取平均值

修改记录：
    2026-03-18 QA Agent 初始版本
    2026-03-18 QA Agent 重构：公共函数抽取到 test_helpers
"""

import shutil
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "core"))

from systest import Systest
from test_helpers import (
    collect_device_info,
    collect_health_status,
    collect_storage_config,
    collect_system_info,
    collect_ufs_config,
    compare_health,
    find_test_dir,
    parse_fio_output,
    run_fio,
    try_fstrim,
)

# ============================================================
# 测试配置
# ============================================================

TEST_NAME = "t_perf_SeqWriteBurst_003"
EXPECTED_BANDWIDTH = 1650  # MB/s
TOLERANCE = 0.05           # 5%
FIO_PARAMS = {
    "rw": "write",
    "bs": "128k",
    "iodepth": 32,
    "numjobs": 1,
    "runtime": 60,
    "size": "4G",
}
RW_TYPE = "WRITE"


# ============================================================
# 主测试流程
# ============================================================

def main():
    kit = Systest(
        test_name=TEST_NAME,
        device="/dev/ufs0",
        output_dir="./results/perf",
        log_dir="./logs",
    )

    # ========== Precondition ==========
    kit.step("Precondition - 1.1 系统环境收集")
    sys_info = collect_system_info()
    kit.info(f"操作系统: {sys_info['os']}")
    kit.info(f"CPU: {sys_info['cpu_model']} ({sys_info['cpu_cores']} cores)")
    kit.info(f"内存: {sys_info['mem_total_gb']} GB")
    kit.info(f"FIO: {sys_info['fio_version']}")

    kit.step("Precondition - 1.2 测试目标信息收集")
    dev_info = collect_device_info(kit.device)
    kit.info(f"设备路径: {dev_info['device']} (exists={dev_info['device_exists']})")
    kit.info(f"设备型号: {dev_info['model']}")
    kit.info(f"固件版本: {dev_info['firmware']}")
    kit.info(f"设备容量: {dev_info['capacity_gb']} GB")

    kit.step("Precondition - 1.3 存储设备配置检查")
    storage_config = collect_storage_config(kit.device)
    kit.info(f"Write Booster: {storage_config['write_booster']}")
    kit.info(f"省电模式: {storage_config['power_mode']}")
    if storage_config["write_booster"] == "0":
        kit.info("⚠️ Write Booster 未启用，可能影响写入 Burst 性能")

    kit.step("Precondition - 1.4 UFS 器件配置检查")
    ufs_config = collect_ufs_config(kit.device)
    kit.info(f"UFS 版本: {ufs_config['ufs_version']}")
    kit.info(f"LUN 数量: {ufs_config['lun_count']}")

    kit.step("Precondition - 1.5 器件健康状况检查")
    health_before = collect_health_status(kit.device)
    kit.info(f"SMART 状态: {'PASSED' if health_before['smart_passed'] else 'FAILED/UNKNOWN'}")
    kit.info(f"温度: {health_before['temperature_c']}℃" if health_before["temperature_c"] else "温度: 未知")
    kit.info(f"UFS 错误计数: {health_before['ufs_error_count']}")

    kit.step("Precondition - 1.6 前置条件验证")
    precondition = kit.check_precondition(mode="development")

    if health_before["temperature_c"] and health_before["temperature_c"] >= 70:
        kit.fail(f"温度过高 ({health_before['temperature_c']}℃ >= 70℃)")
        kit.report({"status": "SKIP", "reason": "温度过高"})
        return 1

    if not precondition.get("passed", True) and precondition.get("errors"):
        kit.fail("Precondition 检查失败")
        kit.report({"status": "SKIP", "reason": "Precondition 失败", "precondition": precondition})
        return 1

    test_dir = find_test_dir(min_free_gb=5)
    if not test_dir:
        kit.fail("未找到可用空间≥5GB 的目录")
        kit.report({"status": "SKIP", "reason": "空间不足"})
        return 1
    kit.info(f"测试目录: {test_dir}")

    precondition_snapshot = {
        "sys_info": sys_info, "dev_info": dev_info,
        "storage_config": storage_config, "ufs_config": ufs_config,
        "health_before": health_before,
    }

    # ========== Test Steps ==========
    kit.step("Test Steps - 执行 FIO 顺序写 Burst 测试")
    kit.info(f"FIO 参数: {FIO_PARAMS}")

    success, output, error = run_fio(test_dir, FIO_PARAMS, job_name="seq_write_burst")

    if not success:
        kit.fail(f"FIO 执行失败：{error}")
        shutil.rmtree(test_dir, ignore_errors=True)
        kit.report({"status": "FAIL", "reason": f"FIO 执行失败：{error}", "precondition_snapshot": precondition_snapshot})
        return 1

    parsed_result = parse_fio_output(output, rw_type=RW_TYPE)
    kit.info(f"顺序写带宽: {parsed_result['bandwidth_mbs']} MB/s")
    kit.info(f"IOPS: {parsed_result['iops']}")
    kit.info(f"平均延迟: {parsed_result['latency_avg_us']} μs")

    # ========== Postcondition ==========
    kit.step("Postcondition - 设备恢复")
    kit.info("等待 5 秒，让设备回到空闲状态...")
    time.sleep(5)

    kit.step("Postcondition - 数据清理")
    shutil.rmtree(test_dir, ignore_errors=True)
    kit.info(f"已清理测试目录: {test_dir}")

    if try_fstrim(test_dir):
        kit.info("fstrim 执行成功，已清理未使用块")
    else:
        kit.info("fstrim 不可用或执行失败（非关键）")

    kit.step("Postcondition - 测试后状态检查")
    health_after = collect_health_status(kit.device)
    changes = compare_health(health_before, health_after)

    kit.info(f"温度变化: {health_before.get('temperature_c', 'N/A')} → {health_after.get('temperature_c', 'N/A')}℃")
    kit.info(f"UFS 错误变化: {health_before['ufs_error_count']} → {health_after['ufs_error_count']}")

    if changes["error_increase"] > 0:
        kit.fail(f"测试期间新增 {changes['error_increase']} 个 UFS 错误")

    postcondition = kit.check_postcondition(precondition)

    if postcondition.get("critical_fail", False):
        kit.fail("Postcondition 检查失败：坏块数量增加")
        kit.report({"status": "FAIL", "reason": "Postcondition 检查失败", "metrics": parsed_result,
                     "precondition_snapshot": precondition_snapshot, "postcondition": postcondition})
        return 1

    # ========== 验收标准判定 ==========
    kit.step("验收标准判定")
    min_bandwidth = EXPECTED_BANDWIDTH * (1 - TOLERANCE)
    passed = parsed_result["bandwidth_mbs"] >= min_bandwidth

    kit.info(f"验收标准: {parsed_result['bandwidth_mbs']} MB/s >= {min_bandwidth} MB/s → {'PASS' if passed else 'FAIL'}")

    status = "PASS" if passed else "FAIL"
    kit.report({
        "status": status, "metrics": parsed_result,
        "precondition_snapshot": precondition_snapshot,
        "health_before": health_before, "health_after": health_after,
        "changes": changes, "postcondition": postcondition,
    })

    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
