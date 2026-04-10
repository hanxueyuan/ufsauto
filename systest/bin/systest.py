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

# Add project root to Python path
script_dir = Path(__file__).parent.absolute()
project_root = script_dir.parent
sys.path.insert(0, str(project_root))

from core.runner import TestRunner
from core.collector import ResultCollector
from core.reporter import ReportGenerator
from core.logger import get_logger, close_all_loggers


def cmd_run(args):
    """Execute tests"""
    import time
    from datetime import datetime

    # Generate test ID (script name + suite/test name + timestamp suffix)
    script_name = Path(__file__).stem  # SysTest
    name_suffix = ""
    if args.suite:
        name_suffix = f"_{args.suite}"
    elif args.test:
        name_suffix = f"_{args.test}"
    test_id = f"{script_name}{name_suffix}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

    # Initialize logging (separated by test ID)
    logger = get_logger(
        test_id=test_id,
        log_dir='logs',
        console_level=logging.DEBUG if args.verbose else logging.INFO,
        file_level=logging.DEBUG
    )

    # Load preset configuration (if any)
    if hasattr(args, 'config') and args.config:
        config_path = Path(args.config)
        if config_path.exists():
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    preset_config = json.load(f)
            except json.JSONDecodeError as e:
                logger.error(f"Invalid preset configuration file: {config_path}: {e}")
                return 2
            # Apply preset configuration
            if preset_config.get('device') and not args.device:
                args.device = preset_config['device']
            if preset_config.get('test_dir') and not args.test_dir:
                args.test_dir = preset_config['test_dir']
            logger.info(f"Loaded preset configuration: {args.config}")

    # Auto-load default runtime configuration
    default_config_path = project_root / 'config' / 'runtime.json'
    if default_config_path.exists():
        try:
            with open(default_config_path, 'r', encoding='utf-8') as f:
                default_config = json.load(f)
        except json.JSONDecodeError as e:
            logger.warning(f"Invalid default configuration file: {default_config_path}: {e} (continuing with empty config)")
            default_config = {}
        # Apply default configuration: only override if user hasn't specified
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

    # Batch test
    batch_results = []
    for i in range(args.batch):
        if args.batch > 1:
            logger.info(f"\n{'='*60}")
            logger.info(f"Batch test {i+1}/{args.batch}")
            logger.info(f"{'='*60}")

        # Determine suites to run
        suites_to_run = []
        if args.all:
            suites_to_run = ['performance', 'qos']
        elif args.suite:
            suites_to_run = [args.suite]
        elif args.test:
            # Single test, find所属 suite
            runner_tmp = TestRunner()
            for suite_name, tests in runner_tmp.list_suites().items():
                if args.test in tests:
                    suites_to_run = [suite_name]
                    break

        if not suites_to_run:
            logger.error("No test suite or test item specified")
            return 2

        # Execute each suite
        for suite_name in suites_to_run:
            # Initialize components
            runner = TestRunner(
                device=args.device,
                test_dir=args.test_dir,
                verbose=args.verbose
            )
            collector = ResultCollector(output_dir=args.output)
            reporter = ReportGenerator(template='default')

            # Execute test
            try:
                results = runner.run_suite(suite_name)

                # Collect results
                report_data = collector.collect(results, test_id=test_id, suite_name=suite_name, device=args.device)

                # Generate report
                report_formats = args.format.split(',') if hasattr(args, 'format') and args.format else ['html', 'json']

                # CSV export
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
                    # Close log
                    close_all_loggers()
                    return 2

        # Batch test interval
        if args.batch > 1 and i < args.batch - 1:
            logger.info(f"\nWaiting {args.interval}s before next round...")
            time.sleep(args.interval)

    # Batch test summary
    if args.batch > 1:
        logger.info("\n" + "=" * 60)
        logger.info(f"Batch Test Results Summary ({args.batch} rounds)")
        logger.info("=" * 60)
        for i, result in enumerate(batch_results, 1):
            summary = result['summary']
            logger.info(f"  Round {i}: {summary['passed']}/{summary['total']} passed ({summary['pass_rate']:.1f}%)")

        # Calculate overall pass rate
        total_tests = sum(r['summary']['total'] for r in batch_results)
        total_passed = sum(r['summary']['passed'] for r in batch_results)
        overall_pass_rate = (total_passed / total_tests * 100) if total_tests > 0 else 0
        logger.info("-" * 60)
        logger.info(f"  Total: {total_passed}/{total_tests} passed ({overall_pass_rate:.1f}%)")
        logger.info("=" * 60)

    # Close log
    close_all_loggers()

    # Return code: 1 if any failure
    has_failure = any(r['summary']['failed'] > 0 or r['summary']['errors'] > 0 for r in batch_results)
    return 1 if has_failure else 0


def cmd_list(args):
    """List available tests"""
    from core.runner import TestRunner

    runner = TestRunner()

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

    if args.latest:
        report_path = reporter.get_latest_report()
    elif args.id:
        report_path = reporter.get_report(args.id)
    else:
        print("Please specify --latest or --id")
        return 1

    if report_path:
        logger.info(f"Report path: {report_path}")
        print(f"\nReport path: {report_path}")
        if args.open:
            import webbrowser
            webbrowser.open(f'file://{report_path}')

        # CSV export
        if hasattr(args, 'export_csv') and args.export_csv:
            csv_path = f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            # Generate CSV from JSON result
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

    # Reset configuration
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

    # Set device path
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

    # Set test directory
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

    # Show configuration
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

    # Build command
    cmd = [sys.executable, str(check_script)]
    if args.report:
        cmd.extend(['--report', '--output', args.output])
    if args.no_save:
        cmd.append('--no-save')
    if args.verbose:
        cmd.append('-v')

    # Execute check
    result = subprocess.run(cmd)
    return result.returncode


def cmd_compare_baseline(args):
    """Performance baseline comparison"""
    import subprocess

    compare_script = script_dir / 'compare_baseline.py'

    if not compare_script.exists():
        print(f"Comparison script does not exist: {compare_script}")
        return 1

    # Build command
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

    # Execute comparison
    result = subprocess.run(cmd)

    # CSV export (if any)
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
  SysTest check-env --save-config              # First use: check environment and save config
  SysTest run --suite performance              # Run performance tests (development mode)
  SysTest run --all                            # Run all test suites (production mode)
  SysTest report --latest                      # View latest report

Execute Tests:
  SysTest run --suite performance              # Performance test suite
  SysTest run --suite qos                      # QoS test suite
  SysTest run --test t_perf_SeqReadBurst_001   # Single test
  SysTest run --test t_perf_SeqReadBurst_001 -v  # Single test (verbose)
  SysTest run --suite performance --batch 3 --interval 60  # Batch 3 times, 60s interval
  SysTest run --suite performance --device /dev/sda  # Custom device
  SysTest run --suite performance --test-dir /mapdata/ufs_test  # Custom test directory
  SysTest run --suite performance --config configs/ufs31_128GB.json  # Preset config
  SysTest run --all                            # Run all suites

View Information:
  SysTest list                                 # List all tests
  SysTest list --detail                        # Detailed information
  SysTest report --latest                      # View latest report
  SysTest report --id SysTest_performance_20260409_090726  # Specific report
  SysTest report --latest --export-csv         # Export CSV

Environment Management:
  SysTest check-env                            # Check environment
  SysTest check-env --save-config              # Save configuration
  SysTest config --show                        # Show configuration
  SysTest config --device /dev/sda             # Set device path
  SysTest config --test-dir /mapdata/ufs_test  # Set test directory
  SysTest config --reset                       # Reset configuration

Compare Baselines:
  SysTest compare-baseline --baseline1 results/gold/ --baseline2 results/current/

Complete Workflow:
  # Automotive-grade UFS 3.1 test flow
  SysTest check-env --save-config              # 1. Environment detection
  SysTest run --suite performance              # 2. Performance test
  SysTest run --suite qos                      # 3. QoS test
  SysTest report --latest                      # 4. View report
  SysTest compare-baseline --baseline1 results/gold/ --baseline2 results/current/  # 5. Compare
================================================================================
        """
    )

    subparsers = parser.add_subparsers(dest='command', help='Available commands')

    # run command
    run_parser = subparsers.add_parser('run',
        help='Execute tests',
        description='Execute UFS performance/reliability tests',
        epilog="""Examples:
  [Basic Usage]
  # Run full performance test suite
  python3 bin/SysTest run --suite=performance

  # Run QoS test suite (automotive-grade latency test)
  python3 bin/SysTest run --suite=qos

  # Run reliability test suite
  python3 bin/SysTest run --suite=reliability

  # Run all test suites
  python3 bin/SysTest run --all

  [Single Test]
  # Run single test item
  python3 bin/SysTest run --test=t_perf_SeqReadBurst_001

  # Run single test item (verbose output)
  python3 bin/SysTest run --test=t_perf_SeqReadBurst_001 -v

  [Batch Test]
  # Batch test 3 times, 60s interval
  python3 bin/SysTest run --suite=performance --batch=3 --interval=60

  [Specify Device and Directory]
  # Specify device path
  python3 bin/SysTest run --suite=performance --device=/dev/sda

  # Specify test directory
  python3 bin/SysTest run --suite=performance --test-dir=/mapdata/ufs_test

  # Specify both device and test directory
  python3 bin/SysTest run --suite=performance --device=/dev/sda --test-dir=/mapdata/ufs_test

  [Using Preset Configuration]
  # Use preset configuration (e.g., configs/ufs31_128GB.json)
  python3 bin/SysTest run --suite=performance --config=configs/ufs31_128GB.json

  # Use automotive-grade configuration
  python3 bin/SysTest run --suite=performance --config=configs/automotive_grade.json

  [Complete Examples]
  # Automotive-grade performance validation: batch 3 times + specify device
  python3 bin/SysTest run --suite=performance --batch=3 --device=/dev/sda

  # Full reliability test: all suites + verbose output
  python3 bin/SysTest run --all -v

  # Production environment test: use preset configuration
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
    run_parser.add_argument('--export-csv', action='store_true', help='Export CSV format results')
    run_parser.set_defaults(func=cmd_run)

    # list command
    list_parser = subparsers.add_parser('list',
        help='List available tests',
        description='List all available test suites and test items',
        epilog="""Examples:
  # List all test suites
  python3 bin/SysTest list

  # Show detailed information (including test item descriptions)
  python3 bin/SysTest list --detail
""")
    list_parser.add_argument('--detail', action='store_true', help='Show detailed information')
    list_parser.set_defaults(func=cmd_list)

    # report command
    report_parser = subparsers.add_parser('report',
        help='Generate/view report',
        description='Generate or view test report',
        epilog="""Examples:
  # View latest test report
  python3 bin/SysTest report --latest

  # View report by ID
  python3 bin/SysTest report --id=SysTest_performance_20260407_103000

  # Export CSV format results
  python3 bin/SysTest report --latest --export-csv
""")
    report_parser.add_argument('--latest', action='store_true', help='View latest report')
    report_parser.add_argument('--id', help='Specify report ID')
    report_parser.add_argument('--open', action='store_true', help='Open in browser')
    report_parser.add_argument('--export-csv', action='store_true', help='Export CSV format')
    report_parser.set_defaults(func=cmd_report)

    # config command
    config_parser = subparsers.add_parser('config',
        help='View/manage configuration',
        description='View or modify runtime configuration',
        epilog="""Examples:
  # Show current configuration content
  python3 bin/SysTest config --show

  # Set device path
  python3 bin/SysTest config --device=/dev/sda

  # Set test directory
  python3 bin/SysTest config --test-dir=/mapdata/ufs_test

  # Reset configuration to default
  python3 bin/SysTest config --reset
""")
    config_parser.add_argument('--show', action='store_true', help='Show configuration content')
    config_parser.add_argument('--reset', action='store_true', help='Reset configuration to default')
    config_parser.add_argument('--device', help='Set device path')
    config_parser.add_argument('--test-dir', help='Set test directory')
    config_parser.set_defaults(func=cmd_config)

    # check-env command
    check_env_parser = subparsers.add_parser('check-env',
        help='Check environment and generate configuration',
        description='Detect UFS device and test directory, auto-generate runtime.json configuration',
        epilog="""Examples:
  # Check environment and auto-save configuration (default behavior)
  python3 bin/SysTest check-env

  # Generate JSON report
  python3 bin/SysTest check-env --report

  # Verbose output mode
  python3 bin/SysTest check-env -v

  # Only detect, do not save configuration
  python3 bin/SysTest check-env --no-save
""")
    check_env_parser.add_argument('--report', action='store_true', help='Generate JSON report')
    check_env_parser.add_argument('--output', default='env_check_report.json', help='Report output path')
    check_env_parser.add_argument('--no-save', action='store_true', help='Do not save configuration file (default will auto-save runtime.json)')
    check_env_parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')
    check_env_parser.set_defaults(func=cmd_check_env)

    # compare-baseline command
    compare_parser = subparsers.add_parser('compare-baseline',
        help='Compare performance baselines',
        description='Compare performance differences between two sets of test results',
        epilog="""Examples:
  # Compare development board and CI/CD test results
  python3 bin/SysTest compare-baseline --dev=results/SysTest_perf_dev --ci=results/SysTest_perf_ci

  # Compare two baseline directories
  python3 bin/SysTest compare-baseline --baseline1=baseline_v1 --baseline2=baseline_v2

  # Set allowed difference threshold to 15%
  python3 bin/SysTest compare-baseline --baseline1=baseline_v1 --baseline2=baseline_v2 --threshold=0.15

  # Output report to specified path
  python3 bin/SysTest compare-baseline --baseline1=baseline_v1 --baseline2=baseline_v2 --output=comparison_report.json
""")
    compare_parser.add_argument('--dev', help='Development board test result directory')
    compare_parser.add_argument('--ci', help='CI/CD test result directory')
    compare_parser.add_argument('--baseline1', help='First baseline directory')
    compare_parser.add_argument('--baseline2', help='Second baseline directory')
    compare_parser.add_argument('--threshold', type=float, default=0.10, help='Allowed difference ratio (default 0.10)')
    compare_parser.add_argument('--output', help='Report output path')
    compare_parser.set_defaults(func=cmd_compare_baseline)

    # Parse arguments
    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    # Execute command
    return args.func(args)


if __name__ == '__main__':
    sys.exit(main())
