"""
UFS 3.1 性能测试 - 吞吐量测试
包含顺序读写、随机读写的吞吐量测试用例
"""
import pytest
import time
import numpy as np
from src.test_base import UFSTestBase

pytestmark = [pytest.mark.performance, pytest.mark.ufs31]

class TestUFSThroughput(UFSTestBase):
    """UFS吞吐量测试类"""
    
    def setup_method(self, method):
        """测试方法初始化"""
        super().setup_method(method)
        self.block_size = self.get_block_size()
        # 性能测试前先做垃圾回收
        import gc
        gc.collect()
        
    @pytest.mark.parametrize("block_count", [1, 8, 64, 512, 4096, 32768])
    def test_sequential_read_throughput(self, block_count):
        """
        测试顺序读吞吐量
        参数: block_count - 每次读取的块数
        """
        data_size = self.block_size * block_count
        total_size = 1024 * 1024 * 1024  # 1GB总测试数据量
        iterations = total_size // data_size
        
        # 确保LBA范围有效
        max_lba = self.get_total_blocks() - block_count * iterations
        if max_lba <= 0:
            pytest.skip("设备容量不足，跳过顺序读测试")
            
        base_lba = self.get_random_lba(max_blocks=block_count * iterations)
        
        # 预写入测试数据
        for i in range(iterations):
            lba = base_lba + i * block_count
            test_data = self.generate_test_data(data_size, pattern="random")
            self.ufs.write(lba, test_data)
            
        # 执行读测试
        start_time = time.time()
        for i in range(iterations):
            lba = base_lba + i * block_count
            self.ufs.read(lba, count=block_count)
        end_time = time.time()
        
        elapsed_time = end_time - start_time
        throughput = (total_size / (1024 * 1024)) / elapsed_time  # MB/s
        
        # 记录测试结果
        pytest.record_property(f"seq_read_{block_count}_blocks_throughput", f"{throughput:.2f} MB/s")
        
        # UFS 3.1 顺序读性能要求 >= 2100 MB/s
        if block_count >= 4096:  # 大块读取
            self.assert_greater_than(throughput, 2100, 
                                   f"顺序读吞吐量不达标: {throughput:.2f} MB/s < 2100 MB/s")
        elif block_count >= 512:  # 中块读取
            self.assert_greater_than(throughput, 1800, 
                                   f"顺序读吞吐量不达标: {throughput:.2f} MB/s < 1800 MB/s")
            
    @pytest.mark.parametrize("block_count", [1, 8, 64, 512, 4096, 32768])
    def test_sequential_write_throughput(self, block_count):
        """
        测试顺序写吞吐量
        参数: block_count - 每次写入的块数
        """
        data_size = self.block_size * block_count
        total_size = 512 * 1024 * 1024  # 512MB总测试数据量
        iterations = total_size // data_size
        
        # 确保LBA范围有效
        max_lba = self.get_total_blocks() - block_count * iterations
        if max_lba <= 0:
            pytest.skip("设备容量不足，跳过顺序写测试")
            
        base_lba = self.get_random_lba(max_blocks=block_count * iterations)
        
        # 生成测试数据
        test_datas = [self.generate_test_data(data_size, pattern="random") for _ in range(iterations)]
        
        # 执行写测试
        start_time = time.time()
        for i in range(iterations):
            lba = base_lba + i * block_count
            self.ufs.write(lba, test_datas[i])
        end_time = time.time()
        
        elapsed_time = end_time - start_time
        throughput = (total_size / (1024 * 1024)) / elapsed_time  # MB/s
        
        # 记录测试结果
        pytest.record_property(f"seq_write_{block_count}_blocks_throughput", f"{throughput:.2f} MB/s")
        
        # UFS 3.1 顺序写性能要求 >= 1600 MB/s
        if block_count >= 4096:  # 大块写入
            self.assert_greater_than(throughput, 1600, 
                                   f"顺序写吞吐量不达标: {throughput:.2f} MB/s < 1600 MB/s")
        elif block_count >= 512:  # 中块写入
            self.assert_greater_than(throughput, 1200, 
                                   f"顺序写吞吐量不达标: {throughput:.2f} MB/s < 1200 MB/s")
            
    @pytest.mark.parametrize("queue_depth", [1, 8, 32, 128, 256])
    def test_random_read_throughput(self, queue_depth):
        """
        测试随机读吞吐量
        参数: queue_depth - 队列深度
        """
        block_size = self.block_size
        total_ops = 10000  # 总IO操作数
        total_size = total_ops * block_size
        
        # 生成随机LBA地址
        max_lba = self.get_total_blocks() - 1
        lbas = [self.get_random_lba() for _ in range(total_ops)]
        
        # 预写入测试数据
        for lba in lbas:
            test_data = self.generate_test_data(block_size, pattern="random")
            self.ufs.write(lba, test_data)
            
        # 执行读测试
        start_time = time.time()
        # 模拟队列深度（实际应使用异步IO）
        for i in range(0, total_ops, queue_depth):
            batch = lbas[i:i+queue_depth]
            for lba in batch:
                self.ufs.read(lba, count=1)
        end_time = time.time()
        
        elapsed_time = end_time - start_time
        iops = total_ops / elapsed_time
        throughput = (total_size / (1024 * 1024)) / elapsed_time  # MB/s
        
        # 记录测试结果
        pytest.record_property(f"rand_read_qd{queue_depth}_iops", f"{iops:.0f}")
        pytest.record_property(f"rand_read_qd{queue_depth}_throughput", f"{throughput:.2f} MB/s")
        
        # UFS 3.1 随机读性能要求
        if queue_depth >= 128:
            self.assert_greater_than(iops, 400000, 
                                   f"随机读IOPS不达标: {iops:.0f} < 400000 (QD={queue_depth})")
        elif queue_depth >= 32:
            self.assert_greater_than(iops, 200000, 
                                   f"随机读IOPS不达标: {iops:.0f} < 200000 (QD={queue_depth})")
            
    @pytest.mark.parametrize("queue_depth", [1, 8, 32, 128, 256])
    def test_random_write_throughput(self, queue_depth):
        """
        测试随机写吞吐量
        参数: queue_depth - 队列深度
        """
        block_size = self.block_size
        total_ops = 5000  # 总IO操作数
        total_size = total_ops * block_size
        
        # 生成随机LBA地址和测试数据
        max_lba = self.get_total_blocks() - 1
        operations = []
        for _ in range(total_ops):
            lba = self.get_random_lba()
            data = self.generate_test_data(block_size, pattern="random")
            operations.append((lba, data))
            
        # 执行写测试
        start_time = time.time()
        # 模拟队列深度（实际应使用异步IO）
        for i in range(0, total_ops, queue_depth):
            batch = operations[i:i+queue_depth]
            for lba, data in batch:
                self.ufs.write(lba, data)
        end_time = time.time()
        
        elapsed_time = end_time - start_time
        iops = total_ops / elapsed_time
        throughput = (total_size / (1024 * 1024)) / elapsed_time  # MB/s
        
        # 记录测试结果
        pytest.record_property(f"rand_write_qd{queue_depth}_iops", f"{iops:.0f}")
        pytest.record_property(f"rand_write_qd{queue_depth}_throughput", f"{throughput:.2f} MB/s")
        
        # UFS 3.1 随机写性能要求
        if queue_depth >= 128:
            self.assert_greater_than(iops, 350000, 
                                   f"随机写IOPS不达标: {iops:.0f} < 350000 (QD={queue_depth})")
        elif queue_depth >= 32:
            self.assert_greater_than(iops, 150000, 
                                   f"随机写IOPS不达标: {iops:.0f} < 150000 (QD={queue_depth})")
            
    def test_read_write_mixed_throughput(self):
        """测试读写混合吞吐量"""
        block_size = self.block_size
        total_ops = 8000
        read_ratio = 0.7  # 70%读，30%写
        
        # 生成操作序列
        operations = []
        for i in range(total_ops):
            lba = self.get_random_lba()
            if np.random.random() < read_ratio:
                operations.append(("read", lba))
            else:
                data = self.generate_test_data(block_size, pattern="random")
                operations.append(("write", lba, data))
                
        # 预写入所有要读取的LBA
        for op in operations:
            if op[0] == "read":
                test_data = self.generate_test_data(block_size, pattern="random")
                self.ufs.write(op[1], test_data)
                
        # 执行混合读写测试
        start_time = time.time()
        for op in operations:
            if op[0] == "read":
                self.ufs.read(op[1], count=1)
            else:
                self.ufs.write(op[1], op[2])
        end_time = time.time()
        
        elapsed_time = end_time - start_time
        total_iops = total_ops / elapsed_time
        
        # 记录测试结果
        pytest.record_property("mixed_rw_iops", f"{total_iops:.0f}")
        pytest.record_property("mixed_rw_read_ratio", f"{read_ratio*100}%")
        
        # 混合读写性能要求
        self.assert_greater_than(total_iops, 250000, 
                               f"混合读写IOPS不达标: {total_iops:.0f} < 250000")
                               
    def test_sustained_write_performance(self):
        """测试持续写入性能（验证SLC缓存溢出后的性能）"""
        block_size = self.block_size
        block_count = 32768  # 128MB per write
        total_writes = 32  # 总共写入4GB
        total_size = block_size * block_count * total_writes
        
        base_lba = self.get_random_lba(max_blocks=block_count * total_writes)
        test_data = self.generate_test_data(block_size * block_count, pattern="random")
        
        # 记录每次写入的性能
        throughputs = []
        
        start_time = time.time()
        for i in range(total_writes):
            lba = base_lba + i * block_count
            iter_start = time.time()
            self.ufs.write(lba, test_data)
            iter_end = time.time()
            
            iter_time = iter_end - iter_start
            throughput = (block_size * block_count / (1024 * 1024)) / iter_time
            throughputs.append(throughput)
            
        end_time = time.time()
        total_time = end_time - start_time
        avg_throughput = (total_size / (1024 * 1024)) / total_time
        min_throughput = min(throughputs)
        
        # 记录测试结果
        pytest.record_property("sustained_write_avg_throughput", f"{avg_throughput:.2f} MB/s")
        pytest.record_property("sustained_write_min_throughput", f"{min_throughput:.2f} MB/s")
        
        # 持续写入性能要求：即使缓存溢出，最低性能也应大于400MB/s
        self.assert_greater_than(min_throughput, 400, 
                               f"持续写入最低性能不达标: {min_throughput:.2f} MB/s < 400 MB/s")
        self.assert_greater_than(avg_throughput, 800, 
                               f"持续写入平均性能不达标: {avg_throughput:.2f} MB/s < 800 MB/s")
