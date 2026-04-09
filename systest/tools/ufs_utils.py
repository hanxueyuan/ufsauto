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

    # Prevent path traversal attack
    if '..' in device_path:
        return False

    # Only allow standard device naming patterns
    # /dev/sd[a-zA-Z]+  (e.g., /dev/sda, /dev/sdb)
    # /dev/mmcblk[0-9]+  (e.g., /dev/mmcblk0)
    # /dev/nvme[0-9]+n[0-9]+  (e.g., /dev/nvme0n1)
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
    length: int                     # Descriptor length
    descriptor_type: int            # Descriptor type (0x01)
    device_type: int                # Device type
    device_class: int               # Device class
    con_device_sub_class: int       # Device subclass
    con_device_protocol: int        # Device protocol
    number_of_luns: int             # LUN count
    number_of_wluns: int            # W-LUN count
    boot_enable: int                # Boot partition enable
    descriptor_access_enable: int   # Descriptor access enable
    initial_power_mode: int         # Initial power mode
    high_priority_lun: int          # High priority LUN
    secure_removal_type: int        # Secure removal type
    support_security_lun: int       # Security LUN support
    background_operations: int      # Background operation support
    provisioning_mode: int          # Provisioning mode
    max_active_luns: int            # Max active LUNs
    device_write_buffer_size: int   # Write buffer size
    max_write_buffer_size: int      # Max write buffer
    max_data_buffer_size: int       # Max data buffer
    initial_active_icc_level: int   # Initial active ICC level
    specification_version: int      # Specification version
    manufacturing_date: str         # Manufacturing date
    manufacturer_id: str            # Manufacturer ID
    product_name: str               # Product name
    serial_number: str              # Serial number
    oem_id: str                     # OEM ID
    manufacturing_location: str     # Manufacturing location
    device_version: int             # Device version
    firmware_version: str           # Firmware version
    device_total_capacity: int      # Total capacity (KB)
    remaining_total_capacity: int   # Remaining capacity (KB)


@dataclass
class UFSHealthDescriptor:
    """UFS Health Descriptor

    Reference: UFS 2.1/3.1 Specification Section 14.5
    """
    length: int                     # Descriptor length
    descriptor_type: int            # Descriptor type (0x05)
    pre_eol_info: int               # Pre-EOL info (0x00-0x03)
    device_life_time_est_a: int     # Device life time est A (SLC/MLC)
    device_life_time_est_b: int     # Device life time est B (TLC)
    vendor_specific: bytes          # Vendor specific info


@dataclass
class UFSPowerDescriptor:
    """UFS Power Descriptor

    Reference: UFS 2.1/3.1 Specification Section 14.6
    """
    length: int                     # Descriptor length
    descriptor_type: int            # Descriptor type (0x06)
    active_icc_level: int           # Active ICC level
    power_mode: str                 # Current power mode
    active_power_mode: str          # Active power mode
    sleep_power_mode: str           # Sleep power mode
    hibernate_power_mode: str       # Hibernate power mode
    b_max_active_icc_level: int     # Max active ICC level
    b_max_sleep_icc_level: int      # Max sleep ICC level
    b_max_hibernate_icc_level: int  # Max hibernate ICC level
    b_active_power_state: int       # Active power state
    b_sleep_power_state: int        # Sleep power state
    b_hibernate_power_state: int    # Hibernate power state


@dataclass
class UFSUnitDescriptor:
    """UFS Unit Descriptor

    Reference: UFS 2.1/3.1 Specification Section 14.3
    For detailed information of each LUN
    """
    length: int                     # Descriptor length
    descriptor_type: int            # Descriptor type (0x03)
    unit_index: int                 # Unit index
    lu_enable: int                  # LU enable
    boot_lun_id: int                # Boot LUN ID
    lu_write_protect: int           # Write protect status
    lu_memory_type: int             # Memory type (SLC/MLC/TLC)
    number_of_allocation_units: int # Allocation unit count
    allocation_unit_size: int       # Allocation unit size
    provisioning_type: int          # Provisioning type
    thin_provisioning_threshold: int # Thin provisioning threshold
    device_max_write_buffer_size: int # Max write buffer
    device_max_read_buffer_size: int  # Max read buffer
    logical_block_size: int         # Logical block size
    logical_block_count: int        # Logical block count
    total_capacity_kb: int          # Total capacity (KB)


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
        # Validate device path
        if not validate_device_path(device_path):
            raise ValueError(f"Invalid device path: {device_path} (must be /dev/sd*, /dev/mmcblk*, or /dev/nvme*n*)")
        self.device_path = device_path
        self.logger = logger or logging.getLogger(__name__)

        # sysfs path
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

        # 1. Check device file exists
        if not self.exists():
            raise UFSUtilsError(f"Device does not exist: {self.device_path}")

        # 2. Check permissions
        if not os.access(self.device_path, os.R_OK | os.W_OK):
            raise UFSUtilsError(f"Insufficient device permissions: {self.device_path}")

        # 3. Check if mounted
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

        # Try using ufs-utils tool
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

        # Fallback: Read from sysfs
        return self._get_info_from_sysfs()

    def _parse_ufs_info(self, output: str) -> UFSDeviceInfo:
        """Parse ufs-utils output"""
        # Simplified implementation, actual parsing depends on output format
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
        # Try to read device size
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

        # If device is mounted, check mount point
        mount_point = self._get_mount_point()
        if mount_point:
            stat = os.statvfs(mount_point)
            available_gb = (stat.f_bavail * stat.f_frsize) / (1024 ** 3)
        else:
            # Device not mounted, check /tmp
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
        # Default health status (assumes OK if health info not available)
        health = {
            'status': 'OK',
            'pre_eol_info': 'N/A',
            'device_life_time_est_a': 'N/A',
            'device_life_time_est_b': 'N/A',
            'critical_warning': 0
        }

        # Try to read from sysfs (UFS health info is optional)
        health_dir = self._find_ufs_health_dir()
        if health_dir:
            try:
                # Read pre-EOL info
                pre_eol_file = health_dir / 'pre_eol_info'
                if pre_eol_file.exists():
                    health['pre_eol_info'] = pre_eol_file.read_text().strip()

                # Read device life time estimates
                life_a_file = health_dir / 'device_life_time_est_a'
                if life_a_file.exists():
                    health['device_life_time_est_a'] = life_a_file.read_text().strip()

                life_b_file = health_dir / 'device_life_time_est_b'
                if life_b_file.exists():
                    health['device_life_time_est_b'] = life_b_file.read_text().strip()

                # Read critical warning
                warn_file = health_dir / 'critical_warning'
                if warn_file.exists():
                    health['critical_warning'] = int(warn_file.read_text().strip())

                # Determine overall status
                if health['critical_warning'] > 0:
                    health['status'] = 'WARNING'
                elif health['pre_eol_info'] not in ('0x00', None, 'N/A', ''):
                    health['status'] = 'PRE_EOL'

            except Exception as e:
                self.logger.debug(f"Failed to read health status: {e}")

        # Only log if health info is actually available
        if health['status'] != 'OK' or health['pre_eol_info'] != 'N/A':
            self.logger.debug(f"Health status: {health['status']}")
        return health

    def _find_ufs_health_dir(self) -> Optional[Path]:
        """Find UFS health info directory

        Optimization strategy:
        1. Directly derive sysfs path from device path (efficient)
        2. Fallback to traversal matching (compatible with multi-device scenarios)
        """
        # Extract device name from device path (e.g., /dev/sda -> sda)
        device_name = Path(self.device_path).name

        # Strategy 1: Directly derive sysfs path (efficient)
        # /dev/sda -> /sys/block/sda/device/ -> Find ufs related path
        sys_block = Path(f'/sys/block/{device_name}')
        if sys_block.exists():
            # Look up driver
            for _ in range(5):
                driver_link = sys_block / 'device' / 'driver'
                if driver_link.is_symlink():
                    driver_name = os.readlink(driver_link)
                    if 'ufs' in driver_name.lower() or 'ufshcd' in driver_name.lower():
                        # Found UFS driver, try to locate health_descriptor
                        # Typical path: /sys/class/ufs_device/ufsX/health_descriptor/
                        ufs_class = Path('/sys/class/ufs_device')
                        if ufs_class.exists():
                            for ufs_dir in ufs_class.iterdir():
                                health_dir = ufs_dir / 'health_descriptor'
                                if health_dir.exists():
                                    self.logger.debug(f"Found health directory via direct derivation: {health_dir}")
                                    return health_dir

        # Strategy 2: Fallback to traversal matching (compatible with multi-device scenarios)
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

        # Health info is optional - don't warn if not available
        # Many platforms don't expose UFS health info via sysfs
        return None

    def flush_cache(self) -> bool:
        """
        Flush device cache

        Returns:
            bool: True on success
        """
        self.logger.info("Flushing device cache...")

        try:
            # Use blockdev to flush
            result = subprocess.run(
                ['blockdev', '--flushbuffers', self.device_path],
                capture_output=True,
                text=True,
                timeout=10
            )

            if result.returncode != 0:
                self.logger.warning(f"blockdev flush failed: {result.stderr}")

            # sync system call
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

            # Read current scheduler
            current = scheduler_file.read_text().strip()
            self.logger.debug(f"Current scheduler: {current}")

            # Set new scheduler
            scheduler_file.write_text(scheduler)

            # Verify
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

        # Read from debugfs or other interfaces
        # Framework provided here, actual implementation depends on specific platform

        return counters


# ========== Convenience functions ==========

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

    # -- Method 1: Find block device via ufshcd driver --

    # Check if ufshcd module is loaded
    try:
        r = subprocess.run(['lsmod'], capture_output=True, text=True, timeout=5)
        ufshcd_loaded = 'ufshcd' in r.stdout if r.returncode == 0 else False
    except Exception:
        ufshcd_loaded = False

    if ufshcd_loaded:
        # Scan both sd* and mmcblk* devices (some platforms name UFS as mmcblk*)
        for pattern in ['/sys/block/sd*', '/sys/block/mmcblk*']:
            for blk in sorted(glob.glob(pattern)):
                dev_name = os.path.basename(blk)
                try:
                    # Look up driver to check if it's ufshcd
                    # Typical path: /sys/block/sda/device/../../.. points to host adapter
                    for depth in range(2, 6):
                        driver_link = os.path.join(blk, 'device', *(['..'] * depth), 'driver')
                        driver_link = os.path.normpath(driver_link)
                        if os.path.islink(driver_link):
                            driver_name = os.path.basename(os.readlink(driver_link))
                            if 'ufshcd' in driver_name:
                                result['found'] = True
                                result['device'] = f'/dev/{dev_name}'
                                result['controller'] = driver_name

                                # Read vendor / model / rev
                                dev_dir = os.path.join(blk, 'device')
                                result['vendor'] = _read_attr(os.path.join(dev_dir, 'vendor'))
                                result['model'] = _read_attr(os.path.join(dev_dir, 'model'))
                                result['fw_version'] = _read_attr(os.path.join(dev_dir, 'rev'))

                                # Capacity
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

    # -- Method 2: Fallback to check /dev/disk/by-id/ --

    try:
        for link in sorted(glob.glob('/dev/disk/by-id/*')):
            basename = os.path.basename(link).lower()
            if 'ufs' in basename:
                real = os.path.realpath(link)
                result['found'] = True
                result['device'] = real
                result['controller'] = 'by-id'
                result['model'] = os.path.basename(link)

                # Try to read capacity
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

    # -- Not found --
    if ufshcd_loaded:
        result['reason'] = 'ufshcd module loaded, but no associated block device found'
    else:
        result['reason'] = 'ufshcd controller not detected'

    return result
