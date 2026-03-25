"""
测试 reporter.py - 报告生成器
"""
import sys
import json
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.reporter import ReportGenerator


import unittest


class TestReporter(unittest.TestCase):
    def test_reporter_initialization(self):
        """测试报告生成器初始化"""
        reporter = ReportGenerator()
        assert reporter is not None


    def test_reporter_generate_json(self):
        """测试 JSON 报告生成"""
        reporter = ReportGenerator()
        report_data = {
            'test_id': 'test_report_001',
            'summary': {
                'total': 2,
                'passed': 1,
                'failed': 1,
                'pass_rate': 50.0,
            },
            'test_cases': [
                {'name': 'test_a', 'status': 'PASS', 'duration': 1.0},
                {'name': 'test_b', 'status': 'FAIL', 'duration': 2.0},
            ],
        }
        with tempfile.TemporaryDirectory() as tmpdir:
            report_path = reporter.generate(report_data, output_dir=tmpdir, formats=['json'])
            # 验证 JSON 文件存在
            json_files = list(Path(tmpdir).rglob('*.json'))
            assert len(json_files) > 0


    def test_reporter_generate_html(self):
        """测试 HTML 报告生成"""
        reporter = ReportGenerator()
        report_data = {
            'test_id': 'test_report_002',
            'timestamp': '2026-03-22T23:00:00',
            'duration': 60.0,
            'summary': {
                'total': 3,
                'passed': 3,
                'failed': 0,
                'pass_rate': 100.0,
            },
            'test_cases': [
                {'name': f'test_{i}', 'status': 'PASS', 'duration': 1.0, 'metrics': {}}
                for i in range(3)
            ],
        }
        with tempfile.TemporaryDirectory() as tmpdir:
            report_path = reporter.generate(report_data, output_dir=tmpdir, formats=['html'])
            html_files = list(Path(tmpdir).rglob('*.html'))
            assert len(html_files) > 0



if __name__ == "__main__":
    unittest.main()
