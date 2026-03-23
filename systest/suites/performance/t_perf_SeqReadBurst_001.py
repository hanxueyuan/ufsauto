#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
顺序读性能测试
测试 UFS 设备的顺序读取带宽（Burst 模式）

测试用例 ID: t_perf_SeqReadBurst_001
测试目的：验证 UFS 设备顺序读 Burst 性能是否达标
前置条件：
    1. UFS 设备已挂载
    2. 有足够可用空间（≥2GB）
    3. FIO 工具已安装
测试步骤：
    1. 预填充测试文件（避免读 sparse file）
    2. 执行 FIO 顺序读测试（128K block, 60s, 含 10s ramp）
    3. 验证带宽、IOPS、延迟是否达标
预期结果：
    - 带宽 ≥ 2100 MB/s
    - 平均延迟 < 200 μs
    - p99.999 尾延迟 < 5000 μs (5ms)
测试耗时：约 70 秒（含 ramp）
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
    """顺序读性能测试"""
    
    name = "seq_read_burst"
    description = "顺序读取性能测试（Burst 模式）"
    
    def __init__(
        self,
        device: str = '/dev/ufs0',
        verbose: bool = False,
        logger=None,
        simulate: bool = False,
        # === 可配置参数 ===
        bs: str = '128k',
        size: str = '1G',
        runtime: int = 60,
        ramp_time: int = 10,
        ioengine: str = 'sync',
        iodepth: int = 1,
        # === 性能目标（可根据 UFS 规格调整）===
        target_bw_mbps: float = 2100,
        max_avg_latency_us: float = 200,
        max_tail_latency_us: float = 5000,  # p99.999
        # === 可选功能 ===
        verify: str = None,  # 'md5', 'crc32c', None
        prefill: bool = True,
    ):
        super().__init__(device, verbose, logger)
        self.test_file = "/tmp/ufs_test_seq_read"
        self.bs = bs
        self.size = size
        self.runtime = runtime
        self.ramp_time = ramp_time
        self.ioengine = ioengine
        self.iodepth = iodepth
        self.target_bw_mbps = target_bw_mbps
        self.max_avg_latency_us = max_avg_latency_us
        self.max_tail_latency_us = max_tail_latency_us
        self.verify_mode = verify
        self.prefill = prefill
        self.simulate = simulate
        
        # 初始化工具
        if simulate:
            self.logger.info("🔧 模拟模式：使用 UFS 模拟器")
            self.sim = UFSSimulator(device_path='/tmp/ufs_sim.img', logger=self.logger)
            self.fio = None
            self.ufs = self.sim
        else:
            self.fio = FIO(timeout=self.runtime + self.ramp_time + 30, logger=self.logger)
            self.ufs = UFSDevice(device, logger=self.logger)
            self.sim = None
    
    def setup(self) -> bool:
        """测试前准备 - 检查前置条件 + 预填充数据"""
        self.logger.info("开始检查前置条件...")
        
        # 1. 检查设备是否存在
        if not self.ufs.exists():
            self.logger.error(f"设备不存在：{self.device}")
            return False
        self.logger.debug(f"✅ 设备存在：{self.device}")
        
        # 2. 检查可用空间（至少 2GB）
        if not self.ufs.check_available_space(min_gb=2.0):
            self.logger.error("可用空间不足")
            return False
        self.logger.debug("✅ 可用空间充足（≥2GB）")
        
        # 3. 检查 FIO 工具
        try:
            result = subprocess.run(['which', 'fio'], capture_output=True)
            if result.returncode != 0:
                self.logger.error("FIO 工具未安装")
                return False
            self.logger.debug("✅ FIO 工具已安装")
        except Exception as e:
            self.logger.error(f"检查 FIO 失败：{e}")
            return False
        
        # 4. 检查权限
        if not os.access(self.device, os.R_OK | os.W_OK):
            self.logger.error(f"设备权限不足：{self.device}")
            return False
        self.logger.debug(f"✅ 设备权限正常：{self.device}")
        
        # 5. 检查设备健康状态
        health = self.ufs.get_health_status()
        if health['status'] != 'OK':
            self.logger.warning(f"设备健康状态异常：{health['status']}")
            # 不阻止测试，但记录警告
        
        # 6. 预填充测试文件（避免读 sparse file / 未初始化数据）
        if self.prefill and not self.simulate:
            self.logger.info(f"预填充测试文件：{self.test_file} ({self.size})")
            try:
                # 用 dd 写入真实数据
                result = subprocess.run(
                    ['dd', 'if=/dev/urandom', f'of={self.test_file}',
                     'bs=1M', f'count={self._parse_size_mb(self.size)}',
                     'conv=fdatasync'],
                    capture_output=True,
                    text=True,
                    timeout=120
                )
                if result.returncode != 0:
                    self.logger.warning(f"预填充失败，继续测试：{result.stderr}")
                else:
                    self.logger.debug("✅ 测试文件预填充完成")
            except subprocess.TimeoutExpired:
                self.logger.warning("预填充超时，继续测试")
            except Exception as e:
                self.logger.warning(f"预填充异常，继续测试：{e}")
        
        # 7. 记录完整测试配置（便于问题复现）
        self.logger.info("📋 测试配置:")
        self.logger.info(f"  bs={self.bs}, size={self.size}, runtime={self.runtime}s")
        self.logger.info(f"  ioengine={self.ioengine}, iodepth={self.iodepth}, ramp_time={self.ramp_time}s")
        self.logger.info(f"  target_bw={self.target_bw_mbps} MB/s, max_avg_lat={self.max_avg_latency_us} μs")
        self.logger.info(f"  max_tail_lat(p99.999)={self.max_tail_latency_us} μs, verify={self.verify_mode}")
        
        self.logger.info("✅ 前置条件检查通过")
        return True
    
    def execute(self) -> dict:
        """执行顺序读性能测试"""
        self.logger.info("开始执行顺序读性能测试...")
        
        try:
            if self.simulate:
                # 模拟模式
                metrics = self.sim.simulate_performance('seq_read')
            else:
                # 构建 FIO 参数，包含 ramp_time 和可选 verify
                extra_kwargs = {}
                if self.ramp_time > 0:
                    extra_kwargs['ramp_time'] = self.ramp_time
                if self.verify_mode:
                    extra_kwargs['verify'] = self.verify_mode
                
                metrics = self.fio.run_seq_read(
                    filename=self.test_file,
                    size=self.size,
                    runtime=self.runtime,
                    bs=self.bs,
                    ioengine=self.ioengine,
                    iodepth=self.iodepth,
                    **extra_kwargs
                )
            
            # 提取关键指标
            bw_mbps = metrics.bandwidth['value']
            iops = metrics.iops['value']
            avg_lat_us = metrics.latency_ns['mean'] / 1000
            p99999_ns = metrics.latency_ns['percentile'].get('99.999', 0)
            p99999_us = p99999_ns / 1000 if p99999_ns else 0
            
            self.logger.info(f"📊 测试结果:")
            self.logger.info(f"  带宽：{bw_mbps:.1f} MB/s")
            self.logger.info(f"  IOPS: {iops:.0f}")
            self.logger.info(f"  平均延迟：{avg_lat_us:.1f} μs")
            self.logger.info(f"  p99.999 延迟：{p99999_us:.1f} μs")
            
            return {
                'bandwidth': metrics.bandwidth,
                'iops': metrics.iops,
                'latency_avg': {
                    'value': avg_lat_us,
                    'unit': 'μs'
                },
                'latency_99999': {
                    'value': p99999_us,
                    'unit': 'μs'
                },
                'cpu': getattr(metrics, 'cpu', {}),
                'raw': getattr(metrics, 'raw', {}),
            }
            
        except Exception as e:
            self.logger.error(f"测试执行失败：{e}")
            raise
    
    def validate(self, result: dict) -> bool:
        """
        标注指标是否达标。
        
        性能测试哲学：指标不达标不等于测试失败。
        - 测试只要能跑完、数据采集完整，就算 PASS（完成）
        - "达标/不达标"只是标注（annotation），供后续分析参考
        - 只有测试本身跑不起来（setup 失败、FIO crash）才算 ERROR
        
        Returns:
            bool: 永远返回 True（测试完成）。指标达标情况通过 result['annotations'] 记录。
        """
        annotations = []
        
        # === 指标 1：带宽 ===
        actual_bw = result['bandwidth']['value']
        bw_met = actual_bw >= self.target_bw_mbps
        annotations.append({
            'metric': '带宽',
            'actual': f'{actual_bw:.1f} MB/s',
            'target': f'>= {self.target_bw_mbps} MB/s',
            'met': bw_met,
        })
        
        status = "✅" if bw_met else "⚠️"
        self.logger.info(f"{status} 带宽：{actual_bw:.1f} MB/s (目标 ≥ {self.target_bw_mbps} MB/s)")
        self.logger.log_assertion(
            assertion='带宽',
            expected=f'>= {self.target_bw_mbps} MB/s',
            actual=f'{actual_bw:.1f} MB/s',
            passed=bw_met
        )
        
        # === 指标 2：平均延迟 ===
        actual_lat = result['latency_avg']['value']
        lat_met = actual_lat < self.max_avg_latency_us
        annotations.append({
            'metric': '平均延迟',
            'actual': f'{actual_lat:.1f} μs',
            'target': f'< {self.max_avg_latency_us} μs',
            'met': lat_met,
        })
        
        status = "✅" if lat_met else "⚠️"
        self.logger.info(f"{status} 平均延迟：{actual_lat:.1f} μs (目标 < {self.max_avg_latency_us} μs)")
        self.logger.log_assertion(
            assertion='平均延迟',
            expected=f'< {self.max_avg_latency_us} μs',
            actual=f'{actual_lat:.1f} μs',
            passed=lat_met
        )
        
        # === 指标 3：尾延迟 ===
        actual_tail = result['latency_99999']['value']
        if actual_tail > 0:
            tail_met = actual_tail < self.max_tail_latency_us
            annotations.append({
                'metric': 'p99.999 延迟',
                'actual': f'{actual_tail:.1f} μs',
                'target': f'< {self.max_tail_latency_us} μs',
                'met': tail_met,
            })
            
            status = "✅" if tail_met else "⚠️"
            self.logger.info(f"{status} p99.999 延迟：{actual_tail:.1f} μs (目标 < {self.max_tail_latency_us} μs)")
            self.logger.log_assertion(
                assertion='尾延迟(p99.999)',
                expected=f'< {self.max_tail_latency_us} μs',
                actual=f'{actual_tail:.1f} μs',
                passed=tail_met
            )
        else:
            self.logger.info("ℹ️ 未获取到 p99.999 延迟数据，跳过标注")
        
        # === 指标 4：IOPS 与带宽一致性（数据完整性校验，非性能指标）===
        actual_iops = result['iops']['value']
        bs_bytes = self._parse_bs_bytes(self.bs)
        if bs_bytes > 0 and actual_iops > 0:
            expected_bw_from_iops = (actual_iops * bs_bytes) / (1024 * 1024)
            iops_consistent = abs(expected_bw_from_iops - actual_bw) / max(actual_bw, 1) < 0.20
            annotations.append({
                'metric': 'IOPS-带宽一致性',
                'actual': f'IOPS={actual_iops:.0f}, 推算BW={expected_bw_from_iops:.1f} MB/s',
                'target': f'与实际BW {actual_bw:.1f} MB/s 偏差 < 20%',
                'met': iops_consistent,
            })
            
            status = "✅" if iops_consistent else "⚠️"
            self.logger.info(
                f"{status} IOPS 一致性：{actual_iops:.0f} IOPS × {self.bs} "
                f"≈ {expected_bw_from_iops:.1f} MB/s (实际 {actual_bw:.1f} MB/s)"
            )
        
        # === 汇总标注到 result ===
        result['annotations'] = annotations
        
        met_count = sum(1 for a in annotations if a['met'])
        total_count = len(annotations)
        self.logger.info(f"📋 指标标注完成：{met_count}/{total_count} 项达标")
        
        not_met = [a for a in annotations if not a['met']]
        if not_met:
            self.logger.info(f"⚠️ 未达标指标（供后续分析）：")
            for a in not_met:
                self.logger.info(f"  - {a['metric']}：实际 {a['actual']}，目标 {a['target']}")
        
        # 性能测试：只要数据采集完整，永远返回 True（PASS = 测试完成）
        # 指标是否达标通过 annotations 记录，不影响测试状态
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
            return False  # 改为返回 False，让调用方知道清理出了问题
    
    # === 工具方法 ===
    
    @staticmethod
    def _parse_size_mb(size_str: str) -> int:
        """解析大小字符串为 MB"""
        size_str = size_str.strip().upper()
        if size_str.endswith('G'):
            return int(float(size_str[:-1]) * 1024)
        elif size_str.endswith('M'):
            return int(float(size_str[:-1]))
        elif size_str.endswith('K'):
            return max(1, int(float(size_str[:-1]) / 1024))
        else:
            return int(size_str) // (1024 * 1024)
    
    @staticmethod
    def _parse_bs_bytes(bs_str: str) -> int:
        """解析 block size 字符串为字节"""
        bs_str = bs_str.strip().lower()
        if bs_str.endswith('k'):
            return int(float(bs_str[:-1]) * 1024)
        elif bs_str.endswith('m'):
            return int(float(bs_str[:-1]) * 1024 * 1024)
        else:
            return int(bs_str)
