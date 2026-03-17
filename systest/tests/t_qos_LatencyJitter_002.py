#!/usr/bin/env python3
"""
测试用例：t_qos_LatencyJitter_002
延迟抖动测试

测试目的:
验证 UFS 设备的延迟抖动指标，评估设备延迟的稳定性，
确保延迟标准差<500μs，满足车规级系统对延迟稳定性的要求。

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
    - 开启功能：检查 TURBO Mode 状态（待实现自动检查）
    - 关闭功能：检查省电模式状态（待实现自动检查）
    - 特殊配置：检查并记录特殊配置

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
