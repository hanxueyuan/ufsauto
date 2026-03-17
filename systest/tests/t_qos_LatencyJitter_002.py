#!/usr/bin/env python3
"""
测试用例：t_qos_LatencyJitter_002
延迟抖动测试

测试目的:
验证 UFS 设备的延迟抖动指标，评估设备延迟的稳定性，
确保延迟标准差<500μs，满足车规级系统对延迟稳定性的要求。

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
2. 配置参数：rw=randread, bs=4k, iodepth=16, numjobs=4, runtime=300, lat_percentiles=1
3. FIO 持续随机读取 300 秒（5 分钟），4 个并发线程
4. 收集延迟统计数据，计算标准差

Postcondition:
- 延迟统计数据已保存到 results/qos/目录
- 生成延迟抖动报告
- 设备恢复到空闲状态（等待 5 秒）
- 数据清理：无测试数据残留
- 测试后器件状态检查：SMART、温度、错误计数

验收标准:
- 延迟标准差 < 500 μs

注意事项:
- 4 个并发线程模拟多任务场景
- 延迟抖动反映设备稳定性，对实时系统至关重要
- 如果抖动超标，检查系统负载和 GC 干扰
- 建议重复测试 3 次取平均值
"""

import sys
from pathlib import Path

from runner import TestRunner

sys.path.insert(0, str(Path(__file__).parent.parent / "core"))


def main():
    print("=" * 80)
    print("测试用例：t_qos_LatencyJitter_002")
    print("延迟抖动测试")
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

    result = runner.run_test("t_qos_LatencyJitter_002")

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
        print(f"  - 平均延迟：{metrics.get('lat_avg', 0)} μs")
        print(f"  - 标准差：{metrics.get('lat_stddev', 0)} μs")

    print()
    print("验收目标:")
    print("  - 延迟标准差 < 500 μs")
    print()
    print("=" * 80)

    return 0 if status == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
