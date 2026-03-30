#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
顺序读性能测试
测试 UFS 设备的顺序读取带宽（Burst 模式）

测试用例 ID: t_perf_SeqReadBurst_001
测试目的：验证 UFS 设备顺序读 Burst 性能是否达标
前置条件：
    1. UFS 设备已挂载
    2. 有足够可用空间（≥2GB）
    3. FIO 工具已安装
测试步骤：
    1. 预填充测试文件（避免读 sparse file）
    2. 执行 FIO 顺序读测试（128K block, 60s, 含 10s ramp）
    3. 验证带宽、IOPS、延迟是否达标
预期结果：
    - 带宽 ≥ 2100 MB/s
    - 平均延迟 < 200 μs
    - p99.999 尾延迟 < 5000 μs (5ms)
测试耗时：约 70 秒（含 ramp）
"""

import os
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
from ufs_simulator import UFSSimulator


class Test(TestCase):
    """顺序读性能测试"""
    
    name = "seq_read_burst"
    description = "顺序读取性能测试（Burst 模式）"
    
    def __init__(
        self,
        device: str = '/dev/ufs0',
        verbose: bool = False,
        logger=None,
        simulate: bool = False,
        # === 可配置参数 ===
        bs: str = '128k',
        size: str = '1G',
        runtime: int = 60,
        ramp_time: int = 10,
        ioengine: str = 'sync',
        iodepth: int = 1,
        # === 性能目标（可根据 UFS 规格调整）===
        target_bw_mbps: float = 2100,
        max_avg_latency_us: float = 200,
        max_tail_latency_us: float = 5000,  # p99.999
        # === 可选功能 ===
        verify: str = None,  # 'md5', 'crc32c', None
        prefill: bool = True,
    ):
        super().__init__(device, verbose, logger)
        self.test_file = "/tmp/ufs_test_seq_read"
        self.bs = bs
        self.size = size
        self.runtime = runtime
        self.ramp_time = ramp_time
        self.ioengine = ioengine
        self.iodepth = iodepth
        self.target_bw_mbps = target_bw_mbps
        self.max_avg_latency_us = max_avg_latency_us
        self.max_tail_latency_us = max_tail_latency_us
        self.verify_mode = verify
        self.prefill = prefill
        self.simulate = simulate
        
        # 初始化工具
        if simulate:
            self.logger.info("🔧 模拟模式：使用 UFS 模拟器")
            self.sim = UFSSimulator(device_path='/tmp/ufs_sim.img', logger=self.logger)
            self.fio = None
            self.ufs = self.sim
        else:
            self.fio = FIO(timeout=self.runtime + self.ramp_time + 30, logger=self.logger)
            self.ufs = UFSDevice(device, logger=self.logger)
            self.sim = None
    
    def setup(self) -> bool:
        """测试前准备 - 检查前置条件 + 预填充数据"""
        self.logger.info("开始检查前置条件...")
        
        # 1. 检查设备是否存在
        if not self.ufs.exists():
            self.logger.error(f"设备不存在：{self.device}")
            return False
        self.logger.debug(f"📊 设备存在：{self.device}")
        
        # 2. 检查可用空间（至少 2GB）
        if not self.ufs.check_available_space(min_gb=2.0):
            self.logger.error("可用空间不足")
            return False
        self.logger.debug("📊 可用空间充足（≥2GB）")
        
        # 3. 检查 FIO 工具
        try:
            result = subprocess.run(['which', 'fio'], capture_output=True)
            if result.returncode != 0:
                self.logger.error("FIO 工具未安装")
                return False
            self.logger.debug("📊 FIO 工具已安装")
        except Exception as e:
            self.logger.error(f"检查 FIO 失败：{e}")
            return False
        
        # 4. 检查权限
        if not os.access(self.device, os.R_OK | os.W_OK):
            self.logger.error(f"设备权限不足：{self.device}")
            return False
        self.logger.debug(f"📊 设备权限正常：{self.device}")
        
        # 5. 检查设备健康状态
        health = self.ufs.get_health_status()
        if health['status'] != 'OK':
            self.logger.warning(f"设备健康状态异常：{health['status']}")
            # 不阻止测试，但记录警告
        
        # 6. 预填充测试文件（避免读 sparse file / 未初始化数据）
        if self.prefill and not self.simulate:
            self.logger.info(f"预填充测试文件：{self.test_file} ({self.size})")
            try:
                # 用 dd 写入真实数据
                result = subprocess.run(
                    ['dd', 'if=/dev/urandom', f'of={self.test_file}',
                     'bs=1M', f'count={self._parse_size_mb(self.size)}',
                     'conv=fdatasync'],
                    capture_output=True,
                    text=True,
                    timeout=120
                )
                if result.returncode != 0:
                    self.logger.warning(f"预填充失败，继续测试：{result.stderr}")
                else:
                    self.logger.debug("📊 测试文件预填充完成")
            except subprocess.TimeoutExpired:
                self.logger.warning("预填充超时，继续测试")
            except Exception as e:
                self.logger.warning(f"预填充异常，继续测试：{e}")
        
        # 7. 记录完整测试配置（便于问题复现）
        self.logger.info("📋 测试配置:")
        self.logger.info(f"  bs={self.bs}, size={self.size}, runtime={self.runtime}s")
        self.logger.info(f"  ioengine={self.ioengine}, iodepth={self.iodepth}, ramp_time={self.ramp_time}s")
        self.logger.info(f"  target_bw={self.target_bw_mbps} MB/s, max_avg_lat={self.max_avg_latency_us} μs")
        self.logger.info(f"  max_tail_lat(p99.999)={self.max_tail_latency_us} μs, verify={self.verify_mode}")
        
        self.logger.info("📊 前置条件检查通过")
