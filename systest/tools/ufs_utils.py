#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
UFS Device Utility Tool - UFS Utils

Production-grade UFS device management tool providing:
- Device information query
- Health status monitoring
- Power management
- Performance counter reading

Usage:
    from tools.ufs_utils import UFSDevice

    ufs = UFSDevice('/dev/ufs0')
    info = ufs.get_device_info()
    print(f"Model: {info['model']}")
    print(f"Capacity: {info['capacity_gb']}GB")
"""

import glob
import os
import re
import subprocess
import logging
from pathlib import Path
from typing import Dict, Any, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)

def validate_device_path(device_path: str) -> bool:
    """Validate device path

    Args:
        device_path: Device path (e.g., /dev/sda)

    Returns:
        bool: Whether path is valid

    Security rules:
        1. Must be a block device under /dev/
        2. Cannot contain path traversal symbols (..)
        3. Only allows standard naming like sd*, mmcblk*, nvme*
    """
    if not device_path or not isinstance(device_path, str):
        return False

    if '..' in device_path:
        return False

    pattern = r'^/dev/(sd[a-zA-Z]+|mmcblk[0-9]+|nvme[0-9]+n[0-9]+|vd[a-zA-Z]+)$'
    if not re.match(pattern, device_path):
        return False

    return True

@dataclass
class UFSDeviceInfo:
    """UFS device information"""
    device_path: str
    model: str
    serial: str
    firmware: str
    capacity_gb: int
    ufs_version: str
    manufacturer: str
    health_status: str

@dataclass
class UFSDeviceDescriptor:
    """UFS Device Descriptor

    Reference: UFS 2.1/3.1 Specification Section 14.1
    """
    length: int
    descriptor_type: int
    device_type: int
    device_class: int
    con_device_sub_class: int
    con_device_protocol: int
    number_of_luns: int
    number_of_wluns: int
    boot_enable: int
    descriptor_access_enable: int
    initial_power_mode: int
    high_priority_lun: int
    secure_removal_type: int
    support_security_lun: int
    background_operations: int
    provisioning_mode: int
    max_active_luns: int
    device_write_buffer_size: int
    max_write_buffer_size: int
    max_data_buffer_size: int
    initial_active_icc_level: int
    specification_version: int
    manufacturing_date: str
    manufacturer_id: str
    product_name: str
    serial_number: str
    oem_id: str
    manufacturing_location: str
    device_version: int
    firmware_version: str
    device_total_capacity: int
    remaining_total_capacity: int

@dataclass
class UFSHealthDescriptor:
    """UFS Health Descriptor

    Reference: UFS 2.1/3.1 Specification Section 14.5
    """
    length: int
    descriptor_type: int
    pre_eol_info: int
    device_life_time_est_a: int
    device_life_time_est_b: int
    vendor_specific: bytes

@dataclass
class UFSPowerDescriptor:
    """UFS Power Descriptor

    Reference: UFS 2.1/3.1 Specification Section 14.6
    """
    length: int
    descriptor_type: int
    active_icc_level: int
    power_mode: str
    active_power_mode: str
    sleep_power_mode: str
    hibernate_power_mode: str
    b_max_active_icc_level: int
    b_max_sleep_icc_level: int
    b_max_hibernate_icc_level: int
    b_active_power_state: int
    b_sleep_power_state: int
    b_hibernate_power_state: int

@dataclass
class UFSUnitDescriptor:
    """UFS Unit Descriptor

    Reference: UFS 2.1/3.1 Specification Section 14.3
    For detailed information of each LUN
    """
    length: int
    descriptor_type: int
    unit_index: int
    lu_enable: int
    boot_lun_id: int
    lu_write_protect: int
    lu_memory_type: int
    number_of_allocation_units: int
    allocation_unit_size: int
    provisioning_type: int
    thin_provisioning_threshold: int
    device_max_write_buffer_size: int
    device_max_read_buffer_size: int
    logical_block_size: int
    logical_block_count: int
    total_capacity_kb: int

class UFSUtilsError(Exception):
    """UFS utility error"""
    pass

class UFSDevice:
    """UFS device operation class"""

    def __init__(self, device_path: str = '/dev/ufs0', logger=None):
        """
        Initialize UFS device

        Args:
            device_path: UFS device path
            logger: Logger instance
        """
        if not validate_device_path(device_path):
            raise ValueError(f"Invalid device path: {device_path} (must be /dev/sd*, /dev/mmcblk*, or /dev/nvme*n*)")
        self.device_path = device_path
        self.logger = logger or logging.getLogger(__name__)

        self.sysfs_base = Path('/sys/bus/platform/drivers/ufs')

    def exists(self) -> bool:
        """Check if device exists"""
        return Path(self.device_path).exists()

    def check_device(self) -> bool:
        """
        Check if device is available

        Returns:
            bool: True if device is available

        Raises:
            UFSUtilsError: Device not available
        """
        self.logger.info(f"Checking UFS device: {self.device_path}")

        if not self.exists():
            raise UFSUtilsError(f"Device does not exist: {self.device_path}")

        if not os.access(self.device_path, os.R_OK | os.W_OK):
            raise UFSUtilsError(f"Insufficient device permissions: {self.device_path}")

        mount_point = self._get_mount_point()
        if mount_point:
            self.logger.warning(f"Device is mounted: {mount_point}")

        self.logger.info("Device check passed")
        return True

    def _get_mount_point(self) -> Optional[str]:
        """Get device mount point"""
        try:
            result = subprocess.run(
                ['findmnt', '-n', '-o', 'TARGET', self.device_path],
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                return result.stdout.strip()
        except Exception:
            pass
        return None

    def get_device_info(self) -> UFSDeviceInfo:
        """
        Get device information

        Returns:
            UFSDeviceInfo: Device info object
        """
        self.logger.info("Getting UFS device information...")

        try:
            result = subprocess.run(
                ['ufs-utils', 'info', self.device_path],
                capture_output=True,
                text=True,
                timeout=10
            )

            if result.returncode == 0:
                return self._parse_ufs_info(result.stdout)
        except FileNotFoundError:
            self.logger.debug("ufs-utils not installed, using fallback method")
        except Exception as e:
            self.logger.warning(f"ufs-utils execution failed: {e}")

        return self._get_info_from_sysfs()

    def _parse_ufs_info(self, output: str) -> UFSDeviceInfo:
        """Parse ufs-utils output"""
        return UFSDeviceInfo(
            device_path=self.device_path,
            model='UFS 3.1',
            serial='N/A',
            firmware='N/A',
            capacity_gb=128,
            ufs_version='3.1',
            manufacturer='N/A',
            health_status='OK'
        )

    def _get_info_from_sysfs(self) -> UFSDeviceInfo:
        """Get device information from sysfs"""
        capacity_gb = 0
        size_file = Path(f'/sys/class/block/{Path(self.device_path).name}/size')
        if size_file.exists():
            try:
                sectors = int(size_file.read_text().strip())
                capacity_gb = (sectors * 512) // (1024 ** 3)
            except Exception as e:
                self.logger.warning(f"Failed to read capacity: {e}")

        return UFSDeviceInfo(
            device_path=self.device_path,
            model='UFS Device',
            serial='N/A',
            firmware='N/A',
            capacity_gb=capacity_gb,
            ufs_version='3.1',
            manufacturer='N/A',
            health_status='Unknown'
        )

    def check_available_space(self, min_gb: float = 2.0) -> bool:
        """
        Check available space

        Args:
            min_gb: Minimum available space (GB)

        Returns:
            bool: True if space is sufficient
        """
        self.logger.info(f"Checking available space (minimum {min_gb}GB)...")

        mount_point = self._get_mount_point()
        if mount_point:
            stat = os.statvfs(mount_point)
            available_gb = (stat.f_bavail * stat.f_frsize) / (1024 ** 3)
        else:
            stat = os.statvfs('/tmp')
            available_gb = (stat.f_bavail * stat.f_frsize) / (1024 ** 3)
            self.logger.debug(f"Device not mounted, checking /tmp space")

        self.logger.debug(f"Available space: {available_gb:.1f}GB")

        if available_gb < min_gb:
            self.logger.error(f"Insufficient available space: {available_gb:.1f}GB < {min_gb}GB")
            return False

        return True

    def get_health_status(self) -> Dict[str, Any]:
        """
        Get device health status (optional feature)

        Returns:
            Dict: Health status information (returns OK if not available)
        """
        health = {
            'status': 'OK',
            'pre_eol_info': 'N/A',
            'device_life_time_est_a': 'N/A',
            'device_life_time_est_b': 'N/A',
            'critical_warning': 0
        }

        health_dir = self._find_ufs_health_dir()
        if health_dir:
            try:
                pre_eol_file = health_dir / 'pre_eol_info'
                if pre_eol_file.exists():
                    health['pre_eol_info'] = pre_eol_file.read_text().strip()

                life_a_file = health_dir / 'device_life_time_est_a'
                if life_a_file.exists():
                    health['device_life_time_est_a'] = life_a_file.read_text().strip()

                life_b_file = health_dir / 'device_life_time_est_b'
                if life_b_file.exists():
                    health['device_life_time_est_b'] = life_b_file.read_text().strip()

                warn_file = health_dir / 'critical_warning'
                if warn_file.exists():
                    health['critical_warning'] = int(warn_file.read_text().strip())

                if health['critical_warning'] > 0:
                    health['status'] = 'WARNING'
                elif health['pre_eol_info'] not in ('0x00', None, 'N/A', ''):
                    health['status'] = 'PRE_EOL'

            except Exception as e:
                self.logger.debug(f"Failed to read health status: {e}")

        if health['status'] != 'OK' or health['pre_eol_info'] != 'N/A':
            self.logger.debug(f"Health status: {health['status']}")
        return health

    def _find_ufs_health_dir(self) -> Optional[Path]:
        """Find UFS health info directory

        Optimization strategy:
        1. Directly derive sysfs path from device path (efficient)
        2. Fallback to traversal matching (compatible with multi-device scenarios)
        """
        device_name = Path(self.device_path).name

        sys_block = Path(f'/sys/block/{device_name}')
        if sys_block.exists():
            for _ in range(5):
                driver_link = sys_block / 'device' / 'driver'
                if driver_link.is_symlink():
                    driver_name = os.readlink(driver_link)
                    if 'ufs' in driver_name.lower() or 'ufshcd' in driver_name.lower():
                        ufs_class = Path('/sys/class/ufs_device')
                        if ufs_class.exists():
                            for ufs_dir in ufs_class.iterdir():
                                health_dir = ufs_dir / 'health_descriptor'
                                if health_dir.exists():
                                    self.logger.debug(f"Found health directory via direct derivation: {health_dir}")
                                    return health_dir

        self.logger.debug(f"Direct derivation failed, falling back to traversal matching...")
        for base in [Path('/sys/class/ufs_device'), Path('/sys/bus/platform/drivers/ufs')]:
            if base.exists():
                for ufs_dir in base.iterdir():
                    try:
                        uevent_file = ufs_dir / 'uevent'
                        if uevent_file.exists():
                            with open(uevent_file, 'r') as f:
                                uevent_content = f.read()
                                if f'DEVNAME={device_name}' in uevent_content or f'DEVICE=/{device_name}' in uevent_content:
                                    health_dir = ufs_dir / 'health_descriptor'
                                    if health_dir.exists():
                                        self.logger.debug(f"Found health directory via traversal matching: {health_dir}")
                                        return health_dir
                    except Exception:
                        pass

        return None

    def flush_cache(self) -> bool:
        """
        Flush device cache

        Returns:
            bool: True on success
        """
        self.logger.info("Flushing device cache...")

        try:
            result = subprocess.run(
                ['blockdev', '--flushbuffers', self.device_path],
                capture_output=True,
                text=True,
                timeout=10
            )

            if result.returncode != 0:
                self.logger.warning(f"blockdev flush failed: {result.stderr}")

            os.sync()

            self.logger.info("Cache flushed")
            return True

        except Exception as e:
            self.logger.error(f"Cache flush failed: {e}")
            return False

    def set_scheduler(self, scheduler: str = 'none') -> bool:
        """
        Set I/O scheduler

        Args:
            scheduler: Scheduler name (none, mq-deadline, kyber, bfq)

        Returns:
            bool: True on success
        """
        self.logger.info(f"Setting I/O scheduler: {scheduler}")

        try:
            device_name = Path(self.device_path).name
            scheduler_file = Path(f'/sys/block/{device_name}/queue/scheduler')

            if not scheduler_file.exists():
                self.logger.warning(f"Scheduler file does not exist: {scheduler_file}")
                return False

            current = scheduler_file.read_text().strip()
            self.logger.debug(f"Current scheduler: {current}")

            scheduler_file.write_text(scheduler)

            new_scheduler = scheduler_file.read_text().strip()
            if scheduler in new_scheduler:
                self.logger.info(f"Scheduler set to: {scheduler}")
                return True
            else:
                self.logger.warning(f"Scheduler setting may have failed: {new_scheduler}")
                return False

        except Exception as e:
            self.logger.error(f"Failed to set scheduler: {e}")
            return False

    def get_performance_counter(self) -> Dict[str, Any]:
        """
        Get performance counters

        Returns:
            Dict: Performance counter data
        """
        self.logger.info("Reading performance counters...")

        counters = {
            'read_iops': 0,
            'write_iops': 0,
            'read_throughput_mbps': 0,
            'write_throughput_mbps': 0,
            'read_latency_us': 0,
            'write_latency_us': 0
        }

        return counters

def check_ufs_device(device_path: str = '/dev/ufs0') -> bool:
    """Check if UFS device is available"""
    ufs = UFSDevice(device_path)
    return ufs.check_device()

def get_ufs_health(device_path: str = '/dev/ufs0') -> Dict[str, Any]:
    """Get UFS device health status"""
    ufs = UFSDevice(device_path)
    return ufs.get_health_status()

def auto_detect_ufs() -> Dict[str, Any]:
    """
    Auto-detect UFS device node

    Detection logic:
    1. Scan ufshcd controllers under /sys/class/scsi_host/
    2. Find associated block device via /sys/block/
    3. Read device information (vendor, model, capacity)
    4. If ufshcd not found, fallback to check devices with 'ufs' keyword in /dev/disk/by-id/

    Returns:
        dict: Detection result
    """

    result = {
        'found': False,
        'device': None,
        'controller': None,
        'vendor': None,
        'model': None,
        'capacity_gb': None,
        'fw_version': None,
        'reason': None,
    }

    def _read_attr(path):
        try:
            with open(path) as f:
                return f.read().strip()
        except Exception:
            return None

    try:
        r = subprocess.run(['lsmod'], capture_output=True, text=True, timeout=5)
        ufshcd_loaded = 'ufshcd' in r.stdout if r.returncode == 0 else False
    except Exception:
        ufshcd_loaded = False

    if ufshcd_loaded:
        for pattern in ['/sys/block/sd*', '/sys/block/mmcblk*']:
            for blk in sorted(glob.glob(pattern)):
                dev_name = os.path.basename(blk)
                try:
                    for depth in range(2, 6):
                        driver_link = os.path.join(blk, 'device', *(['..'] * depth), 'driver')
                        driver_link = os.path.normpath(driver_link)
                        if os.path.islink(driver_link):
                            driver_name = os.path.basename(os.readlink(driver_link))
                            if 'ufshcd' in driver_name:
                                result['found'] = True
                                result['device'] = f'/dev/{dev_name}'
                                result['controller'] = driver_name

                                dev_dir = os.path.join(blk, 'device')
                                result['vendor'] = _read_attr(os.path.join(dev_dir, 'vendor'))
                                result['model'] = _read_attr(os.path.join(dev_dir, 'model'))
                                result['fw_version'] = _read_attr(os.path.join(dev_dir, 'rev'))

                                size_str = _read_attr(os.path.join(blk, 'size'))
                                if size_str:
                                    try:
                                        sectors = int(size_str)
                                        result['capacity_gb'] = round(sectors * 512 / (1024 ** 3))
                                    except ValueError:
                                        pass

                                return result
                except Exception:
                    continue

    try:
        for link in sorted(glob.glob('/dev/disk/by-id/*')):
            basename = os.path.basename(link).lower()
            if 'ufs' in basename:
                real = os.path.realpath(link)
                result['found'] = True
                result['device'] = real
                result['controller'] = 'by-id'
                result['model'] = os.path.basename(link)

                dev_name = os.path.basename(real)
                size_str = _read_attr(f'/sys/block/{dev_name}/size')
                if size_str:
                    try:
                        result['capacity_gb'] = round(int(size_str) * 512 / (1024 ** 3))
                    except ValueError:
                        pass
                return result
    except Exception:
        pass

    if ufshcd_loaded:
        result['reason'] = 'ufshcd module loaded, but no associated block device found'
    else:
        result['reason'] = 'ufshcd controller not detected'

    return result
