#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Sequential Write Performance Test
Test UFS device sequential write bandwidth (Burst mode)

Test Case ID: t_perf_SeqWriteBurst_002
Test Objective: Verify UFS device sequential write Burst performance meets targets
Prerequisites:
    1. UFS device is mounted
    2. Sufficient available space (>= 2GB)
    3. FIO tool is installed
Test Steps:
    1. Execute FIO sequential write test (128K block, 60s, including 10s ramp)
    2. Validate bandwidth, IOPS, latency meet targets
Expected Results:
    - Bandwidth >= 1650 MB/s
    - Average latency < 300 us
    - p99.999 tail latency < 8000 us (8ms)
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
    """Sequential write performance test"""

    name = "seq_write_burst"
    description = "Sequential write performance test (Burst mode)"

    fio_rw = 'write'
    fio_bs = '128k'
    fio_size = '1G'
    fio_runtime = 60
    fio_iodepth = 1
    fio_ramp_time = 10
    fio_ioengine = 'sync'

    target_bandwidth_mbps = 1650
    max_avg_latency_us = 300
    max_tail_latency_us = 8000
