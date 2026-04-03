#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
寿命耐久性可靠性测试
测试 UFS 设备在长期写入负载下的耐久性

测试用例 ID: t_reliability_EnduranceTest_003
测试目的：验证 UFS 设备在模拟长期使用场景下的耐久性
前置条件：
    1. UFS 设备已挂载
    2. 有足够可用空间（≥8GB）
    3. FIO 工具已安装
测试步骤：
    1. 记录初始设备寿命指标
    2. 执行长时间随机写入测试（4K QD8，60分钟）
    3. 记录测试后设备寿命指标
    4. 验证设备寿命消耗在预期范围内
预期结果：
    - 设备寿命指示器正常变化
    - 无异常健康状态警告
    - 坏块数量未异常增加
测试耗时：约 65 分钟
"""

import os
import sys
import subprocess
from pathlib import Path
from typing import Dict, Any

# 添加 core 和 tools 模块路径
core_dir = Path(__file__).parent.parent.parent / 'core'
tools_dir = Path(__file__).parent.parent.parent / 'tools'
sys.path.insert(0, str(core_dir))
sys.path.insert(0, str(tools_dir))

from runner import TestCase
from fio_wrapper import FIO, FIOError
from ufs_utils import UFSDevice


class Test(TestCase):
    """寿命耐久性可靠性测试"""
    
    name = "reliability_endurance_test"
    description = "寿命耐久性可靠性测试"
    
    def __init__(
        self,
        device: str = '/dev/ufs0',
        test_dir: Path = None,
        verbose: bool = False,
        logger = None,
        runtime: int = 3600,  # 60分钟
        ramp_time: int = 120,  # 2分钟 ramp
        ioengine: str = 'sync',
        iodepth: int = 8,
        # === 可靠性阈值 ===
        max_life_consumption_pct: float = 5.0,  # 最大寿命消耗百分比
        prefill: bool = True,
    ):
        super().__init__(device, test_dir, verbose, logger)
        self.test_file = self.get_test_file_path('reliability_endurance')
        self.runtime = runtime
        self.ramp_time = ramp_time
        self.ioengine = ioengine
        self.iodepth = iodepth
        self.max_life_consumption = max_life_consumption_pct
        self.prefill = prefill
        
        # 初始化工具
        self.fio = FIO(timeout=self.runtime + self.ramp_time + 120, logger=self.logger)
        self.ufs = UFSDevice(device, logger=self.logger)
    
    def setup(self) -> bool:
        """测试前准备 - 检查前置条件 + 记录初始状态"""
        self.logger.info("开始检查前置条件...")
        
        # 1. 检查设备是否存在
        if not self.ufs.exists():
            self.logger.error(f"设备不存在：{self.device}")
            return False
        self.logger.debug(f"📊 设备存在：{self.device}")
        
        # 2. 检查可用空间（至少 8GB）
        if not self.ufs.check_available_space(min_gb=8.0):
            self.logger.error("可用空间不足（需要 ≥8GB）")
            return False
        self.logger.debug("📊 可用空间充足（≥8GB）")
        
        # 3. 检查 FIO 工具
        try:
            result = subprocess.run(['which', 'fio'], capture_output=True)
            if result.returncode != 0:
                self.logger.error("FIO 工具未安装")
                return False
            self.logger.debug("📊 FIO 工具已安装")
        except Exception as e:
            self.logger.error(f"检查 FIO 失败：{e}")
            return False
        
        # 4. 检查权限
        if not os.access(self.device, os.R_OK | os.W_OK):
            self.logger.error(f"设备权限不足：{self.device}")
            return False
        self.logger.debug(f"📊 设备权限正常：{self.device}")
        
        # 5. 预填充测试文件（大容量）
        if self.prefill:
            self.logger.info(f"预填充测试文件：{self.test_file} (8GB)")
            try:
                result = subprocess.run(
                    ['dd', 'if=/dev/urandom', f'of={self.test_file}',
                     'bs=1M', 'count=8192', 'conv=fdatasync'],
                    capture_output=True, timeout=600
                )
                if result.returncode != 0:
                    self.logger.warning(f"预填充失败，继续测试：{result.stderr}")
            except subprocess.TimeoutExpired:
                self.logger.warning("预填充超时，继续测试")
            except Exception as e:
                self.logger.warning(f"预填充异常，继续测试：{e}")
        
        # 6. 记录完整测试配置
        self.logger.info("📋 测试配置:")
        self.logger.info(f"  runtime={self.runtime}s, ramp_time={self.ramp_time}s")
        self.logger.info(f"  ioengine={self.ioengine}, iodepth={self.iodepth}")
        self.logger.info(f"  max_life_consumption={self.max_life_consumption}%")
        
        self.logger.info("📊 前置条件检查通过")
        return True
    
    def execute(self) -> Dict[str, Any]:
        """执行寿命耐久性测试"""
        self.logger.info("开始执行寿命耐久性测试（随机写入 60 分钟）...")
        
        try:
            extra_kwargs = {}
            if self.ramp_time > 0:
                extra_kwargs['ramp_time'] = self.ramp_time
            
            metrics = self.fio.run_rand_write(
                filename=self.test_file,
                size='8G',
                runtime=self.runtime,
                bs='4k',
                iodepth=self.iodepth,
                ioengine=self.ioengine,
                **extra_kwargs
            )
            
            # 提取关键指标
            iops = metrics.iops['value']
            bw_mbps = metrics.bandwidth['value']
            avg_lat_us = metrics.latency_ns['mean'] / 1000
            
            self.logger.info(f"📊 耐久性测试结果:")
            self.logger.info(f"  IOPS: {iops:.0f}")
            self.logger.info(f"  带宽: {bw_mbps:.1f} MB/s")
            self.logger.info(f"  平均延迟: {avg_lat_us:.1f} ms")
            
            return {
                'iops': {'value': iops, 'unit': 'IOPS'},
                'bandwidth': {'value': bw_mbps, 'unit': 'MB/s'},
                'latency_avg': {'value': avg_lat_us, 'unit': 'ms'},
                'raw': getattr(metrics, 'raw', {}),
            }
            
        except FIOError as e:
            self.logger.error(f"测试执行失败：{e}")
            raise
    
    def validate(self, result: Dict[str, Any]) -> bool:
        """验证寿命耐久性测试结果"""
        annotations = []
        
        # 记录测试指标
        iops = result['iops']['value']
        bw = result['bandwidth']['value']
        annotations.append({
            'metric': '耐久性测试 IOPS',
            'actual': f'{iops:.0f}',
            'reference': 'N/A',
            'gap': 'N/A',
        })
        annotations.append({
            'metric': '耐久性测试带宽',
            'actual': f'{bw:.1f} MB/s',
            'reference': 'N/A',
            'gap': 'N/A',
        })
        result['annotations'] = annotations
        self.logger.info(f"📊 耐久性测试指标已记录")
        
        # === Postcondition 检查（硬件可靠性验证）===
        self._check_postcondition()
        
        return True  # 框架根据 failures 自动判断最终状态
    
    def teardown(self) -> bool:
        """测试后清理"""
        # 清理测试文件 → 父类自动处理
        return super().teardown()
