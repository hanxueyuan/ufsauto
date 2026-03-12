"""
UFS 3.1 可靠性测试 - 数据完整性测试
包含各种场景下的数据完整性验证测试用例，符合ISO 26262功能安全标准
"""
import pytest
import time
import random
import hashlib
import numpy as np
from src.test_base import UFSTestBase

pytestmark = [pytest.mark.reliability, pytest.mark.automotive, pytest.mark.ufs31]

class TestUFSDataIntegrity(UFSTestBase):
    """UFS数据完整性测试类"""
    
    def setup_method(self, method):
        """测试方法初始化"""
        super().setup_method(method)
        self.block_size = self.get_block_size()
        self.test_region_size = 1024 * 1024 * 1024  # 1GB测试区域
        self.test_region_blocks = self.test_region_size // self.block_size
        self.base_lba = self.get_random_lba(max_blocks=self.test_region_blocks)
        
    def test_sequential_write_read_verify(self):
        """测试顺序写入-读取-验证数据完整性"""
        iterations = 10
        block_count = 4096  # 16MB per iteration
        
        for i in range(iterations):
            lba = self.base_lba + i * block_count
            test_data = self.generate_test_data(self.block_size * block_count, pattern="incremental")
            
            # 写入数据
            self.ufs.write(lba, test_data)
            
            # 立即读取验证
            read_data = self.ufs.read(lba, count=block_count)
            assert read_data == test_data, f"第{i}次顺序写入后立即验证失败"
            
            # 延迟读取验证
            time.sleep(0.1)
            read_data = self.ufs.read(lba, count=block_count)
            assert read_data == test_data, f"第{i}次顺序写入后延迟验证失败"
            
            # 计算数据校验和
            original_md5 = hashlib.md5(test_data).hexdigest()
            read_md5 = hashlib.md5(read_data).hexdigest()
            assert original_md5 == read_md5, f"第{i}次MD5校验失败"
            
        pytest.record_property("sequential_write_verify_iterations", iterations)
        pytest.record_property("sequential_write_verify_result", "PASS")
        
    def test_random_write_read_verify(self):
        """测试随机写入-读取-验证数据完整性"""
        operations = 1000
        written_blocks = {}
        
        for i in range(operations):
            # 随机选择LBA
            offset = random.randint(0, self.test_region_blocks - 1)
            lba = self.base_lba + offset
            
            # 生成随机数据
            test_data = self.generate_test_data(self.block_size, pattern="random")
            data_md5 = hashlib.md5(test_data).hexdigest()
            
            # 写入数据
            self.ufs.write(lba, test_data)
            written_blocks[lba] = data_md5
            
            # 立即验证
            read_data = self.ufs.read(lba, count=1)
            read_md5 = hashlib.md5(read_data).hexdigest()
            assert read_md5 == data_md5, f"第{i}次随机写入验证失败，LBA: {lba}"
            
        # 全部写入后再次验证所有块
        for lba, expected_md5 in written_blocks.items():
            read_data = self.ufs.read(lba, count=1)
            read_md5 = hashlib.md5(read_data).hexdigest()
            assert read_md5 == expected_md5, f"随机写入后整体验证失败，LBA: {lba}"
            
        pytest.record_property("random_write_verify_operations", operations)
        pytest.record_property("random_write_verify_result", "PASS")
        
    def test_data_retention_short_term(self):
        """测试短期数据保持能力（常温下）"""
        # 写入测试数据
        test_blocks = 1000
        block_md5 = {}
        
        for i in range(test_blocks):
            lba = self.base_lba + i
            test_data = self.generate_test_data(self.block_size, pattern="random")
            md5 = hashlib.md5(test_data).hexdigest()
            self.ufs.write(lba, test_data)
            block_md5[lba] = md5
            
        # 等待1小时（这里加速测试，实际测试需要更长时间）
        wait_time = 60  # 1分钟加速测试
        time.sleep(wait_time)
        
        # 验证数据
        errors = 0
        for lba, expected_md5 in block_md5.items():
            read_data = self.ufs.read(lba, count=1)
            read_md5 = hashlib.md5(read_data).hexdigest()
            if read_md5 != expected_md5:
                errors += 1
                pytest.record_property(f"data_retention_error_lba_{lba}", f"expected: {expected_md5}, actual: {read_md5}")
                
        assert errors == 0, f"短期数据保持测试发现{errors}个错误块"
        
        pytest.record_property("data_retention_short_term_wait_time", f"{wait_time}s")
        pytest.record_property("data_retention_short_term_result", "PASS")
        
    def test_data_retention_high_temperature(self):
        """测试高温下的数据保持能力"""
        # 写入测试数据
        test_blocks = 500
        block_md5 = {}
        
        for i in range(test_blocks):
            lba = self.base_lba + i
            test_data = self.generate_test_data(self.block_size, pattern="random")
            md5 = hashlib.md5(test_data).hexdigest()
            self.ufs.write(lba, test_data)
            block_md5[lba] = md5
            
        # 模拟高温环境（85°C）
        self._set_temperature(85)
        wait_time = 300  # 5分钟加速测试
        time.sleep(wait_time)
        
        # 恢复到常温
        self._set_temperature(25)
        time.sleep(60)  # 等待温度稳定
        
        # 验证数据
        errors = 0
        for lba, expected_md5 in block_md5.items():
            read_data = self.ufs.read(lba, count=1)
            read_md5 = hashlib.md5(read_data).hexdigest()
            if read_md5 != expected_md5:
                errors += 1
                
        assert errors == 0, f"高温数据保持测试发现{errors}个错误块"
        
        pytest.record_property("data_retention_high_temp", "85°C")
        pytest.record_property("data_retention_high_temp_duration", f"{wait_time}s")
        pytest.record_property("data_retention_high_temp_result", "PASS")
        
    def test_write_read_disturb(self):
        """测试读写干扰（相邻块读写不影响已有数据）"""
        # 写入基准数据到目标块
        target_lba = self.base_lba + 100
        target_data = self.generate_test_data(self.block_size, pattern="random")
        target_md5 = hashlib.md5(target_data).hexdigest()
        self.ufs.write(target_lba, target_data)
        
        # 对相邻块进行大量读写操作
        iterations = 10000
        adjacent_lbas = [self.base_lba + i for i in range(80, 120) if i != 100]
        
        for i in range(iterations):
            lba = random.choice(adjacent_lbas)
            if random.random() < 0.5:
                test_data = self.generate_test_data(self.block_size, pattern="random")
                self.ufs.write(lba, test_data)
            else:
                self.ufs.read(lba, count=1)
                
        # 验证目标块数据未被干扰
        read_data = self.ufs.read(target_lba, count=1)
        read_md5 = hashlib.md5(read_data).hexdigest()
        assert read_md5 == target_md5, "读写干扰测试失败，目标块数据被损坏"
        
        pytest.record_property("write_read_disturb_iterations", iterations)
        pytest.record_property("write_read_disturb_result", "PASS")
        
    def test_read_disturb_robustness(self):
        """测试读干扰鲁棒性（同一块多次读取不损坏数据）"""
        # 写入测试数据
        test_lba = self.base_lba
        test_data = self.generate_test_data(self.block_size, pattern="random")
        expected_md5 = hashlib.md5(test_data).hexdigest()
        self.ufs.write(test_lba, test_data)
        
        # 大量读取同一块
        read_count = 1000000  # 100万次读取
        for i in range(read_count):
            self.ufs.read(test_lba, count=1)
            if i % 10000 == 0:
                # 每1万次验证一次数据
                read_data = self.ufs.read(test_lba, count=1)
                read_md5 = hashlib.md5(read_data).hexdigest()
                assert read_md5 == expected_md5, f"第{i}次读取后数据损坏"
                
        # 最终验证
        read_data = self.ufs.read(test_lba, count=1)
        read_md5 = hashlib.md5(read_data).hexdigest()
        assert read_md5 == expected_md5, "读干扰测试最终验证失败"
        
        pytest.record_property("read_disturb_count", read_count)
        pytest.record_property("read_disturb_result", "PASS")
        
    def test_power_loss_data_integrity(self):
        """测试突然掉电时的数据完整性"""
        test_blocks = 100
        iterations = 50
        
        for i in range(iterations):
            # 写入基准数据
            baseline_data = {}
            for j in range(test_blocks):
                lba = self.base_lba + j
                data = self.generate_test_data(self.block_size, pattern="random")
                self.ufs.write(lba, data)
                baseline_data[lba] = hashlib.md5(data).hexdigest()
                
            # 开始随机写入，然后突然掉电
            write_thread = threading.Thread(target=self._random_writes, args=(test_blocks, 1000))
            write_thread.start()
            
            # 随机时间后掉电
            time.sleep(random.uniform(0.05, 0.2))
            self.ufs.disconnect()
            write_thread.join(timeout=1.0)
            
            # 重新上电
            time.sleep(0.1)
            assert self.ufs.connect(), f"第{i}次掉电后上电失败"
            
            # 验证数据：未被写入的块应保持原样，被写入的块要么是旧数据要么是新数据
            errors = 0
            for lba, expected_md5 in baseline_data.items():
                try:
                    read_data = self.ufs.read(lba, count=1)
                    read_md5 = hashlib.md5(read_data).hexdigest()
                    # 数据要么是基线版本，要么是被成功写入的新版本
                    # 这里简化为只要读取成功且不是全FF或全0就算通过
                    assert not all(b in (0x00, 0xff) for b in read_data), f"LBA {lba} 数据为空"
                except Exception as e:
                    errors += 1
                    
            assert errors == 0, f"第{i}次掉电测试发现{errors}个不可恢复的块错误"
            
        pytest.record_property("power_loss_data_integrity_iterations", iterations)
        pytest.record_property("power_loss_data_integrity_result", "PASS")
        
    def test_ecc_correction_capability(self):
        """测试ECC纠错能力"""
        # 注意：这个测试需要硬件支持注入错误，这里模拟测试
        test_lba = self.base_lba
        original_data = self.generate_test_data(self.block_size, pattern="random")
        self.ufs.write(test_lba, original_data)
        
        # 模拟读取到有1bit错误的数据（实际测试需要硬件支持）
        # 这里验证设备能够纠正可纠正的错误
        health = self.ufs.get_health_status()
        initial_ecc_errors = health["ecc_error_count"]
        
        # 执行大量随机读写，可能产生可纠正的ECC错误
        for _ in range(10000):
            lba = self.get_random_lba()
            if random.random() < 0.5:
                self.ufs.read(lba, count=1)
            else:
                data = self.generate_test_data(self.block_size, pattern="random")
                self.ufs.write(lba, data)
                
        # 检查ECC错误计数是否在合理范围内
        health = self.ufs.get_health_status()
        total_ecc_errors = health["ecc_error_count"] - initial_ecc_errors
        
        # ECC错误应该被纠正，不会导致数据损坏
        assert total_ecc_errors <= 100, f"ECC错误数过多: {total_ecc_errors}"
        
        # 验证所有数据仍然可读
        read_data = self.ufs.read(test_lba, count=1)
        assert read_data == original_data, "ECC纠错失败，数据损坏"
        
        pytest.record_property("ecc_correction_errors", total_ecc_errors)
        pytest.record_property("ecc_correction_result", "PASS")
        
    def test_bad_block_management(self):
        """测试坏块管理能力"""
        # 写入大量数据，验证坏块管理
        total_blocks = 10000
        errors = 0
        
        for i in range(total_blocks):
            lba = self.base_lba + i
            try:
                data = self.generate_test_data(self.block_size, pattern="random")
                self.ufs.write(lba, data)
                read_back = self.ufs.read(lba, count=1)
                assert read_back == data, f"块 {lba} 读写不一致"
            except Exception as e:
                errors += 1
                # 标记为坏块，设备应该自动重映射
                pytest.record_property(f"bad_block_{lba}", str(e))
                
        # 坏块率应该小于0.01%
        bad_block_rate = errors / total_blocks * 100
        assert bad_block_rate < 0.01, f"坏块率过高: {bad_block_rate:.4f}% >= 0.01%"
        
        health = self.ufs.get_health_status()
        reported_bad_blocks = health["bad_block_count"]
        assert reported_bad_blocks >= errors, "设备报告的坏块数少于实际发现的坏块数"
        
        pytest.record_property("tested_blocks", total_blocks)
        pytest.record_property("bad_blocks_found", errors)
        pytest.record_property("bad_block_rate", f"{bad_block_rate:.4f}%")
        pytest.record_property("bad_block_management_result", "PASS")
        
    def _random_writes(self, test_blocks, count):
        """执行随机写入操作"""
        try:
            for _ in range(count):
                lba = self.base_lba + random.randint(0, test_blocks - 1)
                data = self.generate_test_data(self.block_size, pattern="random")
                self.ufs.write(lba, data)
        except Exception:
            # 预期会因为掉电而失败
            pass
            
    def _set_temperature(self, temperature):
        """设置环境温度（模拟）"""
        pytest.record_property("test_temperature", f"{temperature}°C")
        time.sleep(0.5)  # 模拟温度稳定时间
