#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
UFS 设备模拟器 - UFS Device Simulator

在没有实际 UFS 硬件的情况下，提供：
- 块设备模拟（使用文件/loop device）
- 性能指标模拟（基于 UFS 3.1 规格）
- 健康状态模拟
- 错误注入测试

Usage:
    # 创建模拟设备
    python3 tools/ufs_simulator.py create --size=128G
    
    # 运行模拟测试
    python3 tools/ufs_simulator.py run --suite=performance
"""

import os
import json
import random
import logging
import subprocess
from pathlib import Path
from typing import Dict, Any, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class UFSDeviceConfig:
    """UFS 设备配置（基于 UFS 3.1 规格）"""
    # 设备信息
    model: str = "UFS 3.1 128GB"
    capacity_gb: int = 128
    ufs_version: str = "3.1"
    manufacturer: str = "Simulated"
    
    # 性能规格（UFS 3.1 典型值）
    seq_read_mbps: int = 2100
    seq_write_mbps: int = 1650
    rand_read_iops: int = 200000
    rand_write_iops: int = 330000
    mixed_rw_iops: int = 150000
    
    # 延迟规格（μs）
    read_latency_us: int = 80
    write_latency_us: int = 120
    
    # 健康状态
    health_status: str = "OK"
    pre_eol_info: str = "0x00"
    device_life_time: str = "0x01"


class UFSSimulator:
    """UFS 设备模拟器"""
    
    def __init__(self, device_path: str = '/tmp/ufs_sim.img', config: Optional[UFSDeviceConfig] = None, logger=None):
        """
        初始化 UFS 模拟器
        
        Args:
            device_path: 模拟设备文件路径
            config: 设备配置
            logger: 日志记录器
        """
        self.device_path = device_path
        self.config = config or UFSDeviceConfig()
        self.logger = logger or logging.getLogger(__name__)
        self.initialized = False
    
    def create_device(self, size_gb: int = 128) -> bool:
        """
        创建模拟设备文件
        
        Args:
            size_gb: 设备大小（GB）
        
        Returns:
            bool: 成功返回 True
        """
        self.logger.info(f"创建模拟 UFS 设备：{self.device_path} ({size_gb}GB)")
        
        try:
            # 创建稀疏文件（不实际占用空间）
            size_bytes = size_gb * 1024 * 1024 * 1024
            
            with open(self.device_path, 'wb') as f:
                f.seek(size_bytes - 1)
                f.write(b'\x00')
            
            self.logger.info(f"✅ 模拟设备创建成功：{size_gb}GB")
            self.initialized = True
            return True
            
        except Exception as e:
            self.logger.error(f"创建模拟设备失败：{e}")
            return False
    
    def setup_loop_device(self) -> Optional[str]:
        """
        设置 loop 设备
        
        Returns:
            str: loop 设备路径（如/dev/loop0），失败返回 None
        """
        self.logger.info("设置 loop 设备...")
        
        try:
            # 查找空闲 loop 设备
            result = subprocess.run(
                ['losetup', '-f'],
                capture_output=True,
                text=True
            )
            
            if result.returncode != 0:
                self.logger.error("无法找到空闲 loop 设备")
                return None
            
            loop_device = result.stdout.strip()
            
            # 关联文件到 loop 设备
            result = subprocess.run(
                ['losetup', loop_device, self.device_path],
                capture_output=True,
                text=True
            )
            
            if result.returncode != 0:
                self.logger.error(f"关联 loop 设备失败：{result.stderr}")
                return None
            
            self.logger.info(f"✅ Loop 设备已设置：{loop_device}")
            return loop_device
            
        except Exception as e:
            self.logger.error(f"设置 loop 设备失败：{e}")
            return None
    
    def cleanup_loop_device(self, loop_device: str) -> bool:
        """
        清理 loop 设备
        
        Args:
            loop_device: loop 设备路径
        
        Returns:
            bool: 成功返回 True
        """
        try:
            subprocess.run(['losetup', '-d', loop_device], check=True)
            self.logger.info(f"✅ Loop 设备已清理：{loop_device}")
            return True
        except Exception as e:
            self.logger.error(f"清理 loop 设备失败：{e}")
            return False
    
    def get_device_info(self) -> Dict[str, Any]:
        """获取模拟设备信息"""
        return {
            'device_path': self.device_path,
            'model': self.config.model,
            'capacity_gb': self.config.capacity_gb,
            'ufs_version': self.config.ufs_version,
            'manufacturer': self.config.manufacturer,
            'simulated': True
        }
    
    def get_health_status(self) -> Dict[str, Any]:
        """获取模拟健康状态"""
        return {
            'status': self.config.health_status,
            'pre_eol_info': self.config.pre_eol_info,
            'device_life_time_est_a': self.config.device_life_time,
            'device_life_time_est_b': self.config.device_life_time,
            'critical_warning': 0,
            'simulated': True
        }
    
    def simulate_performance(self, test_type: str) -> Dict[str, Any]:
        """
        模拟性能测试结果
        
        Args:
            test_type: 测试类型（seq_read, seq_write, rand_read, rand_write, mixed_rw）
        
        Returns:
            Dict: 性能指标
        """
        self.logger.info(f"模拟性能测试：{test_type}")
        
        # 添加 ±5% 的随机波动，模拟真实环境
        variance = lambda x: x * (1 + random.uniform(-0.05, 0.05))
        
        if test_type == 'seq_read':
            bandwidth = variance(self.config.seq_read_mbps)
            return {
                'bandwidth': {'value': bandwidth, 'unit': 'MB/s'},
                'iops': {'value': bandwidth * 8, 'unit': 'IOPS'},  # 128K block
                'latency_ns': {
                    'mean': self.config.read_latency_us * 1000,
                    'stddev': self.config.read_latency_us * 100,
                    'min': self.config.read_latency_us * 500,
                    'max': self.config.read_latency_us * 3000,
                    'percentile': {
                        '50.000000': self.config.read_latency_us * 1000,
                        '90.000000': self.config.read_latency_us * 1500,
                        '99.000000': self.config.read_latency_us * 2000,
                        '99.990000': self.config.read_latency_us * 3000,
                        '99.999000': self.config.read_latency_us * 5000
                    }
                }
            }
        
        elif test_type == 'seq_write':
            bandwidth = variance(self.config.seq_write_mbps)
            return {
                'bandwidth': {'value': bandwidth, 'unit': 'MB/s'},
                'iops': {'value': bandwidth * 8, 'unit': 'IOPS'},
                'latency_ns': {
                    'mean': self.config.write_latency_us * 1000,
                    'stddev': self.config.write_latency_us * 150,
                    'min': self.config.write_latency_us * 500,
                    'max': self.config.write_latency_us * 4000,
                    'percentile': {
                        '50.000000': self.config.write_latency_us * 1000,
                        '90.000000': self.config.write_latency_us * 1500,
                        '99.000000': self.config.write_latency_us * 2500,
                        '99.990000': self.config.write_latency_us * 4000,
                        '99.999000': self.config.write_latency_us * 6000
                    }
                }
            }
        
        elif test_type == 'rand_read':
            iops = variance(self.config.rand_read_iops)
            return {
                'iops': {'value': iops, 'unit': 'IOPS'},
                'bandwidth': {'value': iops * 4 / 1024, 'unit': 'MB/s'},  # 4K block
                'latency_ns': {
                    'mean': self.config.read_latency_us * 1000,
                    'stddev': self.config.read_latency_us * 200,
                    'min': self.config.read_latency_us * 300,
                    'max': self.config.read_latency_us * 5000,
                    'percentile': {
                        '50.000000': self.config.read_latency_us * 800,
                        '90.000000': self.config.read_latency_us * 1500,
                        '99.000000': self.config.read_latency_us * 3000,
                        '99.990000': self.config.read_latency_us * 8000,
                        '99.999000': self.config.read_latency_us * 12000
                    }
                }
            }
        
        elif test_type == 'rand_write':
            iops = variance(self.config.rand_write_iops)
            return {
                'iops': {'value': iops, 'unit': 'IOPS'},
                'bandwidth': {'value': iops * 4 / 1024, 'unit': 'MB/s'},
                'latency_ns': {
                    'mean': self.config.write_latency_us * 1000,
                    'stddev': self.config.write_latency_us * 250,
                    'min': self.config.write_latency_us * 400,
                    'max': self.config.write_latency_us * 6000,
                    'percentile': {
                        '50.000000': self.config.write_latency_us * 800,
                        '90.000000': self.config.write_latency_us * 1800,
                        '99.000000': self.config.write_latency_us * 3500,
                        '99.990000': self.config.write_latency_us * 9000,
                        '99.999000': self.config.write_latency_us * 15000
                    }
                }
            }
        
        elif test_type == 'mixed_rw':
            iops = variance(self.config.mixed_rw_iops)
            return {
                'total_iops': {'value': iops, 'unit': 'IOPS'},
                'read_iops': {'value': iops * 0.7, 'unit': 'IOPS'},
                'write_iops': {'value': iops * 0.3, 'unit': 'IOPS'},
                'bandwidth': {'value': iops * 4 / 1024, 'unit': 'MB/s'},
                'latency_ns': {
                    'mean': (self.config.read_latency_us * 0.7 + self.config.write_latency_us * 0.3) * 1000,
                    'stddev': 150000,
                    'min': 2000000,
                    'max': 8000000,
                    'percentile': {}
                }
            }
        
        else:
            return {}
    
    def check_available_space(self, min_gb: float = 2.0) -> bool:
        """检查可用空间"""
        try:
            stat = os.statvfs(os.path.dirname(self.device_path) or '.')
            available_gb = (stat.f_bavail * stat.f_frsize) / (1024 ** 3)
            return available_gb >= min_gb
        except Exception as e:
            self.logger.error(f"检查空间失败：{e}")
            return False
    
    def flush_cache(self) -> bool:
        """刷新缓存"""
        try:
            os.sync()
            return True
        except Exception as e:
            self.logger.error(f"刷新缓存失败：{e}")
            return False


# 便捷函数
def create_simulated_ufs(size_gb: int = 128, logger=None) -> UFSSimulator:
    """创建模拟 UFS 设备"""
    sim = UFSSimulator(logger=logger)
    sim.create_device(size_gb)
    return sim


def get_mock_fio_results(test_type: str, logger=None) -> Dict[str, Any]:
    """获取模拟 FIO 测试结果（用于 dry-run 模式）"""
    sim = UFSSimulator(logger=logger)
    return sim.simulate_performance(test_type)
