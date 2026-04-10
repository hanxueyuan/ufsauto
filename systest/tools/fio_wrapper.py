#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FIO Tool Wrapper - FIO Wrapper

Production-grade FIO test tool wrapper providing:
- Unified FIO command construction
- Result parsing and validation
- Error handling and retry
- Standardized performance metrics output

Usage:
    from tools.fio_wrapper import FIO

    fio = FIO()
    result = fio.run_seq_read(
        filename='/dev/ufs0',
        size='1G',
        runtime=60,
        bs='128k'
    )
    print(f"Bandwidth: {result['bandwidth']['value']} {result['bandwidth']['unit']}")
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
    """FIO IO engine"""
    SYNC = 'sync'
    LIBAIO = 'libaio'
    IO_URING = 'io_uring'
    PSYNC = 'psync'
    PVSYNC = 'pvsync'

class FIORWType(Enum):
    """FIO read/write mode"""
    READ = 'read'
    WRITE = 'write'
    RANDREAD = 'randread'
    RANDWRITE = 'randwrite'
    READWRITE = 'readwrite'
    RANDRW = 'randrw'
    TRIM = 'trim'

@dataclass
class FIOConfig:
    """FIO configuration parameters"""
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

    rate_iops: Optional[int] = None
    rate: Optional[int] = None
    thinktime: Optional[int] = None
    ramp_time: Optional[int] = None
    time_based: bool = False
    verify: Optional[str] = None

    rwmixread: Optional[int] = None

    output_format: str = 'json'

    def to_args(self) -> List[str]:
        """Convert to FIO command line arguments"""
        args = ['fio', f'--name={self.name}']

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

        if self.rwmixread is not None:
            args.append(f'--rwmixread={self.rwmixread}')

        args.append(f'--output-format={self.output_format}')

        return args

@dataclass
class FIOMetrics:
    """FIO performance metrics (standardized output)"""
    bandwidth: Dict[str, Any]
    iops: Dict[str, Any]
    latency_ns: Dict[str, Any]
    cpu: Dict[str, Any]
    raw: Dict[str, Any]

    @classmethod
    def from_fio_output(cls, fio_output: Dict[str, Any], rw_type: str) -> 'FIOMetrics':
        """Create metrics object from FIO JSON output"""
        import logging
        logger = logging.getLogger(__name__)

        logger.debug(f"FIO output keys: {list(fio_output.keys())}")
        job = fio_output['jobs'][0]
        logger.debug(f"Job data keys: {list(job.keys())}")

        if 'read' in job:
            logger.debug(f"Read data keys: {list(job['read'].keys())}")
        if 'write' in job:
            logger.debug(f"Write data keys: {list(job['write'].keys())}")

        if 'read' in rw_type.lower():
            io_stats = job.get('read', {})
        elif 'write' in rw_type.lower():
            io_stats = job.get('write', {})
        else:
            read_stats = job.get('read', {})
            write_stats = job.get('write', {})
            read_bw = read_stats.get('bw_bytes', 0)
            write_bw = write_stats.get('bw_bytes', 0)
            read_iops = read_stats.get('iops', 0)
            write_iops = write_stats.get('iops', 0)
            io_stats = {
                'bw_bytes': read_bw + write_bw,
                'iops': read_iops + write_iops,
                'lat_ns_read': read_stats.get('lat_ns', {}),
                'lat_ns_write': write_stats.get('lat_ns', {})
            }

        bandwidth = {
            'value': io_stats.get('bw_bytes', 0) / (1024 * 1024),
            'unit': 'MB/s'
        }

        iops = {
            'value': io_stats.get('iops', 0),
            'unit': 'IOPS'
        }

        if 'lat_ns_read' in io_stats and 'lat_ns_write' in io_stats:
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
            lat_ns = io_stats.get('lat_ns', {})
            latency = {
                'min': lat_ns.get('min', 0),
                'max': lat_ns.get('max', 0),
                'mean': lat_ns.get('mean', 0),
                'stddev': lat_ns.get('stddev', 0),
                'percentile': lat_ns.get('percentile', {})
            }

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
    """FIO execution error"""
    def __init__(self, message: str, returncode: int = -1, stderr: str = ''):
        super().__init__(message)
        self.returncode = returncode
        self.stderr = stderr

class FIO:
    """FIO tool wrapper class"""

    def __init__(self, timeout: int = 300, retries: int = 1, logger=None):
        """
        Initialize FIO tool

        Args:
            timeout: FIO execution timeout (seconds)
            retries: Number of retry attempts on failure
            logger: Logger instance
        """
        self.timeout = timeout
        self.retries = retries
        self.logger = logger or logging.getLogger(__name__)

    def run(self, config: FIOConfig, allowed_prefixes: list = None) -> FIOMetrics:
        """
        Execute FIO test

        Args:
            config: FIO configuration
            allowed_prefixes: List of allowed file path prefixes (e.g., ['/tmp', '/mapdata'])

        Returns:
            FIOMetrics: Performance metrics

        Raises:
            FIOError: FIO execution failure
        """
        filename = Path(config.filename)
        if allowed_prefixes and not str(filename).startswith("/dev/"):
            if not any(str(filename).startswith(p) for p in allowed_prefixes):
                if not str(filename).startswith('/dev/'):
                    raise FIOError(f"Invalid filename path: {config.filename} (must be within allowed directories or device path)")
        cmd = config.to_args()

        self.logger.info(f"Executing FIO test: {config.name}")
        self.logger.debug(f"FIO command: {' '.join(cmd)}")

        last_error = None
        for attempt in range(1, self.retries + 1):
            try:
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=self.timeout + 30
                )

                if result.returncode != 0:
                    self.logger.error("FIO execution failed:")
                    self.logger.error(f"  Command: {' '.join(cmd[:10])}...")
                    self.logger.error(f"  Return code: {result.returncode}")
                    stderr_preview = result.stderr[:500] if result.stderr else 'None'
                    self.logger.error(f"  stderr: {stderr_preview}")
                    if len(result.stderr or '') > 500:
                        self.logger.debug(f"  stderr full content: {result.stderr}")

                    raise FIOError(
                        f"FIO execution failed: {result.stderr}",
                        returncode=result.returncode,
                        stderr=result.stderr
                    )

                if not result.stdout or not result.stdout.strip():
                    stderr_msg = result.stderr.strip() if result.stderr else 'No error output'
                    raise FIOError(f"FIO produced no output. Possible causes: 1) Wrong device path 2) Insufficient permissions 3) FIO installation issue. stderr: {stderr_msg}")

                import re

                self.logger.debug(f"FIO raw output length: stdout={len(result.stdout)} chars, stderr={len(result.stderr)} chars")
                self.logger.debug(f"FIO capture strategy: Use regex to extract JSON part")

                json_match = re.search(r'\{[\s\S]*\}', result.stdout)
                if json_match:
                    json_str = json_match.group(0)
                    self.logger.debug(f"Successfully extracted JSON, length: {len(json_str)} chars")
                else:
                    json_str = result.stdout
                    self.logger.warning(f"JSON part not found, using full output")

                if not json_str.strip().startswith('{'):
                    self.logger.error(f"FIO output format error, raw output preview:")
                    self.logger.error(f"  stdout[:500]: {result.stdout[:500]}...")
                    self.logger.error(f"  stderr[:500]: {result.stderr[:500] if result.stderr else 'None'}...")
                    raise FIOError(f"FIO output format error (non-JSON). stdout={len(result.stdout)} chars, stderr={len(result.stderr)} chars. Preview: {json_str[:200]}...")

                try:
                    fio_output = json.loads(json_str)
                except json.JSONDecodeError as e:
                    import tempfile
                    debug_file = Path(tempfile.mktemp(suffix='_fio_debug.json'))
                    try:
                        with open(debug_file, 'w', encoding='utf-8') as f:
                            f.write(result.stdout)
                        self.logger.error(f"FIO output parsing failed: {e}")
                        self.logger.error(f"  Debug file saved: {debug_file}")
                        self.logger.error(f"  stdout length: {len(result.stdout)} chars")
                        self.logger.error(f"  stderr length: {len(result.stderr)} chars")
                        raise FIOError(f"FIO output parsing failed: {e}. Debug file: {debug_file}")
                    finally:
                        if debug_file.exists():
                            try:
                                debug_file.unlink()
                            except Exception:
                                pass

                metrics = FIOMetrics.from_fio_output(fio_output, config.rw)

                self.logger.info(f"FIO test completed: {config.name}")
                self.logger.info(f"  Bandwidth: {metrics.bandwidth['value']:.2f} {metrics.bandwidth['unit']}")
                self.logger.info(f"  IOPS: {metrics.iops['value']:.0f} {metrics.iops['unit']}")
                if 'mean' in metrics.latency_ns:
                    avg_lat = metrics.latency_ns['mean'] / 1000
                elif 'read' in metrics.latency_ns and 'write' in metrics.latency_ns:
                    read_lat = metrics.latency_ns['read'].get('mean', 0) / 1000
                    write_lat = metrics.latency_ns['write'].get('mean', 0) / 1000
                    avg_lat = (read_lat + write_lat) / 2
                else:
                    avg_lat = 0
                self.logger.info(f"  Average latency: {avg_lat:.2f} μs")

                return metrics

            except subprocess.TimeoutExpired as e:
                import signal
                import os
                try:
                    if e.pid is not None:
                        os.killpg(os.getpgid(e.pid), signal.SIGKILL)
                        self.logger.debug(f"Killed timed out process group: {e.pid}")
                except (ProcessLookupError, ValueError):
                    pass
                last_error = FIOError(f"FIO execution timeout ({self.timeout}s)")
                self.logger.warning(f"Attempt {attempt}/{self.retries}: {last_error}")

            except json.JSONDecodeError as e:
                last_error = FIOError(f"FIO output parsing failed: {e}")
                self.logger.error(f"Attempt {attempt}/{self.retries}: {last_error}")
                break

            except FIOError as e:
                last_error = e
                self.logger.warning(f"Attempt {attempt}/{self.retries}: {e}")

                if attempt < self.retries:
                    import time
                    wait_time = 2 ** (attempt - 1)
                    self.logger.info(f"Waiting {wait_time}s before retry...")
                    time.sleep(wait_time)

        raise last_error or FIOError("FIO execution failed (unknown error)")

    def run_seq_read(
        self,
        filename: str = '/dev/ufs0',
        size: str = '1G',
        runtime: int = 60,
        bs: str = '128k',
        ioengine: str = 'sync',
        **kwargs
    ) -> FIOMetrics:
        """Sequential read test (Burst mode)"""
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
        """Sequential write test (Burst mode)"""
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
        """Random read test (IOPS mode)"""
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
        """Random write test (IOPS mode)"""
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
        Mixed read/write test

        Args:
            read_ratio: Read operation percentage (0-100)
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
        iodepth: int = 1,
        ioengine: str = 'sync',
        ramp_time: int = 0,
        **kwargs
    ) -> FIOMetrics:
        """Latency test (QD=1, small block)

        Args:
            ramp_time: Warm-up time (seconds), used for steady state
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

def seq_read(**kwargs) -> FIOMetrics:
    """Sequential read test (convenience function)"""
    return FIO().run_seq_read(**kwargs)

def seq_write(**kwargs) -> FIOMetrics:
    """Sequential write test (convenience function)"""
    return FIO().run_seq_write(**kwargs)

def rand_read(**kwargs) -> FIOMetrics:
    """Random read test (convenience function)"""
    return FIO().run_rand_read(**kwargs)

def rand_write(**kwargs) -> FIOMetrics:
    """Random write test (convenience function)"""
    return FIO().run_rand_write(**kwargs)

def mixed_rw(**kwargs) -> FIOMetrics:
    """Mixed read/write test (convenience function)"""
    return FIO().run_mixed_rw(**kwargs)
