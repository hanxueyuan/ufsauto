#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
顺序写性能测试
测试 UFS 设备的顺序写入带宽（Burst 模式）

测试用例 ID: t_perf_SeqWriteBurst_003
测试目的：验证 UFS 设备顺序写 Burst 性能是否达标（≥1650 MB/s）
前置条件：
    1. UFS 设备已挂载
    2. 有足够可用空间（≥2GB）
    3. FIO 工具已安装
测试步骤：
    1. 执行 FIO 顺序写测试（128K block, 60s）
    2. 验证带宽是否达标
预期结果：带宽 ≥ 1650 MB/s
测试耗时：约 60 秒
"""

import sys
import subprocess
from pathlib import Path

# 添加 core 和 tools 模块路径
core_dir = Path(__file__).parent.parent.parent / 'core'
tools_dir = Path(__file__).parent.parent.parent / 'tools'
sys.path.insert(0, str(core_dir))
sys.path.insert(0, str(tools_dir))

from runner import TestCase
from fio_wrapper import FIO, FIOError
from ufs_utils import UFSDevice


class Test(TestCase):
    """顺序写性能测试"""
    
    name = "seq_write_burst"
    description = "顺序写入性能测试（Burst 模式）"
    
    def __init__(self, device: str = '/dev/ufs0', verbose: bool = False, logger=None):
        super().__init__(device, verbose, logger)
        self.test_file = f"/tmp/ufs_test_seq_write"
        self.size = "1G"
        self.runtime = 60
        self.target = 1650  # MB/s
        
        # 初始化工具
        self.fio = FIO(timeout=self.runtime + 30, logger=self.logger)
        self.ufs = UFSDevice(device, logger=self.logger)
    
    def setup(self) -> bool:
        """测试前准备 - 检查前置条件"""
        self.logger.info("开始检查前置条件...")
        
        # 1.1 检查设备是否存在
        if not self.ufs.exists():
            self.logger.error(f"设备不存在：{self.device}")
            return False
        self.logger.debug("✅ 设备存在")
        
        # 1.2 检查可用空间
        if not self.ufs.check_available_space(min_gb=2.0):
            return False
        self.logger.debug("✅ 可用空间充足")
        
        # 1.3 检查 FIO 工具
        try:
            result = subprocess.run(['which', 'fio'], capture_output=True)
            if result.returncode != 0:
                self.logger.error("FIO 工具未安装")
                return False
            self.logger.debug("✅ FIO 工具已安装")
        except Exception as e:
            self.logger.error(f"检查 FIO 失败：{e}")
            return False
        
        # 1.4 检查权限
        import os
        if not os.access(self.device, os.R_OK | os.W_OK):
            self.logger.error(f"设备权限不足：{self.device}")
            return False
        self.logger.debug("✅ 设备权限正常")
        
        self.logger.info("✅ 前置条件检查通过")
        return True
    
    def execute(self) -> dict:
        """执行 FIO 顺序写测试"""
        self.logger.info("开始执行顺序写性能测试...")
        
        try:
            metrics = self.fio.run_seq_write(
                filename=self.test_file,
                size=self.size,
                runtime=self.runtime,
                bs='128k',
                ioengine='sync'
            )
            
            self.logger.info(f"📊 测试结果:")
            self.logger.info(f"  带宽：{metrics.bandwidth['value']:.1f} MB/s")
            self.logger.info(f"  IOPS: {metrics.iops['value']:.0f}")
            self.logger.info(f"  平均延迟：{metrics.latency_ns['mean']/1000:.1f} μs")
            
            return {
                'bandwidth': metrics.bandwidth,
                'iops': metrics.iops,
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
        actual = result['bandwidth']['value']
        passed = actual >= self.target
        
        if passed:
            self.logger.info(f"✅ 性能达标：{actual:.1f} MB/s ≥ {self.target} MB/s")
        else:
            self.logger.warning(f"❌ 性能不达标：{actual:.1f} MB/s < {self.target} MB/s")
        
        self.logger.log_assertion(
            assertion='带宽达标',
            expected=f'>= {self.target} MB/s',
            actual=f'{actual:.1f} MB/s',
            passed=passed
        )
        
        return passed
    
    def teardown(self) -> bool:
        """清理测试文件"""
        try:
            import os
            test_path = Path(self.test_file)
            if test_path.exists():
                test_path.unlink()
                self.logger.debug(f"清理测试文件：{self.test_file}")
            
            self.ufs.flush_cache()
            self.logger.info("测试清理完成")
            return True
        except Exception as e:
            self.logger.warning(f"清理失败：{e}")
            return True
