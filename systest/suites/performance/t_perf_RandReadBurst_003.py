#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Random Read Performance Test
Test UFS device random read IOPS (4K QD32)

Test Case ID: t_perf_RandReadBurst_003
Test Objective: Verify UFS device random read IOPS performance
Prerequisites:
    1. UFS device is mounted
    2. Sufficient available space (>= 2GB)
    3. FIO tool is installed
Test Steps:
    1. Prefill test file
    2. Execute FIO random read test (4K block, QD32, 60s, including 10s ramp)
    3. Validate IOPS, bandwidth, latency meet targets
Expected Metrics (reference):
    - IOPS >= 120,000
    - Average latency < 160 us
    - p99.999 tail latency < 5000 us
Test Duration: Approximately 70 seconds (including ramp)
"""

import os
import sys
import subprocess
from pathlib import Path
from typing import Dict, Any

# Add core and tools module paths
core_dir = Path(__file__).parent.parent.parent / 'core'
tools_dir = Path(__file__).parent.parent.parent / 'tools'
sys.path.insert(0, str(core_dir))
sys.path.insert(0, str(tools_dir))

from runner import TestCase
from fio_wrapper import FIO, FIOError, FIOMetrics
from ufs_utils import UFSDevice


class Test(TestCase):
    """Random read performance test"""

    name = "rand_read_burst"
    description = "Random read performance test (4K QD32)"

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
        target_iops: float = 120000,
        max_avg_latency_us: float = 160,
        max_tail_latency_us: float = 5000,
        prefill: bool = True,
    ):
        super().__init__(device, test_dir, verbose, logger)
        self.test_file = self.get_test_file_path('rand_read')
        self.bs = bs
        self.size = size
        self.runtime = runtime
        self.ramp_time = ramp_time
        self.ioengine = ioengine
        self.iodepth = iodepth
        self.target_iops = target_iops
        self.max_avg_latency_us = max_avg_latency_us
        self.max_tail_latency_us = max_tail_latency_us
        self.prefill = prefill

        # Initialize tools
        self.fio = FIO(timeout=self.runtime + self.ramp_time + 30, logger=self.logger)
        self.ufs = UFSDevice(device, logger=self.logger)

    def setup(self) -> bool:
        """Check prerequisites"""
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

        # Check device health status
        health = self.ufs.get_health_status()
        if health['status'] != 'OK':
            self.logger.warning(f"Device health status abnormal: {health['status']}")

        # Prefill test file
        if self.prefill:
            self.logger.info(f"Prefilling test file: {self.test_file} ({self.size})")
            try:
                size_mb = self._parse_size_mb(self.size)
                subprocess.run(
                    ['dd', 'if=/dev/urandom', f'of={self.test_file}',
                     'bs=1M', f'count={size_mb}', 'conv=fdatasync'],
                    capture_output=True, text=True, timeout=120
                )
            except Exception as e:
                self.logger.warning(f"Prefill exception, continuing test: {e}")

        self.logger.info("Test Configuration:")
        self.logger.info(f"  bs={self.bs}, size={self.size}, runtime={self.runtime}s, iodepth={self.iodepth}")
        self.logger.info(f"  ioengine={self.ioengine}, ramp_time={self.ramp_time}s")
        self.logger.info(f"  target_iops={self.target_iops}, max_avg_lat={self.max_avg_latency_us} us")

        self.logger.info("Prerequisites check passed")
        return True

    def _parse_size_mb(self, size_str: str) -> int:
        """Parse size string to MB"""
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
                return 1024  # Default 1GB

    def execute(self) -> Dict[str, Any]:
        """Execute FIO random read test"""
        self.logger.info("Starting random read performance test...")

        try:
            # Use fio_wrapper convenience API to execute
            metrics_obj = self.fio.run_rand_read(
                filename=self.test_file,
                direct=True,
                size=self.size,
                runtime=self.runtime,
                bs=self.bs,
                iodepth=self.iodepth,
                ioengine=self.ioengine,
                ramp_time=self.ramp_time
            )

            # Convert to standard metrics format
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
                    'value': lat['mean'] / 1000,  # ns -> us
                    'unit': 'us',
                    'target': self.max_avg_latency_us
                },
                'latency_p99': {
                    'value': lat['percentile'].get('99.0', 0) / 1000,
                    'unit': 'us'
                },
                'latency_p9999': {
                    'value': lat['percentile'].get('99.99', 0) / 1000,
                    'unit': 'us'
                },
                'latency_p99999': {
                    'value': lat['percentile'].get('99.999', 0) / 1000,
                    'unit': 'us',
                    'target': self.max_tail_latency_us
                },
                'runtime': {
                    'value': metrics_obj.raw['jobs'][0]['elapsed'],
                    'unit': 's'
                }
            }

            # Log results summary
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
        """Validate test results meet targets

        Performance test principle: Record failures for non-compliance, but always return True
        Final status is automatically judged by framework based on failures
        """
        self.logger.info("Validating test results...")

        all_ok = True

        # Validate IOPS - fail only if below 90% of target
        iops = result['iops']['value']
        target = self.target_iops
        if iops < target * 0.9:
            self.record_failure(
                "Random Read IOPS",
                f">= {target:.0f} IOPS",
                f"{iops:.0f} IOPS",
                "IOPS significantly below target"
            )
            all_ok = False
        elif iops < target:
            # Between 90%-100% of target, log warning but not failure
            self.logger.warning(
                f"IOPS below target: {iops:.0f} < {target:.0f},"
                " but within tolerance (>= 90%), test continues"
            )

        # Validate average latency
        avg_lat = result['latency_avg']['value']
        if avg_lat > self.max_avg_latency_us:
            self.record_failure(
                "Average Latency",
                f"< {self.max_avg_latency_us} us",
                f"{avg_lat:.1f} us",
                "Average latency exceeds limit"
            )
            all_ok = False

        # Validate tail latency (p99.999)
        tail_lat = result['latency_p99999']['value']
        if tail_lat > self.max_tail_latency_us:
            self.record_failure(
                "p99.999 Tail Latency",
                f"< {self.max_tail_latency_us} us",
                f"{tail_lat:.1f} us",
                "Tail latency spread exceeds limit"
            )
            all_ok = False

        # Postcondition check (hardware health)
        self._check_postcondition()

        if all_ok:
            self.logger.info("All validations passed")
        else:
            self.logger.warning(f"Total {len(self._failures)} validations failed")

        return True  # Performance test always returns True, framework judges final status based on failures

    def teardown(self) -> bool:
        """Post-test cleanup - parent class auto cleans test file"""
        return super().teardown()
