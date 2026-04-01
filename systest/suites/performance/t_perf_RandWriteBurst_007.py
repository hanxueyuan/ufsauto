#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
随机写性能测试
测试 UFS 设备的随机写入 IOPS（4K QD32）

测试用例 ID: t_perf_RandWriteBurst_007
测试目的：验证 UFS 设备随机写 IOPS 性能
前置条件：
    1. UFS 设备已挂载
    2. 有足够可用空间（≥2GB）
    3. FIO 工具已安装
测试步骤：
    1. 执行 FIO 随机写测试（4K block, QD32, 60s, 含 10s ramp）
    2. 标注 IOPS、带宽、延迟是否达标
预期指标（参考）：
    - IOPS ≥ 330,000
    - 平均延迟 < 100 μs
    - p99.999 尾延迟 < 8000 μs
测试耗时：约 70 秒（含 ramp）
"""

import os
import sys
import subprocess
from pathlib import Path
from typing import Dict, Any

core_dir = Path(__file__).parent.parent.parent / 'core'
tools_dir = Path(__file__).parent.parent.parent / 'tools'
sys.path.insert(0, str(core_dir))
sys.path.insert(0, str(tools_dir))

from runner import TestCase
from fio_wrapper import FIO, FIOError, FIOMetrics
from ufs_utils import UFSDevice
from ufs_simulator import UFSSimulator


class Test(TestCase):
    """随机写性能测试"""
    
    name = "rand_write_burst"
    description = "随机写入性能测试（4K QD32）"
    
    def __init__(
        self,
        device: str = '/dev/ufs0',
        verbose: bool = False,
        logger=None,
        simulate: bool = False,
        bs: str = '4k',
        size: str = '1G',
        runtime: int = 60,
        ramp_time: int = 10,
        ioengine: str = 'sync',
        iodepth: int = 32,
        target_iops: float = 330000,
        max_avg_latency_us: float = 100,
        max_tail_latency_us: float = 8000,
    ):
        super().__init__(device, verbose, logger)
        self.simulate = simulate
        self.test_file = "/tmp/ufs_test_rand_write"
        self.bs = bs
        self.size = size
        self.runtime = runtime
        self.ramp_time = ramp_time
        self.ioengine = ioengine
        self.iodepth = iodepth
        self.target_iops = target_iops
        self.max_avg_latency_us = max_avg_latency_us
        self.max_tail_latency_us = max_tail_latency_us
        
        self.sim = UFSSimulator(device, logger=self.logger)
        self.fio = FIO(timeout=self.runtime + self.ramp_time + 30, logger=self.logger)
        self.ufs = self.sim if simulate else UFSDevice(device, logger=self.logger)
    
    def setup(self) -> bool:
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
            self.logger.error(f"设备权限不足")
            return False
        
        # 检查设备健康状态
        health = self.ufs.get_health_status()
        if health['status'] != 'OK':
            self.logger.warning(f"设备健康状态异常：{health['status']}")
        
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
                return 1024
    
    def execute(self) -> Dict[str, Any]:
        """执行 FIO 随机写测试"""
        self.logger.info("🚀 开始执行随机写性能测试...")
        
        if self.simulate:
            self.logger.info("🔧 模拟模式：生成模拟测试结果")
            return self.sim.generate_performance_result(
                'rand_write',
                target_iops=self.target_iops,
                runtime=self.runtime
            )
        
        try:
            # 删除已存在的测试文件
            if Path(self.test_file).exists():
                os.unlink(self.test_file)
            
            # 使用 fio_wrapper 便捷 API 执行
            metrics_obj = self.fio.run_rand_write(
                filename=self.test_file,
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
            self.logger.info(f"  平均延迟: {metrics['latency_avg']['value']:.1f} μs (目标: <{self.max_avg_latency_us})")
            self.logger.info(f"  p99.999 尾延迟: {metrics['latency_p99999']['value']:.1f} μs (目标: <{self.max_tail_latency_us})")
            
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
                "随机写 IOPS",
                f"≥ {target:.0f} IOPS",
                f"{iops:.0f} IOPS",
                "IOPS 显著低于目标值"
            )
            all_ok = False
        elif iops < target:
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
        
        return True
    
    def teardown(self) -> bool:
        """测试后清理"""
        # 清理测试文件
        if not self.simulate and Path(self.test_file).exists():
            try:
                os.unlink(self.test_file)
                self.logger.debug(f"🧹 已清理测试文件: {self.test_file}")
            except Exception as e:
                self.logger.warning(f"清理测试文件失败: {e}")
        
        # 调用父类清理（记录测试后健康状态）
        return super().teardown()
