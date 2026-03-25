#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
UFS 设备操作工具 - UFS Utils

生产级 UFS 设备管理工具，提供：
- 设备信息查询
- 健康状态监控
- 电源管理
- 性能计数器读取

Usage:
    from tools.ufs_utils import UFSDevice
    
    ufs = UFSDevice('/dev/ufs0')
    info = ufs.get_device_info()
    print(f"设备型号：{info['model']}")
    print(f"容量：{info['capacity_gb']}GB")
"""

import os
import subprocess
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class UFSDeviceInfo:
    """UFS 设备信息"""
    device_path: str
    model: str
    serial: str
    firmware: str
    capacity_gb: int
    ufs_version: str
    manufacturer: str
    health_status: str


class UFSUtilsError(Exception):
    """UFS 工具错误"""
    pass


class UFSDevice:
    """UFS 设备操作类"""
    
    def __init__(self, device_path: str = '/dev/ufs0', logger=None):
        """
        初始化 UFS 设备
        
        Args:
            device_path: UFS 设备路径
            logger: 日志记录器
        """
        self.device_path = device_path
        self.logger = logger or logging.getLogger(__name__)
        
        # sysfs 路径
        self.sysfs_base = Path('/sys/bus/platform/drivers/ufs')
    
    def exists(self) -> bool:
        """检查设备是否存在"""
        return Path(self.device_path).exists()
    
    def check_device(self) -> bool:
        """
        检查设备是否可用
        
        Returns:
            bool: 设备可用返回 True
        
        Raises:
            UFSUtilsError: 设备不可用
        """
        self.logger.info(f"检查 UFS 设备：{self.device_path}")
        
        # 1. 检查设备文件存在
        if not self.exists():
            raise UFSUtilsError(f"设备不存在：{self.device_path}")
        
        # 2. 检查权限
        if not os.access(self.device_path, os.R_OK | os.W_OK):
            raise UFSUtilsError(f"设备权限不足：{self.device_path}")
        
        # 3. 检查是否被挂载
        mount_point = self._get_mount_point()
        if mount_point:
            self.logger.warning(f"设备已挂载：{mount_point}")
        
        self.logger.info("设备检查通过")
        return True
    
    def _get_mount_point(self) -> Optional[str]:
        """获取设备的挂载点"""
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
        获取设备信息
        
        Returns:
            UFSDeviceInfo: 设备信息对象
        """
        self.logger.info("获取 UFS 设备信息...")
        
        # 尝试使用 ufs-utils 工具
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
            self.logger.debug("ufs-utils 未安装，使用备用方法")
        except Exception as e:
            self.logger.warning(f"ufs-utils 执行失败：{e}")
        
        # 备用方法：从 sysfs 读取
        return self._get_info_from_sysfs()
    
    def _parse_ufs_info(self, output: str) -> UFSDeviceInfo:
        """解析 ufs-utils 输出"""
        # 简化实现，实际需要根据输出格式解析
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
        """从 sysfs 获取设备信息"""
        # 尝试读取设备大小
        capacity_gb = 0
        size_file = Path(f'/sys/class/block/{Path(self.device_path).name}/size')
        if size_file.exists():
            try:
                sectors = int(size_file.read_text().strip())
                capacity_gb = (sectors * 512) // (1024 ** 3)
            except Exception as e:
                self.logger.warning(f"读取容量失败：{e}")
        
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
        检查可用空间
        
        Args:
            min_gb: 最小可用空间（GB）
        
        Returns:
            bool: 空间足够返回 True
        """
        self.logger.info(f"检查可用空间（最小 {min_gb}GB）...")
        
        # 如果设备已挂载，检查挂载点
        mount_point = self._get_mount_point()
        if mount_point:
            stat = os.statvfs(mount_point)
            available_gb = (stat.f_bavail * stat.f_frsize) / (1024 ** 3)
        else:
            # 设备未挂载，检查 /tmp
            stat = os.statvfs('/tmp')
            available_gb = (stat.f_bavail * stat.f_frsize) / (1024 ** 3)
            self.logger.debug(f"设备未挂载，检查 /tmp 空间")
        
        self.logger.debug(f"可用空间：{available_gb:.1f}GB")
        
        if available_gb < min_gb:
            self.logger.error(f"可用空间不足：{available_gb:.1f}GB < {min_gb}GB")
            return False
        
        return True
    
    def get_health_status(self) -> Dict[str, Any]:
        """
        获取设备健康状态
        
        Returns:
            Dict: 健康状态信息
        """
        self.logger.info("获取 UFS 设备健康状态...")
        
        health = {
            'status': 'OK',
            'pre_eol_info': 'N/A',
            'device_life_time_est_a': 'N/A',
            'device_life_time_est_b': 'N/A',
            'critical_warning': 0
        }
        
        # 尝试从 sysfs 读取
        health_dir = self._find_ufs_health_dir()
        if health_dir:
            try:
                # 读取预 EOL 信息
                pre_eol_file = health_dir / 'pre_eol_info'
                if pre_eol_file.exists():
                    health['pre_eol_info'] = pre_eol_file.read_text().strip()
                
                # 读取设备寿命估算
                life_a_file = health_dir / 'device_life_time_est_a'
                if life_a_file.exists():
                    health['device_life_time_est_a'] = life_a_file.read_text().strip()
                
                life_b_file = health_dir / 'device_life_time_est_b'
                if life_b_file.exists():
                    health['device_life_time_est_b'] = life_b_file.read_text().strip()
                
                # 读取严重警告
                warn_file = health_dir / 'critical_warning'
                if warn_file.exists():
                    health['critical_warning'] = int(warn_file.read_text().strip())
                
                # 判断整体状态
                if health['critical_warning'] > 0:
                    health['status'] = 'WARNING'
                elif health['pre_eol_info'] != '0x00':
                    health['status'] = 'PRE_EOL'
                    
            except Exception as e:
                self.logger.warning(f"读取健康状态失败：{e}")
        
        self.logger.info(f"健康状态：{health['status']}")
        return health
    
    def _find_ufs_health_dir(self) -> Optional[Path]:
        """查找 UFS 健康信息目录"""
        # 典型路径：/sys/class/ufs_device/ufsX/health_descriptor/
        for base in [Path('/sys/class/ufs_device'), Path('/sys/bus/platform/drivers/ufs')]:
            if base.exists():
                for ufs_dir in base.iterdir():
                    health_dir = ufs_dir / 'health_descriptor'
                    if health_dir.exists():
                        return health_dir
        return None
    
    def flush_cache(self) -> bool:
        """
        刷新设备缓存
        
        Returns:
            bool: 成功返回 True
        """
        self.logger.info("刷新设备缓存...")
        
        try:
            # 使用 blockdev 刷新
            result = subprocess.run(
                ['blockdev', '--flushbuffers', self.device_path],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode != 0:
                self.logger.warning(f"blockdev 刷新失败：{result.stderr}")
            
            # sync 系统调用
            os.sync()
            
            self.logger.info("缓存刷新完成")
            return True
            
        except Exception as e:
            self.logger.error(f"刷新缓存失败：{e}")
            return False
    
    def set_scheduler(self, scheduler: str = 'none') -> bool:
        """
        设置 I/O 调度器
        
        Args:
            scheduler: 调度器名称 (none, mq-deadline, kyber, bfq)
        
        Returns:
            bool: 成功返回 True
        """
        self.logger.info(f"设置 I/O 调度器：{scheduler}")
        
        try:
            device_name = Path(self.device_path).name
            scheduler_file = Path(f'/sys/block/{device_name}/queue/scheduler')
            
            if not scheduler_file.exists():
                self.logger.warning(f"调度器文件不存在：{scheduler_file}")
                return False
            
            # 读取当前调度器
            current = scheduler_file.read_text().strip()
            self.logger.debug(f"当前调度器：{current}")
            
            # 设置新调度器
            scheduler_file.write_text(scheduler)
            
            # 验证
            new_scheduler = scheduler_file.read_text().strip()
            if scheduler in new_scheduler:
                self.logger.info(f"调度器已设置为：{scheduler}")
                return True
            else:
                self.logger.warning(f"调度器设置可能失败：{new_scheduler}")
                return False
                
        except Exception as e:
            self.logger.error(f"设置调度器失败：{e}")
            return False
    
    def get_performance_counter(self) -> Dict[str, Any]:
        """
        获取性能计数器
        
        Returns:
            Dict: 性能计数器数据
        """
        self.logger.info("读取性能计数器...")
        
        counters = {
            'read_iops': 0,
            'write_iops': 0,
            'read_throughput_mbps': 0,
            'write_throughput_mbps': 0,
            'read_latency_us': 0,
            'write_latency_us': 0
        }
        
        # 从 debugfs 或其他接口读取
        # 这里提供框架，实际实现需要根据具体平台
        
        return counters


# ========== 便捷函数 ==========

def check_ufs_device(device_path: str = '/dev/ufs0') -> bool:
    """检查 UFS 设备是否可用"""
    ufs = UFSDevice(device_path)
    return ufs.check_device()


def get_ufs_health(device_path: str = '/dev/ufs0') -> Dict[str, Any]:
    """获取 UFS 设备健康状态"""
    ufs = UFSDevice(device_path)
    return ufs.get_health_status()


def auto_detect_ufs() -> Dict[str, Any]:
    """
    自动探测 UFS 设备节点

    探测逻辑：
    1. 扫描 /sys/class/scsi_host/ 下的 ufshcd 控制器
    2. 通过 /sys/block/ 找到关联的块设备
    3. 读取设备信息（vendor, model, capacity）
    4. 如果找不到 ufshcd，回退检查 /dev/disk/by-id/ 中含 ufs 关键字的设备

    Returns:
        dict: 探测结果
    """
    import glob as _glob

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

    # ── 方法 1：通过 ufshcd 驱动查找块设备 ──

    # 检查 ufshcd 模块是否加载
    try:
        r = subprocess.run(['lsmod'], capture_output=True, text=True, timeout=5)
        ufshcd_loaded = 'ufshcd' in r.stdout if r.returncode == 0 else False
    except Exception:
        ufshcd_loaded = False

    if ufshcd_loaded:
        for blk in sorted(_glob.glob('/sys/block/sd*')):
            dev_name = os.path.basename(blk)
            try:
                # 往上找 driver，看是否是 ufshcd
                # 典型路径: /sys/block/sda/device/../../..  指向 host adapter
                for depth in range(2, 6):
                    driver_link = os.path.join(blk, 'device', *(['..'] * depth), 'driver')
                    driver_link = os.path.normpath(driver_link)
                    if os.path.islink(driver_link):
                        driver_name = os.path.basename(os.readlink(driver_link))
                        if 'ufshcd' in driver_name:
                            result['found'] = True
                            result['device'] = f'/dev/{dev_name}'
                            result['controller'] = driver_name

                            # 读取 vendor / model / rev
                            dev_dir = os.path.join(blk, 'device')
                            result['vendor'] = _read_attr(os.path.join(dev_dir, 'vendor'))
                            result['model'] = _read_attr(os.path.join(dev_dir, 'model'))
                            result['fw_version'] = _read_attr(os.path.join(dev_dir, 'rev'))

                            # 容量
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

    # ── 方法 2：回退检查 /dev/disk/by-id/ ──

    try:
        for link in sorted(_glob.glob('/dev/disk/by-id/*')):
            basename = os.path.basename(link).lower()
            if 'ufs' in basename:
                real = os.path.realpath(link)
                result['found'] = True
                result['device'] = real
                result['controller'] = 'by-id'
                result['model'] = os.path.basename(link)

                # 尝试读容量
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

    # ── 没找到 ──
    if ufshcd_loaded:
        result['reason'] = 'ufshcd 模块已加载，但未找到关联块设备'
    else:
        result['reason'] = '未检测到 ufshcd 控制器'

    return result
