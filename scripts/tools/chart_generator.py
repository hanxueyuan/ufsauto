#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
图表生成模块

功能：
- 使用 matplotlib 生成图表
- 性能对比柱状图（目标 vs 实际）
- 趋势折线图（多次测试对比）
- 达标率饼图
- 保存到 reports/charts/ 目录
"""

import json
import os
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional

matplotlib = None
plt = None

def _ensure_matplotlib():
    """确保 matplotlib 已导入"""
    global matplotlib, plt
    if matplotlib is None:
        try:
            import matplotlib
            import matplotlib.pyplot as plt
            matplotlib.use('Agg')
            return True
        except ImportError:
            print("⚠️  matplotlib 未安装，无法生成图表")
            print("   安装命令：pip install matplotlib")
            return False
    return True

class ChartGenerator:
    """图表生成器"""

    def __init__(self, output_dir: Path = None):
        self.output_dir = output_dir or Path(__file__).parent / 'reports' / 'charts'
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.generated_charts = []

    def generate_performance_bar_chart(
        self,
        test_results: List[Dict],
        target_config: Dict = None,
        filename: str = None
    ) -> Optional[Path]:
        """
        生成性能对比柱状图（目标 vs 实际）

        Args:
            test_results: 测试结果列表，每项包含 name, bandwidth_mbps, iops 等
            target_config: 目标配置，包含 target_bandwidth_mbps, target_iops 等
            filename: 输出文件名

        Returns:
            生成的图表文件路径
        """
        if not _ensure_matplotlib():
            return None

        if not test_results:
            print("⚠️  没有测试数据，跳过图表生成")
            return None

        import matplotlib.pyplot as plt
        import numpy as np

        test_names = [t['name'] for t in test_results]
        bandwidths = [t.get('bandwidth_mbps', 0) for t in test_results]
        iops_list = [t.get('iops', 0) for t in test_results]

        fig, ax1 = plt.subplots(figsize=(12, 6))

        x = np.arange(len(test_names))
        width = 0.35

        bars1 = ax1.bar(x - width/2, bandwidths, width, label='带宽 (MB/s)', color='#4CAF50')
        ax1.set_xlabel('测试用例')
        ax1.set_ylabel('带宽 (MB/s)', color='#4CAF50')
        ax1.tick_params(axis='y', labelcolor='#4CAF50')
        ax1.set_ylim(0, max(bandwidths) * 1.2 if bandwidths else 100)

        if target_config and 'target_bandwidth_mbps' in target_config:
            target_bw = target_config['target_bandwidth_mbps']
            ax1.axhline(y=target_bw, color='red', linestyle='--', label=f'目标带宽 ({target_bw} MB/s)')

        ax2 = ax1.twinx()
        bars2 = ax2.bar(x + width/2, iops_list, width, label='IOPS', color='#2196F3')
        ax2.set_ylabel('IOPS', color='#2196F3')
        ax2.tick_params(axis='y', labelcolor='#2196F3')
        ax2.set_ylim(0, max(iops_list) * 1.2 if iops_list else 1000)

        if target_config and 'target_iops' in target_config:
            target_iops = target_config['target_iops']
            ax2.axhline(y=target_iops, color='orange', linestyle='--', label=f'目标 IOPS ({target_iops})')

        ax1.set_xticks(x)
        ax1.set_xticklabels(test_names, rotation=45, ha='right')

        lines1, labels1 = ax1.get_legend_handles_labels()
        lines2, labels2 = ax2.get_legend_handles_labels()
        ax1.legend(lines1 + lines2, labels1 + labels2, loc='upper left')

        plt.title('性能对比：目标 vs 实际', fontsize=14, fontweight='bold')
        fig.tight_layout()

        if filename is None:
            filename = f'performance_comparison_{datetime.now().strftime("%Y%m%d_%H%M%S")}.png'
        output_path = self.output_dir / filename
        plt.savefig(output_path, dpi=150, bbox_inches='tight')
        plt.close()

        self.generated_charts.append(output_path)
        print(f"✓ 性能对比柱状图已保存：{output_path}")
        return output_path

    def generate_trend_line_chart(
        self,
        history_comparison: Dict,
        filename: str = None
    ) -> Optional[Path]:
        """
        生成趋势折线图（多次测试对比）

        Args:
            history_comparison: 历史对比数据（来自 history_comparison.py）
            filename: 输出文件名

        Returns:
            生成的图表文件路径
        """
        if not _ensure_matplotlib():
            return None

        if not history_comparison or 'trends' not in history_comparison:
            print("⚠️  没有历史对比数据，跳过趋势图生成")
            return None

        import matplotlib.pyplot as plt

        trends = history_comparison['trends']

        if not trends:
            print("⚠️  趋势数据为空")
            return None

        test_names = list(trends.keys())
        current_bw = [trends[t]['current']['bandwidth_mbps'] for t in test_names]
        hist_avg_bw = [trends[t]['history_avg']['bandwidth_mbps'] for t in test_names]
        hist_min_bw = [trends[t]['history_min']['bandwidth_mbps'] for t in test_names]
        hist_max_bw = [trends[t]['history_max']['bandwidth_mbps'] for t in test_names]

        fig, ax = plt.subplots(figsize=(12, 6))

        x = range(len(test_names))

        ax.fill_between(x, hist_min_bw, hist_max_bw, alpha=0.3, color='gray', label='历史范围')

        ax.plot(x, hist_avg_bw, 'o--', color='blue', label='历史平均', linewidth=2, markersize=8)

        ax.plot(x, current_bw, 's-', color='red', label='当前测试', linewidth=2, markersize=8)

        ax.set_xlabel('测试用例')
        ax.set_ylabel('带宽 (MB/s)')
        ax.set_title('性能趋势对比：历史 vs 当前', fontsize=14, fontweight='bold')
        ax.set_xticks(x)
        ax.set_xticklabels(test_names, rotation=45, ha='right')
        ax.legend()
        ax.grid(True, alpha=0.3)

        fig.tight_layout()

        if filename is None:
            filename = f'trend_comparison_{datetime.now().strftime("%Y%m%d_%H%M%S")}.png'
        output_path = self.output_dir / filename
        plt.savefig(output_path, dpi=150, bbox_inches='tight')
        plt.close()

        self.generated_charts.append(output_path)
        print(f"✓ 趋势折线图已保存：{output_path}")
        return output_path

    def generate_pass_rate_pie_chart(
        self,
        test_results: List[Dict],
        filename: str = None
    ) -> Optional[Path]:
        """
        生成达标率饼图

        Args:
            test_results: 测试结果列表
            filename: 输出文件名

        Returns:
            生成的图表文件路径
        """
        if not _ensure_matplotlib():
            return None

        if not test_results:
            print("⚠️  没有测试数据，跳过饼图生成")
            return None

        import matplotlib.pyplot as plt

        status_counts = {}
        for result in test_results:
            status = result.get('status', 'UNKNOWN')
            status_counts[status] = status_counts.get(status, 0) + 1

        labels = []
        sizes = []
        colors = []

        status_colors = {
            'PASS': '#4CAF50',
            'WARNING': '#FFC107',
            'FAIL': '#F44336',
            'ERROR': '#9C27B0',
            'TIMEOUT': '#FF5722',
            'UNKNOWN': '#9E9E9E'
        }

        for status, count in sorted(status_counts.items()):
            labels.append(f'{status} ({count})')
            sizes.append(count)
            colors.append(status_colors.get(status, '#9E9E9E'))

        fig, ax = plt.subplots(figsize=(8, 8))

        wedges, texts, autotexts = ax.pie(
            sizes,
            labels=labels,
            colors=colors,
            autopct='%1.1f%%',
            startangle=90,
            explode=[0.05] * len(sizes)
        )

        for autotext in autotexts:
            autotext.set_color('white')
            autotext.set_fontsize(12)

        ax.set_title('测试达标率分布', fontsize=14, fontweight='bold')
        ax.axis('equal')

        fig.tight_layout()

        if filename is None:
            filename = f'pass_rate_pie_{datetime.now().strftime("%Y%m%d_%H%M%S")}.png'
        output_path = self.output_dir / filename
        plt.savefig(output_path, dpi=150, bbox_inches='tight')
        plt.close()

        self.generated_charts.append(output_path)
        print(f"✓ 达标率饼图已保存：{output_path}")
        return output_path

    def generate_all_charts(
        self,
        test_results: List[Dict],
        history_comparison: Dict = None,
        target_config: Dict = None
    ) -> List[Path]:
        """
        生成所有图表

        Args:
            test_results: 测试结果列表
            history_comparison: 历史对比数据（可选）
            target_config: 目标配置（可选）

        Returns:
            生成的所有图表文件路径列表
        """
        print("\n开始生成图表...")

        charts = []

        chart1 = self.generate_performance_bar_chart(test_results, target_config)
        if chart1:
            charts.append(chart1)

        if history_comparison and history_comparison.get('status') != 'no_history':
            chart2 = self.generate_trend_line_chart(history_comparison)
            if chart2:
                charts.append(chart2)

        chart3 = self.generate_pass_rate_pie_chart(test_results)
        if chart3:
            charts.append(chart3)

        print(f"\n✓ 共生成 {len(charts)} 个图表")
        return charts

    def print_generated_charts(self):
        """打印已生成的图表列表"""
        if not self.generated_charts:
            print("未生成任何图表")
            return

        print("\n已生成的图表:")
        print("-" * 70)
        for chart_path in self.generated_charts:
            print(f"  • {chart_path}")
        print("-" * 70)

def main():
    """主函数 - 演示用法"""
    print("图表生成模块")
    print("=" * 70)

    generator = ChartGenerator()

    test_results = [
        {'name': 'seq_read_burst', 'bandwidth_mbps': 2150.5, 'iops': 15200, 'status': 'PASS'},
        {'name': 'seq_write_burst', 'bandwidth_mbps': 1850.3, 'iops': 14800, 'status': 'PASS'},
        {'name': 'rand_read_burst', 'bandwidth_mbps': 450.2, 'iops': 95000, 'status': 'WARNING'},
        {'name': 'rand_write_burst', 'bandwidth_mbps': 380.5, 'iops': 82000, 'status': 'PASS'},
        {'name': 'mixed_rw', 'bandwidth_mbps': 420.8, 'iops': 88000, 'status': 'PASS'},
    ]

    target_config = {
        'target_bandwidth_mbps': 2100,
        'target_iops': 15000
    }

    history_comparison = {
        'trends': {
            'seq_read_burst': {
                'current': {'bandwidth_mbps': 2150.5},
                'history_avg': {'bandwidth_mbps': 2100.0},
                'history_min': {'bandwidth_mbps': 2050.0},
                'history_max': {'bandwidth_mbps': 2200.0}
            },
            'seq_write_burst': {
                'current': {'bandwidth_mbps': 1850.3},
                'history_avg': {'bandwidth_mbps': 1800.0},
                'history_min': {'bandwidth_mbps': 1750.0},
                'history_max': {'bandwidth_mbps': 1900.0}
            }
        }
    }

    charts = generator.generate_all_charts(
        test_results=test_results,
        history_comparison=history_comparison,
        target_config=target_config
    )

    generator.print_generated_charts()

if __name__ == '__main__':
    main()
