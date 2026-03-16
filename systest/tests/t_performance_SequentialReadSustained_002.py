#!/usr/bin/env python3
"""
测试用例：t_performance_SequentialReadSustained_002
顺序读带宽 (Sustained) 测试

测试目的:
验证 UFS 设备的顺序读带宽 Sustained 性能，评估设备在长时间连续读取下的稳定带宽，
确保满足车规级 UFS 3.1 的≥1800 MB/s 要求。

Precondition:
- 系统环境：Debian 12, kernel 5.15.120, 8 核，16GB, fio-3.33
- 设备信息：/dev/ufs0, UFS 3.1 128GB, v1.0.0, ≥10GB 可用空间
- 存储配置：开启 TURBO Mode, 关闭省电模式
- LUN 配置：4 个 LUN, LUN1→/dev/ufs0
- 健康状况：SMART 正常，寿命>90%, 温度<70℃, 无错误

Test Steps:
1. 使用 FIO 工具发起顺序读测试
2. 配置参数：rw=read, bs=128k, iodepth=32, numjobs=1, runtime=300, time_based
3. FIO 持续读取 300 秒（5 分钟），记录带宽数据
4. 收集测试结果，计算平均带宽

Postcondition:
- 测试结果保存到 results/performance/目录
- 设备恢复到空闲状态（等待 5 秒）

验收标准:
- PASS: 平均带宽 ≥ 1800 MB/s（允许 5% 误差，即≥1710 MB/s）
- FAIL: 平均带宽 < 1710 MB/s

注意事项:
- Sustained 测试时间长（300 秒），反映设备持续性能
- 测试过程中监控设备温度，防止过热降频
- 如果性能衰减>20%，检查 SLC Cache 是否耗尽
- 建议重复测试 3 次取平均值
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / 'core'))

from runner import TestRunner


def main():
    """执行测试用例"""
    print("=" * 80)
    print("测试用例：t_performance_SequentialReadSustained_002")
    print("顺序读带宽 (Sustained) 测试")
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
    
    result = runner.run_test('t_performance_SequentialReadSustained_002')
    
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
        bandwidth = metrics.get('bandwidth', 0)
        if bandwidth:
            print(f"  - 带宽：{bandwidth} MB/s")
    
    print()
    print("验收目标:")
    print("  - ≥ 1800 MB/s (容差：95%)")
    print("  - 即 ≥ 1710 MB/s")
    print()
    print("=" * 80)
    
    return 0 if status == 'PASS' else 1


if __name__ == '__main__':
    sys.exit(main())
