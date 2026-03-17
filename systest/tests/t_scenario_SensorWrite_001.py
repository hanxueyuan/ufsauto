#!/usr/bin/env python3
"""
测试用例：t_scenario_SensorWrite_001
传感器数据写入测试

测试目的:
模拟智驾系统传感器数据持续写入场景，验证 UFS 设备在多路传感器并发写入时的性能表现，
确保满足≥400 MB/s 的持续写入带宽要求。

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
    - 可用空间：≥5GB

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
    - ✓ 可用空间验证（必须≥5GB）
    - ✓ 温度验证（必须<70℃）
    - ✓ 剩余寿命验证（必须>90%）

Test Steps:
1. 模拟 8 路摄像头传感器并发写入
2. 配置参数：rw=write, bs=64k, iodepth=8, numjobs=8, rate=50M, runtime=300
3. 8 个线程并发写入 300 秒（5 分钟）
4. 监控总写入带宽
5. 检查是否有丢包或写入失败

Postcondition:
- 记录总写入带宽
- 检查丢包率（应为 0%）
- 生成场景测试报告
- 清理测试数据
- 设备恢复到空闲状态（等待 5 秒）
- 测试后器件状态检查：SMART、温度、错误计数

验收标准:
- 总写入带宽 ≥ 400 MB/s（8 × 50MB/s）
- 丢包率 = 0%
- 延迟 p99 < 1,000 μs
- 无写入错误

注意事项:
- 模拟真实智驾场景，8 路传感器并发
- 每路传感器 50MB/s，总计 400MB/s
- 限速是为了模拟真实传感器，不是测试峰值性能
- 如果带宽不足，检查 CPU 负载和 IO 调度策略
- 建议重复测试 3 次取平均值
"""

import sys
from pathlib import Path

from runner import TestRunner

sys.path.insert(0, str(Path(__file__).parent.parent / "core"))


def main():
    print("=" * 80)
    print("测试用例：t_scenario_SensorWrite_001")
    print("传感器数据写入测试")
    print("=" * 80)
    print()

    runner = TestRunner(
        device="/dev/ufs0",
        output_dir="./results/scenario",
        verbose=True,
        check_precondition=True,
        mode="development"
    )

    print("开始执行测试...")
    print()

    result = runner.run_test("t_scenario_SensorWrite_001")

    print()
    print("=" * 80)
    print("测试结果")
    print("=" * 80)

    status = result.get("status", "UNKNOWN")
    print("✅ PASS" if status == "PASS" else "❌ FAIL" if status == "FAIL" else f"状态：{status}")

    metrics = result.get("metrics", {})
    if metrics:
        print()
        print("测试指标:")
        bandwidth = metrics.get("bandwidth", 0)
        if bandwidth:
            print(f"  - 总写入带宽：{bandwidth} MB/s")

    print()
    print("验收目标:")
    print("  - 总写入带宽 ≥ 400 MB/s")
    print("  - 丢包率 = 0%")
    print()
    print("=" * 80)

    return 0 if status == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
