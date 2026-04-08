#!/usr/bin/env python3
# -*- coding: utf-8 -*-

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


class Test(TestCase):
    name = "seq_write_burst"
    description = "Sequential write performance test (Burst mode)"

    def __init__(
        self,
        device: str = '/dev/ufs0',
        test_dir: Path = None,
        verbose: bool = False,
        logger=None,
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
        super().__init__(device, test_dir, verbose, logger)
        self.test_file = self.get_test_file_path('seq_write')
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

        self.fio = FIO(timeout=self.runtime + self.ramp_time + 30, logger=self.logger)
        self.ufs = UFSDevice(device, logger=self.logger)

    def setup(self) -> bool:
        self.logger.info("Checking prerequisites...")

        if not self.ufs.exists():
            self.logger.error(f"Device does not exist: {self.device}")
            return False

        if not self.ufs.check_available_space(min_gb=2.0):
            return False

        try:
            result = subprocess.run(['which', 'fio'], capture_output=True)
            if result.returncode != 0:
                self.logger.error("FIO tool not installed")
                return False
        except Exception as e:
            self.logger.error(f"FIO check failed: {e}")
            return False

        if not os.access(self.device, os.R_OK | os.W_OK):
            self.logger.error(f"Insufficient device permissions: {self.device}")
            return False

        health = self.ufs.get_health_status()
        if health['status'] != 'OK':
            self.logger.warning(f"Device health status abnormal: {health['status']}")

        self.logger.info("Test Configuration:")
        self.logger.info(f"  bs={self.bs}, size={self.size}, runtime={self.runtime}s")
        self.logger.info(f"  ioengine={self.ioengine}, iodepth={self.iodepth}, ramp_time={self.ramp_time}s")
        self.logger.info(f"  target_bw={self.target_bw_mbps} MB/s, max_avg_lat={self.max_avg_latency_us} us")

        self.logger.info("Prerequisites check passed")
        return True

    def _parse_size_mb(self, size_str: str) -> int:
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
                return 1024

    def execute(self) -> Dict[str, Any]:
        self.logger.info("Starting sequential write performance test...")

        try:
            if Path(self.test_file).exists():
                os.unlink(self.test_file)

            metrics_obj = self.fio.run_seq_write(
                filename=self.test_file,
                direct=True,
                size=self.size,
                runtime=self.runtime,
                bs=self.bs,
                ioengine=self.ioengine,
                iodepth=self.iodepth,
                ramp_time=self.ramp_time
            )

            lat = metrics_obj.latency_ns
            metrics = {
                'bandwidth': {
                    'value': metrics_obj.bandwidth['value'],
                    'unit': 'MB/s',
                    'target': self.target_bw_mbps
                },
                'iops': {
                    'value': metrics_obj.iops['value'],
                    'unit': 'IOPS'
                },
                'latency_avg': {
                    'value': lat.get('mean', 0) / 1000,
                    'unit': 'us',
                    'target': self.max_avg_latency_us
                },
                'latency_p99': {
                    'value': lat.get('percentile', {}).get('99.0', 0) / 1000,
                    'unit': 'us'
                },
                'latency_p9999': {
                    'value': lat.get('percentile', {}).get('99.99', 0) / 1000,
                    'unit': 'us'
                },
                'latency_p99999': {
                    'value': lat.get('percentile', {}).get('99.999', 0) / 1000,
                    'unit': 'us',
                    'target': self.max_tail_latency_us
                },
                'runtime': {
                    'value': metrics_obj.raw.get('jobs', [{}])[0].get('elapsed', 0),
                    'unit': 's'
                }
            }

            self.logger.info("Test completed, results summary:")
            self.logger.info(f"  Bandwidth: {metrics['bandwidth']['value']:.1f} MB/s (target: >= {self.target_bw_mbps})")
            self.logger.info(f"  IOPS: {metrics['iops']['value']:.0f}")
            self.logger.info(f"  Average Latency: {metrics['latency_avg']['value']:.1f} us (target: < {self.max_avg_latency_us})")
            self.logger.info(f"  p99.999 Tail Latency: {metrics['latency_p99999']['value']:.1f} us (target: < {self.max_tail_latency_us})")

            return metrics

        except FIOError as e:
            self.logger.error(f"FIO execution failed: {e}")
            raise

    def validate(self, result: Dict[str, Any]) -> bool:
        self.logger.info("Validating test results...")

        all_ok = True

        bw = result['bandwidth']['value']
        target = self.target_bw_mbps
        if bw < target * 0.9:
            self.record_failure(
                "Sequential Write Bandwidth",
                f">= {target} MB/s",
                f"{bw:.1f} MB/s",
                "Bandwidth significantly below target"
            )
            all_ok = False
        elif bw < target:
            self.logger.warning(
                f"Bandwidth below target: {bw:.1f} MB/s < {target} MB/s,"
                " but within tolerance (>= 90%), test continues"
            )

        avg_lat = result['latency_avg']['value']
        if avg_lat > self.max_avg_latency_us:
            self.record_failure(
                "Average Latency",
                f"< {self.max_avg_latency_us} us",
                f"{avg_lat:.1f} us",
                "Average latency exceeds limit"
            )
            all_ok = False

        tail_lat = result['latency_p99999']['value']
        if tail_lat > self.max_tail_latency_us:
            self.record_failure(
                "p99.999 Tail Latency",
                f"< {self.max_tail_latency_us} us",
                f"{tail_lat:.1f} us",
                "Tail latency spread exceeds limit"
            )
            all_ok = False

        self._check_postcondition()

        if all_ok:
            self.logger.info("All validations passed")
        else:
            self.logger.warning(f"Total {len(self._failures)} validations failed")

        return True

    def teardown(self) -> bool:
        return super().teardown()
