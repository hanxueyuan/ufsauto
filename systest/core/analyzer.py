#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
失效分析引擎 - Failure Analysis Engine

生产级失效分析工具，提供：
- 失效模式自动匹配
- 根因分析建议
- 历史数据对比
- 趋势分析

Usage:
    from core.analyzer import FailureAnalyzer
    
    analyzer = FailureAnalyzer()
    analysis = analyzer.analyze(test_result)
    print(analysis['root_cause'])
    print(analysis['suggestions'])
"""

import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class FailureMode(Enum):
    """失效模式分类"""
    # 性能类
    LOW_BANDWIDTH = "low_bandwidth"
    LOW_IOPS = "low_iops"
    HIGH_LATENCY = "high_latency"
    LATENCY_JITTER = "latency_jitter"
    
    # 稳定性类
    TEST_TIMEOUT = "test_timeout"
    TEST_CRASH = "test_crash"
    DEVICE_NOT_FOUND = "device_not_found"
    PERMISSION_DENIED = "permission_denied"
    
    # 资源类
    INSUFFICIENT_SPACE = "insufficient_space"
    MEMORY_EXHAUSTED = "memory_exhausted"
    CPU_THROTTLING = "cpu_throttling"
    
    # 设备健康类
    DEVICE_DEGRADED = "device_degraded"
    WEAR_LEVELING = "wear_leveling"
    THERMAL_THROTTLING = "thermal_throttling"
    
    # 未知
    UNKNOWN = "unknown"


@dataclass
class FailureAnalysis:
    """失效分析结果"""
    test_name: str
    failure_mode: FailureMode
    severity: str  # critical, major, minor
    root_cause: str
    suggestions: List[str]
    confidence: float  # 0.0 - 1.0
    related_metrics: Dict[str, Any]


class FailureAnalyzer:
    """失效分析引擎"""
    
    def __init__(self, logger=None):
        """
        初始化失效分析引擎
        
        Args:
            logger: 日志记录器
        """
        self.logger = logger or logging.getLogger(__name__)
        
        # 失效模式库
        self.failure_modes = self._build_failure_mode_library()
    
    def _build_failure_mode_library(self) -> Dict[FailureMode, Dict]:
        """构建失效模式库"""
        return {
            FailureMode.LOW_BANDWIDTH: {
                'description': '带宽低于预期阈值',
                'severity': 'major',
                'possible_causes': [
                    'I/O 调度器配置不当',
                    '设备固件问题',
                    '总线带宽限制',
                    '并发访问冲突',
                    '缓存未命中'
                ],
                'suggestions': [
                    '检查 I/O 调度器设置（建议：none 或 mq-deadline）',
                    '检查设备固件版本，必要时升级',
                    '检查 PCIe/NVMe 链路宽度和速度',
                    '确保测试期间无其他进程访问设备',
                    '检查 CPU frequency governor 设置'
                ],
                'thresholds': {
                    'seq_read': 2100,  # MB/s
                    'seq_write': 1650  # MB/s
                }
            },
            
            FailureMode.LOW_IOPS: {
                'description': 'IOPS 低于预期阈值',
                'severity': 'major',
                'possible_causes': [
                    '队列深度不足',
                    'I/O 引擎效率低',
                    '设备固件问题',
                    'CPU 性能瓶颈'
                ],
                'suggestions': [
                    '增加 --iodepth 参数（建议：32-256）',
                    '尝试 libaio 或 io_uring 引擎',
                    '检查设备固件版本',
                    '监控系统 CPU 使用率'
                ],
                'thresholds': {
                    'rand_read': 200000,  # IOPS
                    'rand_write': 330000,  # IOPS
                    'mixed_rw': 150000  # IOPS
                }
            },
            
            FailureMode.HIGH_LATENCY: {
                'description': '延迟高于预期阈值',
                'severity': 'major',
                'possible_causes': [
                    '设备过载',
                    '队列深度过高',
                    '设备进入节能模式',
                    '温度过高导致降频'
                ],
                'suggestions': [
                    '降低 --iodepth 参数',
                    '检查设备温度',
                    '禁用设备自动节能功能',
                    '检查系统负载'
                ],
                'thresholds': {
                    'avg_latency_us': 100,  # μs
                    'p99_latency_us': 500  # μs
                }
            },
            
            FailureMode.TEST_TIMEOUT: {
                'description': '测试执行超时',
                'severity': 'critical',
                'possible_causes': [
                    '设备无响应',
                    '系统死锁',
                    '资源耗尽',
                    '硬件故障'
                ],
                'suggestions': [
                    '检查设备连接状态',
                    '查看 dmesg 日志',
                    '重启设备后重试',
                    '联系硬件供应商'
                ]
            },
            
            FailureMode.DEVICE_NOT_FOUND: {
                'description': '测试设备不存在',
                'severity': 'critical',
                'possible_causes': [
                    '设备未正确连接',
                    '设备路径配置错误',
                    '驱动未加载',
                    '设备硬件故障'
                ],
                'suggestions': [
                    '检查设备物理连接',
                    '验证设备路径（/dev/ufs0）',
                    '检查 UFS 驱动是否加载',
                    '运行 lsblk 查看设备列表'
                ]
            },
            
            FailureMode.INSUFFICIENT_SPACE: {
                'description': '可用空间不足',
                'severity': 'minor',
                'possible_causes': [
                    '测试文件过大',
                    '设备空间已用尽',
                    '其他进程占用空间'
                ],
                'suggestions': [
                    '清理设备空间',
                    '减小测试文件大小',
                    '检查是否有其他进程占用'
                ]
            },
            
            FailureMode.THERMAL_THROTTLING: {
                'description': '设备因温度过高降频',
                'severity': 'major',
                'possible_causes': [
                    '散热不良',
                    '环境温度过高',
                    '持续高负载测试',
                    '风扇故障'
                ],
                'suggestions': [
                    '检查设备温度传感器',
                    '改善散热条件',
                    '降低环境温度',
                    '在测试之间增加冷却时间'
                ]
            },
            
            FailureMode.DEVICE_DEGRADED: {
                'description': '设备健康状态下降',
                'severity': 'critical',
                'possible_causes': [
                    'NAND 闪存磨损',
                    '坏块增加',
                    'ECC 错误率上升',
                    '设备接近寿命终点'
                ],
                'suggestions': [
                    '检查设备健康状态（SMART）',
                    '查看预 EOL 指示器',
                    '备份重要数据',
                    '计划设备更换'
                ]
            }
        }
    
    def analyze(self, test_result: Dict[str, Any], threshold_config: Optional[Dict] = None) -> FailureAnalysis:
        """
        分析测试结果
        
        Args:
            test_result: 测试结果字典
            threshold_config: 阈值配置（可选）
        
        Returns:
            FailureAnalysis: 分析结果
        """
        test_name = test_result.get('name', 'unknown')
        status = test_result.get('status', 'UNKNOWN')
        metrics = test_result.get('metrics', {})
        error = test_result.get('error', '')
        
        self.logger.info(f"分析测试结果：{test_name} ({status})")
        
        # 1. 根据状态快速判断
        if status == 'PASS':
            return FailureAnalysis(
                test_name=test_name,
                failure_mode=FailureMode.UNKNOWN,
                severity='info',
                root_cause='测试通过，无需分析',
                suggestions=[],
                confidence=1.0,
                related_metrics=metrics
            )
        
        # 2. 错误类型分析
        if status == 'ERROR':
            if 'timeout' in error.lower():
                return self._create_analysis(test_name, FailureMode.TEST_TIMEOUT, metrics)
            elif 'not found' in error.lower() or 'no such' in error.lower():
                return self._create_analysis(test_name, FailureMode.DEVICE_NOT_FOUND, metrics)
            elif 'permission' in error.lower():
                return self._create_analysis(test_name, FailureMode.PERMISSION_DENIED, metrics)
            elif 'space' in error.lower() or 'no space' in error.lower():
                return self._create_analysis(test_name, FailureMode.INSUFFICIENT_SPACE, metrics)
            else:
                return self._create_analysis(test_name, FailureMode.UNKNOWN, metrics, error)
        
        # 3. 性能指标分析
        if status == 'FAIL':
            return self._analyze_performance(test_name, metrics, threshold_config)
        
        # 默认
        return self._create_analysis(test_name, FailureMode.UNKNOWN, metrics)
    
    def _analyze_performance(self, test_name: str, metrics: Dict, threshold_config: Optional[Dict]) -> FailureAnalysis:
        """分析性能测试失败"""
        
        # 检查带宽
        if 'bandwidth' in metrics:
            bw = metrics['bandwidth'].get('value', 0)
            
            if 'seq_read' in test_name and bw < 2100:
                return self._create_analysis(test_name, FailureMode.LOW_BANDWIDTH, metrics)
            elif 'seq_write' in test_name and bw < 1650:
                return self._create_analysis(test_name, FailureMode.LOW_BANDWIDTH, metrics)
        
        # 检查 IOPS
        if 'iops' in metrics:
            iops = metrics['iops'].get('value', 0)
            
            if 'rand_read' in test_name and iops < 200000:
                return self._create_analysis(test_name, FailureMode.LOW_IOPS, metrics)
            elif 'rand_write' in test_name and iops < 330000:
                return self._create_analysis(test_name, FailureMode.LOW_IOPS, metrics)
            elif 'mixed' in test_name and iops < 150000:
                return self._create_analysis(test_name, FailureMode.LOW_IOPS, metrics)
        
        # 检查延迟
        if 'latency_avg' in metrics:
            latency = metrics['latency_avg'].get('value', 0)
            if latency > 100:  # > 100μs
                return self._create_analysis(test_name, FailureMode.HIGH_LATENCY, metrics)
        
        # 未知性能问题
        return self._create_analysis(test_name, FailureMode.UNKNOWN, metrics)
    
    def _create_analysis(self, test_name: str, failure_mode: FailureMode, metrics: Dict, error: str = '') -> FailureAnalysis:
        """创建分析结果"""
        mode_info = self.failure_modes.get(failure_mode, {})
        
        # 根据错误信息增强根因分析
        root_cause = mode_info.get('description', '未知失效模式')
        if error:
            root_cause += f" (错误：{error})"
        
        suggestions = mode_info.get('suggestions', ['请检查测试环境和配置'])
        
        # 计算置信度
        confidence = 0.8 if failure_mode != FailureMode.UNKNOWN else 0.5
        
        return FailureAnalysis(
            test_name=test_name,
            failure_mode=failure_mode,
            severity=mode_info.get('severity', 'major'),
            root_cause=root_cause,
            suggestions=suggestions,
            confidence=confidence,
            related_metrics=metrics
        )
    
    def generate_report(self, analyses: List[FailureAnalysis]) -> Dict[str, Any]:
        """
        生成失效分析报告
        
        Args:
            analyses: 分析结果列表
        
        Returns:
            Dict: 汇总报告
        """
        report = {
            'total_tests': len(analyses),
            'passed': sum(1 for a in analyses if a.failure_mode == FailureMode.UNKNOWN and a.severity == 'info'),
            'failed': sum(1 for a in analyses if a.severity in ['critical', 'major']),
            'warnings': sum(1 for a in analyses if a.severity == 'minor'),
            'failure_modes': {},
            'critical_issues': [],
            'suggestions': []
        }
        
        # 统计失效模式
        for analysis in analyses:
            if analysis.severity != 'info':
                mode = analysis.failure_mode.value
                report['failure_modes'][mode] = report['failure_modes'].get(mode, 0) + 1
                
                if analysis.severity == 'critical':
                    report['critical_issues'].append({
                        'test': analysis.test_name,
                        'issue': analysis.root_cause,
                        'suggestions': analysis.suggestions
                    })
                
                report['suggestions'].extend(analysis.suggestions)
        
        # 去重建议
        report['suggestions'] = list(dict.fromkeys(report['suggestions']))
        
        return report


# 便捷函数
def analyze_test_result(result: Dict[str, Any]) -> FailureAnalysis:
    """快速分析测试结果"""
    return FailureAnalyzer().analyze(result)
