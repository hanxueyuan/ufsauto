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
from fio_wrapper import FIO, FIOError, FIOConfig
from ufs_utils import UFSDevice


class Test(TestCase):
    name = "rand_write_burst"
    description = "Random write performance test (4K QD32)"

    def __init__(
        self,
        device: str = '/dev/ufs0',
        test_dir: Path = None,
        verbose: bool = False,
        logger=None,
        bs: str = '4k',
        size: str = '1G',
        runtime: int = 60,
        ramp_time: int = 10,
        ioengine: str = 'sync',
        iodepth: int = 32,
        target_iops: float = 100000,
        max_avg_latency_us: float = 150,
        max_tail_latency_us: float = 8000,
    ):
        super().__init__(device, test_dir, verbose, logger)
        self.test_file = self.get_test_file_path('rand_write')
        self.bs = bs
        self.size = size
        self.runtime = runtime
        self.ramp_time = ramp_time
        self.ioengine = ioengine
        self.iodepth = iodepth
        self.target_iops = target_iops
        self.max_avg_latency_us = max_avg_latency_us
        self.max_tail_latency_us = max_tail_latency_us

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
            self.logger.error(f"Insufficient device permissions")
            return False

        health = self.ufs.get_health_status()
        if health['status'] != 'OK':
            self.logger.warning(f"Device health status abnormal: {health['status']}")

        self.logger.info("Test Configuration:")
        self.logger.info(f"  bs={self.bs}, size={self.size}, runtime={self.runtime}s, iodepth={self.iodepth}")
        self.logger.info(f"  ioengine={self.ioengine}, ramp_time={self.ramp_time}s")
        self.logger.info(f"  target_iops={self.target_iops}, max_avg_lat={self.max_avg_latency_us} us")

        self.logger.info("Prerequisites check passed")
        return True

    def execute(self) -> Dict[str, Any]:
        self.logger.info("Starting random write performance test...")

        try:
            if Path(self.test_file).exists():
                os.unlink(self.test_file)

            metrics_obj = self.fio.run_rand_write(
                filename=self.test_file,
                direct=True,
                size=self.size,
                runtime=self.runtime,
                bs=self.bs,
                iodepth=self.iodepth,
                ioengine=self.ioengine,
                ramp_time=self.ramp_time
            )

            lat = metrics_obj.latency_ns
            metrics = {
                'iops': {
                    'value': metrics_obj.iops['value'],
                    'unit': 'IOPS',
                    'target': self.target_iops
                },
                'bandwidth': {
                    'value': metrics_obj.bandwidth['value'],
                    'unit': 'MB/s'
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
            self.logger.info(f"  IOPS: {metrics['iops']['value']:.0f} (target: >= {self.target_iops})")
            self.logger.info(f"  Bandwidth: {metrics['bandwidth']['value']:.1f} MB/s")
            self.logger.info(f"  Average Latency: {metrics['latency_avg']['value']:.1f} us (target: < {self.max_avg_latency_us})")
            self.logger.info(f"  p99.999 Tail Latency: {metrics['latency_p99999']['value']:.1f} us (target: < {self.max_tail_latency_us})")

            return metrics

        except FIOError as e:
            self.logger.error(f"FIO execution failed: {e}")
            raise

    def validate(self, result: Dict[str, Any]) -> bool:
        self.logger.info("Validating test results...")

        all_ok = True

        iops = result['iops']['value']
        target = self.target_iops
        if iops < target * 0.9:
            self.record_failure(
                "Random Write IOPS",
                f">= {target:.0f} IOPS",
                f"{iops:.0f} IOPS",
                "IOPS significantly below target"
            )
            all_ok = False
        elif iops < target:
            self.logger.warning(
                f"IOPS below target: {iops:.0f} < {target:.0f},"
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
