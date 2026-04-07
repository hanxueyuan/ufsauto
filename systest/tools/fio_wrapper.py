#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FIO 工具封装层 - FIO Wrapper

生产级 FIO 测试工具封装，提供：
- 统一的 FIO 命令构建
- 结果解析与验证
- 错误处理与重试
- 性能指标标准化输出

Usage:
    from tools.fio_wrapper import FIO
    
    fio = FIO()
    result = fio.run_seq_read(
        filename='/dev/ufs0',
        size='1G',
        runtime=60,
        bs='128k'
    )
    print(f"带宽：{result['bandwidth']['value']} {result['bandwidth']['unit']}")
"""

import subprocess
import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class FIOEngine(Enum):
    """FIO IO 引擎"""
    SYNC = 'sync'
    LIBAIO = 'libaio'
    IO_URING = 'io_uring'
    PSYNC = 'psync'
    PVSYNC = 'pvsync'


class FIORWType(Enum):
    """FIO 读写模式"""
    READ = 'read'
    WRITE = 'write'
    RANDREAD = 'randread'
    RANDWRITE = 'randwrite'
    READWRITE = 'readwrite'
    RANDRW = 'randrw'
    TRIM = 'trim'


@dataclass
class FIOConfig:
    """FIO 配置参数"""
    # 基本参数
    name: str = 'fio_test'
    filename: str = '/dev/ufs0'
    rw: str = 'read'
    bs: str = '4k'
    size: str = '1G'
    runtime: int = 60
    ioengine: str = 'sync'
    direct: bool = True
    numjobs: int = 1
    iodepth: int = 1
    group_reporting: bool = True
    
    # 高级参数
    rate_iops: Optional[int] = None
    rate: Optional[int] = None  # MB/s
    thinktime: Optional[int] = None
    ramp_time: Optional[int] = None
    time_based: bool = False
    verify: Optional[str] = None
    
    # 混合读写比例（仅当 rw=readwrite 或 randrw 时有效）
    rwmixread: Optional[int] = None
    
    # 输出格式
    output_format: str = 'json'
    
    def to_args(self) -> List[str]:
        """转换为 FIO 命令行参数"""
        args = ['fio', f'--name={self.name}']
        
        # 基本参数
        args.append(f'--filename={self.filename}')
        args.append(f'--rw={self.rw}')
        args.append(f'--bs={self.bs}')
        
        if self.size:
            args.append(f'--size={self.size}')
        
        if self.runtime:
            args.append(f'--runtime={self.runtime}')
        
        if self.time_based:
            args.append('--time_based')
        
        args.append(f'--ioengine={self.ioengine}')
        
        if self.direct:
            args.append('--direct=1')
        
        args.append(f'--numjobs={self.numjobs}')
        args.append(f'--iodepth={self.iodepth}')
        
        if self.group_reporting:
            args.append('--group_reporting')
        
        # 高级参数
        if self.rate_iops:
            args.append(f'--rate_iops={self.rate_iops}')
        
        if self.rate:
            args.append(f'--rate={self.rate}')
        
        if self.thinktime:
            args.append(f'--thinktime={self.thinktime}')
        
        if self.ramp_time:
            args.append(f'--ramp_time={self.ramp_time}')
        
        if self.verify:
            args.append(f'--verify={self.verify}')
        
        # 混合读写比例
        if self.rwmixread is not None:
            args.append(f'--rwmixread={self.rwmixread}')
        
        # 输出格式
        args.append(f'--output-format={self.output_format}')
        
        return args


@dataclass
class FIOMetrics:
    """FIO 性能指标（标准化输出）"""
    # 带宽
    bandwidth: Dict[str, Any]
    # IOPS
    iops: Dict[str, Any]
    # 延迟（纳秒）
    latency_ns: Dict[str, Any]
    # CPU 使用率
    cpu: Dict[str, Any]
    # 原始数据（用于深度分析）
    raw: Dict[str, Any]
    
    @classmethod
    def from_fio_output(cls, fio_output: Dict[str, Any], rw_type: str) -> 'FIOMetrics':
        """从 FIO JSON 输出创建指标对象"""
        job = fio_output['jobs'][0]
        
        # 根据读写类型选择数据源
        if 'read' in rw_type.lower():
            io_stats = job.get('read', {})
        elif 'write' in rw_type.lower():
            io_stats = job.get('write', {})
        else:
            # 混合模式，合并读写
            read_stats = job.get('read', {})
            write_stats = job.get('write', {})
            # 带宽和 IOPS 合并
            read_bw = read_stats.get('bw_bytes', 0)
            write_bw = write_stats.get('bw_bytes', 0)
            read_iops = read_stats.get('iops', 0)
            write_iops = write_stats.get('iops', 0)
            # 延迟：分开统计读和写，不合并（合并会丢失信息）
            io_stats = {
                'bw_bytes': read_bw + write_bw,
                'iops': read_iops + write_iops,
                'lat_ns_read': read_stats.get('lat_ns', {}),
                'lat_ns_write': write_stats.get('lat_ns', {})
            }
        
        # 带宽 (MB/s)
        bandwidth = {
            'value': io_stats.get('bw_bytes', 0) / (1024 * 1024),
            'unit': 'MB/s'
        }
        
        # IOPS
        iops = {
            'value': io_stats.get('iops', 0),
            'unit': 'IOPS'
        }
        
        # 延迟统计：混合读写模式分开统计读和写
        if 'lat_ns_read' in io_stats and 'lat_ns_write' in io_stats:
            # 混合模式：分别记录读和写的延迟
            lat_read = io_stats['lat_ns_read']
            lat_write = io_stats['lat_ns_write']
            latency = {
                'read': {
                    'min': lat_read.get('min', 0),
                    'max': lat_read.get('max', 0),
                    'mean': lat_read.get('mean', 0),
                    'stddev': lat_read.get('stddev', 0),
                    'percentile': lat_read.get('percentile', {})
                },
                'write': {
                    'min': lat_write.get('min', 0),
                    'max': lat_write.get('max', 0),
                    'mean': lat_write.get('mean', 0),
                    'stddev': lat_write.get('stddev', 0),
                    'percentile': lat_write.get('percentile', {})
                }
            }
        else:
            # 纯读或纯写模式
            lat_ns = io_stats.get('lat_ns', {})
            latency = {
                'min': lat_ns.get('min', 0),
                'max': lat_ns.get('max', 0),
                'mean': lat_ns.get('mean', 0),
                'stddev': lat_ns.get('stddev', 0),
                'percentile': lat_ns.get('percentile', {})
            }
        
        # CPU 使用率
        usr_cpu = job.get('usr_cpu', 0)
        sys_cpu = job.get('sys_cpu', 0)
        cpu = {
            'usr': usr_cpu,
            'sys': sys_cpu,
            'total': usr_cpu + sys_cpu
        }
        
        return cls(
            bandwidth=bandwidth,
            iops=iops,
            latency_ns=latency,
            cpu=cpu,
            raw=fio_output
        )


class FIOError(Exception):
    """FIO 执行错误"""
    def __init__(self, message: str, returncode: int = -1, stderr: str = ''):
        super().__init__(message)
        self.returncode = returncode
        self.stderr = stderr


class FIO:
    """FIO 工具封装类"""
    
    def __init__(self, timeout: int = 300, retries: int = 1, logger=None):
        """
        初始化 FIO 工具
        
        Args:
            timeout: FIO 执行超时时间（秒）
            retries: 失败重试次数
            logger: 日志记录器
        """
        self.timeout = timeout
        self.retries = retries
        self.logger = logger or logging.getLogger(__name__)
    
    def run(self, config: FIOConfig, dry_run: bool = False, allowed_prefixes: list = None) -> FIOMetrics:
        """
        执行 FIO 测试
        
        Args:
            config: FIO 配置
            dry_run: 是否仅打印命令不执行
            allowed_prefixes: 允许的文件路径前缀列表（如 ['/tmp', '/mapdata']）
        
        Returns:
            FIOMetrics: 性能指标
        
        Raises:
            FIOError: FIO 执行失败
        """
        # 验证 filename 路径
        filename = Path(config.filename)
        if allowed_prefixes:
            # 检查是否在允许的目录内
            if not any(str(filename).startswith(p) for p in allowed_prefixes):
                # 也允许设备路径（/dev/ 开头）
                if not str(filename).startswith('/dev/'):
                    raise FIOError(f"非法的 filename 路径：{config.filename} (必须在允许的目录内或设备路径)")
        cmd = config.to_args()
        
        self.logger.info(f"执行 FIO 测试：{config.name}")
        self.logger.debug(f"FIO 命令：{' '.join(cmd)}")
        
        if dry_run:
            self.logger.info("[DRY-RUN] 模拟执行")
            return self._create_mock_metrics(config.rw)
        
        # 执行 FIO（带重试）
        last_error = None
        for attempt in range(1, self.retries + 1):
            try:
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=self.timeout + 30  # 额外 30 秒用于启动和清理
                )
                
                if result.returncode != 0:
                    raise FIOError(
                        f"FIO 执行失败：{result.stderr}",
                        returncode=result.returncode,
                        stderr=result.stderr
                    )
                
                # 解析 JSON 输出
                # 检查 stdout 是否为空
                if not result.stdout or not result.stdout.strip():
                    stderr_msg = result.stderr.strip() if result.stderr else '无错误输出'
                    raise FIOError(f"FIO 未输出任何数据。可能原因：1) 设备路径错误 2) 权限不足 3) FIO 安装问题。stderr: {stderr_msg}")
                
                # 检查输出是否是 JSON 格式
                if not result.stdout.strip().startswith('{'):
                    raise FIOError(f"FIO 输出格式错误（非 JSON）: {result.stdout[:200]}...")
                
                try:
                    fio_output = json.loads(result.stdout)
                except json.JSONDecodeError as e:
                    raise FIOError(f"FIO 输出解析失败：{e}. 输出内容：{result.stdout[:500]}...")
                
                # 转换为标准化指标
                metrics = FIOMetrics.from_fio_output(fio_output, config.rw)
                
                self.logger.info(f"FIO 测试完成：{config.name}")
                self.logger.info(f"  带宽：{metrics.bandwidth['value']:.2f} {metrics.bandwidth['unit']}")
                self.logger.info(f"  IOPS: {metrics.iops['value']:.0f} {metrics.iops['unit']}")
                self.logger.info(f"  平均延迟：{metrics.latency_ns['mean']/1000:.2f} μs")
                
                return metrics
                
            except subprocess.TimeoutExpired as e:
                last_error = FIOError(f"FIO 执行超时（{self.timeout}s）")
                self.logger.warning(f"尝试 {attempt}/{self.retries}: {last_error}")
                
            except json.JSONDecodeError as e:
                last_error = FIOError(f"FIO 输出解析失败：{e}")
                self.logger.error(f"尝试 {attempt}/{self.retries}: {last_error}")
                break  # JSON 解析错误不重试
                
            except FIOError as e:
                last_error = e
                self.logger.warning(f"尝试 {attempt}/{self.retries}: {e}")
                
                if attempt < self.retries:
                    import time
                    wait_time = 2 ** (attempt - 1)  # 指数退避
                    self.logger.info(f"等待 {wait_time}s 后重试...")
                    time.sleep(wait_time)
        
        # 所有重试失败
        raise last_error or FIOError("FIO 执行失败（未知错误）")
    
    def _create_mock_metrics(self, rw_type: str) -> FIOMetrics:
        """创建模拟指标（用于 dry-run）"""
        return FIOMetrics(
            bandwidth={'value': 0, 'unit': 'MB/s'},
            iops={'value': 0, 'unit': 'IOPS'},
            latency_ns={'min': 0, 'max': 0, 'mean': 0, 'stddev': 0, 'percentile': {}},
            cpu={'usr': 0, 'sys': 0, 'total': 0},
            raw={}
        )
    
    # ========== 便捷方法：常用测试场景 ==========
    
    def run_seq_read(
        self,
        filename: str = '/dev/ufs0',
        size: str = '1G',
        runtime: int = 60,
        bs: str = '128k',
        ioengine: str = 'sync',
        **kwargs
    ) -> FIOMetrics:
        """顺序读测试（Burst 模式）"""
        config = FIOConfig(
            name='seq_read',
            filename=filename,
            rw='read',
            bs=bs,
            size=size,
            runtime=runtime,
            ioengine=ioengine,
            time_based=True,
            **kwargs
        )
        return self.run(config)
    
    def run_seq_write(
        self,
        filename: str = '/dev/ufs0',
        size: str = '1G',
        runtime: int = 60,
        bs: str = '128k',
        ioengine: str = 'sync',
        **kwargs
    ) -> FIOMetrics:
        """顺序写测试（Burst 模式）"""
        config = FIOConfig(
            name='seq_write',
            filename=filename,
            rw='write',
            bs=bs,
            size=size,
            runtime=runtime,
            ioengine=ioengine,
            time_based=True,
            **kwargs
        )
        return self.run(config)
    
    def run_rand_read(
        self,
        filename: str = '/dev/ufs0',
        size: str = '1G',
        runtime: int = 60,
        bs: str = '4k',
        iodepth: int = 32,
        ioengine: str = 'sync',
        **kwargs
    ) -> FIOMetrics:
        """随机读测试（IOPS 模式）"""
        config = FIOConfig(
            name='rand_read',
            filename=filename,
            rw='randread',
            bs=bs,
            size=size,
            runtime=runtime,
            ioengine=ioengine,
            iodepth=iodepth,
            time_based=True,
            **kwargs
        )
        return self.run(config)
    
    def run_rand_write(
        self,
        filename: str = '/dev/ufs0',
        size: str = '1G',
        runtime: int = 60,
        bs: str = '4k',
        iodepth: int = 32,
        ioengine: str = 'sync',
        **kwargs
    ) -> FIOMetrics:
        """随机写测试（IOPS 模式）"""
        config = FIOConfig(
            name='rand_write',
            filename=filename,
            rw='randwrite',
            bs=bs,
            size=size,
            runtime=runtime,
            ioengine=ioengine,
            iodepth=iodepth,
            time_based=True,
            **kwargs
        )
        return self.run(config)
    
    def run_mixed_rw(
        self,
        filename: str = '/dev/ufs0',
        size: str = '1G',
        runtime: int = 60,
        bs: str = '4k',
        iodepth: int = 32,
        read_ratio: int = 70,
        ioengine: str = 'sync',
        **kwargs
    ) -> FIOMetrics:
        """
        混合读写测试
        
        Args:
            read_ratio: 读操作百分比（0-100）
        """
        config = FIOConfig(
            name='mixed_rw',
            filename=filename,
            rw='randrw',
            bs=bs,
            size=size,
            runtime=runtime,
            ioengine=ioengine,
            iodepth=iodepth,
            time_based=True,
            rwmixread=read_ratio,
            **kwargs
        )
        return self.run(config)
    
    def run_latency_test(
        self,
        filename: str = '/dev/ufs0',
        size: str = '512M',
        runtime: int = 120,
        bs: str = '4k',
        iodepth: int = 1,  # QD=1 测延迟
        ioengine: str = 'sync',
        ramp_time: int = 0,
        **kwargs
    ) -> FIOMetrics:
        """延迟测试（QD=1，小 block）
        
        Args:
            ramp_time: 预热时间（秒），用于稳定状态
        """
        config = FIOConfig(
            name='latency',
            filename=filename,
            rw='randread',
            bs=bs,
            size=size,
            runtime=runtime,
            ioengine=ioengine,
            iodepth=iodepth,
            time_based=True,
            ramp_time=ramp_time if ramp_time > 0 else None,
            **kwargs
        )
        return self.run(config)


# ========== 模块级便捷函数 ==========

def seq_read(**kwargs) -> FIOMetrics:
    """顺序读测试（便捷函数）"""
    return FIO().run_seq_read(**kwargs)


def seq_write(**kwargs) -> FIOMetrics:
    """顺序写测试（便捷函数）"""
    return FIO().run_seq_write(**kwargs)


def rand_read(**kwargs) -> FIOMetrics:
    """随机读测试（便捷函数）"""
    return FIO().run_rand_read(**kwargs)


def rand_write(**kwargs) -> FIOMetrics:
    """随机写测试（便捷函数）"""
    return FIO().run_rand_write(**kwargs)


def mixed_rw(**kwargs) -> FIOMetrics:
    """混合读写测试（便捷函数）"""
    return FIO().run_mixed_rw(**kwargs)
