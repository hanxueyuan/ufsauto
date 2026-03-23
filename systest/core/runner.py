#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试执行引擎 - Test Runner
负责加载测试套件、执行测试用例、收集结果

测试状态定义：
    PASS  - 测试完成，数据采集成功。对于性能测试，指标是否达标通过 annotations 记录。
    FAIL  - 验证不通过。用于功能测试（如数据校验失败）。性能测试一般不产生 FAIL。
    ERROR - 测试执行过程中发生异常（FIO crash、IO error 等）。
    SKIP  - 前置条件不满足，测试未执行（设备不存在、空间不足、工具未安装等）。
    ABORT - 测试被中断或超时（用户 Ctrl+C、超时 kill）。
"""

import logging
import signal
import subprocess
import json
import time
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Any

# 默认 logger（向后兼容）
logger = logging.getLogger(__name__)


class TestAborted(Exception):
    """测试被中断"""
    pass


class FailStop(Exception):
    """
    Fail-Stop：立刻终止当前 case 的后续逻辑。
    
    在 execute() 或 validate() 中 raise FailStop("原因") 即可。
    case 状态变为 FAIL，suite 也会停下来（由 TestRunner 处理）。
    
    典型场景：设备返回 IO error、数据严重损坏、继续跑有风险。
    """
    pass


class TestCase:
    """
    测试用例基类
    
    Failure 处理方式：
    
    1. Fail-Continue（软失败）：
       在 execute/validate 中用 self.record_failure() 记录失败，但继续执行后续逻辑。
       case 跑完后，如果有任何 failure 记录，最终状态为 FAIL。
       suite 继续跑下一个 case。
       
    2. Fail-Stop（硬失败）：
       在 execute/validate 中 raise FailStop("原因")。
       case 立刻停止，最终状态为 FAIL。
       suite 也停下来（不再跑后续 case）。
    """
    
    name: str = "base_test"
    description: str = "基础测试用例"
    
    def __init__(self, device: str = '/dev/ufs0', verbose: bool = False, logger=None):
        self.device = device
        self.verbose = verbose
        self.logger = logger or logging.getLogger(f"systest.test.{self.name}")
        self.start_time = None
        self.end_time = None
        # Fail-Continue 收集器
        self._failures: List[Dict[str, Any]] = []
    
    def record_failure(self, check: str, expected: str, actual: str, reason: str = ''):
        """
        记录一个 Fail-Continue 失败（软失败）。
        
        调用后 case 继续执行，但最终状态会变为 FAIL。
        所有 failure 记录会出现在结果的 'failures' 字段中。
        
        Args:
            check: 检查项名称（如 "Pattern A 数据校验"）
            expected: 期望值
            actual: 实际值
            reason: 附加说明（可选）
        """
        failure = {
            'check': check,
            'expected': expected,
            'actual': actual,
            'reason': reason,
            'timestamp': datetime.now().isoformat(),
        }
        self._failures.append(failure)
        self.logger.warning(
            f"❌ [Fail-Continue] {check}: 期望 {expected}, 实际 {actual}"
            + (f" ({reason})" if reason else "")
        )
    
    @property
    def has_failures(self) -> bool:
        """是否有 Fail-Continue 记录"""
        return len(self._failures) > 0
    
    def setup(self) -> bool:
        """测试前准备。返回 False 则测试状态为 SKIP。"""
        self.logger.debug(f"Setup: {self.name}")
        return True
    
    def execute(self) -> Dict[str, Any]:
        """执行测试逻辑"""
        raise NotImplementedError("子类必须实现 execute 方法")
    
    def validate(self, result: Dict[str, Any]) -> bool:
        """
        验证结果。
        
        对于性能测试：建议永远返回 True，指标达标情况通过 result['annotations'] 记录。
        对于功能测试：
          - Fail-Continue：用 self.record_failure() 记录失败，返回 True 让流程走完。
            框架会根据 self.has_failures 自动将最终状态设为 FAIL。
          - Fail-Stop：raise FailStop("原因") 立刻终止。
          - 也可以直接返回 False（等效于 Fail-Continue 只有一个失败项）。
        """
        raise NotImplementedError("子类必须实现 validate 方法")
    
    def teardown(self) -> bool:
        """测试后清理"""
        self.logger.debug(f"Teardown: {self.name}")
        return True
    
    def run(self) -> Dict[str, Any]:
        """完整执行流程"""
        self.start_time = datetime.now()
        self._failures = []  # 重置 failure 收集器
        self.logger.info(f"开始执行测试：{self.name}")
        
        # 注册信号处理，捕获中断
        original_handler = signal.getsignal(signal.SIGINT)
        def _abort_handler(signum, frame):
            raise TestAborted("测试被用户中断 (SIGINT)")
        
        try:
            signal.signal(signal.SIGINT, _abort_handler)
            
            # Setup
            self.logger.debug("执行 Setup...")
            if not self.setup():
                self.end_time = datetime.now()
                duration = (self.end_time - self.start_time).total_seconds()
                self.logger.warning(f"前置条件不满足，跳过测试：{self.name}")
                return {
                    'name': self.name,
                    'status': 'SKIP',
                    'reason': 'Setup returned False (precondition not met)',
                    'duration': duration,
                    'timestamp': self.start_time.isoformat()
                }
            
            # Execute
            self.logger.debug("执行测试逻辑...")
            result = self.execute()
            
            # Validate
            self.logger.debug("验证结果...")
            passed = self.validate(result)
            
            self.end_time = datetime.now()
            duration = (self.end_time - self.start_time).total_seconds()
            
            # 最终状态：validate 返回 False 或有 Fail-Continue 记录 → FAIL
            if not passed or self.has_failures:
                status = 'FAIL'
            else:
                status = 'PASS'
            
            self.logger.info(f"测试完成：{self.name} - {status} ({duration:.2f}s)")
            
            run_result = {
                'name': self.name,
                'status': status,
                'metrics': result,
                'duration': duration,
                'timestamp': self.start_time.isoformat()
            }
            
            # 附带 Fail-Continue 记录
            if self._failures:
                run_result['failures'] = self._failures
                self.logger.info(f"  共 {len(self._failures)} 个失败项（Fail-Continue）")
            
            return run_result
        
        except FailStop as e:
            # Fail-Stop：立刻终止，状态为 FAIL
            self.end_time = datetime.now()
            duration = (self.end_time - self.start_time).total_seconds()
            self.logger.error(f"Fail-Stop 触发，测试终止：{self.name} - {e}")
            run_result = {
                'name': self.name,
                'status': 'FAIL',
                'fail_mode': 'stop',
                'reason': str(e),
                'duration': duration,
                'timestamp': self.start_time.isoformat()
            }
            if self._failures:
                run_result['failures'] = self._failures
            return run_result
        
        except TestAborted:
            self.end_time = datetime.now()
            duration = (self.end_time - self.start_time).total_seconds()
            self.logger.warning(f"测试被中断：{self.name} ({duration:.2f}s)")
            return {
                'name': self.name,
                'status': 'ABORT',
                'reason': 'Test interrupted by user',
                'duration': duration,
                'timestamp': self.start_time.isoformat()
            }
        
        except KeyboardInterrupt:
            self.end_time = datetime.now()
            duration = (self.end_time - self.start_time).total_seconds()
            self.logger.warning(f"测试被中断：{self.name} ({duration:.2f}s)")
            return {
                'name': self.name,
                'status': 'ABORT',
                'reason': 'KeyboardInterrupt',
                'duration': duration,
                'timestamp': self.start_time.isoformat()
            }
            
        except subprocess.TimeoutExpired as e:
            self.end_time = datetime.now()
            duration = (self.end_time - self.start_time).total_seconds()
            self.logger.error(f"测试超时：{self.name} ({duration:.2f}s)")
            return {
                'name': self.name,
                'status': 'ABORT',
                'reason': f'Timeout: {e}',
                'duration': duration,
                'timestamp': self.start_time.isoformat()
            }
            
        except Exception as e:
            self.end_time = datetime.now()
            duration = (self.end_time - self.start_time).total_seconds()
            self.logger.error(f"测试执行失败 {self.name}: {e}", exc_info=True)
            return {
                'name': self.name,
                'status': 'ERROR',
                'error': str(e),
                'duration': duration,
                'timestamp': self.start_time.isoformat()
            }
        finally:
            signal.signal(signal.SIGINT, original_handler)
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
        stopped = False
        
        for i, test_name in enumerate(tests, 1):
            # 如果之前有 Fail-Stop，后续 case 全部 SKIP
            if stopped:
                logger.warning(f"[{i}/{len(tests)}] 跳过测试（前序 Fail-Stop）：{test_name}")
                results.append({
                    'name': test_name,
                    'status': 'SKIP',
                    'reason': 'Skipped due to previous Fail-Stop',
                    'duration': 0
                })
                continue
            
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
                
                # 检查是否 Fail-Stop
                if result.get('fail_mode') == 'stop':
                    logger.error(f"  🛑 Fail-Stop 触发，后续测试将被跳过")
                    stopped = True
                
                status_icons = {
                    'PASS': '✅', 'FAIL': '❌', 'ERROR': '💥',
                    'SKIP': '⏭️', 'ABORT': '⏹️'
                }
                icon = status_icons.get(result['status'], '❓')
                logger.info(f"  {icon} {result['status']} ({result['duration']:.2f}s)")
                
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
