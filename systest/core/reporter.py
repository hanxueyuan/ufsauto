#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Report Generator - Report Generator
Responsible for generating HTML/JSON/PDF test reports
"""

import json
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional
from string import Template

logger = logging.getLogger(__name__)


class ReportGenerator:
    """Test report generator"""

    # HTML report template (pure standard library, no external dependencies)
    HTML_TEMPLATE = Template('''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>UFS System Test Report - $test_id</title>
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif; margin: 40px; background: #f5f5f5; }
        .container { max-width: 1200px; margin: 0 auto; background: white; padding: 30px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        h1 { color: #333; border-bottom: 3px solid #007bff; padding-bottom: 10px; }
        h2 { color: #555; margin-top: 30px; }
        .summary { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; margin: 20px 0; }
        .summary-card { padding: 20px; border-radius: 8px; text-align: center; }
        .summary-card.total { background: #e3f2fd; }
        .summary-card.passed { background: #e8f5e9; }
        .summary-card.failed { background: #ffebee; }
        .summary-card .value { font-size: 36px; font-weight: bold; }
        .summary-card .label { color: #666; margin-top: 5px; }
        .pass-rate { font-size: 24px; font-weight: bold; }
        .pass-rate.good { color: #2e7d32; }
        .pass-rate.bad { color: #c62828; }
        table { width: 100%; border-collapse: collapse; margin: 20px 0; }
        th, td { padding: 12px; text-align: left; border-bottom: 1px solid #ddd; }
        th { background: #f8f9fa; font-weight: 600; }
        tr:hover { background: #f8f9fa; }
        .status { padding: 4px 12px; border-radius: 4px; font-weight: 500; }
        .status.PASS { background: #e8f5e9; color: #2e7d32; }
        .status.FAIL { background: #ffebee; color: #c62828; }
        .status.ERROR { background: #fff3e0; color: #ef6c00; }
        .status.DRY-RUN-PASS { background: #e8f5e9; color: #2e7d32; }
        .failure-analysis { background: #fff3e0; padding: 20px; border-radius: 8px; margin: 20px 0; }
        .failure-analysis h3 { color: #e65100; margin-top: 0; }
        .metrics { font-family: monospace; background: #f8f9fa; padding: 2px 6px; border-radius: 3px; }
        .footer { margin-top: 40px; padding-top: 20px; border-top: 1px solid #ddd; color: #666; font-size: 14px; }
    </style>
</head>
<body>
    <div class="container">
        <h1>UFS System Test Report</h1>

        <div class="meta">
            <p><strong>Test ID:</strong> $test_id</p>
            <p><strong>Time:</strong> $timestamp</p>
            <p><strong>Suite:</strong> $suite</p>
            <p><strong>Device:</strong> $device</p>
        </div>

        <h2>Summary Statistics</h2>
        <div class="summary">
            <div class="summary-card total">
                <div class="value">$total</div>
                <div class="label">Total</div>
            </div>
            <div class="summary-card passed">
                <div class="value">$passed</div>
                <div class="label">Passed</div>
            </div>
            <div class="summary-card failed">
                <div class="value">$failed</div>
                <div class="label">Failed</div>
            </div>
            <div class="summary-card">
                <div class="pass-rate $pass_rate_class">$pass_rate%</div>
                <div class="label">Pass Rate</div>
            </div>
        </div>

        <h2>Test Results</h2>
        <table>
            <thead>
                <tr>
                    <th>Test</th>
                    <th>Status</th>
                    <th>Duration</th>
                    <th>Key Metrics</th>
                </tr>
            </thead>
            <tbody>
                $test_rows
            </tbody>
        </table>

        $failure_section

        <div class="footer">
            <p>UFS System Test Framework SysTest | Generated: $gen_time</p>
        </div>
    </div>
</body>
</html>''')

    def __init__(self, template: str = 'default'):
        self.template = template
        self.results_dir = Path('./results')

    def generate(
        self,
        report_data: Dict[str, Any],
        output_dir: Optional[str] = None,
        formats: Optional[List[str]] = None
    ) -> str:
        """
        Generate report

        Args:
            report_data: Report data
            output_dir: Output directory
            formats: Report format list ['html', 'json', 'pdf']

        Returns:
            Main report file path
        """
        if formats is None:
            formats = ['html', 'json']

        if output_dir:
            output_path = Path(output_dir) / report_data['test_id']
        else:
            output_path = self.results_dir / report_data['test_id']

        output_path.mkdir(parents=True, exist_ok=True)

        main_report = None

        for fmt in formats:
            if fmt == 'html':
                report_path = self._generate_html(report_data, output_path)
                if main_report is None:
                    main_report = report_path
            elif fmt == 'json':
                report_path = self._generate_json(report_data, output_path)
                if main_report is None:
                    main_report = report_path

        logger.info(f"Report generated: {main_report}")
        return str(main_report)

    def _generate_html(self, report_data: Dict[str, Any], output_path: Path) -> Path:
        """Generate HTML report"""
        # Prepare template variables
        pass_rate = report_data['summary']['pass_rate']

        test_rows = []
        failures = []

        for result in report_data['test_cases']:
            status = result.get('status', 'UNKNOWN')
            # DRY-RUN-PASS displayed as PASS style
            status_class = status if status in ['PASS', 'FAIL', 'ERROR', 'DRY-RUN-PASS'] else 'ERROR'
            if status_class == 'DRY-RUN-PASS':
                status_class = 'PASS'

            # Extract key metrics
            metrics = result.get('metrics', {})
            metrics_str = self._format_metrics(metrics)

            row = f'''<tr>
                <td>{result['name']}</td>
                <td><span class="status {status_class}">{status}</span></td>
                <td>{result.get('duration', 0):.2f}s</td>
                <td>{metrics_str}</td>
            </tr>'''
            test_rows.append(row)

            # Collect failures
            if status == 'FAIL':
                failures.append(self._create_failure_analysis(result))

        # Failure section
        if failures:
            failure_section = '<h2>Failure Analysis</h2>' + '\n'.join(failures)
        else:
            failure_section = ''

        # Fill template
        html_content = self.HTML_TEMPLATE.substitute(
            test_id=report_data['test_id'],
            timestamp=report_data['timestamp'],
            suite=report_data.get('suite', '-'),
            device=report_data.get('device', '-'),
            total=report_data['summary']['total'],
            passed=report_data['summary']['passed'],
            failed=report_data['summary']['failed'],
            pass_rate=f'{pass_rate:.1f}',
            pass_rate_class='good' if pass_rate >= 90 else 'bad',
            test_rows='\n'.join(test_rows),
            failure_section=failure_section,
            gen_time=datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        )

        # Save file
        report_path = output_path / 'report.html'
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(html_content)

        logger.debug(f"HTML report saved: {report_path}")
        return report_path

    def _generate_json(self, report_data: Dict[str, Any], output_path: Path) -> Path:
        """Generate JSON report"""
        report_path = output_path / 'report.json'
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(report_data, f, indent=2, ensure_ascii=False)

        logger.debug(f"JSON report saved: {report_path}")
        return report_path

    def _format_metrics(self, metrics: Dict[str, Any]) -> str:
        """Format metrics display"""
        if not metrics:
            return '-'

        parts = []
        for key, value in metrics.items():
            if isinstance(value, dict):
                val = value.get('value', '-')
                unit = value.get('unit', '')
                parts.append(f'{key}: {val} {unit}')
            else:
                parts.append(f'{key}: {value}')

        return '<br>'.join(parts[:3])  # Max 3 metrics

    def _create_failure_analysis(self, result: Dict[str, Any]) -> str:
        """Create failure analysis HTML"""
        test_name = result.get('name', 'unknown_test')
        status = result.get('status', 'UNKNOWN')
        duration = float(result.get('duration') or 0.0)  # Handle None value

        # Collect failure details
        failures = result.get('failures', [])
        error = result.get('error', '')
        reason = result.get('reason', '')
        fail_mode = result.get('fail_mode', '')

        # Build failure details list
        failure_items = []
        if error:
            failure_items.append(f'Error: {error}')
        if reason:
            failure_items.append(f'Reason: {reason}')
        if fail_mode == 'stop':
            failure_items.append('Fail-Stop: Test was forcibly terminated')

        for f in failures:
            check = f.get('check', 'Unknown check')
            expected = f.get('expected', '-')
            actual = f.get('actual', '-')
            failure_reason = f.get('reason', '')
            failure_items.append(f'{check}: Expected {expected}, Actual {actual}' + (f' ({failure_reason})' if failure_reason else ''))

        if not failure_items:
            failure_items.append('See log file for detailed failure reason')

        # Build suggestions list
        suggestions = []
        if 'permission' in (error + reason).lower():
            suggestions.append('Check user permissions, use sudo or join disk group')
        if 'not found' in (error + reason).lower() or 'no such' in (error + reason).lower():
            suggestions.append('Verify device path is correct, run check-env detection')
        if 'space' in (error + reason).lower():
            suggestions.append('Free up disk space or specify --test-dir to another partition')
        if 'timeout' in (error + reason).lower():
            suggestions.append('Check device response, view dmesg logs')
        if not suggestions:
            suggestions.extend([
                'Check test log file to locate specific problem',
                'Check test environment and device status',
                'Re-run test to confirm if reproducible'
            ])

        failure_html = '<br>'.join(f'<li>{item}</li>' for item in failure_items)
        suggestion_html = '<br>'.join(f'<li>{item}</li>' for item in suggestions)

        return f'''<div class="failure-analysis">
            <h3>{test_name}</h3>
            <p><strong>Status:</strong> <span class="status {status}">{status}</span></p>
            <p><strong>Duration:</strong> {duration:.2f}s</p>
            <p><strong>Failure Details:</strong></p>
            <ul>
                {failure_html}
            </ul>
            <p><strong>Suggested Actions:</strong></p>
            <ul>
                {suggestion_html}
            </ul>
        </div>'''

    def get_latest_report(self) -> Optional[str]:
        """Get latest report path"""
        if not self.results_dir.exists():
            return None

        test_dirs = [d for d in self.results_dir.iterdir() if d.is_dir()]
        if not test_dirs:
            return None

        latest = max(test_dirs, key=lambda d: d.stat().st_mtime)
        report_path = latest / 'report.html'

        return str(report_path) if report_path.exists() else None

    def get_report(self, test_id: str) -> Optional[str]:
        """Get specified test report"""
        report_path = self.results_dir / test_id / 'report.html'
        return str(report_path) if report_path.exists() else None
