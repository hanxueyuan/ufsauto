#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
性能测试基类 - 消除重复代码

使用方法:
    子类只需定义测试特定的配置参数，无需重复实现 setup/execute/validate 方法。

Example:
    class SeqReadTest(PerformanceTestCase):
        name = "seq_read"
        description = "顺序读性能测试"
        fio_rw = 'read'
        fio_bs = '128k'
        target_bandwidth_mbps = 2100
"""

import subprocess
from pathlib import Path
from typing import Dict, Any, Optional

from runner import TestCase
from fio_wrapper import FIO, FIOConfig, FIOError
from ufs_utils import UFSDevice

class PerformanceTestCase(TestCase):
    """性能测试基类

    提供通用的：
    - 前置条件检查（设备、空间、FIO、权限）
    - FIO 测试执行
    - 性能指标验证
    - Postcondition 检查
    """

    name: str = "base_performance_test"
    description: str = "性能测试基类"

    target_bandwidth_mbps: float = 0
    target_iops: float = 0
    max_avg_latency_us: float = float('inf')
    max_tail_latency_us: float = float('inf')

    fio_rw: str = 'read'
    fio_bs: str = '4k'
    fio_size: str = '1G'
    fio_runtime: int = 60
    fio_iodepth: int = 1
    fio_ramp_time: int = 0
    fio_ioengine: str = 'sync'
    fio_rwmixread: int = 70

    def __init__(self, device: str = '/dev/sda', test_dir: Path = None, verbose: bool = False, logger=None):
        super().__init__(device, test_dir, verbose, logger)
        self.fio = FIO(
            timeout=self.fio_runtime + self.fio_ramp_time + 30,
            logger=self.logger
        )
        self.ufs = UFSDevice(device, logger=self.logger)
        self.test_file: Optional[Path] = None

    def setup(self) -> bool:
        """通用前置条件检查"""
        self.logger.info("开始检查前置条件...")

        if not self.ufs.exists():
            detected_device = self._auto_detect_device()
            if detected_device:
                self.logger.info(f"设备 {self.device} 不存在，使用检测到的设备：{detected_device}")
                self.device = detected_device
                self.ufs = UFSDevice(self.device, logger=self.logger)
            else:
                self.logger.warning(f"设备不存在：{self.device}（继续验证）")
        else:
            self.logger.debug(f"📊 设备存在：{self.device}")

        if not self.ufs.check_available_space(min_gb=2.0):
            self.logger.error("可用空间不足（需要≥2GB）")
            return False
        self.logger.debug(f"📊 可用空间充足（≥2GB）")

        try:
            result = subprocess.run(['which', 'fio'], capture_output=True)
            if result.returncode != 0:
                self.logger.error("FIO 工具未安装")
                return False
            self.logger.debug(f"📊 FIO 已安装")
        except Exception as e:
            self.logger.error(f"检查 FIO 失败：{e}")
            return False

        try:
            import os
            if not os.access(self.device, os.R_OK | os.W_OK):
                self.logger.error(f"设备权限不足：{self.device}")
                return False
            self.logger.debug(f"📊 设备权限正常")
        except Exception as e:
            self.logger.error(f"检查权限失败：{e}")
            return False

        self.test_file = self.get_test_file_path(self.name)

        self.logger.info("=" * 60)
        self.logger.info("📋 测试配置详情:")
        self.logger.info("=" * 60)
        self.logger.info(f"  FIO 参数:")
        self.logger.info(f"    - rw (读写模式): {self.fio_rw}")
        self.logger.info(f"    - bs (块大小): {self.fio_bs}")
        self.logger.info(f"    - size (测试文件大小): {self.fio_size}")
        self.logger.info(f"    - runtime (测试时长): {self.fio_runtime}s")
        self.logger.info(f"    - ramp_time (预热时间): {self.fio_ramp_time}s")
        self.logger.info(f"    - iodepth (队列深度): {self.fio_iodepth}")
        self.logger.info(f"    - ioengine (IO 引擎): {self.fio_ioengine}")
        if self.fio_rw == 'randrw' and self.fio_rwmixread:
            self.logger.info(f"    - rwmixread (读混合比例): {self.fio_rwmixread}%")
        self.logger.info(f"")
        self.logger.info(f"  性能目标:")
        if self.target_bandwidth_mbps > 0:
            self.logger.info(f"    - 带宽：≥ {self.target_bandwidth_mbps} MB/s")
        if self.target_iops > 0:
            self.logger.info(f"    - IOPS: ≥ {self.target_iops}")
        if self.max_avg_latency_us < float('inf'):
            self.logger.info(f"    - 平均延迟：≤ {self.max_avg_latency_us} μs")
        if self.max_tail_latency_us < float('inf'):
            self.logger.info(f"    - 尾部延迟 (p99.999): ≤ {self.max_tail_latency_us} μs")
        self.logger.info("=" * 60)

        self.logger.info("✅ 前置条件检查通过")
        return True

    def _auto_detect_device(self) -> Optional[str]:
        """自动检测可用的块设备"""
        import os
        import glob

        device_priority = ['sda', 'vda', 'mmcblk0', 'nvme0n1']

        for device_name in device_priority:
            device_path = f'/dev/{device_name}'
            if os.path.exists(device_path):
                self.logger.debug(f"找到可用设备：{device_path}")
                return device_path

        try:
            block_devices = glob.glob('/dev/sd*') + glob.glob('/dev/vd*') + glob.glob('/dev/mmcblk*') + glob.glob('/dev/nvme*')
            if block_devices:
                for device in sorted(block_devices):
                    if not device[-1].isdigit():
                        self.logger.debug(f"找到块设备：{device}")
                        return device
        except Exception as e:
            self.logger.debug(f"块设备检测失败：{e}")

        return None

    def execute_fio_test(self, extra_config: dict = None) -> Dict[str, Any]:
        """
        通用 FIO 测试执行

        Args:
            extra_config: 额外的 FIO 配置参数

        Returns:
            性能指标字典
        """
        self.logger.info(f"🚀 开始执行性能测试...")

        fio_config_dict = {
            'name': self.name,
            'filename': str(self.test_file),
            'rw': self.fio_rw,
            'bs': self.fio_bs,
            'size': self.fio_size,
            'runtime': self.fio_runtime,
            'ioengine': self.fio_ioengine,
            'iodepth': self.fio_iodepth,
            'direct': True,
            'time_based': True,
        }

        if self.fio_ramp_time > 0:
            fio_config_dict['ramp_time'] = self.fio_ramp_time

        if self.fio_rw == 'randrw' and self.fio_rwmixread:
            fio_config_dict['rwmixread'] = self.fio_rwmixread

        if extra_config:
            fio_config_dict.update(extra_config)

        try:
            metrics_obj = self.fio.run(FIOConfig(**fio_config_dict))

            job_data = metrics_obj.raw.get('jobs', [{}])[0]

            if self.fio_rw == 'randrw':
                read_stats = job_data.get('read', {})
                write_stats = job_data.get('write', {})

                read_iops = read_stats.get('iops', 0)
                write_iops = write_stats.get('iops', 0)
                iops = read_iops + write_iops

                read_bw = read_stats.get('bw_bytes', 0)
                write_bw = write_stats.get('bw_bytes', 0)
                bandwidth_mbps = (read_bw + write_bw) / (1024 * 1024)

                read_lat_ns = read_stats.get('lat_ns', {})
                write_lat_ns = write_stats.get('lat_ns', {})
                avg_read_lat_us = read_lat_ns.get('mean', 0) / 1000
                avg_write_lat_us = write_lat_ns.get('mean', 0) / 1000
                if iops > 0:
                    avg_latency_us = (avg_read_lat_us * read_iops + avg_write_lat_us * write_iops) / iops
                else:
                    avg_latency_us = (avg_read_lat_us + avg_write_lat_us) / 2

                read_percentiles = read_lat_ns.get('percentile', {})
                write_percentiles = write_lat_ns.get('percentile', {})
                p99999_read = read_percentiles.get('99.999', 0) / 1000
                p99999_write = write_percentiles.get('99.999', 0) / 1000
                p99999_latency_us = max(p99999_read, p99999_write)
            else:
                io_type = 'read' if 'read' in self.fio_rw.lower() else 'write'
                io_stats = job_data.get(io_type, {})

                bandwidth_mbps = io_stats.get('bw_bytes', 0) / (1024 * 1024)
                iops = io_stats.get('iops', 0)

                lat_ns = io_stats.get('lat_ns', {})
                avg_latency_us = lat_ns.get('mean', 0) / 1000
                percentiles = lat_ns.get('percentile', {})
                p99999_latency_us = percentiles.get('99.999', 0) / 1000

            return {
                'bandwidth_mbps': bandwidth_mbps,
                'iops': iops,
                'avg_latency_us': avg_latency_us,
                'p99999_latency_us': p99999_latency_us,
            }

        except FIOError as e:
            self.logger.error(f"FIO 测试失败：{e}")
            return {'error': str(e)}

    def validate_performance(self, metrics: Dict[str, Any]) -> bool:
        """
        通用性能验证 - 量化性能达标比例

        Args:
            metrics: 性能指标字典

        Returns:
            bool: 验证是否通过
        """
        if 'error' in metrics:
            self.record_failure(
                "FIO 执行",
                "成功完成",
                f"执行失败：{metrics['error']}",
                "FIO 执行失败"
            )
            return True

        self.logger.info("=" * 60)
        self.logger.info("📊 性能验证结果:")
        self.logger.info("=" * 60)

        if self.target_bandwidth_mbps > 0:
            bw = metrics.get('bandwidth_mbps', 0)
            bw_ratio = (bw / self.target_bandwidth_mbps) * 100
            if bw_ratio >= 100:
                self.logger.info(f"  ✅ 带宽：{bw:.1f} MB/s / {self.target_bandwidth_mbps} MB/s = {bw_ratio:.1f}% (达标)")
            elif bw_ratio >= 90:
                self.logger.warning(f"  ⚠️  带宽：{bw:.1f} MB/s / {self.target_bandwidth_mbps} MB/s = {bw_ratio:.1f}% (达标率 90-100%，可接受)")
            else:
                self.logger.warning(f"  ⚠️  带宽：{bw:.1f} MB/s / {self.target_bandwidth_mbps} MB/s = {bw_ratio:.1f}% (显著不达标 <90%)")
                self.record_failure(
                    "带宽性能",
                    f"≥ {self.target_bandwidth_mbps} MB/s",
                    f"{bw:.1f} MB/s",
                    f"带宽性能显著不达标 ({bw_ratio:.1f}% < 90%)"
                )

        if self.target_iops > 0:
            iops_val = metrics.get('iops', 0)
            iops_ratio = (iops_val / self.target_iops) * 100
            if iops_ratio >= 100:
                self.logger.info(f"  ✅ IOPS: {iops_val:.0f} / {self.target_iops} = {iops_ratio:.1f}% (达标)")
            elif iops_ratio >= 90:
                self.logger.warning(f"  ⚠️  IOPS: {iops_val:.0f} / {self.target_iops} = {iops_ratio:.1f}% (达标率 90-100%，可接受)")
            else:
                self.logger.warning(f"  ⚠️  IOPS: {iops_val:.0f} / {self.target_iops} = {iops_ratio:.1f}% (显著不达标 <90%)")
                self.record_failure(
                    "IOPS 性能",
                    f"≥ {self.target_iops}",
                    f"{iops_val:.0f}",
                    f"IOPS 性能显著不达标 ({iops_ratio:.1f}% < 90%)"
                )

        if self.max_avg_latency_us < float('inf'):
            lat = metrics.get('avg_latency_us', float('inf'))
            lat_ratio = (lat / self.max_avg_latency_us) * 100 if self.max_avg_latency_us > 0 else 0
            if lat_ratio <= 100:
                self.logger.info(f"  ✅ 平均延迟：{lat:.1f} μs / {self.max_avg_latency_us} μs = {lat_ratio:.1f}% (达标)")
            else:
                self.logger.warning(f"  ⚠️  平均延迟：{lat:.1f} μs / {self.max_avg_latency_us} μs = {lat_ratio:.1f}% (超出限制)")
                self.record_failure(
                    "平均延迟",
                    f"≤ {self.max_avg_latency_us} μs",
                    f"{lat:.1f} μs",
                    f"平均延迟超出限制 ({lat_ratio:.1f}% > 100%)"
                )

        if self.max_tail_latency_us < float('inf'):
            tail_lat = metrics.get('p99999_latency_us', float('inf'))
            tail_ratio = (tail_lat / self.max_tail_latency_us) * 100 if self.max_tail_latency_us > 0 else 0
            if tail_ratio <= 100:
                self.logger.info(f"  ✅ 尾部延迟：{tail_lat:.0f} μs / {self.max_tail_latency_us} μs = {tail_ratio:.1f}% (达标)")
            else:
                self.logger.warning(f"  ⚠️  尾部延迟：{tail_lat:.0f} μs / {self.max_tail_latency_us} μs = {tail_ratio:.1f}% (超出预期)")
                self.record_failure(
                    "尾部延迟 (p99.999)",
                    f"≤ {self.max_tail_latency_us} μs",
                    f"{tail_lat:.0f} μs",
                    f"尾部延迟超出预期 ({tail_ratio:.1f}% > 100%)"
                )

        self.logger.info("=" * 60)

        self._check_postcondition()

        return True

    def execute(self) -> Dict[str, Any]:
        """执行测试逻辑 - 子类通常不需要覆盖"""
        return self.execute_fio_test()

    def validate(self, result: Dict[str, Any]) -> bool:
        """验证结果 - 子类通常不需要覆盖"""
        return self.validate_performance(result)

    def teardown(self) -> bool:
        """测试后清理 - 父类会自动清理测试文件"""
        return super().teardown()
