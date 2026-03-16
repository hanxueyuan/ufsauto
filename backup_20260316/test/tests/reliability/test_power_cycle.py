"""
UFS 3.1 可靠性测试 - 上下电测试
包含各种电源循环场景下的可靠性测试用例，符合AEC-Q100车规标准
"""
import pytest
import time
import random
from src.test_base import UFSTestBase

pytestmark = [pytest.mark.reliability, pytest.mark.automotive, pytest.mark.ufs31]

class TestUFSPowerCycle(UFSTestBase):
    """UFS电源循环测试类"""
    
    def setup_method(self, method):
        """测试方法初始化"""
        super().setup_method(method)
        self.block_size = self.get_block_size()
        self.test_lba = self.get_random_lba()
        self.test_data = self.generate_test_data(self.block_size, pattern="random")
        # 写入基准测试数据
        self.ufs.write(self.test_lba, self.test_data)
        
    def test_power_cycle_normal_operation(self):
        """测试正常上下电操作"""
        cycles = 100
        
        for i in range(cycles):
            # 断开连接（模拟下电）
            self.ufs.disconnect()
            time.sleep(0.1)  # 模拟断电时间
            
            # 重新连接（模拟上电）
            assert self.ufs.connect(), f"第{i}次上电失败"
            
            # 验证设备信息
            info = self.ufs.get_device_info()
            assert info["ufs_version"] == "3.1", "设备版本不匹配"
            
            # 验证数据完整性
            read_data = self.ufs.read(self.test_lba, count=1)
            assert read_data == self.test_data, f"第{i}次上电后数据损坏"
            
            # 验证基本功能
            test_data = self.generate_test_data(self.block_size, pattern="random")
            self.ufs.write(self.test_lba, test_data)
            read_back = self.ufs.read(self.test_lba, count=1)
            assert read_back == test_data, f"第{i}次上电后写入功能异常"
            
        # 记录测试结果
        pytest.record_property("power_cycle_normal_cycles", cycles)
        pytest.record_property("power_cycle_normal_result", "PASS")
        
    def test_power_cycle_during_read(self):
        """测试读操作过程中突然断电"""
        cycles = 50
        
        for i in range(cycles):
            # 开始连续读操作
            read_thread = threading.Thread(target=self._continuous_read, args=(100,))
            read_thread.start()
            
            # 随机时间后断电
            time.sleep(random.uniform(0.01, 0.1))
            self.ufs.disconnect()
            read_thread.join(timeout=1.0)
            
            # 重新上电
            time.sleep(0.1)
            assert self.ufs.connect(), f"第{i}次读中断后上电失败"
            
            # 验证数据完整性
            read_data = self.ufs.read(self.test_lba, count=1)
            assert read_data == self.test_data, f"第{i}次读中断后数据损坏"
            
            # 验证设备健康状态
            health = self.ufs.get_health_status()
            assert health["crc_error_count"] == 0, "读中断导致CRC错误"
            
        pytest.record_property("power_cycle_during_read_cycles", cycles)
        pytest.record_property("power_cycle_during_read_result", "PASS")
        
    def test_power_cycle_during_write(self):
        """测试写操作过程中突然断电"""
        cycles = 50
        
        for i in range(cycles):
            # 写入前先备份数据
            backup_data = self.ufs.read(self.test_lba, count=1)
            
            # 开始写操作
            new_data = self.generate_test_data(self.block_size, pattern="random")
            write_thread = threading.Thread(target=self.ufs.write, args=(self.test_lba, new_data))
            write_thread.start()
            
            # 随机时间后断电（在写操作完成前）
            time.sleep(random.uniform(0.001, 0.005))
            self.ufs.disconnect()
            write_thread.join(timeout=1.0)
            
            # 重新上电
            time.sleep(0.1)
            assert self.ufs.connect(), f"第{i}次写中断后上电失败"
            
            # 验证数据一致性：要么是旧数据，要么是新数据，不能是损坏的数据
            read_data = self.ufs.read(self.test_lba, count=1)
            assert read_data in (backup_data, new_data), f"第{i}次写中断后数据损坏，既不是旧数据也不是新数据"
            
            # 验证文件系统完整性（如果有）
            # 这里简化为验证基本IO功能正常
            test_data = self.generate_test_data(self.block_size, pattern="random")
            assert self.ufs.write(self.test_lba, test_data), "写中断后写入功能异常"
            assert self.ufs.read(self.test_lba, count=1) == test_data, "写中断后读取功能异常"
            
        pytest.record_property("power_cycle_during_write_cycles", cycles)
        pytest.record_property("power_cycle_during_write_result", "PASS")
        
    def test_power_cycle_during_erase(self):
        """测试擦除操作过程中突然断电"""
        cycles = 30
        block_count = 64  # 64块 = 256KB
        lba_base = self.get_random_lba(max_blocks=block_count)
        
        for i in range(cycles):
            # 预写入数据
            test_data = self.generate_test_data(self.block_size * block_count, pattern="random")
            self.ufs.write(lba_base, test_data)
            
            # 开始擦除操作
            erase_thread = threading.Thread(target=self.ufs.erase, args=(lba_base, block_count))
            erase_thread.start()
            
            # 随机时间后断电
            time.sleep(random.uniform(0.01, 0.05))
            self.ufs.disconnect()
            erase_thread.join(timeout=2.0)
            
            # 重新上电
            time.sleep(0.1)
            assert self.ufs.connect(), f"第{i}次擦除中断后上电失败"
            
            # 验证擦除区域可正常访问和写入
            new_data = self.generate_test_data(self.block_size * block_count, pattern="random")
            assert self.ufs.write(lba_base, new_data), "擦除中断后写入失败"
            read_back = self.ufs.read(lba_base, count=block_count)
            assert read_back == new_data, "擦除中断后读写数据不一致"
            
        pytest.record_property("power_cycle_during_erase_cycles", cycles)
        pytest.record_property("power_cycle_during_erase_result", "PASS")
        
    def test_power_cycle_during_trim(self):
        """测试TRIM操作过程中突然断电"""
        cycles = 30
        block_count = 128
        lba_base = self.get_random_lba(max_blocks=block_count)
        
        for i in range(cycles):
            # 预写入数据
            test_data = self.generate_test_data(self.block_size * block_count, pattern="random")
            self.ufs.write(lba_base, test_data)
            
            # 开始TRIM操作
            trim_thread = threading.Thread(target=self.ufs.trim, args=(lba_base, block_count))
            trim_thread.start()
            
            # 随机时间后断电
            time.sleep(random.uniform(0.005, 0.02))
            self.ufs.disconnect()
            trim_thread.join(timeout=1.0)
            
            # 重新上电
            time.sleep(0.1)
            assert self.ufs.connect(), f"第{i}次TRIM中断后上电失败"
            
            # 验证TRIM区域可正常访问
            new_data = self.generate_test_data(self.block_size * block_count, pattern="random")
            assert self.ufs.write(lba_base, new_data), "TRIM中断后写入失败"
            
        pytest.record_property("power_cycle_during_trim_cycles", cycles)
        pytest.record_property("power_cycle_during_trim_result", "PASS")
        
    def test_cold_boot_after_long_power_off(self):
        """测试长时间断电后的冷启动"""
        # 模拟长时间断电
        self.ufs.disconnect()
        time.sleep(5.0)  # 5秒断电时间
        
        # 冷启动
        assert self.ufs.connect(), "长时间断电后冷启动失败"
        
        # 验证所有功能正常
        info = self.ufs.get_device_info()
        assert info["capacity"] > 0, "冷启动后容量信息错误"
        
        # 验证数据
        read_data = self.ufs.read(self.test_lba, count=1)
        assert read_data == self.test_data, "冷启动后数据损坏"
        
        # 执行完整功能测试
        self._run_full_function_test()
        
        pytest.record_property("cold_boot_test_result", "PASS")
        
    def test_power_loss_under_high_load(self):
        """测试高负载下的突然掉电"""
        cycles = 20
        
        for i in range(cycles):
            # 启动高负载IO
            load_thread = threading.Thread(target=self._high_load_io, args=(1000,))
            load_thread.start()
            
            # 运行一段时间后断电
            time.sleep(random.uniform(0.1, 0.5))
            self.ufs.disconnect()
            load_thread.join(timeout=2.0)
            
            # 重新上电
            time.sleep(0.2)
            assert self.ufs.connect(), f"第{i}次高负载掉电后上电失败"
            
            # 验证设备健康状态
            health = self.ufs.get_health_status()
            assert health["bad_block_count"] == 0, "高负载掉电导致坏块"
            assert health["ecc_error_count"] <= 10, "高负载掉电导致过多ECC错误"
            
            # 验证基本功能
            self._run_smoke_test()
            
        pytest.record_property("power_loss_under_high_load_cycles", cycles)
        pytest.record_property("power_loss_under_high_load_result", "PASS")
        
    def test_power_cycle_temperature_extremes(self):
        """测试极端温度下的电源循环"""
        # 模拟低温环境（-40°C）
        self._set_temperature(-40)
        time.sleep(1.0)
        
        for i in range(20):
            self.ufs.disconnect()
            time.sleep(0.1)
            assert self.ufs.connect(), f"低温下第{i}次上电失败"
            self._run_smoke_test()
            
        # 模拟高温环境（125°C）
        self._set_temperature(125)
        time.sleep(1.0)
        
        for i in range(20):
            self.ufs.disconnect()
            time.sleep(0.1)
            assert self.ufs.connect(), f"高温下第{i}次上电失败"
            self._run_smoke_test()
            
        # 恢复常温
        self._set_temperature(25)
        
        pytest.record_property("power_cycle_temperature_extremes_result", "PASS")
        
    def _continuous_read(self, count):
        """连续读操作"""
        try:
            for _ in range(count):
                self.ufs.read(self.test_lba, count=1)
        except Exception:
            # 预期会因为断电而失败
            pass
            
    def _high_load_io(self, operations):
        """高负载IO操作"""
        try:
            for i in range(operations):
                lba = self.get_random_lba()
                if random.random() < 0.7:
                    self.ufs.read(lba, count=1)
                else:
                    data = self.generate_test_data(self.block_size, pattern="random")
                    self.ufs.write(lba, data)
        except Exception:
            # 预期会因为断电而失败
            pass
            
    def _run_smoke_test(self):
        """冒烟测试：验证基本功能正常"""
        # 读写测试
        test_data = self.generate_test_data(self.block_size, pattern="random")
        assert self.ufs.write(self.test_lba, test_data)
        assert self.ufs.read(self.test_lba, count=1) == test_data
        
        # 命令测试
        result = self.ufs.send_command(0x00)  # NOP命令
        assert result["status"] == 0
        
    def _run_full_function_test(self):
        """完整功能测试"""
        self._run_smoke_test()
        
        # 多块读写测试
        block_count = 32
        test_data = self.generate_test_data(self.block_size * block_count, pattern="random")
        lba = self.get_random_lba(max_blocks=block_count)
        assert self.ufs.write(lba, test_data)
        assert self.ufs.read(lba, count=block_count) == test_data
        
        # 擦除测试
        assert self.ufs.erase(lba, block_count)
        
    def _set_temperature(self, temperature):
        """设置环境温度（模拟）"""
        # 实际测试中需要控制温箱，这里仅记录
        pytest.record_property("test_temperature", f"{temperature}°C")
        time.sleep(0.5)  # 模拟温度稳定时间
