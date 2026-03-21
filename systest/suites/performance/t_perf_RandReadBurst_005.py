#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
随机读性能测试
测试 UFS 设备的随机读取 IOPS（4K QD32）

测试用例 ID: t_perf_RandReadBurst_005
测试目的：验证 UFS 设备随机读 IOPS 性能是否达标（≥200 KIOPS）
前置条件：
    1. UFS 设备已挂载
    2. 有足够可用空间（≥2GB）
    3. FIO 工具已安装
测试步骤：
    1. 执行 FIO 随机读测试（4K block, QD32, 60s）
    2. 验证 IOPS 是否达标
预期结果：IOPS ≥ 200,000
测试耗时：约 60 秒
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
    """随机读性能测试"""
    
    name = "rand_read_burst"
    description = "随机读取性能测试（4K QD32）"
    
    def __init__(self, device: str = '/dev/ufs0', verbose: bool = False, logger=None, simulate: bool = False):
        super().__init__(device, verbose, logger)
        self.simulate = simulate
        self.test_file = f"/tmp/ufs_test_rand_read"
        self.size = "1G"
        self.runtime = 60
        self.bs = '4k'
        self.iodepth = 32
        self.target = 200000  # IOPS
        
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
        
        self.logger.info("✅ 前置条件检查通过")
        return True
    
    def execute(self) -> dict:
        """执行 FIO 随机读测试"""
        self.logger.info("开始执行随机读性能测试...")
        
        try:
            metrics = self.fio.run_rand_read(
                filename=self.test_file,
                size=self.size,
                runtime=self.runtime,
                bs=self.bs,
                iodepth=self.iodepth,
                ioengine='sync'
            )
            
            self.logger.info(f"📊 测试结果:")
            self.logger.info(f"  IOPS: {metrics.iops['value']:.0f}")
            self.logger.info(f"  带宽：{metrics.bandwidth['value']:.1f} MB/s")
            self.logger.info(f"  平均延迟：{metrics.latency_ns['mean']/1000:.1f} μs")
            
            return {
                'iops': metrics.iops,
                'bandwidth': metrics.bandwidth,
                'latency_avg': {
                    'value': metrics.latency_ns['mean'] / 1000,
                    'unit': 'μs'
                }
            }
            
        except FIOError as e:
            self.logger.error(f"FIO 执行失败：{e}")
            raise
    
    def validate(self, result: dict) -> bool:
        """验证结果是否达标"""
        actual = result['iops']['value']
        passed = actual >= self.target
        
        if passed:
            self.logger.info(f"✅ 性能达标：{actual:.0f} IOPS ≥ {self.target} IOPS")
        else:
            self.logger.warning(f"❌ 性能不达标：{actual:.0f} IOPS < {self.target} IOPS")
        
        self.logger.log_assertion(
            assertion='IOPS 达标',
            expected=f'>= {self.target} IOPS',
            actual=f'{actual:.0f} IOPS',
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
