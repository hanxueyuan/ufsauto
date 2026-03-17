#!/usr/bin/env python3
"""
测试用例：t_qos_LatencyPercentile_001
延迟百分位测试

测试目的:
验证 UFS 设备的延迟百分位指标，评估设备在不同负载下的延迟表现，
确保 p99.99 延迟<10ms，满足车规级实时性要求。

Precondition:
1.1 系统环境收集
    - 操作系统：读取 /etc/os-release，收集 PRETTY_NAME 字段
    - CPU/内存：收集并记录实际 CPU/内存配置（/proc/cpuinfo, /proc/meminfo）
    - FIO 版本：执行 fio --version，收集版本号

1.2 测试目标信息收集
    - 设备路径：检查/dev/ufs0 是否存在
    - 设备型号：读取并记录实际设备型号
    - 固件版本：读取并记录实际固件版本
    - 设备容量：读取并记录实际设备容量
    - 可用空间：调用 df 命令获取实际可用空间

1.3 存储设备配置检查
    - 查看支持的功能：
      - 方法 1：cat /sys/block/<device>/device/features
      - 方法 2：smartctl -i /dev/<device> | grep "Features"
      - 方法 3：hdparm -I /dev/<device> | grep "Advanced power management"
      - 预期：列出设备支持的所有功能列表
    - 需要开启的功能：
      - TURBO Mode（如支持）：
        - 检查方法：cat /sys/block/<device>/device/turbo_mode
        - 预期值：1（开启）
        - 开启方法：echo 1 > /sys/block/<device>/device/turbo_mode
      - Write Booster（如支持）：
        - 检查方法：cat /sys/block/<device>/device/write_booster
        - 预期值：1（开启）
        - 开启方法：echo 1 > /sys/block/<device>/device/write_booster
    - 需要关闭的功能：
      - 省电模式（Auto Low Power Mode）：
        - 检查方法：cat /sys/block/<device>/device/power_save
        - 预期值：0（关闭）
        - 关闭方法：echo 0 > /sys/block/<device>/device/power_save
      - 自动休眠（Auto Sleep）：
        - 检查方法：cat /sys/block/<device>/device/auto_sleep
        - 预期值：0（关闭）
        - 关闭方法：echo 0 > /sys/block/<device>/device/auto_sleep
    - 特殊配置项：
      - IO 调度器：
        - 检查方法：cat /sys/block/<device>/queue/scheduler
        - 预期值：none（性能测试推荐）
        - 设置方法：echo none > /sys/block/<device>/queue/scheduler

1.4 UFS 器件配置检查
    - LUN 数量：调用 _get_lun_count() 获取实际 LUN 数量
    -

1.5 器件健康状况检查
    - SMART 状态：调用 smartctl -H 检查实际 SMART 状态
    - 剩余寿命：调用 smartctl -l smartctl 获取实际剩余寿命
    - 温度状态：读取/sys/class/hwmon/*/temp*_input 获取实际温度
    - 错误计数：读取/sys/block/<device>/device/stats 获取实际错误计数

1.6 前置条件验证
    - ✓ SMART 状态验证（必须为正常）
    - ✓ 可用空间验证（必须≥10GB）
    - ✓ 温度验证（必须<70℃）
    - ✓ 剩余寿命验证（必须>90%）

Test Steps:
1. 使用 FIO 发起随机读测试
2. 配置参数：rw=randread, bs=4k, iodepth=32, numjobs=1, runtime=300, lat_percentiles=1
3. FIO 持续随机读取 300 秒（5 分钟）
4. 收集延迟统计数据（p50/p99/p99.9/p99.99）

Postcondition:
- 延迟统计数据已保存到 results/qos/目录
- 生成延迟分布报告
- 设备恢复到空闲状态（等待 5 秒）
- 数据清理：无测试数据残留
- 测试后器件状态检查：SMART、温度、错误计数

验收标准:
- p50 < 200 μs
- p99 < 1,000 μs
- p99.9 < 5,000 μs
- p99.99 < 10,000 μs (10ms)

注意事项:
- 延迟测试需要较长时间（300 秒）以确保统计准确性
- 系统负载会影响延迟结果，建议在空闲系统上测试
- p99.99 是关键指标，反映极端情况下的延迟表现
- 建议重复测试 3 次取平均值
"""

import sys
from pathlib import Path

from runner import TestRunner

sys.path.insert(0, str(Path(__file__).parent.parent / "core"))


def main():
    print("=" * 80)
    print("测试用例：t_qos_LatencyPercentile_001")
    print("延迟百分位测试")
    print("=" * 80)
    print()

    runner = TestRunner(
        device="/dev/ufs0", output_dir="./results/qos", verbose=True, check_precondition=True, mode="development"
    )

    print("开始执行测试...")
    print()

    result = runner.run_test("t_qos_LatencyPercentile_001")

    print()
    print("=" * 80)
    print("测试结果")
    print("=" * 80)

    status = result.get("status", "UNKNOWN")
    print("✅ PASS" if status == "PASS" else "❌ FAIL" if status == "FAIL" else f"状态：{status}")

    metrics = result.get("metrics", {})
    if metrics:
        print()
        print("延迟统计:")
        print(f"  - p50: {metrics.get('lat_p50', 0)} μs")
        print(f"  - p99: {metrics.get('lat_p99', 0)} μs")
        print(f"  - p99.9: {metrics.get('lat_p99_9', 0)} μs")
        print(f"  - p99.99: {metrics.get('lat_p99_99', 0)} μs")

    print()
    print("验收目标:")
    print("  - p50 < 200 μs")
    print("  - p99 < 1,000 μs")
    print("  - p99.9 < 5,000 μs")
    print("  - p99.99 < 10,000 μs")
    print()
    print("=" * 80)

    return 0 if status == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
