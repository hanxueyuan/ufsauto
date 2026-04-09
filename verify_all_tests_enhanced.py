#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
增强版测试验证脚本 - 支持完整失效分析

用途：
- 记录完整的测试上下文
- 保存 FIO 原始输出
- 捕获系统状态快照
- 生成结构化日志
- 支持调试模式

用法：
    python3 verify_all_tests_enhanced.py              # 标准模式
    python3 verify_all_tests_enhanced.py --verbose    # 调试模式
    python3 verify_all_tests_enhanced.py --save-fio   # 保存 FIO 原始输出
"""

import sys
import os
import json
import logging
import time
import subprocess
import traceback
import argparse
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional

# Add systest directory to Python path
systest_dir = Path(__file__).parent / 'systest'
sys.path.insert(0, str(systest_dir / 'core'))
sys.path.insert(0, str(systest_dir / 'tools'))

from logger import get_logger, close_all_loggers

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


def get_system_snapshot() -> Dict[str, Any]:
    """获取系统状态快照"""
    snapshot = {
        'timestamp': datetime.now().isoformat(),
        'cpu': {},
        'memory': {},
        'disk': {},
        'process': {}
    }
    
    try:
        # CPU 使用率
        result = subprocess.run(
            ['bash', '-c', 'top -bn1 | grep "Cpu(s)"'],
            capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0:
            parts = result.stdout.split(',')
            snapshot['cpu']['user'] = parts[0].split(':')[1].strip().split()[0]
            snapshot['cpu']['sys'] = parts[2].strip().split()[0] if len(parts) > 2 else 'N/A'
            snapshot['cpu']['idle'] = parts[3].strip().split()[0] if len(parts) > 3 else 'N/A'
    except Exception as e:
        snapshot['cpu']['error'] = str(e)
    
    try:
        # 内存使用
        result = subprocess.run(
            ['bash', '-c', 'free -m | grep Mem'],
            capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0:
            parts = result.stdout.split()
            snapshot['memory'] = {
                'total_mb': int(parts[1]),
                'used_mb': int(parts[2]),
                'free_mb': int(parts[3]),
                'usage_percent': round(int(parts[2]) / int(parts[1]) * 100, 1)
            }
    except Exception as e:
        snapshot['memory']['error'] = str(e)
    
    try:
        # 磁盘 IO 统计
        result = subprocess.run(
            ['bash', '-c', 'iostat -x 1 1 | tail -n +4 | head -1'],
            capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0:
            parts = result.stdout.split()
            if len(parts) >= 10:
                snapshot['disk'] = {
                    'device': parts[0],
                    'util_percent': parts[9],
                    'await_ms': parts[8]
                }
    except Exception as e:
        snapshot['disk']['error'] = str(e)
    
    return snapshot


class EnhancedTestVerifier:
    """增强版测试验证器 - 支持完整失效分析"""

    def __init__(self, device='/dev/vda', test_dir=Path('/tmp/ufs_test'),
                 verbose=False, save_fio_output=False):
        self.device = device
        self.test_dir = test_dir
        self.verbose = verbose
        self.save_fio_output = save_fio_output
        self.test_id = f"EnhancedVerify_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # 日志目录
        log_dir = Path(__file__).parent / 'logs' / 'enhanced'
        log_dir.mkdir(parents=True, exist_ok=True)
        
        # 创建结果目录（用于保存 FIO 原始输出）
        self.results_dir = Path(__file__).parent / 'results' / self.test_id
        self.results_dir.mkdir(parents=True, exist_ok=True)
        
        self.logger = get_logger(
            test_id=self.test_id,
            log_dir=str(log_dir),
            console_level=logging.DEBUG if verbose else logging.INFO,
            file_level=logging.DEBUG,
            enable_json=True  # 启用 JSON 格式
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
        
        # 失效分析数据
        self.failure_context = {}

    def log_test_start(self, test_name: str, config: Dict):
        """记录测试开始（包含完整上下文）"""
        self.logger.info(f"=" * 70)
        self.logger.info(f"测试开始：{test_name}")
        self.logger.info(f"=" * 70)
        self.logger.info(f"时间：{datetime.now().isoformat()}")
        self.logger.info(f"配置：{json.dumps(config, indent=2)}")
        
        # 测试前系统状态快照
        self.pre_snapshot = get_system_snapshot()
        self.logger.info(f"测试前系统状态：{json.dumps(self.pre_snapshot, indent=2)}")
        
        if self.verbose:
            self.logger.debug(f"DEBUG: 测试 ID={self.test_id}")
            self.logger.debug(f"DEBUG: 设备={self.device}")
            self.logger.debug(f"DEBUG: 测试目录={self.test_dir}")

    def log_test_complete(self, test_name: str, result: Dict, duration: float):
        """记录测试完成（包含系统状态对比）"""
        status = result.get('status', 'UNKNOWN')
        self.logger.info(f"-" * 70)
        self.logger.info(f"测试完成：{test_name}")
        self.logger.info(f"状态：{status}")
        self.logger.info(f"耗时：{duration:.2f}秒")
        
        if status == 'PASS':
            self.logger.info(f"带宽：{result.get('bandwidth_mbps', 0):.1f} MB/s")
            self.logger.info(f"IOPS: {result.get('iops', 0):.0f}")
            self.logger.info(f"延迟：{result.get('avg_latency_us', 0):.1f} μs")
        elif status == 'ERROR':
            self.logger.error(f"错误：{result.get('error', 'Unknown')}")
            if 'stack_trace' in result:
                self.logger.error(f"堆栈跟踪:\n{result['stack_trace']}")
        
        # 测试后系统状态快照
        post_snapshot = get_system_snapshot()
        self.logger.info(f"测试后系统状态：{json.dumps(post_snapshot, indent=2)}")
        
        # 对比系统状态变化
        if hasattr(self, 'pre_snapshot'):
            self._log_system_comparison(self.pre_snapshot, post_snapshot, test_name)
    
    def _log_system_comparison(self, pre: Dict, post: Dict, test_name: str):
        """记录系统状态对比"""
        self.logger.info(f"系统状态变化对比:")
        
        # CPU 对比
        if 'cpu' in pre and 'cpu' in post:
            pre_idle = pre['cpu'].get('idle', 'N/A')
            post_idle = post['cpu'].get('idle', 'N/A')
            if pre_idle != 'N/A' and post_idle != 'N/A':
                try:
                    change = float(post_idle) - float(pre_idle)
                    self.logger.info(f"  CPU Idle: {pre_idle}% → {post_idle}% (变化：{change:+.1f}%)")
                except:
                    pass
        
        # 内存对比
        if 'memory' in pre and 'memory' in post:
            pre_usage = pre['memory'].get('usage_percent', 'N/A')
            post_usage = post['memory'].get('usage_percent', 'N/A')
            if pre_usage != 'N/A' and post_usage != 'N/A':
                change = float(post_usage) - float(pre_usage)
                self.logger.info(f"  内存使用：{pre_usage}% → {post_usage}% (变化：{change:+.1f}%)")
        
        # 磁盘 IO 对比
        if 'disk' in pre and 'disk' in post:
            pre_util = pre['disk'].get('util_percent', 'N/A')
            post_util = post['disk'].get('util_percent', 'N/A')
            if pre_util != 'N/A' and post_util != 'N/A':
                self.logger.info(f"  磁盘利用率：{pre_util}% → {post_util}%")

    def run_test(self, test_name: str, test_type: str, rw_mode: str,
                 extra_args: Dict = None) -> Dict[str, Any]:
        """运行单个测试（增强版 - 完整失效分析）"""
        # 准备完整测试配置
        config = self.dev_config.copy()
        if extra_args:
            config.update(extra_args)
        
        # 记录完整测试配置（JSON 格式）
        test_config = {
            'test_name': test_name,
            'test_type': test_type,
            'rw_mode': rw_mode,
            'runtime': config.get('runtime'),
            'size': config.get('size'),
            'bs': config.get('bs'),
            'iodepth': config.get('iodepth'),
            'ioengine': config.get('ioengine'),
            'ramp_time': config.get('ramp_time'),
            'skip_prefill': config.get('skip_prefill'),
            'device': str(self.device),
            'test_dir': str(self.test_dir),
            'timestamp': datetime.now().isoformat()
        }
        
        self.logger.info(f"测试配置详情：{json.dumps(test_config, indent=2)}")
        self.log_test_start(test_name, config)
        
        test_file = self.test_dir / f"ufs_test_{test_name}"
        
        start_time = time.time()
        fio_cmd = None
        
        try:
            # 1. 创建测试文件（带详细日志）
            self.logger.info(f"[Step 1/3] 创建测试文件：{test_file}")
            try:
                test_file.parent.mkdir(parents=True, exist_ok=True)
                with open(test_file, 'wb') as f:
                    f.seek(64 * 1024 * 1024 - 1)
                    f.write(b'\0')
                self.logger.info(f"✓ 测试文件创建成功 (64MB)")
                
                if self.verbose:
                    self.logger.debug(f"文件路径：{test_file}")
                    self.logger.debug(f"文件大小：{test_file.stat().st_size} bytes")
                    
            except Exception as e:
                self.logger.error(f"✗ 创建测试文件失败：{e}")
                self.logger.error(f"堆栈跟踪：\n{traceback.format_exc()}")
                return {
                    'name': test_name,
                    'type': test_type,
                    'status': 'ERROR',
                    'error': f'创建测试文件失败：{e}',
                    'stack_trace': traceback.format_exc(),
                    'elapsed': time.time() - start_time
                }
            
            # 2. 构建 FIO 命令
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
            
            self.logger.info(f"[Step 2/3] 执行 FIO 测试")
            self.logger.info(f"FIO 命令：{' '.join(fio_cmd)}")
            
            if self.verbose:
                self.logger.debug(f"DEBUG: 完整命令={fio_cmd}")
            
            # 3. 执行 FIO
            result = subprocess.run(
                fio_cmd,
                capture_output=True,
                text=True,
                timeout=config['runtime'] + 30
            )
            
            # 保存 FIO 原始输出（始终保存）
            fio_output_data = {
                'stdout': result.stdout,
                'stderr': result.stderr,
                'returncode': result.returncode,
                'command': ' '.join(fio_cmd),
                'timestamp': datetime.now().isoformat()
            }
            self.fio_outputs[test_name] = fio_output_data
            fio_output_file = self.results_dir / f'fio_output_{test_name}.json'
            with open(fio_output_file, 'w', encoding='utf-8') as f:
                json.dump(fio_output_data, f, indent=2, ensure_ascii=False)
            self.logger.info(f"✓ FIO 原始输出已保存：{fio_output_file}")
            
            # 4. 检查执行结果
            combined_output = result.stdout + result.stderr
            
            if result.returncode != 0 and not combined_output.strip().startswith('{'):
                error_msg = f"FIO 执行失败 (exit code={result.returncode})"
                self.logger.error(f"✗ {error_msg}")
                self.logger.error(f"标准输出：{result.stdout[:500] if result.stdout else 'empty'}")
                self.logger.error(f"标准错误：{result.stderr[:500] if result.stderr else 'empty'}")
                
                return {
                    'name': test_name,
                    'type': test_type,
                    'status': 'ERROR',
                    'error': error_msg,
                    'fio_stdout': result.stdout[:1000],
                    'fio_stderr': result.stderr[:1000],
                    'fio_exit_code': result.returncode,
                    'elapsed': time.time() - start_time
                }
            
            # 5. 解析 JSON 输出（带详细错误处理）
            self.logger.info(f"[Step 3/3] 解析 FIO 输出")
            
            try:
                json_start = combined_output.find('{')
                json_end = combined_output.rfind('}') + 1
                if json_start >= 0 and json_end > json_start:
                    json_str = combined_output[json_start:json_end]
                    fio_output = json.loads(json_str)
                else:
                    fio_output = json.loads(combined_output)
                
                self.logger.info(f"✓ FIO JSON 解析成功")
                
                if self.verbose:
                    self.logger.debug(f"DEBUG: JSON 长度={len(json_str)}")
                    self.logger.debug(f"DEBUG: 完整 JSON={json_str[:500]}...")
                    
            except json.JSONDecodeError as e:
                error_msg = f"JSON 解析失败：{e}"
                self.logger.error(f"✗ {error_msg}")
                self.logger.error(f"原始输出 (前 1000 字符):\n{combined_output[:1000]}")
                self.logger.error(f"堆栈跟踪:\n{traceback.format_exc()}")
                
                return {
                    'name': test_name,
                    'type': test_type,
                    'status': 'ERROR',
                    'error': error_msg,
                    'raw_output': combined_output[:2000],
                    'stack_trace': traceback.format_exc(),
                    'elapsed': time.time() - start_time
                }
            
            # 6. 提取性能指标
            job = fio_output.get('jobs', [{}])[0]
            io_type = 'read' if 'read' in rw_mode.lower() else 'write'
            if rw_mode in ['randrw', 'rw']:
                io_stats = job.get('read', {})
            else:
                io_stats = job.get(io_type, {})
            
            bw_bytes = io_stats.get('bw_bytes', 0)
            bw_mbps = bw_bytes / (1024 * 1024)
            iops = io_stats.get('iops', 0)
            lat_ns = io_stats.get('lat_ns', {})
            avg_lat_us = lat_ns.get('mean', 0) / 1000
            
            elapsed = time.time() - start_time
            
            # 7. 清理测试文件（带日志）
            try:
                test_file.unlink()
                self.logger.info(f"✓ 测试文件已清理")
            except Exception as e:
                self.logger.warning(f"⚠ 清理测试文件失败：{e}")
            
            # 8. 记录测试结果
            self.logger.info(f"测试结果:")
            self.logger.info(f"  带宽：{bw_mbps:.1f} MB/s")
            self.logger.info(f"  IOPS: {iops:.0f}")
            self.logger.info(f"  平均延迟：{avg_lat_us:.1f} μs")
            self.logger.info(f"  实际耗时：{elapsed:.1f}s")
            
            return {
                'name': test_name,
                'type': test_type,
                'status': 'PASS',
                'bandwidth_mbps': bw_mbps,
                'iops': iops,
                'avg_latency_us': avg_lat_us,
                'elapsed': elapsed,
                'fio_json': fio_output,  # 保存完整 JSON
                'test_config': test_config  # 保存测试配置
            }
            
        except subprocess.TimeoutExpired:
            elapsed = time.time() - start_time
            error_msg = f"FIO 执行超时 (>{config['runtime'] + 30}s)"
            self.logger.error(f"✗ {error_msg}")
            self.logger.error(f"命令：{' '.join(fio_cmd) if fio_cmd else 'N/A'}")
            self.logger.error(f"堆栈跟踪:\n{traceback.format_exc()}")
            
            return {
                'name': test_name,
                'type': test_type,
                'status': 'TIMEOUT',
                'error': error_msg,
                'command': ' '.join(fio_cmd) if fio_cmd else 'N/A',
                'timeout_limit': config['runtime'] + 30,
                'stack_trace': traceback.format_exc(),
                'elapsed': elapsed
            }
            
        except Exception as e:
            elapsed = time.time() - start_time
            error_msg = f"测试异常：{type(e).__name__}: {e}"
            self.logger.error(f"✗ {error_msg}")
            self.logger.error(f"命令：{' '.join(fio_cmd) if fio_cmd else 'N/A'}")
            self.logger.error(f"堆栈跟踪:\n{traceback.format_exc()}")
            
            return {
                'name': test_name,
                'type': test_type,
                'status': 'ERROR',
                'error': error_msg,
                'exception_type': type(e).__name__,
                'command': ' '.join(fio_cmd) if fio_cmd else 'N/A',
                'stack_trace': traceback.format_exc(),
                'elapsed': elapsed
            }

    def verify_all_tests(self) -> List[Dict]:
        """验证所有测试用例"""
        test_cases = [
            ('seq_read_burst', 'performance', 'read', None),
            ('seq_write_burst', 'performance', 'write', None),
            ('rand_read_burst', 'performance', 'randread', {'bs': '4k', 'iodepth': 32}),
            ('rand_write_burst', 'performance', 'randwrite', {'bs': '4k', 'iodepth': 32}),
            ('mixed_rw', 'performance', 'randrw', {'bs': '4k', 'iodepth': 32, 'rwmixread': 70}),
            ('qos_latency', 'qos', 'randread', {'bs': '4k', 'iodepth': 1}),
        ]
        
        self.logger.info(f"开始验证 {len(test_cases)} 个测试用例...")
        self.logger.info(f"开发模式配置：runtime={self.dev_config['runtime']}s, size={self.dev_config['size']}")
        self.logger.info(f"调试模式：{self.verbose}")
        self.logger.info(f"保存 FIO 输出：{self.save_fio_output}")
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
        
        self.logger.info("=" * 70)
        self.logger.info(f"验证完成")
        self.logger.info(f"  总计：{len(self.results)} 个测试用例")
        self.logger.info(f"  通过：{passed}")
        self.logger.info(f"  失败：{failed}")
        self.logger.info(f"  总耗时：{total_elapsed:.1f}秒")
        self.logger.info("=" * 70)
        
        return self.results

    def print_summary(self):
        """打印结果摘要"""
        print()
        print("=" * 70)
        print("  UFS Auto 增强版验证 - 测试结果摘要")
        print("=" * 70)
        print()
        
        passed = sum(1 for r in self.results if r['status'] == 'PASS')
        total = len(self.results)
        
        if passed == total:
            print("✅ 所有测试用例验证通过！")
        else:
            print(f"❌ {total - passed} 个测试用例失败")
            print()
            print("失败详情:")
            for r in self.results:
                if r['status'] != 'PASS':
                    print(f"  - {r['name']}: {r.get('error', 'Unknown')}")
        
        print()
        print(f"日志位置：logs/enhanced/{self.test_id}.log")
        if self.save_fio_output:
            print(f"FIO 输出：/tmp/fio_output_*.json")
        print()


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='增强版测试验证脚本')
    parser.add_argument('--verbose', '-v', action='store_true', help='启用调试模式')
    parser.add_argument('--save-fio', action='store_true', help='保存 FIO 原始输出')
    parser.add_argument('--device', default='/dev/vda', help='测试设备路径')
    parser.add_argument('--test-dir', default='/tmp/ufs_test', help='测试目录')
    args = parser.parse_args()
    
    print()
    print("=" * 70)
    print("  UFS Auto 增强版测试验证")
    print("=" * 70)
    print()
    print(f"调试模式：{args.verbose}")
    print(f"保存 FIO 输出：{args.save_fio}")
    print(f"测试设备：{args.device}")
    print(f"测试目录：{args.test_dir}")
    print()
    
    # 创建测试目录
    test_dir = Path(args.test_dir)
    test_dir.mkdir(parents=True, exist_ok=True)
    
    # 创建验证器
    verifier = EnhancedTestVerifier(
        device=args.device,
        test_dir=test_dir,
        verbose=args.verbose,
        save_fio_output=args.save_fio
    )
    
    # 运行测试
    results = verifier.verify_all_tests()
    
    # 打印摘要
    verifier.print_summary()
    
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
    
    # 清理
    close_all_loggers()
    
    # 返回结果
    passed = sum(1 for r in results if r['status'] == 'PASS')
    return 0 if passed == len(results) else 1


if __name__ == '__main__':
    sys.exit(main())
