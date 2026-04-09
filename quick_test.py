#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
开发模式快速测试脚本

用途：用最少的时间和循环次数验证框架能跑通
- 测试时间：每个用例 5 秒
- 测试大小：64MB
- 跳过预填充
- 只运行 1 个测试用例验证框架

用法：
    python3 quick_test.py
"""

import sys
import os
import json
import logging
from pathlib import Path
from datetime import datetime

# Add systest directory to Python path (where core/ tools/ suites/ live)
systest_dir = Path(__file__).parent / 'systest'
sys.path.insert(0, str(systest_dir / 'core'))
sys.path.insert(0, str(systest_dir / 'tools'))

# Import after path setup
from runner import TestCase
from logger import get_logger


class QuickTest(TestCase):
    """快速验证测试 - 5 秒顺序读"""

    name = "quick_test_seq_read"
    description = "开发模式快速验证测试"

    def __init__(self, device='/dev/sda', test_dir=None, verbose=True, logger=None):
        super().__init__(device, test_dir, verbose, logger)
        self.test_file = self.get_test_file_path('quick_test')
        # 开发模式配置：最少时间和循环
        self.bs = '128k'
        self.size = '64M'  # 小文件
        self.runtime = 5   # 5 秒测试
        self.ramp_time = 0  # 无预热
        self.ioengine = 'sync'
        self.iodepth = 1

    def setup(self) -> bool:
        """简化前置检查 - 开发模式跳过设备检查"""
        self.logger.info("=== 快速测试 - 前置检查 ===")

        # 1. 检查设备（开发模式可选）
        if os.path.exists(self.device):
            self.logger.info(f"✓ 设备存在：{self.device}")
        else:
            self.logger.warning(f"⚠ 设备不存在：{self.device}（开发模式继续）")

        # 2. 检查空间
        try:
            import subprocess
            result = subprocess.run(['df', '-B1', os.path.dirname(self.test_file)],
                                    capture_output=True, text=True)
            if result.returncode == 0:
                lines = result.stdout.strip().split('\n')
                if len(lines) >= 2:
                    parts = lines[1].split()
                    avail = int(parts[3]) / (1024**3)  # GB
                    if avail < 1.0:
                        self.logger.error(f"可用空间不足：{avail:.1f}GB < 1GB")
                        return False
                    self.logger.info(f"✓ 可用空间：{avail:.1f}GB")
        except Exception as e:
            self.logger.warning(f"空间检查跳过：{e}")

        # 3. 检查 FIO
        try:
            result = subprocess.run(['fio', '--version'], capture_output=True, text=True)
            if result.returncode == 0:
                self.logger.info(f"✓ FIO 已安装：{result.stdout.strip()}")
        except Exception as e:
            self.logger.error(f"FIO 未安装：{e}")
            return False

        # 4. 创建测试文件（小文件，快速创建）
        self.logger.info(f"创建测试文件：{self.test_file} ({self.size})")
        try:
            self.test_file.parent.mkdir(parents=True, exist_ok=True)
            # 快速创建文件（不预填充随机数据）
            with open(self.test_file, 'wb') as f:
                f.seek(64 * 1024 * 1024 - 1)  # 64MB
                f.write(b'\0')
            self.logger.info(f"✓ 测试文件创建完成")
        except Exception as e:
            self.logger.error(f"创建测试文件失败：{e}")
            return False

        self.logger.info("✓ 前置检查通过")
        return True

    def execute(self) -> dict:
        """执行快速 FIO 测试"""
        self.logger.info("=== 执行 FIO 测试 ===")
        self.logger.info(f"配置：bs={self.bs}, size={self.size}, runtime={self.runtime}s")

        try:
            import subprocess
            fio_cmd = [
                'fio',
                '--name=quick_test',
                f'--filename={self.test_file}',
                '--rw=read',
                f'--bs={self.bs}',
                f'--size={self.size}',
                f'--runtime={self.runtime}',
                f'--ioengine={self.ioengine}',
                f'--iodepth={self.iodepth}',
                '--direct=1',
                '--time_based',
                '--output-format=json'
            ]

            self.logger.info(f"执行命令：{' '.join(fio_cmd)}")
            result = subprocess.run(fio_cmd, capture_output=True, text=True, timeout=60)

            if result.returncode != 0:
                self.logger.error(f"FIO 执行失败：{result.stderr}")
                return {'error': result.stderr}

            # 解析 JSON 输出
            fio_output = json.loads(result.stdout)
            job = fio_output.get('jobs', [{}])[0]
            read_stats = job.get('read', {})

            # 提取指标
            bw_bytes = read_stats.get('bw_bytes', 0)
            bw_mbps = bw_bytes / (1024 * 1024)
            iops = read_stats.get('iops', 0)
            lat_ns = read_stats.get('lat_ns', {})
            avg_lat_us = lat_ns.get('mean', 0) / 1000

            metrics = {
                'bandwidth_mbps': bw_mbps,
                'iops': iops,
                'avg_latency_us': avg_lat_us,
                'runtime_s': job.get('elapsed', 0)
            }

            self.logger.info(f"✓ 测试完成")
            self.logger.info(f"  带宽：{bw_mbps:.1f} MB/s")
            self.logger.info(f"  IOPS: {iops:.0f}")
            self.logger.info(f"  平均延迟：{avg_lat_us:.1f} μs")
            self.logger.info(f"  实际运行：{job.get('elapsed', 0):.1f}s")

            return metrics

        except subprocess.TimeoutExpired:
            self.logger.error("FIO 执行超时")
            return {'error': 'timeout'}
        except Exception as e:
            self.logger.error(f"FIO 执行异常：{e}")
            return {'error': str(e)}

    def validate(self, result: dict) -> bool:
        """验证结果"""
        self.logger.info("=== 验证结果 ===")

        if 'error' in result:
            self.logger.error(f"验证失败：{result['error']}")
            return False

        # 简单验证：只要有数据就算通过
        bw = result.get('bandwidth_mbps', 0)
        if bw > 0:
            self.logger.info(f"✓ 验证通过：带宽 {bw:.1f} MB/s")
            return True
        else:
            self.logger.error("验证失败：带宽为 0")
            return False

    def teardown(self) -> bool:
        """清理测试文件"""
        self.logger.info("=== 清理 ===")
        try:
            if self.test_file.exists():
                self.test_file.unlink()
                self.logger.info(f"✓ 测试文件已删除")
        except Exception as e:
            self.logger.warning(f"清理失败：{e}")
        return True


def main():
    """主函数"""
    print("=" * 60)
    print("  UFS Auto 开发模式快速测试")
    print("=" * 60)
    print()

    # 初始化日志
    test_id = f"QuickTest_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    logger = get_logger(
        test_id=test_id,
        log_dir='logs',
        console_level=logging.INFO,
        file_level=logging.DEBUG
    )

    # 加载配置
    config_path = Path(__file__).parent / 'config' / 'runtime.json'
    device = '/dev/vda'  # 当前环境使用 vda
    test_dir = Path('/tmp/ufs_test')

    if config_path.exists():
        with open(config_path, 'r') as f:
            config = json.load(f)
            device = config.get('device', '/dev/vda')
            test_dir = Path(config.get('test_dir', '/tmp/ufs_test'))
            mode_config = config.get('test_mode', {})
            print(f"测试模式：{mode_config.get('mode', 'unknown')}")
            print(f"快速测试：{mode_config.get('quick_test', False)}")
            print(f"设备：{device}")
            print(f"测试目录：{test_dir}")
            print()

    # 创建测试目录
    test_dir.mkdir(parents=True, exist_ok=True)

    # 执行测试
    print("开始测试...")
    print()

    test = QuickTest(device=device, test_dir=test_dir, verbose=True, logger=logger)

    try:
        # Setup
        if not test.setup():
            print("\n❌ 前置检查失败")
            return 1

        # Execute
        result = test.execute()

        # Validate
        if not test.validate(result):
            print("\n❌ 验证失败")
            return 1

        # Teardown
        test.teardown()

        print()
        print("=" * 60)
        print("  ✅ 快速测试完成！")
        print("=" * 60)
        print()
        print("测试结果:")
        if 'error' not in result:
            print(f"  带宽：{result.get('bandwidth_mbps', 0):.1f} MB/s")
            print(f"  IOPS: {result.get('iops', 0):.0f}")
            print(f"  延迟：{result.get('avg_latency_us', 0):.1f} μs")
        print()
        print("框架验证通过！可以开始正式测试了")
        print()
        return 0

    except Exception as e:
        logger.error(f"测试异常：{e}")
        print(f"\n❌ 测试异常：{e}")
        return 1


if __name__ == '__main__':
    sys.exit(main())
