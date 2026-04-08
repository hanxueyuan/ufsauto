#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Mixed Read/Write Performance Test
Test UFS device mixed random read/write IOPS (70% read/30% write, 4K QD32)

Test Case ID: t_perf_MixedRw_005
Test Objective: Verify UFS device mixed read/write IOPS performance
Prerequisites:
    1. UFS device is mounted
    2. Sufficient available space (>= 2GB)
    3. FIO tool is installed
Test Steps:
    1. Execute FIO mixed read/write test (4K block, QD32, 70/30, 60s, including 10s ramp)
    2. Validate total IOPS, read/write IOPS distribution, latency meet targets
Expected Metrics (reference):
    - Total IOPS >= 150,000
    - Average latency < 200 us
    - p99.999 tail latency < 8000 us
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
from fio_wrapper import FIO, FIOError, FIOConfig
from ufs_utils import UFSDevice


class Test(TestCase):
    """Mixed read/write performance test"""

    name = "mixed_rw"
    description = "Mixed random read/write performance test (70% read/30% write)"

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
        rw_mix: int = 70,
        target_total_iops: float = 150000,  # Adjust based on specific device
        max_avg_latency_us: float = 200,  # Adjust based on specific device
        max_tail_latency_us: float = 8000,  # Adjust based on specific device
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

        self.logger.info("Test Configuration:")
        self.logger.info(f"  bs={self.bs}, size={self.size}, runtime={self.runtime}s, iodepth={self.iodepth}")
        self.logger.info(f"  rw_mix={self.rw_mix}% read, ioengine={self.ioengine}, ramp_time={self.ramp_time}s")
        self.logger.info(f"  target_total_iops={self.target_total_iops}")

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
        """Execute test logic"""
        self.logger.info("Starting mixed read/write performance test...")

        try:
            # Build FIO test parameters
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

            # Add direct=True parameter
            fio_args['direct'] = True
            result = self.fio.run(FIOConfig(**fio_args))

            # Parse results
            job_data = result.raw.get('jobs', [{}])[0]

            # Extract read/write IOPS
            read_iops = job_data.get('read', {}).get('iops', 0)
            write_iops = job_data.get('write', {}).get('iops', 0)
            total_iops = read_iops + write_iops

            # Extract latency data
            read_lat_ns = job_data.get('read', {}).get('lat_ns', {})
            write_lat_ns = job_data.get('write', {}).get('lat_ns', {})

            avg_read_latency_us = read_lat_ns.get('mean', 0) / 1000  # Convert to us
            avg_write_latency_us = write_lat_ns.get('mean', 0) / 1000  # Convert to us
            # IOPS weighted average latency
            if total_iops > 0:
                avg_latency_us = (avg_read_latency_us * read_iops + avg_write_latency_us * write_iops) / total_iops
            else:
                avg_latency_us = (avg_read_latency_us + avg_write_latency_us) / 2

            # Extract tail latency
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
        """
        Validate results.
        For performance tests, return True. Metrics compliance is recorded via failures.
        """
        # Check if there are errors
        if 'error' in result:
            self.record_failure(
                "FIO Execution",
                "Completed successfully",
                f"Execution failed: {result['error']}",
                "FIO execution failed"
            )
            return True  # Let framework handle failure recording

        # Validate performance metrics
        total_iops = result.get('total_iops', 0)
        avg_latency_us = result.get('avg_latency_us', float('inf'))
        p99999_latency_us = result.get('p99999_latency_us', float('inf'))

        # Record metrics compliance
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

        # Execute Postcondition check (hardware reliability validation)
        self._check_postcondition()

        if hasattr(self, '_failures') and len(self._failures) > 0:
            self.logger.warning(f"Total {len(self._failures)} validations failed")

        return True  # Performance test always returns True, framework judges final status based on failures

    def teardown(self) -> bool:
        """Post-test cleanup - parent class auto cleans test file"""
        return super().teardown()
