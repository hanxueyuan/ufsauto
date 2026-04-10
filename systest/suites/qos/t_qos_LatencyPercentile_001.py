#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
QoS Latency Percentile Test
Test UFS device latency distribution and percentile metrics

Test Case ID: t_qos_LatencyPercentile_001
Test Objective: Verify UFS device latency percentile metrics (p50/p99/p99.99)
Prerequisites:
    1. UFS device is mounted
    2. Sufficient available space (>= 2GB)
    3. FIO tool is installed
Test Steps:
    1. Execute FIO random read test (4K block, QD=1, 60s)
    2. Record p50/p99/p99.99 latency
    3. Validate latency percentiles meet targets
Expected Metrics:
    - p50 latency < 50 us
    - p99 latency < 200 us
    - p99.99 latency < 500 us
Test Duration: Approximately 60 seconds
"""

import sys
import json
from datetime import datetime
from pathlib import Path

core_dir = Path(__file__).parent.parent.parent / 'core'
tools_dir = Path(__file__).parent.parent.parent / 'tools'
sys.path.insert(0, str(core_dir))
sys.path.insert(0, str(tools_dir))

from systest.core.runner import TestCase
from systest.tools.fio_wrapper import FIO, FIOError
from systest.tools.ufs_utils import UFSDevice
from typing import Dict, Any

class Test(TestCase):
    """QoS latency percentile test"""

    name = "qos_latency_percentile"
    description = "QoS latency percentile test (p50/p99/p99.99)"

    def __init__(
        self,
        device: str = '/dev/sda',
        test_dir: Path = None,
        verbose: bool = False,
        logger=None,
        mode: str = None,
        bs: str = '4k',
        size: str = '1G',
        runtime: int = 60,
        ramp_time: int = 10,
        ioengine: str = 'sync',
        iodepth: int = 1,
        p50_latency_us: float = 50,
        p99_latency_us: float = 200,
        p9999_latency_us: float = 500,
    ):
        super().__init__(device, test_dir, verbose, logger)
        self.mode = mode
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

        # Adjust runtime based on mode
        if mode == 'production':
            self.runtime = max(runtime, 300)  # Production mode: at least 300s
        
        self.fio = FIO(timeout=self.runtime + self.ramp_time + 30, logger=self.logger)
        self.ufs = UFSDevice(device, logger=self.logger)

    def setup(self) -> bool:
        """Pre-test setup - Check prerequisites"""
        self.logger.info("Checking prerequisites...")

        if not self.ufs.exists():
            self.logger.error(f"Device does not exist: {self.device}")
            return False
        self.logger.debug(f"Device exists: {self.device}")

        if not self.ufs.check_available_space(min_gb=2.0):
            self.logger.error("Insufficient available space (requires >= 2GB)")
            return False
        self.logger.debug(f"Available space sufficient (>= 2GB)")

        import subprocess
        try:
            result = subprocess.run(['which', 'fio'], capture_output=True, text=True)
            if result.returncode != 0:
                self.logger.error("FIO tool not installed")
                return False
            self.logger.debug(f"FIO installed")
        except Exception as e:
            self.logger.error(f"FIO check failed: {e}")
            return False

        if not self.ufs.check_device():
            self.logger.error(f"Insufficient device permissions: {self.device}")
            return False
        self.logger.debug(f"Device permissions OK")

        health = self.ufs.get_health_status()
        self._pre_test_health = health
        self.logger.debug(f"Health baseline: {health['status']}")

        self.logger.info("Prerequisites check passed")
        return True

    def execute(self) -> Dict[str, Any]:
        """Execute QoS latency percentile test"""
        self.start_time = datetime.now()
        self.logger.info("Starting QoS latency percentile test...")
        self.logger.info(f"  bs={self.bs}, size={self.size}, runtime={self.runtime}s, iodepth={self.iodepth}")

        try:
            self.logger.info("Executing FIO random read test (QD=1)...")
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

            lat_ns = metrics_obj.latency_ns
            percentiles = lat_ns.get('percentile', {})

            lat_distribution = {
                'p50': percentiles.get('50.000000', 0) / 1000,
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

            self.logger.info("Latency distribution data:")
            self.logger.info(f"  min:     {lat_distribution['min']:.1f} us")
            self.logger.info(f"  p50:     {lat_distribution['p50']:.1f} us")
            self.logger.info(f"  p90:     {lat_distribution['p90']:.1f} us")
            self.logger.info(f"  p95:     {lat_distribution['p95']:.1f} us")
            self.logger.info(f"  p99:     {lat_distribution['p99']:.1f} us")
            self.logger.info(f"  p99.9:   {lat_distribution['p99.9']:.1f} us")
            self.logger.info(f"  p99.99:  {lat_distribution['p99.99']:.1f} us")
            self.logger.info(f"  p99.999: {lat_distribution['p99.999']:.1f} us")
            self.logger.info(f"  max:     {lat_distribution['max']:.1f} us")
            self.logger.info(f"  mean:    {lat_distribution['mean']:.1f} us")
            self.logger.info(f"  stddev:  {lat_distribution['stddev']:.1f} us")

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
                self.logger.info(f"Latency distribution data saved: {distribution_file}")
            except Exception as e:
                self.logger.warning(f"Failed to save distribution data: {e}")

            return lat_distribution

        except FIOError as e:
            self.logger.error(f"FIO execution failed: {e}")
            raise

    def validate(self, result: Dict[str, Any]) -> bool:
        """Validate latency percentiles meet targets"""
        self.logger.info("Validating latency percentile metrics...")

        lat_p50 = result.get('p50', 0)
        lat_p99 = result.get('p99', 0)
        lat_p9999 = result.get('p99.99', 0)

        if lat_p50 > self.p50_latency_us:
            self.record_failure(
                "p50 Latency",
                f"< {self.p50_latency_us} us",
                f"{lat_p50:.1f} us",
                "p50 latency exceeds limit"
            )
        else:
            self.logger.info(f"  p50 latency: {lat_p50:.1f} us (< {self.p50_latency_us} us)")

        if lat_p99 > self.p99_latency_us:
            self.record_failure(
                "p99 Latency",
                f"< {self.p99_latency_us} us",
                f"{lat_p99:.1f} us",
                "p99 latency exceeds limit"
            )
        else:
            self.logger.info(f"  p99 latency: {lat_p99:.1f} us (< {self.p99_latency_us} us)")

        if lat_p9999 > self.p9999_latency_us:
            self.record_failure(
                "p99.99 Latency",
                f"< {self.p9999_latency_us} us",
                f"{lat_p9999:.1f} us",
                "p99.99 latency exceeds limit"
            )
        else:
            self.logger.info(f"  p99.99 latency: {lat_p9999:.1f} us (< {self.p9999_latency_us} us)")

        self._check_postcondition()

        return True

    def teardown(self) -> bool:
        """Post-test cleanup"""
        return super().teardown()
