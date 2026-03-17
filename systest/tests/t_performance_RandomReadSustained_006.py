#!/usr/bin/env python3
"""
测试用例：t_performance_RandomReadSustained_006
随机读 IOPS (Sustained) 测试

测试目的:
验证 UFS 设备的随机读 IOPS Sustained 性能，评估设备在长时间连续随机读取下的稳定 IOPS，
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
1. 使用 FIO 工具发起随机读测试
2. 配置参数：rw=randread, bs=4k, iodepth=32, numjobs=1, runtime=300, time_based
3. FIO 持续随机读取 300 秒（5 分钟），记录 IOPS 数据
4. 收集测试结果，计算平均 IOPS

Postcondition:
- 测试结果保存到 results/performance/目录
- 设备恢复到空闲状态（等待 5 秒）
- 数据清理：无测试数据残留

验收标准:
- PASS: 平均 IOPS ≥ 280 KIOPS（允许 5% 误差，即≥266 KIOPS）
- FAIL: 平均 IOPS < 266 KIOPS

注意事项:
- Sustained 测试时间长（300 秒），反映设备持续性能
- 4K 块大小模拟随机读取场景
- 测试过程中监控设备温度，防止过热降频
- 如果性能衰减>20%，检查设备散热
- 建议重复测试 3 次取平均值
"""

import sys
from pathlib import Path

from runner import TestRunner

sys.path.insert(0, str(Path(__file__).parent.parent / "core"))


def main():
    print("=" * 80)
    print("测试用例：t_performance_RandomReadSustained_006")
    print("随机读 IOPS (Sustained) 测试")
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

    result = runner.run_test("t_performance_RandomReadSustained_006")

    print()
    print("=" * 80)
    print("测试结果")
    print("=" * 80)

    status = result.get("status", "UNKNOWN")
    print("✅ PASS" if status == "PASS" else "❌ FAIL" if status == "FAIL" else f"状态：{status}")

    if status == "PASS":
        print(f"✅ 随机读 IOPS (Sustained) 满足车规级要求 (≥280 KIOPS)")
    elif status == "FAIL":
        print(f"❌ 随机读 IOPS (Sustained) 未达到车规级要求 (<266 KIOPS)")
        print("\n建议检查:")
        print("1. 设备温度是否正常")
        print("2. 重复测试 3 次取平均值")

    print()
    print("=" * 80)

    return 0 if status == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
