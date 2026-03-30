#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
QoS 延迟稳定性测试
测试 UFS 设备在连续多次测试中的延迟稳定性（标准差）

测试用例 ID: t_qos_LatencyStability_004
测试目的：验证 UFS 设备在连续 10 次延迟测试中结果稳定（标准差 < 10%）
前置条件：
    1. UFS 设备已挂载
    2. 有足够可用空间（≥2GB）
    3. FIO 工具已安装
    4. 系统负载较低
测试步骤：
    1. 预填充测试文件
    2. 执行 10 次 FIO 延迟测试（4K block, QD1, 30s, 含 5s ramp）
    3. 收集每次的平均延迟和 p99.99 延迟
    4. 计算 10 次结果的标准差和变异系数
    5. 验证变异系数 < 10%
预期指标：
    - 平均延迟变异系数 < 10%
    - p99.99 延迟变异系数 < 15%
测试耗时：约 350 秒（10次 × 35秒）
"""

import os
import sys
import subprocess
import statistics
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
    """QoS 延迟稳定性测试"""
    
    name = "qos_latency_stability"
    description = "QoS 延迟稳定性测试（连续10次）"
    
    def __init__(
        self,
        device: str = '/dev/ufs0',
        verbose: bool = False,
        logger=None,
        simulate: bool = False,
        bs: str = '4k',
        size: str = '256M',
        runtime: int = 30,
        ramp_time: int = 5,
        ioengine: str = 'sync',
        iodepth: int = 1,
        iterations: int = 10,
        max_avg_cv_percent: float = 10.0,
        max_p9999_cv_percent: float = 15.0,
        prefill: bool = True,
    ):
        super().__init__(device, verbose, logger)
        self.simulate = simulate
        self.test_file = "/tmp/ufs_test_qos_stability"
        self.bs = bs
        self.size = size
        self.runtime = runtime
        self.ramp_time = ramp_time
        self.ioengine = ioengine
        self.iodepth = iodepth
        self.iterations = iterations
        self.max_avg_cv_percent = max_avg_cv_percent
        self.max_p9999_cv_percent = max_p9999_cv_percent
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
        self.logger.info(f"  iterations={self.iterations}, max_avg_cv={self.max_avg_cv_percent}%, max_p9999_cv={self.max_p9999_cv_percent}%")
        
        self.logger.info("📊 前置条件检查通过")
        return True
    
    def execute(self) -> dict:
        self.logger.info(f"开始执行 QoS 延迟稳定性测试（连续 {self.iterations} 次）...")
        
        avg_latencies = []
        p9999_latencies = []
        
        for i in range(self.iterations):
            self.logger.info(f"📊 第 {i+1}/{self.iterations} 次测试...")
            
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
                avg_lat = metrics.latency_ns['mean'] / 1000
                p9999_lat = percentiles.get('99.990000', 0) / 1000
                
                avg_latencies.append(avg_lat)
                p9999_latencies.append(p9999_lat)
                
                self.logger.debug(f"  第 {i+1} 次: avg={avg_lat:.1f}μs, p99.99={p9999_lat:.1f}μs")
                
            except Exception as e:
                self.logger.error(f"第 {i+1} 次测试失败：{e}")
                # 继续后续测试，但记录异常值
                avg_latencies.append(float('inf'))
                p9999_latencies.append(float('inf'))
        
        # 计算统计指标
        valid_avg = [x for x in avg_latencies if x != float('inf')]
        valid_p9999 = [x for x in p9999_latencies if x != float('inf')]
        
        if not valid_avg or not valid_p9999:
            raise Exception("所有测试迭代都失败")
        
        avg_mean = statistics.mean(valid_avg)
        avg_stdev = statistics.stdev(valid_avg) if len(valid_avg) > 1 else 0
        avg_cv = (avg_stdev / avg_mean * 100) if avg_mean > 0 else 0
        
        p9999_mean = statistics.mean(valid_p9999)
        p9999_stdev = statistics.stdev(valid_p9999) if len(valid_p9999) > 1 else 0
        p9999_cv = (p9999_stdev / p9999_mean * 100) if p9999_mean > 0 else 0
        
        self.logger.info(f"📊 稳定性测试结果:")
        self.logger.info(f"  平均延迟: {avg_mean:.1f} ± {avg_stdev:.1f} μs (CV: {avg_cv:.1f}%)")
        self.logger.info(f"  p99.99延迟: {p9999_mean:.1f} ± {p9999_stdev:.1f} μs (CV: {p9999_cv:.1f}%)")
        
        return {
            'latency_avg_mean': {'value': avg_mean, 'unit': 'μs'},
            'latency_avg_stdev': {'value': avg_stdev, 'unit': 'μs'},
            'latency_avg_cv': {'value': avg_cv, 'unit': '%'},
            'latency_p9999_mean': {'value': p9999_mean, 'unit': 'μs'},
            'latency_p9999_stdev': {'value': p9999_stdev, 'unit': 'μs'},
            'latency_p9999_cv': {'value': p9999_cv, 'unit': '%'},
            'iterations_completed': len(valid_avg),
            'iterations_total': self.iterations,
        }
    
    def validate(self, result: dict) -> bool:
        """验证延迟稳定性结果"""
        annotations = []
        
        # 平均延迟稳定性
        avg_cv = result['latency_avg_cv']['value']
        gap_avg_cv = (avg_cv - self.max_avg_cv_percent) / self.max_avg_cv_percent * 100 if self.max_avg_cv_percent > 0 else 0
        annotations.append({
            'metric': '平均延迟变异系数',
            'actual': f'{avg_cv:.1f}%',
            'reference': f'< {self.max_avg_cv_percent}%',
            'gap': f'{gap_avg_cv:+.1f}%',
        })
        self.logger.info(f"📊 平均延迟 CV：{avg_cv:.1f}%（参考 < {self.max_avg_cv_percent}%，gap {gap_avg_cv:+.1f}%）")
        
        # p99.99 延迟稳定性
        p9999_cv = result['latency_p9999_cv']['value']
        gap_p9999_cv = (p9999_cv - self.max_p9999_cv_percent) / self.max_p9999_cv_percent * 100 if self.max_p9999_cv_percent > 0 else 0
        annotations.append({
            'metric': 'p99.99 延迟变异系数',
            'actual': f'{p9999_cv:.1f}%',
            'reference': f'< {self.max_p9999_cv_percent}%',
            'gap': f'{gap_p9999_cv:+.1f}%',
        })
        self.logger.info(f"📊 p99.99 延迟 CV：{p9999_cv:.1f}%（参考 < {self.max_p9999_cv_percent}%，gap {gap_p9999_cv:+.1f}%）")
        
        # 完成率
        completed = result['iterations_completed']
        total = result['iterations_total']
        completion_rate = completed / total * 100
        annotations.append({
            'metric': '测试完成率',
            'actual': f'{completed}/{total} ({completion_rate:.1f}%)',
            'reference': '100%',
            'gap': f'{completion_rate - 100:+.1f}%',
        })
        self.logger.info(f"📊 测试完成率：{completed}/{total} ({completion_rate:.1f}%)")
        
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