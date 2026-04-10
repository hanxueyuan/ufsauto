#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
报告生成器 - 增强版测试报告生成

功能：
- 系统信息（OS/内核/Python/FIO 版本）
- 硬件信息（设备类型/路径/容量）
- 系统资源（CPU/内存/磁盘）
- 测试模式（开发/生产）
- 测试配置参数
- 测试用例详情表
- 性能对比表（目标值 vs 实际值）
- 问题分析章节
- 改进建议章节

用法：
    from report_generator import ReportGenerator

    generator = ReportGenerator()
    report_path = generator.generate_markdown(report_data, output_dir='reports')
"""

import json
import logging
import subprocess
import platform
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)

def get_system_info() -> Dict[str, Any]:
    """获取系统信息"""
    info = {
        'os': platform.system(),
        'os_version': platform.version(),
        'kernel': platform.release(),
        'python_version': platform.python_version(),
        'architecture': platform.machine(),
        'hostname': platform.node(),
        'timestamp': datetime.now().isoformat()
    }

    try:
        result = subprocess.run(['fio', '--version'], capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            info['fio_version'] = result.stdout.strip()
    except Exception as e:
        info['fio_version'] = f'Error: {e}'

    return info

def get_hardware_info(device: str = '/dev/vda') -> Dict[str, Any]:
    """获取硬件信息"""
    info = {
        'device': device,
        'device_exists': Path(device).exists() if device else False,
        'device_type': 'Unknown',
        'capacity': 'Unknown'
    }

    if info['device_exists']:
        try:
            result = subprocess.run(
                ['lsblk', '-dnpo', 'NAME,TYPE,SIZE', device],
                capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0:
                parts = result.stdout.strip().split()
                if len(parts) >= 3:
                    info['device_type'] = parts[1]
                    info['capacity'] = parts[2]
        except Exception as e:
            info['device_error'] = str(e)

    try:
        result = subprocess.run(['df', '-B1', '/'], capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            lines = result.stdout.strip().split('\n')
            if len(lines) >= 2:
                parts = lines[1].split()
                info['root_capacity'] = {
                    'total': int(parts[1]) / (1024**3),
                    'used': int(parts[2]) / (1024**3),
                    'available': int(parts[3]) / (1024**3)
                }
    except Exception as e:
        pass

    return info

def get_resource_info() -> Dict[str, Any]:
    """获取系统资源信息"""
    info = {
        'cpu': {},
        'memory': {},
        'disk': {}
    }

    try:
        result = subprocess.run(['nproc'], capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            info['cpu']['cores'] = int(result.stdout.strip())
    except:
        pass

    try:
        result = subprocess.run(['free', '-m'], capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            lines = result.stdout.strip().split('\n')
            for line in lines:
                if line.startswith('Mem:'):
                    parts = line.split()
                    info['memory'] = {
                        'total_mb': int(parts[1]),
                        'used_mb': int(parts[2]),
                        'free_mb': int(parts[3]),
                        'available_mb': int(parts[6]) if len(parts) > 6 else 0
                    }
                    break
    except:
        pass

    return info

class ReportGenerator:
    """增强版报告生成器"""

    def __init__(self):
        self.reports_dir = Path(__file__).parent / 'reports'
        self.reports_dir.mkdir(parents=True, exist_ok=True)

        self.performance_targets = {
            'seq_read_burst': {'bandwidth_mbps': 500, 'iops': 10000, 'latency_us': 100},
            'seq_write_burst': {'bandwidth_mbps': 200, 'iops': 5000, 'latency_us': 200},
            'rand_read_burst': {'bandwidth_mbps': 100, 'iops': 50000, 'latency_us': 50},
            'rand_write_burst': {'bandwidth_mbps': 50, 'iops': 20000, 'latency_us': 100},
            'mixed_rw': {'bandwidth_mbps': 80, 'iops': 30000, 'latency_us': 80},
            'qos_latency': {'bandwidth_mbps': 100, 'iops': 50000, 'latency_us': 50}
        }

    def generate_markdown(
        self,
        report_data: Dict[str, Any],
        output_dir: Optional[str] = None,
        filename: Optional[str] = None
    ) -> str:
        """
        生成 Markdown 格式报告

        Args:
            report_data: 报告数据
            output_dir: 输出目录
            filename: 文件名（可选）

        Returns:
            报告文件路径
        """
        if output_dir:
            output_path = Path(output_dir)
        else:
            output_path = self.reports_dir

        output_path.mkdir(parents=True, exist_ok=True)

        if filename:
            report_file = output_path / filename
        else:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            report_file = output_path / f'report_{timestamp}.md'

        content = self._generate_markdown_content(report_data)

        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(content)

        logger.info(f"报告已生成：{report_file}")
        return str(report_file)

    def _generate_markdown_content(self, report_data: Dict[str, Any]) -> str:
        """生成 Markdown 报告内容"""
        lines = []

        lines.append("# UFS Auto 测试报告\n")
        lines.append(f"**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        lines.append(f"**测试 ID**: {report_data.get('test_id', 'N/A')}\n")
        lines.append("")

        lines.append("## 1. 测试环境\n")
        lines.append("### 1.1 系统信息\n")
        sys_info = get_system_info()
        lines.append(f"- **操作系统**: {sys_info['os']} {sys_info['os_version']}")
        lines.append(f"- **内核版本**: {sys_info['kernel']}")
        lines.append(f"- **Python 版本**: {sys_info['python_version']}")
        lines.append(f"- **FIO 版本**: {sys_info['fio_version']}")
        lines.append(f"- **架构**: {sys_info['architecture']}")
        lines.append(f"- **主机名**: {sys_info['hostname']}")
        lines.append("")

        lines.append("### 1.2 硬件信息\n")
        hw_info = get_hardware_info(report_data.get('device', '/dev/vda'))
        lines.append(f"- **测试设备**: {hw_info['device']}")
        lines.append(f"- **设备类型**: {hw_info['device_type']}")
        lines.append(f"- **设备容量**: {hw_info['capacity']}")
        if 'root_capacity' in hw_info:
            rc = hw_info['root_capacity']
            lines.append(f"- **根分区容量**: {rc['total']:.1f}GB (已用：{rc['used']:.1f}GB, 可用：{rc['available']:.1f}GB)")
        lines.append("")

        lines.append("### 1.3 系统资源\n")
        res_info = get_resource_info()
        if 'cpu' in res_info and 'cores' in res_info['cpu']:
            lines.append(f"- **CPU 核心数**: {res_info['cpu']['cores']}")
        if 'memory' in res_info and 'total_mb' in res_info['memory']:
            m = res_info['memory']
            lines.append(f"- **内存**: {m['total_mb']}MB (可用：{m['available_mb']}MB)")
        lines.append("")

        lines.append("## 2. 测试方法\n")
        lines.append("### 2.1 测试模式\n")
        test_mode = report_data.get('test_mode', 'development')
        mode_desc = "开发模式（快速验证）" if test_mode == 'development' else "生产模式（完整测试）"
        lines.append(f"- **测试模式**: {mode_desc}")
        lines.append(f"- **测试时长**: {report_data.get('total_duration', 0):.1f}秒")
        lines.append("")

        lines.append("### 2.2 测试配置参数\n")
        config = report_data.get('config', {})
        lines.append(f"- **块大小 (bs)**: {config.get('bs', 'N/A')}")
        lines.append(f"- **测试大小 (size)**: {config.get('size', 'N/A')}")
        lines.append(f"- **运行时间 (runtime)**: {config.get('runtime', 'N/A')}秒")
        lines.append(f"- **IO 引擎 (ioengine)**: {config.get('ioengine', 'N/A')}")
        lines.append(f"- **IO 深度 (iodepth)**: {config.get('iodepth', 'N/A')}")
        lines.append("")

        lines.append("### 2.3 测试用例详情\n")
        lines.append("| 测试用例 | 类型 | 读写模式 | 块大小 | IO 深度 | 状态 |")
        lines.append("|---------|------|---------|--------|--------|------|")

        test_cases = report_data.get('test_cases', [])
        for tc in test_cases:
            name = tc.get('name', 'N/A')
            ttype = tc.get('type', 'N/A')
            rw = tc.get('rw_mode', 'N/A')
            cfg = tc.get('test_config', {})
            bs = cfg.get('bs', config.get('bs', 'N/A'))
            iodepth = cfg.get('iodepth', config.get('iodepth', 'N/A'))
            status = "✅ 通过" if tc.get('status') == 'PASS' else f"❌ {tc.get('status', 'UNKNOWN')}"
            lines.append(f"| {name} | {ttype} | {rw} | {bs} | {iodepth} | {status} |")
        lines.append("")

        lines.append("## 3. 性能对比\n")
        lines.append("### 3.1 目标值 vs 实际值\n")
        lines.append("| 测试用例 | 指标 | 目标值 | 实际值 | 达标率 | 状态 |")
        lines.append("|---------|------|--------|--------|--------|------|")

        for tc in test_cases:
            name = tc.get('name', 'N/A')
            if tc.get('status') != 'PASS':
                lines.append(f"| {name} | - | - | - | - | ❌ 失败 |")
                continue

            metrics = self.performance_targets.get(name, {})
            actual_bw = tc.get('bandwidth_mbps', 0)
            actual_iops = tc.get('iops', 0)
            actual_lat = tc.get('avg_latency_us', 0)

            if 'bandwidth_mbps' in metrics:
                target = metrics['bandwidth_mbps']
                rate = (actual_bw / target * 100) if target > 0 else 0
                status = "✅" if rate >= 100 else "⚠️" if rate >= 80 else "❌"
                lines.append(f"| {name} | 带宽 (MB/s) | {target} | {actual_bw:.1f} | {rate:.1f}% | {status} |")

            if 'iops' in metrics:
                target = metrics['iops']
                rate = (actual_iops / target * 100) if target > 0 else 0
                status = "✅" if rate >= 100 else "⚠️" if rate >= 80 else "❌"
                lines.append(f"| {name} | IOPS | {target} | {actual_iops:.0f} | {rate:.1f}% | {status} |")

            if 'latency_us' in metrics:
                target = metrics['latency_us']
                rate = (target / actual_lat * 100) if actual_lat > 0 else 0
                status = "✅" if actual_lat <= target else "⚠️" if actual_lat <= target * 1.2 else "❌"
                lines.append(f"| {name} | 延迟 (μs) | ≤{target} | {actual_lat:.1f} | {rate:.1f}% | {status} |")

        lines.append("")

        total_tests = len(test_cases)
        passed_tests = sum(1 for tc in test_cases if tc.get('status') == 'PASS')
        pass_rate = (passed_tests / total_tests * 100) if total_tests > 0 else 0
        lines.append(f"**总体达标率**: {pass_rate:.1f}% ({passed_tests}/{total_tests})\n")
        lines.append("")

        lines.append("## 4. 问题分析\n")

        failed_tests = [tc for tc in test_cases if tc.get('status') != 'PASS']
        underperforming = []

        for tc in test_cases:
            if tc.get('status') != 'PASS':
                continue
            name = tc.get('name', 'N/A')
            metrics = self.performance_targets.get(name, {})
            actual_bw = tc.get('bandwidth_mbps', 0)
            actual_lat = tc.get('avg_latency_us', 0)

            if 'bandwidth_mbps' in metrics and actual_bw < metrics['bandwidth_mbps'] * 0.8:
                underperforming.append({
                    'name': name,
                    'issue': f"带宽低于目标值的 80% (实际：{actual_bw:.1f}, 目标：{metrics['bandwidth_mbps']})"
                })
            if 'latency_us' in metrics and actual_lat > metrics['latency_us'] * 1.2:
                underperforming.append({
                    'name': name,
                    'issue': f"延迟高于目标值的 120% (实际：{actual_lat:.1f}, 目标：≤{metrics['latency_us']})"
                })

        if failed_tests or underperforming:
            lines.append("### 4.1 未达标项目\n")

            for tc in failed_tests:
                name = tc.get('name', 'N/A')
                status = tc.get('status', 'UNKNOWN')
                error = tc.get('error', 'Unknown error')
                lines.append(f"#### {name}")
                lines.append(f"- **状态**: {status}")
                lines.append(f"- **错误**: {error}")
                lines.append(f"- **可能原因**:")
                if 'timeout' in error.lower() or 'timeout' in status.lower():
                    lines.append("  - 设备响应慢或无响应")
                    lines.append("  - 系统资源不足")
                    lines.append("  - IO 阻塞")
                elif 'permission' in error.lower():
                    lines.append("  - 权限不足")
                    lines.append("  - 设备路径错误")
                else:
                    lines.append("  - 需要查看详细日志")
                lines.append(f"- **验证方法**:")
                lines.append("  - 检查系统日志：`dmesg | tail -50`")
                lines.append("  - 检查设备状态：`lsblk`")
                lines.append("  - 重新运行测试验证")
                lines.append("")

            for item in underperforming:
                lines.append(f"#### {item['name']}")
                lines.append(f"- **问题**: {item['issue']}")
                lines.append(f"- **可能原因**:")
                lines.append("  - 设备性能瓶颈")
                lines.append("  - 系统资源竞争")
                lines.append("  - 测试配置不当")
                lines.append(f"- **验证方法**:")
                lines.append("  - 监控系统资源使用情况")
                lines.append("  - 检查其他 IO 负载")
                lines.append("  - 调整测试参数重新测试")
                lines.append("")
        else:
            lines.append("✅ 所有测试用例均达标，无需分析。\n")

        lines.append("")

        specific_actions = []

        for tc in failed_tests:
            name = tc.get('name', 'N/A')
            error = tc.get('error', '').lower()
            status = tc.get('status', 'UNKNOWN')

            if 'timeout' in error or 'timeout' in status.lower():
                specific_actions.append(f"**{name}**: 检查设备响应超时 - 查看 dmesg 日志确认设备状态")
            elif 'permission' in error:
                specific_actions.append(f"**{name}**: 修复权限问题 - 使用 sudo 或将用户加入 disk 组")
            elif 'no space' in error or 'space' in error:
                specific_actions.append(f"**{name}**: 释放磁盘空间或指定 --test-dir 到其他分区")
            elif 'not found' in error:
                specific_actions.append(f"**{name}**: 验证设备路径是否正确 - 运行 lsblk 确认")
            elif 'fio' in error:
                specific_actions.append(f"**{name}**: 检查 FIO 工具安装 - 运行 'which fio' 验证")

        for item in underperforming:
            name = item['name']
            if '带宽' in item['issue']:
                specific_actions.append(f"**{name}**: 带宽不达标 - 检查 IO 调度器、设备队列深度")
            elif '延迟' in item['issue']:
                specific_actions.append(f"**{name}**: 延迟过高 - 检查系统负载、CPU 频率调节")

        if specific_actions:
            lines.append("## 5. 改进建议\n")
            lines.append("### 5.1 具体改进行动\n")
            for i, action in enumerate(specific_actions, 1):
                lines.append(f"{i}. {action}")
            lines.append("")
            lines.append("### 5.2 通用建议\n")
            lines.append("- 查看详细日志文件定位具体问题")
            lines.append("- 检查系统资源使用情况 (CPU/内存/IO)")
            lines.append("- 对比历史测试结果分析趋势")
            lines.append("")

        lines.append("---\n")
        lines.append("*报告由 UFS Auto 自动生成*\n")

        return '\n'.join(lines)

    def generate_json(self, report_data: Dict[str, Any], output_dir: Optional[str] = None) -> str:
        """生成 JSON 格式报告"""
        if output_dir:
            output_path = Path(output_dir)
        else:
            output_path = self.reports_dir

        output_path.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        report_file = output_path / f'report_{timestamp}.json'

        enhanced_data = report_data.copy()
        enhanced_data['system_info'] = get_system_info()
        enhanced_data['hardware_info'] = get_hardware_info(report_data.get('device', '/dev/vda'))
        enhanced_data['resource_info'] = get_resource_info()
        enhanced_data['generated_at'] = datetime.now().isoformat()

        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(enhanced_data, f, indent=2, ensure_ascii=False)

        logger.info(f"JSON 报告已生成：{report_file}")
        return str(report_file)

def main():
    """测试报告生成器"""
    sample_data = {
        'test_id': 'Test_20260409_120000',
        'test_mode': 'development',
        'device': '/dev/vda',
        'total_duration': 31.3,
        'config': {
            'bs': '128k',
            'size': '64M',
            'runtime': 5,
            'ioengine': 'sync',
            'iodepth': 1
        },
        'test_cases': [
            {
                'name': 'seq_read_burst',
                'type': 'performance',
                'rw_mode': 'read',
                'status': 'PASS',
                'bandwidth_mbps': 50447.4,
                'iops': 403579,
                'avg_latency_us': 2.3,
                'test_config': {'bs': '128k', 'iodepth': 1}
            },
            {
                'name': 'seq_write_burst',
                'type': 'performance',
                'rw_mode': 'write',
                'status': 'PASS',
                'bandwidth_mbps': 195.2,
                'iops': 1562,
                'avg_latency_us': 639.8,
                'test_config': {'bs': '128k', 'iodepth': 1}
            }
        ]
    }

    generator = ReportGenerator()
    report_path = generator.generate_markdown(sample_data)
    print(f"报告已生成：{report_path}")

if __name__ == '__main__':
    main()
