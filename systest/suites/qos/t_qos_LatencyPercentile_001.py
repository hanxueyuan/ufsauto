#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
QoS 延迟百分位测试
测试 UFS 设备的延迟分布（p99.99）

测试用例 ID: t_qos_LatencyPercentile_001
测试目的：验证 UFS 设备延迟百分位是否达标（p99.99 < 10ms）
前置条件：
    1. UFS 设备已挂载
    2. 有足够可用空间（≥2GB）
    3. FIO 工具已安装
    4. 系统负载较低
测试步骤：
    1. 执行 FIO 延迟测试（4K block, QD1, 120s）
    2. 收集延迟百分位数据（p50, p90, p99, p99.99）
    3. 验证 p99.99 延迟是否达标
预期结果：p99.99 延迟 < 10ms
测试耗时：约 120 秒
"""

import sys
import subprocess
from pathlib import Path

core_dir = Path(__file__).parent.parent.parent / 'core'
tools_dir = Path(__file__).parent.parent.parent / 'tools'
sys.path.insert(0, str(core_dir))
sys.path.insert(0, str(tools_dir))

from runner import TestCase
from fio_wrapper import FIO, FIOError
from ufs_utils import UFSDevice
from ufs_simulator import UFSSimulator


class Test(TestCase):
    """QoS 延迟百分位测试"""
    
    name = "qos_latency_percentile"
    description = "QoS 延迟百分位测试（p99.99）"
    
    def __init__(self, device: str = '/dev/ufs0', verbose: bool = False, logger=None, simulate: bool = False):
        super().__init__(device, verbose, logger)
        self.simulate = simulate
        self.test_file = f"/tmp/ufs_test_qos_latency"
        self.size = "512M"
        self.runtime = 120
        self.bs = '4k'
        self.iodepth = 1  # QD=1 测延迟
        self.target_p9999 = 10000  # μs (10ms)
        
        self.sim = UFSSimulator(device, logger=self.logger)
        self.fio = FIO(timeout=self.runtime + 30, logger=self.logger)
        self.ufs = self.sim if simulate else UFSDevice(device, logger=self.logger)
    
    def setup(self) -> bool:
        """测试前准备"""
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
        
        import os
        if not os.access(self.device, os.R_OK | os.W_OK):
            self.logger.error(f"设备权限不足")
            return False
        
        # 检查系统负载（可选）
        self.logger.debug("前置条件检查通过")
        return True
    
    def execute(self) -> dict:
        """执行 FIO 延迟测试"""
        self.logger.info("开始执行 QoS 延迟百分位测试...")
        
        try:
            metrics = self.fio.run_latency_test(
                filename=self.test_file,
                size=self.size,
                runtime=self.runtime,
                bs=self.bs,
                iodepth=self.iodepth,
                ioengine='sync'
            )
            
            # 提取延迟百分位数据
            percentiles = metrics.latency_ns.get('percentile', {})
            p50 = percentiles.get('50.000000', 0) / 1000  # μs
            p90 = percentiles.get('90.000000', 0) / 1000
            p99 = percentiles.get('99.000000', 0) / 1000
            p9999 = percentiles.get('99.990000', 0) / 1000
            p99999 = percentiles.get('99.999000', 0) / 1000
            
            self.logger.info(f"📊 延迟分布:")
            self.logger.info(f"  p50:    {p50:.1f} μs")
            self.logger.info(f"  p90:    {p90:.1f} μs")
            self.logger.info(f"  p99:    {p99:.1f} μs")
            self.logger.info(f"  p99.99: {p9999:.1f} μs")
            self.logger.info(f"  p99.999: {p99999:.1f} μs")
            
            return {
                'latency_p50': {'value': p50, 'unit': 'μs'},
                'latency_p90': {'value': p90, 'unit': 'μs'},
                'latency_p99': {'value': p99, 'unit': 'μs'},
                'latency_p9999': {'value': p9999, 'unit': 'μs'},
                'latency_p99999': {'value': p99999, 'unit': 'μs'},
                'latency_avg': metrics.latency_avg
            }
            
        except FIOError as e:
            self.logger.error(f"FIO 执行失败：{e}")
            raise
    
    def validate(self, result: dict) -> bool:
        """验证结果是否达标"""
        actual = result['latency_p9999']['value']
        passed = actual < self.target_p9999
        
        if passed:
            self.logger.info(f"✅ 延迟达标：p99.99={actual:.1f}μs < {self.target_p9999/1000:.1f}ms")
        else:
            self.logger.warning(f"❌ 延迟不达标：p99.99={actual:.1f}μs ≥ {self.target_p9999/1000:.1f}ms")
        
        self.logger.log_assertion(
            assertion='p99.99 延迟达标',
            expected=f'< {self.target_p9999/1000:.1f}ms',
            actual=f'{actual/1000:.2f}ms',
            passed=passed
        )
        
        return passed
    
    def teardown(self) -> bool:
        """清理测试文件"""
        try:
            test_path = Path(self.test_file)
            if test_path.exists():
                test_path.unlink()
            
            self.ufs.flush_cache()
            self.logger.info("测试清理完成")
            return True
        except Exception as e:
            self.logger.warning(f"清理失败：{e}")
            return True
