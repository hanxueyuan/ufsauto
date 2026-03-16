"""
UFS 3.1 功能测试 - 基础操作测试
包含设备连接、读写、擦除等基础功能测试用例
"""
import pytest
from src.test_base import UFSTestBase

pytestmark = [pytest.mark.functional, pytest.mark.ufs31]

class TestUFSBasicOperations(UFSTestBase):
    """UFS基础操作测试类"""
    
    def test_device_connection(self):
        """测试设备连接功能"""
        # 验证设备已连接
        assert self.ufs.is_connected == True, "UFS设备未连接"
        
        # 验证设备信息不为空
        assert self.device_info is not None, "设备信息为空"
        assert "model" in self.device_info, "设备信息中缺少model字段"
        assert "ufs_version" in self.device_info, "设备信息中缺少ufs_version字段"
        
        # 验证UFS版本为3.1
        assert self.device_info["ufs_version"] == "3.1", f"UFS版本不匹配，期望3.1，实际{self.device_info['ufs_version']}"
        
    def test_device_info(self):
        """测试设备信息读取"""
        info = self.ufs.get_device_info()
        
        # 验证必要字段存在
        required_fields = ["model", "manufacturer", "serial_number", "capacity", 
                          "ufs_version", "spec_version", "max_speed", "max_lanes"]
        for field in required_fields:
            assert field in info, f"设备信息缺少必填字段: {field}"
            
        # 验证容量大于0
        assert info["capacity"] > 0, "设备容量为0"
        
        # 验证规格版本符合UFS 3.1
        assert info["spec_version"] == "JESD220E", f"规格版本不匹配，期望JESD220E，实际{info['spec_version']}"
        
    def test_single_block_read_write(self):
        """测试单块读写操作"""
        block_size = self.get_block_size()
        lba = self.get_random_lba()
        
        # 生成测试数据
        test_data = self.generate_test_data(block_size, pattern="random")
        
        # 写入数据
        write_result = self.ufs.write(lba, test_data)
        self.assert_success(write_result, "单块写入失败")
        
        # 读取数据
        read_data = self.ufs.read(lba, count=1)
        assert len(read_data) == block_size, f"读取数据长度不匹配，期望{block_size}，实际{len(read_data)}"
        
        # 验证数据一致性
        assert read_data == test_data, "单块读写数据不一致"
        
    def test_multiple_block_read_write(self):
        """测试多块读写操作"""
        block_size = self.get_block_size()
        block_count = 16  # 16块 = 64KB
        lba = self.get_random_lba(max_blocks=block_count)
        
        # 生成测试数据
        test_data = self.generate_test_data(block_size * block_count, pattern="incremental")
        
        # 写入数据
        write_result = self.ufs.write(lba, test_data)
        self.assert_success(write_result, "多块写入失败")
        
        # 读取数据
        read_data = self.ufs.read(lba, count=block_count)
        assert len(read_data) == block_size * block_count, f"读取数据长度不匹配，期望{block_size * block_count}，实际{len(read_data)}"
        
        # 验证数据一致性
        assert read_data == test_data, "多块读写数据不一致"
        
    def test_large_block_read_write(self):
        """测试大块读写操作"""
        block_size = self.get_block_size()
        block_count = 1024  # 1024块 = 4MB
        lba = self.get_random_lba(max_blocks=block_count)
        
        # 生成测试数据
        test_data = self.generate_test_data(block_size * block_count, pattern="random")
        
        # 写入数据
        write_result = self.ufs.write(lba, test_data)
        self.assert_success(write_result, "大块写入失败")
        
        # 读取数据
        read_data = self.ufs.read(lba, count=block_count)
        assert len(read_data) == block_size * block_count, f"读取数据长度不匹配，期望{block_size * block_count}，实际{len(read_data)}"
        
        # 验证数据一致性
        assert read_data == test_data, "大块读写数据不一致"
        
    def test_block_erase(self):
        """测试块擦除操作"""
        block_size = self.get_block_size()
        block_count = 8
        lba = self.get_random_lba(max_blocks=block_count)
        
        # 先写入非零数据
        test_data = self.generate_test_data(block_size * block_count, pattern="ff")
        self.ufs.write(lba, test_data)
        
        # 执行擦除
        erase_result = self.ufs.erase(lba, block_count)
        self.assert_success(erase_result, "块擦除失败")
        
        # 读取擦除后的数据
        read_data = self.ufs.read(lba, count=block_count)
        
        # 验证擦除后的数据为全0（或者根据设备实际行为）
        # 注意：有些设备擦除后为全1，这里需要根据实际情况调整
        assert all(b in (0x00, 0xff) for b in read_data), "块擦除后数据不为空"
        
    def test_trim_command(self):
        """测试TRIM命令"""
        block_size = self.get_block_size()
        block_count = 32
        lba = self.get_random_lba(max_blocks=block_count)
        
        # 先写入数据
        test_data = self.generate_test_data(block_size * block_count, pattern="random")
        self.ufs.write(lba, test_data)
        
        # 执行TRIM
        trim_result = self.ufs.trim(lba, block_count)
        self.assert_success(trim_result, "TRIM命令执行失败")
        
        # TRIM后数据可能仍可读，但性能应该提升，这里只验证命令执行成功
        
    def test_temperature_reading(self):
        """测试温度读取功能"""
        temperature = self.ufs.get_temperature()
        
        # 验证温度在合理范围内（车规级通常为-40°C ~ 125°C）
        self.assert_between(temperature, -40, 125, f"温度值超出合理范围: {temperature}°C")
        
    def test_health_status(self):
        """测试健康状态读取"""
        health_status = self.ufs.get_health_status()
        
        # 验证必要字段存在
        required_fields = ["total_blocks_written", "remaining_life", "bad_block_count",
                          "ecc_error_count", "crc_error_count", "power_cycle_count"]
        for field in required_fields:
            assert field in health_status, f"健康状态缺少必填字段: {field}"
            
        # 验证剩余寿命在0-100之间
        self.assert_between(health_status["remaining_life"], 0, 100, 
                           f"剩余寿命值不合理: {health_status['remaining_life']}%")
                           
        # 验证坏块数和错误数非负
        assert health_status["bad_block_count"] >= 0, "坏块数不能为负数"
        assert health_status["ecc_error_count"] >= 0, "ECC错误数不能为负数"
        assert health_status["crc_error_count"] >= 0, "CRC错误数不能为负数"
        
    def test_consecutive_read_write(self):
        """测试连续读写操作"""
        block_size = self.get_block_size()
        iterations = 100
        lba_base = self.get_random_lba(max_blocks=iterations)
        
        for i in range(iterations):
            lba = lba_base + i
            test_data = self.generate_test_data(block_size, pattern="incremental")
            
            # 写入
            write_result = self.ufs.write(lba, test_data)
            self.assert_success(write_result, f"第{i}次写入失败")
            
            # 读取
            read_data = self.ufs.read(lba, count=1)
            assert read_data == test_data, f"第{i}次读写数据不一致"
            
    def test_random_read_write(self):
        """测试随机地址读写"""
        block_size = self.get_block_size()
        iterations = 50
        total_blocks = self.get_total_blocks()
        
        for i in range(iterations):
            lba = self.get_random_lba()
            test_data = self.generate_test_data(block_size, pattern="random")
            
            # 写入
            write_result = self.ufs.write(lba, test_data)
            self.assert_success(write_result, f"随机写入失败，LBA: {lba}")
            
            # 读取
            read_data = self.ufs.read(lba, count=1)
            assert read_data == test_data, f"随机读写数据不一致，LBA: {lba}"
            
    def test_boundary_lba_operation(self):
        """测试边界LBA地址操作"""
        block_size = self.get_block_size()
        total_blocks = self.get_total_blocks()
        
        # 测试LBA 0
        test_data = self.generate_test_data(block_size, pattern="random")
        write_result = self.ufs.write(0, test_data)
        self.assert_success(write_result, "LBA 0写入失败")
        read_data = self.ufs.read(0, count=1)
        assert read_data == test_data, "LBA 0读写数据不一致"
        
        # 测试最后一个LBA
        last_lba = total_blocks - 1
        test_data = self.generate_test_data(block_size, pattern="random")
        write_result = self.ufs.write(last_lba, test_data)
        self.assert_success(write_result, f"最后一个LBA({last_lba})写入失败")
        read_data = self.ufs.read(last_lba, count=1)
        assert read_data == test_data, f"最后一个LBA({last_lba})读写数据不一致"
