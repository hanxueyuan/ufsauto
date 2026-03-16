#!/usr/bin/env python3
"""
测试用例：t_scenario_SensorWrite_001
传感器数据写入测试

测试目的:
模拟智驾系统传感器数据持续写入场景，验证 UFS 设备在多路传感器并发写入时的性能表现，
确保满足≥400 MB/s 的持续写入带宽要求。



Test Steps:
1. 模拟 8 路摄像头传感器并发写入
2. 配置参数：rw=write, bs=64k, iodepth=8, numjobs=8, rate=50M, runtime=300
3. 8 个线程并发写入 300 秒（5 分钟）
4. 监控总写入带宽
5. 检查是否有丢包或写入失败

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
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "core"))

from runner import TestRunner


def main():
    print("=" * 80)
    print("测试用例：t_scenario_SensorWrite_001")
    print("传感器数据写入测试")
    print("=" * 80)
    print()

    runner = TestRunner(
        device="/dev/ufs0", output_dir="./results/scenario", verbose=True, check_precondition=True, mode="development"
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
    print("  - 总写入带宽 ≥ 400 MB/s（8 × 50MB/s）")
    print("  - 丢包率 = 0%")
    print("  - 延迟 p99 < 1,000 μs")
    print("  - 无写入错误")
    print()
    print("=" * 80)

    return 0 if status == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
