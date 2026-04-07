"""
测试 runner.py - TestCase 基类和 TestRunner 执行引擎的深度测试
"""
import sys
import logging
from pathlib import Path
from unittest.mock import MagicMock

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.runner import TestRunner, TestCase, FailStop


# --- TestCase 基类测试 ---

import unittest


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



class DummyFailContinueTest(TestCase):
    """模拟 Fail-Continue：多项校验，部分失败，继续跑完"""
    name = "dummy_fail_continue"

    def execute(self):
        results = {}

        # 第一项校验：失败
        results['check_a'] = 'bad_value'
        self.record_failure('Check A', expected='good_value', actual='bad_value')

        # 第二项校验：通过（继续执行到这里）
        results['check_b'] = 'ok'

        # 第三项校验：也失败
        results['check_c'] = 'wrong'
        self.record_failure('Check C', expected='right', actual='wrong', reason='数据不一致')

        return results

    def validate(self, result):
        # 返回 True，让框架根据 has_failures 自动判定 FAIL
        return True



class DummyFailStopTest(TestCase):
    """模拟 Fail-Stop：遇到严重问题立刻终止"""
    name = "dummy_fail_stop"

    def execute(self):
        result = {}
        result['step_1'] = 'done'

        # 严重问题，立刻停
        raise FailStop("设备返回 IO error")

        # 这行不会执行
        result['step_2'] = 'done'  # noqa: E501
        return result

    def validate(self, result):
        return True



class DummyPerfTest(TestCase):
    """模拟性能测试：validate 永远返回 True，指标走 annotations"""
    name = "dummy_perf"

    def execute(self):
        return {
            'bandwidth': {'value': 1800, 'unit': 'MB/s'},
            'iops': {'value': 14000, 'unit': 'IOPS'},
        }

    def validate(self, result):
        annotations = []

        bw = result['bandwidth']['value']
        annotations.append({
            'metric': '带宽',
            'actual': f'{bw} MB/s',
            'target': '>= 2100 MB/s',
            'met': bw >= 2100,
        })

        iops = result['iops']['value']
        annotations.append({
            'metric': 'IOPS',
            'actual': f'{iops}',
            'target': '>= 15000',
            'met': iops >= 15000,
        })

        result['annotations'] = annotations
        # 性能测试：永远返回 True
        return True




class TestRunnerUnit(unittest.TestCase):
    def test_testcase_pass(self):
        """测试用例通过"""
        tc = DummyPassTest()
        result = tc.run()
        assert result['status'] == 'PASS'
        assert result['name'] == 'dummy_pass'
        assert 'duration' in result
        assert result['duration'] >= 0


    def test_testcase_fail(self):
        """测试用例失败"""
        tc = DummyFailTest()
        result = tc.run()
        assert result['status'] == 'FAIL'


    def test_testcase_crash(self):
        """测试用例崩溃"""
        tc = DummyCrashTest()
        result = tc.run()
        assert result['status'] == 'ERROR'
        assert 'error' in result
        assert 'exploded' in result['error']


    def test_testcase_setup_fail(self):
        """测试 setup 失败 → SKIP（前置条件不满足）"""
        tc = DummySetupFailTest()
        result = tc.run()
        assert result['status'] == 'SKIP'
        assert 'precondition' in result.get('reason', '').lower() or 'setup' in result.get('reason', '').lower()


    def test_testcase_with_device(self):
        """测试带设备路径"""
        tc = DummyPassTest(device="/dev/ufs0")
        assert tc.device == "/dev/ufs0"


    def test_testcase_with_verbose(self):
        """测试 verbose 模式"""
        tc = DummyPassTest(verbose=True)
        assert tc.verbose == True


    def test_testcase_with_logger(self):
        """测试自定义 logger"""
        logger = MagicMock()
        tc = DummyPassTest(logger=logger)
        tc.run()
        assert logger.info.called or logger.debug.called


    def test_testcase_teardown_called(self):
        """测试 teardown 被调用"""
        tc = DummyPassTest()
        tc.teardown = MagicMock(return_value=True)
        tc.run()
        tc.teardown.assert_called()


    def test_testcase_result_has_timestamp(self):
        """测试结果包含时间戳"""
        tc = DummyPassTest()
        result = tc.run()
        assert 'timestamp' in result


    def test_testcase_result_has_metrics(self):
        """测试结果包含指标"""
        tc = DummyPassTest()
        result = tc.run()
        assert 'metrics' in result
        assert 'bandwidth' in result['metrics']


    # --- TestRunner 测试 ---

    def test_runner_dry_run(self):
        """测试 dry-run 模式"""
        runner = TestRunner(dry_run=True)
        assert runner is not None


    def test_runner_list_suites(self):
        """测试列出测试套件"""
        runner = TestRunner(dry_run=True)
        suites = runner.list_suites()
        assert isinstance(suites, dict)
        assert 'performance' in suites


    def test_runner_performance_suite_count(self):
        """测试性能套件用例数"""
        runner = TestRunner(dry_run=True)
        suites = runner.list_suites()
        assert len(suites['performance']) == 5


    def test_runner_qos_suite_exists(self):
        """测试 QoS 套件存在"""
        runner = TestRunner(dry_run=True)
        suites = runner.list_suites()
        assert 'qos' in suites


    def test_runner_suite_names(self):
        """测试用例命名规范"""
        runner = TestRunner(dry_run=True)
        suites = runner.list_suites()
        for name in suites['performance']:
            assert name.startswith('t_perf_'), f"命名不规范: {name}"


    def test_runner_performance_test_names(self):
        """测试性能用例具体名称"""
        runner = TestRunner(dry_run=True)
        suites = runner.list_suites()
        perf = suites['performance']
        expected = {'t_perf_SeqReadBurst_001', 't_perf_SeqWriteBurst_002', 
                    't_perf_RandReadBurst_003', 't_perf_RandWriteBurst_004', 
                    't_perf_MixedRw_005'}
        assert set(perf) == expected


    # --- Fail-Continue 测试 ---

    def test_fail_continue_records_failures(self):
        """Fail-Continue：记录失败但继续执行，最终 FAIL"""
        tc = DummyFailContinueTest()
        result = tc.run()

        assert result['status'] == 'FAIL'
        assert 'failures' in result
        assert len(result['failures']) == 2
        assert result['failures'][0]['check'] == 'Check A'
        assert result['failures'][1]['check'] == 'Check C'
        assert result['failures'][1]['reason'] == '数据不一致'


    def test_fail_continue_executes_all_steps(self):
        """Fail-Continue：即使有失败，后续步骤也执行了"""
        tc = DummyFailContinueTest()
        result = tc.run()

        # check_b 在 check_a 失败之后，应该也执行到了
        assert result['metrics']['check_b'] == 'ok'
        assert result['metrics']['check_c'] == 'wrong'


    # --- Fail-Stop 测试 ---

    def test_fail_stop_terminates_case(self):
        """Fail-Stop：立刻终止，状态为 FAIL"""
        tc = DummyFailStopTest()
        result = tc.run()

        assert result['status'] == 'FAIL'
        assert result['fail_mode'] == 'stop'
        assert 'IO error' in result['reason']


    # --- 性能测试 annotations 测试 ---

    def test_perf_validate_always_pass(self):
        """性能测试：即使指标未达标，状态仍为 PASS"""
        tc = DummyPerfTest()
        result = tc.run()

        assert result['status'] == 'PASS'
        assert 'annotations' in result['metrics']

        annotations = result['metrics']['annotations']
        assert len(annotations) == 2

        # 带宽未达标（1800 < 2100）
        assert annotations[0]['met'] == False
        # IOPS 未达标（14000 < 15000）
        assert annotations[1]['met'] == False


    def test_perf_annotations_structure(self):
        """性能测试：annotations 结构完整"""
        tc = DummyPerfTest()
        result = tc.run()

        for ann in result['metrics']['annotations']:
            assert 'metric' in ann
            assert 'actual' in ann
            assert 'target' in ann
            assert 'met' in ann
            assert isinstance(ann['met'], bool)


    # --- record_failure 不影响无 failure 的 case ---

    def test_no_failures_means_pass(self):
        """没有 record_failure 且 validate 返回 True → PASS"""
        tc = DummyPassTest()
        result = tc.run()
        assert result['status'] == 'PASS'
        assert 'failures' not in result



if __name__ == "__main__":
    unittest.main()
