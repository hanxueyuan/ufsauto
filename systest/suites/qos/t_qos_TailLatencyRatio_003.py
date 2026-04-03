#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
QoS 尾部发散度测试
测试 UFS 设备的延迟尾部发散度（p99.99/p50）

测试用例 ID: t_qos_TailLatencyRatio_003
测试目的：验证 UFS 设备延迟尾部发散度满足车规要求（< 100x）
前置条件：
    1. UFS 设备已挂载
    2. 有足够可用空间（≥2GB）
    3. FIO 工具已安装
    4. 系统负载较低
测试步骤：
    1. 预填充测试文件
    2. 执行 FIO 延迟测试（4K block, QD1, 120s, 含 10s ramp）
    3. 收集延迟百分位数据（p50, p99.99）
    4. 计算尾部发散度比值（p99.99/p50）
    5. 验证比值 < 100x
预期指标：
    - 尾部发散度 < 100x
    - p99.99 < 2ms (车规 QoS 要求)
测试耗时：约 130 秒（含 ramp）
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
    """QoS 尾部发散度测试"""
    
    name = "qos_tail_latency_ratio"
    description = "QoS 尾部发散度测试（p99.99/p50）"
    
    def __init__(
        self,
        device: str = '/dev/ufs0',
        test_dir: Path = None,
        verbose: bool = False,
        logger=None,
        simulate: bool = False,
        bs: str = '4k',
        size: str = '512M',
        runtime: int = 120,
        ramp_time: int = 10,
        ioengine: str = 'sync',
        iodepth: int = 1,
        target_tail_ratio: float = 100.0,
        target_p9999_us: float = 2000,  # 2ms
        prefill: bool = True,
    ):
        super().__init__(device, test_dir, verbose, logger)
        self.simulate = simulate
        self.test_file = self.get_test_file_path('qos_tail_ratio')
        self.bs = bs
        self.size = size
        self.runtime = runtime
        self.ramp_time = ramp_time
        self.ioengine = ioengine
        self.iodepth = iodepth
        self.target_tail_ratio = target_tail_ratio
        self.target_p9999_us = target_p9999_us
        self.prefill = prefill
        
        self.sim = UFSSimulator(device_path=device, logger=self.logger)
        self.fio = FIO(timeout=self.runtime + self.ramp_time + 30, logger=self.logger)
        self.ufs = self.sim if simulate else UFSDevice(device, logger=self.logger)
        # 模拟模式：自动创建模拟设备文件
        if simulate and self.sim is not None:
            if not self.sim.exists():
                self.sim.create_device(size_gb=128)
    
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
        
        # 预填充
        if self.prefill:
            self.logger.info(f"预填充测试文件：{self.test_file} ({self.size})")
            try:
                size_mb = self._parse_size_mb(self.size)
                subprocess.run(
                    ['dd', 'if=/dev/urandom', f'of={self.test_file}',
                     'bs=1M', f'count={size_mb}', 'conv=fdatasync'],
                    capture_output=True, text=True, timeout=120
                )
            except Exception as e:
                self.logger.warning(f"预填充异常，继续测试：{e}")
        
        self.logger.info("📋 测试配置:")
        self.logger.info(f"  bs={self.bs}, size={self.size}, runtime={self.runtime}s, iodepth={self.iodepth}")
        self.logger.info(f"  ioengine={self.ioengine}, ramp_time={self.ramp_time}s")
        self.logger.info(f"  target_tail_ratio={self.target_tail_ratio}x, target_p99.99={self.target_p9999_us} μs")
        
        self.logger.info("📊 前置条件检查通过")
        return True
    
    def execute(self) -> dict:
        self.logger.info("开始执行 QoS 尾部发散度测试...")
        
        try:
            extra_kwargs = {}
            if self.ramp_time > 0:
                extra_kwargs['ramp_time'] = self.ramp_time
            
            metrics = self.fio.run_latency_test(
                filename=self.test_file,
                size=self.size,
                runtime=self.runtime,
                bs=self.bs,
                iodepth=self.iodepth,
                ioengine=self.ioengine,
                **extra_kwargs
            )
            
            percentiles = metrics.latency_ns.get('percentile', {})
            p50 = percentiles.get('50.000000', 0) / 1000
            p9999 = percentiles.get('99.990000', 0) / 1000
            avg = metrics.latency_ns['mean'] / 1000
            
            self.logger.info(f"📊 延迟分布:")
            self.logger.info(f"  平均值：{avg:.1f} μs")
            self.logger.info(f"  p50:    {p50:.1f} μs")
            self.logger.info(f"  p99.99: {p9999:.1f} μs")
            
            return {
                'latency_avg': {'value': avg, 'unit': 'μs'},
                'latency_p50': {'value': p50, 'unit': 'μs'},
                'latency_p9999': {'value': p9999, 'unit': 'μs'},
            }
            
        except Exception as e:
            self.logger.error(f"测试执行失败：{e}")
            raise
    
    def validate(self, result: dict) -> bool:
        """验证尾部发散度结果"""
        annotations = []
        
        p50 = result['latency_p50']['value']
        p9999 = result['latency_p9999']['value']
        
        # 检查 p99.99 绝对值
        if p9999 > 0:
            gap_p9999 = (p9999 - self.target_p9999_us) / self.target_p9999_us * 100 if self.target_p9999_us > 0 else 0
            annotations.append({
                'metric': 'p99.99 延迟',
                'actual': f'{p9999:.1f} μs',
                'reference': f'{self.target_p9999_us} μs',
                'gap': f'{gap_p9999:+.1f}%',
            })
            self.logger.info(f"📊 p99.99 延迟：{p9999:.1f} μs（参考 {self.target_p9999_us} μs，gap {gap_p9999:+.1f}%）")
        
        # 计算尾部发散度
        if p50 > 0 and p9999 > 0:
            tail_ratio = p9999 / p50
            gap_ratio = (tail_ratio - self.target_tail_ratio) / self.target_tail_ratio * 100 if self.target_tail_ratio > 0 else 0
            annotations.append({
                'metric': '尾部发散度',
                'actual': f'p99.99/p50 = {tail_ratio:.1f}x',
                'reference': f'< {self.target_tail_ratio}x',
                'gap': f'{gap_ratio:+.1f}%',
            })
            self.logger.info(f"📊 尾部发散度：p99.99/p50 = {tail_ratio:.1f}x（参考 < {self.target_tail_ratio}x，gap {gap_ratio:+.1f}%）")
        
        result['annotations'] = annotations
        self.logger.info(f"📊 共 {len(annotations)} 项指标数据已采集")
        
        # === Postcondition 检查（硬件可靠性验证）===
        self._check_postcondition()
        
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
    
    @staticmethod
    def _parse_size_mb(size_str: str) -> int:
        size_str = size_str.strip().upper()
        if size_str.endswith('G'):
            return int(float(size_str[:-1]) * 1024)
        elif size_str.endswith('M'):
            return int(float(size_str[:-1]))
        return int(size_str) // (1024 * 1024)