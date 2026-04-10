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

import sys
from pathlib import Path

core_dir = Path(__file__).parent.parent.parent / 'core'
tools_dir = Path(__file__).parent.parent.parent / 'tools'
sys.path.insert(0, str(core_dir))
sys.path.insert(0, str(tools_dir))

from runner import TestCase
from .base import PerformanceTestCase

class Test(PerformanceTestCase):
    """Random read performance test"""

    name = "rand_read_burst"
    description = "Random read performance test (4K QD32)"

    fio_rw = 'randread'
    fio_bs = '4k'
    fio_size = '1G'
    fio_runtime = 60
    fio_iodepth = 32
    fio_ramp_time = 10
    fio_ioengine = 'sync'

    target_iops = 120000
    max_avg_latency_us = 160
    max_tail_latency_us = 5000
