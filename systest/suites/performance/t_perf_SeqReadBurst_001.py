#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
顺序读性能测试
测试 UFS 设备的顺序读取带宽（Burst 模式）

测试用例 ID: t_perf_SeqReadBurst_001
测试目的：验证 UFS 设备顺序读 Burst 性能是否达标（≥2100 MB/s）
前置条件：
    1. UFS 设备已挂载
    2. 有足够可用空间（≥2GB）
    3. FIO 工具已安装
测试步骤：
    1. 创建测试文件
    2. 执行 FIO 顺序读测试（128K block, 60s）
    3. 验证带宽是否达标
预期结果：带宽 ≥ 2100 MB/s
测试耗时：约 60 秒
"""

import subprocess
import json
from pathlib import Path
import sys

# 添加 core 模块路径
core_dir = Path(__file__).parent.parent.parent / 'core'
sys.path.insert(0, str(core_dir))
from runner import TestCase


class Test(TestCase):
    """顺序读性能测试"""
    
    name = "seq_read_burst"
    description = "顺序读取性能测试（Burst 模式）"
    
    def __init__(self, device: str = '/dev/ufs0', verbose: bool = False, logger=None):
        super().__init__(device, verbose, logger)
        self.test_file = f"/tmp/ufs_test_seq_read"
        self.size = "1G"
        self.runtime = 60
        self.target = 2100  # MB/s
    
    def setup(self) -> bool:
        """测试前准备"""
        try:
            self.logger.debug("检查测试环境...")
            # 确保测试目录可写
            Path('/tmp').mkdir(parents=True, exist_ok=True)
            self.logger.info("测试环境准备完成")
            return True
        except Exception as e:
            self.logger.error(f"Setup 失败：{e}")
            return False
    
    def execute(self) -> dict:
        """执行 FIO 顺序读测试"""
        fio_cmd = [
            'fio',
            '--name=seq_read',
            f'--filename={self.test_file}',
            '--rw=read',
            '--bs=128k',
            '--size=' + self.size,
            '--runtime=' + str(self.runtime),
            '--time_based',
            '--ioengine=sync',  # 使用 sync 引擎（无需额外依赖）
            '--direct=1',
            '--numjobs=1',
            '--group_reporting',
            '--output-format=json'
        ]
        
        self.logger.info(f"执行 FIO 顺序读测试...")
        self.logger.debug(f"FIO 命令：{' '.join(fio_cmd)}")
        
        result = subprocess.run(
            fio_cmd,
            capture_output=True,
            text=True,
            timeout=self.runtime + 30
        )
        
        if result.returncode != 0:
            self.logger.error(f"FIO 执行失败：{result.stderr}")
            raise RuntimeError(f"FIO 执行失败：{result.stderr}")
        
        # 解析 FIO 输出
        fio_output = json.loads(result.stdout)
        job = fio_output['jobs'][0]['read']
        
        metrics = {
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
            }
        }
        
        # 记录关键指标
        self.logger.info(f"带宽：{metrics['bandwidth']['value']:.1f} MB/s")
        self.logger.info(f"IOPS: {metrics['iops']['value']:.0f}")
        self.logger.info(f"平均延迟：{metrics['latency_avg']['value']:.1f} μs")
        
        return metrics
    
    def validate(self, result: dict) -> bool:
        """验证结果是否达标"""
        actual = result['bandwidth']['value']
        passed = actual >= self.target
        
        if passed:
            self.logger.info(f"✅ 性能达标：{actual:.1f} MB/s ≥ {self.target} MB/s")
        else:
            self.logger.warning(f"❌ 性能不达标：{actual:.1f} MB/s < {self.target} MB/s")
        
        # 记录断言结果
        self.logger.log_assertion(
            assertion='带宽达标',
            expected=f'>= {self.target} MB/s',
            actual=f'{actual:.1f} MB/s',
            passed=passed
        )
        
        return passed
    
    def teardown(self) -> bool:
        """清理测试文件"""
        try:
            test_path = Path(self.test_file)
            if test_path.exists():
                test_path.unlink()
                self.logger.debug(f"清理测试文件：{self.test_file}")
            self.logger.info("测试清理完成")
            return True
        except Exception as e:
            self.logger.warning(f"清理失败：{e}")
            return True
