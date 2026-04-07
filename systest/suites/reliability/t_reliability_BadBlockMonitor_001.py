#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
可靠性 - 坏块监控测试
监控 UFS 设备的坏块增长情况

测试用例 ID: t_reliability_BadBlockMonitor_001
测试目的：验证 UFS 设备在测试前后坏块无增长
前置条件：
    1. UFS 设备已挂载
    2. 有足够可用空间（≥2GB）
    3. FIO 工具已安装
测试步骤：
    1. 记录测试前坏块计数
    2. 执行随机写测试（施加压力）
    3. 记录测试后坏块计数
    4. 对比坏块是否增长
预期结果：
    - 坏块计数无增长
测试耗时：约 120 秒
"""

import sys
from pathlib import Path

# 添加 core 和 tools 模块路径
core_dir = Path(__file__).parent.parent.parent / 'core'
tools_dir = Path(__file__).parent.parent.parent / 'tools'
sys.path.insert(0, str(core_dir))
sys.path.insert(0, str(tools_dir))

from runner import TestCase
from fio_wrapper import FIO, FIOError
from ufs_utils import UFSDevice
from typing import Dict, Any


class TestCase(TestCase):
    """可靠性 - 坏块监控测试"""
    
    name = "reliability_badblock_monitor"
    description = "坏块监控测试（测试前后对比）"
    
    def __init__(
        self,
        device: str = '/dev/ufs0',
        test_dir: Path = None,
        verbose: bool = False,
        logger=None,
        # === 测试参数 ===
        bs: str = '128k',
        size: str = '1G',
        runtime: int = 60,
        ioengine: str = 'sync',
        iodepth: int = 32,
    ):
        super().__init__(device, test_dir, verbose, logger)
        self.test_file = self.get_test_file_path('reliability_badblock')
        self.bs = bs
        self.size = size
        self.runtime = runtime
        self.ioengine = ioengine
        self.iodepth = iodepth
        
        # 初始化工具
        self.fio = FIO(timeout=self.runtime + 60, logger=self.logger)
        self.ufs = UFSDevice(device, logger=self.logger)
        
        # 坏块计数
        self.pre_badblocks = 0
        self.post_badblocks = 0
    
    def setup(self) -> bool:
        """测试前准备 - 记录坏块基线"""
        self.logger.info("开始检查前置条件...")
        
        # 1. 检查设备是否存在
        if not self.ufs.exists():
            self.logger.error(f"设备不存在：{self.device}")
            return False
        self.logger.debug(f"📊 设备存在：{self.device}")
        
        # 2. 检查可用空间
        if not self.ufs.check_available_space(min_gb=2.0):
            self.logger.error("可用空间不足（需要≥2GB）")
            return False
        self.logger.debug(f"📊 可用空间充足（≥2GB）")
        
        # 3. 检查 FIO 是否已安装
        if not self.fio.is_installed():
            self.logger.error("FIO 工具未安装")
            return False
        self.logger.debug(f"📊 FIO 已安装")
        
        # 4. 记录测试前坏块计数
        health = self.ufs.get_health_status()
        self._pre_test_health = health
        self.pre_badblocks = health.get('bad_blocks', 0)
        self.logger.info(f"📊 测试前坏块计数：{self.pre_badblocks}")
        
        self.logger.info("✅ 前置条件检查通过")
        return True
    
    def execute(self) -> Dict[str, Any]:
        """执行坏块监控测试"""
        self.logger.info("开始执行坏块监控测试...")
        self.logger.info(f"  施加压力：随机写 {self.size}, runtime={self.runtime}s")
        
        try:
            # 执行随机写测试（施加压力）
            self.logger.info("执行 FIO 随机写测试...")
            self.fio.run_rand_write(
                filename=self.test_file,
                size=self.size,
                runtime=self.runtime,
                bs=self.bs,
                ioengine=self.ioengine,
                iodepth=self.iodepth,
                direct=True,
            )
            
            self.logger.info("✅ 压力测试完成")
            return {'status': 'completed'}
            
        except FIOError as e:
            self.logger.error(f"FIO 执行失败：{e}")
            raise
    
    def validate(self, result: Dict[str, Any]) -> bool:
        """验证坏块是否增长"""
        self.logger.info("验证坏块计数...")
        
        # 记录测试后坏块计数
        health = self.ufs.get_health_status()
        self._post_test_health = health
        self.post_badblocks = health.get('bad_blocks', 0)
        self.logger.info(f"📊 测试后坏块计数：{self.post_badblocks}")
        
        # 对比坏块是否增长
        if self.post_badblocks > self.pre_badblocks:
            self.record_failure(
                "坏块增长",
                f"{self.pre_badblocks} → {self.post_badblocks}",
                f"增加 {self.post_badblocks - self.pre_badblocks} 个坏块",
                "测试过程中出现坏块增长"
            )
            return False
        else:
            self.logger.info(f"  ✅ 坏块计数：{self.pre_badblocks} → {self.post_badblocks} (无增长)")
            return True
