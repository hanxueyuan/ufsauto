#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
混合读写性能测试
测试 UFS 设备的混合随机读写 IOPS（70% 读/30% 写，4K QD32）

测试用例 ID: t_perf_MixedRw_009
测试目的：验证 UFS 设备混合读写 IOPS 性能是否达标（≥150 KIOPS）
前置条件：
    1. UFS 设备已挂载
    2. 有足够可用空间（≥2GB）
    3. FIO 工具已安装
测试步骤：
    1. 执行 FIO 混合读写测试（4K block, QD32, 70/30, 60s）
    2. 验证读写 IOPS 是否达标
预期结果：总 IOPS ≥ 150,000
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


class Test(TestCase):
    """混合读写性能测试"""
    
    name = "mixed_rw"
    description = "混合随机读写性能测试（70% 读/30% 写）"
    
    def __init__(self, device: str = '/dev/ufs0', verbose: bool = False, logger=None):
        super().__init__(device, verbose, logger)
        self.test_file = f"/tmp/ufs_test_mixed_rw"
        self.size = "1G"
        self.runtime = 60
        self.bs = '4k'
        self.iodepth = 32
        self.rw_mix = 70  # 70% 读
        self.target = 150000  # IOPS
        
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
        
        self.logger.info("✅ 前置条件检查通过")
        return True
    
    def execute(self) -> dict:
        """执行 FIO 混合读写测试"""
        self.logger.info(f"开始执行混合读写测试（{self.rw_mix}% 读）...")
        
        try:
            metrics = self.fio.run_mixed_rw(
                filename=self.test_file,
                size=self.size,
                runtime=self.runtime,
                bs=self.bs,
                iodepth=self.iodepth,
                read_ratio=self.rw_mix,
                ioengine='sync'
            )
            
            # 从原始数据中提取读写分别的 IOPS
            raw = metrics.raw
            job = raw['jobs'][0]
            read_iops = job.get('read', {}).get('iops', 0)
            write_iops = job.get('write', {}).get('iops', 0)
            total_iops = read_iops + write_iops
            
            self.logger.info(f"📊 测试结果:")
            self.logger.info(f"  总 IOPS: {total_iops:.0f}")
            self.logger.info(f"  读 IOPS: {read_iops:.0f} ({self.rw_mix}%)")
            self.logger.info(f"  写 IOPS: {write_iops:.0f} ({100-self.rw_mix}%)")
            self.logger.info(f"  带宽：{metrics.bandwidth['value']:.1f} MB/s")
            
            return {
                'total_iops': {
                    'value': total_iops,
                    'unit': 'IOPS'
                },
                'read_iops': {
                    'value': read_iops,
                    'unit': 'IOPS'
                },
                'write_iops': {
                    'value': write_iops,
                    'unit': 'IOPS'
                },
                'bandwidth': metrics.bandwidth
            }
            
        except FIOError as e:
            self.logger.error(f"FIO 执行失败：{e}")
            raise
    
    def validate(self, result: dict) -> bool:
        """验证结果是否达标"""
        actual = result['total_iops']['value']
        passed = actual >= self.target
        
        if passed:
            self.logger.info(f"✅ 性能达标：{actual:.0f} IOPS ≥ {self.target} IOPS")
        else:
            self.logger.warning(f"❌ 性能不达标：{actual:.0f} IOPS < {self.target} IOPS")
        
        self.logger.log_assertion(
            assertion='总 IOPS 达标',
            expected=f'>= {self.target} IOPS',
            actual=f'{actual:.0f} IOPS',
            passed=passed
        )
        
        # 分别记录读写 IOPS
        read_iops = result['read_iops']['value']
        write_iops = result['write_iops']['value']
        self.logger.info(f"读 IOPS: {read_iops:.0f}, 写 IOPS: {write_iops:.0f}")
        
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
