"""
测试 runner.py - TestCase 基类和 TestRunner 执行引擎的深度测试
"""
import sys
import logging
from pathlib import Path
from unittest.mock import MagicMock

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.runner import TestRunner, TestCase


# --- TestCase 基类测试 ---

class DummyPassTest(TestCase):
    """模拟通过的测试"""
    name = "dummy_pass"
    description = "always passes"
    
    def execute(self):
        return {'bandwidth': {'value': 2500, 'unit': 'MB/s'}}
    
    def validate(self, result):
        return True


class DummyFailTest(TestCase):
    """模拟失败的测试"""
    name = "dummy_fail"
    description = "always fails"
    
    def execute(self):
        return {'bandwidth': {'value': 500, 'unit': 'MB/s'}}
    
    def validate(self, result):
        return False


class DummyCrashTest(TestCase):
    """模拟崩溃的测试"""
    name = "dummy_crash"
    description = "always crashes"
    
    def execute(self):
        raise RuntimeError("device exploded")
    
    def validate(self, result):
        return False


class DummySetupFailTest(TestCase):
    """模拟 setup 失败的测试"""
    name = "dummy_setup_fail"
    description = "setup fails"
    
    def setup(self):
        return False
    
    def execute(self):
        return {}
    
    def validate(self, result):
        return True


def test_testcase_pass():
    """测试用例通过"""
    tc = DummyPassTest()
    result = tc.run()
    assert result['status'] == 'PASS'
    assert result['name'] == 'dummy_pass'
    assert 'duration' in result
    assert result['duration'] >= 0


def test_testcase_fail():
    """测试用例失败"""
    tc = DummyFailTest()
    result = tc.run()
    assert result['status'] == 'FAIL'


def test_testcase_crash():
    """测试用例崩溃"""
    tc = DummyCrashTest()
    result = tc.run()
    assert result['status'] == 'ERROR'
    assert 'error' in result
    assert 'exploded' in result['error']


def test_testcase_setup_fail():
    """测试 setup 失败 → SKIP（前置条件不满足）"""
    tc = DummySetupFailTest()
    result = tc.run()
    assert result['status'] == 'SKIP'
    assert 'precondition' in result.get('reason', '').lower() or 'setup' in result.get('reason', '').lower()


def test_testcase_with_device():
    """测试带设备路径"""
    tc = DummyPassTest(device="/dev/ufs0")
    assert tc.device == "/dev/ufs0"


def test_testcase_with_verbose():
    """测试 verbose 模式"""
    tc = DummyPassTest(verbose=True)
    assert tc.verbose == True


def test_testcase_with_logger():
    """测试自定义 logger"""
    logger = MagicMock()
    tc = DummyPassTest(logger=logger)
    tc.run()
    assert logger.info.called or logger.debug.called


def test_testcase_teardown_called():
    """测试 teardown 被调用"""
    tc = DummyPassTest()
    tc.teardown = MagicMock(return_value=True)
    tc.run()
    tc.teardown.assert_called()


def test_testcase_result_has_timestamp():
    """测试结果包含时间戳"""
    tc = DummyPassTest()
    result = tc.run()
    assert 'timestamp' in result


def test_testcase_result_has_metrics():
    """测试结果包含指标"""
    tc = DummyPassTest()
    result = tc.run()
    assert 'metrics' in result
    assert 'bandwidth' in result['metrics']


# --- TestRunner 测试 ---

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


def test_runner_performance_test_names():
    """测试性能用例具体名称"""
    runner = TestRunner(dry_run=True)
    suites = runner.list_suites()
    perf = suites['performance']
    expected = {'t_perf_SeqReadBurst_001', 't_perf_SeqWriteBurst_003', 
                't_perf_RandReadBurst_005', 't_perf_RandWriteBurst_007', 
                't_perf_MixedRw_009'}
    assert set(perf) == expected
