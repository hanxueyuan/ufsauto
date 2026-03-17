#!/usr/bin/env python3
"""
测试用例：t_performance_RandomWriteBurst_007
随机写 IOPS (Burst) 测试

测试目的:
验证 UFS 设备的随机写 IOPS Burst 性能，评估设备在短时间内能达到的最大随机写入 IOPS，
确保满足车规级 UFS 3.1 的≥280 KIOPS 要求。

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

1.4 UFS 器件配置检查
    - LUN 数量：调用 _get_lun_count() 获取实际 LUN 数量
    - 

1.5 器件健康状况检查
    - SMART 状态：调用 smartctl -H 检查实际 SMART 状态
    - 剩余寿命：调用 smartctl -l smartctl 获取实际剩余寿命
    - 温度状态：读取/sys/class/hwmon/*/temp*_input 获取实际温度

1.6 前置条件验证
    - ✓ SMART 状态验证（必须为正常）
    - ✓ 可用空间验证（必须≥10GB）
    - ✓ 温度验证（必须<70℃）
    - ✓ 剩余寿命验证（必须>90%）

Test Steps:
1. 使用 FIO 工具发起随机写测试
2. 配置参数：rw=randwrite, bs=4k, iodepth=32, numjobs=1, runtime=60, time_based
3. FIO 持续随机写入 60 秒，记录 IOPS 数据
4. 收集测试结果，计算平均 IOPS

Postcondition:
- 测试结果保存到 results/performance/目录
- 配置恢复：无配置变更，无需恢复
- 设备恢复到空闲状态（等待 5 秒）
- 数据清理：删除测试生成的数据（执行 TRIM）

验收标准:
- PASS: 平均 IOPS ≥ 280 KIOPS（允许 5% 误差，即≥266 KIOPS）
- FAIL: 平均 IOPS < 266 KIOPS

注意事项:
- Burst 测试时间短（60 秒），反映设备峰值写入性能
- 4K 块大小模拟随机写入场景
- 测试前建议执行 TRIM，确保设备处于最佳状态
- 如果测试失败，检查 SLC Cache 状态
- 建议重复测试 3 次取平均值
"""

import sys
from pathlib import Path

from runner import TestRunner

sys.path.insert(0, str(Path(__file__).parent.parent / "core"))


def main():
    print("=" * 80)
    print("测试用例：t_performance_RandomWriteBurst_007")
    print("随机写 IOPS (Burst) 测试")
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

    result = runner.run_test("t_performance_RandomWriteBurst_007")

    print()
    print("=" * 80)
    print("测试结果")
    print("=" * 80)

    status = result.get("status", "UNKNOWN")
    print("✅ PASS" if status == "PASS" else "❌ FAIL" if status == "FAIL" else f"状态：{status}")

    if status == "PASS":
        print(f"✅ 随机写 IOPS (Burst) 满足车规级要求 (≥280 KIOPS)")
    elif status == "FAIL":
        print(f"❌ 随机写 IOPS (Burst) 未达到车规级要求 (<266 KIOPS)")
        print("\n建议检查:")
        print("1. 执行 TRIM 后重试")
        print("2. 检查 SLC Cache 状态")
        print("3. 重复测试 3 次取平均值")

    print()
    print("=" * 80)

    return 0 if status == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
