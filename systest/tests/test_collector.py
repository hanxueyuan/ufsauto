"""
测试 collector.py - 结果收集器
"""
import sys
import json
import tempfile
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.collector import ResultCollector


def test_collector_initialization():
    """测试收集器初始化"""
    with tempfile.TemporaryDirectory() as tmpdir:
        collector = ResultCollector(output_dir=tmpdir)
        assert collector is not None


def test_collector_collect_empty():
    """测试收集空结果"""
    with tempfile.TemporaryDirectory() as tmpdir:
        collector = ResultCollector(output_dir=tmpdir)
        results = []
        report = collector.collect(results, test_id="test_001")
        assert 'summary' in report
        assert report['summary']['total'] == 0
        assert report['summary']['passed'] == 0


def test_collector_collect_with_results():
    """测试收集有数据的结果"""
    with tempfile.TemporaryDirectory() as tmpdir:
        collector = ResultCollector(output_dir=tmpdir)
        results = [
            {
                'name': 'test_seq_read',
                'status': 'PASS',
                'duration': 60.0,
                'metrics': {'bandwidth': {'value': 2200, 'unit': 'MB/s'}},
            },
            {
                'name': 'test_seq_write',
                'status': 'FAIL',
                'duration': 60.0,
                'metrics': {'bandwidth': {'value': 1500, 'unit': 'MB/s'}},
            },
        ]
        report = collector.collect(results, test_id="test_002")
        assert report['summary']['total'] == 2
        assert report['summary']['passed'] == 1
        assert report['summary']['failed'] == 1


def test_collector_pass_rate():
    """测试通过率计算"""
    with tempfile.TemporaryDirectory() as tmpdir:
        collector = ResultCollector(output_dir=tmpdir)
        results = [
            {'name': f'test_{i}', 'status': 'PASS' if i < 3 else 'FAIL', 'duration': 1.0, 'metrics': {}}
            for i in range(4)
        ]
        report = collector.collect(results, test_id="test_003")
        assert report['summary']['pass_rate'] == 75.0
