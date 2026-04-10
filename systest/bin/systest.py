#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SysTest - UFS System Test Framework Main Entry
Unified test entry, parameterized execution, automatic reporting, failure analysis

Usage:
    SysTest run --suite=performance --device=/dev/ufs0
    SysTest list
    SysTest report --latest
"""

import sys
import os
import json
import argparse
import logging
from datetime import datetime
from pathlib import Path

script_dir = Path(__file__).parent.absolute()
project_root = script_dir.parent
sys.path.insert(0, str(project_root))

from core.runner import TestRunner
from core.collector import ResultCollector
from core.reporter import ReportGenerator
from core.logger import get_logger, close_all_loggers

def get_test_mode(args, runtime_config):
    """Determine test mode: command line > env > config > default"""
    # Priority 1: Command line argument
    if hasattr(args, 'mode') and args.mode:
        return args.mode
    
    # Priority 2: Environment variable
    import os
    env_mode = os.environ.get('SYSTEST_MODE')
    if env_mode:
        return env_mode
    
    # Priority 3: Config file
    if runtime_config.get('mode'):
        return runtime_config['mode']
    
    # Default: development
    return 'development'


def cmd_run(args):
    """Execute tests"""
    import time
    from datetime import datetime

    script_name = Path(__file__).stem
    name_suffix = ""
    if args.suite:
        name_suffix = f"_{args.suite}"
    elif args.test:
        name_suffix = f"_{args.test}"
    test_id = f"{script_name}{name_suffix}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

    # Load runtime config to determine mode
    default_config_path = project_root / 'config' / 'runtime.json'
    runtime_config = {}
    if default_config_path.exists():
        try:
            with open(default_config_path, 'r', encoding='utf-8') as f:
                runtime_config = json.load(f)
        except json.JSONDecodeError:
            runtime_config = {}
    
    # Determine test mode
    test_mode = get_test_mode(args, runtime_config)
    mode_display = 'Development' if test_mode == 'development' else 'Production'
    
    # Determine log level based on mode
    console_level = logging.DEBUG if (args.verbose or test_mode == 'development') else logging.INFO
    file_level = logging.DEBUG if test_mode == 'development' else logging.INFO

    logger = get_logger(
        test_id=test_id,
        log_dir='logs',
        console_level=console_level,
        file_level=file_level
    )

    # 测试前摘要 - 终端清晰显示
    print("\n" + "=" * 60)
    print("📊 UFS 测试开始")
    print("=" * 60)
    print(f"测试模式：{mode_display.upper()}")
    print(f"设备路径：{args.device or 'auto'}")
    print(f"测试目录：{args.test_dir or 'auto'}")
    print(f"测试套件：{args.suite or args.test or 'all'}")
    if args.batch > 1:
        print(f"批量测试：{args.batch} 轮，间隔 {args.interval}s")
    print("=" * 60 + "\n")

    # Log test mode at startup
    logger.info(f"测试模式：{mode_display}")

    if hasattr(args, 'config') and args.config:
        config_path = Path(args.config)
        if config_path.exists():
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    preset_config = json.load(f)
            except json.JSONDecodeError as e:
                logger.error(f"Invalid preset configuration file: {config_path}: {e}")
                return 2
            if preset_config.get('device') and not args.device:
                args.device = preset_config['device']
            if preset_config.get('test_dir') and not args.test_dir:
                args.test_dir = preset_config['test_dir']
            logger.info(f"Loaded preset configuration: {args.config}")

    default_config_path = project_root / 'config' / 'runtime.json'
    if default_config_path.exists():
        try:
            with open(default_config_path, 'r', encoding='utf-8') as f:
                default_config = json.load(f)
        except json.JSONDecodeError as e:
            logger.warning(f"Invalid default configuration file: {default_config_path}: {e} (continuing with empty config)")
            default_config = {}
        if default_config.get('device') and not args.device:
            args.device = default_config['device']
            logger.info(f"Loaded default device path: {args.device} (from config/runtime.json)")
        if default_config.get('test_dir') and not args.test_dir:
            args.test_dir = default_config['test_dir']
            logger.info(f"Loaded default test directory: {args.test_dir} (from config/runtime.json)")

    logger.info("Starting test execution")
    if args.all:
        logger.info("Mode: Run all test suites")
    elif args.suite:
        logger.info(f"Suite: {args.suite}")
    elif args.test:
        logger.info(f"Test: {args.test}")
    if args.device:
        logger.info(f"Device: {args.device} (specified)")
    else:
        logger.warning("Device path not specified, will use default /dev/sda")
        logger.warning("  Recommend running: python3 bin/SysTest check-env --save-config")
        args.device = '/dev/sda'
    if args.test_dir:
        logger.info(f"Test directory: {args.test_dir} (specified)")
    else:
        logger.warning("Test directory not specified, will use default /mapdata/ufs_test")
        logger.warning("  Recommend running: python3 bin/SysTest check-env --save-config")
        args.test_dir = '/mapdata/ufs_test'
    if args.batch > 1:
        logger.info(f"Batch test: {args.batch} runs, {args.interval}s interval")
    logger.info(f"Test ID: {test_id}")
    logger.debug(f"Log file: {logger.get_log_file()}")

    batch_results = []
    for i in range(args.batch):
        if args.batch > 1:
            logger.info(f"\n{'='*60}")
            logger.info(f"Batch test {i+1}/{args.batch}")
            logger.info(f"{'='*60}")

        suites_to_run = []
        if args.all:
            suites_to_run = ['performance', 'qos']
        elif args.suite:
            suites_to_run = [args.suite]
        elif args.test:
            runner_tmp = TestRunner()
            for suite_name, tests in runner_tmp.list_suites().items():
                if args.test in tests:
                    suites_to_run = [suite_name]
                    break

        if not suites_to_run:
            logger.error("No test suite or test item specified")
            return 2

        for suite_name in suites_to_run:
            runner = TestRunner(
                device=args.device,
                test_dir=args.test_dir,
                verbose=args.verbose,
                mode=test_mode
            )
            collector = ResultCollector(output_dir=args.output)
            reporter = ReportGenerator(template='default')

            try:
                results = runner.run_suite(suite_name)

                report_data = collector.collect(results, test_id=test_id, suite_name=suite_name, device=args.device)

                report_formats = args.format.split(',') if hasattr(args, 'format') and args.format else ['html', 'json']

                if hasattr(args, 'export_csv') and args.export_csv:
                    report_formats.append('csv')

                report_path = reporter.generate(report_data, output_dir=args.output, formats=report_formats)

                logger.info(f"Test completed - Pass rate: {report_data['summary']['pass_rate']:.1f}%")
                logger.info(f"Report generated: {report_path}")
                logger.info(f"Log file: {logger.get_log_file()}")

                batch_results.append(report_data)

            except Exception as e:
                logger.critical(f"Test execution failed: {e}", exc_info=True)
                logger.error(f"Error log: {logger.get_error_file()}")
                
                # 终端错误输出 - 红色高亮 + 调试建议
                print(f"\n\033[31m❌ 严重错误：{e}\033[0m")
                print("测试已 forcibly 终止\n")
                print("💡 调试建议:")
                error_msg = str(e).lower()
                if 'device' in error_msg:
                    print("  1. 检查设备路径是否正确")
                    print("  2. 运行 'lsblk' 查看设备列表")
                    print("  3. 检查设备权限：ls -la /dev/sd*")
                elif 'permission' in error_msg:
                    print("  1. 使用 sudo 运行测试")
                    print("  2. 或将用户加入 disk 组：sudo usermod -aG disk $USER")
                elif 'space' in error_msg:
                    print("  1. 检查磁盘空间：df -h")
                    print("  2. 清理测试目录或指定 --test-dir")
                else:
                    print("  1. 查看详细日志：tail -f logs/*.log")
                    print("  2. 检查错误日志：cat logs/*_error.log")
                print(f"\n详细错误信息请查看：{logger.get_error_file()}\n")
                
                if args.batch == 1:
                    close_all_loggers()
                    return 2

        if args.batch > 1 and i < args.batch - 1:
            logger.info(f"\nWaiting {args.interval}s before next round...")
            time.sleep(args.interval)

    # 测试完成摘要 - 终端清晰显示
    print("\n" + "=" * 60)
    print("📊 测试完成摘要")
    print("=" * 60)
    
    if args.batch > 1:
        logger.info("\n" + "=" * 60)
        logger.info(f"Batch Test Results Summary ({args.batch} rounds)")
        logger.info("=" * 60)
        
        print(f"批量测试汇总 ({args.batch} 轮):")
        for i, result in enumerate(batch_results, 1):
            summary = result['summary']
            logger.info(f"  Round {i}: {summary['passed']}/{summary['total']} passed ({summary['pass_rate']:.1f}%)")
            print(f"  第 {i} 轮：{summary['passed']}/{summary['total']} 通过 ({summary['pass_rate']:.1f}%)")

        total_tests = sum(r['summary']['total'] for r in batch_results)
        total_passed = sum(r['summary']['passed'] for r in batch_results)
        total_failed = sum(r['summary']['failed'] for r in batch_results)
        total_errors = sum(r['summary']['errors'] for r in batch_results)
        overall_pass_rate = (total_passed / total_tests * 100) if total_tests > 0 else 0
        logger.info("-" * 60)
        logger.info(f"  Total: {total_passed}/{total_tests} passed ({overall_pass_rate:.1f}%)")
        logger.info("=" * 60)
        
        print("-" * 60)
        print(f"  总计：{total_passed}/{total_tests} 通过 ({overall_pass_rate:.1f}%)")
    else:
        # 单轮测试摘要
        if batch_results:
            result = batch_results[0]
            summary = result['summary']
            total = summary['total']
            passed = summary['passed']
            failed = summary['failed']
            errors = summary['errors']
            pass_rate = summary['pass_rate']
            
            print(f"总测试数：{total}")
            print(f"\033[32m✅ 通过：{passed}\033[0m")
            if failed > 0:
                print(f"\033[31m❌ 失败：{failed}\033[0m")
            if errors > 0:
                print(f"\033[31m⚠️  错误：{errors}\033[0m")
            print(f"通过率：{pass_rate:.1f}%")
            
            # 显示失败测试列表
            if failed > 0:
                print("\n失败测试列表:")
                for tc in result.get('test_cases', []):
                    if tc.get('status') == 'FAIL':
                        print(f"  \033[31m❌ {tc['name']}\033[0m")
                        if 'failures' in tc:
                            for f in tc['failures']:
                                print(f"     - {f['check']}: {f['reason']}")
    
    print("=" * 60)
    
    # 显示日志和报告路径
    log_file = logger.get_log_file()
    error_file = logger.get_error_file()
    print(f"\n详细日志：{log_file}")
    print(f"错误日志：{error_file}")
    if batch_results:
        report_path = batch_results[0].get('report_path', 'N/A')
        print(f"测试报告：{report_path}")
    print("=" * 60 + "\n")

    close_all_loggers()

    has_failure = any(r['summary']['failed'] > 0 or r['summary']['errors'] > 0 for r in batch_results)
    return 1 if has_failure else 0

def cmd_list(args):
    """List available tests"""
    from core.runner import TestRunner

    runner = TestRunner()

    # Filter by suite if specified
    if hasattr(args, 'suite') and args.suite:
        suites = runner.list_suites()
        if args.suite in suites:
            print(f"\n=== Test Suite: {args.suite} ===\n")
            tests = suites[args.suite]
            for test in tests:
                print(f"  - {test}")
            print(f"\nTotal: {len(tests)} test items in suite '{args.suite}'")
        else:
            print(f"Unknown suite: {args.suite}")
            print(f"Available suites: {', '.join(suites.keys())}")
            return 1
        return 0

    print("\n=== Available Test Suites ===\n")
    suites = runner.list_suites()

    for suite_name, tests in suites.items():
        print(f"Suite: {suite_name}")
        for test in tests:
            print(f"  - {test}")
        print()

    print(f"Total: {sum(len(t) for t in suites.values())} test items, {len(suites)} suites")

def cmd_report(args):
    """Generate/view report"""
    from core.reporter import ReportGenerator
    from core.logger import get_logger
    from datetime import datetime

    logger = get_logger(test_id='report', log_dir='logs', console_level=logging.INFO, file_level=logging.DEBUG)
    reporter = ReportGenerator()

    if hasattr(args, 'list') and args.list:
        # List all available reports
        print("\n=== Available Reports ===\n")
        results_dir = Path('./results')
        if results_dir.exists():
            # Scan subdirectories for report.html files
            html_reports = list(results_dir.glob('*/report.html'))
            json_reports = list(results_dir.glob('*/results.json'))
            
            # Sort by modification time (newest first)
            html_reports.sort(key=lambda x: x.parent.stat().st_mtime, reverse=True)
            json_reports.sort(key=lambda x: x.parent.stat().st_mtime, reverse=True)
            
            if html_reports:
                print(f"Found {len(html_reports)} HTML report(s):\n")
                for i, report in enumerate(html_reports[:10], 1):  # Show latest 10
                    mtime = datetime.fromtimestamp(report.parent.stat().st_mtime)
                    print(f"{i}. {report.parent.name}")
                    print(f"   Path: {report.absolute()}")
                    print(f"   Time: {mtime.strftime('%Y-%m-%d %H:%M:%S')}")
                if len(html_reports) > 10:
                    print(f"\n... and {len(html_reports) - 10} more")
            else:
                print("No HTML reports found")
            
            print()
            
            if json_reports:
                print(f"Found {len(json_reports)} JSON report(s):\n")
                for i, report in enumerate(json_reports[:10], 1):  # Show latest 10
                    mtime = datetime.fromtimestamp(report.parent.stat().st_mtime)
                    print(f"{i}. {report.parent.name}")
                    print(f"   Path: {report.absolute()}")
                    print(f"   Time: {mtime.strftime('%Y-%m-%d %H:%M:%S')}")
                if len(json_reports) > 10:
                    print(f"\n... and {len(json_reports) - 10} more")
            else:
                print("No JSON reports found")
        else:
            print(f"Report directory does not exist: {results_dir}")
            print("Run tests first to generate reports")
        return 0

    if args.latest:
        report_path = reporter.get_latest_report()
    elif args.id:
        report_path = reporter.get_report(args.id)
    else:
        print("Please specify --latest, --id, or --list")
        return 1

    if report_path:
        logger.info(f"Report path: {report_path}")
        print(f"\nReport path: {report_path}")
        if args.open:
            import webbrowser
            webbrowser.open(f'file://{report_path}')

        if hasattr(args, 'export_csv') and args.export_csv:
            csv_path = f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            json_path = Path(report_path).parent / 'results.json'
            if json_path.exists():
                import json
                with open(json_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                with open(csv_path, 'w', encoding='utf-8') as f:
                    f.write("test_name,status,duration,metric_name,metric_value,metric_unit\n")
                    for tc in data.get('test_cases', []):
                        name = tc.get('name', '')
                        status = tc.get('status', '')
                        duration = tc.get('duration', 0)
                        metrics = tc.get('metrics', {})
                        for m_name, m_val in metrics.items():
                            if isinstance(m_val, dict):
                                val = m_val.get('value', '')
                                unit = m_val.get('unit', '')
                            else:
                                val = m_val
                                unit = ''
                            f.write(f"{name},{status},{duration:.2f},{m_name},{val},{unit}\n")
                print(f"CSV exported: {csv_path}")

        return 0
    else:
        logger.error("Report not found")
        print("Report not found")
        return 1

def cmd_config(args):
    """View/manage configuration"""
    import json
    from pathlib import Path

    config_path = Path(__file__).parent.parent / 'config' / 'runtime.json'

    if hasattr(args, 'reset') and args.reset:
        default_config = {
            "device": None,
            "test_dir": None,
            "device_capacity_gb": None,
            "env_checked_at": None,
            "system": {},
            "toolchain": {},
            "_comment": "Configuration reset, please run check-env --save-config to regenerate"
        }
        config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(default_config, f, indent=2, ensure_ascii=False)
        print(f"Configuration reset: {config_path}")
        return 0

    if hasattr(args, 'device') and args.device:
        if not config_path.exists():
            config = {}
        else:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
        config['device'] = args.device
        config['env_checked_at'] = datetime.now().isoformat()
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        print(f"Device path set: {args.device}")

    if hasattr(args, 'test_dir') and args.test_dir:
        if not config_path.exists():
            config = {}
        else:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
        config['test_dir'] = args.test_dir
        config['env_checked_at'] = datetime.now().isoformat()
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        print(f"Test directory set: {args.test_dir}")

    if hasattr(args, 'show') and args.show:
        if config_path.exists():
            print(f"\n=== Configuration File: {config_path} ===\n")
            with open(config_path, 'r', encoding='utf-8') as f:
                print(f.read())
        else:
            print(f"Configuration file does not exist: {config_path}")
            print("Run 'SysTest check-env --save-config' to auto-generate configuration")

    return 0

def cmd_check_env(args):
    """Environment check"""
    import subprocess

    check_script = script_dir / 'check_env.py'

    if not check_script.exists():
        print(f"Environment check script does not exist: {check_script}")
        return 1

    cmd = [sys.executable, str(check_script)]
    if args.report:
        cmd.extend(['--report', '--output', args.output])
    # --save-config is default behavior, --no-save overrides it
    if hasattr(args, 'no_save') and args.no_save:
        cmd.append('--no-save')
    if args.verbose:
        cmd.append('-v')

    result = subprocess.run(cmd)
    return result.returncode

def cmd_mode(args):
    """View/set test mode"""
    import json
    from pathlib import Path

    config_path = Path(__file__).parent.parent / 'config' / 'runtime.json'
    
    # Load current config
    if config_path.exists():
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
    else:
        config = {}
    
    current_mode = config.get('mode', 'development')
    
    if hasattr(args, 'set') and args.set:
        # Set mode
        if args.set not in ['development', 'production']:
            print(f"Invalid mode: {args.set}. Must be 'development' or 'production'")
            return 1
        
        config['mode'] = args.set
        config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        
        mode_display = 'Development' if args.set == 'development' else 'Production'
        print(f"Test mode set to: {mode_display}")
        print(f"Configuration file: {config_path}")
    else:
        # Show current mode
        mode_display = 'Development' if current_mode == 'development' else 'Production'
        print(f"\n=== Current Test Mode ===")
        print(f"Mode: {mode_display}")
        print(f"Config file: {config_path}")
        print(f"\nTo change mode:")
        print(f"  python3 bin/systest.py mode --set=development")
        print(f"  python3 bin/systest.py mode --set=production")
        print(f"\nOr use environment variable:")
        print(f"  export SYSTEST_MODE=production")
        print(f"\nOr use command line argument:")
        print(f"  python3 bin/systest.py run --suite performance --mode=production")
    
    return 0


def cmd_compare_baseline(args):
    """Performance baseline comparison"""
    import subprocess

    compare_script = script_dir / 'compare_baseline.py'

    if not compare_script.exists():
        print(f"Comparison script does not exist: {compare_script}")
        return 1

    cmd = [sys.executable, str(compare_script)]
    if args.dev:
        cmd.extend(['--dev', args.dev])
    if args.ci:
        cmd.extend(['--ci', args.ci])
    if args.baseline1:
        cmd.extend(['--baseline1', args.baseline1])
    if args.baseline2:
        cmd.extend(['--baseline2', args.baseline2])
    if args.threshold:
        cmd.extend(['--threshold', str(args.threshold)])
    if args.output:
        cmd.extend(['--output', args.output])

    result = subprocess.run(cmd)

    if hasattr(args, 'export_csv') and args.export_csv:
        print("\nCSV export functionality will be implemented in the comparison script")

    return result.returncode

def main():
    """Main function - Unified entry"""
    parser = argparse.ArgumentParser(
        description='''UFS Auto - UFS 存储设备自动化测试框架

快速开始:
  %(prog)s check-env --save-config     # 检查环境并保存配置
  %(prog)s run --suite performance     # 运行性能测试（开发模式）
  %(prog)s mode --show                 # 查看当前模式

常用命令:
  %(prog)s list                        # 列出所有测试
  %(prog)s run --suite <name>          # 运行测试套件
  %(prog)s report --latest             # 查看最新报告
  %(prog)s config --show               # 查看配置
  %(prog)s mode --set=production       # 切换到生产模式

使用示例:
  # 开发模式快速验证
  %(prog)s run --suite performance

  # 生产模式完整测试
  %(prog)s run --suite performance --mode=production

  # 运行单个测试
  %(prog)s run --test t_perf_SeqReadBurst_001

  # 查看详细日志
  %(prog)s run --suite performance --verbose

  # 自定义设备和测试目录
  %(prog)s run --suite performance --device=/dev/sda --test-dir=/mapdata/ufs_test

  # 批量测试（3 次，间隔 60 秒）
  %(prog)s run --suite performance --batch=3 --interval=60

详细文档：docs/README.md
GitHub: https://github.com/hanxueyuan/ufsauto
''',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    subparsers = parser.add_subparsers(dest='command', help='Available commands')

    run_parser = subparsers.add_parser('run',
        help='Execute tests',
        description='Execute UFS performance/reliability tests',
        epilog="""Examples:
  [Basic Usage]
  python3 bin/SysTest run --suite=performance

  python3 bin/SysTest run --suite=qos

  python3 bin/SysTest run --all

  [Single Test]
  python3 bin/SysTest run --test=t_perf_SeqReadBurst_001

  python3 bin/SysTest run --test=t_perf_SeqReadBurst_001 -v

  [Batch Test]
  python3 bin/SysTest run --suite=performance --batch=3 --interval=60

  [Specify Device and Directory]
  python3 bin/SysTest run --suite=performance --device=/dev/sda

  python3 bin/SysTest run --suite=performance --test-dir=/mapdata/ufs_test

  python3 bin/SysTest run --suite=performance --device=/dev/sda --test-dir=/mapdata/ufs_test

  [Using Preset Configuration]
  python3 bin/SysTest run --suite=performance --config=configs/ufs31_128GB.json

  python3 bin/SysTest run --suite=performance --config=configs/automotive_grade.json

  [Complete Examples]
  python3 bin/SysTest run --suite=performance --batch=3 --device=/dev/sda

  python3 bin/SysTest run --all -v

  python3 bin/SysTest run --config=configs/ufs31_128GB.json
""")
    run_parser.add_argument('--suite', '-s', type=str, help='测试套件名称 (performance, qos)')
    run_parser.add_argument('--test', '-t', type=str, help='单个测试名称 (t_perf_SeqReadBurst_001)')
    run_parser.add_argument('--all', '-a', action='store_true', help='运行所有测试套件')
    run_parser.add_argument('--device', '-d', default=None, help='设备路径 (默认：/dev/sda)')
    run_parser.add_argument('--test-dir', '-tdir', default=None, help='测试目录 (默认：/tmp/ufs_test)')
    run_parser.add_argument('--output', '-o', default='./results', help='输出目录')
    run_parser.add_argument('--format', '-f', default='html,json,txt', help='报告格式 (html/json/txt/csv)')
    run_parser.add_argument('--verbose', '-v', action='store_true', help='详细日志模式')
    run_parser.add_argument('--batch', '-b', type=int, default=1, help='批量测试次数')
    run_parser.add_argument('--interval', '-i', type=int, default=60, help='批量测试间隔 (秒)')
    run_parser.add_argument('--config', '-c', default=None, help='预设配置文件路径')
    run_parser.add_argument('--mode', '-m', choices=['development', 'production'], help='测试模式 (默认：development)')
    run_parser.add_argument('--export-csv', action='store_true', help='导出 CSV 格式结果')
    run_parser.set_defaults(func=cmd_run)

    list_parser = subparsers.add_parser('list',
        help='List available tests',
        description='List all available test suites and test items',
        epilog="""Examples:
  python3 bin/SysTest list

  python3 bin/SysTest list --suite performance

  python3 bin/SysTest list --detail
""")
    list_parser.add_argument('--detail', action='store_true', help='显示详细信息')
    list_parser.add_argument('--suite', '-s', type=str, help='按套件名称过滤 (performance, qos)')
    list_parser.set_defaults(func=cmd_list)

    report_parser = subparsers.add_parser('report',
        help='Generate/view report',
        description='Generate or view test report',
        epilog="""Examples:
  python3 bin/SysTest report --latest

  python3 bin/SysTest report --id=SysTest_performance_20260407_103000

  python3 bin/SysTest report --latest --export-csv
""")
    report_parser.add_argument('--latest', action='store_true', help='显示最新报告路径')
    report_parser.add_argument('--id', type=str, help='指定报告 ID')
    report_parser.add_argument('--list', action='store_true', help='列出所有历史报告')
    report_parser.add_argument('--open', action='store_true', help='在浏览器中打开')
    report_parser.add_argument('--export-csv', action='store_true', help='导出 CSV 格式')
    report_parser.set_defaults(func=cmd_report)

    config_parser = subparsers.add_parser('config',
        help='View/manage configuration',
        description='View or modify runtime configuration',
        epilog="""Examples:
  python3 bin/SysTest config --show

  python3 bin/SysTest config --device=/dev/sda

  python3 bin/SysTest config --test-dir=/mapdata/ufs_test

  python3 bin/SysTest config --reset
""")
    config_parser.add_argument('--show', action='store_true', help='Show configuration content')
    config_parser.add_argument('--reset', action='store_true', help='Reset configuration to default')
    config_parser.add_argument('--device', help='Set device path')
    config_parser.add_argument('--test-dir', help='Set test directory')
    config_parser.set_defaults(func=cmd_config)

    check_env_parser = subparsers.add_parser('check-env',
        help='Check environment and generate configuration',
        description='Detect UFS device and test directory, auto-generate runtime.json configuration',
        epilog="""Examples:
  python3 bin/SysTest check-env

  python3 bin/SysTest check-env --report

  python3 bin/SysTest check-env -v

  python3 bin/SysTest check-env --no-save
""")
    check_env_parser.add_argument('--report', action='store_true', help='Generate JSON report')
    check_env_parser.add_argument('--output', default='env_check_report.json', help='Report output path')
    check_env_parser.add_argument('--save-config', action='store_true', help='Save configuration to runtime.json (default behavior)')
    check_env_parser.add_argument('--no-save', action='store_true', help='Do not save configuration file')
    check_env_parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')
    check_env_parser.set_defaults(func=cmd_check_env)

    compare_parser = subparsers.add_parser('compare-baseline',
        help='Compare performance baselines',
        description='Compare performance differences between two sets of test results',
        epilog="""Examples:
  python3 bin/SysTest compare-baseline --dev=results/SysTest_perf_dev --ci=results/SysTest_perf_ci

  python3 bin/SysTest compare-baseline --baseline1=baseline_v1 --baseline2=baseline_v2

  python3 bin/SysTest compare-baseline --baseline1=baseline_v1 --baseline2=baseline_v2 --threshold=0.15

  python3 bin/SysTest compare-baseline --baseline1=baseline_v1 --baseline2=baseline_v2 --output=comparison_report.json
""")
    compare_parser.add_argument('--dev', help='Development board test result directory')
    compare_parser.add_argument('--ci', help='CI/CD test result directory')
    compare_parser.add_argument('--baseline1', help='First baseline directory')
    compare_parser.add_argument('--baseline2', help='Second baseline directory')
    compare_parser.add_argument('--threshold', type=float, default=0.10, help='Allowed difference ratio (default 0.10)')
    compare_parser.add_argument('--output', help='Report output path')
    compare_parser.set_defaults(func=cmd_compare_baseline)

    mode_parser = subparsers.add_parser('mode',
        help='View/set test mode',
        description='View or set test mode (development/production)',
        epilog="""Examples:
  python3 bin/systest.py mode

  python3 bin/systest.py mode --set=development

  python3 bin/systest.py mode --set=production

Mode Differences:
  Development mode (default):
    - Test duration: 60s (short)
    - Iterations: Single run
    - Log level: DEBUG (verbose)
    - Reports: Brief summary
    - Pre-checks: Skip some validations
    - Cleanup: Keep test files for debugging
    - Use for: Quick iteration during development
  
  Production mode:
    - Test duration: 300s+ (comprehensive)
    - Iterations: Multiple runs (3x)
    - Log level: INFO (concise)
    - Reports: Complete detailed reports
    - Pre-checks: All validations enabled
    - Cleanup: Auto cleanup test files
    - Use for: Final validation before deployment

Three ways to set mode:
  1. Config file: Edit config/runtime.json (persistent)
  2. Environment: export SYSTEST_MODE=production (session)
  3. CLI arg: --mode=production (one-time override)

Priority: CLI arg > Environment > Config file > Default (development)
""")
    mode_parser.add_argument('--set', type=str, choices=['development', 'production'], help='设置测试模式')
    mode_parser.add_argument('--show', action='store_true', help='显示当前模式')
    mode_parser.set_defaults(func=cmd_mode)

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    return args.func(args)

if __name__ == '__main__':
    sys.exit(main())
