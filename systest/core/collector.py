#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Result Collector - Result Collector
Responsible for collecting test results, generating standard data formats, and saving raw data
"""

import json
import logging
import shutil
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)


class ResultCollector:
    """Test result collector"""

    def __init__(self, output_dir: str = './results'):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"Result output directory: {self.output_dir.absolute()}")

    def collect(
        self,
        results: List[Dict[str, Any]],
        test_id: Optional[str] = None,
        suite_name: Optional[str] = None,
        device: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Collect test results

        Args:
            results: Test results list
            test_id: Test ID (uses timestamp by default)
            suite_name: Test suite name
            device: Test device
            metadata: Additional metadata

        Returns:
            Complete report data structure
        """
        if test_id is None:
            test_id = f"SysTest_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        # Create test output directory
        test_dir = self.output_dir / test_id
        test_dir.mkdir(parents=True, exist_ok=True)

        # Calculate summary statistics
        total = len(results)
        passed = sum(1 for r in results if r.get('status') in ['PASS', 'DRY-RUN-PASS'])
        failed = sum(1 for r in results if r.get('status') == 'FAIL')
        errors = sum(1 for r in results if r.get('status') == 'ERROR')
        pass_rate = (passed / total * 100) if total > 0 else 0

        # Build report data
        report_data = {
            'test_id': test_id,
            'timestamp': datetime.now().isoformat(),
            'suite': suite_name,
            'device': device,
            'test_cases': results,
            'summary': {
                'total': total,
                'passed': passed,
                'failed': failed,
                'errors': errors,
                'pass_rate': pass_rate
            },
            'metadata': metadata or {}
        }

        # Save JSON results
        json_path = test_dir / 'results.json'
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(report_data, f, indent=2, ensure_ascii=False)
        logger.debug(f"Results saved: {json_path}")

        # Save detailed log for each test case
        for result in results:
            if 'log_file' in result:
                log_src = Path(result['log_file'])
                log_size = 0
                # Get file size in advance for error handling
                if log_src.exists():
                    try:
                        log_size = log_src.stat().st_size
                    except Exception:
                        pass

                try:
                    if log_src.exists():
                        log_dst = test_dir / f"{result['name']}.log"

                        # Large file copy progress notification
                        if log_size > 100 * 1024 * 1024:  # > 100MB
                            logger.info(f"Copying large log file: {result['name']} ({log_size / 1024 / 1024:.1f} MB)")
                            logger.info(f"   Target: {log_dst}")

                        shutil.copy2(log_src, log_dst)
                        logger.debug(f"Log copied: {result['name']} ({log_size / 1024 / 1024:.1f} MB)")
                except Exception as e:
                    # Don't get file size again in error handling, use previously obtained value
                    if log_size > 500 * 1024 * 1024:  # > 500MB
                        logger.warning(f"Large log file copy failed {result['name']} ({log_size / 1024 / 1024:.1f} MB): {e}")
                        logger.warning(f"File is large, copy may need more space or time")
                        logger.warning(f"Manual cleanup: rm {log_dst}")
                    else:
                        logger.warning(f"Log file copy failed {result['name']} ({log_size / 1024 / 1024:.1f} MB): {e}")
                    logger.warning(f"Recommendation: Manually copy or delete large log files to free space")
                    # Clean up partially created files
                    if 'log_dst' in locals() and log_dst.exists():
                        try:
                            log_dst.unlink()
                        except Exception:
                            pass
                # Continue processing other results, don't interrupt entire flow

        # Save summary information
        summary_path = test_dir / 'summary.txt'
        self._save_summary(summary_path, report_data)

        logger.info(f"Test {test_id} results summary: {passed}/{total} passed ({pass_rate:.1f}%)")

        return report_data

    def _save_summary(self, path: Path, report_data: Dict[str, Any]):
        """Save text format summary"""
        lines = [
            "=" * 60,
            "UFS System Test Report",
            "=" * 60,
            "",
            f"Test ID: {report_data['test_id']}",
            f"Time: {report_data['timestamp']}",
            f"Suite: {report_data['suite']}",
            f"Device: {report_data['device']}",
            "",
            "-" * 60,
            "Summary Statistics",
            "-" * 60,
            f"Total: {report_data['summary']['total']} items",
            f"Passed: {report_data['summary']['passed']} items",
            f"Failed: {report_data['summary']['failed']} items",
            f"Errors: {report_data['summary']['errors']} items",
            f"Pass Rate: {report_data['summary']['pass_rate']:.1f}%",
            "",
            "-" * 60,
            "Test Results",
            "-" * 60,
        ]

        for result in report_data['test_cases']:
            status_icon = '[PASS]' if result['status'] == 'PASS' else '[FAIL]' if result['status'] == 'FAIL' else '[ERROR]'
            lines.append(f"{status_icon} {result['name']}: {result['status']} ({result.get('duration', 0):.2f}s)")

        lines.append("")
        lines.append("=" * 60)

        with open(path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines))

        logger.debug(f"Summary saved: {path}")

    def get_latest_test_id(self) -> Optional[str]:
        """Get latest test ID"""
        test_dirs = [d for d in self.output_dir.iterdir() if d.is_dir()]
        if not test_dirs:
            return None

        latest = max(test_dirs, key=lambda d: d.stat().st_mtime)
        return latest.name

    def load_results(self, test_id: str) -> Optional[Dict[str, Any]]:
        """Load results for specified test"""
        json_path = self.output_dir / test_id / 'results.json'

        if not json_path.exists():
            logger.warning(f"Results file does not exist: {json_path}")
            return None

        with open(json_path, 'r', encoding='utf-8') as f:
            return json.load(f)

    def list_tests(self) -> List[Dict[str, Any]]:
        """List all test results"""
        tests = []

        for test_dir in sorted(self.output_dir.iterdir(), key=lambda d: d.stat().st_mtime, reverse=True):
            if not test_dir.is_dir():
                continue

            json_path = test_dir / 'results.json'
            if not json_path.exists():
                continue

            try:
                with open(json_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    tests.append({
                        'test_id': test_dir.name,
                        'timestamp': data.get('timestamp', ''),
                        'suite': data.get('suite', ''),
                        'pass_rate': data['summary']['pass_rate'],
                        'total': data['summary']['total'],
                        'passed': data['summary']['passed']
                    })
            except Exception as e:
                logger.warning(f"Failed to load test results {test_dir.name}: {e}")

        return tests
