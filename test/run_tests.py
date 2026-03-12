#!/usr/bin/env python3
"""
UFS 3.1 自动化测试执行脚本
"""
import argparse
import sys
import os
import pytest
from datetime import datetime

def main():
    parser = argparse.ArgumentParser(description='UFS 3.1 车规级测试执行脚本')
    
    parser.add_argument('--test-type', choices=['all', 'functional', 'performance', 'reliability'], 
                       default='all', help='测试类型')
    parser.add_argument('--output-dir', default='reports', help='测试报告输出目录')
    parser.add_argument('--verbose', '-v', action='store_true', help=' verbose输出')
    parser.add_argument('--dry-run', action='store_true', help='仅显示要执行的测试，不实际运行')
    parser.add_argument('--markers', help='指定要运行的标记测试，如"functional and not slow"')
    parser.add_argument('--html-report', default=None, help='HTML报告文件名')
    parser.add_argument('--junit-xml', default=None, help='JUnit XML报告文件名')
    
    args = parser.parse_args()
    
    # 创建输出目录
    os.makedirs(args.output_dir, exist_ok=True)
    
    # 生成默认报告文件名
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    if args.html_report is None:
        args.html_report = f"{args.output_dir}/ufs_test_report_{timestamp}.html"
    if args.junit_xml is None:
        args.junit_xml = f"{args.output_dir}/ufs_test_results_{timestamp}.xml"
    
    # 构建pytest命令参数
    pytest_args = []
    
    if args.verbose:
        pytest_args.append('-v')
    
    pytest_args.extend([
        f'--html={args.html_report}',
        '--self-contained-html',
        f'--junitxml={args.junit_xml}',
        '--tb=short',
        '--timeout=300',
    ])
    
    # 添加测试标记过滤
    if args.markers:
        pytest_args.extend(['-m', args.markers])
    else:
        if args.test_type == 'functional':
            pytest_args.extend(['-m', 'functional'])
        elif args.test_type == 'performance':
            pytest_args.extend(['-m', 'performance'])
        elif args.test_type == 'reliability':
            pytest_args.extend(['-m', 'reliability'])
    
    # 测试目录
    pytest_args.append('tests/')
    
    if args.dry_run:
        pytest_args.append('--collect-only')
        print("将要执行的测试命令：")
        print(f"pytest {' '.join(pytest_args)}")
        return 0
    
    print(f"开始执行UFS 3.1 {args.test_type}测试...")
    print(f"测试报告将保存到: {args.html_report}")
    print(f"JUnit结果将保存到: {args.junit_xml}")
    print("=" * 60)
    
    # 执行测试
    exit_code = pytest.main(pytest_args)
    
    print("=" * 60)
    print(f"测试执行完成，退出码: {exit_code}")
    
    if exit_code == 0:
        print("✅ 所有测试通过！")
    else:
        print(f"❌ 有 {exit_code} 个测试失败，请查看报告。")
    
    return exit_code

if __name__ == '__main__':
    sys.exit(main())
