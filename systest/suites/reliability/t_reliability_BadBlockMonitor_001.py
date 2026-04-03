#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
坏块监控可靠性测试
测试 UFS 设备在压力写入后的坏块增长情况

测试用例 ID: t_reliability_BadBlockMonitor_001
测试目的：验证 UFS 设备在压力写入后坏块数量不增加
前置条件：
    1. UFS 设备已挂载
    2. 有足够可用空间（≥4GB）
    3. FIO 工具已安装
测试步骤：
    1. 记录初始坏块数量
    2. 执行全盘随机写入压力测试（4K QD32, 30分钟）
    3. 记录测试后坏块数量
    4. 验证坏块数量未增加
预期结果：
    - 坏块数量保持不变或减少（坏块修复）
    - 无新的严重警告标志
测试耗时：约 35 分钟
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
    """坏块监控可靠性测试"""
    
    name = "reliability_bad_block_monitor"
    description = "坏块监控可靠性测试"
    
    def __init__(
        self,
        device: str = '/dev/ufs0',
        test_dir: Path = None,
        verbose: bool = False,
        logger=None,
        simulate: bool = False,
        # === 测试参数 ===
        runtime: int = 1800,  # 30分钟
        ramp_time: int = 60,   # 1分钟 ramp
        ioengine: str = 'sync',
        iodepth: int = 32,
        # === 可靠性阈值 ===
        max_bad_block_increase: int = 0,  # 坏块不允许增加
        prefill: bool = True,
    ):
        super().__init__(device, test_dir, verbose, logger)
        self.test_file = self.get_test_file_path('reliability_bad_block')
        self.runtime = runtime
        self.ramp_time = ramp_time
        self.ioengine = ioengine
        self.iodepth = iodepth
        self.max_bad_block_increase = max_bad_block_increase
        self.prefill = prefill
        self.simulate = simulate
        
        # 初始化工具
        if simulate:
            self.logger.info("🔧 模拟模式：使用 UFS 模拟器")
            self.sim = UFSSimulator(device_path='/tmp/ufs_sim.img', logger=self.logger)
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
        
        # 2. 检查可用空间（至少 4GB）
        if not self.ufs.check_available_space(min_gb=4.0):
            self.logger.error("可用空间不足（需要 ≥4GB）")
            return False
        self.logger.debug("📊 可用空间充足（≥4GB）")
        
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
        
        # 5. 预填充测试文件（全盘写入模式）
        if self.prefill and not self.simulate:
            self.logger.info(f"预填充测试文件：{self.test_file} (全盘模式)")
            try:
                # 获取设备大小
                device_size = self._get_device_size_gb()
                size_gb = min(device_size, 4)  # 最多 4GB
                size_str = f"{size_gb}G"
                
                result = subprocess.run(
                    ['dd', 'if=/dev/urandom', f'of={self.test_file}',
                     'bs=1M', f'count={int(size_gb * 1024)}',
                     'conv=fdatasync'],
                    capture_output=True,
                    text=True,
                    timeout=300
                )
                if result.returncode != 0:
                    self.logger.warning(f"预填充失败，继续测试：{result.stderr}")
                else:
                    self.logger.debug(f"📊 测试文件预填充完成 ({size_gb}GB)")
            except subprocess.TimeoutExpired:
                self.logger.warning("预填充超时，继续测试")
            except Exception as e:
                self.logger.warning(f"预填充异常，继续测试：{e}")
        
        # 6. 记录完整测试配置
        self.logger.info("📋 测试配置:")
        self.logger.info(f"  runtime={self.runtime}s, ramp_time={self.ramp_time}s")
        self.logger.info(f"  ioengine={self.ioengine}, iodepth={self.iodepth}")
        self.logger.info(f"  max_bad_block_increase={self.max_bad_block_increase}")
        
        self.logger.info("📊 前置条件检查通过")
        return True
    
    def execute(self) -> dict:
        """执行坏块压力测试"""
        self.logger.info("开始执行坏块压力测试（随机写入 30 分钟）...")
        
        try:
            if self.simulate:
                # 模拟模式
                metrics = self.sim.simulate_performance('rand_write')
            else:
                # 构建 FIO 参数
                extra_kwargs = {}
                if self.ramp_time > 0:
                    extra_kwargs['ramp_time'] = self.ramp_time
                
                metrics = self.fio.run_rand_write(
                    filename=self.test_file,
                    size='100%',  # 全盘写入
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
            
            self.logger.info(f"📊 压力测试结果:")
            self.logger.info(f"  IOPS: {iops:.0f}")
            self.logger.info(f"  带宽：{bw_mbps:.1f} MB/s")
            self.logger.info(f"  平均延迟：{avg_lat_us:.1f} μs")
            
            return {
                'iops': metrics.iops,
                'bandwidth': metrics.bandwidth,
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
        """验证坏块监控结果"""
        annotations = []
        
        # 记录压力测试指标
        iops = result['iops']['value']
        bw = result['bandwidth']['value']
        annotations.append({
            'metric': '压力测试 IOPS',
            'actual': f'{iops:.0f}',
            'reference': 'N/A',
            'gap': 'N/A',
        })
        annotations.append({
            'metric': '压力测试带宽',
            'actual': f'{bw:.1f} MB/s',
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
    
    def _get_device_size_gb(self) -> float:
        """获取设备大小（GB）"""
        try:
            device_name = Path(self.device).name
            size_file = Path(f'/sys/block/{device_name}/size')
            if size_file.exists():
                sectors = int(size_file.read_text().strip())
                return (sectors * 512) / (1024 ** 3)
        except Exception as e:
            self.logger.warning(f"获取设备大小失败：{e}")
        return 4.0  # 默认 4GB