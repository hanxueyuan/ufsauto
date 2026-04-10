#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
UFS Health Monitor - UFS 健康状态监控模块

提供 UFS 设备健康状态的采集、监控和报告功能。

支持多种数据采集方式：
1. sysfs 接口（优先级最高，无需额外工具）
2. SCSI VPD 页面（需要 sg3_utils）
3. 降级方案（当无法获取时返回默认状态）

Usage:
    from tools.health_monitor import UFSHealthMonitor
    
    monitor = UFSHealthMonitor('/dev/sda')
    health = monitor.get_health()
    print(f"Health status: {health['status']}")
    
命令行使用:
    python3 health_monitor.py --device /dev/sda
    python3 health_monitor.py --scan  # 扫描所有可能的 UFS 设备
"""

import os
import subprocess
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class HealthStatus(Enum):
    """UFS 健康状态枚举"""
    OK = 'OK'              # 正常
    WARNING = 'WARNING'    # 警告
    CRITICAL = 'CRITICAL'  # 严重警告
    PRE_EOL = 'PRE_EOL'    # 接近寿命终点
    UNSUPPORTED = 'UNSUPPORTED'  # 不支持


@dataclass
class HealthData:
    """UFS 健康数据"""
    status: HealthStatus = HealthStatus.UNSUPPORTED
    pre_eol_info: str = 'N/A'           # Pre-EOL 信息 (0x00=正常，0x01=警告，0x02=严重)
    device_life_time_est_a: str = 'N/A'  # 寿命估算 A（基于实际使用）
    device_life_time_est_b: str = 'N/A'  # 寿命估算 B（基于工厂测试）
    critical_warning: int = 0           # 关键警告标志 (0=正常，1=警告)
    temperature: Optional[int] = None   # 温度（摄氏度）
    life_span: Optional[int] = None     # 寿命百分比 (0-100)
    source: str = 'none'                # 数据来源：'sysfs', 'scsi', 'none'
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'status': self.status.value,
            'pre_eol_info': self.pre_eol_info,
            'device_life_time_est_a': self.device_life_time_est_a,
            'device_life_time_est_b': self.device_life_time_est_b,
            'critical_warning': self.critical_warning,
            'temperature': self.temperature,
            'life_span': self.life_span,
            'source': self.source
        }


class UFSHealthMonitor:
    """
    UFS 健康状态监控器
    
    提供 UFS 设备健康状态的采集功能，支持多种数据源：
    1. sysfs 接口（推荐）
    2. SCSI VPD 页面（备选）
    """
    
    def __init__(self, device_path: str = '/dev/sda', logger=None):
        """
        初始化健康监控器
        
        Args:
            device_path: 设备路径（如 /dev/sda）
            logger: 日志记录器
        """
        self.device_path = device_path
        self.device_name = Path(device_path).name
        self.logger = logger or logging.getLogger(__name__)
        
    def get_health(self) -> Dict[str, Any]:
        """
        获取设备健康状态
        
        Returns:
            Dict: 健康状态信息
        """
        self.logger.info(f"Getting health status for {self.device_path}")
        
        health = HealthData()
        
        # 优先级 1: 尝试从 sysfs 读取
        health_dir = self._find_ufs_health_dir()
        if health_dir:
            self._read_from_sysfs(health_dir, health)
        
        # 优先级 2: 如果 sysfs 失败，尝试 SCSI
        if health.source == 'none':
            self._read_from_scsi(health)
        
        # 确定最终状态
        if health.source != 'none':
            self._determine_status(health)
        else:
            # 降级处理：无法获取时假设正常
            health.status = HealthStatus.OK
            self.logger.debug("UFS health not available, using default OK status")
        
        result = health.to_dict()
        self.logger.debug(f"Health status: {result['status']} (source: {result['source']})")
        return result
    
    def _find_ufs_health_dir(self) -> Optional[Path]:
        """
        查找 UFS health_descriptor 目录
        
        Returns:
            Path: health_descriptor 目录路径，不存在则返回 None
        """
        self.logger.debug(f"Searching for UFS health directory for {self.device_name}")
        
        # 策略 1: 扫描 /sys/bus/ufs/devices/
        ufs_devices_dir = Path('/sys/bus/ufs/devices')
        if ufs_devices_dir.exists():
            for ufs_dev_dir in ufs_devices_dir.iterdir():
                if ufs_dev_dir.is_dir():
                    health_dir = ufs_dev_dir / 'health_descriptor'
                    if health_dir.exists():
                        self.logger.debug(f"Found UFS health directory: {health_dir}")
                        return health_dir
            self.logger.debug(f"No health_descriptor found under {ufs_devices_dir}")
        
        # 策略 2: 从 SCSI 设备反向查找 UFS 驱动
        sys_block = Path(f'/sys/block/{self.device_name}')
        if sys_block.exists():
            for depth in range(1, 8):
                try:
                    device_dir = sys_block
                    for _ in range(depth):
                        device_dir = device_dir / 'device'
                        if not device_dir.exists():
                            break
                    
                    if device_dir.exists():
                        driver_link = device_dir / 'driver'
                        if driver_link.is_symlink():
                            driver_path = os.readlink(driver_link)
                            driver_name = os.path.basename(driver_path)
                            if 'ufshcd' in driver_name.lower() or 'ufs' in driver_name.lower():
                                self.logger.debug(f"Found UFS driver: {driver_name}")
                                # 查找对应的 UFS 设备
                                ufs_class = Path('/sys/class/ufs_device')
                                if ufs_class.exists():
                                    for ufs_dir in ufs_class.iterdir():
                                        health_dir = ufs_dir / 'health_descriptor'
                                        if health_dir.exists():
                                            self.logger.debug(f"Found via driver link: {health_dir}")
                                            return health_dir
                except Exception:
                    continue
        
        # 策略 3: 尝试 /sys/class/ufs_device/
        ufs_class = Path('/sys/class/ufs_device')
        if ufs_class.exists():
            for ufs_dir in ufs_class.iterdir():
                health_dir = ufs_dir / 'health_descriptor'
                if health_dir.exists():
                    self.logger.debug(f"Found via ufs_class: {health_dir}")
                    return health_dir
        
        self.logger.debug("UFS health directory not found")
        return None
    
    def _read_from_sysfs(self, health_dir: Path, health: HealthData):
        """
        从 sysfs 读取健康状态
        
        Args:
            health_dir: health_descriptor 目录路径
            health: HealthData 对象（会被更新）
        """
        health.source = 'sysfs'
        
        # 读取 Pre-EOL 信息
        pre_eol_file = health_dir / 'pre_eol_info'
        if pre_eol_file.exists():
            try:
                value = pre_eol_file.read_text().strip()
                health.pre_eol_info = value
                self.logger.debug(f"pre_eol_info: {value}")
            except Exception as e:
                self.logger.debug(f"Failed to read pre_eol_info: {e}")
        
        # 读取寿命估算 A
        life_a_file = health_dir / 'device_life_time_est_a'
        if life_a_file.exists():
            try:
                value = life_a_file.read_text().strip()
                health.device_life_time_est_a = value
                # 转换为寿命百分比
                if value.startswith('0x'):
                    life_pct = int(value, 16) * 10
                else:
                    life_pct = int(value) * 10
                health.life_span = min(100, life_pct)
                self.logger.debug(f"device_life_time_est_a: {value}, life_span: {health.life_span}%")
            except Exception as e:
                self.logger.debug(f"Failed to read life_time_est_a: {e}")
        
        # 读取寿命估算 B
        life_b_file = health_dir / 'device_life_time_est_b'
        if life_b_file.exists():
            try:
                value = life_b_file.read_text().strip()
                health.device_life_time_est_b = value
                self.logger.debug(f"device_life_time_est_b: {value}")
            except Exception as e:
                self.logger.debug(f"Failed to read life_time_est_b: {e}")
        
        # 读取关键警告标志
        warn_file = health_dir / 'critical_warning'
        if warn_file.exists():
            try:
                value = int(warn_file.read_text().strip())
                health.critical_warning = value
                self.logger.debug(f"critical_warning: {value}")
            except Exception as e:
                self.logger.debug(f"Failed to read critical_warning: {e}")
        
        # 读取温度（如果可用）
        temp_file = health_dir / 'temperature'
        if temp_file.exists():
            try:
                value = int(temp_file.read_text().strip())
                health.temperature = value
                self.logger.debug(f"temperature: {value}°C")
            except Exception as e:
                self.logger.debug(f"Failed to read temperature: {e}")
    
    def _read_from_scsi(self, health: HealthData):
        """
        从 SCSI VPD 页面读取健康状态（备选方案）
        
        Args:
            health: HealthData 对象（会被更新）
        """
        # 检查 sg_inq 是否可用
        try:
            result = subprocess.run(
                ['which', 'sg_inq'],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode != 0:
                self.logger.debug("sg_inq not available")
                return
        except Exception:
            return
        
        try:
            # 读取 VPD 页面 0xC0
            result = subprocess.run(
                ['sg_inq', '-p', '0xc0', self.device_path],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                output = result.stdout
                self.logger.debug(f"SCSI VPD 0xC0: {output[:200]}...")
                health.source = 'scsi'
                # 注意：SCSI VPD 解析需要厂商特定知识，这里仅标记来源
                
        except Exception as e:
            self.logger.debug(f"SCSI health read failed: {e}")
    
    def _determine_status(self, health: HealthData):
        """
        根据读取的数据确定健康状态
        
        Args:
            health: HealthData 对象
        """
        if health.critical_warning > 0:
            health.status = HealthStatus.CRITICAL
        elif health.pre_eol_info in ('0x01', '0x02'):
            health.status = HealthStatus.PRE_EOL
        else:
            health.status = HealthStatus.OK


def scan_ufs_devices() -> List[str]:
    """
    扫描系统中所有可能的 UFS 设备
    
    Returns:
        List[str]: 设备路径列表
    """
    devices = []
    
    # 方法 1: 扫描 /sys/bus/ufs/devices/
    ufs_devices_dir = Path('/sys/bus/ufs/devices')
    if ufs_devices_dir.exists():
        for ufs_dev_dir in ufs_devices_dir.iterdir():
            if ufs_dev_dir.is_dir():
                # 尝试找到对应的块设备
                uevent_file = ufs_dev_dir / 'uevent'
                if uevent_file.exists():
                    try:
                        content = uevent_file.read_text()
                        for line in content.split('\n'):
                            if line.startswith('DEVNAME='):
                                dev_name = line.split('=')[1]
                                devices.append(f'/dev/{dev_name}')
                    except Exception:
                        pass
    
    # 方法 2: 扫描通过 ufshcd 驱动的设备
    for block_dir in Path('/sys/block').iterdir():
        if block_dir.is_dir():
            dev_name = block_dir.name
            if not dev_name.startswith(('sd', 'mmcblk', 'nvme')):
                continue
            
            # 查找 UFS 驱动
            for depth in range(1, 8):
                device_dir = block_dir
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
                            if 'ufshcd' in driver_name.lower() or 'ufs' in driver_name.lower():
                                devices.append(f'/dev/{dev_name}')
                                break
                        except Exception:
                            pass
    
    return list(set(devices))  # 去重


def main():
    """命令行入口"""
    import argparse
    
    parser = argparse.ArgumentParser(description='UFS Health Monitor')
    parser.add_argument('--device', '-d', help='Device path (e.g., /dev/sda)')
    parser.add_argument('--scan', action='store_true', help='Scan all UFS devices')
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')
    args = parser.parse_args()
    
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format='%(levelname)s: %(message)s'
    )
    
    if args.scan:
        print("🔍 扫描 UFS 设备...")
        devices = scan_ufs_devices()
        if devices:
            print(f"找到 {len(devices)} 个可能的 UFS 设备:")
            for dev in devices:
                print(f"  - {dev}")
        else:
            print("未找到 UFS 设备")
        return
    
    if not args.device:
        # 尝试自动检测
        devices = scan_ufs_devices()
        if devices:
            args.device = devices[0]
            print(f"Auto-detected device: {args.device}")
        else:
            print("❌ 未指定设备且未找到 UFS 设备")
            print("使用方法: python3 health_monitor.py --device /dev/sda")
            print("或扫描所有设备：python3 health_monitor.py --scan")
            return
    
    monitor = UFSHealthMonitor(args.device)
    health = monitor.get_health()
    
    print("\n" + "=" * 60)
    print("UFS 健康状态报告")
    print("=" * 60)
    
    status_icons = {
        'OK': '✅',
        'WARNING': '⚠️',
        'CRITICAL': '❌',
        'PRE_EOL': '⚡',
        'UNSUPPORTED': 'ℹ️'
    }
    
    status = health['status']
    icon = status_icons.get(status, '❓')
    
    print(f"\n{icon} 健康状态：{status}")
    print(f"   数据来源：{health.get('source', 'none')}")
    
    print(f"\n📊 详细信息:")
    print(f"   Pre-EOL 信息：     {health.get('pre_eol_info', 'N/A')}")
    print(f"   寿命估算 A:        {health.get('device_life_time_est_a', 'N/A')}")
    print(f"   寿命估算 B:        {health.get('device_life_time_est_b', 'N/A')}")
    print(f"   寿命百分比：       {health.get('life_span', 'N/A')}%")
    print(f"   关键警告标志：     {health.get('critical_warning', 'N/A')}")
    print(f"   温度：            {health.get('temperature', 'N/A')}°C")
    
    print("\n" + "=" * 60)


if __name__ == '__main__':
    main()
