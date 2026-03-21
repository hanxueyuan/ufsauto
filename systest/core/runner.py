#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试执行引擎 - Test Runner
负责加载测试套件、执行测试用例、收集结果
"""

import logging
import subprocess
import json
import time
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Any

# 默认 logger（向后兼容）
logger = logging.getLogger(__name__)


class TestCase:
    """测试用例基类"""
    
    name: str = "base_test"
    description: str = "基础测试用例"
    
    def __init__(self, device: str = '/dev/ufs0', verbose: bool = False, logger=None):
        self.device = device
        self.verbose = verbose
        self.logger = logger or logging.getLogger(f"systest.test.{self.name}")
        self.start_time = None
        self.end_time = None
    
    def setup(self) -> bool:
        """测试前准备"""
        self.logger.debug(f"Setup: {self.name}")
        return True
    
    def execute(self) -> Dict[str, Any]:
        """执行测试逻辑"""
        raise NotImplementedError("子类必须实现 execute 方法")
    
    def validate(self, result: Dict[str, Any]) -> bool:
        """验证结果"""
        raise NotImplementedError("子类必须实现 validate 方法")
    
    def teardown(self) -> bool:
        """测试后清理"""
        self.logger.debug(f"Teardown: {self.name}")
        return True
    
    def run(self) -> Dict[str, Any]:
        """完整执行流程"""
        self.start_time = datetime.now()
        self.logger.info(f"开始执行测试：{self.name}")
        
        try:
            # Setup
            self.logger.debug("执行 Setup...")
            if not self.setup():
                self.logger.error(f"Setup 失败：{self.name}")
                return {
                    'name': self.name,
                    'status': 'ERROR',
                    'error': 'Setup failed',
                    'duration': 0
                }
            
            # Execute
            self.logger.debug("执行测试逻辑...")
            result = self.execute()
            
            # Validate
            self.logger.debug("验证结果...")
            passed = self.validate(result)
            
            self.end_time = datetime.now()
            duration = (self.end_time - self.start_time).total_seconds()
            
            status = 'PASS' if passed else 'FAIL'
            self.logger.info(f"测试完成：{self.name} - {status} ({duration:.2f}s)")
            
            return {
                'name': self.name,
                'status': status,
                'metrics': result,
                'duration': duration,
                'timestamp': self.start_time.isoformat()
            }
            
        except Exception as e:
            self.end_time = datetime.now()
            self.logger.error(f"测试执行失败 {self.name}: {e}", exc_info=True)
            return {
                'name': self.name,
                'status': 'ERROR',
                'error': str(e),
                'duration': 0
            }
        finally:
            self.teardown()


class TestRunner:
    """测试执行引擎"""
    
    def __init__(self, device: str = '/dev/ufs0', verbose: bool = False, dry_run: bool = False, simulate: bool = False):
        self.device = device
        self.verbose = verbose
        self.dry_run = dry_run
        self.simulate = simulate  # 模拟模式（无硬件）
        self.suites_dir = Path(__file__).parent.parent / 'suites'
        
        # 加载测试套件
        self.suites = self._load_suites()
    
    def _load_suites(self) -> Dict[str, List[str]]:
        """加载可用测试套件"""
        suites = {}
        
        if not self.suites_dir.exists():
            logger.warning(f"测试套件目录不存在：{self.suites_dir}")
            return suites
        
        for suite_dir in self.suites_dir.iterdir():
            if suite_dir.is_dir() and not suite_dir.name.startswith('_'):
                suite_name = suite_dir.name
                # 支持 test_*.py 和 t_*_*.py 两种命名
                test_files = list(suite_dir.glob('*.py'))
                tests = []
                for f in test_files:
                    name = f.stem
                    if name.startswith('test_'):
                        tests.append(name.replace('test_', ''))
                    elif name.startswith('t_') and name.count('_') >= 2:
                        # t_perf_SeqReadBurst_001.py → seq_read_burst_001
                        tests.append(name)
                suites[suite_name] = tests
        
        return suites
    
    def list_suites(self) -> Dict[str, List[str]]:
        """列出所有可用测试套件"""
        return self.suites
    
    def run_suite(self, suite_name: str) -> List[Dict[str, Any]]:
        """执行测试套件"""
        if suite_name not in self.suites:
            raise ValueError(f"未知测试套件：{suite_name}")
        
        logger.info(f"执行测试套件：{suite_name}")
        
        results = []
        tests = self.suites[suite_name]
        
        for i, test_name in enumerate(tests, 1):
            logger.info(f"[{i}/{len(tests)}] 执行测试：{test_name}")
            
            if self.dry_run:
                logger.info(f"  [DRY-RUN] 跳过执行")
                results.append({
                    'name': test_name,
                    'status': 'DRY-RUN',
                    'duration': 0
                })
                continue
            
            # 动态导入测试用例
            try:
                import sys
                suites_dir = Path(__file__).parent.parent / 'suites'
                if str(suites_dir) not in sys.path:
                    sys.path.insert(0, str(suites_dir))
                
                # 导入测试模块（支持 test_*.py 和 t_*_*.py）
                if test_name.startswith('t_'):
                    module_path = suites_dir / suite_name / f'{test_name}.py'
                else:
                    module_path = suites_dir / suite_name / f'test_{test_name}.py'
                import importlib.util
                spec = importlib.util.spec_from_file_location(f'{suite_name}.{test_name}', module_path)
                module = importlib.util.module_from_spec(spec)
                sys.modules[f'{suite_name}.{test_name}'] = module
                spec.loader.exec_module(module)
                # 查找测试类（优先 Test，其次驼峰命名）
                test_class = getattr(module, 'Test', None)
                if not test_class:
                    class_name = ''.join(part.capitalize() for part in test_name.split('_'))
                    test_class = getattr(module, class_name, None)
                if not test_class:
                    raise ImportError(f"未找到测试类（Test 或 {class_name}）")
                test_instance = test_class(device=self.device, verbose=self.verbose, simulate=self.simulate)
                
                result = test_instance.run()
                results.append(result)
                
                status_icon = '✅' if result['status'] == 'PASS' else '❌'
                logger.info(f"  {status_icon} {result['status']} ({result['duration']:.2f}s)")
                
            except ImportError as e:
                logger.error(f"无法导入测试用例 {test_name}: {e}")
                results.append({
                    'name': test_name,
                    'status': 'ERROR',
                    'error': f'Import failed: {e}',
                    'duration': 0
                })
            except Exception as e:
                logger.error(f"测试执行失败 {test_name}: {e}")
                results.append({
                    'name': test_name,
                    'status': 'ERROR',
                    'error': str(e),
                    'duration': 0
                })
        
        return results
    
    def run_test(self, test_name: str) -> Dict[str, Any]:
        """执行单个测试"""
        # 查找测试用例
        for suite_name, tests in self.suites.items():
            if test_name in tests:
                logger.info(f"执行测试：{test_name} (Suite: {suite_name})")
                results = self.run_suite(suite_name)
                for result in results:
                    if result['name'] == test_name:
                        return result
        
        raise ValueError(f"未知测试用例：{test_name}")


# 示例测试用例（顺序读性能测试）
class SeqReadTest(TestCase):
    """顺序读性能测试"""
    
    name = "seq_read_burst"
    description = "顺序读取性能测试（Burst）"
    
    def __init__(self, device: str = '/dev/ufs0', verbose: bool = False):
        super().__init__(device, verbose)
        self.test_file = f"{device}/test_seq_read"
        self.size = "1G"
        self.runtime = 60
    
    def setup(self) -> bool:
        """确保测试设备可写"""
        try:
            # 检查设备是否存在
            if not Path(self.device).exists():
                logger.error(f"设备不存在：{self.device}")
                return False
            return True
        except Exception as e:
            logger.error(f"Setup 失败：{e}")
            return False
    
    def execute(self) -> Dict[str, Any]:
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
            '--ioengine=libaio',
            '--direct=1',
            '--numjobs=1',
            '--group_reporting',
            '--output-format=json'
        ]
        
        logger.debug(f"执行 FIO: {' '.join(fio_cmd)}")
        
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
            'bandwidth': {
                'value': job['bw_bytes'] / (1024 * 1024),  # MB/s
                'unit': 'MB/s'
            },
            'iops': {
                'value': job['iops'],
                'unit': 'IOPS'
            },
            'latency_avg': {
                'value': job['lat_ns']['mean'] / 1000,  # μs
                'unit': 'μs'
            },
            'latency_99999': {
                'value': job['lat_ns']['percentile']['99.999'] / 1000,  # μs
                'unit': 'μs'
            }
        }
    
    def validate(self, result: Dict[str, Any]) -> bool:
        """验证结果是否达标"""
        # 目标值：顺序读 Burst ≥ 2100 MB/s
        target = 2100  # MB/s
        actual = result['bandwidth']['value']
        
        passed = actual >= target
        
        if not passed:
            logger.warning(f"性能不达标：{actual:.1f} MB/s < {target} MB/s")
        
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
