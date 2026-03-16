#!/usr/bin/env python3
"""
测试用例：t_performance_MixedRw_009
混合读写性能测试

测试目的:
验证 UFS 设备在混合读写场景下的性能表现，模拟真实应用中读写并发的负载，
评估设备的综合 IOPS 性能，确保满足≥150 KIOPS 要求。



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
    - 特殊配置：无

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
    - ✓ 可用空间必须≥10GB
    - ✓ 温度必须<70℃
    - ✓ 剩余寿命必须>90%

Test Steps:
1. 使用 FIO 工具发起混合读写测试
2. 配置参数：rw=rw, rwmixread=70, bs=4k, iodepth=16, numjobs=1, runtime=60, time_based
3. FIO 持续混合读写 60 秒（70% 读，30% 写），记录 IOPS 数据
4. 收集测试结果，计算平均 IOPS

验收标准:
- PASS: 平均 IOPS ≥ 150 KIOPS（允许 5% 误差，即≥142.5 KIOPS）
- FAIL: 平均 IOPS < 142.5 KIOPS

注意事项:
- 混合读写模拟真实应用场景（70% 读，30% 写）
- 队列深度 16 适中，平衡性能和资源占用
- 测试前建议执行 TRIM，确保设备处于最佳状态
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / 'core'))

from runner import TestRunner


def main():
    print("=" * 80)
    print("测试用例：t_performance_MixedRw_009")
    print("混合读写性能测试")
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
    
    result = runner.run_test('t_performance_MixedRw_009')
    
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
    print("  - ≥ 150 KIOPS (容差：95%)")
    print("  - 即 ≥ 142.5 KIOPS")
    print()
    print("=" * 80)
    
    return 0 if status == 'PASS' else 1


if __name__ == '__main__':
    sys.exit(main())
