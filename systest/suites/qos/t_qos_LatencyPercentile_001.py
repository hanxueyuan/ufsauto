#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
QoS 延迟百分位测试
测试 UFS 设备的延迟分布和百分位指标

测试用例 ID: t_qos_LatencyPercentile_001
测试目的：验证 UFS 设备延迟百分位指标（p50/p99/p99.99）
前置条件：
    1. UFS 设备已挂载
    2. 有足够可用空间（≥2GB）
    3. FIO 工具已安装
测试步骤：
    1. 执行 FIO 随机读测试（4K block, QD=1, 60s）
    2. 记录 p50/p99/p99.99 延迟
    3. 验证延迟百分位是否达标
预期指标：
    - p50 延迟 < 50 μs
    - p99 延迟 < 200 μs
    - p99.99 延迟 < 500 μs
测试耗时：约 60 秒
"""

import sys
import json
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


class Test(TestCase):
    """QoS 延迟百分位测试"""
    
    name = "qos_latency_percentile"
    description = "QoS 延迟百分位测试（p50/p99/p99.99）"
    
    def __init__(
        self,
        device: str = '/dev/ufs0',
        test_dir: Path = None,
        verbose: bool = False,
        logger=None,
        # === 测试参数 ===
        bs: str = '4k',
        size: str = '1G',
        runtime: int = 60,
        ramp_time: int = 10,
        ioengine: str = 'sync',
        iodepth: int = 1,
        # === 性能目标 ===
        p50_latency_us: float = 50,
        p99_latency_us: float = 200,
        p9999_latency_us: float = 500,
    ):
        super().__init__(device, test_dir, verbose, logger)
        self.test_file = self.get_test_file_path('qos_latency')
        self.bs = bs
        self.size = size
        self.runtime = runtime
        self.ramp_time = ramp_time
        self.ioengine = ioengine
        self.iodepth = iodepth
        self.p50_latency_us = p50_latency_us
        self.p99_latency_us = p99_latency_us
        self.p9999_latency_us = p9999_latency_us
        
        # 初始化工具
        self.fio = FIO(timeout=self.runtime + self.ramp_time + 30, logger=self.logger)
        self.ufs = UFSDevice(device, logger=self.logger)
    
    def setup(self) -> bool:
        """测试前准备 - 检查前置条件"""
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
        import subprocess
        try:
            result = subprocess.run(['which', 'fio'], capture_output=True, text=True)
            if result.returncode != 0:
                self.logger.error("FIO 工具未安装")
                return False
            self.logger.debug(f"📊 FIO 已安装")
        except Exception as e:
            self.logger.error(f"FIO 检查失败：{e}")
            return False
        
        # 4. 检查设备权限
        if not self.ufs.check_device():
            self.logger.error(f"设备权限不足：{self.device}")
            return False
        self.logger.debug(f"📊 设备权限正常")
        
        # 5. 记录健康基线
        health = self.ufs.get_health_status()
        self._pre_test_health = health
        self.logger.debug(f"📊 健康基线：{health['status']}")
        
        self.logger.info("✅ 前置条件检查通过")
        return True
    
    def execute(self) -> Dict[str, Any]:
        """执行 QoS 延迟百分位测试"""
        self.logger.info("开始执行 QoS 延迟百分位测试...")
        self.logger.info(f"  bs={self.bs}, size={self.size}, runtime={self.runtime}s, iodepth={self.iodepth}")
        
        try:
            # 执行 FIO 随机读测试（QD=1，测量延迟）
            self.logger.info("执行 FIO 随机读测试（QD=1）...")
            metrics_obj = self.fio.run_rand_read(
                filename=self.test_file,
                size=self.size,
                runtime=self.runtime,
                bs=self.bs,
                ioengine=self.ioengine,
                iodepth=self.iodepth,
                ramp_time=self.ramp_time,
                direct=True,
            )
            
            # 提取完整的延迟分布数据
            lat_ns = metrics_obj.latency_ns
            percentiles = lat_ns.get('percentile', {})
            
            # 收集所有百分位数据
            lat_distribution = {
                'p50': percentiles.get('50.000000', 0) / 1000,  # ns → μs
                'p90': percentiles.get('90.000000', 0) / 1000,
                'p95': percentiles.get('95.000000', 0) / 1000,
                'p99': percentiles.get('99.000000', 0) / 1000,
                'p99.9': percentiles.get('99.900000', 0) / 1000,
                'p99.99': percentiles.get('99.990000', 0) / 1000,
                'p99.999': percentiles.get('99.999000', 0) / 1000,
                'min': lat_ns.get('min', 0) / 1000,
                'max': lat_ns.get('max', 0) / 1000,
                'mean': lat_ns.get('mean', 0) / 1000,
                'stddev': lat_ns.get('stddev', 0) / 1000,
            }
            
            self.logger.info("📊 延迟分布数据:")
            self.logger.info(f"  最小值：{lat_distribution['min']:.1f} μs")
            self.logger.info(f"  p50:    {lat_distribution['p50']:.1f} μs")
            self.logger.info(f"  p90:    {lat_distribution['p90']:.1f} μs")
            self.logger.info(f"  p95:    {lat_distribution['p95']:.1f} μs")
            self.logger.info(f"  p99:    {lat_distribution['p99']:.1f} μs")
            self.logger.info(f"  p99.9:  {lat_distribution['p99.9']:.1f} μs")
            self.logger.info(f"  p99.99: {lat_distribution['p99.99']:.1f} μs")
            self.logger.info(f"  p99.999:{lat_distribution['p99.999']:.1f} μs")
            self.logger.info(f"  最大值：{lat_distribution['max']:.1f} μs")
            self.logger.info(f"  平均值：{lat_distribution['mean']:.1f} μs")
            self.logger.info(f"  标准差：{lat_distribution['stddev']:.1f} μs")
            
            # 保存延迟分布数据到文件（用于后续绘制图表）
            try:
                distribution_file = self.test_file.parent / f'qos_latency_distribution_{self.test_file.stem}.json'
                with open(distribution_file, 'w', encoding='utf-8') as f:
                    json.dump({
                        'test_name': self.name,
                        'timestamp': self.start_time.isoformat() if hasattr(self, 'start_time') else 'N/A',
                        'device': self.device,
                        'distribution': lat_distribution,
                        'raw_fio': metrics_obj.raw.get('jobs', [{}])[0] if metrics_obj.raw else {}
                    }, f, indent=2, ensure_ascii=False)
                self.logger.info(f"📁 延迟分布数据已保存：{distribution_file}")
            except Exception as e:
                self.logger.warning(f"⚠️  保存分布数据失败：{e}")
            
            return lat_distribution
            
        except FIOError as e:
            self.logger.error(f"FIO 执行失败：{e}")
            raise
    
    def validate(self, result: Dict[str, Any]) -> bool:
        """验证延迟百分位是否达标"""
        self.logger.info("验证延迟百分位指标...")
        
        lat_p50 = result.get('p50', 0)
        lat_p99 = result.get('p99', 0)
        lat_p9999 = result.get('p99.99', 0)
        
        # 验证 p50
        if lat_p50 > self.p50_latency_us:
            self.record_failure(
                "p50 延迟",
                f"< {self.p50_latency_us} μs",
                f"{lat_p50:.1f} μs",
                "p50 延迟超出限制"
            )
        else:
            self.logger.info(f"  ✅ p50 延迟：{lat_p50:.1f} μs (< {self.p50_latency_us} μs)")
        
        # 验证 p99
        if lat_p99 > self.p99_latency_us:
            self.record_failure(
                "p99 延迟",
                f"< {self.p99_latency_us} μs",
                f"{lat_p99:.1f} μs",
                "p99 延迟超出限制"
            )
        else:
            self.logger.info(f"  ✅ p99 延迟：{lat_p99:.1f} μs (< {self.p99_latency_us} μs)")
        
        # 验证 p99.99
        if lat_p9999 > self.p9999_latency_us:
            self.record_failure(
                "p99.99 延迟",
                f"< {self.p9999_latency_us} μs",
                f"{lat_p9999:.1f} μs",
                "p99.99 延迟超出限制"
            )
        else:
            self.logger.info(f"  ✅ p99.99 延迟：{lat_p9999:.1f} μs (< {self.p9999_latency_us} μs)")
        
        return True
    
    def teardown(self) -> bool:
        """测试后清理"""
        return super().teardown()
