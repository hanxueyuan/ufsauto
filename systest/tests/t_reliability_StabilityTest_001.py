#!/usr/bin/env python3
"""
测试用例：t_reliability_StabilityTest_001
长期稳定性测试 ⭐ 最关键测试

测试目的:
验证 UFS 设备在长时间（24 小时）连续工作下的稳定性，
确保无数据错误、无性能衰减、无设备故障，满足车规级可靠性要求。

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
    - 可用空间：≥20GB（长时间测试需要更多空间）

1.3 存储设备配置检查
    - 开启功能：无特殊开启
    - 关闭功能：自动休眠（避免影响长时间测试）
    - 特殊配置：IO 调度器设置为 none（减少调度延迟）

1.4 UFS 器件配置检查
    - LUN 数量：4 个
    - LUN0：64GB 系统盘（已挂载）
    - LUN1：32GB 数据盘（测试目标）
    - LUN2：16GB 日志盘
    - LUN3：16GB 预留
    - LUN 映射：LUN1→/dev/ufs0

1.5 器件健康状况检查
    - SMART 状态：正常
    - 剩余寿命：98%
    - 坏块数量：0
    - 温度状态：35℃（当前）/ 45℃（最高）
    - 错误计数：CRC 错误=0, 重传次数=0

1.6 前置条件验证
    - ✓ SMART 状态必须为正常
    - ✓ 可用空间必须≥20GB
    - ✓ 温度必须<70℃
    - ✓ 剩余寿命必须>90%

Test Steps:
1. 启动 24 小时稳定性测试
2. 配置参数：rw=randrw, rwmixread=70, bs=4k, iodepth=32, numjobs=2, runtime=86400, verify=0
3. 每 5 分钟记录一次性能数据（带宽/IOPS/延迟/温度）
4. 监控错误计数（CRC 错误/重传次数/IO 错误）
5. 24 小时后停止测试，分析数据

验收标准:
- 无 IO 错误（错误计数=0）
- 性能衰减 < 20%（初始带宽 vs 最终带宽）
- 设备温度 < 70℃（全程）
- 无设备掉线或重启

注意事项:
- 24 小时测试时间长，确保电源稳定
- 测试前备份重要数据（虽然不会破坏数据）
- 建议定期检查设备温度
- 如温度超过 70℃，暂停测试并改善散热
- 测试过程中不要中断，否则需要重新开始
"""

from runner import TestRunner
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "core"))


def main():
    print("=" * 80)
    print("测试用例：t_reliability_StabilityTest_001")
    print("长期稳定性测试 ⭐ 最关键测试")
    print("=" * 80)
    print()
    print("⚠️  警告：此测试将运行 24 小时！")
    print()

    runner = TestRunner(
        device="/dev/ufs0", output_dir="./results/reliability", verbose=True, check_precondition=True, mode="development"
    )

    print("开始执行测试...")
    print()

    result = runner.run_test("t_reliability_StabilityTest_001")

    print()
    print("=" * 80)
    print("测试结果")
    print("=" * 80)

    status = result.get("status", "UNKNOWN")
    print("✅ PASS" if status == "PASS" else "❌ FAIL" if status == "FAIL" else f"状态：{status}")

    print()
    print("验收目标:")
    print("  - 无 IO 错误（错误计数=0）")
    print("  - 性能衰减 < 20%（初始带宽 vs 最终带宽）")
    print("  - 设备温度 < 70℃（全程）")
    print("  - 无设备掉线或重启")
    print()
    print("=" * 80)

    return 0 if status == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
