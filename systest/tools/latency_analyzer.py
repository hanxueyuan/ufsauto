#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
延迟分析器 - Latency Analyzer
负责延迟分布分析、尾部延迟根因定位、QoS 指标计算
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class LatencyBucket:
    """延迟桶（用于分布统计）"""
    min_us: float
    max_us: float
    count: int
    percentage: float


@dataclass
class QoSMetrics:
    """QoS 指标集合"""
    avg_us: float
    p50_us: float
    p90_us: float
    p99_us: float
    p9999_us: float
    p99999_us: float
    min_us: float
    max_us: float
    stddev_us: float
    total_ios: int
    
    # 派生指标
    tail_ratio_p99_p50: float  # p99/p50
    tail_ratio_p9999_p50: float  # p99.99/p50
    coefficient_of_variation: float  # stddev/avg


class LatencyAnalyzer:
    """延迟分析器"""
    
    # 车规级 QoS 参考标准（UFS 3.1 128GB）
    QOS_TARGETS = {
        'p99_us': 500,      # p99 < 500μs
        'p9999_us': 2000,   # p99.99 < 2ms
        'p99999_us': 5000,  # p99.999 < 5ms
        'tail_ratio': 100,  # p99.99/p50 < 100x
    }
    
    # 延迟桶配置（用于分布可视化）
    BUCKET_CONFIG = [
        (0, 50), (50, 100), (100, 200), (200, 500),
        (500, 1000), (1000, 2000), (2000, 5000),
        (5000, 10000), (10000, float('inf'))
    ]
    
    def __init__(self, verbose: bool = False, logger=None):
        self.verbose = verbose
        self.logger = logger or logging.getLogger(__name__)
    
    def analyze(self, fio_json_path: str) -> Dict[str, Any]:
        """
        分析 FIO JSON 输出，生成完整的延迟分析报告
        
        Args:
            fio_json_path: FIO JSON 结果文件路径
        
        Returns:
            包含 QoS 指标、分布数据、根因建议的分析报告
        """
        with open(fio_json_path, 'r') as f:
            fio_data = json.load(f)
        
        # 提取延迟数据（支持 read/lat 和 write/lat）
        jobs = fio_data.get('jobs', [])
        if not jobs:
            raise ValueError("FIO JSON 中无 jobs 数据")
        
        job = jobs[0]  # 单 job 模式
        read_lat = job.get('read', {})
        write_lat = job.get('write', {})
        
        # 分析读取延迟
        read_metrics = self._extract_metrics(read_lat, 'read')
        read_distribution = self._extract_distribution(read_lat)
        
        # 分析写入延迟
        write_metrics = self._extract_metrics(write_lat, 'write')
        write_distribution = self._extract_distribution(write_lat)
        
        # 生成根因分析建议
        read_root_causes = self._analyze_root_causes(read_metrics, 'read')
        write_root_causes = self._analyze_root_causes(write_metrics, 'write')
        
        return {
            'read': {
                'metrics': read_metrics,
                'distribution': read_distribution,
                'root_causes': read_root_causes,
            },
            'write': {
                'metrics': write_metrics,
                'distribution': write_distribution,
                'root_causes': write_root_causes,
            },
            'summary': {
                'qos_compliance': self._check_qos_compliance(read_metrics, write_metrics),
                'overall_health': self._assess_overall_health(read_metrics, write_metrics),
            }
        }
    
    def _extract_metrics(self, lat_data: Dict, io_type: str) -> QoSMetrics:
        """从 FIO 延迟数据提取 QoS 指标"""
        if not lat_data:
            return None
        
        lat_ns = lat_data.get('lat_ns', {})
        percentiles = lat_ns.get('percentile', {})
        
        def get_percentile(key: str) -> float:
            val = percentiles.get(key, 0)
            return val / 1000 if val > 0 else 0  # ns → μs
        
        avg_us = lat_ns.get('mean', 0) / 1000
        stddev_us = lat_ns.get('stddev', 0) / 1000
        total_ios = lat_data.get('total_ios', 0)
        
        p50 = get_percentile('50.000000')
        p99 = get_percentile('99.000000')
        p9999 = get_percentile('99.990000')
        p99999 = get_percentile('99.999000')
        
        return QoSMetrics(
            avg_us=avg_us,
            p50_us=p50,
            p90_us=get_percentile('90.000000'),
            p99_us=p99,
            p9999_us=p9999,
            p99999_us=p99999,
            min_us=lat_ns.get('min', 0) / 1000,
            max_us=lat_ns.get('max', 0) / 1000,
            stddev_us=stddev_us,
            total_ios=total_ios,
            tail_ratio_p99_p50=p99 / p50 if p50 > 0 else 0,
            tail_ratio_p9999_p50=p9999 / p50 if p50 > 0 else 0,
            coefficient_of_variation=stddev_us / avg_us if avg_us > 0 else 0,
        )
    
    def _extract_distribution(self, lat_data: Dict) -> List[LatencyBucket]:
        """提取延迟分布（桶统计）"""
        if not lat_data:
            return []
        
        # FIO 的 bucket 数据（如果有）
        buckets_data = lat_data.get('lat_ns', {}).get('buckets', {})
        if not buckets_data:
            return []
        
        total = sum(int(v) for v in buckets_data.values())
        buckets = []
        
        for (min_val, max_val), bucket_key in self.BUCKET_CONFIG:
            # FIO bucket key 是字符串形式的上限值
            key = str(int(max_val * 1000)) if max_val != float('inf') else 'inf'
            count = int(buckets_data.get(key, 0))
            percentage = (count / total * 100) if total > 0 else 0
            
            buckets.append(LatencyBucket(
                min_us=min_val,
                max_us=max_val,
                count=count,
                percentage=percentage,
            ))
        
        return buckets
    
    def _analyze_root_causes(self, metrics: QoSMetrics, io_type: str) -> List[Dict[str, str]]:
        """基于 QoS 指标分析可能的根因"""
        if not metrics:
            return []
        
        causes = []
        
        # 检查尾部延迟过高
        if metrics.p9999_us > self.QOS_TARGETS['p9999_us']:
            causes.append({
                'symptom': f'{io_type} p99.99 延迟过高 ({metrics.p9999_us:.1f} μs)',
                'possible_causes': [
                    '垃圾回收 (GC) 活动频繁',
                    '写放大过高导致后台搬移',
                    'NAND 读取延迟随 P/E 周期增加',
                    '温度过高影响 NAND 性能',
                ],
                'suggested_actions': [
                    '检查测试期间 GC 活动日志',
                    '增加 OP 预留空间',
                    '验证 FTL 磨损均衡策略',
                    '监控测试温度',
                ],
                'priority': 'high',
            })
        
        # 检查尾部发散度
        if metrics.tail_ratio_p9999_p50 > self.QOS_TARGETS['tail_ratio']:
            causes.append({
                'symptom': f'{io_type} 尾部发散度过高 (p99.99/p50 = {metrics.tail_ratio_p9999_p50:.1f}x)',
                'possible_causes': [
                    'FTL 映射表更新延迟不稳定',
                    'NAND 块间性能差异大',
                    '队列深度变化导致调度延迟波动',
                ],
                'suggested_actions': [
                    '分析延迟时间序列，定位延迟峰值时刻',
                    '检查是否有关联的写入放大',
                    '验证 FTL 映射表大小和缓存命中率',
                ],
                'priority': 'medium',
            })
        
        # 检查变异系数
        if metrics.coefficient_of_variation > 1.0:
            causes.append({
                'symptom': f'{io_type} 延迟波动大 (CV = {metrics.coefficient_of_variation:.2f})',
                'possible_causes': [
                    '混合负载导致资源竞争',
                    '后台任务（GC、磨损均衡）干扰',
                    '系统负载不稳定',
                ],
                'suggested_actions': [
                    '使用更纯净的测试环境',
                    '增加测试时长以平滑波动',
                    '检查系统负载（top/vmstat）',
                ],
                'priority': 'medium',
            })
        
        return causes
    
    def _check_qos_compliance(self, read: QoSMetrics, write: QoSMetrics) -> Dict[str, Any]:
        """检查 QoS 合规性"""
        results = {}
        
        for metric, target in self.QOS_TARGETS.items():
            read_val = getattr(read, f'{metric}_us' if metric != 'tail_ratio' else 'tail_ratio_p9999_p50', 0)
            write_val = getattr(write, f'{metric}_us' if metric != 'tail_ratio' else 'tail_ratio_p9999_p50', 0)
            
            results[metric] = {
                'target': target,
                'read_value': read_val,
                'read_pass': read_val <= target,
                'write_value': write_val,
                'write_pass': write_val <= target if write else True,
            }
        
        return results
    
    def _assess_overall_health(self, read: QoSMetrics, write: QoSMetrics) -> str:
        """评估整体健康度"""
        compliance = self._check_qos_compliance(read, write)
        
        pass_count = sum(
            1 for m in compliance.values()
            if m['read_pass'] and (m['write_pass'] if write else True)
        )
        total = len(compliance)
        
        ratio = pass_count / total if total > 0 else 0
        
        if ratio == 1.0:
            return 'excellent'
        elif ratio >= 0.75:
            return 'good'
        elif ratio >= 0.5:
            return 'fair'
        else:
            return 'poor'
    
    def generate_report(self, analysis: Dict[str, Any], output_path: str):
        """生成人类可读的分析报告"""
        lines = [
            "=" * 70,
            "UFS QoS 延迟分析报告",
            "=" * 70,
            "",
        ]
        
        # 读取延迟
        read = analysis['read']['metrics']
        if read:
            lines.extend([
                "📊 读取延迟",
                "-" * 40,
                f"  平均值：   {read.avg_us:8.1f} μs",
                f"  p50:       {read.p50_us:8.1f} μs",
                f"  p99:       {read.p99_us:8.1f} μs",
                f"  p99.99:    {read.p9999_us:8.1f} μs",
                f"  p99.999:   {read.p99999_us:8.1f} μs",
                f"  尾部比：   {read.tail_ratio_p9999_p50:8.1f}x (p99.99/p50)",
                "",
            ])
        
        # 写入延迟
        write = analysis['write']['metrics']
        if write:
            lines.extend([
                "📊 写入延迟",
                "-" * 40,
                f"  平均值：   {write.avg_us:8.1f} μs",
                f"  p50:       {write.p50_us:8.1f} μs",
                f"  p99:       {write.p99_us:8.1f} μs",
                f"  p99.99:    {write.p9999_us:8.1f} μs",
                f"  p99.999:   {write.p99999_us:8.1f} μs",
                f"  尾部比：   {write.tail_ratio_p9999_p50:8.1f}x (p99.99/p50)",
                "",
            ])
        
        # QoS 合规性
        lines.extend([
            "✅ QoS 合规性检查",
            "-" * 40,
        ])
        for metric, result in analysis['summary']['qos_compliance'].items():
            icon = '✅' if (result['read_pass'] and result['write_pass']) else '❌'
            lines.append(f"  {icon} {metric}: 目标 ≤ {result['target']}, "
                        f"读 {result['read_value']:.1f}, 写 {result['write_value']:.1f}")
        lines.append("")
        
        # 整体健康度
        health = analysis['summary']['overall_health']
        health_icon = {'excellent': '🟢', 'good': '🟡', 'fair': '🟠', 'poor': '🔴'}.get(health, '⚪')
        lines.extend([
            f"🏥 整体健康度：{health_icon} {health.upper()}",
            "",
        ])
        
        # 根因分析
        if analysis['read']['root_causes']:
            lines.extend([
                "🔍 读取延迟根因分析",
                "-" * 40,
            ])
            for cause in analysis['read']['root_causes']:
                lines.append(f"  ⚠️ {cause['symptom']} [优先级：{cause['priority']}]")
                for c in cause['possible_causes']:
                    lines.append(f"     • 可能原因：{c}")
                for a in cause['suggested_actions']:
                    lines.append(f"     • 建议动作：{a}")
            lines.append("")
        
        if analysis['write']['root_causes']:
            lines.extend([
                "🔍 写入延迟根因分析",
                "-" * 40,
            ])
            for cause in analysis['write']['root_causes']:
                lines.append(f"  ⚠️ {cause['symptom']} [优先级：{cause['priority']}]")
                for c in cause['possible_causes']:
                    lines.append(f"     • 可能原因：{c}")
                for a in cause['suggested_actions']:
                    lines.append(f"     • 建议动作：{a}")
            lines.append("")
        
        lines.append("=" * 70)
        
        with open(output_path, 'w') as f:
            f.write('\n'.join(lines))
        
        self.logger.info(f"分析报告已保存：{output_path}")


if __name__ == '__main__':
    import sys
    if len(sys.argv) < 2:
        print("Usage: python latency_analyzer.py <fio_json_path> [output_path]")
        sys.exit(1)
    
    analyzer = LatencyAnalyzer(verbose=True)
    analysis = analyzer.analyze(sys.argv[1])
    
    output = sys.argv[2] if len(sys.argv) > 2 else 'latency_analysis.txt'
    analyzer.generate_report(analysis, output)
    print(f"分析完成，报告：{output}")
