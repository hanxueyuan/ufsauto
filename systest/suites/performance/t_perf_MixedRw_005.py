#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Mixed Random Read/Write Performance Test
Test UFS device mixed random read/write IOPS (70% read/30% write)

Test Case ID: t_perf_MixedRw_005
Test Objective: Verify UFS device mixed read/write IOPS performance
Prerequisites:
    1. UFS device is mounted
    2. Sufficient available space (>= 2GB)
    3. FIO tool is installed
Test Steps:
    1. Execute FIO mixed random read/write test (4K block, QD32, 60s, including 10s ramp)
    2. Validate total IOPS, latency meet targets
Expected Metrics (reference):
    - Total IOPS >= 150,000
    - Average latency < 200 us
    - p99.999 tail latency < 8000 us
Test Duration: Approximately 70 seconds (including ramp)
"""

import os
import sys
import subprocess
from datetime import datetime
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
    """Mixed random read/write performance test"""

    name = "mixed_rw"
    description = "Mixed random read/write performance test (70% read/30% write)"

    def __init__(
        self,
        device: str = '/dev/sda',
        test_dir: Path = None,
        verbose: bool = False,
        logger=None,
        bs: str = '4k',
        size: str = '1G',
        runtime: int = 60,
        ramp_time: int = 10,
        ioengine: str = 'sync',
        iodepth: int = 32,
        rw_mix: int = 70,
        target_total_iops: float = 150000,
        max_avg_latency_us: float = 200,
        max_tail_latency_us: float = 8000,
    ):
        super().__init__(device, test_dir, verbose, logger)
        self.test_file = self.get_test_file_path('mixed_rw')
        self.bs = bs
        self.size = size
        self.runtime = runtime
        self.ramp_time = ramp_time
        self.ioengine = ioengine
        self.iodepth = iodepth
        self.rw_mix = rw_mix
        self.target_total_iops = target_total_iops
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
            self.logger.error(f"Insufficient device permissions: {self.device}")
            return False

        self.logger.info("Test Configuration:")
        self.logger.info(f"  bs={self.bs}, size={self.size}, runtime={self.runtime}s, iodepth={self.iodepth}")
        self.logger.info(f"  rw_mix={self.rw_mix}% read, ioengine={self.ioengine}, ramp_time={self.ramp_time}s")
        self.logger.info(f"  target_total_iops={self.target_total_iops}")

        self.logger.info("Prerequisites check passed")
        return True

    def execute(self) -> Dict[str, Any]:
        self.start_time = datetime.now()
        self.logger.info("Starting mixed read/write performance test...")

        try:
            fio_args = {
                'filename': self.test_file,
                'bs': self.bs,
                'size': self.size,
                'runtime': self.runtime,
                'ramp_time': self.ramp_time,
                'ioengine': self.ioengine,
                'iodepth': self.iodepth,
                'rw': 'randrw',
                'rwmixread': self.rw_mix,
                'output_format': 'json'
            }

            fio_args['direct'] = True
            result = self.fio.run(FIOConfig(**fio_args))

            job_data = result.raw.get('jobs', [{}])[0]

            read_iops = job_data.get('read', {}).get('iops', 0)
            write_iops = job_data.get('write', {}).get('iops', 0)
            total_iops = read_iops + write_iops

            read_lat_ns = job_data.get('read', {}).get('lat_ns') or {}
            write_lat_ns = job_data.get('write', {}).get('lat_ns') or {}

            avg_read_latency_us = read_lat_ns.get('mean', 0) / 1000
            avg_write_latency_us = write_lat_ns.get('mean', 0) / 1000
            if total_iops > 0:
                avg_latency_us = (avg_read_latency_us * read_iops + avg_write_latency_us * write_iops) / total_iops
            else:
                avg_latency_us = (avg_read_latency_us + avg_write_latency_us) / 2

            read_clat_ns = job_data.get('read', {}).get('clat_ns', {}).get('percentile', {})
            write_clat_ns = job_data.get('write', {}).get('clat_ns', {}).get('percentile', {})

            p99999_read_latency_us = read_clat_ns.get('99.999', 0) / 1000
            p99999_write_latency_us = write_clat_ns.get('99.999', 0) / 1000
            p99999_latency_us = max(p99999_read_latency_us, p99999_write_latency_us)

            return {
                'total_iops': total_iops,
                'read_iops': read_iops,
                'write_iops': write_iops,
                'avg_latency_us': avg_latency_us,
                'avg_read_latency_us': avg_read_latency_us,
                'avg_write_latency_us': avg_write_latency_us,
                'p99999_latency_us': p99999_latency_us,
                'p99999_read_latency_us': p99999_read_latency_us,
                'p99999_write_latency_us': p99999_write_latency_us,
                'raw_fio_result': result
            }

        except FIOError as e:
            self.logger.error(f"FIO test failed: {e}")
            return {'error': str(e), 'pass': False}
        except Exception as e:
            self.logger.error(f"Test execution exception: {e}")
            return {'error': str(e), 'pass': False}

    def validate(self, result: Dict[str, Any]) -> bool:
        if 'error' in result:
            self.record_failure(
                "FIO Execution",
                "Completed successfully",
                f"Execution failed: {result['error']}",
                "FIO execution failed"
            )
            return True

        total_iops = result.get('total_iops', 0)
        avg_latency_us = result.get('avg_latency_us', float('inf'))
        p99999_latency_us = result.get('p99999_latency_us', float('inf'))

        if total_iops >= self.target_total_iops:
            self.logger.info(f"Total IOPS: {total_iops:.0f} >= {self.target_total_iops}")
        else:
            self.record_failure(
                "Total IOPS Performance",
                f">= {self.target_total_iops}",
                f"{total_iops:.0f}",
                "Mixed read/write performance below target"
            )

        if avg_latency_us <= self.max_avg_latency_us:
            self.logger.info(f"Average Latency: {avg_latency_us:.1f}us <= {self.max_avg_latency_us}us")
        else:
            self.record_failure(
                "Average Latency",
                f"<= {self.max_avg_latency_us}us",
                f"{avg_latency_us:.1f}us",
                "Average latency exceeds target"
            )

        if p99999_latency_us <= self.max_tail_latency_us:
            self.logger.info(f"Tail Latency (p99.999): {p99999_latency_us:.0f}us <= {self.max_tail_latency_us}us")
        else:
            self.record_failure(
                "Tail Latency (p99.999)",
                f"<= {self.max_tail_latency_us}us",
                f"{p99999_latency_us:.0f}us",
                "Tail latency exceeds target"
            )

        self._check_postcondition()

        if hasattr(self, '_failures') and len(self._failures) > 0:
            self.logger.warning(f"Total {len(self._failures)} validations failed")

        return True

    def teardown(self) -> bool:
        return super().teardown()
