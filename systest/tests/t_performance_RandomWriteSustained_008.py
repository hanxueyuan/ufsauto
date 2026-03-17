#!/usr/bin/env python3
"""
测试用例：t_performance_RandomWriteSustained_008 ⭐
随机写 IOPS (Sustained) 测试

测试目的:
验证 UFS 设备的随机写 IOPS Sustained 性能，评估设备在长时间连续随机写入下的稳定 IOPS，
检测 SLC Cache 耗尽后的性能表现，确保满足车规级 UFS 3.1 的≥60 KIOPS 要求。

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
    - 可用空间：≥20GB（长时间测试需要更多空间）

1.3 存储设备配置检查
    - 开启功能：检查 TURBO Mode 状态（待实现自动检查）
    - 关闭功能：检查省电模式状态（待实现自动检查）

1.4 UFS 器件配置检查
    - LUN 数量：调用 _get_lun_count() 获取实际 LUN 数量
    - 

1.5 器件健康状况检查
    - SMART 状态：调用 smartctl -H 检查实际 SMART 状态
    - 剩余寿命：调用 smartctl -l smartctl 获取实际剩余寿命
    - 温度状态：读取/sys/class/hwmon/*/temp*_input 获取实际温度

1.6 前置条件验证
    - ✓ SMART 状态验证（必须为正常）
    - ✓ 可用空间验证（必须≥20GB）
    - ✓ 温度验证（必须<70℃）
    - ✓ 剩余寿命验证（必须>90%）

Test Steps:
1. 使用 FIO 工具发起随机写测试
2. 配置参数：rw=randwrite, bs=4k, iodepth=32, numjobs=1, runtime=300, time_based
3. FIO 持续随机写入 300 秒（5 分钟），记录 IOPS 数据
4. 收集测试结果，计算平均 IOPS

Postcondition:
- 测试结果保存到 results/performance/目录
- 配置恢复：无配置变更，无需恢复
- 设备恢复到空闲状态（等待 5 秒）
- 数据清理：删除测试生成的数据（执行 TRIM）

验收标准:
- PASS: 平均 IOPS ≥ 60 KIOPS（允许 5% 误差，即≥57 KIOPS）
- FAIL: 平均 IOPS < 57 KIOPS

注意事项:
- ⭐ Sustained 测试时间长（300 秒），可能触发 SLC Cache 耗尽
- 4K 块大小模拟随机写入场景
- 测试过程中密切监控 IOPS 变化曲线
- 如果性能衰减>80%，可能是 SLC Cache 耗尽（正常现象）
- 测试后建议执行 TRIM，恢复设备状态
- 建议重复测试 3 次取平均值
"""

import sys
from pathlib import Path

from runner import TestRunner

sys.path.insert(0, str(Path(__file__).parent.parent / "core"))


def main():
    print("=" * 80)
    print("测试用例：t_performance_RandomWriteSustained_008 ⭐")
    print("随机写 IOPS (Sustained) 测试")
    print("=" * 80)
    print()

    runner = TestRunner(
        device="/dev/ufs0",
        output_dir="./results/performance",
        verbose=True,
        check_precondition=True,
        mode="development"
    )

    print("开始执行测试...")
    print()

    result = runner.run_test("t_performance_RandomWriteSustained_008")

    print()
    print("=" * 80)
    print("测试结果")
    print("=" * 80)

    status = result.get("status", "UNKNOWN")
    print("✅ PASS" if status == "PASS" else "❌ FAIL" if status == "FAIL" else f"状态：{status}")

    if status == "PASS":
        print(f"✅ 随机写 IOPS (Sustained) 满足车规级要求 (≥60 KIOPS)")
    elif status == "FAIL":
        print(f"❌ 随机写 IOPS (Sustained) 未达到车规级要求 (<57 KIOPS)")
        print("\n建议检查:")
        print("1. 执行 TRIM 后重试")
        print("2. 检查 SLC Cache 状态")
        print("3. 监控 IOPS 变化曲线")
        print("4. 重复测试 3 次取平均值")

    print()
    print("=" * 80)

    return 0 if status == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
