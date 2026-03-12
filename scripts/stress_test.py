#!/usr/bin/env python3
"""
UFS压力测试脚本
用于验证UFS设备在高负载下的稳定性和可靠性
"""

import os
import sys
import time
import random
import logging
import argparse
from datetime import datetime
from typing import List, Dict, Any
from dataclasses import dataclass

# 添加src目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from ufs_device import UfsDevice

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('stress_test.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

@dataclass
class TestResult:
    """测试结果"""
    test_name: str
    start_time: str
    end_time: str
    duration: float
    operations: int
    errors: int
    avg_latency: float
    min_latency: float
    max_latency: float
    success: bool

class UfsStressTester:
    """UFS压力测试器"""
    
    def __init__(self, device_path: str, test_lba: int, test_size_gb: int = 10):
        self.device_path = device_path
        self.test_lba = test_lba
        self.test_size_gb = test_size_gb
        self.total_blocks = (test_size_gb * 1024 * 1024 * 1024) // 512
        self.running = False
        self.results: List[TestResult] = []
        
        # 统计信息
        self.write_count = 0
        self.read_count = 0
        self.error_count = 0
        self.total_bytes_written = 0
        self.total_bytes_read = 0
        self.start_time = 0
        
        logger.info(f"初始化压力测试器")
        logger.info(f"设备: {device_path}")
        logger.info(f"测试起始LBA: {test_lba}")
        logger.info(f"测试区域大小: {test_size_gb} GB ({self.total_blocks} 块)")
        
    def random_io_test(self, duration_sec: int, block_size: int = 4096, 
                     read_ratio: float = 0.7, write_ratio: float = 0.3) -> TestResult:
        """
        随机IO混合测试
        :param duration_sec: 测试时长（秒）
        :param block_size: 块大小（字节）
        :param read_ratio: 读取比例
        :param write_ratio: 写入比例
        """
        test_name = f"随机IO测试_{block_size}B_{int(read_ratio*100)}读"
        logger.info(f"开始{test_name}，时长: {duration_sec}秒")
        
        blocks_per_io = block_size // 512
        operations = 0
        errors = 0
        latencies = []
        start_time = time.time()
        
        with UfsDevice(self.device_path) as dev:
            if not dev.is_open:
                logger.error("无法打开设备")
                return TestResult(
                    test_name=test_name,
                    start_time=datetime.fromtimestamp(start_time).isoformat(),
                    end_time=datetime.fromtimestamp(time.time()).isoformat(),
                    duration=0,
                    operations=0,
                    errors=1,
                    avg_latency=0,
                    min_latency=0,
                    max_latency=0,
                    success=False
                )
                
            while time.time() - start_time < duration_sec:
                # 随机选择LBA
                lba = self.test_lba + random.randint(0, self.total_blocks - blocks_per_io)
                
                # 随机选择操作类型
                if random.random() < read_ratio:
                    # 读取操作
                    op_start = time.time()
                    ok, data = dev.read_lba(lba, blocks_per_io)
                    op_duration = time.time() - op_start
                    
                    if ok:
                        self.read_count += 1
                        self.total_bytes_read += len(data)
                        latencies.append(op_duration)
                        operations += 1
                    else:
                        errors += 1
                        self.error_count += 1
                        logger.warning(f"读取错误，LBA: {lba}")
                else:
                    # 写入操作
                    data = os.urandom(block_size)
                    op_start = time.time()
                    ok, _ = dev.write_lba(lba, data)
                    op_duration = time.time() - op_start
                    
                    if ok:
                        self.write_count += 1
                        self.total_bytes_written += len(data)
                        latencies.append(op_duration)
                        operations += 1
                    else:
                        errors += 1
                        self.error_count += 1
                        logger.warning(f"写入错误，LBA: {lba}")
                        
                # 定期打印状态
                if operations % 1000 == 0 and operations > 0:
                    elapsed = time.time() - start_time
                    avg_lat = sum(latencies[-1000:]) / 1000 * 1000
                    iops = operations / elapsed
                    logger.info(f"已运行 {int(elapsed)}s, 操作数: {operations}, 错误: {errors}, "
                               f"IOPS: {iops:.0f}, 平均延迟: {avg_lat:.2f}ms")
                                
        end_time = time.time()
        duration = end_time - start_time
        
        # 计算统计信息
        if latencies:
            avg_latency = sum(latencies) / len(latencies) * 1000
            min_latency = min(latencies) * 1000
            max_latency = max(latencies) * 1000
        else:
            avg_latency = 0
            min_latency = 0
            max_latency = 0
            
        success = errors == 0
        
        result = TestResult(
            test_name=test_name,
            start_time=datetime.fromtimestamp(start_time).isoformat(),
            end_time=datetime.fromtimestamp(end_time).isoformat(),
            duration=duration,
            operations=operations,
            errors=errors,
            avg_latency=avg_latency,
            min_latency=min_latency,
            max_latency=max_latency,
            success=success
        )
        
        self.results.append(result)
        
        logger.info(f"{test_name} 完成")
        logger.info(f"总操作数: {operations}, 错误数: {errors}")
        logger.info(f"平均延迟: {avg_latency:.2f}ms, 最小: {min_latency:.2f}ms, 最大: {max_latency:.2f}ms")
        logger.info(f"成功率: {(operations - errors)/operations*100:.2f}%" if operations > 0 else "无操作")
        
        return result
        
    def sequential_write_test(self, block_size: int = 1024 * 1024) -> TestResult:
        """顺序写入测试，写入整个测试区域"""
        test_name = f"顺序写入测试_{block_size}B"
        logger.info(f"开始{test_name}")
        
        blocks_per_io = block_size // 512
        operations = 0
        errors = 0
        latencies = []
        start_time = time.time()
        
        with UfsDevice(self.device_path) as dev:
            if not dev.is_open:
                logger.error("无法打开设备")
                return TestResult(
                    test_name=test_name,
                    start_time=datetime.fromtimestamp(start_time).isoformat(),
                    end_time=datetime.fromtimestamp(time.time()).isoformat(),
                    duration=0,
                    operations=0,
                    errors=1,
                    avg_latency=0,
                    min_latency=0,
                    max_latency=0,
                    success=False
                )
                
            for offset in range(0, self.total_blocks, blocks_per_io):
                lba = self.test_lba + offset
                data = os.urandom(block_size)
                
                op_start = time.time()
                ok, _ = dev.write_lba(lba, data)
                op_duration = time.time() - op_start
                
                if ok:
                    self.write_count += 1
                    self.total_bytes_written += len(data)
                    latencies.append(op_duration)
                    operations += 1
                else:
                    errors += 1
                    self.error_count += 1
                    logger.warning(f"写入错误，LBA: {lba}")
                    
                if operations % 100 == 0:
                    progress = offset / self.total_blocks * 100
                    elapsed = time.time() - start_time
                    speed = (operations * block_size) / elapsed / (1024 * 1024)
                    logger.info(f"进度: {progress:.1f}%, 速度: {speed:.2f} MB/s, 错误: {errors}")
                    
        end_time = time.time()
        duration = end_time - start_time
        
        if latencies:
            avg_latency = sum(latencies) / len(latencies) * 1000
            min_latency = min(latencies) * 1000
            max_latency = max(latencies) * 1000
        else:
            avg_latency = 0
            min_latency = 0
            max_latency = 0
            
        success = errors == 0
        write_speed = (operations * block_size) / duration / (1024 * 1024) if duration > 0 else 0
        
        result = TestResult(
            test_name=test_name,
            start_time=datetime.fromtimestamp(start_time).isoformat(),
            end_time=datetime.fromtimestamp(end_time).isoformat(),
            duration=duration,
            operations=operations,
            errors=errors,
            avg_latency=avg_latency,
            min_latency=min_latency,
            max_latency=max_latency,
            success=success
        )
        
        self.results.append(result)
        
        logger.info(f"{test_name} 完成")
        logger.info(f"写入大小: {operations * block_size / (1024*1024*1024):.2f} GB")
        logger.info(f"平均写入速度: {write_speed:.2f} MB/s")
        logger.info(f"平均延迟: {avg_latency:.2f}ms")
        logger.info(f"错误数: {errors}")
        
        return result
        
    def power_cycle_test(self, cycles: int = 100) -> TestResult:
        """
        电源循环测试
        :param cycles: 循环次数
        """
        test_name = "电源循环测试"
        logger.info(f"开始{test_name}，循环次数: {cycles}")
        
        errors = 0
        operations = 0
        start_time = time.time()
        
        for i in range(cycles):
            logger.info(f"第 {i+1}/{cycles} 次循环")
            
            try:
                with UfsDevice(self.device_path) as dev:
                    if not dev.is_open:
                        errors += 1
                        logger.error("无法打开设备")
                        continue
                        
                    # 写入测试数据
                    test_data = b"POWER_CYCLE_TEST" * 32  # 512字节
                    ok, _ = dev.write_lba(self.test_lba, test_data)
                    if not ok:
                        errors += 1
                        logger.warning("写入测试数据失败")
                        continue
                        
                    # 刷新缓存
                    dev.flush_cache()
                    
                    # 切换到低功耗模式
                    dev.set_power_mode(dev.PowerMode.SLEEP)
                    time.sleep(0.1)
                    
                    # 唤醒
                    dev.set_power_mode(dev.PowerMode.ACTIVE)
                    time.sleep(0.1)
                    
                    # 验证数据
                    ok, read_data = dev.read_lba(self.test_lba, 1)
                    if not ok or read_data != test_data:
                        errors += 1
                        logger.warning("数据验证失败")
                        continue
                        
                    operations += 1
                    
            except Exception as e:
                errors += 1
                logger.error(f"循环异常: {str(e)}")
                
            # 冷却
            time.sleep(0.5)
            
        end_time = time.time()
        duration = end_time - start_time
        
        success = errors == 0
        
        result = TestResult(
            test_name=test_name,
            start_time=datetime.fromtimestamp(start_time).isoformat(),
            end_time=datetime.fromtimestamp(end_time).isoformat(),
            duration=duration,
            operations=operations,
            errors=errors,
            avg_latency=0,
            min_latency=0,
            max_latency=0,
            success=success
        )
        
        self.results.append(result)
        
        logger.info(f"{test_name} 完成")
        logger.info(f"成功循环: {operations}/{cycles}")
        logger.info(f"错误数: {errors}")
        logger.info(f"成功率: {operations/cycles*100:.2f}%")
        
        return result
        
    def temperature_cycle_test(self, duration_hours: int = 24) -> TestResult:
        """
        温度循环测试（需要温控 chamber 支持）
        :param duration_hours: 测试时长（小时）
        """
        test_name = "温度循环测试"
        logger.info(f"开始{test_name}，时长: {duration_hours}小时")
        
        operations = 0
        errors = 0
        start_time = time.time()
        end_time = start_time + duration_hours * 3600
        
        while time.time() < end_time:
            try:
                with UfsDevice(self.device_path) as dev:
                    if not dev.is_open:
                        errors += 1
                        time.sleep(60)
                        continue
                        
                    # 获取温度
                    health = dev.get_health_report()
                    temp = health['temperature_celsius']
                    
                    # 执行IO操作
                    for _ in range(100):
                        lba = self.test_lba + random.randint(0, self.total_blocks - 8)
                        data = os.urandom(4096)
                        ok, _ = dev.write_lba(lba, data)
                        if ok:
                            ok, read_data = dev.read_lba(lba, 8)
                            if ok and read_data == data:
                                operations += 1
                            else:
                                errors += 1
                        else:
                            errors += 1
                            
                    elapsed = time.time() - start_time
                    logger.info(f"已运行 {elapsed/3600:.1f}小时, 当前温度: {temp}°C, "
                               f"操作数: {operations}, 错误: {errors}")
                               
            except Exception as e:
                logger.error(f"测试异常: {str(e)}")
                errors += 1
                
            time.sleep(60)  # 每分钟执行一轮
            
        test_end_time = time.time()
        duration = test_end_time - start_time
        
        success = errors == 0
        
        result = TestResult(
            test_name=test_name,
            start_time=datetime.fromtimestamp(start_time).isoformat(),
            end_time=datetime.fromtimestamp(test_end_time).isoformat(),
            duration=duration,
            operations=operations,
            errors=errors,
            avg_latency=0,
            min_latency=0,
            max_latency=0,
            success=success
        )
        
        self.results.append(result)
        
        logger.info(f"{test_name} 完成")
        logger.info(f"总操作数: {operations}")
        logger.info(f"错误数: {errors}")
        
        return result
        
    def generate_report(self, output_file: str = "stress_test_report.json"):
        """生成测试报告"""
        import json
        
        report = {
            "test_info": {
                "device": self.device_path,
                "test_start_time": datetime.fromtimestamp(self.start_time).isoformat(),
                "test_end_time": datetime.now().isoformat(),
                "total_duration": time.time() - self.start_time,
                "test_lba": self.test_lba,
                "test_size_gb": self.test_size_gb
            },
            "statistics": {
                "total_write_operations": self.write_count,
                "total_read_operations": self.read_count,
                "total_errors": self.error_count,
                "total_bytes_written": self.total_bytes_written,
                "total_bytes_read": self.total_bytes_read,
                "total_data_processed": self.total_bytes_written + self.total_bytes_read
            },
            "test_results": [
                {
                    "test_name": r.test_name,
                    "start_time": r.start_time,
                    "end_time": r.end_time,
                    "duration_seconds": r.duration,
                    "operations": r.operations,
                    "errors": r.errors,
                    "avg_latency_ms": r.avg_latency,
                    "min_latency_ms": r.min_latency,
                    "max_latency_ms": r.max_latency,
                    "success": r.success
                } for r in self.results
            ],
            "overall_result": "PASS" if all(r.success for r in self.results) else "FAIL"
        }
        
        with open(output_file, 'w') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
            
        logger.info(f"测试报告已保存到: {output_file}")
        
        # 打印汇总
        print("\n" + "="*80)
        print("压力测试汇总报告")
        print("="*80)
        print(f"设备: {self.device_path}")
        print(f"总运行时间: {(time.time() - self.start_time)/3600:.2f} 小时")
        print(f"总写入量: {self.total_bytes_written / (1024**4):.2f} TB")
        print(f"总读取量: {self.total_bytes_read / (1024**4):.2f} TB")
        print(f"总操作数: {self.write_count + self.read_count}")
        print(f"总错误数: {self.error_count}")
        print(f"整体结果: {'✅ 通过' if report['overall_result'] == 'PASS' else '❌ 失败'}")
        print("\n各测试项结果:")
        for r in self.results:
            status = "✅ PASS" if r.success else "❌ FAIL"
            print(f"  {r.test_name:<30} {status} - {r.operations} 操作, {r.errors} 错误")
        print("="*80)

def main():
    parser = argparse.ArgumentParser(description='UFS压力测试工具')
    parser.add_argument('-d', '--device', default='/dev/ufs0', help='UFS设备路径')
    parser.add_argument('--lba', type=int, default=1024*1024*1024//512, help='测试起始LBA (默认: 1GB位置)')
    parser.add_argument('--size', type=int, default=10, help='测试区域大小(GB) (默认: 10GB)')
    
    subparsers = parser.add_subparsers(dest='test_type', help='测试类型')
    
    # 随机IO测试
    parser_random = subparsers.add_parser('random', help='随机IO混合测试')
    parser_random.add_argument('--duration', type=int, default=3600, help='测试时长(秒) (默认: 3600)')
    parser_random.add_argument('--block-size', type=int, default=4096, help='块大小(字节) (默认: 4096)')
    parser_random.add_argument('--read-ratio', type=float, default=0.7, help='读取比例 (默认: 0.7)')
    
    # 顺序写入测试
    parser_seq = subparsers.add_parser('sequential', help='顺序写入测试')
    parser_seq.add_argument('--block-size', type=int, default=1024*1024, help='块大小(字节) (默认: 1MB)')
    
    # 电源循环测试
    parser_power = subparsers.add_parser('power', help='电源循环测试')
    parser_power.add_argument('--cycles', type=int, default=100, help='循环次数 (默认: 100)')
    
    # 温度循环测试
    parser_temp = subparsers.add_parser('temperature', help='温度循环测试')
    parser_temp.add_argument('--duration', type=int, default=24, help='测试时长(小时) (默认: 24)')
    
    # 完整压力测试
    parser_full = subparsers.add_parser('full', help='完整压力测试套件')
    
    args = parser.parse_args()
    
    if not args.test_type:
        parser.print_help()
        return 1
        
    tester = UfsStressTester(args.device, args.lba, args.size)
    tester.start_time = time.time()
    
    try:
        if args.test_type == 'random':
            tester.random_io_test(args.duration, args.block_size, args.read_ratio)
        elif args.test_type == 'sequential':
            tester.sequential_write_test(args.block_size)
        elif args.test_type == 'power':
            tester.power_cycle_test(args.cycles)
        elif args.test_type == 'temperature':
            tester.temperature_cycle_test(args.duration)
        elif args.test_type == 'full':
            logger.info("执行完整压力测试套件...")
            tester.sequential_write_test()
            tester.random_io_test(3600, 4096, 0.7)  # 1小时7:3混合
            tester.random_io_test(1800, 4096, 0.5)  # 30分钟5:5混合
            tester.random_io_test(1800, 16384, 0.8) # 30分钟16K 8:2混合
            tester.power_cycle_test(100)
            logger.info("完整测试套件执行完成")
            
    except KeyboardInterrupt:
        logger.info("测试被用户中断")
    except Exception as e:
        logger.error(f"测试异常: {str(e)}", exc_info=True)
        return 1
    finally:
        tester.generate_report()
        
    return 0 if all(r.success for r in tester.results) else 1

if __name__ == '__main__':
    sys.exit(main())
