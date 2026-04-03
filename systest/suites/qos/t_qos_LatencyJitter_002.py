#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
QoS 延迟抖动测试
测试 UFS 设备的延迟稳定性（标准差）

测试用例 ID: t_qos_LatencyJitter_002
测试目的：验证 UFS 设备延迟抖动（标准差）
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

注意：
    - 使用 get_test_file_path() 获取测试文件路径
    - teardown 时基类会自动清理测试文件
"""

import os
import sys
import subprocess
from pathlib import Path
from typing import Dict, Any

core_dir = Path(__file__).parent.parent.parent / 'core'
tools_dir = Path(__file__).parent.parent.parent / 'tools'
sys.path.insert(0, str(core_dir))
sys.path.insert(0, str(tools_dir))

from runner import TestCase
from fio_wrapper import FIO, FIOError, FIOMetrics
from ufs_utils import UFSDevice
from ufs_simulator import UFSSimulator


class Test(TestCase):
    """QoS 延迟抖动测试"""
    
    name = "qos_latency_jitter"
    description = "QoS 延迟抖动测试（标准差）"
    
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
        target_stddev_us: float = 500,
        target_jitter_pct: float = 50,
        prefill: bool = True,
    ):
        super().__init__(device, test_dir, verbose, logger)
        self.simulate = simulate
        self.test_file = self.get_test_file_path('qos_jitter')
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
        
        # 检查设备健康状态
        health = self.ufs.get_health_status()
        if health['status'] != 'OK':
            self.logger.warning(f"设备健康状态异常：{health['status']}")
        
        # 预填充
        if self.prefill and not self.simulate:
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
        
        self.logger.info("📊 前置条件检查通过")
        return True
    
    def _parse_size_mb(self, size_str: str) -> int:
        """解析大小字符串为 MB"""
        size_str = size_str.lower()
        if size_str.endswith('g'):
            return int(size_str[:-1]) * 1024
        elif size_str.endswith('m'):
            return int(size_str[:-1])
        elif size_str.endswith('k'):
            return max(1, int(size_str[:-1]) // 1024)
        else:
            try:
                return int(size_str) // 1024 // 1024
            except ValueError:
                return 512  # 默认 512MB
    
    def execute(self) -> Dict[str, Any]:
        """执行 FIO 延迟抖动测试"""
        self.logger.info("🚀 开始执行 QoS 延迟抖动测试...")
        
        if self.simulate:
            self.logger.info("🔧 模拟模式：生成模拟测试结果")
            return self.sim.generate_latency_jitter_result(
                target_stddev_us=self.target_stddev_us,
                target_jitter_pct=self.target_jitter_pct
            )
        
        try:
            # 使用 fio_wrapper 便捷 API 执行延迟测试
            metrics_obj = self.fio.run_latency_test(
                filename=self.test_file,
                size=self.size,
                runtime=self.runtime,
                bs=self.bs,
                iodepth=self.iodepth,
                ioengine=self.ioengine,
                ramp_time=self.ramp_time
            )
            
            # 转换为标准 metrics 格式（利用 FIOMetrics 已解析的数据）
            lat = metrics_obj.latency_ns
            avg_ns = lat['mean']
            stddev_ns = lat.get('stddev', 0)
            
            # 计算抖动系数（标准差 / 平均值）
            if avg_ns > 0:
                jitter_pct = (stddev_ns / avg_ns) * 100
            else:
                jitter_pct = 0
            
            metrics = {
                'iops': {
                    'value': metrics_obj.iops['value'],
                    'unit': 'IOPS'
                },
                'bandwidth': {
                    'value': metrics_obj.bandwidth['value'],
                    'unit': 'MB/s'
                },
                'latency_min': {
                    'value': lat.get('min', 0) / 1000,  # ns → μs
                    'unit': 'μs'
                },
                'latency_max': {
                    'value': lat.get('max', 0) / 1000,  # ns → μs
                    'unit': 'μs'
                },
                'latency_avg': {
                    'value': avg_ns / 1000,  # ns → μs
                    'unit': 'μs'
                },
                'latency_stddev': {
                    'value': stddev_ns / 1000,  # ns → μs
                    'unit': 'μs',
                    'target': self.target_stddev_us
                },
                'jitter_percent': {
                    'value': jitter_pct,
                    'unit': '%',
                    'target': self.target_jitter_pct
                },
                'runtime': {
                    'value': metrics_obj.raw['jobs'][0]['elapsed'],
                    'unit': 's'
                }
            }
            
            # 日志输出结果
            self.logger.info("📊 测试完成，抖动统计:")
            self.logger.info(f"  IOPS: {metrics['iops']['value']:.0f}")
            self.logger.info(f"  最小延迟: {metrics['latency_min']['value']:.1f} μs")
            self.logger.info(f"  最大延迟: {metrics['latency_max']['value']:.1f} μs")
            self.logger.info(f"  平均延迟: {metrics['latency_avg']['value']:.1f} μs")
            self.logger.info(f"  标准差: {metrics['latency_stddev']['value']:.1f} μs (目标: <{self.target_stddev_us})")
            self.logger.info(f"  抖动系数: {metrics['jitter_percent']['value']:.1f}% (目标: <{self.target_jitter_pct}%)")
            
            return metrics
            
        except FIOError as e:
            self.logger.error(f"FIO 执行失败: {e}")
            raise
    
    def validate(self, result: Dict[str, Any]) -> bool:
        """验证测试结果是否达标"""
        self.logger.info("🔍 验证测试结果...")
        
        all_ok = True
        
        # 验证延迟标准差
        stddev = result['latency_stddev']['value']
        target = self.target_stddev_us
        if stddev > target:
            self.record_failure(
                "延迟标准差",
                f"< {target} μs",
                f"{stddev:.1f} μs",
                "延迟抖动超出限制"
            )
            all_ok = False
        
        # 验证抖动系数
        jitter = result['jitter_percent']['value']
        target_jitter = self.target_jitter_pct
        if jitter > target_jitter:
            self.record_failure(
                "抖动系数",
                f"< {target_jitter}%",
                f"{jitter:.1f}%",
                "延迟一致性不达标"
            )
            all_ok = False
        
        # Postcondition 检查（硬件健康）
        self._check_postcondition()
        
        if all_ok:
            self.logger.info("✅ 所有验证通过")
        else:
            self.logger.warning(f"⚠️  共有 {len(self._failures)} 项验证不通过")
        
        return True
    
    def teardown(self) -> bool:
        """测试后清理"""
        # 清理测试文件
        if not self.simulate and Path(self.test_file).exists():
            try:
                os.unlink(self.test_file)
                self.logger.debug(f"🧹 已清理测试文件: {self.test_file}")
            except Exception as e:
                self.logger.warning(f"清理测试文件失败: {e}")
        
        # 调用父类清理（记录测试后健康状态）
        return super().teardown()
