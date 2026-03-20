#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
随机写性能测试
测试 UFS 设备的随机写入性能（4K QD32）
"""

import subprocess
import json
import logging
from pathlib import Path
import sys

core_dir = Path(__file__).parent.parent.parent / 'core'
sys.path.insert(0, str(core_dir))
from runner import TestCase

logger = logging.getLogger(__name__)


class Test(TestCase):
    """随机写性能测试"""
    
    name = "rand_write_burst"
    description = "随机写入性能测试（4K QD32）"
    
    def __init__(self, device: str = '/dev/ufs0', verbose: bool = False):
        super().__init__(device, verbose)
        self.test_file = f"/tmp/ufs_test_rand_write"
        self.size = "1G"
        self.runtime = 60
        self.block_size = "4k"
        self.iodepth = 32
        self.target = 60000  # IOPS
    
    def setup(self) -> bool:
        """测试前准备"""
        try:
            Path('/tmp').mkdir(parents=True, exist_ok=True)
            return True
        except Exception as e:
            logger.error(f"Setup 失败：{e}")
            return False
    
    def execute(self) -> dict:
        """执行 FIO 随机写测试"""
        fio_cmd = [
            'fio',
            '--name=rand_write',
            f'--filename={self.test_file}',
            '--rw=randwrite',
            '--bs=' + self.block_size,
            '--size=' + self.size,
            '--runtime=' + str(self.runtime),
            '--time_based',
            '--ioengine=sync',
            '--direct=1',
            '--iodepth=' + str(self.iodepth),
            '--numjobs=1',
            '--group_reporting',
            '--output-format=json'
        ]
        
        logger.info(f"执行 FIO 随机写测试 (4K QD{self.iodepth})...")
        
        result = subprocess.run(
            fio_cmd,
            capture_output=True,
            text=True,
            timeout=self.runtime + 30
        )
        
        if result.returncode != 0:
            raise RuntimeError(f"FIO 执行失败：{result.stderr}")
        
        fio_output = json.loads(result.stdout)
        job = fio_output['jobs'][0]['write']
        
        return {
            'iops': {'value': job['iops'], 'unit': 'IOPS'},
            'bandwidth': {'value': job['bw_bytes'] / (1024 * 1024), 'unit': 'MB/s'},
            'latency_avg': {'value': job['lat_ns']['mean'] / 1000, 'unit': 'μs'},
        }
    
    def validate(self, result: dict) -> bool:
        actual = result['iops']['value']
        passed = actual >= self.target
        logger.info(f"{'✅' if passed else '❌'} {actual:.0f} IOPS {'≥' if passed else '<'} {self.target} IOPS")
        return passed
    
    def teardown(self) -> bool:
        try:
            test_path = Path(self.test_file)
            if test_path.exists():
                test_path.unlink()
            return True
        except Exception as e:
            logger.warning(f"清理失败：{e}")
            return True
