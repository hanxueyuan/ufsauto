#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试执行引擎 - Test Runner
负责加载测试套件、执行测试用例、收集结果

测试状态定义:
    PASS  - 测试完成,数据采集成功。对于性能测试,指标是否达标通过 annotations 记录。
    FAIL  - 验证不通过。用于功能测试(如数据校验失败)。性能测试一般不产生 FAIL。
    ERROR - 测试执行过程中发生异常(FIO crash、IO error 等)。
    SKIP  - 前置条件不满足,测试未执行(设备不存在、空间不足、工具未安装等)。
    ABORT - 测试被中断或超时(用户 Ctrl+C、超时 kill)。
"""

import logging
import signal
import subprocess
import json
import time
import os
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Any

# 默认 logger(向后兼容)
logger = logging.getLogger(__name__)

# 性能阈值常量
PERFORMANCE_THRESHOLD = 0.9  # 性能达标阈值（90%）


class TestAborted(Exception):
    """测试被中断"""
    pass


class FailStop(Exception):
    """
    Fail-Stop:立刻终止当前 case 的后续逻辑。

    在 execute() 或 validate() 中 raise FailStop("原因") 即可。
    case 状态变为 FAIL,suite 也会停下来(由 TestRunner 处理)。

    典型场景:设备返回 IO error、数据严重损坏、继续跑有风险。
    """
    pass


class TestCase:
    """
    测试用例基类

    Failure 处理方式:

    1. Fail-Continue(软失败):
       在 execute/validate 中用 self.record_failure() 记录失败,但继续执行后续逻辑。
       case 跑完后,如果有任何 failure 记录,最终状态为 FAIL。
       suite 继续跑下一个 case。

    2. Fail-Stop(硬失败):
       在 execute/validate 中 raise FailStop("原因")。
       case 立刻停止,最终状态为 FAIL。
       suite 也停下来(不再跑后续 case)。
    """

    name: str = "base_test"
    description: str = "基础测试用例"

    def __init__(self, device: str = '/dev/sda', test_dir: Path = None, verbose: bool = False, logger=None):
        self.device = device
        self.test_dir = test_dir  # 全局测试目录,所有测试共用
        self.verbose = verbose
        self.logger = logger or logging.getLogger(f"systest.test.{self.name}")
        self.start_time = None
        self.end_time = None
        # Fail-Continue 收集器
        self._failures: List[Dict[str, Any]] = []
        # 健康状态监控
        self._pre_test_health = None
        self._post_test_health = None

        # 如果测试目录已指定,确保它存在
        if self.test_dir and not self.test_dir.exists():
            self.test_dir.mkdir(parents=True, exist_ok=True)

    def get_test_file_path(self, name: str) -> Path:
        """获取测试文件路径，统一放在全局测试目录下"""
        """获取测试文件路径,统一放在全局测试目录下

        Args:
            name: 测试文件名称(如 "seq_read")
        """
        if self.test_dir:
            test_file = self.test_dir / f"ufs_test_{name}"
            # 验证路径在 test_dir 下（防止路径遍历）
            try:
                test_file.resolve().relative_to(self.test_dir.resolve())
            except ValueError:
                raise RuntimeError(f"测试文件路径不在测试目录内：{test_file}")
            return test_file
        else:
            # 回退到 /tmp
            return Path(f'/tmp/ufs_test_{name}')

    def record_failure(self, check: str, expected: str, actual: str, reason: str = ''):
        """
        记录一个 Fail-Continue 失败(软失败)。

        调用后 case 继续执行,但最终状态会变为 FAIL。
        所有 failure 记录会出现在结果的 'failures' 字段中。

        Args:
            check: 检查项名称(如 "Pattern A 数据校验")
            expected: 期望值
            actual: 实际值
            reason: 附加说明(可选)
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

        # 自动记录健康基线(Postcondition 对比用)
        try:
            from tools.ufs_utils import UFSDevice
            ufs = UFSDevice(self.device, logger=self.logger)
            self._pre_test_health = ufs.get_health_status()
            self.logger.debug(f"📊 记录健康基线: {self._pre_test_health.get('status', 'Unknown')}")
        except Exception as e:
            self.logger.warning(f"⚠️  健康状态记录失败: {e}")
            self._pre_test_health = None

        return True

    def execute(self) -> Dict[str, Any]:
        """执行测试逻辑"""
        raise NotImplementedError("子类必须实现 execute 方法")

    def validate(self, result: Dict[str, Any]) -> bool:
        """
        验证结果。

        对于性能测试:建议永远返回 True,指标达标情况通过 result['annotations'] 记录。
        对于功能测试:
          - Fail-Continue:用 self.record_failure() 记录失败,返回 True 让流程走完。
            框架会根据 self.has_failures 自动将最终状态设为 FAIL。
          - Fail-Stop:raise FailStop("原因") 立刻终止。
          - 也可以直接返回 False(等效于 Fail-Continue 只有一个失败项)。

        Postcondition 检查(硬件可靠性验证)应在子类的 validate() 末尾调用
        self._check_postcondition() 方法。
        """
        raise NotImplementedError("子类必须实现 validate 方法")

    def _check_postcondition(self) -> bool:
        """
        Postcondition 检查 - 硬件可靠性验证

        检查测试前后设备健康状态变化,确保无硬件损伤。
        子类可在 validate() 末尾调用此方法。

        Returns:
            bool: 检查通过返回 True,有硬件损伤记录 failure 但返回 True(让框架处理)
        """
        if not self._pre_test_health or not self._post_test_health:
            self.logger.warning("⚠️  Postcondition 检查跳过:健康状态数据不完整")
            return True

        # 检查健康状态恶化
        pre_status = self._pre_test_health.get('status', 'OK')
        post_status = self._post_test_health.get('status', 'OK')

        if pre_status == 'OK' and post_status != 'OK':
            self.record_failure(
                "设备健康状态",
                "OK",
                post_status,
                f"测试后设备健康状态恶化"
            )

        # 检查坏块增加(需要具体的坏块计数逻辑)
        # 注意:当前 ufs_utils.py 的 get_health_status() 返回简化数据
        # 实际项目中需要从 SMART 或 UFS 描述符读取具体坏块数
        pre_warning = self._pre_test_health.get('critical_warning', 0)
        post_warning = self._post_test_health.get('critical_warning', 0)

        if post_warning > pre_warning:
            self.record_failure(
                "严重警告标志",
                f"{pre_warning}",
                f"{post_warning}",
                "设备出现新的严重警告"
            )

        # 检查预 EOL 状态变化
        pre_eol = self._pre_test_health.get('pre_eol_info', '0x00')
        post_eol = self._post_test_health.get('pre_eol_info', '0x00')

        if pre_eol == '0x00' and post_eol != '0x00':
            self.record_failure(
                "预寿命结束状态",
                "正常",
                f"EOL 警告: {post_eol}",
                "设备接近寿命终点"
            )

        self.logger.info("✅ Postcondition 检查完成")
        return True

    def teardown(self) -> bool:
        """测试后清理"""
        self.logger.debug(f"Teardown: {self.name}")

        # 自动清理测试文件
        if hasattr(self, "test_file") and self.test_file and isinstance(self.test_file, Path):
            if self.test_file.exists():
                try:
                    file_size = self.test_file.stat().st_size
                    self.test_file.unlink()
                    self.logger.debug(f"🧹 已清理测试文件：{self.test_file} ({file_size / 1024 / 1024:.1f} MB)")
                except Exception as e:
                    self.logger.warning(f"⚠️  清理测试文件失败：{e}")
                    # 尝试获取文件大小并提醒用户
                    if self.test_file.exists():
                        try:
                            file_size = self.test_file.stat().st_size
                            self.logger.warning(f"⚠️  测试文件未删除：{self.test_file} ({file_size / 1024 / 1024:.1f} MB)")
                            if file_size > 100 * 1024 * 1024:  # > 100MB
                                self.logger.warning(f"💡 文件较大，请手动删除以释放空间：rm {self.test_file}")
                            else:
                                self.logger.debug(f"💡 文件较小，可手动删除：rm {self.test_file}")
                        except Exception as stat_error:
                            self.logger.warning(f"⚠️  无法获取文件大小（可能已被删除或锁定）: {stat_error}")
                            self.logger.warning(f"💡 请检查文件状态：ls -lh {self.test_file}")

    def run(self) -> Dict[str, Any]:
        """完整执行流程"""
        self.start_time = datetime.now()
        self._failures = []  # 重置 failure 收集器
        self.logger.info(f"开始执行测试:{self.name}")

        # 注册信号处理,捕获中断
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
                self.logger.warning(f"前置条件不满足,跳过测试:{self.name}")
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

            # 框架层统一判断 PASS/FAIL
            # 规则:
            # 1. validate 返回 False → FAIL
            # 2. 有 Fail-Continue 记录 → FAIL
            # 3. 其他情况 → PASS
            should_fail = False
            fail_reasons = []
            
            if not passed:
                should_fail = True
                fail_reasons.append("验证未通过")
            
            if self.has_failures:
                should_fail = True
                fail_reasons.append(f"有 {len(self._failures)} 个 Fail-Continue 项")
            
            if should_fail:
                status = 'FAIL'
                self.logger.info(f"测试完成:{self.name} - ❌ FAIL ({duration:.2f}s)")
                self.logger.info(f"  失败原因：{', '.join(fail_reasons)}")
            else:
                status = 'PASS'
                self.logger.info(f"测试完成:{self.name} - ✅ PASS ({duration:.2f}s)")

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
                self.logger.info(f"  共 {len(self._failures)} 个失败项(Fail-Continue)")

            return run_result

        except FailStop as e:
            # Fail-Stop:立刻终止,状态为 FAIL
            self.end_time = datetime.now()
            duration = (self.end_time - self.start_time).total_seconds()
            self.logger.error(f"Fail-Stop 触发,测试终止:{self.name} - {e}")
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
            self.logger.warning(f"测试被中断:{self.name} ({duration:.2f}s)")
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
            self.logger.warning(f"测试被中断:{self.name} ({duration:.2f}s)")
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
            self.logger.error(f"测试超时:{self.name} ({duration:.2f}s)")
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

    def __init__(self, device: str = None, test_dir: str = None, verbose: bool = False, dry_run: bool = False,
                 ci_mode: bool = False, quick_factor: float = 1.0):
        self.device_override = device  # 用户手动指定
        self.test_dir_override = test_dir  # 用户手动指定
        self.verbose = verbose
        self.dry_run = dry_run
        self.ci_mode = ci_mode  # CI/CD 环境模式
        self.quick_factor = quick_factor  # 快速模式因子 (0.5 = 时间减半)
        self.suites_dir = Path(__file__).parent.parent / 'suites'
        self.config_dir = Path(__file__).parent.parent / 'config'
        self.test_dir = None  # 最终确定的测试目录
        self.device = None  # 最终确定的设备路径

        # === Dry-run 模式：使用临时参数验证框架 ===
        if self.dry_run:
            logger.info("🧪 [DRY-RUN] 使用临时参数验证框架")
            self.device = '/dev/null'  # 避免真实设备
            self.test_dir = Path('/tmp/systest_dryrun')
            self.test_dir.mkdir(parents=True, exist_ok=True)
            logger.info(f"  设备路径: {self.device} (临时)")
            logger.info(f"  测试目录: {self.test_dir} (临时)")
            # 跳过 CI 环境验证（dry-run 不需要真实配置）
            self.suites = self._load_suites()
            return

        # === 生产模式：使用真实参数 ===
        # 加载运行时配置
        self.runtime_config = self._load_runtime_config()

        # 每次运行都自动做一次环境检测，确保配置是最新的
        # 如果检测结果变化，自动更新 runtime.json
        from systest.bin.check_env import EnvironmentChecker
        checker = EnvironmentChecker(mode='deploy', verbose=False, config_dir=self.config_dir)
        checker.collect_storage()
        checker.collect_test_directory()
        
        # 更新 runtime_config 用最新检测结果
        if checker.runtime_config.get('device'):
            self.runtime_config['device'] = checker.runtime_config['device']
        if checker.runtime_config.get('test_dir'):
            self.runtime_config['test_dir'] = checker.runtime_config['test_dir']
        
        # 检测完成后自动保存更新配置
        try:
            config_path = self.config_dir / 'runtime.json'
            # 保留原有其他字段（system、toolchain 等），只更新设备和目录
            merged = {**self.runtime_config, **checker.runtime_config}
            merged['env_checked_at'] = checker.runtime_config.get('env_checked_at')
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(merged, f, indent=2, ensure_ascii=False)
            logger.info(f"✅ 配置已自动更新: {config_path} (最新环境检测结果)")
            self.runtime_config = merged
        except Exception as e:
            logger.warning(f"⚠️  自动保存配置失败: {e} (继续使用当前检测结果)")

        # 确定设备路径：用户指定 > 最新自动检测结果
        if self.device_override:
            self.device = self.device_override
            logger.info(f"✅ 设备路径: {self.device} (手动指定)")
        elif self.runtime_config.get('device'):
            self.device = self.runtime_config['device']
            logger.info(f"✅ 设备路径: {self.device} (自动检测)")
        else:
            self.device = '/dev/sda'
            logger.warning(f"⚠️  自动检测失败，使用默认值: {self.device} (开发板通用)")

        # 确定测试目录
        self._resolve_test_dir()

        # CI 环境验证（仅在 CI 模式下执行）
        if self.ci_mode:
            self._validate_ci_environment()

        # 加载测试套件
        self.suites = self._load_suites()

    def _load_runtime_config(self) -> Dict[str, Any]:
        """加载 runtime.json 配置文件"""
        config_path = self.config_dir / 'runtime.json'
        if config_path.exists():
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                checked_at = config.get('env_checked_at', '未知时间')
                logger.info(f"📄 已加载配置: {config_path} (环境检查时间: {checked_at})")
                return config
            except Exception as e:
                logger.warning(f"⚠️  配置文件读取失败: {e}")
                return {}
        else:
            logger.info(f"ℹ️  配置文件不存在: {config_path} (建议运行 check-env --save-config)")
            return {}

    def _resolve_test_dir(self):
        """确定测试目录：用户指定 > 自动检测 > 回退默认"""
        # 允许的测试目录前缀（安全白名单）
        allowed_prefixes = ['/tmp', '/mapdata']
        
        # 1) 用户手动指定（最高优先级）
        if self.test_dir_override:
            test_dir = Path(self.test_dir_override).absolute()
            # 验证路径是否在允许的目录内
            if not any(str(test_dir).startswith(p) for p in allowed_prefixes):
                logger.error(f"❌ 测试目录不在允许的范围内：{test_dir}")
                logger.error(f"💡 允许的目录前缀：{allowed_prefixes}")
                raise RuntimeError(f"测试目录必须在以下目录之一：{allowed_prefixes}")
            self.test_dir = test_dir
            self.test_dir.mkdir(parents=True, exist_ok=True)
            logger.info(f"✅ 测试目录：{self.test_dir} (手动指定)")
            return

        # 2) 从自动检测结果读取
        if self.runtime_config.get("test_dir"):
            self.test_dir = Path(self.runtime_config["test_dir"]).absolute()
            self.test_dir.mkdir(parents=True, exist_ok=True)
            logger.info(f"✅ 测试目录：{self.test_dir} (自动检测)")
            return

        # 3) 回退策略（顺序尝试，确保至少一个成功）
        fallback_dirs = [
            Path('/mapdata/ufs_test').absolute(),
            Path('/tmp/ufs_test').absolute(),
        ]
        for fallback in fallback_dirs:
            try:
                fallback.mkdir(parents=True, exist_ok=True)
                self.test_dir = fallback
                logger.warning(f"⚠️  回退到默认目录：{self.test_dir}")
                return
            except Exception:
                continue
        
        # 所有回退都失败（极罕见）
        try:
            self.test_dir = Path('/tmp/ufs_test').absolute()
            self.test_dir.mkdir(parents=True, exist_ok=True)
            logger.error(f"❌ 所有回退目录创建失败，强制使用：{self.test_dir}")
        except Exception as e:
            logger.critical(f"❌ 测试目录创建完全失败：{e}")
            logger.critical(f"💡 可能原因：磁盘空间已满、/tmp 目录不可写、或权限不足")
            logger.critical(f"💡 请检查：df -h /tmp && ls -ld /tmp")
            raise RuntimeError(f"无法创建任何测试目录：{e}")
        
        # 检查可用空间
        try:
            import shutil
            stat = shutil.disk_usage(self.test_dir)
            free_gb = stat.free / (1024 ** 3)
            if free_gb < 2:
                logger.warning(f"⚠️  测试目录可用空间不足：{free_gb:.1f} GB (推荐≥2GB)")
                logger.warning(f"💡 请清理空间或指定 --test-dir 到其他目录")
                logger.warning(f"💡 查看磁盘使用：df -h {self.test_dir}")
            else:
                logger.debug(f"✅ 测试目录可用空间：{free_gb:.1f} GB")
        except Exception as e:
            logger.warning(f"⚠️  无法检查磁盘空间：{e}")
    def _validate_ci_environment(self):
        """CI/CD 环境验证 - 检测常见低级配置错误

        检查项:
        1. 测试目录是否回退到 /tmp (CI 应手动指定)
        2. 设备路径是否为默认值 (CI 应手动指定 --device 或运行 check-env --save-config)
        3. runtime.json 是否存在 (CI 应有配置文件)

        Returns:
            bool: True = 环境合规, False = 存在问题
        """
        errors = []
        warnings = []

        # 1. 检查测试目录回退
        if self.test_dir == Path('/tmp/ufs_test').absolute():
            errors.append("测试目录回退到 /tmp (CI 环境应手动指定 --test-dir)")

        # 2. 检查设备路径是否为默认值
        if self.device == '/dev/sda' and not self.device_override and not self.runtime_config.get('device'): 
            errors.append("设备路径为默认值 /dev/sda (CI 环境应手动指定 --device 或运行 check-env --save-config)")

        # 3. 检查 runtime.json 是否存在
        config_path = self.config_dir / 'runtime.json'
        if not config_path.exists():
            warnings.append("runtime.json 配置文件不存在 (建议运行 check-env --save-config)")

        # 输出结果
        if errors:
            logger.error("=" * 60)
            logger.error("CI 环境验证失败")
            logger.error("=" * 60)
            for i, err in enumerate(errors, 1):
                logger.error(f"  {i}. {err}")
            logger.error("")
            logger.error("建议修复方案:")
            logger.error("  1. 在 GitHub Actions 中添加 check-env --save-config 步骤")
            logger.error("  2. 或手动指定参数: --test-dir=/path --device=/dev/xxx")
            logger.error("=" * 60)

            # CI 模式下抛异常（阻止继续执行）
            raise RuntimeError("CI 环境验证失败，请检查上述错误并修复")

        if warnings:
            logger.warning("=" * 60)
            logger.warning("CI 环境验证警告")
            logger.warning("=" * 60)
            for i, warn in enumerate(warnings, 1):
                logger.warning(f"  {i}. {warn}")
            logger.warning("=" * 60)

        if not errors and not warnings:
            logger.info("✅ CI 环境验证通过")

        return len(errors) == 0

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
        """加载可用测试套件"""
        suites = {}

        if not self.suites_dir.exists():
            logger.warning(f"测试套件目录不存在:{self.suites_dir}")
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
            raise ValueError(f"未知测试套件:{suite_name}")

        logger.info(f"执行测试套件:{suite_name}")

        results = []
        tests = self.suites[suite_name]
        stopped = False

        for i, test_name in enumerate(tests, 1):
            # 如果之前有 Fail-Stop,后续 case 全部 SKIP
            if stopped:
                logger.warning(f"[{i}/{len(tests)}] 跳过测试(前序 Fail-Stop):{test_name}")
                results.append({
                    'name': test_name,
                    'status': 'SKIP',
                    'reason': 'Skipped due to previous Fail-Stop',
                    'duration': 0
                })
                continue

            logger.info(f"[{i}/{len(tests)}] 执行测试:{test_name}")

            if self.dry_run:
                # Dry-run 模式：验证测试用例能正确导入和解析参数
                try:
                    import sys
                    suites_dir = Path(__file__).parent.parent / 'suites'
                    if str(suites_dir) not in sys.path:
                        sys.path.insert(0, str(suites_dir))

                    # 导入测试模块（验证文件存在）
                    if test_name.startswith('t_'):
                        module_path = suites_dir / suite_name / f'{test_name}.py'
                    else:
                        module_path = suites_dir / suite_name / f'test_{test_name}.py'

                    if not module_path.exists():
                        logger.error(f"  ❌ 测试文件不存在: {module_path}")
                        results.append({
                            'name': test_name,
                            'status': 'ERROR',
                            'reason': f'Test file not found: {module_path}',
                            'duration': 0
                        })
                        continue

                    # 动态导入（验证语法正确）
                    import importlib.util
                    spec = importlib.util.spec_from_file_location(f'{suite_name}.{test_name}', module_path)
                    module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(module)

                    # 验证 TestCase 类存在
                    if 'TestCase' not in dir(module):
                        logger.error(f"  ❌ TestCase 类不存在: {test_name}")
                        results.append({
                            'name': test_name,
                            'status': 'ERROR',
                            'reason': 'TestCase class not found',
                            'duration': 0
                        })
                        continue

                    # 创建实例（验证参数解析）
                    test_instance = module.TestCase(device=self.device, test_dir=self.test_dir)
                    logger.info(f"  ✅ [DRY-RUN] 测试用例验证通过: {test_instance.__class__.__name__}")
                    results.append({
                        'name': test_name,
                        'status': 'DRY-RUN-PASS',
                        'class': test_instance.__class__.__name__,
                        'duration': 0
                    })
                except SyntaxError as e:
                    logger.error(f"  ❌ [DRY-RUN] 语法错误: {e}")
                    results.append({
                        'name': test_name,
                        'status': 'ERROR',
                        'reason': f'Syntax error: {e}',
                        'duration': 0
                    })
                except Exception as e:
                    logger.error(f"  ❌ [DRY-RUN] 导入失败: {e}")
                    results.append({
                        'name': test_name,
                        'status': 'ERROR',
                        'reason': f'Import error: {e}',
                        'duration': 0
                    })
                continue

            # 动态导入测试用例
            try:
                import sys
                suites_dir = Path(__file__).parent.parent / 'suites'
                if str(suites_dir) not in sys.path:
                    sys.path.insert(0, str(suites_dir))

                # 导入测试模块(支持 test_*.py 和 t_*_*.py)
                if test_name.startswith('t_'):
                    module_path = suites_dir / suite_name / f'{test_name}.py'
                else:
                    module_path = suites_dir / suite_name / f'test_{test_name}.py'
                import importlib.util
                spec = importlib.util.spec_from_file_location(f'{suite_name}.{test_name}', module_path)
                module = importlib.util.module_from_spec(spec)
                sys.modules[f'{suite_name}.{test_name}'] = module
                spec.loader.exec_module(module)
                # 查找测试类(优先 Test,其次驼峰命名)
                test_class = getattr(module, 'Test', None)
                if not test_class:
                    class_name = ''.join(part.capitalize() for part in test_name.split('_'))
                    test_class = getattr(module, class_name, None)
                if not test_class:
                    raise ImportError(f"未找到测试类(Test 或 {class_name})")
                test_instance = test_class(
                    device=self.device,
                    test_dir=self.test_dir,
                    verbose=self.verbose,
                    logger=logger
                )
                
                # 快速模式：调整 runtime 参数
                if self.quick_factor != 1.0 and hasattr(test_instance, 'runtime'):
                    test_instance.runtime = int(test_instance.runtime * self.quick_factor)
                    test_instance.logger.info(f"⚡ 快速模式：runtime 调整为 {test_instance.runtime}s")

                result = test_instance.run()
                results.append(result)

                # 检查是否 Fail-Stop
                if result.get('fail_mode') == 'stop':
                    logger.error(f"  🛑 Fail-Stop 触发,后续测试将被跳过")
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

        # 套件执行总结
        total = len(results)
        passed = sum(1 for r in results if r['status'] == 'PASS' or r['status'] == 'DRY-RUN-PASS')
        failed = sum(1 for r in results if r['status'] == 'FAIL')
        errors = sum(1 for r in results if r['status'] == 'ERROR')
        skipped = sum(1 for r in results if r['status'] == 'SKIP')
        aborted = sum(1 for r in results if r['status'] == 'ABORT')
        
        logger.info("=" * 60)
        logger.info(f"📊 测试套件执行总结：{suite_name}")
        logger.info("=" * 60)
        logger.info(f"  总计：{total} 个测试用例")
        logger.info(f"  ✅ PASS:  {passed}")
        logger.info(f"  ❌ FAIL:  {failed}")
        logger.info(f"  💥 ERROR: {errors}")
        logger.info(f"  ⏭️  SKIP:  {skipped}")
        logger.info(f"  ⏹️  ABORT: {aborted}")
        logger.info("-" * 60)
        
        # 显示每个测试用例的执行时间
        logger.info("📋 测试用例执行时间:")
        for r in results:
            duration = r.get('duration', 0)
            status = r.get('status', 'UNKNOWN')
            name = r.get('name', 'unknown')
            logger.info(f"  {name}: {duration:.2f}s [{status}]")
        
        # 判断套件整体是否通过
        if failed > 0 or errors > 0:
            suite_status = '❌ FAIL'
            logger.info(f"📋 套件状态：{suite_status} ({failed + errors} 个测试失败)")
        elif passed > 0:
            suite_status = '✅ PASS'
            logger.info(f"📋 套件状态：{suite_status} (所有测试通过)")
        else:
            suite_status = '⚠️  SKIP'
            logger.info(f"📋 套件状态：{suite_status} (所有测试跳过)")
        
        logger.info("=" * 60)
        
        return results

    def run_test(self, test_name: str) -> Dict[str, Any]:
        """执行单个测试"""
        # 查找测试用例
        for suite_name, tests in self.suites.items():
            if test_name in tests:
                logger.info(f"执行测试:{test_name} (Suite: {suite_name})")
                results = self.run_suite(suite_name)
                for result in results:
                    if result['name'] == test_name:
                        return result

        raise ValueError(f"未知测试用例:{test_name}")
