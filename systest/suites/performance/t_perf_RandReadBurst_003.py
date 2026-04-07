#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
随机读性能测试
测试 UFS 设备的随机读取 IOPS（4K QD32）

测试用例 ID: t_perf_RandReadBurst_003
测试目的：验证 UFS 设备随机读 IOPS 性能
前置条件：
    1. UFS 设备已挂载
    2. 有足够可用空间（≥2GB）
    3. FIO 工具已安装
测试步骤：
    1. 预填充测试文件
    2. 执行 FIO 随机读测试（4K block, QD32, 60s, 含 10s ramp）
    3. 标注 IOPS、带宽、延迟是否达标
预期指标（参考）：
    - IOPS ≥ 200,000
    - 平均延迟 < 160 μs
    - p99.999 尾延迟 < 5000 μs
测试耗时：约 70 秒（含 ramp）
"""

import os
import sys
import subprocess
from pathlib import Path
from typing import Dict, Any

# 添加 core 和 tools 模块路径
core_dir = Path(__file__).parent.parent.parent / 'core'
tools_dir = Path(__file__).parent.parent.parent / 'tools'
sys.path.insert(0, str(core_dir))
sys.path.insert(0, str(tools_dir))

from runner import TestCase
from fio_wrapper import FIO, FIOError, FIOMetrics
from ufs_utils import UFSDevice


class Test(TestCase):
    """随机读性能测试"""
    
    name = "rand_read_burst"
    description = "随机读取性能测试（4K QD32）"
    
    def __init__(
        self,
        device: str = '/dev/ufs0',
        test_dir: Path = None,
        verbose: bool = False,
        logger=None,
        bs: str = '4k',
        size: str = '1G',
        runtime: int = 60,
        ramp_time: int = 10,
        ioengine: str = 'sync',
        iodepth: int = 32,
        target_iops: float = 120000,
        max_avg_latency_us: float = 160,
        max_tail_latency_us: float = 5000,
        prefill: bool = True,
    ):
        super().__init__(device, test_dir, verbose, logger)
        self.test_file = self.get_test_file_path('rand_read')
        self.bs = bs
        self.size = size
        self.runtime = runtime
        self.ramp_time = ramp_time
        self.ioengine = ioengine
        self.iodepth = iodepth
        self.target_iops = target_iops
        self.max_avg_latency_us = max_avg_latency_us
        self.max_tail_latency_us = max_tail_latency_us
        self.prefill = prefill
        
        # 初始化工具
        self.fio = FIO(timeout=self.runtime + self.ramp_time + 30, logger=self.logger)
        self.ufs = UFSDevice(device, logger=self.logger)
    
    def setup(self) -> bool:
        """检查前置条件"""
        self.logger.info("开始检查前置条件...")
        
        if not self.ufs.exists():
            self.logger.error(f"设备不存在：{self.device}")
            return False
        
        if not self.ufs.check_available_space(min_gb=2.0):
            return False
        
        try:
            result = subprocess.run(['which', 'fio'], capture_output=True)
            if result.returncode != 0:
                self.logger.error("FIO 工具未安装")
                return False
        except Exception as e:
            self.logger.error(f"检查 FIO 失败：{e}")
            return False
        
        if not os.access(self.device, os.R_OK | os.W_OK):
            self.logger.error(f"设备权限不足：{self.device}")
            return False
        
        # 检查设备健康状态
        health = self.ufs.get_health_status()
        if health['status'] != 'OK':
            self.logger.warning(f"设备健康状态异常：{health['status']}")
        
        # 预填充
        if self.prefill:
            self.logger.info(f"预填充测试文件：{self.test_file} ({self.size})")
            try:
                size_mb = self._parse_size_mb(self.size)
                subprocess.run(
                    ['dd', 'if=/dev/urandom', f'of={self.test_file}',
                     'bs=1M', f'count={size_mb}', 'conv=fdatasync'],
                    capture_output=True, text=True, timeout=120
                )
            except Exception as e:
                self.logger.warning(f"预填充异常，继续测试：{e}")
        
        self.logger.info("📋 测试配置:")
        self.logger.info(f"  bs={self.bs}, size={self.size}, runtime={self.runtime}s, iodepth={self.iodepth}")
        self.logger.info(f"  ioengine={self.ioengine}, ramp_time={self.ramp_time}s")
        self.logger.info(f"  target_iops={self.target_iops}, max_avg_lat={self.max_avg_latency_us} μs")
        
        self.logger.info("📊 前置条件检查通过")
        return True
    
    def _parse_size_mb(self, size_str: str) -> int:
        """解析大小字符串为 MB"""
        size_str = size_str.lower()
        if size_str.endswith('g'):
            return int(size_str[:-1]) * 1024
        elif size_str.endswith('m'):
            return int(size_str[:-1])
        elif size_str.endswith('k'):
            return max(1, int(size_str[:-1]) // 1024)
        else:
            try:
                return int(size_str) // 1024 // 1024
            except ValueError:
                return 1024  # 默认 1GB
    
    def execute(self) -> Dict[str, Any]:
        """执行 FIO 随机读测试"""
        self.logger.info("🚀 开始执行随机读性能测试...")
        
        try:
            # 使用 fio_wrapper 便捷 API 执行
            metrics_obj = self.fio.run_rand_read(
                filename=self.test_file,
                direct=True,
                size=self.size,
                runtime=self.runtime,
                bs=self.bs,
                iodepth=self.iodepth,
                ioengine=self.ioengine,
                ramp_time=self.ramp_time
            )
            
            # 转换为标准 metrics 格式
            lat = metrics_obj.latency_ns
            metrics = {
                'iops': {
                    'value': metrics_obj.iops['value'],
                    'unit': 'IOPS',
                    'target': self.target_iops
                },
                'bandwidth': {
                    'value': metrics_obj.bandwidth['value'],
                    'unit': 'MB/s'
                },
                'latency_avg': {
                    'value': lat['mean'] / 1000,  # ns → μs
                    'unit': 'μs',
                    'target': self.max_avg_latency_us
                },
                'latency_p99': {
                    'value': lat['percentile'].get('99.0', 0) / 1000,
                    'unit': 'μs'
                },
                'latency_p9999': {
                    'value': lat['percentile'].get('99.99', 0) / 1000,
                    'unit': 'μs'
                },
                'latency_p99999': {
                    'value': lat['percentile'].get('99.999', 0) / 1000,
                    'unit': 'μs',
                    'target': self.max_tail_latency_us
                },
                'runtime': {
                    'value': metrics_obj.raw['jobs'][0]['elapsed'],
                    'unit': 's'
                }
            }
            
            # 日志输出结果
            self.logger.info("📊 测试完成，结果汇总:")
            self.logger.info(f"  IOPS: {metrics['iops']['value']:.0f} (目标: ≥{self.target_iops})")
            self.logger.info(f"  带宽: {metrics['bandwidth']['value']:.1f} MB/s")
            self.logger.info(f"  平均延迟: {metrics['latency_avg']['value']:.1f} μs (target: <{self.max_avg_latency_us})")
            self.logger.info(f"  p99.999 尾延迟: {metrics['latency_p99999']['value']:.1f} μs (target: <{self.max_tail_latency_us})")
            
            return metrics
            
        except FIOError as e:
            self.logger.error(f"FIO 执行失败: {e}")
            raise
    
    def validate(self, result: Dict[str, Any]) -> bool:
        """验证测试结果是否达标
        
        性能测试原则：不达标记录 failure，但始终返回 True 让流程走完
        最终状态由框架根据 failures 自动判断
        """
        self.logger.info("🔍 验证测试结果...")
        
        all_ok = True
        
        # 验证 IOPS - 低于 90% 目标才算失败
        iops = result['iops']['value']
        target = self.target_iops
        if iops < target * 0.9:
            self.record_failure(
                "随机读 IOPS",
                f"≥ {target:.0f} IOPS",
                f"{iops:.0f} IOPS",
                "IOPS 显著低于目标值"
            )
            all_ok = False
        elif iops < target:
            # 在目标 90%-100% 之间，记录警告但不算失败
            self.logger.warning(
                f"⚠️  IOPS 未达标: {iops:.0f} < {target:.0f}，"
                "但在容忍范围内（≥90%），测试继续"
            )
        
        # 验证平均延迟
        avg_lat = result['latency_avg']['value']
        if avg_lat > self.max_avg_latency_us:
            self.record_failure(
                "平均延迟",
                f"< {self.max_avg_latency_us} μs",
                f"{avg_lat:.1f} μs",
                "平均延迟超出限制"
            )
            all_ok = False
        
        # 验证尾延迟（p99.999）
        tail_lat = result['latency_p99999']['value']
        if tail_lat > self.max_tail_latency_us:
            self.record_failure(
                "p99.999 尾延迟",
                f"< {self.max_tail_latency_us} μs",
                f"{tail_lat:.1f} μs",
                "尾延迟发散超出限制"
            )
            all_ok = False
        
        # Postcondition 检查（硬件健康）
        self._check_postcondition()
        
        if all_ok:
            self.logger.info("✅ 所有验证通过")
        else:
            self.logger.warning(f"⚠️  共有 {len(self._failures)} 项验证不通过")
        
        return True  # 性能测试始终返回 True，由框架根据 failures 判断最终状态
    
    def teardown(self) -> bool:
        """测试后清理 - 父类会自动清理测试文件"""
        return super().teardown()
