#!/usr/bin/env python3
"""
测试用例：t_performance_SequentialReadBurst_001
顺序读带宽 (Burst) 测试

测试目的:
验证 UFS 设备的顺序读带宽 Burst 性能，评估设备在短时间内能达到的最大读取带宽，
确保满足车规级 UFS 3.1 的≥2100 MB/s 要求。

Precondition:
1.1 系统环境收集
    - 操作系统：收集并记录实际 OS 信息（/etc/os-release）
    - CPU/内存：收集并记录实际 CPU/内存配置（/proc/cpuinfo, /proc/meminfo）
    - FIO 版本：调用 fio --version 获取实际版本

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
    - LUN 配置：读取并记录各 LUN 容量和用途
    - LUN 映射：验证 LUN 与/dev/ufs0 映射关系（待实现）
    - 
    - 
    - 

1.5 器件健康状况检查
    - SMART 状态：调用 smartctl -H 检查实际 SMART 状态
    - 剩余寿命：调用 smartctl -l smartctl 获取实际剩余寿命
    - 坏块数量：读取并记录实际坏块数量
    - 温度状态：读取/sys/class/hwmon/*/temp*_input 获取实际温度
    - 错误计数：读取/sys/block/<device>/device/stats 获取实际错误计数

1.6 前置条件验证
    - ✓ SMART 状态验证（必须为正常）
    - ✓ 可用空间验证（必须≥10GB）
    - ✓ 温度验证（必须<70℃）
    - ✓ 剩余寿命验证（必须>90%）

Test Steps:
1. 使用 FIO 工具发起顺序读测试
2. 配置参数：rw=read, bs=128k, iodepth=32, numjobs=1, runtime=60, time_based
3. FIO 持续读取 60 秒，记录带宽数据
4. 收集测试结果，计算平均带宽

Postcondition:
- 测试结果保存到 results/performance/目录
- 配置恢复：无配置变更，无需恢复
- 设备恢复到空闲状态（等待 5 秒）
- 数据清理：无测试数据残留

验收标准:
- PASS: 平均带宽 ≥ 2100 MB/s（允许 5% 误差，即≥1995 MB/s）
- FAIL: 平均带宽 < 1995 MB/s

注意事项:
- Burst 测试时间短（60 秒），反映设备峰值性能
- 测试前确保设备未处于过热状态
- 如果测试失败，检查设备温度、队列深度配置
- 建议重复测试 3 次取平均值
"""

import os
import sys
from pathlib import Path

from runner import TestRunner

# 添加 core 模块路径
sys.path.insert(0, str(Path(__file__).parent.parent / "core"))


def main():
    """执行测试用例"""
    print("=" * 80)
    print("测试用例：t_performance_SequentialReadBurst_001")
    print("顺序读带宽 (Burst) 测试")
    print("=" * 80)
    print()

    # 创建 TestRunner
    runner = TestRunner(
        device="/dev/ufs0",
        output_dir="./results/performance",
        verbose=True,
        check_precondition=True,
        mode="development",  # 开发模式：只记录问题，不阻止测试
    )

    # 执行测试
    print("开始执行测试...")
    print()

    result = runner.run_test("t_performance_SequentialReadBurst_001")

    # 显示结果
    print()
    print("=" * 80)
    print("测试结果")
    print("=" * 80)

    status = result.get("status", "UNKNOWN")
    if status == "PASS":
        print("✅ PASS")
    elif status == "FAIL":
        print("❌ FAIL")
    elif status == "SKIPPED":
        print("⚠️  SKIPPED")
        reason = result.get("reason", "未知原因")
        print(f"原因：{reason}")
    else:
        print(f"状态：{status}")

    # 显示指标
    metrics = result.get("metrics", {})
    if metrics:
        print()
        print("测试指标:")
        bandwidth = metrics.get("bandwidth", 0)
        if bandwidth:
            print(f"  - 带宽：{bandwidth} MB/s")

        iops = metrics.get("iops", 0)
        if iops:
            print(f"  - IOPS: {iops} K")

        latency = metrics.get("latency_avg", 0)
        if latency:
            print(f"  - 平均延迟：{latency} μs")

    # 显示验收目标
    print()
    print("验收目标:")
    print("  - ≥ 2100 MB/s (容差：95%)")
    print("  - 即 ≥ 1995 MB/s")

    print()
    print("=" * 80)

    # 返回结果
    return 0 if status == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
