#!/usr/bin/env python3
"""
测试用例：t_scenario_SensorWrite_001
传感器数据写入测试

测试目的:
模拟智驾系统传感器数据持续写入场景，验证 UFS 设备在多路传感器并发写入时的性能表现，
确保满足≥400 MB/s 的持续写入带宽要求。



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
    - 可用空间：≥5GB

1.3 存储设备配置检查
    - 开启功能：无特殊开启
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
    - ✓ 可用空间必须≥5GB
    - ✓ 温度必须<70℃
    - ✓ 剩余寿命必须>90%

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

sys.path.insert(0, str(Path(__file__).parent.parent / 'core'))

from runner import TestRunner


def main():
    print("=" * 80)
    print("测试用例：t_scenario_SensorWrite_001")
    print("传感器数据写入测试")
    print("=" * 80)
    print()
    
    runner = TestRunner(
        device='/dev/ufs0',
        output_dir='./results/scenario',
        verbose=True,
        check_precondition=True,
        mode='development'
    )
    
    print("开始执行测试...")
    print()
    
    result = runner.run_test('t_scenario_SensorWrite_001')
    
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
            print(f"  - 总写入带宽：{bandwidth} MB/s")
    
    print()
    print("验收目标:")
    print("  - 总写入带宽 ≥ 400 MB/s（8 × 50MB/s）")
    print("  - 丢包率 = 0%")
    print("  - 延迟 p99 < 1,000 μs")
    print("  - 无写入错误")
    print()
    print("=" * 80)
    
    return 0 if status == 'PASS' else 1


if __name__ == '__main__':
    sys.exit(main())
