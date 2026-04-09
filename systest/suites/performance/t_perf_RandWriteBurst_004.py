#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Random Write Performance Test
Test UFS device random write IOPS (4K QD32)

Test Case ID: t_perf_RandWriteBurst_004
Test Objective: Verify UFS device random write IOPS performance
Prerequisites:
    1. UFS device is mounted
    2. Sufficient available space (>= 2GB)
    3. FIO tool is installed
Test Steps:
    1. Execute FIO random write test (4K block, QD32, 60s, including 10s ramp)
    2. Validate IOPS, bandwidth, latency meet targets
Expected Metrics (reference):
    - IOPS >= 100,000
    - Average latency < 150 us
    - p99.999 tail latency < 8000 us
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
    """Random write performance test"""

    name = "rand_write_burst"
    description = "Random write performance test (4K QD32)"

    # FIO 配置
    fio_rw = 'randwrite'
    fio_bs = '4k'
    fio_size = '1G'
    fio_runtime = 60
    fio_iodepth = 32
    fio_ramp_time = 10
    fio_ioengine = 'sync'

    # 性能目标
    target_iops = 100000
    max_avg_latency_us = 150
    max_tail_latency_us = 8000
