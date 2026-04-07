#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
QoS 延迟分布图表生成器
从延迟分布数据生成可视化图表
"""

import json
import logging
from pathlib import Path
from typing import Dict, Any, List

logger = logging.getLogger(__name__)


class QoSChartGenerator:
    """QoS 延迟分布图表生成器"""
    
    def __init__(self, output_dir: Path = None):
        self.output_dir = output_dir or Path('./qos_charts')
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def load_distribution_data(self, json_file: Path) -> Dict[str, Any]:
        """加载延迟分布数据"""
        with open(json_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def generate_text_chart(self, distribution: Dict[str, float], test_name: str = "QoS Test") -> str:
        """
        生成文本格式的延迟分布图表（ASCII 艺术）
        
        输出示例:
        延迟分布 (μs):
        p50     [████████████████████] 120.5
        p90     [████████████████████████████████████████] 245.8
        p99     [████████████████████████████████████████████████] 389.2
        p99.9   [████████████████████████████████████████████████████████] 567.3
        p99.99  [████████████████████████████████████████████████████████████████] 892.1
        p99.999 [████████████████████████████████████████████████████████████████████████] 1234.5
        """
        chart_lines = []
        chart_lines.append(f"📊 {test_name} 延迟分布 (μs):")
        chart_lines.append("=" * 80)
        
        # 找到最大值用于归一化
        max_val = distribution.get('p99.999', 1)
        if max_val == 0:
            max_val = 1
        
        # 百分位数据
        percentiles = [
            ('p50', 'p50'),
            ('p90', 'p90'),
            ('p95', 'p95'),
            ('p99', 'p99'),
            ('p99.9', 'p99.9'),
            ('p99.99', 'p99.99'),
            ('p99.999', 'p99.999'),
        ]
        
        max_bar_length = 50  # 最大条形长度
        
        for key, label in percentiles:
            value = distribution.get(key, 0)
            bar_length = int((value / max_val) * max_bar_length)
            bar = '█' * bar_length
            chart_lines.append(f"{label:8} [{bar:<{max_bar_length}}] {value:.1f} μs")
        
        # 添加统计信息
        chart_lines.append("")
        chart_lines.append("统计信息:")
        chart_lines.append(f"  最小值：{distribution.get('min', 0):.1f} μs")
        chart_lines.append(f"  最大值：{distribution.get('max', 0):.1f} μs")
        chart_lines.append(f"  平均值：{distribution.get('mean', 0):.1f} μs")
        chart_lines.append(f"  标准差：{distribution.get('stddev', 0):.1f} μs")
        chart_lines.append(f"  尾部系数 (p99.999/p50): {distribution.get('p99.999', 0) / max(distribution.get('p50', 1), 0.1):.1f}x")
        
        return "\n".join(chart_lines)
    
    def generate_csv(self, distribution: Dict[str, float], test_name: str = "QoS Test") -> str:
        """生成 CSV 格式数据"""
        lines = []
        lines.append("Metric,Value (μs)")
        
        for key in ['min', 'p50', 'p90', 'p95', 'p99', 'p99.9', 'p99.99', 'p99.999', 'max', 'mean', 'stddev']:
            value = distribution.get(key, 0)
            lines.append(f"{key},{value:.1f}")
        
        return "\n".join(lines)
    
    def save_results(self, data: Dict[str, Any], base_name: str = "qos_result"):
        """保存所有格式的结果"""
        distribution = data.get('distribution', {})
        test_name = data.get('test_name', 'QoS Test')
        
        # 保存文本图表
        text_chart = self.generate_text_chart(distribution, test_name)
        text_file = self.output_dir / f'{base_name}_chart.txt'
        with open(text_file, 'w', encoding='utf-8') as f:
            f.write(text_chart)
        logger.info(f"📁 文本图表已保存：{text_file}")
        
        # 保存 CSV
        csv_data = self.generate_csv(distribution, test_name)
        csv_file = self.output_dir / f'{base_name}_data.csv'
        with open(csv_file, 'w', encoding='utf-8') as f:
            f.write(csv_data)
        logger.info(f"📁 CSV 数据已保存：{csv_file}")
        
        # 保存完整 JSON
        json_file = self.output_dir / f'{base_name}_full.json'
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        logger.info(f"📁 完整数据已保存：{json_file}")


def generate_qos_chart(json_file: Path, output_dir: Path = None):
    """便捷函数：从 JSON 文件生成图表"""
    generator = QoSChartGenerator(output_dir)
    data = generator.load_distribution_data(json_file)
    
    base_name = json_file.stem.replace('qos_latency_distribution_', '')
    generator.save_results(data, base_name)
    
    # 打印文本图表
    text_chart = generator.generate_text_chart(data.get('distribution', {}), data.get('test_name', 'QoS Test'))
    print(text_chart)
    
    return generator


if __name__ == '__main__':
    import sys
    
    if len(sys.argv) > 1:
        json_file = Path(sys.argv[1])
        if json_file.exists():
            generate_qos_chart(json_file)
        else:
            print(f"❌ 文件不存在：{json_file}")
            sys.exit(1)
    else:
        print("用法：python3 qos_chart_generator.py <json_file>")
        print("示例：python3 qos_chart_generator.py qos_latency_distribution_seq_read.json")
