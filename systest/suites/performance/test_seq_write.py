#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
顺序写性能测试
测试 UFS 设备的顺序写入带宽（Burst 模式）
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
    """顺序写性能测试"""
    
    name = "seq_write_burst"
    description = "顺序写入性能测试（Burst 模式）"
    
    def __init__(self, device: str = '/dev/ufs0', verbose: bool = False):
        super().__init__(device, verbose)
        self.test_file = f"/tmp/ufs_test_seq_write"
        self.size = "1G"
        self.runtime = 60
        self.target = 1650  # MB/s (UFS 3.1 128GB 目标值)
    
    def setup(self) -> bool:
        """测试前准备"""
        try:
            # 确保测试目录可写
            Path('/tmp').mkdir(parents=True, exist_ok=True)
            
            # 清理旧测试文件
            test_path = Path(self.test_file)
            if test_path.exists():
                test_path.unlink()
            
            return True
        except Exception as e:
            logger.error(f"Setup 失败：{e}")
            return False
    
    def execute(self) -> dict:
        """执行 FIO 顺序写测试"""
        fio_cmd = [
            'fio',
            '--name=seq_write',
            f'--filename={self.test_file}',
            '--rw=write',
            '--bs=128k',
            '--size=' + self.size,
            '--runtime=' + str(self.runtime),
            '--time_based',
            '--ioengine=sync',
            '--direct=1',
            '--numjobs=1',
            '--group_reporting',
            '--output-format=json'
        ]
        
        logger.info(f"执行 FIO 顺序写测试...")
        
        if self.verbose:
            logger.debug(f"FIO 命令：{' '.join(fio_cmd)}")
        
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
        job = fio_output['jobs'][0]['write']
        
        return {
            'bandwidth': {
                'value': job['bw_bytes'] / (1024 * 1024),
                'unit': 'MB/s'
            },
            'iops': {
                'value': job['iops'],
                'unit': 'IOPS'
            },
            'latency_avg': {
                'value': job['lat_ns']['mean'] / 1000,
                'unit': 'μs'
            },
            'latency_99999': {
                'value': job['lat_ns']['percentile']['99.999'] / 1000,
                'unit': 'μs'
            },
            'total_bytes': {
                'value': job['io_bytes'],
                'unit': 'bytes'
            }
        }
    
    def validate(self, result: dict) -> bool:
        """验证结果是否达标"""
        actual = result['bandwidth']['value']
        passed = actual >= self.target
        
        if passed:
            logger.info(f"✅ 性能达标：{actual:.1f} MB/s ≥ {self.target} MB/s")
        else:
            logger.warning(f"❌ 性能不达标：{actual:.1f} MB/s < {self.target} MB/s")
        
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
