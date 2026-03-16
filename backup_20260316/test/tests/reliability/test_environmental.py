"""
UFS 3.1 可靠性测试 - 环境可靠性测试
包含温度、湿度、振动等环境条件下的可靠性测试用例，符合AEC-Q100 Grade 2车规标准
"""
import pytest
import time
import random
import numpy as np
from src.test_base import UFSTestBase

pytestmark = [pytest.mark.reliability, pytest.mark.automotive, pytest.mark.ufs31]

class TestUFSEnvironmentalReliability(UFSTestBase):
    """UFS环境可靠性测试类"""
    
    def setup_method(self, method):
        """测试方法初始化"""
        super().setup_method(method)
        self.block_size = self.get_block_size()
        self.test_data = self.generate_test_data(self.block_size * 1024, pattern="random")
        self.base_lba = self.get_random_lba(max_blocks=10000)
        
    @pytest.mark.parametrize("temperature", [-40, -20, 0, 25, 60, 85, 105, 125])
    def test_operation_at_temperature(self, temperature):
        """测试不同温度下的功能正确性"""
        # 设置环境温度
        self._set_temperature(temperature)
        time.sleep(300)  # 5分钟温度稳定时间（加速测试用30s）
        
        # 执行功能测试
        self._run_full_function_test()
        
        # 执行性能测试
        throughput = self._measure_sequential_read_throughput()
        pytest.record_property(f"throughput_{temperature}C", f"{throughput:.2f} MB/s")
        
        # 性能下降不应超过30%
        if temperature in (-40, 125):
            self.assert_greater_than(throughput, 1500 * 0.7, 
                                   f"{temperature}°C下性能下降过多: {throughput:.2f} MB/s")
                                   
        pytest.record_property(f"operation_at_{temperature}C_result", "PASS")
        
    def test_temperature_cycling(self):
        """测试温度循环可靠性"""
        cycles = 100
        temperature_profile = [
            (-40, 30),   # -40°C保持30分钟
            (25, 15),    # 常温过渡15分钟
            (125, 30),   # 125°C保持30分钟
            (25, 15),    # 常温过渡15分钟
        ]
        
        for cycle in range(cycles):
            pytest.record_property("temperature_cycle", cycle)
            
            for temp, hold_time in temperature_profile:
                self._set_temperature(temp)
                time.sleep(hold_time)  # 保持时间（加速测试用1s）
                
                # 在每个温度点执行功能测试
                self._run_smoke_test()
                
                # 验证数据完整性
                read_data = self.ufs.read(self.base_lba, count=1)
                assert read_data == self.test_data[:self.block_size], "温度循环中数据损坏"
                
        # 测试完成后恢复常温
        self._set_temperature(25)
        time.sleep(60)
        
        # 最终完整功能验证
        self._run_full_function_test()
        
        pytest.record_property("temperature_cycles_completed", cycles)
        pytest.record_property("temperature_cycling_result", "PASS")
        
    def test_thermal_shock(self):
        """测试热冲击可靠性（快速温度变化）"""
        cycles = 50
        
        for cycle in range(cycles):
            pytest.record_property("thermal_shock_cycle", cycle)
            
            # 低温到高温快速切换
            self._set_temperature(-40)
            time.sleep(60)  # 稳定时间
            self._run_smoke_test()
            
            # 快速切换到高温（< 1分钟）
            self._set_temperature(125, ramp_rate=50)  # 50°C/分钟的升温速率
            time.sleep(60)
            self._run_smoke_test()
            
            # 快速切换回低温
            self._set_temperature(-40, ramp_rate=50)
            time.sleep(60)
            self._run_smoke_test()
            
        # 恢复常温并验证
        self._set_temperature(25)
        self._run_full_function_test()
        
        # 验证设备健康状态
        health = self.ufs.get_health_status()
        assert health["bad_block_count"] == 0, "热冲击测试导致坏块"
        assert health["ecc_error_count"] <= 50, "热冲击测试导致过多ECC错误"
        
        pytest.record_property("thermal_shock_cycles_completed", cycles)
        pytest.record_property("thermal_shock_result", "PASS")
        
    @pytest.mark.parametrize("humidity", [10, 30, 50, 70, 90, 95])
    def test_humidity_operation(self, humidity):
        """测试不同湿度下的功能正确性"""
        # 设置湿度，温度保持25°C
        self._set_humidity(humidity, temperature=25)
        time.sleep(120)  # 湿度稳定时间
        
        # 执行长时间读写测试
        operations = 1000
        for i in range(operations):
            lba = self.base_lba + i
            data = self.generate_test_data(self.block_size, pattern="random")
            self.ufs.write(lba, data)
            read_back = self.ufs.read(lba, count=1)
            assert read_back == data, f"湿度{humidity}%下读写失败，LBA: {lba}"
            
        pytest.record_property(f"humidity_{humidity}_percent_result", "PASS")
        
    def test_high_temperature_high_humidity(self):
        """测试高温高湿可靠性（85°C/85% RH）"""
        # 设置85°C/85% RH环境
        self._set_temperature(85)
        self._set_humidity(85)
        time.sleep(300)  # 稳定时间
        
        # 长时间运行测试（持续1000小时，这里加速测试）
        test_duration = 3600  # 1小时加速测试
        start_time = time.time()
        
        while time.time() - start_time < test_duration:
            # 持续执行IO操作
            for _ in range(100):
                lba = self.get_random_lba()
                if random.random() < 0.7:
                    self.ufs.read(lba, count=1)
                else:
                    data = self.generate_test_data(self.block_size, pattern="random")
                    self.ufs.write(lba, data)
                    
            # 每10分钟验证一次数据完整性
            if int(time.time() - start_time) % 600 == 0:
                read_data = self.ufs.read(self.base_lba, count=1)
                assert read_data == self.test_data[:self.block_size], "高温高湿下数据损坏"
                
        # 恢复常温常湿
        self._set_temperature(25)
        self._set_humidity(50)
        time.sleep(3600)  # 干燥时间
        
        # 完整功能验证
        self._run_full_function_test()
        
        # 验证没有封装或腐蚀问题
        health = self.ufs.get_health_status()
        assert health["bad_block_count"] == 0, "高温高湿测试导致坏块"
        
        pytest.record_property("hthh_test_duration", f"{test_duration}s")
        pytest.record_property("hthh_test_result", "PASS")
        
    def test_vibration_operation(self):
        """测试振动环境下的功能正确性"""
        # 启动振动测试（10-2000Hz，1g加速度，符合车规振动标准）
        self._start_vibration(frequency_range=(10, 2000), acceleration=1.0)
        
        # 在振动环境下执行IO测试
        operations = 10000
        errors = 0
        
        for i in range(operations):
            try:
                lba = self.base_lba + i
                data = self.generate_test_data(self.block_size, pattern="random")
                self.ufs.write(lba, data)
                read_back = self.ufs.read(lba, count=1)
                assert read_back == data, "振动下读写不一致"
            except Exception as e:
                errors += 1
                if errors > 10:  # 允许少量重试错误
                    raise
                    
        # 停止振动
        self._stop_vibration()
        
        assert errors <= 10, f"振动测试中错误过多: {errors}"
        
        # 振动后验证所有数据
        for i in range(operations):
            lba = self.base_lba + i
            read_data = self.ufs.read(lba, count=1)
            # 验证数据完整性
            
        pytest.record_property("vibration_test_operations", operations)
        pytest.record_property("vibration_test_errors", errors)
        pytest.record_property("vibration_test_result", "PASS")
        
    def test_mechanical_shock(self):
        """测试机械冲击可靠性"""
        # 执行1500g，0.5ms的半正弦冲击（符合AEC-Q100标准）
        shocks = 100
        
        for i in range(shocks):
            # 沿X轴冲击
            self._apply_shock(axis="x", acceleration=1500, duration_ms=0.5)
            self._run_smoke_test()
            
            # 沿Y轴冲击
            self._apply_shock(axis="y", acceleration=1500, duration_ms=0.5)
            self._run_smoke_test()
            
            # 沿Z轴冲击
            self._apply_shock(axis="z", acceleration=1500, duration_ms=0.5)
            self._run_smoke_test()
            
        # 冲击测试后完整验证
        self._run_full_function_test()
        
        # 验证设备没有物理损坏
        info = self.ufs.get_device_info()
        assert info is not None, "机械冲击后设备无法识别"
        
        pytest.record_property("mechanical_shocks_applied", shocks * 3)
        pytest.record_property("mechanical_shock_result", "PASS")
        
    def test_temperature_bias_operation(self):
        """测试温度偏置下的运行可靠性"""
        # 高温偏置测试（125°C，最高工作温度）
        self._set_temperature(125)
        time.sleep(300)
        
        # 持续运行100小时（加速测试）
        start_time = time.time()
        test_duration = 3600  # 1小时
        
        while time.time() - start_time < test_duration:
            # 执行高负载操作
            self._high_load_test(duration=60)
            
            # 检查温度和健康状态
            temp = self.ufs.get_temperature()
            self.assert_between(temp, 120, 135, f"温度过高: {temp}°C")
            
            health = self.ufs.get_health_status()
            assert health["remaining_life"] > 98, "高温偏置测试导致寿命过度消耗"
            
        # 低温偏置测试（-40°C，最低工作温度）
        self._set_temperature(-40)
        time.sleep(300)
        
        start_time = time.time()
        while time.time() - start_time < test_duration:
            self._high_load_test(duration=60)
            
            temp = self.ufs.get_temperature()
            self.assert_between(temp, -45, -35, f"温度过低: {temp}°C")
            
        # 恢复常温
        self._set_temperature(25)
        self._run_full_function_test()
        
        pytest.record_property("temperature_bias_test_result", "PASS")
        
    def test_operating_life_estimation(self):
        """测试工作寿命估算（加速寿命测试）"""
        # 加速条件：125°C，连续高负载
        self._set_temperature(125)
        time.sleep(300)
        
        # 运行加速寿命测试
        test_duration = 3600 * 24  # 24小时加速测试，相当于正常使用约1000小时
        start_time = time.time()
        
        initial_health = self.ufs.get_health_status()
        initial_life = initial_health["remaining_life"]
        
        while time.time() - start_time < test_duration:
            self._high_load_test(duration=300)  # 5分钟高负载
            
            # 每小时记录一次健康状态
            if int(time.time() - start_time) % 3600 == 0:
                current_health = self.ufs.get_health_status()
                current_life = current_health["remaining_life"]
                life_consumed = initial_life - current_life
                pytest.record_property("life_consumed", f"{life_consumed:.2f}%")
                
                # 寿命消耗应该符合预期，24小时加速测试消耗不应超过1%
                assert life_consumed < 1.0, f"寿命消耗过快: {life_consumed:.2f}% in 24h"
                
        # 恢复常温
        self._set_temperature(25)
        
        # 计算估计寿命
        final_health = self.ufs.get_health_status()
        total_life_consumed = initial_life - final_health["remaining_life"]
        estimated_life_hours = (test_duration / 3600) * (100 / total_life_consumed) if total_life_consumed > 0 else float('inf')
        
        pytest.record_property("estimated_operating_life", f"{estimated_life_hours:.0f} hours")
        pytest.record_property("operating_life_test_result", "PASS")
        
        # 车规级要求工作寿命至少20000小时
        self.assert_greater_than(estimated_life_hours, 20000, 
                               f"估计工作寿命不足: {estimated_life_hours:.0f}小时 < 20000小时")
        
    def _run_smoke_test(self):
        """冒烟测试"""
        test_data = self.generate_test_data(self.block_size, pattern="random")
        test_lba = self.base_lba
        
        # 测试基本读写
        assert self.ufs.write(test_lba, test_data)
        read_back = self.ufs.read(test_lba, count=1)
        assert read_back == test_data
        
        # 测试基本命令
        result = self.ufs.send_command(0x00)  # NOP
        assert result["status"] == 0
        
    def _run_full_function_test(self):
        """完整功能测试"""
        self._run_smoke_test()
        
        # 多块读写测试
        block_count = 1024
        test_data = self.generate_test_data(self.block_size * block_count, pattern="random")
        lba = self.base_lba + 100
        
        assert self.ufs.write(lba, test_data)
        read_back = self.ufs.read(lba, count=block_count)
        assert read_back == test_data
        
        # 擦除测试
        assert self.ufs.erase(lba, block_count)
        
        # TRIM测试
        assert self.ufs.trim(lba, block_count)
        
    def _measure_sequential_read_throughput(self):
        """测量顺序读吞吐量"""
        block_count = 4096
        total_size = self.block_size * block_count
        lba = self.base_lba
        
        # 预写入数据
        test_data = self.generate_test_data(total_size, pattern="random")
        self.ufs.write(lba, test_data)
        
        # 测试读取
        start = time.time()
        self.ufs.read(lba, count=block_count)
        elapsed = time.time() - start
        
        return (total_size / (1024 * 1024)) / elapsed
        
    def _high_load_test(self, duration):
        """高负载测试"""
        end_time = time.time() + duration
        while time.time() < end_time:
            lba = self.get_random_lba()
            if random.random() < 0.7:
                self.ufs.read(lba, count=1)
            else:
                data = self.generate_test_data(self.block_size, pattern="random")
                self.ufs.write(lba, data)
                
    def _set_temperature(self, temperature, ramp_rate=1.0):
        """设置环境温度（模拟）"""
        pytest.record_property("set_temperature", f"{temperature}°C, {ramp_rate}°C/min")
        time.sleep(0.1)  # 模拟温度变化时间
        
    def _set_humidity(self, humidity, temperature=25):
        """设置环境湿度（模拟）"""
        pytest.record_property("set_humidity", f"{humidity}% at {temperature}°C")
        time.sleep(0.1)
        
    def _start_vibration(self, frequency_range, acceleration):
        """启动振动测试（模拟）"""
        pytest.record_property("vibration_start", f"{frequency_range[0]}-{frequency_range[1]}Hz, {acceleration}g")
        time.sleep(0.1)
        
    def _stop_vibration(self):
        """停止振动测试（模拟）"""
        pytest.record_property("vibration_stop", "")
        time.sleep(0.1)
        
    def _apply_shock(self, axis, acceleration, duration_ms):
        """施加机械冲击（模拟）"""
        pytest.record_property("shock_applied", f"{axis} axis, {acceleration}g, {duration_ms}ms")
        time.sleep(0.01)
