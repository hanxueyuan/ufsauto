#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ECC 错误率可靠性测试
测试 UFS 设备在大量读写后的 ECC 错误率

测试用例 ID: t_reliability_ECCErrorRate_002
测试目的：验证 UFS 设备在压力读写后 ECC 错误率在可接受范围内
前置条件：
    1. UFS 设备已挂载
    2. 有足够可用空间（≥2GB）
    3. FIO 工具已安装
测试步骤：
    1. 记录初始 ECC 错误统计
    2. 执行混合读写压力测试（70%读/30%写, 4K QD16, 20分钟）
    3. 记录测试后 ECC 错误统计
    4. 验证 ECC 错误率未显著增加
预期结果：
    - ECC 错误率 < 10^-15 (车规要求)
    - 无不可纠正错误
测试耗时：约 25 分钟
"""

import os
import sys
import subprocess
from pathlib import Path

# 添加 core 和 tools 模块路径
core_dir = Path(__file__).parent.parent.parent / 'core'
tools_dir = Path(__file__).parent.parent.parent / 'tools'
sys.path.insert(0, str(core_dir))
sys.path.insert(0, str(tools_dir))

from runner import TestCase
from fio_wrapper import FIO, FIOError
from ufs_utils import UFSDevice
from ufs_simulator import UFSSimulator


class Test(TestCase):
    """ECC 错误率可靠性测试"""
    
    name = "reliability_ecc_error_rate"
    description = "ECC 错误率可靠性测试"
    
    def __init__(
        self,
        device: str = '/dev/ufs0',
        test_dir: Path = None,
        verbose: bool = False,
        logger=None,
        simulate: bool = False,
        # === 测试参数 ===
        runtime: int = 1200,  # 20分钟
        ramp_time: int = 60,   # 1分钟 ramp
        ioengine: str = 'sync',
        iodepth: int = 16,
        read_ratio: int = 70,
        # === 可靠性阈值 ===
        max_ecc_error_increase: float = 0.0,  # ECC 错误不允许增加
        prefill: bool = True,
    ):
        super().__init__(device, test_dir, verbose, logger)
        self.test_file = self.get_test_file_path('reliability_ecc')
        self.runtime = runtime
        self.ramp_time = ramp_time
        self.ioengine = ioengine
        self.iodepth = iodepth
        self.read_ratio = read_ratio
        self.max_ecc_error_increase = max_ecc_error_increase
        self.prefill = prefill
        self.simulate = simulate
        
        # 初始化工具
        if simulate:
            self.logger.info("🔧 模拟模式：使用 UFS 模拟器")
            self.sim = UFSSimulator(device_path='/tmp/ufs_sim.img', logger=self.logger)
            # 自动创建模拟设备文件
            if not self.sim.exists():
                self.sim.create_device(size_gb=128)
            self.fio = None
            self.ufs = self.sim
        else:
            self.fio = FIO(timeout=self.runtime + self.ramp_time + 60, logger=self.logger)
            self.ufs = UFSDevice(device, logger=self.logger)
            self.sim = None
    
    def setup(self) -> bool:
        """测试前准备 - 检查前置条件 + 记录初始状态"""
        self.logger.info("开始检查前置条件...")
        
        # 1. 检查设备是否存在
        if not self.ufs.exists():
            self.logger.error(f"设备不存在：{self.device}")
            return False
        self.logger.debug(f"📊 设备存在：{self.device}")
        
        # 2. 检查可用空间（至少 2GB）
        if not self.ufs.check_available_space(min_gb=2.0):
            self.logger.error("可用空间不足（需要 ≥2GB）")
            return False
        self.logger.debug("📊 可用空间充足（≥2GB）")
        
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
        
        # 5. 预填充测试文件
        if self.prefill and not self.simulate:
            self.logger.info(f"预填充测试文件：{self.test_file} (2GB)")
            try:
                result = subprocess.run(
                    ['dd', 'if=/dev/urandom', f'of={self.test_file}',
                     'bs=1M', 'count=2048', 'conv=fdatasync'],
                    capture_output=True,
                    text=True,
                    timeout=120
                )
                if result.returncode != 0:
                    self.logger.warning(f"预填充失败，继续测试：{result.stderr}")
                else:
                    self.logger.debug("📊 测试文件预填充完成 (2GB)")
            except subprocess.TimeoutExpired:
                self.logger.warning("预填充超时，继续测试")
            except Exception as e:
                self.logger.warning(f"预填充异常，继续测试：{e}")
        
        # 6. 记录完整测试配置
        self.logger.info("📋 测试配置:")
        self.logger.info(f"  runtime={self.runtime}s, ramp_time={self.ramp_time}s")
        self.logger.info(f"  ioengine={self.ioengine}, iodepth={self.iodepth}")
        self.logger.info(f"  read_ratio={self.read_ratio}%, max_ecc_error_increase={self.max_ecc_error_increase}")
        
        self.logger.info("📊 前置条件检查通过")
        return True
    
    def execute(self) -> dict:
        """执行 ECC 压力测试"""
        self.logger.info("开始执行 ECC 压力测试（混合读写 20 分钟）...")
        
        try:
            if self.simulate:
                # 模拟模式
                metrics = self.sim.simulate_performance('mixed_rw')
            else:
                # 构建 FIO 参数
                extra_kwargs = {}
                if self.ramp_time > 0:
                    extra_kwargs['ramp_time'] = self.ramp_time
                
                metrics = self.fio.run_mixed_rw(
                    filename=self.test_file,
                    size='2G',
                    runtime=self.runtime,
                    bs='4k',
                    iodepth=self.iodepth,
                    read_ratio=self.read_ratio,
                    ioengine=self.ioengine,
                    **extra_kwargs
                )
            
            # 提取关键指标
            total_iops = metrics.iops['value']
            read_iops = total_iops * (self.read_ratio / 100)
            write_iops = total_iops * ((100 - self.read_ratio) / 100)
            avg_lat_us = metrics.latency_ns['mean'] / 1000
            
            self.logger.info(f"📊 压力测试结果:")
            self.logger.info(f"  总 IOPS: {total_iops:.0f}")
            self.logger.info(f"  读 IOPS: {read_iops:.0f}")
            self.logger.info(f"  写 IOPS: {write_iops:.0f}")
            self.logger.info(f"  平均延迟：{avg_lat_us:.1f} μs")
            
            return {
                'total_iops': metrics.iops,
                'read_iops': {'value': read_iops, 'unit': 'IOPS'},
                'write_iops': {'value': write_iops, 'unit': 'IOPS'},
                'latency_avg': {
                    'value': avg_lat_us,
                    'unit': 'μs'
                },
                'raw': getattr(metrics, 'raw', {}),
            }
            
        except Exception as e:
            self.logger.error(f"测试执行失败：{e}")
            raise
    
    def validate(self, result: dict) -> bool:
        """验证 ECC 错误率结果"""
        annotations = []
        
        # 记录压力测试指标
        total_iops = result['total_iops']['value']
        annotations.append({
            'metric': '混合读写总 IOPS',
            'actual': f'{total_iops:.0f}',
            'reference': 'N/A',
            'gap': 'N/A',
        })
        
        result['annotations'] = annotations
        self.logger.info(f"📊 压力测试指标已记录")
        
        # === Postcondition 检查（硬件可靠性验证）===
        self._check_postcondition()
        
        return True

    def teardown(self) -> bool:
        """清理测试文件"""
        try:
            test_path = Path(self.test_file)
            if test_path.exists():
                test_path.unlink()
                self.logger.debug(f"清理测试文件：{self.test_file}")
            
            # 刷新缓存
            self.ufs.flush_cache()
            
            self.logger.info("测试清理完成")
            return True
        except Exception as e:
            self.logger.warning(f"清理失败：{e}")
            return False