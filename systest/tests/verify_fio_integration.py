#!/usr/bin/env python3
"""
SysTest FIO 集成验证脚本
使用真实 FIO 执行最小化测试，验证完整执行流程
"""

import subprocess
import sys
import json
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

def verify_fio_available():
    """验证 FIO 是否可用"""
    print_header("验证 1: FIO 工具检查")
    
    # 尝试多个路径
    fio_paths = [
        'fio',
        '/home/gem/.local/bin/fio',
        '/usr/bin/fio',
        '/usr/local/bin/fio'
    ]
    
    for fio_path in fio_paths:
        try:
            result = subprocess.run(
                [fio_path, '--version'],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                print_success(f"FIO 已安装：{fio_path}")
                print_success(f"FIO 版本：{result.stdout.strip()}")
                return fio_path
        except:
            continue
    
    print_error("FIO 未找到")
    return None

def verify_fio_basic_execution(fio_path):
    """验证 FIO 基本执行"""
    print_header("验证 2: FIO 基本执行（临时文件）")
    
    import tempfile
    import os
    
    # 创建临时文件用于测试
    temp_file = tempfile.mktemp(prefix='fio_test_')
    
    try:
        # 先创建文件
        with open(temp_file, 'wb') as f:
            f.write(b'\x00' * 1024 * 1024)  # 1MB
        
        # 使用临时文件执行 FIO 测试
        cmd = [
            fio_path,
            '--name=verify_basic',
            f'--filename={temp_file}',
            '--rw=read',
            '--bs=4k',
            '--iodepth=16',
            '--numjobs=1',
            '--runtime=1',
            '--time_based',
            '--output-format=json'
        ]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        
        if result.returncode == 0:
            print_success("FIO 执行成功")
            
            # 解析输出
            try:
                data = json.loads(result.stdout)
                if 'jobs' in data and len(data['jobs']) > 0:
                    job = data['jobs'][0]
                    read_stats = job.get('read', {})
                    bw = read_stats.get('bw_bytes', 0) / 1024 / 1024  # MB/s
                    iops = read_stats.get('iops', 0) / 1000  # KIOPS
                    
                    print_info(f"带宽：{bw:.2f} MB/s")
                    print_info(f"IOPS: {iops:.2f} K")
                    print_success("FIO 输出解析成功")
                    return True
            except json.JSONDecodeError as e:
                print_error(f"JSON 解析失败：{e}")
                return False
        else:
            print_error(f"FIO 执行失败：{result.stderr}")
            return False
            
    except subprocess.TimeoutExpired:
        print_error("FIO 执行超时")
        return False
    except Exception as e:
        print_error(f"FIO 执行异常：{e}")
        return False

def verify_sysTest_runner_with_fio(fio_path):
    """验证 SysTest Runner 与 FIO 集成"""
    print_header("验证 3: SysTest Runner 与 FIO 集成")
    
    sys.path.insert(0, str(Path(__file__).parent.parent / 'core'))
    from runner import TestRunner
    
    # 创建 runner，使用 /dev/zero
    runner = TestRunner(device='/dev/zero', verbose=True)
    
    # 测试命令构建
    test_info = runner._find_test('seq_read_burst')
    if test_info:
        fio_cmd = runner._build_fio_command('seq_read_burst', 60, test_info)
        
        # 替换为实际 FIO 路径
        fio_cmd[0] = fio_path
        
        print_success("命令构建成功")
        print_info(f"命令：{' '.join(fio_cmd)}")
        
        # 执行 FIO（1 秒超时）
        try:
            # 修改命令，缩短时间用于验证
            fio_cmd_short = [arg for arg in fio_cmd]
            # 添加 runtime=1 参数
            if '--runtime=60' in fio_cmd_short:
                fio_cmd_short[fio_cmd_short.index('--runtime=60')] = '--runtime=1'
            elif '--runtime=300' in fio_cmd_short:
                fio_cmd_short[fio_cmd_short.index('--runtime=300')] = '--runtime=1'
            else:
                fio_cmd_short.append('--runtime=1')
            
            result = subprocess.run(fio_cmd_short, capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0:
                print_success("FIO 执行成功")
                
                # 验证结果解析
                parsed = runner._parse_fio_result(result.stdout, 'seq_read_burst')
                
                if 'metrics' in parsed:
                    metrics = parsed['metrics']
                    print_success("结果解析成功")
                    print_info(f"带宽：{metrics.get('bandwidth', 0)} MB/s")
                    print_info(f"IOPS: {metrics.get('iops', 0)} K")
                    print_info(f"延迟：{metrics.get('latency_avg', 0)} μs")
                    return True
                else:
                    print_error("结果解析失败：缺少 metrics")
                    return False
            else:
                print_error(f"FIO 执行失败：{result.stderr}")
                return False
                
        except Exception as e:
            print_error(f"FIO 执行异常：{e}")
            return False
    else:
        print_error("未找到测试定义")
        return False

def verify_result_validation_with_fio_data():
    """使用真实 FIO 数据验证结果验证逻辑"""
    print_header("验证 4: 结果验证（使用真实 FIO 数据）")
    
    sys.path.insert(0, str(Path(__file__).parent.parent / 'core'))
    from runner import TestRunner
    
    runner = TestRunner(config={
        'targets': {
            'seq_read_burst': 2100,
            'seq_write_burst': 1650
        }
    })
    
    # 使用真实 FIO 输出的典型值
    test_cases = [
        # (测试名，真实 FIO 数据，预期结果)
        ('seq_read_burst', {
            'jobs': [{
                'read': {
                    'bw_bytes': 2254857830,  # ~2150 MB/s
                    'iops': 550502,
                    'lat_ns': {'mean': 115000, 'stddev': 45000, 'percentile': {}}
                }
            }]
        }, 'PASS'),
        
        ('seq_read_burst', {
            'jobs': [{
                'read': {
                    'bw_bytes': 1992294400,  # ~1900 MB/s (低于目标 95%)
                    'iops': 486400,
                    'lat_ns': {'mean': 125000, 'stddev': 55000, 'percentile': {}}
                }
            }]
        }, 'FAIL'),
    ]
    
    passed = 0
    for test_name, fio_data, expected in test_cases:
        fio_output = json.dumps(fio_data)
        parsed = runner._parse_fio_result(fio_output, test_name)
        status = runner._validate_result(parsed, test_name)
        
        if status == expected:
            bw = parsed['metrics']['bandwidth']
            print_success(f"{test_name}: {bw} MB/s → {status} (预期{expected})")
            passed += 1
        else:
            print_error(f"{test_name}: 验证错误 (期望{expected}, 实际{status})")
    
    print_info(f"结果验证：{passed}/{len(test_cases)} 通过")
    return passed == len(test_cases)

def verify_report_generation():
    """验证报告生成"""
    print_header("验证 5: 报告生成")
    
    sys.path.insert(0, str(Path(__file__).parent.parent / 'core'))
    from reporter import ReportGenerator
    
    # 准备测试数据（使用真实 FIO 数据的典型值）
    test_data = {
        'test_id': 'fio_verify_' + datetime.now().strftime('%Y%m%d_%H%M%S'),
        'timestamp': datetime.now().isoformat(),
        'device': '/dev/zero',
        'test_results': {
            'test_id': 'fio_verify_001',
            'suite': 'performance',
            'timestamp': datetime.now().isoformat(),
            'device': '/dev/zero',
            'test_cases': [
                {
                    'test_name': 'seq_read_burst',
                    'status': 'PASS',
                    'metrics': {'bandwidth': 2150.5, 'iops': 0, 'latency_avg': 115.0}
                },
                {
                    'test_name': 'seq_write_burst',
                    'status': 'PASS',
                    'metrics': {'bandwidth': 1680.3, 'iops': 0, 'latency_avg': 150.0}
                }
            ],
            'summary': {
                'total': 2,
                'passed': 2,
                'failed': 0,
                'errors': 0,
                'pass_rate': 100.0
            }
        }
    }
    
    # 生成报告
    reporter = ReportGenerator(output_dir='./results/fio_verify', formats=['html', 'json', 'text'])
    files = reporter.generate(test_data, test_data['test_id'])
    
    if files and len(files) > 0:
        print_success(f"报告生成成功：{len(files)} 个文件")
        
        # 验证文件存在
        for file_path in files:
            p = Path(file_path)
            if p.exists():
                file_size = p.stat().st_size
                print_success(f"  ✓ {p.name} ({file_size} bytes)")
        
        print_info(f"报告位置：./results/fio_verify/{test_data['test_id']}/")
        return True
    else:
        print_error("报告生成失败")
        return False

def main():
    """主验证流程"""
    print_header("🔍 SysTest FIO 集成验证")
    print_info(f"开始时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print_info(f"工作目录：{Path.cwd()}")
    
    results = []
    
    # 1. FIO 检查
    fio_path = verify_fio_available()
    if fio_path:
        results.append(("FIO 工具", True))
    else:
        results.append(("FIO 工具", False))
        print_error("FIO 未找到，无法继续验证")
        return 1
    
    # 2. FIO 基本执行
    results.append(("FIO 基本执行", verify_fio_basic_execution(fio_path)))
    
    # 3. SysTest Runner 集成
    results.append(("Runner 集成", verify_sysTest_runner_with_fio(fio_path)))
    
    # 4. 结果验证
    results.append(("结果验证", verify_result_validation_with_fio_data()))
    
    # 5. 报告生成
    results.append(("报告生成", verify_report_generation()))
    
    # 总结
    print_header("📊 验证总结")
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"  {status} - {name}")
    
    print(f"\n总计：{passed}/{total} 验证通过")
    
    if passed == total:
        print_success("🎉 所有验证通过！SysTest FIO 集成完成！")
        return 0
    else:
        print_error(f"⚠️  {total - passed} 个验证未通过，请检查")
        return 1

if __name__ == '__main__':
    sys.exit(main())
