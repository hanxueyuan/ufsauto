#!/usr/bin/env python3
"""
测试用例：t_performance_RandomReadSustained_006
随机读 IOPS (Sustained) 测试

测试目的:
验证 UFS 设备的随机读 IOPS Sustained 性能，评估设备在长时间小文件随机读取下的稳定 IOPS，
确保满足车规级 UFS 3.1 的≥105 KIOPS 要求。



Test Steps:
1. 使用 FIO 工具发起随机读测试
2. 配置参数：rw=randread, bs=4k, iodepth=32, numjobs=1, runtime=300, time_based
3. FIO 持续随机读取 300 秒（5 分钟），记录 IOPS 数据
4. 收集测试结果，计算平均 IOPS

验收标准:
- PASS: 平均 IOPS ≥ 105 KIOPS（允许 5% 误差，即≥99.75 KIOPS）
- FAIL: 平均 IOPS < 99.75 KIOPS

注意事项:
- Sustained 测试时间长（300 秒），反映持续随机读性能
- 测试过程中监控 IOPS 稳定性
- 如果性能衰减>20%，检查设备温度
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "core"))

from runner import TestRunner


def main():
    print("=" * 80)
    print("测试用例：t_performance_RandomReadSustained_006")
    print("随机读 IOPS (Sustained) 测试")
    print("=" * 80)
    print()

    runner = TestRunner(
        device="/dev/ufs0", output_dir="./results/performance", verbose=True, check_precondition=True, mode="development"
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

    metrics = result.get("metrics", {})
    if metrics:
        print()
        print("测试指标:")
        iops = metrics.get("iops", 0)
        if iops:
            print(f"  - IOPS: {iops} K")

    print()
    print("验收目标:")
    print("  - ≥ 105 KIOPS (容差：95%)")
    print("  - 即 ≥ 99.75 KIOPS")
    print()
    print("=" * 80)

    return 0 if status == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
