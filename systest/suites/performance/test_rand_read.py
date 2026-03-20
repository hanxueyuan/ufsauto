#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
随机读性能测试
测试 UFS 设备的随机读取性能（4K QD32）
"""

import subprocess
import json
import logging
from pathlib import Path
import sys

# 添加 core 模块路径
core_dir = Path(__file__).parent.parent.parent / 'core'
sys.path.insert(0, str(core_dir))
from runner import TestCase

logger = logging.getLogger(__name__)


class Test(TestCase):
    """随机读性能测试"""
    
    name = "rand_read_burst"
    description = "随机读取性能测试（4K QD32）"
    
    def __init__(self, device: str = '/dev/ufs0', verbose: bool = False):
        super().__init__(device, verbose)
        self.test_file = f"/tmp/ufs_test_rand_read"
        self.size = "1G"
        self.runtime = 60
        self.block_size = "4k"
        self.iodepth = 32
        self.target = 200000  # IOPS (UFS 3.1 128GB 目标值)
    
    def setup(self) -> bool:
        """测试前准备"""
        try:
            Path('/tmp').mkdir(parents=True, exist_ok=True)
            
            # 预填充数据（随机读需要有效数据）
            logger.info("预填充测试数据...")
            fill_cmd = [
                'fio',
                '--name=fill',
                f'--filename={self.test_file}',
                '--rw=write',
                '--bs=1M',
                '--size=' + self.size,
                '--ioengine=sync',
                '--direct=1',
                '--numjobs=1'
            ]
            subprocess.run(fill_cmd, capture_output=True, timeout=120)
            
            return True
        except Exception as e:
            logger.error(f"Setup 失败：{e}")
            return False
    
    def execute(self) -> dict:
        """执行 FIO 随机读测试"""
        fio_cmd = [
            'fio',
            '--name=rand_read',
            f'--filename={self.test_file}',
            '--rw=randread',
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
        
        logger.info(f"执行 FIO 随机读测试 (4K QD{self.iodepth})...")
        
        result = subprocess.run(
            fio_cmd,
            capture_output=True,
            text=True,
            timeout=self.runtime + 30
        )
        
        if result.returncode != 0:
            raise RuntimeError(f"FIO 执行失败：{result.stderr}")
        
        # 解析 FIO 输出
        fio_output = json.loads(result.stdout)
        job = fio_output['jobs'][0]['read']
        
        return {
            'iops': {
                'value': job['iops'],
                'unit': 'IOPS'
            },
            'bandwidth': {
                'value': job['bw_bytes'] / (1024 * 1024),
                'unit': 'MB/s'
            },
            'latency_avg': {
                'value': job['lat_ns']['mean'] / 1000,
                'unit': 'μs'
            },
            'latency_99999': {
                'value': job['lat_ns']['percentile']['99.999'] / 1000,
                'unit': 'μs'
            }
        }
    
    def validate(self, result: dict) -> bool:
        """验证结果是否达标"""
        actual = result['iops']['value']
        passed = actual >= self.target
        
        if passed:
            logger.info(f"✅ 性能达标：{actual:.0f} IOPS ≥ {self.target} IOPS")
        else:
            logger.warning(f"❌ 性能不达标：{actual:.0f} IOPS < {self.target} IOPS")
        
        return passed
    
    def teardown(self) -> bool:
        """清理测试文件"""
        try:
            test_path = Path(self.test_file)
            if test_path.exists():
                test_path.unlink()
                logger.debug(f"清理测试文件：{self.test_file}")
            return True
        except Exception as e:
            logger.warning(f"清理失败：{e}")
            return True
