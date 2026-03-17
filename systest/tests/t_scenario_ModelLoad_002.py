#!/usr/bin/env python3
"""
测试用例：t_scenario_ModelLoad_002
算法模型加载测试

测试目的:
模拟 AI 模型加载和推理场景，验证 UFS 设备在大文件顺序读取和随机读取混合负载下的性能表现，
确保满足≥1500 MB/s 的读取带宽要求。

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
    - 可用空间：调用 df 命令获取实际可用空间

1.3 存储设备配置检查
    - 查看支持的功能：
      - 方法 1：cat /sys/block/<device>/device/features
      - 方法 2：smartctl -i /dev/<device> | grep "Features"
      - 方法 3：hdparm -I /dev/<device> | grep "Advanced power management"
      - 预期：列出设备支持的所有功能列表
    - 需要开启的功能：
      - TURBO Mode（如支持）：
        - 检查方法：cat /sys/block/<device>/device/turbo_mode
        - 预期值：1（开启）
        - 开启方法：echo 1 > /sys/block/<device>/device/turbo_mode
      - Write Booster（如支持）：
        - 检查方法：cat /sys/block/<device>/device/write_booster
        - 预期值：1（开启）
        - 开启方法：echo 1 > /sys/block/<device>/device/write_booster
    - 需要关闭的功能：
      - 省电模式（Auto Low Power Mode）：
        - 检查方法：cat /sys/block/<device>/device/power_save
        - 预期值：0（关闭）
        - 关闭方法：echo 0 > /sys/block/<device>/device/power_save
      - 自动休眠（Auto Sleep）：
        - 检查方法：cat /sys/block/<device>/device/auto_sleep
        - 预期值：0（关闭）
        - 关闭方法：echo 0 > /sys/block/<device>/device/auto_sleep
    - 特殊配置项：
      - IO 调度器：
        - 检查方法：cat /sys/block/<device>/queue/scheduler
        - 预期值：none（性能测试推荐）
        - 设置方法：echo none > /sys/block/<device>/queue/scheduler

1.4 UFS 器件配置检查
    - LUN 数量：调用 _get_lun_count() 获取实际 LUN 数量
    -

1.5 器件健康状况检查
    - SMART 状态：调用 smartctl -H 检查实际 SMART 状态
    - 剩余寿命：调用 smartctl -l smartctl 获取实际剩余寿命
    - 温度状态：读取/sys/class/hwmon/*/temp*_input 获取实际温度
    - 错误计数：读取/sys/block/<device>/device/stats 获取实际错误计数

1.6 前置条件验证
    - ✓ SMART 状态验证（必须为正常）
    - ✓ 可用空间验证（必须≥10GB）
    - ✓ 温度验证（必须<70℃）
    - ✓ 剩余寿命验证（必须>90%）

Test Steps:
1. 模拟 AI 模型加载和推理并发场景
2. 配置参数：rw=randrw, rwmixread=70, bs=128k, iodepth=16, numjobs=4, runtime=300
3. 4 个并发线程持续运行 300 秒（5 分钟）
4. 监控读取带宽和加载时间
5. 收集测试结果

Postcondition:
- 记录读取带宽
- 记录模型加载时间
- 生成场景测试报告
- 清理测试数据
- 设备恢复到空闲状态（等待 5 秒）
- 测试后器件状态检查：SMART、温度、错误计数

验收标准:
- 读取带宽 ≥ 1500 MB/s
- 模型加载时间 < 5 秒

注意事项:
- 模拟 AI 模型权重加载 + 推理并发场景
- 70% 读 30% 写模拟真实推理负载
- 128K 块大小模拟模型文件读取
- 如果带宽不足，检查队列深度和并发数
- 建议重复测试 3 次取平均值
"""

import sys
from pathlib import Path

from runner import TestRunner

sys.path.insert(0, str(Path(__file__).parent.parent / "core"))


def main():
    print("=" * 80)
    print("测试用例：t_scenario_ModelLoad_002")
    print("算法模型加载测试")
    print("=" * 80)
    print()

    runner = TestRunner(
        device="/dev/ufs0", output_dir="./results/scenario", verbose=True, check_precondition=True, mode="development"
    )

    print("开始执行测试...")
    print()

    result = runner.run_test("t_scenario_ModelLoad_002")

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
            print(f"  - 读取带宽：{bandwidth} MB/s")

    print()
    print("验收目标:")
    print("  - 读取带宽 ≥ 1500 MB/s")
    print("  - 模型加载时间 < 5 秒")
    print()
    print("=" * 80)

    return 0 if status == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
