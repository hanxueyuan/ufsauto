#!/usr/bin/env python3
"""
测试用例：t_performance_SequentialReadSustained_002
顺序读带宽 (Sustained) 测试

测试目的:
验证 UFS 设备的顺序读带宽 Sustained 性能，评估设备在长时间连续读取下的稳定带宽，
确保满足车规级 UFS 3.1 的≥1800 MB/s 要求。

Precondition:
1.1 系统环境收集
    - 操作系统：读取 /etc/os-release，收集 PRETTY_NAME 字段
    - CPU：读取 /proc/cpuinfo，收集 model name 和 cpu cores
    - 内存：读取 /proc/meminfo，收集 MemTotal
    - FIO 版本：执行 fio --version，收集版本号

1.2 测试目标信息收集
    - 设备路径：
      - 方法 1：ls -l /dev/ | grep -E "(ufs|nvme|sd)" 查找存储设备
      - 方法 2：fdisk -l 列出所有块设备
      - 方法 3：通过配置文件或命令行参数指定设备路径
      - 预期：找到目标 UFS 设备节点（如 /dev/ufs0、/dev/sda 等）
    - 设备型号：
      - 方法 1：读取 /sys/block/<device>/device/model（如存在）
      - 方法 2：smartctl -i /dev/<device> 获取设备信息
      - 预期：返回设备型号字符串
    - 固件版本：
      - 方法 1：读取 /sys/block/<device>/device/rev（如存在）
      - 方法 2：smartctl -i /dev/<device> | grep "Firmware Version"
      - 预期：返回固件版本号
    - 设备容量：
      - 方法：fdisk -l /dev/<device> | grep "Disk"
      - 或使用：blockdev --getsize64 /dev/<device>
      - 预期：返回设备总容量
    - 可用空间：
      - 方法：df -BG /dev/<device> | tail -1 | awk '{print $4}'
      - 预期：可用空间≥10GB

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
    - LUN 配置：读取并记录各 LUN 容量和用途
    - LUN 映射：验证 LUN 与/dev/ufs0 映射关系（待实现）

1.5 器件健康状况检查
    - SMART 状态：执行 smartctl -H /dev/ufs0，检查 SMART overall-health
    - 剩余寿命：执行 smartctl -l smartctl /dev/ufs0，收集 Percentage Used
    - 坏块数量：执行 smartctl -l smartctl /dev/ufs0，收集 Available Spare
    - 温度：读取 /sys/class/hwmon/*/temp*_input，转换为摄氏度
    - 错误计数：读取 /sys/block/ufs0/device/stats，收集 CRC 错误和重传次数

1.6 前置条件验证
    - ✓ SMART 状态验证（必须为 PASS）
    - ✓ 可用空间验证（必须≥10GB）
    - ✓ 温度验证（必须<70℃）
    - ✓ 剩余寿命验证（必须>90%）

Test Steps:
1. 使用 FIO 工具发起顺序读测试
2. 配置参数：rw=read, bs=128k, iodepth=32, numjobs=1, runtime=300, time_based
3. FIO 持续读取 300 秒（5 分钟），记录带宽数据
4. 收集测试结果，计算平均带宽

Postcondition:
- 测试结果保存到 results/performance/目录
- 配置恢复：无配置变更，无需恢复
- 设备恢复到空闲状态（等待 5 秒）
- 数据清理：无测试数据残留
- 测试后器件状态检查：SMART、温度、错误计数

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

from runner import TestRunner

sys.path.insert(0, str(Path(__file__).parent.parent / "core"))


def main():
    print("=" * 80)
    print("测试用例：t_performance_SequentialReadSustained_002")
    print("顺序读带宽 (Sustained) 测试")
    print("=" * 80)
    print()

    runner = TestRunner(
        device="/dev/ufs0", output_dir="./results/performance", verbose=True, check_precondition=True, mode="development"
    )

    print("开始执行测试...")
    print()

    result = runner.run_test("t_performance_SequentialReadSustained_002")

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
            print(f"  - 带宽：{bandwidth} MB/s")

    print()
    print("验收目标:")
    print("  - ≥ 1800 MB/s (容差：95%)")
    print("  - 即 ≥ 1710 MB/s")
    print()
    print("=" * 80)

    return 0 if status == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
