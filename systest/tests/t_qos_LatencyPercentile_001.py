#!/usr/bin/env python3
"""
测试用例：t_qos_LatencyPercentile_001
延迟百分位测试

测试目的:
验证 UFS 设备的延迟百分位指标，评估设备在不同负载下的延迟表现，
确保 p99.99 延迟<10ms，满足车规级实时性要求。

Test Steps:
1. 使用 FIO 发起随机读测试
2. 配置参数：rw=randread, bs=4k, iodepth=32, numjobs=1, runtime=300, lat_percentiles=1
3. FIO 持续随机读取 300 秒（5 分钟）
4. 收集延迟统计数据（p50/p99/p99.9/p99.99）

验收标准:
- p50 < 200 μs
- p99 < 1,000 μs
- p99.9 < 5,000 μs
- p99.99 < 10,000 μs (10ms)

注意事项:
- 延迟测试需要较长时间（300 秒）以确保统计准确性
- 系统负载会影响延迟结果，建议在空闲系统上测试
- p99.99 是关键指标，反映极端情况下的延迟表现
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / 'core'))

from runner import TestRunner


def main():
    print("=" * 80)
    print("测试用例：t_qos_LatencyPercentile_001")
    print("延迟百分位测试")
    print("=" * 80)
    print()
    
    runner = TestRunner(
        device='/dev/ufs0',
        output_dir='./results/qos',
        verbose=True,
        check_precondition=True,
        mode='development'
    )
    
    print("开始执行测试...")
    print()
    
    result = runner.run_test('t_qos_LatencyPercentile_001')
    
    print()
    print("=" * 80)
    print("测试结果")
    print("=" * 80)
    
    status = result.get('status', 'UNKNOWN')
    print("✅ PASS" if status == 'PASS' else "❌ FAIL" if status == 'FAIL' else f"状态：{status}")
    
    metrics = result.get('metrics', {})
    if metrics:
        print()
        print("测试指标:")
        latency_p50 = metrics.get('latency_p50', 0)
        latency_p99 = metrics.get('latency_p99', 0)
        latency_p99999 = metrics.get('latency_p99999', 0)
        if latency_p50:
            print(f"  - p50: {latency_p50} μs")
        if latency_p99:
            print(f"  - p99: {latency_p99} μs")
        if latency_p99999:
            print(f"  - p99.99: {latency_p99999} μs")
    
    print()
    print("验收目标:")
    print("  - p50 < 200 μs")
    print("  - p99 < 1,000 μs")
    print("  - p99.9 < 5,000 μs")
    print("  - p99.99 < 10,000 μs (10ms)")
    print()
    print("=" * 80)
    
    return 0 if status == 'PASS' else 1


if __name__ == '__main__':
    sys.exit(main())
