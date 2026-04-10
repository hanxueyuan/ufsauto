#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test Execution Engine - Test Runner
Responsible for loading test suites, executing test cases, and collecting results.

Test Status Definitions:
    PASS  - Test completed, data collection successful. For performance tests,
            whether metrics meet thresholds is recorded via annotations.
    FAIL  - Validation failed. Used for functional tests (e.g., data verification failures).
            Performance tests generally do not produce FAIL.
    ERROR - Exception occurred during test execution (FIO crash, IO error, etc.).
    SKIP  - Preconditions not met, test not executed (device missing, insufficient space,
            tools not installed, etc.).
    ABORT - Test interrupted or timed out (user Ctrl+C, timeout kill).
"""
import logging
import os
import re
import signal
import subprocess
import time
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

PERFORMANCE_THRESHOLD = 0.9

class TestAborted(Exception):
    """Test was aborted"""
    pass

class FailStop(Exception):
    """
    Fail-Stop: Immediately terminate the current test case and stop the suite.

    Raise FailStop("reason") in execute() or validate() to trigger.
    The case status becomes FAIL, and the suite will also stop (handled by TestRunner).

    Typical scenarios: Device returns IO error, severe data corruption, risk in continuing.
    """
    pass

class TestCase:
    """
    Base test case class.

    Failure handling modes:

    1. Fail-Continue (soft failure):
       Use self.record_failure() in execute/validate to record failures, but continue
       executing subsequent logic. After the case completes, if any failures were recorded,
       the final status becomes FAIL. The suite continues to the next case.

    2. Fail-Stop (hard failure):
       Raise FailStop("reason") in execute/validate.
       Execution stops immediately, final status is FAIL.
       The suite also stops (no more cases run).
    """

    name: str = "base_test"
    description: str = "Base test case"

    def __init__(self, device: str = '/dev/sda', test_dir: Path = None, verbose: bool = False, logger=None):
        self._failures: List[Dict[str, Any]] = []
        self.device = device
        self.test_dir = test_dir
        self.verbose = verbose
        self.logger = logger or logging.getLogger(__name__)
        self._pre_test_health = None
        self._post_test_health = None
        self.test_file: Optional[Path] = None

        if self.test_dir and not self.test_dir.exists():
            self.test_dir.mkdir(parents=True, exist_ok=True)

    def get_test_file_path(self, name: str) -> Path:
        """Get test file path, unified under test directory.

        Args:
            name: Test file name (e.g., "seq_read")

        Returns:
            Path: Test file path

        Raises:
            RuntimeError: Raised when test_dir is not specified
        """
        if not self.test_dir:
            raise RuntimeError(f"Test directory not specified, cannot create test file: {name}")

        test_file = self.test_dir / f"ufs_test_{name}"
        try:
            test_file.resolve().relative_to(self.test_dir.resolve())
        except ValueError:
            raise RuntimeError(f"Test file path not within test directory: {test_file}")
        return test_file

    def record_failure(self, check: str, expected: str, actual: str, reason: str = ''):
        """
        Record a Fail-Continue failure (soft failure).

        After calling, the case continues execution but final status becomes FAIL.
        All failure records appear in the result's 'failures' field.

        Args:
            check: Check item name (e.g., "Pattern A Data Verification")
            expected: Expected value
            actual: Actual value
            reason: Additional explanation (optional)
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
            f"[Fail-Continue] {check}: Expected {expected}, Actual {actual}"
            + (f" ({reason})" if reason else "")
        )

    @property
    def has_failures(self) -> bool:
        """Whether there are Fail-Continue records"""
        return len(self._failures) > 0

    def setup(self) -> bool:
        """Pre-test setup. Return False for SKIP status."""
        self.logger.debug(f"Setup: {self.name}")

        try:
            from tools.ufs_utils import UFSDevice
            ufs = UFSDevice(self.device, logger=self.logger)
            self._pre_test_health = ufs.get_health_status()
            self.logger.debug(f"Recorded health baseline: {self._pre_test_health.get('status', 'Unknown')}")
        except Exception as e:
            self.logger.warning(f"Health status recording failed: {type(e).__name__}: {e}")
            self._pre_test_health = None

        return True

    def execute(self) -> Dict[str, Any]:
        """Execute test logic"""
        raise NotImplementedError("Subclasses must implement the execute method")

    def validate(self, result: Dict[str, Any]) -> bool:
        """
        Validate results.

        For performance tests: Recommend always returning True; metric compliance
        is recorded via result['annotations'].

        For functional tests:
          - Fail-Continue: Use self.record_failure() to record failures, return True
            to let the flow complete. Framework automatically sets final status to FAIL
            based on self.has_failures.
          - Fail-Stop: Raise FailStop("reason") to terminate immediately.
          - Or directly return False (equivalent to Fail-Continue with one failure).

        Postcondition checks (hardware reliability validation) should be called at
        the end of subclass validate() via self._check_postcondition().
        """
        raise NotImplementedError("Subclasses must implement the validate method")

    def _check_postcondition(self) -> bool:
        """
        Postcondition check - Hardware reliability validation.

        Check device health status changes before and after test to ensure no
        hardware damage. Subclasses can call this method at the end of validate().

        Returns:
            bool: True if check passes; records failure but returns True if
                  hardware damage detected (let framework handle it)
        """
        self.logger.info("=" * 60)
        self.logger.info("🔍 开始 Postcondition 检查（硬件健康验证）...")
        self.logger.info("=" * 60)

        if not self._pre_test_health:
            self.logger.warning("⚠️  缺少测试前健康状态数据")
            self.logger.warning("   可能原因：setup() 中健康状态采集失败，或 UFS 设备不支持健康查询")

        if not self._post_test_health:
            self.logger.warning("⚠️  缺少测试后健康状态数据")
            self.logger.warning("   可能原因：validate() 前健康状态采集失败，或 UFS 设备不支持健康查询")

        if not self._pre_test_health or not self._post_test_health:
            self.logger.info("⏭️  Postcondition 检查跳过：健康状态数据不完整（非致命，继续测试流程）")
            self.logger.info("=" * 60)
            return True

        self.logger.info("📊 健康状态对比:")
        pre_status = self._pre_test_health.get('status', 'OK')
        post_status = self._post_test_health.get('status', 'OK')
        self.logger.info(f"   测试前：{pre_status}")
        self.logger.info(f"   测试后：{post_status}")

        if pre_status == 'OK' and post_status != 'OK':
            self.logger.error(f"❌ 设备健康状态恶化：{pre_status} → {post_status}")
            self.record_failure(
                "Device Health Status",
                "OK",
                post_status,
                "Device health status degraded after test"
            )
        else:
            self.logger.info(f"✅ 设备健康状态正常：{pre_status} → {post_status}")

        pre_warning = self._pre_test_health.get('critical_warning', 0)
        post_warning = self._post_test_health.get('critical_warning', 0)
        self.logger.info(f"📊 Critical Warning 对比:")
        self.logger.info(f"   测试前：{pre_warning}")
        self.logger.info(f"   测试后：{post_warning}")

        if post_warning > pre_warning:
            self.logger.error(f"❌ 设备出现新的 Critical Warning：{pre_warning} → {post_warning}")
            self.record_failure(
                "Critical Warning Flag",
                f"{pre_warning}",
                f"{post_warning}",
                "Device has new critical warnings"
            )
        else:
            self.logger.info(f"✅ Critical Warning 状态正常：{pre_warning} → {post_warning}")

        pre_eol = self._pre_test_health.get('pre_eol_info', '0x00')
        post_eol = self._post_test_health.get('pre_eol_info', '0x00')
        self.logger.info(f"📊 Pre-EOL 状态对比:")
        self.logger.info(f"   测试前：{pre_eol}")
        self.logger.info(f"   测试后：{post_eol}")

        if pre_eol == '0x00' and post_eol != '0x00':
            self.logger.error(f"❌ 设备接近寿命终点：{post_eol}")
            self.record_failure(
                "Pre-EOL Status",
                "Normal",
                f"EOL Warning: {post_eol}",
                "Device approaching end of life"
            )
        else:
            self.logger.info(f"✅ Pre-EOL 状态正常：{pre_eol} → {post_eol}")

        self.logger.info("=" * 60)
        self.logger.info("✅ Postcondition 检查完成")
        self.logger.info("=" * 60)
        return True

    def teardown(self) -> bool:
        """Post-test cleanup"""
        self.logger.debug(f"Teardown: {self.name}")

        test_file = getattr(self, 'test_file', None)
        if test_file and isinstance(test_file, Path):
            if test_file.exists():
                try:
                    file_size = self.test_file.stat().st_size
                    self.test_file.unlink()
                    self.logger.debug(f"Cleaned up test file: {self.test_file} ({file_size / 1024 / 1024:.1f} MB)")
                except Exception as e:
                    self.logger.warning(f"Test file cleanup failed: {e}")
                    if self.test_file.exists():
                        try:
                            file_size = self.test_file.stat().st_size
                            self.logger.warning(f"Test file not removed: {self.test_file} ({file_size / 1024 / 1024:.1f} MB)")
                            if file_size > 100 * 1024 * 1024:
                                self.logger.warning(f"File is large, please delete manually: rm {self.test_file}")
                            else:
                                self.logger.debug(f"File is small, can delete manually: rm {self.test_file}")
                        except Exception as stat_error:
                            self.logger.warning(f"Unable to get file size (may be deleted or locked): {stat_error}")
                            self.logger.warning(f"Check file status: ls -lh {self.test_file}")

    def run(self) -> Dict[str, Any]:
        """Complete execution flow"""
        self.start_time = datetime.now()
        self._failures = []

        self.logger.info("=" * 60)
        self.logger.info(f"Test Case: {self.name}")
        self.logger.info(f"Description: {self.description}")
        self.logger.info(f"Device: {self.device}")
        self.logger.info(f"Test Directory: {self.test_dir}")
        self.logger.info(f"Test File: {getattr(self, 'test_file', 'Not set')}")
        self.logger.info("=" * 60)

        original_handler = signal.getsignal(signal.SIGINT)
        def _abort_handler(signum, frame):
            raise TestAborted("Test interrupted by user (SIGINT)")

        try:
            signal.signal(signal.SIGINT, _abort_handler)

            self.logger.debug("Executing setup...")
            if not self.setup():
                self.end_time = datetime.now()
                duration = (self.end_time - self.start_time).total_seconds()
                self.logger.warning(f"Preconditions not met, skipping test: {self.name}")
                return {
                    'name': self.name,
                    'status': 'SKIP',
                    'reason': 'Setup returned False (precondition not met)',
                    'duration': duration,
                    'timestamp': self.start_time.isoformat()
                }

            self.logger.debug("Executing test logic...")
            result = self.execute()

            self.logger.debug("Validating results...")

            try:
                from tools.ufs_utils import UFSDevice
                ufs = UFSDevice(self.device, logger=self.logger)
                self._post_test_health = ufs.get_health_status()
                self.logger.debug(f"Recorded post-test health status: {self._post_test_health.get('status', 'Unknown')}")
            except Exception as e:
                self.logger.warning(f"Post-test health recording failed: {type(e).__name__}: {e}")
                self._post_test_health = None

            passed = self.validate(result)

            self.end_time = datetime.now()
            duration = (self.end_time - self.start_time).total_seconds()

            should_fail = False
            fail_reasons = []

            if not passed:
                should_fail = True
                fail_reasons.append("Validation failed")

            if self.has_failures:
                should_fail = True
                fail_reasons.append(f"Has {len(self._failures)} Fail-Continue items")

            if should_fail:
                status = 'FAIL'
                self.logger.info(f"Test completed: {self.name} - FAIL ({duration:.2f}s)")
                self.logger.info(f"  Failure reasons: {', '.join(fail_reasons)}")
            else:
                status = 'PASS'
                self.logger.info(f"Test completed: {self.name} - PASS ({duration:.2f}s)")

            run_result = {
                'name': self.name,
                'status': status,
                'metrics': result,
                'duration': duration,
                'timestamp': self.start_time.isoformat()
            }

            if self._failures:
                run_result['failures'] = self._failures
                self.logger.info(f"  Total {len(self._failures)} Fail-Continue items")

            return run_result

        except FailStop as e:
            self.end_time = datetime.now()
            duration = (self.end_time - self.start_time).total_seconds()
            self.logger.error(f"Fail-Stop triggered, test terminated: {self.name} - {e}")
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
            self.logger.warning(f"Test interrupted: {self.name} ({duration:.2f}s)")
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
            self.logger.warning(f"Test interrupted: {self.name} ({duration:.2f}s)")
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
            self.logger.error(f"Test timeout: {self.name} ({duration:.2f}s)")
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
            self.logger.error(f"Test execution failed {self.name}: {e}", exc_info=True)
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
    """Test execution engine"""

    def __init__(self, device: str = None, test_dir: str = None, verbose: bool = False, mode: str = None):
        self.device_override = device
        self.test_dir_override = test_dir
        self.verbose = verbose
        self.suites_dir = Path(__file__).parent.parent / 'suites'
        self.config_dir = Path(__file__).parent.parent / 'config'
        self.test_dir = None
        self.device = None

        self.runtime_config = self._load_runtime_config()
        
        # Determine test mode: parameter > config > default
        import os
        if mode:
            self.mode = mode
        elif os.environ.get('SYSTEST_MODE'):
            self.mode = os.environ.get('SYSTEST_MODE')
        elif self.runtime_config.get('mode'):
            self.mode = self.runtime_config['mode']
        else:
            self.mode = 'development'
        
        self.is_production = self.mode == 'production'

        import importlib.util
        spec = importlib.util.spec_from_file_location("check_env", str(Path(__file__).parent.parent / 'bin' / 'check_env.py'))
        check_env_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(check_env_module)
        EnvironmentChecker = check_env_module.EnvironmentChecker
        checker = EnvironmentChecker(mode='deploy', verbose=False, config_dir=self.config_dir)
        checker.collect_storage()
        checker.collect_test_directory()

        if checker.runtime_config.get('device'):
            self.runtime_config['device'] = checker.runtime_config['device']
        if checker.runtime_config.get('test_dir'):
            self.runtime_config['test_dir'] = checker.runtime_config['test_dir']

        try:
            config_path = self.config_dir / 'runtime.json'
            merged = {**self.runtime_config, **checker.runtime_config}
            merged['env_checked_at'] = checker.runtime_config.get('env_checked_at')
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(merged, f, indent=2, ensure_ascii=False)
            logger.info(f"Configuration auto-updated: {config_path} (latest environment detection)")
            self.runtime_config = merged
        except Exception as e:
            logger.warning(f"Auto-save configuration failed: {e} (continuing with current detection)")

        if self.device_override:
            self.device = self.device_override
            logger.info(f"Device path: {self.device} (manually specified)")
        elif self.runtime_config.get('device'):
            self.device = self.runtime_config['device']
            logger.info(f"Device path: {self.device} (from config)")
        else:
            self.device = self._auto_detect_device()
            if self.device:
                logger.info(f"Device path: {self.device} (auto-detected)")
            else:
                self.device = '/dev/sda'
                logger.warning(f"Auto-detection failed, using default: {self.device}")

        self._resolve_test_dir()

        self.suites = self._load_suites()

    def _load_runtime_config(self) -> Dict[str, Any]:
        """Load runtime.json configuration file"""
        config_path = self.config_dir / 'runtime.json'
        if config_path.exists():
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                checked_at = config.get('env_checked_at', 'Unknown')
                logger.info(f"Loaded configuration: {config_path} (Environment checked at: {checked_at})")
                return config
            except Exception as e:
                logger.warning(f"Configuration file read failed: {e}")
                return {}
        else:
            logger.info(f"Configuration file does not exist: {config_path} (recommend running check-env --save-config)")
            return {}

    def _auto_detect_device(self) -> Optional[str]:
        """Auto-detect available block device"""
        import os

        device_priority = ['sda', 'vda', 'mmcblk0', 'nvme0n1']

        for device_name in device_priority:
            device_path = f'/dev/{device_name}'
            if os.path.exists(device_path):
                logger.debug(f"Found available device: {device_path}")
                return device_path

        try:
            import glob
            block_devices = glob.glob('/dev/sd*') + glob.glob('/dev/vd*') + glob.glob('/dev/mmcblk*') + glob.glob('/dev/nvme*')
            if block_devices:
                for device in sorted(block_devices):
                    if not device[-1].isdigit():
                        logger.debug(f"Found block device: {device}")
                        return device
        except Exception as e:
            logger.debug(f"Block device detection failed: {e}")

        return None

    def _resolve_test_dir(self):
        """Determine test directory: User specified > Auto-detected > Fallback default"""
        allowed_prefixes = ['/tmp', '/mapdata']

        if self.test_dir_override:
            test_dir = Path(self.test_dir_override).absolute()
            try:
                real_path = test_dir.resolve()
                if not any(str(real_path).startswith(p) for p in allowed_prefixes):
                    logger.error(f"Test directory not within allowed paths: {test_dir} (real path: {real_path})")
                    logger.error(f"Allowed directory prefixes: {allowed_prefixes}")
                    raise RuntimeError(f"Test directory must be within: {allowed_prefixes}")
            except FileNotFoundError:
                try:
                    test_dir.mkdir(parents=True, exist_ok=True)
                    real_path = test_dir.resolve()
                    if not any(str(real_path).startswith(p) for p in allowed_prefixes):
                        logger.error(f"Test directory not within allowed paths: {test_dir} (real path: {real_path})")
                        logger.error(f"Allowed directory prefixes: {allowed_prefixes}")
                        raise RuntimeError(f"Test directory must be within: {allowed_prefixes}")
                except Exception as e:
                    logger.error(f"Test directory verification failed: {e}")
                    raise
            except Exception as e:
                logger.error(f"Test directory verification failed: {e}")
                raise
            self.test_dir = test_dir
            self.test_dir.mkdir(parents=True, exist_ok=True)
            logger.info(f"Test directory: {self.test_dir} (manually specified)")
            return

        if self.runtime_config.get("test_dir"):
            self.test_dir = Path(self.runtime_config["test_dir"]).absolute()
            self.test_dir.mkdir(parents=True, exist_ok=True)
            logger.info(f"Test directory: {self.test_dir} (auto-detected)")
            return

        fallback_dirs = [
            Path('/mapdata/ufs_test').absolute(),
            Path('/tmp/ufs_test').absolute(),
        ]
        for fallback in fallback_dirs:
            try:
                fallback.mkdir(parents=True, exist_ok=True)
                self.test_dir = fallback
                logger.warning(f"Falling back to default directory: {self.test_dir}")
                return
            except Exception:
                continue

        try:
            self.test_dir = Path('/tmp/ufs_test').absolute()
            self.test_dir.mkdir(parents=True, exist_ok=True)
            logger.error(f"All fallback directories failed, forcing: {self.test_dir}")
        except Exception as e:
            logger.critical(f"Test directory creation completely failed: {e}")
            logger.critical(f"Possible causes: Disk full, /tmp not writable, or insufficient permissions")
            logger.critical(f"Check: df -h /tmp && ls -ld /tmp")
            raise RuntimeError(f"Cannot create any test directory: {e}")

        try:
            import shutil
            stat = shutil.disk_usage(self.test_dir)
            free_gb = stat.free / (1024 ** 3)
            if free_gb < 2:
                logger.warning(f"Insufficient space in test directory: {free_gb:.1f} GB (recommended >= 2GB)")
                logger.warning(f"Please free up space or specify --test-dir to another directory")
                logger.warning(f"Check disk usage: df -h {self.test_dir}")
            else:
                logger.debug(f"Test directory available space: {free_gb:.1f} GB")
        except Exception as e:
            logger.warning(f"Unable to check disk space: {e}")

    @staticmethod
    def _run(cmd, timeout=10):
        try:
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
            return r.returncode, r.stdout.strip(), r.stderr.strip()
        except FileNotFoundError:
            return -1, '', 'not found'
        except Exception as e:
            return -2, '', str(e)

    def _load_suites(self) -> Dict[str, List[str]]:
        """Load available test suites"""
        suites = {}

        if not self.suites_dir.exists():
            logger.warning(f"Test suite directory does not exist: {self.suites_dir}")
            return suites

        for suite_dir in self.suites_dir.iterdir():
            if suite_dir.is_dir() and not suite_dir.name.startswith('_'):
                suite_name = suite_dir.name
                test_files = list(suite_dir.glob('*.py'))
                tests = []
                for f in test_files:
                    name = f.stem
                    if name.startswith('test_'):
                        tests.append(name.replace('test_', ''))
                    elif name.startswith('t_') and name.count('_') >= 2:
                        tests.append(name)
                suites[suite_name] = tests

        return suites

    def list_suites(self) -> Dict[str, List[str]]:
        """List all available test suites"""
        return self.suites

    def get_mode_params(self) -> Dict[str, Any]:
        """Get test parameters based on mode"""
        if self.is_production:
            return {
                'fio_runtime': 300,  # 5 minutes for production
                'iterations': 3,  # Multiple iterations
                'log_level': logging.INFO,
                'report_detail': 'full',
                'precheck_skip': False,  # Run all pre-checks
                'auto_cleanup': True,  # Auto cleanup test files
            }
        else:
            return {
                'fio_runtime': 60,  # 1 minute for development
                'iterations': 1,  # Single iteration
                'log_level': logging.DEBUG,
                'report_detail': 'brief',
                'precheck_skip': True,  # Skip some pre-checks
                'auto_cleanup': False,  # Keep test files
            }

    def run_suite(self, suite_name: str, mode_params: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """Execute test suite"""
        if suite_name not in self.suites:
            raise ValueError(f"Unknown test suite: {suite_name}")

        # Get mode-specific parameters
        if mode_params is None:
            mode_params = self.get_mode_params()
        
        mode_display = 'Production' if self.is_production else 'Development'
        logger.info(f"Executing test suite: {suite_name} (Mode: {mode_display})")
        logger.info(f"  Test duration: {mode_params['fio_runtime']}s")
        logger.info(f"  Iterations: {mode_params['iterations']}")
        logger.info(f"  Auto cleanup: {mode_params['auto_cleanup']}")

        results = []
        tests = self.suites[suite_name]
        stopped = False

        for i, test_name in enumerate(tests, 1):
            if stopped:
                logger.warning(f"[{i}/{len(tests)}] Skipping test (previous Fail-Stop): {test_name}")
                results.append({
                    'name': test_name,
                    'status': 'SKIP',
                    'reason': 'Skipped due to previous Fail-Stop',
                    'duration': 0
                })
                continue

            logger.info(f"[{i}/{len(tests)}] Executing test: {test_name}")

            try:
                import sys
                suites_dir = Path(__file__).parent.parent / 'suites'
                if str(suites_dir) not in sys.path:
                    sys.path.insert(0, str(suites_dir))

                if test_name.startswith('t_'):
                    module_path = suites_dir / suite_name / f'{test_name}.py'
                else:
                    module_path = suites_dir / suite_name / f'test_{test_name}.py'
                import importlib.util
                spec = importlib.util.spec_from_file_location(f'{suite_name}.{test_name}', module_path)
                module = importlib.util.module_from_spec(spec)
                sys.modules[f'{suite_name}.{test_name}'] = module
                spec.loader.exec_module(module)
                test_class = getattr(module, 'Test', None)
                if not test_class:
                    class_name = ''.join(part.capitalize() for part in test_name.split('_'))
                    test_class = getattr(module, class_name, None)
                if not test_class:
                    raise ImportError(f"Test class not found (Test or {class_name})")
                test_instance = test_class(
                    device=self.device,
                    test_dir=self.test_dir,
                    verbose=self.verbose,
                    logger=logger,
                    mode=self.mode
                )

                result = test_instance.run()
                results.append(result)

                if result.get('fail_mode') == 'stop':
                    logger.error(f"  Fail-Stop triggered, subsequent tests will be skipped")
                    stopped = True

                status_icons = {
                    'PASS': '[PASS]', 'FAIL': '[FAIL]', 'ERROR': '[ERROR]',
                    'SKIP': '[SKIP]', 'ABORT': '[ABORT]'
                }
                icon = status_icons.get(result['status'], '[UNKNOWN]')
                logger.info(f"  {result['status']} ({result['duration']:.2f}s)")

            except ImportError as e:
                logger.error(f"Unable to import test case {test_name}: {e}")
                results.append({
                    'name': test_name,
                    'status': 'ERROR',
                    'error': f'Import failed: {e}',
                    'duration': 0
                })
            except Exception as e:
                logger.error(f"Test execution failed {test_name}: {e}")
                results.append({
                    'name': test_name,
                    'status': 'ERROR',
                    'error': str(e),
                    'duration': 0
                })

        total = len(results)
        passed = sum(1 for r in results if r['status'] == 'PASS')
        failed = sum(1 for r in results if r['status'] == 'FAIL')
        errors = sum(1 for r in results if r['status'] == 'ERROR')
        skipped = sum(1 for r in results if r['status'] == 'SKIP')
        aborted = sum(1 for r in results if r['status'] == 'ABORT')

        logger.info("=" * 60)
        logger.info(f"Test Suite Execution Summary: {suite_name}")
        logger.info("=" * 60)
        logger.info(f"  Total: {total} test cases")
        logger.info(f"  [PASS]:  {passed}")
        logger.info(f"  [FAIL]:  {failed}")
        logger.info(f"  [ERROR]: {errors}")
        logger.info(f"  [SKIP]:  {skipped}")
        logger.info(f"  [ABORT]: {aborted}")
        logger.info("-" * 60)

        logger.info("Test case execution times:")
        for r in results:
            duration = r.get('duration', 0)
            status = r.get('status', 'UNKNOWN')
            name = r.get('name', 'unknown')
            logger.info(f"  {name}: {duration:.2f}s [{status}]")

        if failed > 0 or errors > 0:
            suite_status = '[FAIL]'
            logger.info(f"Suite status: {suite_status} ({failed + errors} tests failed)")
        elif passed > 0:
            suite_status = '[PASS]'
            logger.info(f"Suite status: {suite_status} (All tests passed)")
        else:
            suite_status = '[SKIP]'
            logger.info(f"Suite status: {suite_status} (All tests skipped)")

        logger.info("=" * 60)

        return results

    def run_test(self, test_name: str) -> Dict[str, Any]:
        """Execute single test"""
        for suite_name, tests in self.suites.items():
            if test_name in tests:
                logger.info(f"Executing test: {test_name} (Suite: {suite_name})")
                results = self.run_suite(suite_name)
                for result in results:
                    if result['name'] == test_name:
                        return result

        raise ValueError(f"Unknown test case: {test_name}")
