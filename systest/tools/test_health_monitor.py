#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
UFS Health Status Test Script

用于测试和验证 UFS 健康状态采集功能

Usage:
    sudo python3 test_health_monitor.py
    python3 test_health_monitor.py --device /dev/sda
"""

import sys
import argparse
import logging
from pathlib import Path

# Add tools directory to path
tools_dir = Path(__file__).parent
sys.path.insert(0, str(tools_dir))

from ufs_utils import UFSDevice

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def print_health_report(health: dict):
    """Print formatted health report"""
    print("\n" + "=" * 60)
    print("UFS 健康状态报告")
    print("=" * 60)
    
    status = health.get('status', 'Unknown')
    status_icon = {
        'OK': '✅',
        'WARNING': '⚠️',
        'CRITICAL': '❌',
        'PRE_EOL': '⚡',
        'UNSUPPORTED': 'ℹ️'
    }.get(status, '❓')
    
    print(f"\n{status_icon} 健康状态：{status}")
    print(f"   数据来源：{health.get('source', 'none')}")
    
    print(f"\n📊 详细信息:")
    print(f"   Pre-EOL 信息：     {health.get('pre_eol_info', 'N/A')}")
    print(f"   寿命估算 A:        {health.get('device_life_time_est_a', 'N/A')}")
    print(f"   寿命估算 B:        {health.get('device_life_time_est_b', 'N/A')}")
    print(f"   寿命百分比：       {health.get('life_span', 'N/A')}%")
    print(f"   关键警告标志：     {health.get('critical_warning', 'N/A')}")
    print(f"   温度：            {health.get('temperature', 'N/A')}°C")
    
    print("\n" + "=" * 60)


def check_sysfs_structure():
    """Check UFS sysfs structure"""
    print("\n🔍 检查 UFS sysfs 结构...")
    
    import os
    
    # 检查 /sys/bus/ufs/devices/
    ufs_devices = Path('/sys/bus/ufs/devices')
    if ufs_devices.exists():
        print(f"✅ {ufs_devices} 存在")
        for dev in ufs_devices.iterdir():
            if dev.is_dir():
                print(f"   设备：{dev.name}")
                health_dir = dev / 'health_descriptor'
                if health_dir.exists():
                    print(f"      ✅ health_descriptor 存在")
                    for f in health_dir.iterdir():
                        if f.is_file():
                            try:
                                content = f.read_text().strip()
                                print(f"         - {f.name}: {content}")
                            except Exception as e:
                                print(f"         - {f.name}: <无法读取: {e}>")
                else:
                    print(f"      ❌ health_descriptor 不存在")
    else:
        print(f"❌ {ufs_devices} 不存在")
    
    # 检查 /sys/class/ufs_device/
    ufs_class = Path('/sys/class/ufs_device')
    if ufs_class.exists():
        print(f"\n✅ {ufs_class} 存在")
        for dev in ufs_class.iterdir():
            if dev.is_dir():
                print(f"   设备：{dev.name}")
    else:
        print(f"\n❌ {ufs_class} 不存在")
    
    # 检查设备映射
    print(f"\n🔍 检查设备映射关系...")
    for block_dev in Path('/sys/block').iterdir():
        if block_dev.is_dir():
            dev_name = block_dev.name
            if dev_name.startswith(('sd', 'mmcblk', 'nvme')):
                print(f"\n   设备：{dev_name}")
                # 查找驱动
                for depth in range(1, 8):
                    device_dir = block_dev
                    for _ in range(depth):
                        device_dir = device_dir / 'device'
                        if not device_dir.exists():
                            break
                    if device_dir.exists():
                        driver_link = device_dir / 'driver'
                        if driver_link.is_symlink():
                            try:
                                driver_path = os.readlink(driver_link)
                                driver_name = os.path.basename(driver_path)
                                print(f"      驱动层级 {depth}: {driver_name}")
                                if 'ufs' in driver_name.lower():
                                    print(f"         ⭐ UFS 驱动找到!")
                            except Exception:
                                pass


def main():
    parser = argparse.ArgumentParser(description='UFS Health Status Test')
    parser.add_argument('--device', '-d', default='/dev/sda',
                        help='Device path (default: /dev/sda)')
    parser.add_argument('--check-sysfs', action='store_true',
                        help='Check sysfs structure only')
    args = parser.parse_args()
    
    if args.check_sysfs:
        check_sysfs_structure()
        return 0
    
    print(f"\n🔍 测试 UFS 健康状态采集功能")
    print(f"设备路径：{args.device}")
    
    try:
        ufs = UFSDevice(args.device, logger=logger)
        
        # 检查设备是否存在
        print(f"\n1. 检查设备存在性...")
        if not ufs.exists():
            print(f"❌ 设备不存在：{args.device}")
            print(f"   请检查设备路径是否正确")
            return 1
        print(f"✅ 设备存在：{args.device}")
        
        # 获取健康状态
        print(f"\n2. 获取健康状态...")
        health = ufs.get_health_status()
        
        print_health_report(health)
        
        # 验证结果
        print(f"\n3. 验证结果...")
        if health['source'] == 'none':
            print(f"⚠️  警告：无法获取 UFS 健康状态")
            print(f"   可能原因:")
            print(f"   - 设备不是 UFS 设备（可能是 SATA SSD、NVMe 等）")
            print(f"   - 内核不支持 UFS 健康查询")
            print(f"   - 需要 root 权限")
            print(f"   - 设备固件不支持健康描述符")
            print(f"\n   降级方案：健康状态默认为 'OK'，测试将继续")
            return 0
        else:
            print(f"✅ 成功获取健康状态（来源：{health['source']}）")
            return 0
            
    except Exception as e:
        print(f"\n❌ 错误：{type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())
