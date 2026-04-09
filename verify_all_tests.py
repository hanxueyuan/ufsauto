#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
开发模式 - 批量验证所有测试用例

用途：用开发模式快速验证所有测试用例能正常执行
- 每个用例 5 秒测试时间
- 64MB 测试大小
- 跳过预填充
- 只验证框架能跑通

用法：
    python3 verify_all_tests.py
"""

import sys
import os
import json
import logging
import time
import traceback
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any

# Add systest directory to Python path
systest_dir = Path(__file__).parent / 'systest'
sys.path.insert(0, str(systest_dir / 'core'))
sys.path.insert(0, str(systest_dir / 'tools'))

from logger import get_logger
from report_generator import ReportGenerator
import subprocess

# 导入新增的模块（如果可用）
try:
    from history_comparison import HistoryComparator
    HAS_HISTORY_COMPARISON = True
except ImportError:
    HAS_HISTORY_COMPARISON = False

try:
    from chart_generator import ChartGenerator
    HAS_CHART_GENERATOR = True
except ImportError:
    HAS_CHART_GENERATOR = False


class TestVerifier:
    """测试验证器 - 批量验证所有测试用例"""

    def __init__(self, device='/dev/vda', test_dir=Path('/tmp/ufs_test'), verbose=True):
        self.device = device
        self.test_dir = test_dir
        self.verbose = verbose
        self.test_id = f"VerifyAll_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # 确保日志目录存在
        log_dir = Path(__file__).parent / 'logs'
        log_dir.mkdir(parents=True, exist_ok=True)
        
        # 创建结果目录（用于保存 FIO 原始输出）
        self.results_dir = Path(__file__).parent / 'results' / self.test_id
        self.results_dir.mkdir(parents=True, exist_ok=True)
        
        self.logger = get_logger(
            test_id=self.test_id,
            log_dir=str(log_dir),
            console_level=logging.INFO,
            file_level=logging.DEBUG
        )
        self.results = []
        self.fio_outputs = {}  # 保存 FIO 原始输出
        
        # 开发模式配置
        self.dev_config = {
            'bs': '128k',
            'size': '64M',
            'runtime': 5,
            'ramp_time': 0,
            'ioengine': 'sync',
            'iodepth': 1,
            'skip_prefill': True
        }

    def verify_fio(self) -> bool:
        """验证 FIO 工具"""
        self.logger.info("验证 FIO 工具...")
        try:
            result = subprocess.run(['fio', '--version'], capture_output=True, text=True)
            if result.returncode == 0:
                self.logger.info(f"✓ FIO 已安装：{result.stdout.strip()}")
                return True
            else:
                self.logger.error(f"FIO 未安装")
                return False
        except Exception as e:
            self.logger.error(f"FIO 验证失败：{e}")
            return False

    def verify_environment(self) -> bool:
        """验证测试环境"""
        self.logger.info("验证测试环境...")
        
        # 检查设备（可选）
        if os.path.exists(self.device):
            self.logger.info(f"✓ 设备存在：{self.device}")
        else:
            self.logger.warning(f"⚠ 设备不存在：{self.device}（继续验证）")
        
        # 检查空间
        try:
            result = subprocess.run(['df', '-B1', str(self.test_dir.parent)],
                                    capture_output=True, text=True)
            if result.returncode == 0:
                lines = result.stdout.strip().split('\n')
                if len(lines) >= 2:
                    parts = lines[1].split()
                    avail = int(parts[3]) / (1024**3)
                    if avail < 1.0:
                        self.logger.error(f"可用空间不足：{avail:.1f}GB")
                        return False
                    self.logger.info(f"✓ 可用空间：{avail:.1f}GB")
        except Exception as e:
            self.logger.warning(f"空间检查跳过：{e}")
        
        # 创建测试目录
        self.test_dir.mkdir(parents=True, exist_ok=True)
        self.logger.info(f"✓ 测试目录：{self.test_dir}")
        
        return True

    def run_test(self, test_name: str, test_type: str, rw_mode: str, 
                 extra_args: Dict = None) -> Dict[str, Any]:
        """运行单个测试（增强版 - 保存 FIO 输出和堆栈跟踪）"""
        self.logger.info(f"运行测试：{test_name} ({test_type})")
        
        # 记录测试配置
        config = self.dev_config.copy()
        if extra_args:
            config.update(extra_args)
        
        self.logger.info(f"测试配置：{json.dumps(config)}")
        
        test_file = self.test_dir / f"ufs_test_{test_name}"
        start_time = time.time()
        fio_cmd = None
        
        try:
            # 创建测试文件
            with open(test_file, 'wb') as f:
                f.seek(64 * 1024 * 1024 - 1)
                f.write(b'\0')
            
            # 构建 FIO 命令
            fio_cmd = [
                'fio',
                f'--name={test_name}',
                f'--filename={test_file}',
                f'--rw={rw_mode}',
                f'--bs={config["bs"]}',
                f'--size={config["size"]}',
                f'--runtime={config["runtime"]}',
                f'--ioengine={config["ioengine"]}',
                f'--iodepth={config["iodepth"]}',
                '--direct=1',
                '--time_based',
                '--output-format=json'
            ]
            
            # 执行测试（合并 stdout 和 stderr）
            result = subprocess.run(fio_cmd, capture_output=True, text=True, 
                                    timeout=config['runtime'] + 30)
            
            elapsed = time.time() - start_time
            
            # 保存 FIO 原始输出（包含 stdout 和 stderr）
            fio_output_data = {
                'stdout': result.stdout,
                'stderr': result.stderr,
                'returncode': result.returncode,
                'command': ' '.join(fio_cmd),
                'timestamp': datetime.now().isoformat()
            }
            self.fio_outputs[test_name] = fio_output_data
            
            # 保存 FIO 输出到 results/<test_id>/ 目录
            fio_file = self.results_dir / f"fio_output_{test_name}.json"
            try:
                with open(fio_file, 'w', encoding='utf-8') as f:
                    json.dump(fio_output_data, f, indent=2, ensure_ascii=False)
                self.logger.info(f"✓ FIO 输出已保存：{fio_file}")
            except Exception as e:
                self.logger.error(f"保存 FIO 输出失败：{e}")
            
            # 合并输出（FIO 可能输出到任一位置）
            combined_output = result.stdout + result.stderr
            
            if result.returncode != 0 and not combined_output.strip().startswith('{'):
                error_msg = f"FIO execution failed (exit code={result.returncode})"
                self.logger.error(f"✗ {test_name} 失败：{error_msg}")
                self.logger.error(f"标准错误：{result.stderr}")
                
                return {
                    'name': test_name,
                    'type': test_type,
                    'rw_mode': rw_mode,
                    'status': 'ERROR',
                    'error': error_msg,
                    'fio_stderr': result.stderr,
                    'fio_exit_code': result.returncode,
                    'elapsed': elapsed
                }
            
            # 解析结果（从容错的合并输出中查找 JSON）
            try:
                # 尝试从合并输出中查找 JSON
                json_start = combined_output.find('{')
                json_end = combined_output.rfind('}') + 1
                if json_start >= 0 and json_end > json_start:
                    json_str = combined_output[json_start:json_end]
                    fio_output = json.loads(json_str)
                else:
                    fio_output = json.loads(combined_output)
            except json.JSONDecodeError as e:
                error_msg = f'JSON parse error: {e}'
                self.logger.error(f"✗ {test_name} JSON 解析失败：{error_msg}")
                self.logger.error(f"输出内容：{combined_output[:500]}")
                stack_trace = traceback.format_exc()
                self.logger.error(f"堆栈跟踪:\n{stack_trace}")
                
                # FIO 输出已在上面保存
                
                return {
                    'name': test_name,
                    'type': test_type,
                    'rw_mode': rw_mode,
                    'status': 'ERROR',
                    'error': error_msg,
                    'raw_output': combined_output[:2000],
                    'stack_trace': stack_trace,
                    'elapsed': elapsed
                }
            job = fio_output.get('jobs', [{}])[0]
            
            # 根据读写类型获取统计
            io_type = 'read' if 'read' in rw_mode.lower() else 'write'
            if rw_mode == 'randrw' or rw_mode == 'rw':
                io_stats = job.get('read', {})  # 混合读写主要看读
            else:
                io_stats = job.get(io_type, {})
            
            bw_bytes = io_stats.get('bw_bytes', 0)
            bw_mbps = bw_bytes / (1024 * 1024)
            iops = io_stats.get('iops', 0)
            lat_ns = io_stats.get('lat_ns', {})
            avg_lat_us = lat_ns.get('mean', 0) / 1000
            
            # 清理测试文件
            try:
                test_file.unlink()
            except:
                pass
            
            self.logger.info(f"✓ {test_name} 完成 ({elapsed:.1f}s)")
            self.logger.info(f"  带宽：{bw_mbps:.1f} MB/s, IOPS: {iops:.0f}, 延迟：{avg_lat_us:.1f} μs")
            
            return {
                'name': test_name,
                'type': test_type,
                'rw_mode': rw_mode,
                'status': 'PASS',
                'bandwidth_mbps': bw_mbps,
                'iops': iops,
                'avg_latency_us': avg_lat_us,
                'elapsed': elapsed
            }
            
        except subprocess.TimeoutExpired:
            elapsed = time.time() - start_time
            error_msg = f"Test timeout (>{config['runtime'] + 30}s)"
            self.logger.error(f"✗ {test_name} 超时：{error_msg}")
            self.logger.error(f"命令：{' '.join(fio_cmd) if fio_cmd else 'N/A'}")
            stack_trace = traceback.format_exc()
            self.logger.error(f"堆栈跟踪:\n{stack_trace}")
            
            # FIO 输出已在上面保存
            
            return {
                'name': test_name,
                'type': test_type,
                'rw_mode': rw_mode,
                'status': 'TIMEOUT',
                'error': error_msg,
                'command': ' '.join(fio_cmd) if fio_cmd else 'N/A',
                'stack_trace': stack_trace,
                'elapsed': elapsed
            }
        except Exception as e:
            elapsed = time.time() - start_time
            error_msg = f"Test exception: {type(e).__name__}: {e}"
            self.logger.error(f"✗ {test_name} 异常：{error_msg}")
            self.logger.error(f"命令：{' '.join(fio_cmd) if fio_cmd else 'N/A'}")
            stack_trace = traceback.format_exc()
            self.logger.error(f"堆栈跟踪:\n{stack_trace}")
            
            # FIO 输出已在上面保存
            
            return {
                'name': test_name,
                'type': test_type,
                'rw_mode': rw_mode,
                'status': 'ERROR',
                'error': error_msg,
                'exception_type': type(e).__name__,
                'command': ' '.join(fio_cmd) if fio_cmd else 'N/A',
                'stack_trace': stack_trace,
                'elapsed': elapsed
            }

    def verify_all_tests(self) -> List[Dict]:
        """验证所有测试用例"""
        # 定义所有测试用例
        test_cases = [
            # Performance 套件
            ('seq_read_burst', 'performance', 'read', None),
            ('seq_write_burst', 'performance', 'write', None),
            ('rand_read_burst', 'performance', 'randread', {'bs': '4k', 'iodepth': 32}),
            ('rand_write_burst', 'performance', 'randwrite', {'bs': '4k', 'iodepth': 32}),
            ('mixed_rw', 'performance', 'randrw', {'bs': '4k', 'iodepth': 32, 'rwmixread': 70}),
            
            # QoS 套件
            ('qos_latency', 'qos', 'randread', {'bs': '4k', 'iodepth': 1}),
        ]
        
        self.logger.info(f"开始验证 {len(test_cases)} 个测试用例...")
        self.logger.info(f"开发模式配置：runtime={self.dev_config['runtime']}s, size={self.dev_config['size']}")
        self.logger.info("")
        
        total_start = time.time()
        
        for test_name, test_type, rw_mode, extra_args in test_cases:
            result = self.run_test(test_name, test_type, rw_mode, extra_args)
            self.results.append(result)
            self.logger.info("")
        
        total_elapsed = time.time() - total_start
        
        # 统计结果
        passed = sum(1 for r in self.results if r['status'] == 'PASS')
        failed = len(self.results) - passed
        
        self.logger.info("=" * 60)
        self.logger.info(f"验证完成：总计 {len(self.results)} 个测试用例")
        self.logger.info(f"  通过：{passed}")
        self.logger.info(f"  失败：{failed}")
        self.logger.info(f"  总耗时：{total_elapsed:.1f}秒")
        self.logger.info("=" * 60)
        
        return self.results
    
    def get_report_data(self, total_duration: float) -> Dict[str, Any]:
        """生成报告数据"""
        return {
            'test_id': self.test_id,
            'test_mode': 'development',
            'device': str(self.device),
            'total_duration': total_duration,
            'config': self.dev_config.copy(),
            'test_cases': self.results
        }

    def print_summary(self):
        """打印结果摘要"""
        print()
        print("=" * 70)
        print("  UFS Auto 开发模式 - 全部测试用例验证结果")
        print("=" * 70)
        print()
        
        # 按类型分组
        perf_results = [r for r in self.results if r['type'] == 'performance']
        qos_results = [r for r in self.results if r['type'] == 'qos']
        
        # Performance 套件
        print("📊 Performance 套件:")
        print("-" * 70)
        print(f"{'测试用例':<25} {'状态':<10} {'带宽 (MB/s)':<15} {'IOPS':<12} {'延迟 (μs)':<12} {'耗时 (s)':<10}")
        print("-" * 70)
        
        for r in perf_results:
            status = "✅ PASS" if r['status'] == 'PASS' else f"❌ {r['status']}"
            bw = f"{r.get('bandwidth_mbps', 0):.1f}" if 'bandwidth_mbps' in r else "-"
            iops = f"{r.get('iops', 0):.0f}" if 'iops' in r else "-"
            lat = f"{r.get('avg_latency_us', 0):.1f}" if 'avg_latency_us' in r else "-"
            elapsed = f"{r.get('elapsed', 0):.1f}"
            print(f"{r['name']:<25} {status:<10} {bw:<15} {iops:<12} {lat:<12} {elapsed:<10}")
        
        print()
        
        # QoS 套件
        print("📊 QoS 套件:")
        print("-" * 70)
        for r in qos_results:
            status = "✅ PASS" if r['status'] == 'PASS' else f"❌ {r['status']}"
            bw = f"{r.get('bandwidth_mbps', 0):.1f}" if 'bandwidth_mbps' in r else "-"
            iops = f"{r.get('iops', 0):.0f}" if 'iops' in r else "-"
            lat = f"{r.get('avg_latency_us', 0):.1f}" if 'avg_latency_us' in r else "-"
            elapsed = f"{r.get('elapsed', 0):.1f}"
            print(f"{r['name']:<25} {status:<10} 带宽：{bw} MB/s, IOPS: {iops}, 延迟：{lat} μs, 耗时：{elapsed}s")
        
        print()
        
        # 总体统计
        passed = sum(1 for r in self.results if r['status'] == 'PASS')
        total = len(self.results)
        total_time = sum(r.get('elapsed', 0) for r in self.results)
        
        print("=" * 70)
        print(f"总计：{total} 个测试用例 | 通过：{passed} | 失败：{total - passed} | 总耗时：{total_time:.1f}秒")
        print("=" * 70)
        
        if passed == total:
            print()
            print("✅ 所有测试用例验证通过！框架功能正常！")
            print()
        else:
            print()
            print(f"⚠️  有 {total - passed} 个测试用例失败，请检查日志")
            print()


def main():
    """主函数"""
    print()
    print("=" * 70)
    print("  UFS Auto 开发模式 - 批量验证所有测试用例")
    print("=" * 70)
    print()
    
    # 加载配置
    config_path = Path(__file__).parent / 'systest' / 'config' / 'runtime.json'
    device = '/dev/vda'
    test_dir = Path('/tmp/ufs_test')
    
    if config_path.exists():
        with open(config_path, 'r') as f:
            config = json.load(f)
            device = config.get('device', '/dev/vda')
            test_dir = Path(config.get('test_dir', '/tmp/ufs_test'))
    
    # 创建验证器
    verifier = TestVerifier(device=device, test_dir=test_dir)
    
    # 验证环境
    print("步骤 1/2: 验证测试环境")
    print("-" * 70)
    if not verifier.verify_fio():
        print("\n❌ FIO 验证失败，无法继续")
        return 1
    
    if not verifier.verify_environment():
        print("\n❌ 环境验证失败")
        return 1
    
    print()
    print("步骤 2/2: 运行所有测试用例")
    print("-" * 70)
    print()
    
    # 运行所有测试
    results = verifier.verify_all_tests()
    
    # 计算总耗时
    total_duration = sum(r.get('elapsed', 0) for r in results)
    
    # 打印摘要
    verifier.print_summary()
    
    # 自动生成报告
    print("生成测试报告...")
    try:
        report_data = verifier.get_report_data(total_duration)
        generator = ReportGenerator()
        report_path = generator.generate_markdown(report_data)
        print(f"✓ 报告已生成：{report_path}")
    except Exception as e:
        print(f"⚠ 报告生成失败：{e}")
    
    # 生成历史对比数据（新模块）
    if HAS_HISTORY_COMPARISON:
        print("\n生成历史对比数据...")
        try:
            comparator = HistoryComparator()
            comparator.load_history_reports(max_reports=10)
            
            # 转换结果格式以适配历史对比模块
            current_for_comparison = []
            for r in results:
                current_for_comparison.append({
                    'name': r['name'],
                    'bandwidth_mbps': r.get('bandwidth_mbps', 0),
                    'iops': r.get('iops', 0),
                    'avg_latency_us': r.get('avg_latency_us', 0),
                    'status': r['status']
                })
            
            comparison = comparator.compare_with_current(current_for_comparison)
            comparator.save_comparison()
            comparator.print_summary()
        except Exception as e:
            print(f"⚠ 历史对比生成失败：{e}")
    
    # 生成图表（新模块）
    if HAS_CHART_GENERATOR:
        print("\n生成图表...")
        try:
            chart_gen = ChartGenerator()
            
            # 加载历史对比数据
            history_comparison = None
            if HAS_HISTORY_COMPARISON and comparator.comparison_result:
                history_comparison = comparator.comparison_result
            
            # 生成所有图表
            charts = chart_gen.generate_all_charts(
                test_results=results,
                history_comparison=history_comparison,
                target_config={'target_bandwidth_mbps': 2100, 'target_iops': 15000}
            )
            chart_gen.print_generated_charts()
        except Exception as e:
            print(f"⚠ 图表生成失败：{e}")
    
    # 返回结果
    passed = sum(1 for r in results if r['status'] == 'PASS')
    return 0 if passed == len(results) else 1


if __name__ == '__main__':
    sys.exit(main())
