#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
混合读写性能测试 - 修复版
测试 UFS 设备的混合随机读写 IOPS（70% 读/30% 写，4K QD32）

测试用例 ID: t_perf_MixedRw_005
测试目的：验证 UFS 设备混合读写 IOPS 性能
前置条件：
    1. UFS 设备已挂载
    2. 有足够可用空间（≥2GB）
    3. FIO 工具已安装
测试步骤：
    1. 执行 FIO 混合读写测试（4K block, QD32, 70/30, 60s, 含 10s ramp）
    2. 标注总 IOPS、读写 IOPS 分布、延迟是否达标
预期指标（参考）：
    - 总 IOPS ≥ 150,000
    - 平均延迟 < 200 μs
    - p99.999 尾延迟 < 8000 μs
测试耗时：约 70 秒（含 ramp）
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
    """混合读写性能测试"""
    
    name = "mixed_rw"
    description = "混合随机读写性能测试（70% 读/30% 写）"
    
    def __init__(
        self,
        device: str = '/dev/ufs0',
        test_dir: Path = None,
        verbose: bool = False,
        logger=None,
        bs: str = '4k',
        size: str = '1G',
        runtime: int = 60,
        ramp_time: int = 10,
        ioengine: str = 'sync',
        iodepth: int = 32,
        rw_mix: int = 70,
        target_total_iops: float = 150000,
        max_avg_latency_us: float = 200,
        max_tail_latency_us: float = 8000,
    ):
        super().__init__(device, test_dir, verbose, logger)
        self.test_file = self.get_test_file_path('mixed_rw')
        self.bs = bs
        self.size = size
        self.runtime = runtime
        self.ramp_time = ramp_time
        self.ioengine = ioengine
        self.iodepth = iodepth
        self.rw_mix = rw_mix
        self.target_total_iops = target_total_iops
        self.max_avg_latency_us = max_avg_latency_us
        self.max_tail_latency_us = max_tail_latency_us
        
        # 初始化工具
        self.fio = FIO(timeout=self.runtime + self.ramp_time + 30, logger=self.logger)
        self.ufs = UFSDevice(device, logger=self.logger)
    
    def setup(self) -> bool:
        """检查前置条件"""
        self.logger.info("开始检查前置条件...")
        
        if not self.ufs.exists():
            self.logger.error(f"设备不存在：{self.device}")
            return False
        
        if not self.ufs.check_available_space(min_gb=2.0):
            return False
        
        try:
            result = subprocess.run(['which', 'fio'], capture_output=True)
            if result.returncode != 0:
                self.logger.error("FIO 工具未安装")
                return False
        except Exception as e:
            self.logger.error(f"检查 FIO 失败：{e}")
            return False
        
        if not os.access(self.device, os.R_OK | os.W_OK):
            self.logger.error(f"设备权限不足：{self.device}")
            return False
        
        self.logger.info("📋 测试配置:")
        self.logger.info(f"  bs={self.bs}, size={self.size}, runtime={self.runtime}s, iodepth={self.iodepth}")
        self.logger.info(f"  rw_mix={self.rw_mix}% read, ioengine={self.ioengine}, ramp_time={self.ramp_time}s")
        self.logger.info(f"  target_total_iops={self.target_total_iops}")
        
        self.logger.info("📊 前置条件检查通过")
        return True
    
    def execute(self) -> Dict[str, Any]:
        """执行测试逻辑"""
        self.logger.info("🚀 开始执行混合读写性能测试...")
        
        try:
            # 构建FIO测试参数
            fio_args = {
                'filename': self.test_file,
                'bs': self.bs,
                'size': self.size,
                'runtime': self.runtime,
                'ramp_time': self.ramp_time,
                'ioengine': self.ioengine,
                'iodepth': self.iodepth,
                'rw': 'randrw',
                'rwmixread': self.rw_mix,
                'output-format': 'json'
            }
            
            # 执行FIO测试
            result = self.fio.run(FIOConfig(**fio_args))
            
            # 解析结果
            job_data = result.get('jobs', [{}])[0]
            
            # 提取读写IOPS
            read_iops = job_data.get('read', {}).get('iops', 0)
            write_iops = job_data.get('write', {}).get('iops', 0)
            total_iops = read_iops + write_iops
            
            # 提取延迟数据
            read_lat_ns = job_data.get('read', {}).get('lat_ns', {})
            write_lat_ns = job_data.get('write', {}).get('lat_ns', {})
            
            avg_read_latency_us = read_lat_ns.get('mean', 0) / 1000  # 转换为μs
            avg_write_latency_us = write_lat_ns.get('mean', 0) / 1000  # 转换为μs
            avg_latency_us = (avg_read_latency_us + avg_write_latency_us) / 2
            
            # 提取尾部延迟
            read_clat_ns = job_data.get('read', {}).get('clat_ns', {}).get('percentile', {})
            write_clat_ns = job_data.get('write', {}).get('clat_ns', {}).get('percentile', {})
            
            p99999_read_latency_us = read_clat_ns.get('99.999', 0) / 1000
            p99999_write_latency_us = write_clat_ns.get('99.999', 0) / 1000
            p99999_latency_us = max(p99999_read_latency_us, p99999_write_latency_us)
            
            return {
                'total_iops': total_iops,
                'read_iops': read_iops,
                'write_iops': write_iops,
                'avg_latency_us': avg_latency_us,
                'avg_read_latency_us': avg_read_latency_us,
                'avg_write_latency_us': avg_write_latency_us,
                'p99999_latency_us': p99999_latency_us,
                'p99999_read_latency_us': p99999_read_latency_us,
                'p99999_write_latency_us': p99999_write_latency_us,
                'raw_fio_result': result
            }
            
        except FIOError as e:
            self.logger.error(f"FIO 测试失败: {e}")
            return {'error': str(e), 'pass': False}
        except Exception as e:
            self.logger.error(f"测试执行异常: {e}")
            return {'error': str(e), 'pass': False}
    
    def validate(self, result: Dict[str, Any]) -> bool:
        """
        验证结果。
        对于性能测试，返回 True，指标达标情况通过 failure 记录。
        """
        # 检查是否有错误
        if 'error' in result:
            self.record_failure(
                "FIO 执行",
                "成功完成",
                f"执行失败：{result['error']}",
                "FIO 执行失败"
            )
            return True  # 让框架处理failure记录
        
        # 验证性能指标
        total_iops = result.get('total_iops', 0)
        avg_latency_us = result.get('avg_latency_us', float('inf'))
        p99999_latency_us = result.get('p99999_latency_us', float('inf'))
        
        # 记录指标达标情况（作为annotations）
        if total_iops >= self.target_total_iops:
            self.logger.info(f"✅ 总IOPS: {total_iops:.0f} ≥ {self.target_total_iops}")
        else:
            self.record_failure(
                "总IOPS性能",
                f"≥ {self.target_total_iops}",
                f"{total_iops:.0f}",
                "混合读写性能不达标"
            )
        
        if avg_latency_us <= self.max_avg_latency_us:
            self.logger.info(f"✅ 平均延迟: {avg_latency_us:.1f}μs ≤ {self.max_avg_latency_us}μs")
        else:
            self.record_failure(
                "平均延迟",
                f"≤ {self.max_avg_latency_us}μs",
                f"{avg_latency_us:.1f}μs",
                "平均延迟超出预期"
            )
        
        if p99999_latency_us <= self.max_tail_latency_us:
            self.logger.info(f"✅ 尾部延迟(p99.999): {p99999_latency_us:.0f}μs ≤ {self.max_tail_latency_us}μs")
        else:
            self.record_failure(
                "尾部延迟(p99.999)",
                f"≤ {self.max_tail_latency_us}μs",
                f"{p99999_latency_us:.0f}μs",
                "尾部延迟超出预期"
            )
        
        # 执行Postcondition检查（硬件可靠性验证）
        self._check_postcondition()
        
        if hasattr(self, '_failures') and len(self._failures) > 0:
            self.logger.warning(f"⚠️  共有 {len(self._failures)} 项验证不通过")
        
        return True  # 性能测试始终返回 True，由框架根据 failures 判断最终状态
    
    def teardown(self) -> bool:
        """测试后清理 - 父类会自动清理测试文件"""
        return super().teardown()
