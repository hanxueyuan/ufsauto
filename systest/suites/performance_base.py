#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
性能测试基类 - 消除重复代码
"""

import subprocess
from pathlib import Path
from typing import Dict, Any

from runner import TestCase
from fio_wrapper import FIO, FIOConfig
from ufs_utils import UFSDevice


class PerformanceTestCase(TestCase):
    """性能测试基类
    
    提供通用的：
    - 前置条件检查（设备、空间、FIO、权限）
    - FIO 测试执行
    - 性能指标验证
    - Postcondition 检查
    """
    
    # 子类必须定义的属性
    name: str = "base_performance_test"
    description: str = "性能测试基类"
    
    # 性能目标（子类覆盖）
    target_bandwidth_mbps: float = 0
    target_iops: float = 0
    max_avg_latency_us: float = float('inf')
    max_tail_latency_us: float = float('inf')
    
    # FIO 配置（子类覆盖）
    fio_rw: str = 'read'
    fio_bs: str = '4k'
    fio_size: str = '1G'
    fio_runtime: int = 60
    fio_iodepth: int = 1
    fio_ramp_time: int = 0
    
    def __init__(self, device: str = '/dev/sda', test_dir: Path = None, verbose: bool = False, logger=None):
        super().__init__(device, test_dir, verbose, logger)
        self.fio = FIO(timeout=self.fio_runtime + self.fio_ramp_time + 30, logger=self.logger)
        self.ufs = UFSDevice(device, logger=self.logger)
    
    def setup(self) -> bool:
        """通用前置条件检查"""
        self.logger.info("开始检查前置条件...")
        
        # 1. 检查设备存在
        if not self.ufs.exists():
            self.logger.error(f"设备不存在：{self.device}")
            return False
        self.logger.debug(f"📊 设备存在：{self.device}")
        
        # 2. 检查可用空间
        if not self.ufs.check_available_space(min_gb=2.0):
            self.logger.error("可用空间不足（需要≥2GB）")
            return False
        self.logger.debug(f"📊 可用空间充足（≥2GB）")
        
        # 3. 检查 FIO 已安装
        try:
            result = subprocess.run(['which', 'fio'], capture_output=True)
            if result.returncode != 0:
                self.logger.error("FIO 工具未安装")
                return False
            self.logger.debug(f"📊 FIO 已安装")
        except Exception as e:
            self.logger.error(f"检查 FIO 失败：{e}")
            return False
        
        # 4. 检查设备权限
        if not self.ufs.check_device():
            self.logger.error(f"设备权限不足：{self.device}")
            return False
        self.logger.debug(f"📊 设备权限正常")
        
        # 5. 记录测试配置
        self.logger.info(f"📋 测试配置:")
        self.logger.info(f"  bs={self.fio_bs}, size={self.fio_size}, runtime={self.fio_runtime}s")
        self.logger.info(f"  iodepth={self.fio_iodepth}, rw={self.fio_rw}, ramp_time={self.fio_ramp_time}s")
        
        self.logger.info("✅ 前置条件检查通过")
        return True
    
    def execute_fio_test(self, extra_config: dict = None) -> Dict[str, Any]:
        """
        通用 FIO 测试执行
        
        Args:
            extra_config: 额外的 FIO 配置参数
        
        Returns:
            性能指标字典
        """
        self.logger.info(f"🚀 开始执行性能测试...")
        
        # 构建 FIO 配置
        fio_config = {
            'filename': self.get_test_file_path(self.name),
            'rw': self.fio_rw,
            'bs': self.fio_bs,
            'size': self.fio_size,
            'runtime': self.fio_runtime,
            'ioengine': 'sync',
            'iodepth': self.fio_iodepth,
            'direct': True,
            'time_based': True,
        }
        
        # 添加 ramp_time（如果有）
        if self.fio_ramp_time > 0:
            fio_config['ramp_time'] = self.fio_ramp_time
        
        # 合并额外配置
        if extra_config:
            fio_config.update(extra_config)
        
        try:
            # 执行 FIO 测试
            metrics_obj = self.fio.run(FIOConfig(**fio_config))
            
            # 提取指标
            job_data = metrics_obj.raw.get('jobs', [{}])[0]
            io_type = 'read' if 'read' in self.fio_rw else 'write'
            io_stats = job_data.get(io_type, {})
            
            # 带宽和 IOPS
            bandwidth_mbps = io_stats.get('bw_bytes', 0) / (1024 * 1024)
            iops = io_stats.get('iops', 0)
            
            # 延迟
            lat_ns = io_stats.get('lat_ns', {})
            avg_latency_us = lat_ns.get('mean', 0) / 1000
            percentiles = lat_ns.get('percentile', {})
            p99999_latency_us = percentiles.get('99.999', 0) / 1000
            
            return {
                'bandwidth_mbps': bandwidth_mbps,
                'iops': iops,
                'avg_latency_us': avg_latency_us,
                'p99999_latency_us': p99999_latency_us,
                'metrics_obj': metrics_obj,
            }
            
        except FIOError as e:
            self.logger.error(f"FIO 测试失败：{e}")
            return {'error': str(e)}
    
    def validate_performance(self, metrics: Dict[str, Any]) -> bool:
        """
        通用性能验证
        
        Args:
            metrics: 性能指标字典
        
        Returns:
            bool: 验证是否通过
        """
        if 'error' in metrics:
            self.record_failure(
                "FIO 执行",
                "成功完成",
                f"执行失败：{metrics['error']}",
                "FIO 执行失败"
            )
            return True
        
        # 带宽验证
        if self.target_bandwidth_mbps > 0:
            bw = metrics.get('bandwidth_mbps', 0)
            if bw >= self.target_bandwidth_mbps:
                self.logger.info(f"✅ 带宽：{bw:.1f} MB/s ≥ {self.target_bandwidth_mbps} MB/s")
            else:
                self.record_failure(
                    "带宽性能",
                    f"≥ {self.target_bandwidth_mbps} MB/s",
                    f"{bw:.1f} MB/s",
                    "带宽性能不达标"
                )
        
        # IOPS 验证
        if self.target_iops > 0:
            iops = metrics.get('iops', 0)
            if iops >= self.target_iops:
                self.logger.info(f"✅ IOPS: {iops:.0f} ≥ {self.target_iops}")
            else:
                self.record_failure(
                    "IOPS 性能",
                    f"≥ {self.target_iops}",
                    f"{iops:.0f}",
                    "IOPS 性能不达标"
                )
        
        # 平均延迟验证
        if self.max_avg_latency_us < float('inf'):
            lat = metrics.get('avg_latency_us', float('inf'))
            if lat <= self.max_avg_latency_us:
                self.logger.info(f"✅ 平均延迟：{lat:.1f}μs ≤ {self.max_avg_latency_us}μs")
            else:
                self.record_failure(
                    "平均延迟",
                    f"≤ {self.max_avg_latency_us}μs",
                    f"{lat:.1f}μs",
                    "平均延迟超出预期"
                )
        
        # 尾部延迟验证
        if self.max_tail_latency_us < float('inf'):
            tail_lat = metrics.get('p99999_latency_us', float('inf'))
            if tail_lat <= self.max_tail_latency_us:
                self.logger.info(f"✅ 尾部延迟 (p99.999): {tail_lat:.0f}μs ≤ {self.max_tail_latency_us}μs")
            else:
                self.record_failure(
                    "尾部延迟 (p99.999)",
                    f"≤ {self.max_tail_latency_us}μs",
                    f"{tail_lat:.0f}μs",
                    "尾部延迟超出预期"
                )
        
        # 执行 Postcondition 检查
        self._check_postcondition()
        
        return True
    
    def execute(self) -> Dict[str, Any]:
        """执行测试逻辑 - 子类通常不需要覆盖"""
        return self.execute_fio_test()
    
    def validate(self, result: Dict[str, Any]) -> bool:
        """验证结果 - 子类通常不需要覆盖"""
        return self.validate_performance(result)
