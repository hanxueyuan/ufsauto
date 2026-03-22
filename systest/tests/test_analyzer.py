"""
测试 analyzer.py - 失效分析引擎
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.analyzer import FailureAnalyzer


def test_analyzer_initialization():
    """测试分析器初始化"""
    analyzer = FailureAnalyzer()
    assert analyzer is not None


def test_analyzer_no_failure():
    """测试无失效的情况"""
    analyzer = FailureAnalyzer()
    result = {
        'name': 'test_seq_read',
        'status': 'PASS',
        'metrics': {'bandwidth': {'value': 2200, 'unit': 'MB/s'}},
    }
    analysis = analyzer.analyze(result)
    assert analysis is not None


def test_analyzer_low_bandwidth():
    """测试低带宽失效分析"""
    analyzer = FailureAnalyzer()
    result = {
        'name': 'test_seq_read',
        'status': 'FAIL',
        'metrics': {'bandwidth': {'value': 500, 'unit': 'MB/s'}},
        'target': {'bandwidth': 2100},
    }
    analysis = analyzer.analyze(result)
    assert analysis is not None


def test_analyzer_crash():
    """测试崩溃失效分析"""
    analyzer = FailureAnalyzer()
    result = {
        'name': 'test_crash',
        'status': 'ERROR',
        'error': 'Device not found',
        'metrics': {},
    }
    analysis = analyzer.analyze(result)
    assert analysis is not None
