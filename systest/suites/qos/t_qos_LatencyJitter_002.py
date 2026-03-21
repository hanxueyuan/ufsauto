#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
QoS 延迟抖动测试
测试 UFS 设备的延迟稳定性（标准差）

测试用例 ID: t_qos_LatencyJitter_002
测试目的：验证 UFS 设备延迟抖动是否达标（stddev < 500μs）
前置条件：
    1. UFS 设备已挂载
    2. 有足够可用空间（≥2GB）
    3. FIO 工具已安装
    4. 系统负载较低
测试步骤：
    1. 执行 FIO 延迟测试（4K block, QD1, 120s）
    2. 收集延迟标准差数据
    3. 验证延迟抖动是否达标
预期结果：延迟标准差 < 500μs
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


class Test(TestCase):
    """QoS 延迟抖动测试"""
    
    name = "qos_latency_jitter"
    description = "QoS 延迟抖动测试（标准差）"
    
    def __init__(self, device: str = '/dev/ufs0', verbose: bool = False, logger=None):
        super().__init__(device, verbose, logger)
        self.test_file = f"/tmp/ufs_test_qos_jitter"
        self.size = "512M"
        self.runtime = 120
        self.bs = '4k'
        self.iodepth = 1
        self.target_stddev = 500  # μs
        
        self.fio = FIO(timeout=self.runtime + 30, logger=self.logger)
        self.ufs = UFSDevice(device, logger=self.logger)
    
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
        
        self.logger.debug("前置条件检查通过")
        return True
    
    def execute(self) -> dict:
        """执行 FIO 延迟抖动测试"""
        self.logger.info("开始执行 QoS 延迟抖动测试...")
        
        try:
            metrics = self.fio.run_latency_test(
                filename=self.test_file,
                size=self.size,
                runtime=self.runtime,
                bs=self.bs,
                iodepth=self.iodepth,
                ioengine='sync'
            )
            
            # 提取延迟统计数据
            latency_ns = metrics.latency_ns
            stddev = latency_ns.get('stddev', 0) / 1000  # μs
            mean = latency_ns.get('mean', 0) / 1000
            min_lat = latency_ns.get('min', 0) / 1000
            max_lat = latency_ns.get('max', 0) / 1000
            
            self.logger.info(f"📊 延迟统计:")
            self.logger.info(f"  最小值：{min_lat:.1f} μs")
            self.logger.info(f"  平均值：{mean:.1f} μs")
            self.logger.info(f"  最大值：{max_lat:.1f} μs")
            self.logger.info(f"  标准差：{stddev:.1f} μs")
            
            # 计算抖动系数（标准差/平均值）
            jitter_ratio = (stddev / mean * 100) if mean > 0 else 0
            self.logger.info(f"  抖动系数：{jitter_ratio:.1f}%")
            
            return {
                'latency_stddev': {'value': stddev, 'unit': 'μs'},
                'latency_mean': {'value': mean, 'unit': 'μs'},
                'latency_min': {'value': min_lat, 'unit': 'μs'},
                'latency_max': {'value': max_lat, 'unit': 'μs'},
                'jitter_ratio': {'value': jitter_ratio, 'unit': '%'}
            }
            
        except FIOError as e:
            self.logger.error(f"FIO 执行失败：{e}")
            raise
    
    def validate(self, result: dict) -> bool:
        """验证结果是否达标"""
        actual = result['latency_stddev']['value']
        passed = actual < self.target_stddev
        
        if passed:
            self.logger.info(f"✅ 延迟抖动达标：stddev={actual:.1f}μs < {self.target_stddev}μs")
        else:
            self.logger.warning(f"❌ 延迟抖动不达标：stddev={actual:.1f}μs ≥ {self.target_stddev}μs")
        
        self.logger.log_assertion(
            assertion='延迟抖动达标',
            expected=f'< {self.target_stddev}μs',
            actual=f'{actual:.1f}μs',
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
