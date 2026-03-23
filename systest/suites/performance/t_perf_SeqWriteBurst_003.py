#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
顺序写性能测试
测试 UFS 设备的顺序写入带宽（Burst 模式）

测试用例 ID: t_perf_SeqWriteBurst_003
测试目的：验证 UFS 设备顺序写 Burst 性能
前置条件：
    1. UFS 设备已挂载
    2. 有足够可用空间（≥2GB）
    3. FIO 工具已安装
测试步骤：
    1. 执行 FIO 顺序写测试（128K block, 60s, 含 10s ramp）
    2. 标注带宽、IOPS、延迟是否达标
预期指标（参考）：
    - 带宽 ≥ 1650 MB/s
    - 平均延迟 < 300 μs
    - p99.999 尾延迟 < 8000 μs (8ms)
测试耗时：约 70 秒（含 ramp）
"""

import os
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
    """顺序写性能测试"""
    
    name = "seq_write_burst"
    description = "顺序写入性能测试（Burst 模式）"
    
    def __init__(
        self,
        device: str = '/dev/ufs0',
        verbose: bool = False,
        logger=None,
        simulate: bool = False,
        bs: str = '128k',
        size: str = '1G',
        runtime: int = 60,
        ramp_time: int = 10,
        ioengine: str = 'sync',
        iodepth: int = 1,
        target_bw_mbps: float = 1650,
        max_avg_latency_us: float = 300,
        max_tail_latency_us: float = 8000,
        verify: str = None,
    ):
        super().__init__(device, verbose, logger)
        self.simulate = simulate
        self.test_file = "/tmp/ufs_test_seq_write"
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
        
        self.sim = UFSSimulator(device, logger=self.logger)
        self.fio = FIO(timeout=self.runtime + self.ramp_time + 30, logger=self.logger)
        self.ufs = self.sim if simulate else UFSDevice(device, logger=self.logger)
    
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
        
        self.logger.info("📋 测试配置:")
        self.logger.info(f"  bs={self.bs}, size={self.size}, runtime={self.runtime}s")
        self.logger.info(f"  ioengine={self.ioengine}, iodepth={self.iodepth}, ramp_time={self.ramp_time}s")
        self.logger.info(f"  target_bw={self.target_bw_mbps} MB/s, max_avg_lat={self.max_avg_latency_us} μs")
        
        self.logger.info("✅ 前置条件检查通过")
        return True
    
    def execute(self) -> dict:
        """执行顺序写性能测试"""
        self.logger.info("开始执行顺序写性能测试...")
        
        try:
            extra_kwargs = {}
            if self.ramp_time > 0:
                extra_kwargs['ramp_time'] = self.ramp_time
            if self.verify_mode:
                extra_kwargs['verify'] = self.verify_mode
            
            metrics = self.fio.run_seq_write(
                filename=self.test_file,
                size=self.size,
                runtime=self.runtime,
                bs=self.bs,
                ioengine=self.ioengine,
                **extra_kwargs
            )
            
            bw_mbps = metrics.bandwidth['value']
            iops = metrics.iops['value']
            avg_lat_us = metrics.latency_ns['mean'] / 1000
            p99999_ns = metrics.latency_ns['percentile'].get('99.999', 0)
            p99999_us = p99999_ns / 1000 if p99999_ns else 0
            
            self.logger.info(f"📊 测试结果:")
            self.logger.info(f"  带宽：{bw_mbps:.1f} MB/s")
            self.logger.info(f"  IOPS: {iops:.0f}")
            self.logger.info(f"  平均延迟：{avg_lat_us:.1f} μs")
            self.logger.info(f"  p99.999 延迟：{p99999_us:.1f} μs")
            
            return {
                'bandwidth': metrics.bandwidth,
                'iops': metrics.iops,
                'latency_avg': {'value': avg_lat_us, 'unit': 'μs'},
                'latency_99999': {'value': p99999_us, 'unit': 'μs'},
            }
            
        except Exception as e:
            self.logger.error(f"测试执行失败：{e}")
            raise
    
    def validate(self, result: dict) -> bool:
        """标注指标（性能测试，永远返回 True）"""
        annotations = []
        
        actual_bw = result['bandwidth']['value']
        annotations.append({
            'metric': '带宽', 'actual': f'{actual_bw:.1f} MB/s',
            'target': f'>= {self.target_bw_mbps} MB/s',
            'met': actual_bw >= self.target_bw_mbps,
        })
        
        actual_lat = result['latency_avg']['value']
        annotations.append({
            'metric': '平均延迟', 'actual': f'{actual_lat:.1f} μs',
            'target': f'< {self.max_avg_latency_us} μs',
            'met': actual_lat < self.max_avg_latency_us,
        })
        
        actual_tail = result['latency_99999']['value']
        if actual_tail > 0:
            annotations.append({
                'metric': 'p99.999 延迟', 'actual': f'{actual_tail:.1f} μs',
                'target': f'< {self.max_tail_latency_us} μs',
                'met': actual_tail < self.max_tail_latency_us,
            })
        
        result['annotations'] = annotations
        met_count = sum(1 for a in annotations if a['met'])
        self.logger.info(f"📋 指标标注：{met_count}/{len(annotations)} 项达标")
        for a in annotations:
            status = "✅" if a['met'] else "⚠️"
            self.logger.info(f"  {status} {a['metric']}：{a['actual']} (目标 {a['target']})")
        
        return True
    
    def teardown(self) -> bool:
        try:
            test_path = Path(self.test_file)
            if test_path.exists():
                test_path.unlink()
            self.ufs.flush_cache()
            self.logger.info("测试清理完成")
            return True
        except Exception as e:
            self.logger.warning(f"清理失败：{e}")
            return False
