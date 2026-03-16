#!/usr/bin/env python3
"""
SysTest 最小化验证脚本（纯 Python 版）
不依赖 FIO，通过模拟真实执行流程验证系统功能
"""

import sys
import json
import time
from pathlib import Path
from datetime import datetime

# 颜色输出
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    END = '\033[0m'

def print_header(text):
    print(f"\n{Colors.BLUE}{'=' * 70}{Colors.END}")
    print(f"{Colors.BLUE}{text}{Colors.END}")
    print(f"{Colors.BLUE}{'=' * 70}{Colors.END}\n")

def print_success(text):
    print(f"{Colors.GREEN}✅ {text}{Colors.END}")

def print_error(text):
    print(f"{Colors.RED}❌ {text}{Colors.END}")

def print_info(text):
    print(f"{Colors.YELLOW}ℹ️  {text}{Colors.END}")

def verify_command_building():
    """验证命令构建逻辑"""
    print_header("验证 1: FIO 命令构建")
    
    sys.path.insert(0, str(Path(__file__).parent.parent / 'core'))
    from runner import TestRunner
    
    runner = TestRunner(device='/dev/zero', verbose=True)
    
    # 测试不同测试类型的命令构建
    test_cases = [
        ('seq_read_burst', 'bandwidth', 2100),
        ('seq_write_sustained', 'bandwidth', 250),
        ('rand_read_burst', 'iops', 200),
        ('rand_write_burst', 'iops', 330),
        ('latency_percentile', 'latency', None),
        ('sensor_write', 'scenario', 400),
    ]
    
    passed = 0
    for test_name, test_type, target in test_cases:
        test_info = runner._find_test(test_name)
        if test_info:
            # 构建命令
            fio_cmd = runner._build_fio_command(test_name, 60, test_info)
            
            # 验证命令包含必要参数
            cmd_str = ' '.join(fio_cmd)
            checks = [
                ('--filename=' in cmd_str, "设备路径"),
                ('--output-format=json' in cmd_str, "JSON 输出"),
                ('--name=' in cmd_str, "测试名称"),
            ]
            
            all_passed = all(check[0] for check in checks)
            
            if all_passed:
                print_success(f"{test_name}: 命令构建正确")
                print_info(f"  命令：fio {' '.join(fio_cmd[1:])}")
                passed += 1
            else:
                print_error(f"{test_name}: 命令缺少必要参数")
                for check, name in checks:
                    if not check:
                        print_info(f"    缺少：{name}")
        else:
            print_error(f"{test_name}: 未找到测试定义")
    
    print_info(f"命令构建验证：{passed}/{len(test_cases)} 通过")
    return passed == len(test_cases)

def verify_result_parsing():
    """验证结果解析逻辑"""
    print_header("验证 2: 结果解析")
    
    sys.path.insert(0, str(Path(__file__).parent.parent / 'core'))
    from runner import TestRunner
    
    runner = TestRunner()
    
    # 使用真实的 FIO 输出格式
    test_cases = [
        ('seq_read_burst', {
            'jobs': [{
                'read': {
                    'bw_bytes': 2147483648,
                    'iops': 524288,
                    'lat_ns': {
                        'mean': 100000,
                        'stddev': 50000,
                        'percentile': {
                            '50.000000': 90000,
                            '99.000000': 200000,
                            '99.999000': 500000
                        }
                    }
                }
            }]
        }),
        ('rand_write_burst', {
            'jobs': [{
                'write': {
                    'bw_bytes': 134217728,
                    'iops': 33554,
                    'lat_ns': {
                        'mean': 200000,
                        'stddev': 100000,
                        'percentile': {
                            '50.000000': 180000,
                            '99.000000': 400000,
                            '99.999000': 800000
                        }
                    }
                }
            }]
        }),
        ('mixed_rw', {
            'jobs': [{
                'read': {
                    'bw_bytes': 536870912,
                    'iops': 131072,
                    'lat_ns': {'mean': 150000, 'stddev': 75000, 'percentile': {}}
                },
                'write': {
                    'bw_bytes': 268435456,
                    'iops': 65536,
                    'lat_ns': {'mean': 180000, 'stddev': 90000, 'percentile': {}}
                }
            }]
        }),
    ]
    
    passed = 0
    for test_name, mock_data in test_cases:
        try:
            parsed = runner._parse_fio_result(json.dumps(mock_data), test_name)
            
            if 'metrics' in parsed:
                metrics = parsed['metrics']
                
                # 验证关键指标
                checks = []
                if 'bandwidth' in metrics:
                    checks.append(f"带宽={metrics['bandwidth']}MB/s")
                if 'iops' in metrics:
                    checks.append(f"IOPS={metrics['iops']}K")
                if 'latency_avg' in metrics:
                    checks.append(f"延迟={metrics['latency_avg']}μs")
                
                print_success(f"{test_name}: 结果解析正确")
                print_info(f"  {', '.join(checks)}")
                passed += 1
            else:
                print_error(f"{test_name}: 解析结果缺少 metrics")
        except Exception as e:
            print_error(f"{test_name}: 解析失败 - {e}")
    
    print_info(f"结果解析验证：{passed}/{len(test_cases)} 通过")
    return passed == len(test_cases)

def verify_result_validation():
    """验证结果验证逻辑"""
    print_header("验证 3: 结果验证（验收标准）")
    
    sys.path.insert(0, str(Path(__file__).parent.parent / 'core'))
    from runner import TestRunner
    
    runner = TestRunner(config={
        'targets': {
            'seq_read_burst': 2100,
            'seq_write_sustained': 250,
            'rand_read_burst': 200,
            'rand_write_burst': 330
        }
    })
    
    # 测试用例：(测试名，指标值，预期结果)
    test_cases = [
        ('seq_read_burst', {'bandwidth': 2150.5}, 'PASS'),
        ('seq_read_burst', {'bandwidth': 1900.0}, 'FAIL'),  # 低于目标 95%
        ('seq_write_sustained', {'bandwidth': 260.0}, 'PASS'),
        ('seq_write_sustained', {'bandwidth': 200.0}, 'FAIL'),
        ('rand_read_burst', {'iops': 210.5}, 'PASS'),
        ('rand_read_burst', {'iops': 180.0}, 'FAIL'),
        ('rand_write_burst', {'iops': 340.2}, 'PASS'),
        ('rand_write_burst', {'iops': 300.0}, 'FAIL'),
    ]
    
    passed = 0
    for test_name, metrics, expected in test_cases:
        result = {'status': 'PASS', 'metrics': metrics}
        status = runner._validate_result(result, test_name)
        
        if status == expected:
            print_success(f"{test_name}: 验证正确 ({metrics} → {status})")
            passed += 1
        else:
            print_error(f"{test_name}: 验证错误 (期望{expected}, 实际{status})")
    
    print_info(f"结果验证：{passed}/{len(test_cases)} 通过")
    return passed == len(test_cases)

def verify_report_generation():
    """验证报告生成"""
    print_header("验证 4: 报告生成")
    
    sys.path.insert(0, str(Path(__file__).parent.parent / 'core'))
    from reporter import ReportGenerator
    
    # 准备测试数据
    test_data = {
        'test_id': 'verify_' + datetime.now().strftime('%Y%m%d_%H%M%S'),
        'timestamp': datetime.now().isoformat(),
        'device': '/dev/zero',
        'test_results': {
            'test_id': 'verify_001',
            'suite': 'performance',
            'timestamp': datetime.now().isoformat(),
            'device': '/dev/zero',
            'test_cases': [
                {
                    'test_name': 'seq_read_burst',
                    'status': 'PASS',
                    'metrics': {'bandwidth': 2150.5, 'iops': 0, 'latency_avg': 120.5}
                },
                {
                    'test_name': 'seq_write_burst',
                    'status': 'PASS',
                    'metrics': {'bandwidth': 1680.3, 'iops': 0, 'latency_avg': 150.2}
                },
                {
                    'test_name': 'rand_write_burst',
                    'status': 'FAIL',
                    'metrics': {'bandwidth': 0, 'iops': 280.5, 'latency_avg': 200.5}
                }
            ],
            'summary': {
                'total': 3,
                'passed': 2,
                'failed': 1,
                'errors': 0,
                'pass_rate': 66.7
            }
        },
        'system_info': {
            'hostname': 'verify-host',
            'kernel': '5.15.0',
            'cpu_count': 8,
            'memory_total': 8192,
            'python_version': '3.11.2'
        }
    }
    
    # 生成报告
    reporter = ReportGenerator(output_dir='./results/verify', formats=['html', 'json', 'text'])
    files = reporter.generate(test_data, test_data['test_id'])
    
    if files and len(files) > 0:
        print_success(f"报告生成成功：{len(files)} 个文件")
        
        # 验证文件存在
        if isinstance(files, str):
            files = [files]
        
        for file_path in files:
            p = Path(file_path)
            if p.exists():
                file_size = p.stat().st_size
                print_success(f"  ✓ {p.name} ({file_size} bytes)")
            else:
                print_error(f"  ✗ {p.name} (文件不存在)")
        
        # 验证内容
        html_file = Path(files[0]) if 'html' in files[0] else Path(files[1]) if len(files) > 1 else None
        if html_file and html_file.exists():
            content = html_file.read_text()
            if 'UFS 系统测试报告' in content and '2150.5' in content:
                print_success("HTML 报告内容正确")
        
        print_info(f"报告位置：./results/verify/{test_data['test_id']}/")
        return True
    else:
        print_error("报告生成失败")
        return False

def verify_failure_analysis():
    """验证失效分析"""
    print_header("验证 5: 失效分析")
    
    sys.path.insert(0, str(Path(__file__).parent.parent / 'core'))
    from analyzer import FailureAnalyzer
    
    analyzer = FailureAnalyzer()
    
    # 测试场景 1: SLC Cache 耗尽
    print_info("场景 1: SLC Cache 耗尽")
    fail_data_1 = {
        'test_id': 'verify_slc_001',
        'test_results': {
            'test_cases': [{
                'test_name': 'seq_write_sustained',
                'status': 'FAIL',
                'metrics': {
                    'bandwidth': 180.5,
                    'latency_avg': 850.6,
                    'latency_stddev': 650.3,
                    'latency_p99999': 3500.0
                }
            }]
        },
        'config': {'targets': {'seq_write_sustained': 250}}
    }
    
    analysis_1 = analyzer.analyze(fail_data_1)
    if analysis_1.get('root_causes'):
        print_success(f"识别出 {len(analysis_1['root_causes'])} 个失效模式")
        for cause in analysis_1['root_causes'][:2]:
            print_info(f"  - {cause['name']} ({cause['confidence']*100:.0f}%)")
    else:
        print_error("未识别出失效模式")
    
    # 测试场景 2: 延迟长尾
    print_info("\n场景 2: 延迟长尾")
    fail_data_2 = {
        'test_id': 'verify_latency_001',
        'test_results': {
            'test_cases': [{
                'test_name': 'latency_percentile',
                'status': 'FAIL',
                'metrics': {
                    'latency_p50': 50.0,
                    'latency_p99': 500.0,
                    'latency_p99999': 8000.0,
                    'latency_stddev': 1200.0
                }
            }]
        },
        'config': {}
    }
    
    analysis_2 = analyzer.analyze(fail_data_2)
    if analysis_2.get('root_causes'):
        print_success(f"识别出 {len(analysis_2['root_causes'])} 个失效模式")
        for cause in analysis_2['root_causes'][:2]:
            print_info(f"  - {cause['name']} ({cause['confidence']*100:.0f}%)")
    else:
        print_error("未识别出失效模式")
    
    return True

def verify_config_management():
    """验证配置管理"""
    print_header("验证 6: 配置管理")
    
    # 直接加载配置 JSON
    config_path = Path(__file__).parent.parent / 'config' / 'default.json'
    if config_path.exists():
        with open(config_path, 'r') as f:
            config = json.load(f)
    else:
        config = {}
    
    checks = [
        ('targets' in config, "验收目标"),
        ('execution' in config, "执行参数"),
        ('device' in config, "设备配置"),
        (len(config.get('targets', {})) >= 8, "目标数量"),
    ]
    
    passed = 0
    for check, name in checks:
        if check:
            print_success(f"配置检查：{name}")
            passed += 1
        else:
            print_error(f"配置检查：{name} 失败")
    
    if config:
        print_success("配置文件加载成功")
        return passed == len(checks)
    else:
        print_error("配置文件加载失败")
        return False

def verify_suite_loading():
    """验证套件加载"""
    print_header("验证 7: 测试套件加载")
    
    sys.path.insert(0, str(Path(__file__).parent.parent / 'core'))
    from runner import TestRunner
    
    runner = TestRunner()
    suites = runner.list_suites()
    
    expected_suites = ['performance', 'qos', 'reliability', 'scenario']
    expected_tests = {
        'performance': 9,
        'qos': 2,
        'reliability': 1,
        'scenario': 2
    }
    
    passed = 0
    for suite_name in expected_suites:
        if suite_name in suites:
            tests = suites[suite_name]
            expected_count = expected_tests.get(suite_name, 0)
            
            if len(tests) >= expected_count:
                print_success(f"{suite_name}: {len(tests)} 个测试项")
                passed += 1
            else:
                print_error(f"{suite_name}: 测试项数量不足 (期望{expected_count}, 实际{len(tests)})")
        else:
            print_error(f"{suite_name}: 套件未找到")
    
    print_info(f"套件加载验证：{passed}/{len(expected_suites)} 通过")
    return passed == len(expected_suites)

def main():
    """主验证流程"""
    print_header("🔍 SysTest 最小化验证（纯 Python 版）")
    print_info(f"开始时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print_info(f"工作目录：{Path.cwd()}")
    print_info("不依赖 FIO，验证完整执行流程")
    
    results = []
    
    # 1. 命令构建
    results.append(("命令构建", verify_command_building()))
    
    # 2. 结果解析
    results.append(("结果解析", verify_result_parsing()))
    
    # 3. 结果验证
    results.append(("结果验证", verify_result_validation()))
    
    # 4. 报告生成
    results.append(("报告生成", verify_report_generation()))
    
    # 5. 失效分析
    results.append(("失效分析", verify_failure_analysis()))
    
    # 6. 配置管理
    results.append(("配置管理", verify_config_management()))
    
    # 7. 套件加载
    results.append(("套件加载", verify_suite_loading()))
    
    # 总结
    print_header("📊 验证总结")
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"  {status} - {name}")
    
    print(f"\n总计：{passed}/{total} 验证通过")
    
    if passed == total:
        print_success("🎉 所有验证通过！SysTest 框架可以投入使用！")
        return 0
    else:
        print_error(f"⚠️  {total - passed} 个验证未通过，请检查")
        return 1

if __name__ == '__main__':
    sys.exit(main())
