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

import sys
from pathlib import Path

core_dir = Path(__file__).parent.parent.parent / 'core'
tools_dir = Path(__file__).parent.parent.parent / 'tools'
sys.path.insert(0, str(core_dir))
sys.path.insert(0, str(tools_dir))

from runner import TestCase
from .base import PerformanceTestCase


class Test(PerformanceTestCase):
    """Mixed random read/write performance test"""

    name = "mixed_rw"
    description = "Mixed random read/write performance test (70% read/30% write)"

    # FIO 配置
    fio_rw = 'randrw'
    fio_bs = '4k'
    fio_size = '1G'
    fio_runtime = 60
    fio_iodepth = 32
    fio_ramp_time = 10
    fio_ioengine = 'sync'
    fio_rwmixread = 70  # 70% 读，30% 写

    # 性能目标
    target_iops = 150000  # 总 IOPS
    max_avg_latency_us = 200
    max_tail_latency_us = 8000
