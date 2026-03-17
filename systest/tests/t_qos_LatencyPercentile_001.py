#!/usr/bin/env python3
"""
测试用例：t_qos_LatencyPercentile_001
延迟百分位测试

测试目的:
验证 UFS 设备的延迟百分位指标，评估设备在不同负载下的延迟表现，
确保 p99.99 延迟<10ms，满足车规级实时性要求。

Precondition:
1.1 系统环境收集
    - 操作系统：Debian 12, kernel 5.15.120
    - CPU/内存：8 核，16GB
    - FIO 版本：fio-3.33

1.2 测试目标信息收集
    - 设备路径：/dev/ufs0
    - 设备型号：UFS 3.1 128GB
    - 固件版本：v1.0.0
    - 设备容量：128GB
    - 可用空间：≥10GB

1.3 存储设备配置检查
    - 开启功能：TURBO Mode
    - 关闭功能：省电模式
    - 特殊配置：无

1.4 UFS 器件配置检查
    - LUN 数量：4 个
    - LUN 映射：LUN1→/dev/ufs0

1.5 器件健康状况检查
    - SMART 状态：正常
    - 剩余寿命：98%
    - 温度状态：35℃（当前）/ 45℃（最高）
    - 错误计数：CRC 错误=0, 重传次数=0

1.6 前置条件验证
    - ✓ SMART 状态必须为正常
    - ✓ 可用空间必须≥10GB
    - ✓ 温度必须<70℃
    - ✓ 剩余寿命必须>90%

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
        device="/dev/ufs0",
        output_dir="./results/qos",
        verbose=True,
        check_precondition=True,
        mode="development"
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
