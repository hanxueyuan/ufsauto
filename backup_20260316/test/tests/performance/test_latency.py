"""
UFS 3.1 性能测试 - 延迟测试
包含读写延迟、响应时间等测试用例
"""
import pytest
import time
import numpy as np
from src.test_base import UFSTestBase

pytestmark = [pytest.mark.performance, pytest.mark.ufs31]

class TestUFSLatency(UFSTestBase):
    """UFS延迟测试类"""
    
    def setup_method(self, method):
        """测试方法初始化"""
        super().setup_method(method)
        self.block_size = self.get_block_size()
        # 延迟测试前先预热设备
        self._warmup_device()
        
    def _warmup_device(self):
        """设备预热，确保设备处于活跃状态"""
        lba = self.get_random_lba()
        test_data = self.generate_test_data(self.block_size, pattern="random")
        for _ in range(10):
            self.ufs.write(lba, test_data)
            self.ufs.read(lba, count=1)
            
    def test_read_latency(self):
        """测试读延迟"""
        iterations = 1000
        latencies = []
        
        # 预写入测试数据
        lba = self.get_random_lba()
        test_data = self.generate_test_data(self.block_size, pattern="random")
        self.ufs.write(lba, test_data)
        
        # 执行读延迟测试
        for _ in range(iterations):
            start = time.perf_counter_ns()
            self.ufs.read(lba, count=1)
            end = time.perf_counter_ns()
            latency_us = (end - start) / 1000  # 转换为微秒
            latencies.append(latency_us)
            
        # 计算统计值
        avg_latency = np.mean(latencies)
        min_latency = np.min(latencies)
        max_latency = np.max(latencies)
        p95_latency = np.percentile(latencies, 95)
        p99_latency = np.percentile(latencies, 99)
        p999_latency = np.percentile(latencies, 99.9)
        
        # 记录测试结果
        pytest.record_property("read_avg_latency", f"{avg_latency:.2f} µs")
        pytest.record_property("read_min_latency", f"{min_latency:.2f} µs")
        pytest.record_property("read_max_latency", f"{max_latency:.2f} µs")
        pytest.record_property("read_p95_latency", f"{p95_latency:.2f} µs")
        pytest.record_property("read_p99_latency", f"{p99_latency:.2f} µs")
        pytest.record_property("read_p999_latency", f"{p999_latency:.2f} µs")
        
        # UFS 3.1 读延迟要求：平均 < 100µs，p99 < 200µs
        self.assert_less_than(avg_latency, 100, 
                            f"平均读延迟不达标: {avg_latency:.2f} µs >= 100 µs")
        self.assert_less_than(p99_latency, 200, 
                            f"P99读延迟不达标: {p99_latency:.2f} µs >= 200 µs")
        
    def test_write_latency(self):
        """测试写延迟"""
        iterations = 1000
        latencies = []
        
        lba_base = self.get_random_lba(max_blocks=iterations)
        test_data = self.generate_test_data(self.block_size, pattern="random")
        
        # 执行写延迟测试
        for i in range(iterations):
            lba = lba_base + i
            start = time.perf_counter_ns()
            self.ufs.write(lba, test_data)
            end = time.perf_counter_ns()
            latency_us = (end - start) / 1000  # 转换为微秒
            latencies.append(latency_us)
            
        # 计算统计值
        avg_latency = np.mean(latencies)
        min_latency = np.min(latencies)
        max_latency = np.max(latencies)
        p95_latency = np.percentile(latencies, 95)
        p99_latency = np.percentile(latencies, 99)
        p999_latency = np.percentile(latencies, 99.9)
        
        # 记录测试结果
        pytest.record_property("write_avg_latency", f"{avg_latency:.2f} µs")
        pytest.record_property("write_min_latency", f"{min_latency:.2f} µs")
        pytest.record_property("write_max_latency", f"{max_latency:.2f} µs")
        pytest.record_property("write_p95_latency", f"{p95_latency:.2f} µs")
        pytest.record_property("write_p99_latency", f"{p99_latency:.2f} µs")
        pytest.record_property("write_p999_latency", f"{p999_latency:.2f} µs")
        
        # UFS 3.1 写延迟要求：平均 < 200µs，p99 < 500µs
        self.assert_less_than(avg_latency, 200, 
                            f"平均写延迟不达标: {avg_latency:.2f} µs >= 200 µs")
        self.assert_less_than(p99_latency, 500, 
                            f"P99写延迟不达标: {p99_latency:.2f} µs >= 500 µs")
        
    def test_random_read_latency(self):
        """测试随机读延迟"""
        iterations = 1000
        latencies = []
        max_lba = self.get_total_blocks() - 1
        
        # 预写入所有要读取的LBA
        lbas = [self.get_random_lba() for _ in range(iterations)]
        for lba in lbas:
            test_data = self.generate_test_data(self.block_size, pattern="random")
            self.ufs.write(lba, test_data)
            
        # 执行随机读测试
        for lba in lbas:
            start = time.perf_counter_ns()
            self.ufs.read(lba, count=1)
            end = time.perf_counter_ns()
            latency_us = (end - start) / 1000
            latencies.append(latency_us)
            
        # 计算统计值
        avg_latency = np.mean(latencies)
        p99_latency = np.percentile(latencies, 99)
        
        # 记录测试结果
        pytest.record_property("random_read_avg_latency", f"{avg_latency:.2f} µs")
        pytest.record_property("random_read_p99_latency", f"{p99_latency:.2f} µs")
        
        # 随机读延迟要求
        self.assert_less_than(avg_latency, 150, 
                            f"随机读平均延迟不达标: {avg_latency:.2f} µs >= 150 µs")
        
    def test_random_write_latency(self):
        """测试随机写延迟"""
        iterations = 500
        latencies = []
        max_lba = self.get_total_blocks() - 1
        
        # 生成随机LBA和测试数据
        operations = []
        for _ in range(iterations):
            lba = self.get_random_lba()
            data = self.generate_test_data(self.block_size, pattern="random")
            operations.append((lba, data))
            
        # 执行随机写测试
        for lba, data in operations:
            start = time.perf_counter_ns()
            self.ufs.write(lba, data)
            end = time.perf_counter_ns()
            latency_us = (end - start) / 1000
            latencies.append(latency_us)
            
        # 计算统计值
        avg_latency = np.mean(latencies)
        p99_latency = np.percentile(latencies, 99)
        
        # 记录测试结果
        pytest.record_property("random_write_avg_latency", f"{avg_latency:.2f} µs")
        pytest.record_property("random_write_p99_latency", f"{p99_latency:.2f} µs")
        
        # 随机写延迟要求
        self.assert_less_than(avg_latency, 250, 
                            f"随机写平均延迟不达标: {avg_latency:.2f} µs >= 250 µs")
        
    @pytest.mark.parametrize("block_size_kb", [4, 16, 64, 256, 1024])
    def test_read_latency_vs_block_size(self, block_size_kb):
        """测试不同块大小下的读延迟"""
        block_count = block_size_kb // 4  # 每个块4KB
        iterations = 200
        latencies = []
        
        # 预写入测试数据
        lba = self.get_random_lba(max_blocks=block_count)
        test_data = self.generate_test_data(block_size_kb * 1024, pattern="random")
        self.ufs.write(lba, test_data)
        
        # 执行测试
        for _ in range(iterations):
            start = time.perf_counter_ns()
            self.ufs.read(lba, count=block_count)
            end = time.perf_counter_ns()
            latency_us = (end - start) / 1000
            latencies.append(latency_us)
            
        avg_latency = np.mean(latencies)
        throughput = (block_size_kb) / (avg_latency / 1e6)  # MB/s
        
        # 记录测试结果
        pytest.record_property(f"read_{block_size_kb}kb_avg_latency", f"{avg_latency:.2f} µs")
        pytest.record_property(f"read_{block_size_kb}kb_throughput", f"{throughput:.2f} MB/s")
        
    @pytest.mark.parametrize("queue_depth", [1, 2, 4, 8, 16, 32])
    def test_read_latency_vs_queue_depth(self, queue_depth):
        """测试不同队列深度下的读延迟"""
        iterations = 500
        latencies = []
        
        # 预写入测试数据
        lbas = [self.get_random_lba() for _ in range(queue_depth)]
        for lba in lbas:
            test_data = self.generate_test_data(self.block_size, pattern="random")
            self.ufs.write(lba, test_data)
            
        # 执行测试
        for _ in range(iterations // queue_depth):
            start = time.perf_counter_ns()
            for lba in lbas:
                self.ufs.read(lba, count=1)
            end = time.perf_counter_ns()
            batch_latency_us = (end - start) / 1000
            latencies.extend([batch_latency_us / queue_depth] * queue_depth)
            
        avg_latency = np.mean(latencies)
        p99_latency = np.percentile(latencies, 99)
        
        # 记录测试结果
        pytest.record_property(f"read_qd{queue_depth}_avg_latency", f"{avg_latency:.2f} µs")
        pytest.record_property(f"read_qd{queue_depth}_p99_latency", f"{p99_latency:.2f} µs")
        
        # 延迟随队列深度增长不应超过2倍
        if queue_depth > 1:
            self.assert_less_than(avg_latency, 200, 
                                f"队列深度{queue_depth}下读延迟过高: {avg_latency:.2f} µs")
        
    def test_read_latency_consistency(self):
        """测试读延迟一致性（抖动测试）"""
        iterations = 2000
        latencies = []
        
        # 预写入测试数据
        lba = self.get_random_lba()
        test_data = self.generate_test_data(self.block_size, pattern="random")
        self.ufs.write(lba, test_data)
        
        # 执行长时间测试
        for _ in range(iterations):
            start = time.perf_counter_ns()
            self.ufs.read(lba, count=1)
            end = time.perf_counter_ns()
            latency_us = (end - start) / 1000
            latencies.append(latency_us)
            
        avg_latency = np.mean(latencies)
        std_dev = np.std(latencies)
        max_latency = np.max(latencies)
        
        # 计算抖动系数（标准差/平均值）
        jitter_factor = std_dev / avg_latency
        
        # 记录测试结果
        pytest.record_property("read_latency_std_dev", f"{std_dev:.2f} µs")
        pytest.record_property("read_latency_jitter_factor", f"{jitter_factor:.4f}")
        pytest.record_property("read_latency_max_min_ratio", f"{max_latency/np.min(latencies):.2f}x")
        
        # 车规级要求抖动系数小于0.3，最大延迟不超过平均的3倍
        self.assert_less_than(jitter_factor, 0.3, 
                            f"读延迟抖动过大: {jitter_factor:.4f} >= 0.3")
        self.assert_less_than(max_latency / avg_latency, 3, 
                            f"读延迟波动过大: {max_latency/avg_latency:.2f}x >= 3x")
        
    def test_write_latency_consistency(self):
        """测试写延迟一致性（抖动测试）"""
        iterations = 1000
        latencies = []
        
        lba_base = self.get_random_lba(max_blocks=iterations)
        test_data = self.generate_test_data(self.block_size, pattern="random")
        
        # 执行长时间测试
        for i in range(iterations):
            lba = lba_base + i
            start = time.perf_counter_ns()
            self.ufs.write(lba, test_data)
            end = time.perf_counter_ns()
            latency_us = (end - start) / 1000
            latencies.append(latency_us)
            
        avg_latency = np.mean(latencies)
        std_dev = np.std(latencies)
        max_latency = np.max(latencies)
        
        # 计算抖动系数
        jitter_factor = std_dev / avg_latency
        
        # 记录测试结果
        pytest.record_property("write_latency_std_dev", f"{std_dev:.2f} µs")
        pytest.record_property("write_latency_jitter_factor", f"{jitter_factor:.4f}")
        pytest.record_property("write_latency_max_min_ratio", f"{max_latency/np.min(latencies):.2f}x")
        
        # 车规级要求抖动系数小于0.5，最大延迟不超过平均的4倍
        self.assert_less_than(jitter_factor, 0.5, 
                            f"写延迟抖动过大: {jitter_factor:.4f} >= 0.5")
        self.assert_less_than(max_latency / avg_latency, 4, 
                            f"写延迟波动过大: {max_latency/avg_latency:.2f}x >= 4x")
        
    def test_command_response_time(self):
        """测试基本命令响应时间"""
        commands = [
            ("NOP", 0x00, []),
            ("TEST_UNIT_READY", 0x00, []),
            ("REQUEST_SENSE", 0x03, [0x00, 0x00, 0x00, 0x12, 0x00]),
            ("INQUIRY", 0x12, [0x00, 0x00, 0x00, 0x24, 0x00]),
        ]
        
        for cmd_name, opcode, args in commands:
            iterations = 100
            latencies = []
            
            for _ in range(iterations):
                start = time.perf_counter_ns()
                self.ufs.send_command(opcode, args)
                end = time.perf_counter_ns()
                latency_us = (end - start) / 1000
                latencies.append(latency_us)
                
            avg_latency = np.mean(latencies)
            
            # 记录测试结果
            pytest.record_property(f"cmd_{cmd_name}_response_time", f"{avg_latency:.2f} µs")
            
            # 基本命令响应时间要求
            self.assert_less_than(avg_latency, 50, 
                                f"{cmd_name}命令响应时间过长: {avg_latency:.2f} µs >= 50 µs")
