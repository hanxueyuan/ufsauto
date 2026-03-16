#!/usr/bin/env python3
"""
测试用例：t_performance_SequentialWriteSustained_004
顺序写带宽 (Sustained) 测试

测试目的:
验证 UFS 设备的顺序写带宽 Sustained 性能，评估设备在长时间连续写入下的稳定带宽，
检测 SLC Cache 耗尽后的性能表现，确保满足车规级 UFS 3.1 的≥250 MB/s 要求。



Test Steps:
1. 使用 FIO 工具发起顺序写测试
2. 配置参数：rw=write, bs=128k, iodepth=32, numjobs=1, runtime=300, time_based
3. FIO 持续写入 300 秒（5 分钟），记录带宽数据
4. 收集测试结果，计算平均带宽，观察性能衰减曲线

验收标准:
- PASS: 平均带宽 ≥ 250 MB/s（允许 5% 误差，即≥237.5 MB/s）
- FAIL: 平均带宽 < 237.5 MB/s

注意事项:
- Sustained 测试时间长（300 秒），可能触发 SLC Cache 耗尽
- 测试过程中密切监控带宽变化曲线
- 如果性能衰减>80%，可能是 SLC Cache 耗尽（正常现象）
- 测试后建议执行 TRIM，恢复设备状态
"""

import sys
from pathlib import Path

from runner import TestRunner

sys.path.insert(0, str(Path(__file__).parent.parent / "core"))


def main():
    print("=" * 80)
    print("测试用例：t_performance_SequentialWriteSustained_004")
    print("顺序写带宽 (Sustained) 测试 ⭐ 关键测试")
    print("=" * 80)
    print()

    runner = TestRunner(
        device="/dev/ufs0", output_dir="./results/performance", verbose=True, check_precondition=True, mode="development"
    )

    print("开始执行测试...")
    print()

    result = runner.run_test("t_performance_SequentialWriteSustained_004")

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
            print(f"  - 带宽：{bandwidth} MB/s")

    print()
    print("验收目标:")
    print("  - ≥ 250 MB/s (容差：95%)")
    print("  - 即 ≥ 237.5 MB/s")
    print()
    print("=" * 80)

    return 0 if status == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
