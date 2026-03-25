#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
混合读写性能测试
测试 UFS 设备的混合随机读写 IOPS（70% 读/30% 写，4K QD32）

测试用例 ID: t_perf_MixedRw_009
测试目的：验证 UFS 设备混合读写 IOPS 性能
前置条件：
    1. UFS 设备已挂载
    2. 有足够可用空间（≥2GB）
    3. FIO 工具已安装
测试步骤：
    1. 执行 FIO 混合读写测试（4K block, QD32, 70/30, 60s, 含 10s ramp）
    2. 标注总 IOPS、读写 IOPS 分布、延迟是否达标
预期指标（参考）：
    - 总 IOPS ≥ 150,000
    - 平均延迟 < 200 μs
    - p99.999 尾延迟 < 8000 μs
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
    """混合读写性能测试"""
    
    name = "mixed_rw"
    description = "混合随机读写性能测试（70% 读/30% 写）"
    
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
        rw_mix: int = 70,
        target_total_iops: float = 150000,
        max_avg_latency_us: float = 200,
        max_tail_latency_us: float = 8000,
    ):
        super().__init__(device, verbose, logger)
        self.simulate = simulate
        self.test_file = "/tmp/ufs_test_mixed_rw"
        self.bs = bs
        self.size = size
        self.runtime = runtime
        self.ramp_time = ramp_time
        self.ioengine = ioengine
        self.iodepth = iodepth
        self.rw_mix = rw_mix
        self.target_total_iops = target_total_iops
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
        
        self.logger.info("📋 测试配置:")
        self.logger.info(f"  bs={self.bs}, size={self.size}, runtime={self.runtime}s, iodepth={self.iodepth}")
        self.logger.info(f"  rw_mix={self.rw_mix}% read, ioengine={self.ioengine}, ramp_time={self.ramp_time}s")
        self.logger.info(f"  target_total_iops={self.target_total_iops}")
        
        self.logger.info("📊 前置条件检查通过")
        return True
    
    def execute(self) -> dict:
        self.logger.info(f"开始执行混合读写测试（{self.rw_mix}% 读）...")
        
        try:
            extra_kwargs = {}
            if self.ramp_time > 0:
                extra_kwargs['ramp_time'] = self.ramp_time
            
            metrics = self.fio.run_mixed_rw(
                filename=self.test_file,
                size=self.size,
                runtime=self.runtime,
                bs=self.bs,
                iodepth=self.iodepth,
                read_ratio=self.rw_mix,
                ioengine=self.ioengine,
                **extra_kwargs
            )
            
            # 从原始数据中提取读写分别的 IOPS
            raw = metrics.raw
            job = raw['jobs'][0]
            read_iops = job.get('read', {}).get('iops', 0)
            write_iops = job.get('write', {}).get('iops', 0)
            total_iops = read_iops + write_iops
            
            avg_lat_us = metrics.latency_ns['mean'] / 1000
            p99999_us = metrics.latency_ns['percentile'].get('99.999', 0) / 1000
            
            self.logger.info(f"📊 测试结果:")
            self.logger.info(f"  总 IOPS: {total_iops:.0f}")
            self.logger.info(f"  读 IOPS: {read_iops:.0f} ({self.rw_mix}%)")
            self.logger.info(f"  写 IOPS: {write_iops:.0f} ({100-self.rw_mix}%)")
            self.logger.info(f"  带宽：{metrics.bandwidth['value']:.1f} MB/s")
            self.logger.info(f"  平均延迟：{avg_lat_us:.1f} μs")
            self.logger.info(f"  p99.999 延迟：{p99999_us:.1f} μs")
            
            return {
                'total_iops': {'value': total_iops, 'unit': 'IOPS'},
                'read_iops': {'value': read_iops, 'unit': 'IOPS'},
                'write_iops': {'value': write_iops, 'unit': 'IOPS'},
                'bandwidth': metrics.bandwidth,
                'latency_avg': {'value': avg_lat_us, 'unit': 'μs'},
                'latency_99999': {'value': p99999_us, 'unit': 'μs'},
            }
            
        except Exception as e:
            self.logger.error(f"测试执行失败：{e}")
            raise
    
    def validate(self, result: dict) -> bool:
        """采集指标数据，计算与参考目标的差距（纯数据，不做 pass/fail 判断）"""
        annotations = []
        
        actual_iops = result['total_iops']['value']
        gap_iops = (actual_iops - self.target_total_iops) / self.target_total_iops * 100 if self.target_total_iops > 0 else 0
        annotations.append({
            'metric': '混合 IOPS',
            'actual': f'{actual_iops:.0f} IOPS',
            'reference': f'{self.target_total_iops} IOPS',
            'gap': f'{gap_iops:+.1f}%',
        })
        self.logger.info(f"📊 混合 IOPS：{actual_iops:.0f}（参考 {self.target_total_iops}，gap {gap_iops:+.1f}%）")
        
        if 'read_ratio' in result:
            ratio = result['read_ratio']['value']
            annotations.append({
                'metric': '读写比例',
                'actual': f'{ratio:.0f}%',
                'reference': f'{self.read_pct}%',
                'gap': f'{ratio - self.read_pct:+.0f}pp',
            })
            self.logger.info(f"📊 读写比例：{ratio:.0f}%（参考 {self.read_pct}%）")
        
        actual_lat = result['latency_avg']['value']
        gap_lat = (actual_lat - self.max_avg_latency_us) / self.max_avg_latency_us * 100 if self.max_avg_latency_us > 0 else 0
        annotations.append({
            'metric': '平均延迟',
            'actual': f'{actual_lat:.1f} μs',
            'reference': f'{self.max_avg_latency_us} μs',
            'gap': f'{gap_lat:+.1f}%',
        })
        self.logger.info(f"📊 平均延迟：{actual_lat:.1f} μs（参考 {self.max_avg_latency_us} μs，gap {gap_lat:+.1f}%）")
        
        result['annotations'] = annotations
        self.logger.info(f"📊 共 {len(annotations)} 项指标数据已采集")
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
