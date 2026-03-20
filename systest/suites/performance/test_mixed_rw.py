#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
混合读写性能测试
测试 UFS 设备的 70% 读/30% 写混合负载性能
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
    """混合读写性能测试"""
    
    name = "mixed_rw_7030"
    description = "混合读写性能测试（70% 读/30% 写）"
    
    def __init__(self, device: str = '/dev/ufs0', verbose: bool = False):
        super().__init__(device, verbose)
        self.test_file = f"/tmp/ufs_test_mixed_rw"
        self.size = "1G"
        self.runtime = 60
        self.block_size = "4k"
        self.iodepth = 32
        self.rw_mix = 70  # 70% 读
        self.target_read_iops = 150000
        self.target_write_iops = 50000
    
    def setup(self) -> bool:
        try:
            Path('/tmp').mkdir(parents=True, exist_ok=True)
            # 预填充数据
            logger.info("预填充测试数据...")
            fill_cmd = ['fio', '--name=fill', f'--filename={self.test_file}',
                       '--rw=write', '--bs=1M', '--size=' + self.size,
                       '--ioengine=sync', '--direct=1', '--numjobs=1']
            subprocess.run(fill_cmd, capture_output=True, timeout=120)
            return True
        except Exception as e:
            logger.error(f"Setup 失败：{e}")
            return False
    
    def execute(self) -> dict:
        fio_cmd = [
            'fio',
            '--name=mixed_rw',
            f'--filename={self.test_file}',
            f'--rw=randrw,{self.rw_mix}',
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
        
        logger.info(f"执行 FIO 混合读写测试 ({self.rw_mix}% 读)...")
        
        result = subprocess.run(fio_cmd, capture_output=True, text=True, timeout=self.runtime + 30)
        
        if result.returncode != 0:
            raise RuntimeError(f"FIO 执行失败：{result.stderr}")
        
        fio_output = json.loads(result.stdout)
        read_job = fio_output['jobs'][0]['read']
        write_job = fio_output['jobs'][0]['write']
        
        return {
            'read_iops': {'value': read_job['iops'], 'unit': 'IOPS'},
            'write_iops': {'value': write_job['iops'], 'unit': 'IOPS'},
            'read_bw': {'value': read_job['bw_bytes'] / (1024 * 1024), 'unit': 'MB/s'},
            'write_bw': {'value': write_job['bw_bytes'] / (1024 * 1024), 'unit': 'MB/s'},
            'latency_avg': {'value': read_job['lat_ns']['mean'] / 1000, 'unit': 'μs'},
        }
    
    def validate(self, result: dict) -> bool:
        read_pass = result['read_iops']['value'] >= self.target_read_iops
        write_pass = result['write_iops']['value'] >= self.target_write_iops
        passed = read_pass and write_pass
        
        logger.info(f"读取：{result['read_iops']['value']:.0f} IOPS {'✅' if read_pass else '❌'}")
        logger.info(f"写入：{result['write_iops']['value']:.0f} IOPS {'✅' if write_pass else '❌'}")
        
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
