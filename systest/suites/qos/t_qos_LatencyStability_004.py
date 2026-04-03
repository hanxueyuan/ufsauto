#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
QoS 延迟稳定性测试
测试 UFS 设备在连续多次测试中的延迟稳定性（变异系数 < 10%）

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

注意：
    - 使用 get_test_file_path() 获取测试文件路径
    - teardown 时基类会自动清理测试文件
"""

import os
import sys
import subprocess
import statistics
from pathlib import Path
from typing import Dict, Any

# 添加 core 和 tools 模块路径
core_dir = Path(__file__).parent.parent.parent / 'core'
tools_dir = Path(__file__).parent.parent.parent / 'tools'
sys.path.insert(0, str(core_dir))
sys.path.insert(0, str(tools_dir))

from runner import TestCase
from fio_wrapper import FIO, FIOError
from ufs_utils import UFSDevice


class Test(TestCase):
    """QoS 延迟稳定性测试"""
    
    name = "qos_latency_stability"
    description = "QoS 延迟稳定性测试（连续多次）"
    
    def __init__(
        self,
        device: str = '/dev/ufs0',
        test_dir: Path = None,
        verbose: bool = False,
        logger = None,
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
        super().__init__(device, test_dir, verbose, logger)
        self.test_file = self.get_test_file_path('qos_stability')
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
        
        # 初始化工具
        self.fio = FIO(timeout=self.runtime + self.ramp_time + 30, logger=self.logger)
        self.ufs = UFSDevice(device, logger=self.logger)
    
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
        
        # 预填充
        if self.prefill:
            self.logger.info(f"预填充测试文件：{self.test_file} ({self.size})")
            try:
                size_mb = self._parse_size_mb(self.size)
                subprocess.run(
                    ['dd', 'if=/dev/urandom', f'of={self.test_file}',
                     'bs=1M', f'count={size_mb}', 'conv=fdatasync'],
                    capture_output=True, timeout=120
                )
            except Exception as e:
                self.logger.warning(f"预填充异常，继续测试：{e}")
        
        self.logger.info("📋 测试配置:")
        self.logger.info(f"  bs={self.bs}, size={self.size}, runtime={self.runtime}s, iodepth={self.iodepth}")
        self.logger.info(f"  iterations={self.iterations}, max_avg_cv={self.max_avg_cv_percent}%, max_p9999_cv={self.max_p9999_cv_percent}%")
        
        self.logger.info("📊 前置条件检查通过")
        return True
    
    def _parse_size_mb(self, size_str: str) -> int:
        """解析大小字符串为 MB"""
        size_str = size_str.strip().upper()
        if size_str.endswith('G'):
            return int(float(size_str[:-1])) * 1024
        elif size_str.endswith('M'):
            return int(float(size_str[:-1]))
        elif size_str.endswith('K'):
            return max(1, int(float(size_str[:-1])) // 1024)
        else:
            try:
                return int(size_str) // 1024 // 1024
            except ValueError:
                return 256  # 默认 256MB
    
    def execute(self) -> Dict[str, Any]:
        """执行测试"""
        self.logger.info(f"🚀 开始执行 QoS 延迟稳定性测试（连续 {self.iterations} 次）...")
        
        avg_latencies: list[float] = []
        p9999_latencies: list[float] = []
        
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
                avg_lat = percentiles.get('50.0', 0) / 1000  # ns → μs
                p9999_lat = percentiles.get('99.99', 0) / 1000  # ns → μs
                
                avg_latencies.append(avg_lat)
                p9999_latencies.append(p9999_lat)
                
                self.logger.debug(f"  第 {i+1} 次: avg={avg_lat:.1f}μs, p99.99={p9999_lat:.1f}μs")
                
            except FIOError as e:
                self.logger.error(f"第 {i+1} 次测试失败：{e}")
                # 继续后续测试，但记录异常值
                avg_latencies.append(float('inf'))
                p9999_latencies.append(float('inf'))
        
        # 计算统计指标
        valid_avg = [x for x in avg_latencies if x != float('inf')]
        valid_p9999 = [x for x in p9999_latencies if x != float('inf')]
        
        if not valid_avg or not valid_p9999:
            raise Exception("所有测试迭代都失败")
        
        avg_mean = statistics.mean(valid_avg) if len(valid_avg) > 0 else 0
        avg_stdev = statistics.stdev(valid_avg) if len(valid_avg) > 1 else 0
        avg_cv = (avg_stdev / avg_mean * 100) if avg_mean > 0 else 0
        
        p9999_mean = statistics.mean(valid_p9999) if len(valid_p9999) > 0 else 0
        p9999_stdev = statistics.stdev(valid_p9999) if len(valid_p9999) > 1 else 0
        p9999_cv = (p9999_stdev / p9999_mean * 100) if p9999_mean > 0 else 0
        
        result = {
            'latency_avg_mean': {'value': avg_mean, 'unit': 'μs'},
            'latency_avg_stdev': {'value': avg_stdev, 'unit': 'μs'},
            'latency_avg_cv': {'value': avg_cv, 'unit': '%'},
            'latency_p9999_mean': {'value': p9999_mean, 'unit': 'μs'},
            'latency_p9999_stdev': {'value': p9999_stdev, 'unit': 'μs'},
            'latency_p9999_cv': {'value': p9999_cv, 'unit': '%'},
            'iterations_completed': len(valid_avg),
            'iterations_total': self.iterations,
        }
        
        # 日志输出结果
        self.logger.info("📊 测试完成，稳定性统计:")
        self.logger.info(f"  平均延迟: {avg_mean:.1f} μs ± {avg_stdev:.1f} μs (CV: {avg_cv:.1f}%)")
        self.logger.info(f"  p99.99 延迟: {p9999_mean:.1f} μs ± {p9999_stdev:.1f} μs (CV: {p9999_cv:.1f}%)")
        
        return result
    
    def validate(self, result: Dict[str, Any]) -> bool:
        """验证测试结果"""
        all_ok = True
        
        # 验证平均延迟变异系数
        avg_cv = result['latency_avg_cv']['value']
        if avg_cv > self.max_avg_cv_percent:
            self.record_failure(
                "平均延迟变异系数",
                f"< {self.max_avg_cv_percent}%",
                f"{avg_cv:.1f}%",
                "平均延迟变异超出限制"
            )
            all_ok = False
        
        # 验证 p99.99 延迟变异系数
        cv = result['latency_p9999_cv']['value']
        if cv > self.max_p9999_cv_percent:
            self.record_failure(
                "p99.99 延迟变异系数",
                f"< {self.max_p9999_cv_percent}%",
                f"{cv:.1f}%",
                "p99.99 延迟变异超出限制"
            )
            all_ok = False
        
        # 完成验证后执行 Postcondition 检查（硬件可靠性验证）
        self._check_postcondition()
        
        if all_ok:
            self.logger.info("✅ 所有验证通过")
        else:
            self.logger.warning(f"⚠️  共有 {len(self._failures)} 项验证不通过")
        
        return all_ok  # 框架根据 failures 自动判断最终状态
    
    def teardown(self) -> bool:
        """测试后清理"""
        # 清理测试文件 → 父类自动处理
        return super().teardown()
