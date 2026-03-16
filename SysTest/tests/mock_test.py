#!/usr/bin/env python3
"""
模拟测试数据生成器
用于在没有硬件的情况下测试报告和失效分析功能
"""

import json
import sys
from pathlib import Path
from datetime import datetime

# 添加核心模块路径
core_dir = Path(__file__).parent.parent / 'core'
sys.path.insert(0, str(core_dir))

from collector import ResultCollector
from reporter import ReportGenerator
from analyzer import FailureAnalyzer


def generate_mock_results(pass_scenario=True):
    """生成模拟测试结果"""
    
    if pass_scenario:
        # 通过场景
        test_cases = [
            {
                'test_name': 'seq_read_burst',
                'status': 'PASS',
                'metrics': {
                    'bandwidth': 2150.5,
                    'iops': 0,
                    'latency_avg': 120.5,
                    'latency_stddev': 45.2,
                    'latency_p50': 100.0,
                    'latency_p99': 250.0,
                    'latency_p99999': 500.0
                },
                'duration': 60.5
            },
            {
                'test_name': 'seq_write_burst',
                'status': 'PASS',
                'metrics': {
                    'bandwidth': 1680.3,
                    'iops': 0,
                    'latency_avg': 150.2,
                    'latency_stddev': 55.8,
                    'latency_p50': 130.0,
                    'latency_p99': 300.0,
                    'latency_p99999': 600.0
                },
                'duration': 60.3
            },
            {
                'test_name': 'rand_read_burst',
                'status': 'PASS',
                'metrics': {
                    'bandwidth': 0,
                    'iops': 205.8,
                    'latency_avg': 85.3,
                    'latency_stddev': 35.6,
                    'latency_p50': 70.0,
                    'latency_p99': 180.0,
                    'latency_p99999': 350.0
                },
                'duration': 60.2
            },
            {
                'test_name': 'rand_write_burst',
                'status': 'PASS',
                'metrics': {
                    'bandwidth': 0,
                    'iops': 340.2,
                    'latency_avg': 95.8,
                    'latency_stddev': 42.3,
                    'latency_p50': 80.0,
                    'latency_p99': 200.0,
                    'latency_p99999': 400.0
                },
                'duration': 60.1
            }
        ]
    else:
        # 失败场景 - SLC Cache 耗尽
        test_cases = [
            {
                'test_name': 'seq_read_burst',
                'status': 'PASS',
                'metrics': {
                    'bandwidth': 2150.5,
                    'iops': 0,
                    'latency_avg': 120.5,
                    'latency_stddev': 45.2,
                    'latency_p50': 100.0,
                    'latency_p99': 250.0,
                    'latency_p99999': 500.0
                },
                'duration': 60.5
            },
            {
                'test_name': 'seq_write_burst',
                'status': 'PASS',
                'metrics': {
                    'bandwidth': 1680.3,
                    'iops': 0,
                    'latency_avg': 150.2,
                    'latency_stddev': 55.8,
                    'latency_p50': 130.0,
                    'latency_p99': 300.0,
                    'latency_p99999': 600.0
                },
                'duration': 60.3
            },
            {
                'test_name': 'seq_write_sustained',
                'status': 'FAIL',
                'metrics': {
                    'bandwidth': 180.5,  # 远低于目标 250
                    'iops': 0,
                    'latency_avg': 850.6,
                    'latency_stddev': 650.3,
                    'latency_p50': 200.0,
                    'latency_p99': 1500.0,
                    'latency_p99999': 3500.0
                },
                'duration': 300.8
            },
            {
                'test_name': 'rand_write_burst',
                'status': 'PASS',
                'metrics': {
                    'bandwidth': 0,
                    'iops': 340.2,
                    'latency_avg': 95.8,
                    'latency_stddev': 42.3,
                    'latency_p50': 80.0,
                    'latency_p99': 200.0,
                    'latency_p99999': 400.0
                },
                'duration': 60.1
            }
        ]
    
    test_results = {
        'test_id': datetime.now().strftime('%Y%m%d_%H%M%S'),
        'suite': 'performance',
        'timestamp': datetime.now().isoformat(),
        'device': '/dev/ufs0',
        'test_cases': test_cases,
        'summary': {
            'total': len(test_cases),
            'passed': sum(1 for tc in test_cases if tc['status'] == 'PASS'),
            'failed': sum(1 for tc in test_cases if tc['status'] == 'FAIL'),
            'errors': 0,
            'pass_rate': sum(1 for tc in test_cases if tc['status'] == 'PASS') / len(test_cases) * 100
        }
    }
    
    return {
        'test_id': test_results['test_id'],
        'suite': 'performance',
        'timestamp': datetime.now().isoformat(),
        'device': '/dev/ufs0',
        'test_results': test_results,
        'system_info': {
            'hostname': 'ufs-test-board',
            'kernel': '5.15.120-byteatom-ck.13',
            'cpu_count': 8,
            'memory_total': 8192,
            'python_version': '3.11.2'
        },
        'device_info': {
            'device_path': '/dev/ufs0',
            'model': 'UFS 3.1 128GB',
            'serial': 'UFS2026031601',
            'size': 128.0,
            'firmware': '1.0.0'
        },
        'config': {
            'targets': {
                'seq_read_burst': 2100,
                'seq_read_sustained': 1800,
                'seq_write_burst': 1650,
                'seq_write_sustained': 250,
                'rand_read_burst': 200,
                'rand_read_sustained': 105,
                'rand_write_burst': 330,
                'rand_write_sustained': 60
            }
        }
    }


def main():
    print("🧪 SysTest 模拟测试")
    print("=" * 60)
    
    # 测试 1: 通过场景
    print("\n📊 测试 1: 通过场景")
    print("-" * 60)
    
    results_pass = generate_mock_results(pass_scenario=True)
    test_id_pass = results_pass['test_id']
    
    # 生成报告
    reporter = ReportGenerator(output_dir='./results/mock', formats=['html', 'json', 'text'])
    report_file = reporter.generate(results_pass, test_id_pass)
    print(f"✅ 报告生成：{report_file}")
    
    # 失效分析
    analyzer = FailureAnalyzer()
    analysis = analyzer.analyze(results_pass)
    print(f"📝 分析结果：{analysis['summary']}")
    
    # 测试 2: 失败场景
    print("\n📊 测试 2: 失败场景 (SLC Cache 耗尽)")
    print("-" * 60)
    
    results_fail = generate_mock_results(pass_scenario=False)
    test_id_fail = results_fail['test_id']
    
    # 生成报告
    reporter = ReportGenerator(output_dir='./results/mock', formats=['html', 'json', 'text'])
    report_file = reporter.generate(results_fail, test_id_fail)
    print(f"✅ 报告生成：{report_file}")
    
    # 失效分析
    analyzer = FailureAnalyzer()
    analysis = analyzer.analyze(results_fail)
    print(f"📝 分析结果：{analysis['summary']}")
    
    if analysis['root_causes']:
        print("\n🔍 根因分析:")
        for i, cause in enumerate(analysis['root_causes'], 1):
            confidence = cause.get('confidence', 0) * 100
            print(f"  {i}. {cause['name']} (置信度：{confidence:.0f}%)")
            print(f"     证据数：{cause.get('evidence_count', 0)}")
            if cause.get('suggestions'):
                print(f"     建议：{cause['suggestions'][0]}")
    
    print("\n" + "=" * 60)
    print("✅ 模拟测试完成!")
    print(f"📁 报告位置：./results/mock/")


if __name__ == '__main__':
    main()
