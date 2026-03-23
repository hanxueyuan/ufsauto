#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
QoS 延迟抖动测试
测试 UFS 设备的延迟稳定性（标准差）

测试用例 ID: t_qos_LatencyJitter_002
测试目的：验证 UFS 设备延迟抖动
前置条件：
    1. UFS 设备已挂载
    2. 有足够可用空间（≥2GB）
    3. FIO 工具已安装
    4. 系统负载较低
测试步骤：
    1. 预填充测试文件
    2. 执行 FIO 延迟测试（4K block, QD1, 120s, 含 10s ramp）
    3. 收集延迟统计（min/avg/max/stddev）
    4. 标注延迟抖动和一致性是否达标
预期指标（参考）：
    - 延迟标准差 < 500 μs
    - 抖动系数 < 50%
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
    """QoS 延迟抖动测试"""
    
    name = "qos_latency_jitter"
    description = "QoS 延迟抖动测试（标准差）"
    
    def __init__(
        self,
        device: str = '/dev/ufs0',
        verbose: bool = False,
        logger=None,
        simulate: bool = False,
        bs: str = '4k',
        size: str = '512M',
        runtime: int = 120,
        ramp_time: int = 10,
        ioengine: str = 'sync',
        iodepth: int = 1,
        target_stddev_us: float = 500,
        target_jitter_pct: float = 50,
        prefill: bool = True,
    ):
        super().__init__(device, verbose, logger)
        self.simulate = simulate
        self.test_file = "/tmp/ufs_test_qos_jitter"
        self.bs = bs
        self.size = size
        self.runtime = runtime
        self.ramp_time = ramp_time
        self.ioengine = ioengine
        self.iodepth = iodepth
        self.target_stddev_us = target_stddev_us
        self.target_jitter_pct = target_jitter_pct
        self.prefill = prefill
        
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
        self.logger.info(f"  target_stddev={self.target_stddev_us} μs, target_jitter={self.target_jitter_pct}%")
        
        self.logger.info("✅ 前置条件检查通过")
        return True
    
    def execute(self) -> dict:
        self.logger.info("开始执行 QoS 延迟抖动测试...")
        
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
            
            latency_ns = metrics.latency_ns
            stddev_us = latency_ns.get('stddev', 0) / 1000
            mean_us = latency_ns.get('mean', 0) / 1000
            min_us = latency_ns.get('min', 0) / 1000
            max_us = latency_ns.get('max', 0) / 1000
            jitter_pct = (stddev_us / mean_us * 100) if mean_us > 0 else 0
            
            self.logger.info(f"📊 延迟统计:")
            self.logger.info(f"  最小值：{min_us:.1f} μs")
            self.logger.info(f"  平均值：{mean_us:.1f} μs")
            self.logger.info(f"  最大值：{max_us:.1f} μs")
            self.logger.info(f"  标准差：{stddev_us:.1f} μs")
            self.logger.info(f"  抖动系数：{jitter_pct:.1f}%")
            
            return {
                'latency_min': {'value': min_us, 'unit': 'μs'},
                'latency_mean': {'value': mean_us, 'unit': 'μs'},
                'latency_max': {'value': max_us, 'unit': 'μs'},
                'latency_stddev': {'value': stddev_us, 'unit': 'μs'},
                'jitter_ratio': {'value': jitter_pct, 'unit': '%'},
            }
            
        except Exception as e:
            self.logger.error(f"测试执行失败：{e}")
            raise
    
    def validate(self, result: dict) -> bool:
        """标注指标（性能测试，永远返回 True）"""
        annotations = []
        
        stddev = result['latency_stddev']['value']
        annotations.append({
            'metric': '延迟标准差', 'actual': f'{stddev:.1f} μs',
            'target': f'< {self.target_stddev_us} μs',
            'met': stddev < self.target_stddev_us,
        })
        
        jitter = result['jitter_ratio']['value']
        annotations.append({
            'metric': '抖动系数', 'actual': f'{jitter:.1f}%',
            'target': f'< {self.target_jitter_pct}%',
            'met': jitter < self.target_jitter_pct,
        })
        
        # max/min 比值：延迟极端值与最小值的比
        min_lat = result['latency_min']['value']
        max_lat = result['latency_max']['value']
        if min_lat > 0:
            max_min_ratio = max_lat / min_lat
            annotations.append({
                'metric': 'Max/Min 比', 'actual': f'{max_min_ratio:.0f}x',
                'target': '< 1000x',
                'met': max_min_ratio < 1000,
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
    
    @staticmethod
    def _parse_size_mb(size_str: str) -> int:
        size_str = size_str.strip().upper()
        if size_str.endswith('G'):
            return int(float(size_str[:-1]) * 1024)
        elif size_str.endswith('M'):
            return int(float(size_str[:-1]))
        return int(size_str) // (1024 * 1024)
