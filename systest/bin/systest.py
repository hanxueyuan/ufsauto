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
                if args.batch == 1:
                    close_all_loggers()
                    return 2

        if args.batch > 1 and i < args.batch - 1:
            logger.info(f"\nWaiting {args.interval}s before next round...")
            time.sleep(args.interval)

    if args.batch > 1:
        logger.info("\n" + "=" * 60)
        logger.info(f"Batch Test Results Summary ({args.batch} rounds)")
        logger.info("=" * 60)
        for i, result in enumerate(batch_results, 1):
            summary = result['summary']
            logger.info(f"  Round {i}: {summary['passed']}/{summary['total']} passed ({summary['pass_rate']:.1f}%)")

        total_tests = sum(r['summary']['total'] for r in batch_results)
        total_passed = sum(r['summary']['passed'] for r in batch_results)
        overall_pass_rate = (total_passed / total_tests * 100) if total_tests > 0 else 0
        logger.info("-" * 60)
        logger.info(f"  Total: {total_passed}/{total_tests} passed ({overall_pass_rate:.1f}%)")
        logger.info("=" * 60)

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
        description='UFS System Test Framework - SysTest',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
================================================================================
Quick Start:
  SysTest check-env --save-config
  SysTest run --suite performance
  SysTest run --all
  SysTest report --latest
  SysTest report --list            # List all available reports
  SysTest mode                    # View current test mode
  SysTest mode --set=production   # Switch to production mode

Execute Tests:
  SysTest run --suite performance
  SysTest run --suite performance --mode=production  # Run in production mode
  SysTest run --suite qos
  SysTest run --test t_perf_SeqReadBurst_001
  SysTest run --test t_perf_SeqReadBurst_001 -v
  SysTest run --suite performance --batch 3 --interval 60
  SysTest run --suite performance --device /dev/sda
  SysTest run --suite performance --test-dir /mapdata/ufs_test
  SysTest run --suite performance --config configs/ufs31_128GB.json
  SysTest run --all

View Information:
  SysTest list
  SysTest list --suite performance  # List tests in specific suite
  SysTest list --detail
  SysTest report --latest
  SysTest report --id SysTest_performance_20260409_090726
  SysTest report --list            # List all available reports
  SysTest report --latest --export-csv
  SysTest mode                    # View current test mode

Environment Management:
  SysTest check-env
  SysTest check-env --save-config
  SysTest check-env --no-save      # Skip saving configuration
  SysTest config --show
  SysTest config --device /dev/sda
  SysTest config --test-dir /mapdata/ufs_test
  SysTest config --reset

Compare Baselines:
  SysTest compare-baseline --baseline1 results/gold/ --baseline2 results/current/

Complete Workflow:
  SysTest check-env --save-config
  SysTest mode --set=development  # Set development mode for quick tests
  SysTest run --suite performance
  SysTest mode --set=production   # Switch to production mode for final validation
  SysTest run --suite performance
  SysTest report --latest
  SysTest compare-baseline --baseline1 results/gold/ --baseline2 results/current/
================================================================================
        """
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
    run_parser.add_argument('--suite', '-s', help='Test suite name (performance/qos)')
    run_parser.add_argument('--test', '-t', help='Single test item name')
    run_parser.add_argument('--all', '-a', action='store_true', help='Run all test suites')
    run_parser.add_argument('--device', '-d', default=None, help='Test device path (default from runtime.json)')
    run_parser.add_argument('--test-dir', '-tdir', default=None, help='Test file directory (default auto-select)')
    run_parser.add_argument('--output', '-o', default='./results', help='Output directory')
    run_parser.add_argument('--format', '-f', default='html,json,txt', help='Report format (html/json/txt/csv)')
    run_parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')
    run_parser.add_argument('--batch', '-b', type=int, default=1, help='Batch test count (default 1)')
    run_parser.add_argument('--interval', '-i', type=int, default=60, help='Batch test interval in seconds (default 60s)')
    run_parser.add_argument('--config', '-c', default=None, help='Load preset configuration (e.g., configs/ufs31_128GB.json)')
    run_parser.add_argument('--mode', '-m', choices=['development', 'production'], help='Test mode (overrides config file)')
    run_parser.add_argument('--export-csv', action='store_true', help='Export CSV format results')
    run_parser.set_defaults(func=cmd_run)

    list_parser = subparsers.add_parser('list',
        help='List available tests',
        description='List all available test suites and test items',
        epilog="""Examples:
  python3 bin/SysTest list

  python3 bin/SysTest list --suite performance

  python3 bin/SysTest list --detail
""")
    list_parser.add_argument('--detail', action='store_true', help='Show detailed information')
    list_parser.add_argument('--suite', '-s', help='Filter by suite name')
    list_parser.set_defaults(func=cmd_list)

    report_parser = subparsers.add_parser('report',
        help='Generate/view report',
        description='Generate or view test report',
        epilog="""Examples:
  python3 bin/SysTest report --latest

  python3 bin/SysTest report --id=SysTest_performance_20260407_103000

  python3 bin/SysTest report --latest --export-csv
""")
    report_parser.add_argument('--latest', action='store_true', help='View latest report')
    report_parser.add_argument('--id', help='Specify report ID')
    report_parser.add_argument('--list', action='store_true', help='List all available reports')
    report_parser.add_argument('--open', action='store_true', help='Open in browser')
    report_parser.add_argument('--export-csv', action='store_true', help='Export CSV format')
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
    mode_parser.add_argument('--set', choices=['development', 'production'], help='Set test mode')
    mode_parser.set_defaults(func=cmd_mode)

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    return args.func(args)

if __name__ == '__main__':
    sys.exit(main())
