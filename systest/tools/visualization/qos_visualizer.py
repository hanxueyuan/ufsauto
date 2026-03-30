#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
QoS 测试结果可视化工具
生成专业的 QoS 分析图表，支持延迟分布、尾部发散度、稳定性分析

Usage:
    from tools.visualization.qos_visualizer import QoSViz
    
    viz = QoSViz()
    viz.plot_latency_distribution(test_results)
    viz.plot_tail_ratio_analysis(test_results)
    viz.plot_stability_analysis(test_results)
"""

import json
import matplotlib.pyplot as plt
import numpy as np
from pathlib import Path
from typing import Dict, List, Any, Optional
import logging

logger = logging.getLogger(__name__)


class QoSViz:
    """QoS 测试结果可视化类"""
    
    def __init__(self, output_dir: str = "results/visualization"):
        """
        初始化可视化工具
        
        Args:
            output_dir: 图表输出目录
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # 设置中文字体支持
        plt.rcParams['font.sans-serif'] = ['SimHei', 'DejaVu Sans']
        plt.rcParams['axes.unicode_minus'] = False
    
    def plot_latency_distribution(self, test_results: Dict[str, Any], title: str = "延迟分布分析"):
        """
        绘制延迟分布图（箱线图 + 百分位标记）
        
        Args:
            test_results: 测试结果字典
            title: 图表标题
        """
        logger.info("生成延迟分布图...")
        
        # 提取延迟数据
        latency_data = []
        labels = []
        
        for test_name, result in test_results.items():
            if 'latency_ns' in result.get('metrics', {}):
                percentiles = result['metrics']['latency_ns'].get('percentile', {})
                # 转换为微秒
                p50 = percentiles.get('50.000000', 0) / 1000
                p90 = percentiles.get('90.000000', 0) / 1000
                p99 = percentiles.get('99.000000', 0) / 1000
                p9999 = percentiles.get('99.990000', 0) / 1000
                p99999 = percentiles.get('99.999000', 0) / 1000
                
                if p50 > 0:
                    latency_data.append([p50, p90, p99, p9999, p99999])
                    labels.append(test_name)
        
        if not latency_data:
            logger.warning("未找到延迟数据，跳过延迟分布图")
            return
        
        # 创建图表
        fig, ax = plt.subplots(figsize=(12, 8))
        
        # 绘制箱线图（简化版，使用百分位数据）
        positions = range(len(latency_data))
        for i, data in enumerate(latency_data):
            # 绘制百分位线
            ax.plot([i, i], [data[0], data[4]], 'b-', alpha=0.7, linewidth=2)
            # 标记关键百分位点
            ax.scatter([i]*5, data, c=['green', 'orange', 'red', 'purple', 'black'], 
                      s=[50, 50, 50, 50, 50], zorder=5)
        
        ax.set_xticks(positions)
        ax.set_xticklabels(labels, rotation=45, ha='right')
        ax.set_ylabel('延迟 (μs)')
        ax.set_title(f'{title}\n(绿色:p50, 橙色:p90, 红色:p99, 紫色:p99.99, 黑色:p99.999)')
        ax.grid(True, alpha=0.3)
        
        # 设置对数刻度（如果数据跨度大）
        max_latency = max(max(data) for data in latency_data)
        min_latency = min(min(data) for data in latency_data)
        if max_latency / min_latency > 10:
            ax.set_yscale('log')
        
        plt.tight_layout()
        output_path = self.output_dir / "latency_distribution.png"
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        plt.close()
        
        logger.info(f"✅ 延迟分布图已保存: {output_path}")
    
    def plot_tail_ratio_analysis(self, test_results: Dict[str, Any], title: str = "尾部发散度分析"):
        """
        绘制尾部发散度分析图
        
        Args:
            test_results: 测试结果字典
            title: 图表标题
        """
        logger.info("生成尾部发散度分析图...")
        
        test_names = []
        tail_ratios = []
        p9999_values = []
        p50_values = []
        
        for test_name, result in test_results.items():
            annotations = result.get('annotations', [])
            for ann in annotations:
                if ann.get('metric') == '尾部发散度':
                    try:
                        ratio_str = ann['actual'].split('=')[1].replace('x', '')
                        ratio = float(ratio_str)
                        tail_ratios.append(ratio)
                        test_names.append(test_name)
                        
                        # 提取具体的 p99.99 和 p50 值
                        metrics = result.get('metrics', {})
                        if 'latency_p9999' in metrics and 'latency_p50' in metrics:
                            p9999_values.append(metrics['latency_p9999']['value'])
                            p50_values.append(metrics['latency_p50']['value'])
                        else:
                            p9999_values.append(0)
                            p50_values.append(0)
                    except (IndexError, ValueError, KeyError) as e:
                        logger.warning(f"解析尾部发散度数据失败: {e}")
                        continue
        
        if not tail_ratios:
            logger.warning("未找到尾部发散度数据，跳过分析图")
            return
        
        # 创建双轴图表
        fig, ax1 = plt.subplots(figsize=(12, 8))
        
        # 尾部发散度柱状图
        bars = ax1.bar(test_names, tail_ratios, alpha=0.7, color='skyblue', label='尾部发散度 (p99.99/p50)')
        ax1.set_ylabel('尾部发散度 (倍数)', color='blue')
        ax1.tick_params(axis='y', labelcolor='blue')
        ax1.set_xticklabels(test_names, rotation=45, ha='right')
        
        # 添加数值标签
        for bar, ratio in zip(bars, tail_ratios):
            ax1.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.1,
                    f'{ratio:.1f}x', ha='center', va='bottom', fontweight='bold')
        
        # p99.99 延迟折线图（右轴）
        ax2 = ax1.twinx()
        if any(p9999_values):
            ax2.plot(test_names, p9999_values, 'ro-', linewidth=2, markersize=8, label='p99.99 延迟')
            ax2.set_ylabel('p99.99 延迟 (μs)', color='red')
            ax2.tick_params(axis='y', labelcolor='red')
        
        ax1.set_title(f'{title}\n车规要求: 尾部发散度 < 100x, p99.99 < 2000μs')
        ax1.grid(True, alpha=0.3)
        
        # 添加参考线
        ax1.axhline(y=100, color='red', linestyle='--', alpha=0.7, label='车规上限 (100x)')
        if any(p9999_values):
            ax2.axhline(y=2000, color='purple', linestyle='--', alpha=0.7, label='p99.99 上限 (2000μs)')
        
        # 合并图例
        lines1, labels1 = ax1.get_legend_handles_labels()
        lines2, labels2 = ax2.get_legend_handles_labels()
        ax1.legend(lines1 + lines2, labels1 + labels2, loc='upper left')
        
        plt.tight_layout()
        output_path = self.output_dir / "tail_ratio_analysis.png"
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        plt.close()
        
        logger.info(f"✅ 尾部发散度分析图已保存: {output_path}")
    
    def plot_stability_analysis(self, test_results: Dict[str, Any], title: str = "延迟稳定性分析"):
        """
        绘制延迟稳定性分析图（多次测试的波动性）
        
        Args:
            test_results: 测试结果字典
            title: 图表标题
        """
        logger.info("生成延迟稳定性分析图...")
        
        stability_data = {}
        
        for test_name, result in test_results.items():
            # 查找稳定性相关的指标
            annotations = result.get('annotations', [])
            avg_cv = None
            p9999_cv = None
            
            for ann in annotations:
                if ann.get('metric') == '平均延迟变异系数':
                    try:
                        cv_str = ann['actual'].replace('%', '')
                        avg_cv = float(cv_str)
                    except (ValueError, KeyError):
                        pass
                elif ann.get('metric') == 'p99.99 延迟变异系数':
                    try:
                        cv_str = ann['actual'].replace('%', '')
                        p9999_cv = float(cv_str)
                    except (ValueError, KeyError):
                        pass
            
            if avg_cv is not None or p9999_cv is not None:
                stability_data[test_name] = {
                    'avg_cv': avg_cv or 0,
                    'p9999_cv': p9999_cv or 0
                }
        
        if not stability_data:
            logger.warning("未找到稳定性数据，跳过分析图")
            return
        
        # 创建图表
        fig, ax = plt.subplots(figsize=(12, 8))
        
        test_names = list(stability_data.keys())
        avg_cvs = [stability_data[name]['avg_cv'] for name in test_names]
        p9999_cvs = [stability_data[name]['p9999_cv'] for name in test_names]
        
        x = np.arange(len(test_names))
        width = 0.35
        
        # 绘制柱状图
        bars1 = ax.bar(x - width/2, avg_cvs, width, label='平均延迟 CV', alpha=0.7, color='lightblue')
        bars2 = ax.bar(x + width/2, p9999_cvs, width, label='p99.99 延迟 CV', alpha=0.7, color='lightcoral')
        
        # 添加数值标签
        for bar, cv in zip(bars1, avg_cvs):
            if cv > 0:
                ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.1,
                       f'{cv:.1f}%', ha='center', va='bottom')
        
        for bar, cv in zip(bars2, p9999_cvs):
            if cv > 0:
                ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.1,
                       f'{cv:.1f}%', ha='center', va='bottom')
        
        ax.set_xlabel('测试用例')
        ax.set_ylabel('变异系数 (%)')
        ax.set_title(f'{title}\n车规要求: 平均延迟 CV < 10%, p99.99 CV < 15%')
        ax.set_xticks(x)
        ax.set_xticklabels(test_names, rotation=45, ha='right')
        ax.legend()
        ax.grid(True, alpha=0.3)
        
        # 添加参考线
        ax.axhline(y=10, color='blue', linestyle='--', alpha=0.7, label='平均延迟上限 (10%)')
        ax.axhline(y=15, color='red', linestyle='--', alpha=0.7, label='p99.99 上限 (15%)')
        
        plt.tight_layout()
        output_path = self.output_dir / "stability_analysis.png"
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        plt.close()
        
        logger.info(f"✅ 延迟稳定性分析图已保存: {output_path}")
    
    def generate_comprehensive_report(self, test_results: Dict[str, Any], report_title: str = "QoS 测试综合报告"):
        """
        生成综合 QoS 测试报告
        
        Args:
            test_results: 所有测试结果
            report_title: 报告标题
        """
        logger.info("生成综合 QoS 测试报告...")
        
        # 生成所有图表
        self.plot_latency_distribution(test_results, "QoS 延迟分布分析")
        self.plot_tail_ratio_analysis(test_results, "QoS 尾部发散度分析")  
        self.plot_stability_analysis(test_results, "QoS 延迟稳定性分析")
        
        # 生成 HTML 报告
        html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>{report_title}</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        .chart {{ margin: 20px 0; text-align: center; }}
        .chart img {{ max-width: 100%; height: auto; }}
        .summary {{ background: #f5f5f5; padding: 15px; border-radius: 5px; margin: 20px 0; }}
        h1, h2 {{ color: #333; }}
    </style>
</head>
<body>
    <h1>{report_title}</h1>
    
    <div class="summary">
        <h2>测试概要</h2>
        <p>共执行 {len(test_results)} 个 QoS 测试用例</p>
        <p>包含: 延迟分布、尾部发散度、稳定性分析</p>
        <p>车规标准: p99.99 &lt; 2ms, 尾部发散度 &lt; 100x, CV &lt; 10-15%</p>
    </div>
    
    <div class="chart">
        <h2>延迟分布分析</h2>
        <img src="latency_distribution.png" alt="延迟分布">
    </div>
    
    <div class="chart">
        <h2>尾部发散度分析</h2>
        <img src="tail_ratio_analysis.png" alt="尾部发散度">
    </div>
    
    <div class="chart">
        <h2>延迟稳定性分析</h2>
        <img src="stability_analysis.png" alt="稳定性分析">
    </div>
</body>
</html>
        """
        
        report_path = self.output_dir / "qos_report.html"
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        logger.info(f"✅ 综合 QoS 报告已生成: {report_path}")
        return str(report_path)


def load_test_results(results_dir: str = "results") -> Dict[str, Any]:
    """
    加载测试结果
    
    Args:
        results_dir: 结果目录路径
        
    Returns:
        Dict: 测试结果字典
    """
    results_path = Path(results_dir)
    if not results_path.exists():
        logger.warning(f"结果目录不存在: {results_path}")
        return {}
    
    # 查找最新的结果文件
    result_files = list(results_path.glob("*/results.json"))
    if not result_files:
        logger.warning("未找到结果文件")
        return {}
    
    latest_result = max(result_files, key=lambda x: x.stat().st_mtime)
    logger.info(f"加载最新结果文件: {latest_result}")
    
    with open(latest_result, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # 转换为测试名称到结果的映射
    test_results = {}
    for test_case in data.get('test_cases', []):
        test_results[test_case['name']] = test_case
    
    return test_results


# 便捷函数
def visualize_qos_results(results_dir: str = "results", output_dir: str = "results/visualization"):
    """快速可视化 QoS 测试结果"""
    test_results = load_test_results(results_dir)
    if not test_results:
        print("❌ 未找到测试结果，无法生成图表")
        return None
    
    viz = QoSViz(output_dir)
    report_path = viz.generate_comprehensive_report(test_results)
    print(f"✅ QoS 可视化报告已生成: {report_path}")
    return report_path


if __name__ == "__main__":
    # 命令行使用
    import argparse
    
    parser = argparse.ArgumentParser(description="QoS 测试结果可视化工具")
    parser.add_argument("--results", default="results", help="测试结果目录")
    parser.add_argument("--output", default="results/visualization", help="图表输出目录")
    
    args = parser.parse_args()
    
    visualize_qos_results(args.results, args.output)