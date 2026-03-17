#!/usr/bin/env python3
"""
测试用例：t_reliability_StabilityTest_001 ⭐
长期稳定性测试 - 最关键测试

测试目的:
验证 UFS 设备在长时间（24 小时）连续工作下的稳定性，
确保无数据错误、无性能衰减、无设备故障，满足车规级可靠性要求。

Precondition:
1.1 系统环境收集
    - 操作系统：读取 /etc/os-release，收集 PRETTY_NAME 字段
    - CPU/内存：收集并记录实际 CPU/内存配置（/proc/cpuinfo, /proc/meminfo）
    - FIO 版本：执行 fio --version，收集版本号

1.2 测试目标信息收集
    - 设备路径：检查/dev/ufs0 是否存在
    - 设备型号：读取并记录实际设备型号
    - 固件版本：读取并记录实际固件版本
    - 设备容量：读取并记录实际设备容量
    - 可用空间：≥20GB（长时间测试需要更多空间）

1.3 存储设备配置检查
    - 开启功能：无特殊开启
    - 关闭功能：自动休眠（避免影响长时间测试）
    - 特殊配置：IO 调度器设置为 none（减少调度延迟）

1.4 UFS 器件配置检查
    - LUN 数量：调用 _get_lun_count() 获取实际 LUN 数量
    - LUN 配置：读取并记录各 LUN 容量和用途
    - LUN 映射：验证 LUN 与/dev/ufs0 映射关系（待实现）
    - 
    - 
    - 

1.5 器件健康状况检查
    - SMART 状态：调用 smartctl -H 检查实际 SMART 状态
    - 剩余寿命：调用 smartctl -l smartctl 获取实际剩余寿命
    - 坏块数量：读取并记录实际坏块数量
    - 温度状态：读取/sys/class/hwmon/*/temp*_input 获取实际温度
    - 错误计数：读取/sys/block/<device>/device/stats 获取实际错误计数

1.6 前置条件验证
    - ✓ SMART 状态验证（必须为正常）
    - ✓ 可用空间验证（必须≥20GB）
    - ✓ 温度验证（必须<70℃）
    - ✓ 剩余寿命验证（必须>90%）
    - ✓ 电源必须稳定
    - ✓ 散热必须良好

Test Steps:
1. 启动 24 小时稳定性测试
2. 配置参数：rw=randrw, rwmixread=70, bs=4k, iodepth=32, numjobs=2, runtime=86400, verify=0
3. 每 5 分钟记录一次性能数据（带宽/IOPS/延迟/温度）
4. 监控错误计数（CRC 错误/重传次数/IO 错误）
5. 24 小时后停止测试，分析数据

Postcondition:
- 测试结果保存到 results/reliability/目录
- 配置恢复：恢复自动休眠功能，恢复 IO 调度器为默认值（如 mq-deadline）
- 设备恢复到空闲状态（等待 10 秒）
- 数据清理：删除测试生成的临时文件
- 测试后器件状态检查：
  - SMART 状态对比（测试前 vs 测试后）
  - 剩余寿命变化
  - 温度变化曲线
  - 错误计数变化（CRC 错误/重传次数）
  - 性能衰减分析（初始带宽 vs 最终带宽）

验收标准:
- 无 IO 错误（错误计数=0）
- 性能衰减 < 20%（初始带宽 vs 最终带宽）
- 设备温度 < 70℃（全程）
- 无设备掉线或重启
- SMART 状态保持正常
- 剩余寿命衰减 < 1%

注意事项:
- ⭐ 24 小时测试时间长，确保电源稳定
- 测试前备份重要数据（虽然不会破坏数据）
- 建议定期检查设备温度
- 如温度超过 70℃，暂停测试并改善散热
- 测试过程中不要中断，否则需要重新开始
- 建议在非工作时间运行此测试
- 测试后必须执行配置恢复和状态检查
"""

import sys
from pathlib import Path

from runner import TestRunner

sys.path.insert(0, str(Path(__file__).parent.parent / "core"))


def main():
    print("=" * 80)
    print("测试用例：t_reliability_StabilityTest_001 ⭐")
    print("长期稳定性测试 - 最关键测试")
    print("=" * 80)
    print()
    print("⚠️  警告：此测试将运行 24 小时！")
    print()

    runner = TestRunner(
        device="/dev/ufs0",
        output_dir="./results/reliability",
        verbose=True,
        check_precondition=True,
        mode="development"
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

    metrics = result.get("metrics", {})
    if metrics:
        print()
        print("24 小时测试统计:")
        print(f"  - 初始带宽：{metrics.get('initial_bandwidth', 0)} MB/s")
        print(f"  - 最终带宽：{metrics.get('final_bandwidth', 0)} MB/s")
        print(f"  - 性能衰减：{metrics.get('performance_degradation', 0)}%")
        print(f"  - 最高温度：{metrics.get('max_temperature', 0)}℃")
        print(f"  - 错误计数：{metrics.get('error_count', 0)}")

    print()
    print("验收目标:")
    print("  - 无 IO 错误（错误计数=0）")
    print("  - 性能衰减 < 20%")
    print("  - 设备温度 < 70℃（全程）")
    print("  - 无设备掉线或重启")
    print()
    print("=" * 80)

    return 0 if status == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
