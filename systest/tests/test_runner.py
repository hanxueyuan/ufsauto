"""
测试 runner.py - 测试执行引擎
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.runner import TestRunner, TestCase


def test_runner_dry_run():
    """测试 dry-run 模式"""
    runner = TestRunner(dry_run=True)
    assert runner is not None


def test_runner_list_suites():
    """测试列出测试套件"""
    runner = TestRunner(dry_run=True)
    suites = runner.list_suites()
    assert isinstance(suites, dict)
    assert 'performance' in suites


def test_runner_performance_suite_count():
    """测试性能套件用例数"""
    runner = TestRunner(dry_run=True)
    suites = runner.list_suites()
    assert len(suites['performance']) == 5


def test_runner_qos_suite_exists():
    """测试 QoS 套件存在"""
    runner = TestRunner(dry_run=True)
    suites = runner.list_suites()
    assert 'qos' in suites


def test_runner_suite_names():
    """测试用例命名规范"""
    runner = TestRunner(dry_run=True)
    suites = runner.list_suites()
    for name in suites['performance']:
        assert name.startswith('t_perf_'), f"命名不规范: {name}"
    for name in suites.get('qos', []):
        assert name.startswith('t_qos_'), f"命名不规范: {name}"


def test_testcase_base_class():
    """测试 TestCase 基类"""
    assert hasattr(TestCase, 'setup')
    assert hasattr(TestCase, 'run')
    assert hasattr(TestCase, 'validate')
    assert hasattr(TestCase, 'teardown')
