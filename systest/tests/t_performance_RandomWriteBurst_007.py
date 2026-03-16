#!/usr/bin/env python3
"""
测试用例：t_performance_RandomWriteBurst_007
随机写 IOPS (Burst) 测试

测试目的:
验证 UFS 设备的随机写 IOPS Burst 性能，评估设备在小文件随机写入场景下的峰值 IOPS，
确保满足车规级 UFS 3.1 的≥330 KIOPS 要求。



Test Steps:
1. 使用 FIO 工具发起随机写测试
2. 配置参数：rw=randwrite, bs=4k, iodepth=32, numjobs=1, runtime=60, time_based
3. FIO 持续随机写入 60 秒，记录 IOPS 数据
4. 收集测试结果，计算平均 IOPS

验收标准:
- PASS: 平均 IOPS ≥ 330 KIOPS（允许 5% 误差，即≥313.5 KIOPS）
- FAIL: 平均 IOPS < 313.5 KIOPS

注意事项:
- 4K 随机写模拟小文件写入场景
- 队列深度 32 充分利用 NCQ 并行性
- 测试前建议执行 TRIM，确保设备处于最佳状态
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / 'core'))

from runner import TestRunner


def main():
    print("=" * 80)
    print("测试用例：t_performance_RandomWriteBurst_007")
    print("随机写 IOPS (Burst) 测试")
    print("=" * 80)
    print()
    
    runner = TestRunner(
        device='/dev/ufs0',
        output_dir='./results/performance',
        verbose=True,
        check_precondition=True,
        mode='development'
    )
    
    print("开始执行测试...")
    print()
    
    result = runner.run_test('t_performance_RandomWriteBurst_007')
    
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
        iops = metrics.get('iops', 0)
        if iops:
            print(f"  - IOPS: {iops} K")
    
    print()
    print("验收目标:")
    print("  - ≥ 330 KIOPS (容差：95%)")
    print("  - 即 ≥ 313.5 KIOPS")
    print()
    print("=" * 80)
    
    return 0 if status == 'PASS' else 1


if __name__ == '__main__':
    sys.exit(main())
