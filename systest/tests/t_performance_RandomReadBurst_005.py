#!/usr/bin/env python3
"""
测试用例：t_performance_RandomReadBurst_005
随机读 IOPS (Burst) 测试

测试目的:
验证 UFS 设备的随机读 IOPS Burst 性能，评估设备在短时间内能达到的最大随机读取 IOPS，
确保满足车规级 UFS 3.1 的≥330 KIOPS 要求。

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
    - 开启功能：TURBO Mode（提升峰值性能）
    - 关闭功能：省电模式（避免性能限制）

1.4 UFS 器件配置检查
    - LUN 数量：4 个
    - LUN 映射：LUN1→/dev/ufs0

1.5 器件健康状况检查
    - SMART 状态：正常
    - 剩余寿命：98%
    - 温度状态：35℃（当前）/ 45℃（最高）

1.6 前置条件验证
    - ✓ SMART 状态必须为正常
    - ✓ 可用空间必须≥10GB
    - ✓ 温度必须<70℃
    - ✓ 剩余寿命必须>90%

Test Steps:
1. 使用 FIO 工具发起随机读测试
2. 配置参数：rw=randread, bs=4k, iodepth=32, numjobs=1, runtime=60, time_based
3. FIO 持续随机读取 60 秒，记录 IOPS 数据
4. 收集测试结果，计算平均 IOPS

Postcondition:
- 测试结果保存到 results/performance/目录
- 配置恢复：无配置变更，无需恢复
- 设备恢复到空闲状态（等待 5 秒）
- 数据清理：无测试数据残留

验收标准:
- PASS: 平均 IOPS ≥ 330 KIOPS（允许 5% 误差，即≥313.5 KIOPS）
- FAIL: 平均 IOPS < 313.5 KIOPS

注意事项:
- Burst 测试时间短（60 秒），反映设备峰值性能
- 4K 块大小模拟随机读取场景
- 测试前确保设备未处于过热状态
- 建议重复测试 3 次取平均值
"""

import sys
from pathlib import Path

from runner import TestRunner

# 添加 core 模块路径
sys.path.insert(0, str(Path(__file__).parent.parent / "core"))


def main():
    print("=" * 80)
    print("测试用例：t_performance_RandomReadBurst_005")
    print("随机读 IOPS (Burst) 测试")
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

    result = runner.run_test("t_performance_RandomReadBurst_005")

    print()
    print("=" * 80)
    print("测试结果")
    print("=" * 80)

    status = result.get("status", "UNKNOWN")
    print("✅ PASS" if status == "PASS" else "❌ FAIL" if status == "FAIL" else f"状态：{status}")

    if status == "PASS":
        print(f"✅ 随机读 IOPS (Burst) 满足车规级要求 (≥330 KIOPS)")
    elif status == "FAIL":
        print(f"❌ 随机读 IOPS (Burst) 未达到车规级要求 (<313.5 KIOPS)")
        print("\n建议检查:")
        print("1. 设备温度是否正常")
        print("2. 队列深度配置是否合理")
        print("3. 重复测试 3 次取平均值")

    print()
    print("=" * 80)

    return 0 if status == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
