#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
历史数据对比模块

功能：
- 读取 reports/ 目录下的历史报告
- 提取性能数据
- 对比当前测试和历史测试
- 生成对比数据（JSON 格式）
- 保存到 reports/history_comparison.json

对比内容：
- 带宽变化趋势
- IOPS 变化趋势
- 延迟变化趋势
- 达标率变化
"""

import json
import os
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional


class HistoryComparator:
    """历史数据对比器"""

    def __init__(self, reports_dir: Path = None):
        self.reports_dir = reports_dir or Path(__file__).parent / 'reports'
        self.history_data = []
        self.comparison_result = {}

    def load_history_reports(self, max_reports: int = 10) -> List[Dict]:
        """
        加载历史报告

        Args:
            max_reports: 最多加载多少个历史报告

        Returns:
            历史报告列表
        """
        if not self.reports_dir.exists():
            print(f"⚠️  报告目录不存在：{self.reports_dir}")
            return []

        # 查找所有 Markdown 报告文件
        report_files = sorted(
            self.reports_dir.glob('*.md'),
            key=lambda x: x.stat().st_mtime,
            reverse=True
        )[:max_reports]

        self.history_data = []

        for report_file in report_files:
            try:
                data = self._parse_report(report_file)
                if data:
                    self.history_data.append(data)
            except Exception as e:
                print(f"⚠️  解析报告失败 {report_file}: {e}")

        # 按时间排序（旧的在前）
        self.history_data.sort(key=lambda x: x.get('timestamp', ''))

        return self.history_data

    def _parse_report(self, report_path: Path) -> Optional[Dict]:
        """
        解析报告文件，提取性能数据

        Args:
            report_path: 报告文件路径

        Returns:
            提取的性能数据字典
        """
        try:
            with open(report_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # 提取基本信息
            data = {
                'report_file': report_path.name,
                'timestamp': datetime.fromtimestamp(
                    report_path.stat().st_mtime
                ).isoformat(),
                'test_cases': []
            }

            # 简单解析 Markdown 表格中的性能数据
            # 查找类似 "seq_read_burst | ✅ PASS | 2100.5 | 15000 | 120.5" 的行
            lines = content.split('\n')
            for line in lines:
                if '|' in line and ('PASS' in line or 'FAIL' in line or 'WARNING' in line):
                    parts = [p.strip() for p in line.split('|')]
                    if len(parts) >= 5:
                        try:
                            test_case = {
                                'name': parts[0].strip(),
                                'status': parts[1].strip(),
                                'bandwidth_mbps': float(parts[2].replace('MB/s', '').replace('-', '0')) if parts[2] not in ['-', ''] else 0,
                                'iops': float(parts[3].replace('-', '0')) if parts[3] not in ['-', ''] else 0,
                                'latency_us': float(parts[4].replace('μs', '').replace('-', '0')) if parts[4] not in ['-', ''] else 0,
                            }
                            data['test_cases'].append(test_case)
                        except (ValueError, IndexError):
                            continue

            return data

        except Exception as e:
            print(f"解析报告 {report_path} 失败：{e}")
            return None

    def compare_with_current(self, current_results: List[Dict]) -> Dict[str, Any]:
        """
        对比当前测试和历史数据

        Args:
            current_results: 当前测试结果列表

        Returns:
            对比结果字典
        """
        if not self.history_data:
            print("⚠️  没有历史数据，跳过对比")
            return {
                'status': 'no_history',
                'message': '没有可用的历史数据',
                'current_results': current_results
            }

        comparison = {
            'timestamp': datetime.now().isoformat(),
            'history_count': len(self.history_data),
            'current_results': current_results,
            'trends': {},
            'summary': {}
        }

        # 按测试用例名称分组历史数据
        history_by_test = {}
        for hist_report in self.history_data:
            for test_case in hist_report.get('test_cases', []):
                test_name = test_case.get('name')
                if test_name not in history_by_test:
                    history_by_test[test_name] = []
                history_by_test[test_name].append(test_case)

        # 对比每个测试用例
        for current_test in current_results:
            test_name = current_test.get('name')
            if test_name in history_by_test:
                history_list = history_by_test[test_name]
                
                # 计算历史平均值
                hist_bw_values = [t.get('bandwidth_mbps', 0) for t in history_list if t.get('bandwidth_mbps', 0) > 0]
                hist_iops_values = [t.get('iops', 0) for t in history_list if t.get('iops', 0) > 0]
                hist_lat_values = [t.get('latency_us', 0) for t in history_list if t.get('latency_us', 0) > 0]

                current_bw = current_test.get('bandwidth_mbps', 0)
                current_iops = current_test.get('iops', 0)
                current_lat = current_test.get('avg_latency_us', 0)

                trend_data = {
                    'test_name': test_name,
                    'current': {
                        'bandwidth_mbps': current_bw,
                        'iops': current_iops,
                        'latency_us': current_lat
                    },
                    'history_avg': {
                        'bandwidth_mbps': sum(hist_bw_values) / len(hist_bw_values) if hist_bw_values else 0,
                        'iops': sum(hist_iops_values) / len(hist_iops_values) if hist_iops_values else 0,
                        'latency_us': sum(hist_lat_values) / len(hist_lat_values) if hist_lat_values else 0
                    },
                    'history_min': {
                        'bandwidth_mbps': min(hist_bw_values) if hist_bw_values else 0,
                        'iops': min(hist_iops_values) if hist_iops_values else 0,
                        'latency_us': min(hist_lat_values) if hist_lat_values else 0
                    },
                    'history_max': {
                        'bandwidth_mbps': max(hist_bw_values) if hist_bw_values else 0,
                        'iops': max(hist_iops_values) if hist_iops_values else 0,
                        'latency_us': max(hist_lat_values) if hist_lat_values else 0
                    },
                    'change_percent': {
                        'bandwidth_mbps': self._calc_change(current_bw, hist_bw_values),
                        'iops': self._calc_change(current_iops, hist_iops_values),
                        'latency_us': self._calc_change(current_lat, hist_lat_values)
                    }
                }

                comparison['trends'][test_name] = trend_data

        # 生成摘要
        comparison['summary'] = self._generate_summary(comparison['trends'])

        self.comparison_result = comparison
        return comparison

    def _calc_change(self, current: float, history_values: List[float]) -> float:
        """计算变化百分比"""
        if not history_values:
            return 0.0
        avg = sum(history_values) / len(history_values)
        if avg == 0:
            return 0.0
        return ((current - avg) / avg) * 100

    def _generate_summary(self, trends: Dict) -> Dict[str, Any]:
        """生成对比摘要"""
        if not trends:
            return {'message': '无对比数据'}

        total_tests = len(trends)
        improved = 0
        degraded = 0
        stable = 0

        for test_name, trend in trends.items():
            bw_change = trend['change_percent'].get('bandwidth_mbps', 0)
            # 带宽提升 >5% 算改进，下降 >5% 算退化
            if bw_change > 5:
                improved += 1
            elif bw_change < -5:
                degraded += 1
            else:
                stable += 1

        return {
            'total_tests': total_tests,
            'improved': improved,
            'degraded': degraded,
            'stable': stable,
            'improvement_rate': round(improved / total_tests * 100, 1) if total_tests > 0 else 0
        }

    def save_comparison(self, output_path: Path = None) -> Path:
        """
        保存对比结果到 JSON 文件

        Args:
            output_path: 输出文件路径

        Returns:
            保存的文件路径
        """
        if not self.comparison_result:
            raise ValueError("没有对比结果，请先调用 compare_with_current()")

        if output_path is None:
            output_path = self.reports_dir / 'history_comparison.json'

        # 确保目录存在
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(self.comparison_result, f, indent=2, ensure_ascii=False)

        print(f"✓ 历史对比数据已保存：{output_path}")
        return output_path

    def print_summary(self):
        """打印对比摘要"""
        if not self.comparison_result:
            print("没有对比数据")
            return

        print("\n" + "=" * 70)
        print("  历史数据对比摘要")
        print("=" * 70)

        summary = self.comparison_result.get('summary', {})
        print(f"测试总数：{summary.get('total_tests', 0)}")
        print(f"改进：{summary.get('improved', 0)}")
        print(f"退化：{summary.get('degraded', 0)}")
        print(f"稳定：{summary.get('stable', 0)}")
        print(f"改进率：{summary.get('improvement_rate', 0)}%")

        print("\n详细趋势:")
        print("-" * 70)
        print(f"{'测试用例':<25} {'带宽变化':<15} {'IOPS 变化':<15} {'延迟变化':<15}")
        print("-" * 70)

        for test_name, trend in self.comparison_result.get('trends', {}).items():
            bw_change = trend['change_percent'].get('bandwidth_mbps', 0)
            iops_change = trend['change_percent'].get('iops', 0)
            lat_change = trend['change_percent'].get('latency_us', 0)

            bw_str = f"{bw_change:+.1f}%"
            iops_str = f"{iops_change:+.1f}%"
            lat_str = f"{lat_change:+.1f}%"

            print(f"{test_name:<25} {bw_str:<15} {iops_str:<15} {lat_str:<15}")

        print("=" * 70)


def main():
    """主函数 - 演示用法"""
    print("历史数据对比模块")
    print("=" * 70)

    comparator = HistoryComparator()

    # 加载历史报告
    print("加载历史报告...")
    history = comparator.load_history_reports(max_reports=10)
    print(f"找到 {len(history)} 份历史报告")

    # 示例当前数据（实际使用时从测试结果获取）
    current_results = [
        {
            'name': 'seq_read_burst',
            'bandwidth_mbps': 2150.5,
            'iops': 15200,
            'avg_latency_us': 118.5
        },
        {
            'name': 'seq_write_burst',
            'bandwidth_mbps': 1850.3,
            'iops': 14800,
            'avg_latency_us': 125.2
        }
    ]

    # 对比
    print("\n对比当前测试和历史数据...")
    comparison = comparator.compare_with_current(current_results)

    # 保存
    comparator.save_comparison()

    # 打印摘要
    comparator.print_summary()


if __name__ == '__main__':
    main()
