#!/usr/bin/env python3
"""
性能基线对比工具

对比开发板和 CI/CD 环境的性能测试结果，确保环境一致性。

使用方法:
    python3 bin/compare_baseline.py --dev results/dev_board/ --ci results/ci/
    python3 bin/compare_baseline.py --baseline1 results/test1/ --baseline2 results/test2/
"""

import sys
import json
import argparse
from pathlib import Path
from datetime import datetime

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))


def load_results(results_dir):
    """加载测试结果"""
    results_path = Path(results_dir) / "results.json"
    
    if not results_path.exists():
        raise FileNotFoundError(f"测试结果不存在：{results_path}")
    
    with open(results_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def extract_metrics(results):
    """提取关键性能指标"""
    metrics = {}
    
    for test_case in results.get('test_cases', []):
        name = test_case['name']
        status = test_case['status']
        
        # 提取关键指标
        test_metrics = {}
        if 'metrics' in test_case:
            metrics_data = test_case['metrics']
            
            # 带宽 (MB/s)
            if 'bandwidth' in metrics_data:
                test_metrics['bandwidth'] = metrics_data['bandwidth'].get('value', 0)
            
            # IOPS
            if 'iops' in metrics_data:
                test_metrics['iops'] = metrics_data['iops'].get('value', 0)
            
            # 延迟 (us)
            if 'latency_avg' in metrics_data:
                test_metrics['latency'] = metrics_data['latency_avg'].get('value', 0)
        
        metrics[name] = {
            'status': status,
            'metrics': test_metrics
        }
    
    return metrics


def compare_metrics(dev_metrics, ci_metrics, threshold=0.10):
    """
    对比性能指标
    
    Args:
        dev_metrics: 开发板性能数据
        ci_metrics: CI/CD 性能数据
        threshold: 允许的性能差异比例 (默认 10%)
    
    Returns:
        dict: 对比结果
    """
    comparison = {
        'timestamp': datetime.now().isoformat(),
        'tests': [],
        'summary': {
            'total': 0,
            'passed': 0,
            'failed': 0,
            'warnings': 0
        }
    }
    
    # 对比每个测试用例
    all_tests = set(dev_metrics.keys()) | set(ci_metrics.keys())
    
    for test_name in sorted(all_tests):
        dev_data = dev_metrics.get(test_name, {})
        ci_data = ci_metrics.get(test_name, {})
        
        test_result = {
            'name': test_name,
            'dev_status': dev_data.get('status', 'N/A'),
            'ci_status': ci_data.get('status', 'N/A'),
            'metrics': []
        }
        
        comparison['summary']['total'] += 1
        
        # 对比各项指标
        all_metrics = set(dev_data.get('metrics', {}).keys()) | set(ci_data.get('metrics', {}).keys())
        
        for metric_name in all_metrics:
            dev_value = dev_data.get('metrics', {}).get(metric_name, 0)
            ci_value = ci_data.get('metrics', {}).get(metric_name, 0)
            
            if dev_value == 0:
                continue
            
            # 计算差异比例
            diff_ratio = abs(ci_value - dev_value) / dev_value
            diff_percent = diff_ratio * 100
            
            # 判断是否通过
            if diff_ratio <= threshold:
                status = 'PASS'
                comparison['summary']['passed'] += 1
            elif diff_ratio <= threshold * 1.5:  # 警告阈值放宽 50%
                status = 'WARNING'
                comparison['summary']['warnings'] += 1
            else:
                status = 'FAIL'
                comparison['summary']['failed'] += 1
            
            # 确定单位
            unit = 'MB/s' if 'bandwidth' in metric_name else 'IOPS' if 'iops' in metric_name else 'us'
            
            test_result['metrics'].append({
                'name': metric_name,
                'dev_value': dev_value,
                'ci_value': ci_value,
                'diff_percent': diff_percent,
                'status': status,
                'unit': unit
            })
        
        comparison['tests'].append(test_result)
    
    return comparison


def generate_report(comparison, output_path=None):
    """生成对比报告"""
    report = []
    report.append("=" * 80)
    report.append("UFS SysTest 性能基线对比报告")
    report.append("=" * 80)
    report.append(f"生成时间：{comparison['timestamp']}")
    report.append("")
    
    # 摘要
    summary = comparison['summary']
    report.append("📊 对比摘要")
    report.append("-" * 40)
    report.append(f"总测试数：{summary['total']}")
    report.append(f"✅ 通过：{summary['passed']} ({summary['passed']/summary['total']*100:.1f}%)")
    report.append(f"⚠️  警告：{summary['warnings']}")
    report.append(f"❌ 失败：{summary['failed']}")
    report.append("")
    
    # 详细结果
    report.append("📋 详细对比")
    report.append("-" * 40)
    
    for test in comparison['tests']:
        report.append(f"\n测试：{test['name']}")
        report.append(f"  开发板：{test['dev_status']}")
        report.append(f"  CI/CD:  {test['ci_status']}")
        
        for metric in test['metrics']:
            status_icon = "✅" if metric['status'] == 'PASS' else "⚠️" if metric['status'] == 'WARNING' else "❌"
            report.append(f"  {status_icon} {metric['name']}:")
            report.append(f"      开发板：{metric['dev_value']:.2f} {metric['unit']}")
            report.append(f"      CI/CD:  {metric['ci_value']:.2f} {metric['unit']}")
            report.append(f"      差异：{metric['diff_percent']:.2f}% [{metric['status']}]")
    
    report.append("")
    report.append("=" * 80)
    
    # 总体评价
    if summary['failed'] == 0 and summary['warnings'] == 0:
        report.append("✅ 环境一致性优秀！所有性能指标差异在允许范围内。")
    elif summary['failed'] == 0:
        report.append("⚠️  环境一致性良好，存在轻微性能差异，建议关注。")
    else:
        report.append("❌ 环境一致性存在问题，性能差异超出允许范围。")
        report.append("\n建议检查:")
        report.append("  1. CI/CD 环境与开发板的硬件配置是否一致")
        report.append("  2. Linux 内核版本和 UFS 驱动版本")
        report.append("  3. FIO 版本和测试参数")
        report.append("  4. 系统负载和后台进程干扰")
    
    report.append("=" * 80)
    
    report_text = "\n".join(report)
    print(report_text)
    
    # 保存报告
    if output_path:
        output_file = Path(output_path)
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(report_text)
        print(f"\n报告已保存：{output_file}")
    
    return comparison['summary']['failed'] == 0


def main():
    parser = argparse.ArgumentParser(description='性能基线对比工具')
    parser.add_argument('--dev', help='开发板测试结果目录')
    parser.add_argument('--ci', help='CI/CD 测试结果目录')
    parser.add_argument('--baseline1', help='第一个基线测试结果目录')
    parser.add_argument('--baseline2', help='第二个基线测试结果目录')
    parser.add_argument('--threshold', type=float, default=0.10, 
                        help='允许的性能差异比例 (默认 0.10 = 10%%)')
    parser.add_argument('--output', help='报告输出路径')
    
    args = parser.parse_args()
    
    # 确定输入目录
    if args.dev and args.ci:
        dir1 = args.dev
        dir2 = args.ci
        label1 = "开发板"
        label2 = "CI/CD"
    elif args.baseline1 and args.baseline2:
        dir1 = args.baseline1
        dir2 = args.baseline2
        label1 = "基线 1"
        label2 = "基线 2"
    else:
        parser.error("请指定 --dev 和 --ci，或 --baseline1 和 --baseline2")
    
    print(f"加载测试结果...")
    print(f"  {label1}: {dir1}")
    print(f"  {label2}: {dir2}")
    print()
    
    try:
        # 加载结果
        results1 = load_results(dir1)
        results2 = load_results(dir2)
        
        # 提取指标
        metrics1 = extract_metrics(results1)
        metrics2 = extract_metrics(results2)
        
        # 对比
        comparison = compare_metrics(metrics1, metrics2, args.threshold)
        
        # 生成报告
        passed = generate_report(comparison, args.output)
        
        sys.exit(0 if passed else 1)
        
    except FileNotFoundError as e:
        print(f"❌ 错误：{e}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ 错误：{e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
