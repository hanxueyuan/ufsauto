#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Sequential Read Performance Test
Test UFS device sequential read bandwidth (Burst mode)

Test Case ID: t_perf_SeqReadBurst_001
Test Objective: Verify UFS device sequential read Burst performance meets targets
Prerequisites:
    1. UFS device is mounted
    2. Sufficient available space (>= 2GB)
    3. FIO tool is installed
Test Steps:
    1. Prefill test file (avoid reading sparse file)
    2. Execute FIO sequential read test (128K block, 60s, including 10s ramp)
    3. Validate bandwidth, IOPS, latency meet targets
Expected Results:
    - Bandwidth >= 2100 MB/s
    - Average latency < 200 us
    - p99.999 tail latency < 5000 us (5ms)
Test Duration: Approximately 70 seconds (including ramp)
"""

import sys
from pathlib import Path

core_dir = Path(__file__).parent.parent.parent / 'core'
tools_dir = Path(__file__).parent.parent.parent / 'tools'
sys.path.insert(0, str(core_dir))
sys.path.insert(0, str(tools_dir))

from systest.core.runner import TestCase
from .base import PerformanceTestCase

class Test(PerformanceTestCase):
    """Sequential read performance test"""

    name = "seq_read_burst"
    description = "Sequential read performance test (Burst mode)"

    fio_rw = 'read'
    fio_bs = '128k'
    fio_size = '1G'
    fio_runtime = 60
    fio_iodepth = 1
    fio_ramp_time = 10
    fio_ioengine = 'sync'

    target_bandwidth_mbps = 2100
    max_avg_latency_us = 200
    max_tail_latency_us = 5000
