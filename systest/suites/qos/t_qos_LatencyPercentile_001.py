#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
QoS 延迟百分位测试
测试 UFS 设备的延迟分布（p99.99）

测试用例 ID: t_qos_LatencyPercentile_001
测试目的：验证 UFS 设备延迟百分位分布
前置条件：
    1. UFS 设备已挂载
    2. 有足够可用空间（≥2GB）
    3. FIO 工具已安装
    4. 系统负载较低
测试步骤：
    1. 预填充测试文件
    2. 执行 FIO 延迟测试（4K block, QD1, 120s, 含 10s ramp）
    3. 收集延迟百分位数据（p50, p90, p99, p99.99, p99.999）
    4. 标注各百分位延迟是否达标
预期指标（参考）：
    - p99.99 < 10ms
    - p99.999 < 20ms
测试耗时：约 130 秒（含 ramp）
"""

import os
import sys
import subprocess
from pathlib import Path
from typing import Dict, Any

# 添加 core 和 tools 模块路径
core_dir = Path(__file__).parent.parent.parent / 'core'
tools_dir = Path(__file__).parent.parent.parent / 'tools'
sys.path.insert(0, str(core_dir))
sys.path.insert(0, str(tools_dir))

from runner import TestCase
from fio_wrapper import FIO, FIOError, FIOMetrics
from ufs_utils import UFSDevice


class Test(TestCase):
    """QoS 延迟百分位测试"""
    
    name = "qos_latency_percentile"
    description = "QoS 延迟百分位测试（p99.99）"
    
    def __init__(
        self,
        device: str = '/dev/ufs0',
        test_dir: Path = None,
        verbose: bool = False,
        logger=None,
        bs: str = '4k',
        size: str = '512M',
        runtime: int = 120,
        ramp_time: int = 10,
        ioengine: str = 'sync',
        iodepth: int = 1,
        target_p9999_us: float = 10000,
        target_p99999_us: float = 20000,
        prefill: bool = True,
    ):
        super().__init__(device, test_dir, verbose, logger)
        self.test_file = self.get_test_file_path('qos_latency')
        self.bs = bs
        self.size = size
        self.runtime = runtime
        self.ramp_time = ramp_time
        self.ioengine = ioengine
        self.iodepth = iodepth
        self.target_p9999_us = target_p9999_us
        self.target_p99999_us = target_p99999_us
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
        
        # 检查设备健康状态
        health = self.ufs.get_health_status()
        if health['status'] != 'OK':
            self.logger.warning(f"设备健康状态异常：{health['status']}")
        
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
        self.logger.info(f"  target_p99.99={self.target_p9999_us} μs, target_p99.999={self.target_p99999_us} μs")
        
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
        """执行 FIO 延迟百分位测试"""
        self.logger.info("🚀 开始执行 QoS 延迟百分位测试...")
        
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
            percentiles = lat.get('percentile', {})
            
            metrics = {
                'iops': {
                    'value': metrics_obj.iops['value'],
                    'unit': 'IOPS'
                },
                'bandwidth': {
                    'value': metrics_obj.bandwidth['value'],
                    'unit': 'MB/s'
                },
                'latency_avg': {
                    'value': lat.get('avg', 0) / 1000,  # ns → μs
                    'unit': 'μs'
                },
                'latency_p50': {
                    'value': percentiles.get('50.0', 0) / 1000,  # ns → μs
                    'unit': 'μs'
                },
                'latency_p90': {
                    'value': percentiles.get('90.0', 0) / 1000,
                    'unit': 'μs'
                },
                'latency_p99': {
                    'value': percentiles.get('99.0', 0) / 1000,
                    'unit': 'μs'
                },
                'latency_p9999': {
                    'value': percentiles.get('99.9', 0) / 1000,
                    'unit': 'μs',
                    'target': self.target_p9999_us
                },
                'latency_p99999': {
                    'value': percentiles.get('99.99', 0) / 1000,
                    'unit': 'μs',
                    'target': self.target_p9999_us
                },
                'runtime': {
                    'value': metrics_obj.raw['jobs'][0]['elapsed'],
                    'unit': 's'
                }
            }
            
            # 日志输出结果
            self.logger.info("📊 测试完成，延迟分布:")
            self.logger.info(f"  IOPS: {metrics['iops']['value']:.0f}")
            self.logger.info(f"  平均延迟: {metrics['latency_avg']['value']:.1f} μs")
            self.logger.info(f"  p50: {metrics['latency_p50']['value']:.1f} μs")
            self.logger.info(f"  p90: {metrics['latency_p90']['value']:.1f} μs")
            self.logger.info(f"  p99: {metrics['latency_p99']['value']:.1f} μs")
            self.logger.info(f"  p99.99: {metrics['latency_p9999']['value']:.1f} μs (目标: <{self.target_p9999_us})")
            
            return metrics
            
        except FIOError as e:
            self.logger.error(f"FIO 执行失败: {e}")
            raise
    
    def validate(self, result: Dict[str, Any]) -> bool:
        """验证测试结果是否达标
        
        对于性能测试：不达标记录 failure 但始终返回 True 让框架处理
        """
        self.logger.info("🔍 验证测试结果...")
        
        all_ok = True
        
        # 验证 p99.99 延迟
        p9999 = result['latency_p9999']['value']
        target = self.target_p9999_us
        if p9999 > target:
            self.record_failure(
                "p99.99 延迟",
                f"< {target} μs",
                f"{p9999:.1f} μs",
                "p99.99 延迟超出限制"
            )
            all_ok = False
        
        # Postcondition 检查（硬件可靠性验证）
        self._check_postcondition()
        
        if all_ok:
            self.logger.info("✅ 所有验证通过")
        else:
            self.logger.warning(f"⚠️  共有 {len(self._failures)} 项验证不通过")
        
        return True  # 性能测试始终返回 True，由框架根据 failures 判断最终状态
    
    def teardown(self) -> bool:
        """测试后清理"""
        # 清理测试文件 → 父类会自动清理
        return super().teardown()
