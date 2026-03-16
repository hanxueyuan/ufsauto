#!/usr/bin/env python3
"""
失效分析引擎 - Failure Analyzer
负责分析测试失败原因，提供根因定位和建议
"""

import json
from pathlib import Path

# 失效规则库
FAIL_RULES = {
    # ========== 性能类失效 ==========
    "SLC_CACHE_EXHAUSTED": {
        "name": "SLC Cache 耗尽",
        "conditions": [
            {"metric": "seq_write_burst", "op": ">", "value": 1000},
            {"metric": "seq_write_sustained", "op": "<", "value": 500},
        ],
        "confidence": 0.8,
        "suggestions": ["增加预热时间后重新测试", "预留更多 OP 空间（建议 10-25%）", "检查固件 SLC 管理策略"],
    },
    "THERMAL_THROTTLING": {
        "name": "热节流",
        "conditions": [
            {"metric": "performance_drop", "op": ">", "value": 0.3},
        ],
        "confidence": 0.7,
        "suggestions": ["改善散热条件（加散热片/风扇）", "降低环境温度至 25℃", "检查设备温度传感器是否准确"],
    },
    "QUEUE_DEPTH_INSUFFICIENT": {
        "name": "队列深度不足",
        "conditions": [
            {"metric": "iops", "op": "<", "value": "target * 0.5"},
        ],
        "confidence": 0.6,
        "suggestions": ["增加队列深度至 32 或更高", "检查驱动是否支持高队列深度"],
    },
    "BANDWIDTH_BELOW_TARGET": {
        "name": "带宽未达标",
        "conditions": [
            {"metric": "bandwidth", "op": "<", "value": "target * 0.9"},
        ],
        "confidence": 0.65,
        "suggestions": ["检查总线频率和模式配置", "确认 UFS 档位是否正确 (HS-G4)", "检查 CPU 频率和内存带宽"],
    },
    "IOPS_BELOW_TARGET": {
        "name": "IOPS 未达标",
        "conditions": [
            {"metric": "iops", "op": "<", "value": "target * 0.9"},
        ],
        "confidence": 0.65,
        "suggestions": ["增加队列深度提升并行度", "增加 numjobs 提升并发", "检查 CPU 性能是否瓶颈"],
    },
    # ========== 延迟类失效 ==========
    "GC_INTERFERENCE": {
        "name": "GC 干扰",
        "conditions": [
            {"metric": "latency_p99999", "op": ">", "value": 1000},
            {"metric": "latency_stddev", "op": ">", "value": 500},
        ],
        "confidence": 0.75,
        "suggestions": ["测试前执行 TRIM 操作", "预留更多 OP 空间", "检查固件 GC 策略"],
    },
    "LATENCY_TAIL_ISSUE": {
        "name": "延迟长尾",
        "conditions": [
            {"metric": "latency_ratio_p9999_p50", "op": ">", "value": 100},
        ],
        "confidence": 0.7,
        "suggestions": ["检查是否有后台 GC 操作", "确认系统负载情况", "检查中断处理和调度延迟"],
    },
    "LATENCY_HIGH_AVG": {
        "name": "平均延迟过高",
        "conditions": [
            {"metric": "latency_avg", "op": ">", "value": 500},
        ],
        "confidence": 0.6,
        "suggestions": ["降低队列深度减少排队", "检查设备是否过热降频", "确认驱动配置是否优化"],
    },
    "SYSTEM_LOAD_INTERFERENCE": {
        "name": "系统负载干扰",
        "conditions": [],
        "confidence": 0.5,
        "suggestions": ["关闭不必要的后台服务", "设置测试进程 CPU 亲和性", "在空闲系统上重新测试"],
    },
    # ========== 可靠性类失效 ==========
    "DEVICE_ERROR": {
        "name": "设备错误",
        "conditions": [],
        "confidence": 0.9,
        "suggestions": ["检查 SMART 详细日志", "备份数据并更换设备", "联系厂商进行设备分析"],
    },
    "DRIVER_ERROR": {
        "name": "驱动问题",
        "conditions": [],
        "confidence": 0.85,
        "suggestions": ["更新 UFS 驱动到最新版本", "检查内核日志中的错误堆栈", "联系芯片厂商获取驱动支持"],
    },
    "PERFORMANCE_DEGRADATION": {
        "name": "性能衰减",
        "conditions": [
            {"metric": "performance_drop", "op": ">", "value": 0.2},
        ],
        "confidence": 0.75,
        "suggestions": ["检查设备温度和散热", "确认 SLC Cache 是否耗尽", "执行全盘 TRIM 后重新测试"],
    },
    "STABILITY_ISSUE": {
        "name": "稳定性问题",
        "conditions": [],
        "confidence": 0.8,
        "suggestions": ["检查电源稳定性", "确认散热系统工作正常", "检查固件版本和已知问题"],
    },
    # ========== 场景类失效 ==========
    "SENSOR_BANDWIDTH_INSUFFICIENT": {
        "name": "传感器带宽不足",
        "conditions": [
            {"metric": "total_bandwidth", "op": "<", "value": 400},
        ],
        "confidence": 0.7,
        "suggestions": ["检查 UFS 总线模式配置", "确认 CPU 处理能力是否足够", "优化传感器数据写入策略"],
    },
    "MODEL_LOAD_SLOW": {
        "name": "模型加载过慢",
        "conditions": [
            {"metric": "read_bandwidth", "op": "<", "value": 1000},
        ],
        "confidence": 0.65,
        "suggestions": ["优化模型文件存储布局", "使用顺序读取提升带宽", "检查内存映射配置"],
    },
}


class FailureAnalyzer:
    """失效分析引擎"""

    def __init__(self):
        self.rules = FAIL_RULES

    def analyze(self, results):
        """执行失效分析"""

        test_cases = results.get("test_results", {}).get("test_cases", [])
        targets = results.get("config", {}).get("targets", {})

        # 收集所有失效发现
        findings = []

        for tc in test_cases:
            if tc.get("status") != "FAIL":
                continue

            test_name = tc.get("test_name", "")
            metrics = tc.get("metrics", {})

            # 规则匹配
            rule_findings = self._match_rules(test_name, metrics, targets)
            findings.extend(rule_findings)

            # 关联分析
            correlation_findings = self._analyze_correlations(test_name, metrics, tc)
            findings.extend(correlation_findings)

        # 综合根因定位
        root_causes = self._synthesize_root_causes(findings)

        return {
            "test_id": results.get("test_id", "unknown"),
            "timestamp": results.get("timestamp", ""),
            "root_causes": root_causes,
            "findings": findings,
            "summary": self._generate_summary(root_causes),
        }

    def _match_rules(self, test_name, metrics, targets):
        """规则匹配"""
        findings = []

        for rule_id, rule in self.rules.items():
            evidence = []

            # 检查条件
            for condition in rule.get("conditions", []):
                metric_name = condition.get("metric")
                op = condition.get("op")
                threshold = condition.get("value")

                # 获取实际值
                actual = self._get_metric_value(test_name, metric_name, metrics, targets)
                if actual is None:
                    continue

                # 计算阈值
                if isinstance(threshold, str) and "target" in threshold:
                    target_val = targets.get(test_name, 0)
                    threshold = eval(threshold.replace("target", str(target_val)))

                # 判断条件
                matched = False
                if op == ">" and actual > threshold:
                    matched = True
                    evidence.append(f"{metric_name}={actual:.2f} > {threshold}")
                elif op == "<" and actual < threshold:
                    matched = True
                    evidence.append(f"{metric_name}={actual:.2f} < {threshold}")
                elif op == ">=" and actual >= threshold:
                    matched = True
                elif op == "<=" and actual <= threshold:
                    matched = True

            if evidence:
                findings.append(
                    {
                        "type": rule_id,
                        "name": rule.get("name", rule_id),
                        "confidence": rule.get("confidence", 0.5),
                        "evidence": evidence,
                        "suggestions": rule.get("suggestions", []),
                    }
                )

        return findings

    def _get_metric_value(self, test_name, metric_name, metrics, targets):
        """获取指标值"""
        # 直接映射
        metric_map = {
            "seq_write_burst": "bandwidth",
            "seq_write_sustained": "bandwidth",
            "seq_read_burst": "bandwidth",
            "seq_read_sustained": "bandwidth",
            "rand_read_burst": "iops",
            "rand_read_sustained": "iops",
            "rand_write_burst": "iops",
            "rand_write_sustained": "iops",
            "latency_p99999": "latency_p99999",
            "latency_p999": "latency_p999",
            "latency_p99": "latency_p99",
            "latency_p50": "latency_p50",
            "latency_stddev": "latency_stddev",
            "latency_avg": "latency_avg",
            "iops": "iops",
            "bandwidth": "bandwidth",
            "total_bandwidth": "bandwidth",
            "read_bandwidth": "bandwidth",
        }

        mapped = metric_map.get(metric_name, metric_name)
        value = metrics.get(mapped, None)

        # 特殊处理：性能下降比例
        if metric_name == "performance_drop":
            target = targets.get(test_name, 0)
            if target > 0 and value:
                return (target - value) / target
            return None

        # 特殊处理：延迟比率 p9999/p50
        if metric_name == "latency_ratio_p9999_p50":
            p99999 = metrics.get("latency_p99999", 0)
            p50 = metrics.get("latency_p50", 1)
            if p50 > 0 and p99999:
                return p99999 / p50
            return None

        return value

    def _analyze_correlations(self, test_name, metrics, test_case):
        """关联分析"""
        findings = []

        # 分析 1: Burst vs Sustained 性能差异
        if "sustained" in test_name:
            burst_name = test_name.replace("sustained", "burst")
            # 这里可以对比历史数据，暂时简化

        # 分析 2: 延迟分布分析
        p99999 = metrics.get("latency_p99999", 0)
        p50 = metrics.get("latency_p50", 1)

        if p50 > 0 and p99999 / p50 > 100:
            findings.append(
                {
                    "type": "LATENCY_TAIL",
                    "name": "延迟长尾",
                    "confidence": 0.7,
                    "evidence": [f"p99999/p50={p99999/p50:.1f}，长尾严重"],
                    "suggestions": ["可能存在 GC 或调度干扰", "检查系统负载情况"],
                }
            )

        return findings

    def _synthesize_root_causes(self, findings):
        """综合根因定位"""
        if not findings:
            return []

        # 按类型分组
        by_type = {}
        for finding in findings:
            type_ = finding.get("type", "UNKNOWN")
            if type_ not in by_type:
                by_type[type_] = []
            by_type[type_].append(finding)

        # 计算综合置信度
        root_causes = []
        for type_, type_findings in by_type.items():
            avg_confidence = sum(f["confidence"] for f in type_findings) / len(type_findings)
            evidence_bonus = min(0.5, len(type_findings) * 0.1)
            final_confidence = min(0.99, avg_confidence * (1 + evidence_bonus))

            # 合并证据和建议
            all_evidence = []
            all_suggestions = []
            for f in type_findings:
                all_evidence.extend(f.get("evidence", []))
                all_suggestions.extend(f.get("suggestions", []))

            # 去重
            all_evidence = list(dict.fromkeys(all_evidence))
            all_suggestions = list(dict.fromkeys(all_suggestions))

            root_causes.append(
                {
                    "type": type_,
                    "name": type_findings[0].get("name", type_),
                    "confidence": final_confidence,
                    "evidence_count": len(type_findings),
                    "evidence": all_evidence,
                    "suggestions": all_suggestions,
                }
            )

        # 按置信度排序
        root_causes.sort(key=lambda x: x["confidence"], reverse=True)

        return root_causes

    def _generate_summary(self, root_causes):
        """生成分析摘要"""
        if not root_causes:
            return "✅ 未检测到明显失效原因"

        top_cause = root_causes[0]
        return f"🔴 主要根因：{top_cause['name']} (置信度：{top_cause['confidence']*100:.0f}%)"
