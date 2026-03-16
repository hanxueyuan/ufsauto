#!/usr/bin/env python3
"""
测试用例：t_qos_LatencyJitter_002
延迟抖动测试

测试目的:
验证 UFS 设备的延迟抖动指标，评估设备延迟的稳定性，
确保延迟标准差<500μs，满足车规级系统对延迟稳定性的要求。



Test Steps:
1. 使用 FIO 发起随机读测试
2. 配置参数：rw=randread, bs=4k, iodepth=16, numjobs=4, runtime=300, lat_percentiles=1
3. FIO 持续随机读取 300 秒（5 分钟），4 个并发线程
4. 收集延迟统计数据，计算标准差

验收标准:
- 延迟标准差 < 500 μs

注意事项:
- 4 个并发线程模拟多任务场景
- 延迟抖动反映设备稳定性，对实时系统至关重要
- 如果抖动超标，检查系统负载和 GC 干扰
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "core"))

from runner import TestRunner


def main():
    print("=" * 80)
    print("测试用例：t_qos_LatencyJitter_002")
    print("延迟抖动测试")
    print("=" * 80)
    print()

    runner = TestRunner(
        device="/dev/ufs0", output_dir="./results/qos", verbose=True, check_precondition=True, mode="development"
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
        print("测试指标:")
        latency_stddev = metrics.get("latency_stddev", 0)
        if latency_stddev:
            print(f"  - 延迟标准差：{latency_stddev} μs")

    print()
    print("验收目标:")
    print("  - 延迟标准差 < 500 μs")
    print()
    print("=" * 80)

    return 0 if status == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
