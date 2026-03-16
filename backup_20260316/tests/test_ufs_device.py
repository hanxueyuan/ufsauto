#!/usr/bin/env python3
"""
UfsDevice 类单元测试
"""

import unittest
import os
import sys
import tempfile
from unittest.mock import Mock, patch, MagicMock

# 添加src目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from ufs_device import UfsDevice, UfsDescType, UfsAttrId, UfsFlagId, UfsOpcode, UfsPowerMode, UfsDeviceInfo

class TestUfsDevice(unittest.TestCase):
    """UfsDevice类单元测试"""
    
    def setUp(self):
        """测试前设置"""
        self.mock_fd = 123  # 模拟文件描述符
        self.device_path = "/dev/mock-ufs"
        
    @patch('os.open')
    @patch('os.close')
    def test_open_close(self, mock_close, mock_open):
        """测试设备打开和关闭"""
        mock_open.return_value = self.mock_fd
        
        dev = UfsDevice(self.device_path)
        self.assertFalse(dev.is_open)
        self.assertIsNone(dev.fd)
        
        # 模拟_read_device_info
        with patch.object(dev, '_read_device_info') as mock_read_info:
            mock_read_info.return_value = Mock(spec=UfsDeviceInfo)
            
            result = dev.open()
            self.assertTrue(result)
            self.assertTrue(dev.is_open)
            self.assertEqual(dev.fd, self.mock_fd)
            mock_open.assert_called_once_with(self.device_path, os.O_RDWR | os.O_SYNC)
            
            # 测试重复打开
            result = dev.open()
            self.assertTrue(result)
            mock_close.assert_called_once_with(self.mock_fd)
            
            # 测试关闭
            dev.close()
            self.assertFalse(dev.is_open)
            self.assertIsNone(dev.fd)
            self.assertEqual(mock_close.call_count, 2)  # 重复打开时关了一次，这里又关一次
            
    @patch('os.open')
    def test_open_failure(self, mock_open):
        """测试打开失败情况"""
        mock_open.side_effect = IOError("Permission denied")
        
        dev = UfsDevice(self.device_path)
        result = dev.open()
        self.assertFalse(result)
        self.assertFalse(dev.is_open)
        self.assertIsNone(dev.fd)
        
    @patch.object(UfsDevice, 'query_descriptor')
    @patch.object(UfsDevice, 'query_attribute')
    @patch.object(UfsDevice, 'query_flag')
    def test_read_device_info(self, mock_query_flag, mock_query_attr, mock_query_desc):
        """测试读取设备信息"""
        # 模拟描述符数据
        device_desc = bytearray(64)
        device_desc[0] = 0x1F  # 制造商ID
        device_desc[5] = 0x31  # 版本3.1
        device_desc[16:32] = b"TEST_UFS_DEVICE\x00\x00\x00"
        device_desc[32:48] = b"SN123456789ABCDEF"
        device_desc[48:56] = b"FW1.0.0\x00\x00"
        device_desc[56:58] = b"\x07\x00"  # 支持WB、HPB、RPMB
        device_desc[60] = 45  # 温度45°C
        
        geom_desc = bytearray(48)
        geom_desc[5] = 8  # 最大LUN=8
        geom_desc[6] = 0x0F  # 支持gear 1-4
        geom_desc[7] = 2  # 2通道
        geom_desc[40:48] = (256 * 1024 * 1024 * 1024 // 512).to_bytes(8, 'little')  # 256GB
        
        power_desc = bytearray(32)
        
        mock_query_desc.side_effect = [device_desc, geom_desc, power_desc]
        mock_query_attr.return_value = 0  # 健康状态
        
        with patch('os.open', return_value=self.mock_fd):
            with UfsDevice(self.device_path) as dev:
                info = dev.device_info
                
                self.assertEqual(info.manufacturer_id, 0x1F)
                self.assertEqual(info.product_name, "TEST_UFS_DEVICE")
                self.assertEqual(info.serial_number, "SN123456789ABCDEF")
                self.assertEqual(info.firmware_version, "FW1.0.0")
                self.assertEqual(info.spec_version, "3.1")
                self.assertEqual(info.total_capacity, 256 * 1024 * 1024 * 1024)
                self.assertEqual(info.max_lun, 8)
                self.assertEqual(info.supported_gear, [1, 2, 3, 4])
                self.assertEqual(info.supported_lanes, 2)
                self.assertTrue(info.write_booster_supported)
                self.assertTrue(info.hpb_supported)
                self.assertTrue(info.rpmb_supported)
                self.assertEqual(info.temperature, 45)
                
    @patch.object(UfsDevice, 'open')
    @patch('fcntl.ioctl')
    def test_query_descriptor(self, mock_ioctl, mock_open):
        """测试查询描述符"""
        mock_open.return_value = True
        mock_ioctl.return_value = b'\x00' * 6 + b'\x01\x02\x03\x04'  # 4字节数据
        
        dev = UfsDevice(self.device_path)
        dev.is_open = True
        dev.fd = self.mock_fd
        
        result = dev.query_descriptor(UfsDescType.DEVICE, 0, 0)
        
        self.assertEqual(result, b'\x01\x02\x03\x04')
        mock_ioctl.assert_called_once()
        
    @patch.object(UfsDevice, 'open')
    @patch('fcntl.ioctl')
    def test_query_attribute(self, mock_ioctl, mock_open):
        """测试查询属性"""
        mock_open.return_value = True
        mock_ioctl.return_value = b'\x00\x00\x00\x00' + (0x12345678).to_bytes(4, 'little')
        
        dev = UfsDevice(self.device_path)
        dev.is_open = True
        dev.fd = self.mock_fd
        
        result = dev.query_attribute(UfsAttrId.bActiveICCLevel)
        
        self.assertEqual(result, 0x12345678)
        
    @patch.object(UfsDevice, 'open')
    @patch('fcntl.ioctl')
    def test_set_attribute(self, mock_ioctl, mock_open):
        """测试设置属性"""
        mock_open.return_value = True
        
        dev = UfsDevice(self.device_path)
        dev.is_open = True
        dev.fd = self.mock_fd
        
        result = dev.set_attribute(UfsAttrId.bActiveICCLevel, 0x02)
        
        self.assertTrue(result)
        mock_ioctl.assert_called_once()
        
    @patch.object(UfsDevice, 'open')
    @patch('fcntl.ioctl')
    def test_query_flag(self, mock_ioctl, mock_open):
        """测试查询标志"""
        mock_open.return_value = True
        mock_ioctl.return_value = b'\x00\x00\x00' + b'\x01'  # 标志为True
        
        dev = UfsDevice(self.device_path)
        dev.is_open = True
        dev.fd = self.mock_fd
        
        result = dev.query_flag(UfsFlagId.fBackgroundOpsEn)
        
        self.assertTrue(result)
        
    @patch.object(UfsDevice, 'open')
    @patch('fcntl.ioctl')
    def test_set_flag(self, mock_ioctl, mock_open):
        """测试设置标志"""
        mock_open.return_value = True
        
        dev = UfsDevice(self.device_path)
        dev.is_open = True
        dev.fd = self.mock_fd
        
        result = dev.set_flag(UfsFlagId.fBackgroundOpsEn, True)
        
        self.assertTrue(result)
        mock_ioctl.assert_called_once()
        
    @patch.object(UfsDevice, 'send_command')
    def test_read_lba(self, mock_send_cmd):
        """测试读取LBA"""
        mock_response = b'\x00' * 4 + b'test_data' * 64  # 512字节
        
        mock_result = Mock()
        mock_result.success = True
        mock_result.response = mock_response
        mock_send_cmd.return_value = mock_result
        
        dev = UfsDevice(self.device_path)
        dev.is_open = True
        dev.fd = self.mock_fd
        
        ok, data = dev.read_lba(1024, 1)
        
        self.assertTrue(ok)
        self.assertEqual(len(data), 512)
        mock_send_cmd.assert_called_once_with(
            opcode=UfsOpcode.READ,
            lun=0,
            lba=1024,
            transfer_len=1
        )
        
    @patch.object(UfsDevice, 'send_command')
    def test_write_lba(self, mock_send_cmd):
        """测试写入LBA"""
        test_data = b'A' * 512
        
        mock_result = Mock()
        mock_result.success = True
        mock_result.duration = 0.01
        mock_send_cmd.return_value = mock_result
        
        dev = UfsDevice(self.device_path)
        dev.is_open = True
        dev.fd = self.mock_fd
        
        ok, duration = dev.write_lba(1024, test_data)
        
        self.assertTrue(ok)
        self.assertEqual(duration, 0.01)
        mock_send_cmd.assert_called_once_with(
            opcode=UfsOpcode.WRITE,
            lun=0,
            lba=1024,
            transfer_len=1,
            data=test_data
        )
        
        # 测试非512倍数数据
        with self.assertRaises(ValueError):
            dev.write_lba(1024, b'A' * 123)
            
    @patch.object(UfsDevice, 'send_command')
    def test_erase_lba(self, mock_send_cmd):
        """测试擦除LBA"""
        mock_result = Mock()
        mock_result.success = True
        mock_result.duration = 0.1
        mock_send_cmd.return_value = mock_result
        
        dev = UfsDevice(self.device_path)
        dev.is_open = True
        dev.fd = self.mock_fd
        
        ok, duration = dev.erase_lba(1024, 100)
        
        self.assertTrue(ok)
        self.assertEqual(duration, 0.1)
        mock_send_cmd.assert_called_once_with(
            opcode=UfsOpcode.ERASE,
            lun=0,
            lba=1024,
            transfer_len=100
        )
        
    @patch.object(UfsDevice, 'query_attribute')
    @patch.object(UfsDevice, 'open')
    def test_power_mode(self, mock_open, mock_query_attr):
        """测试电源模式管理"""
        mock_open.return_value = True
        mock_query_attr.return_value = UfsPowerMode.ACTIVE.value
        
        dev = UfsDevice(self.device_path)
        dev.is_open = True
        dev.fd = self.mock_fd
        
        mode = dev.get_power_mode()
        self.assertEqual(mode, UfsPowerMode.ACTIVE)
        
        with patch.object(dev, 'set_attribute') as mock_set_attr:
            mock_set_attr.return_value = True
            result = dev.set_power_mode(UfsPowerMode.SLEEP)
            self.assertTrue(result)
            mock_set_attr.assert_called_once_with(UfsAttrId.bCurrentPowerMode, UfsPowerMode.SLEEP.value)
            
    @patch.object(UfsDevice, 'query_flag')
    @patch.object(UfsDevice, 'query_attribute')
    @patch.object(UfsDevice, 'query_descriptor')
    @patch.object(UfsDevice, 'open')
    def test_get_health_report(self, mock_open, mock_query_desc, mock_query_attr, mock_query_flag):
        """测试获取健康报告"""
        mock_open.return_value = True
        
        # 模拟设备信息
        mock_dev_info = Mock(spec=UfsDeviceInfo)
        mock_dev_info.product_name = "TestDevice"
        mock_dev_info.serial_number = "TEST123"
        mock_dev_info.firmware_version = "1.0.0"
        mock_dev_info.total_capacity = 256 * 1024**3
        mock_dev_info.write_booster_supported = True
        
        # 模拟描述符返回温度
        mock_desc = bytearray(64)
        mock_desc[60] = 55  # 55°C
        mock_query_desc.return_value = mock_desc
        
        # 模拟属性查询
        mock_query_attr.side_effect = [
            10,  # bDeviceInfo = 10
            1000,  # wAvailableAddrSpaceUnits
            0x0000  # wExceptionEventStatus
        ]
        
        # 模拟标志查询
        mock_query_flag.side_effect = [
            True,  # fWriteBoosterEn
            True   # fBackgroundOpsEn
        ]
        
        with patch.object(dev, '_read_device_info', return_value=mock_dev_info):
            dev = UfsDevice(self.device_path)
            dev.open()
            
            health = dev.get_health_report()
            
            self.assertEqual(health['product_name'], "TestDevice")
            self.assertEqual(health['serial_number'], "TEST123")
            self.assertEqual(health['firmware_version'], "1.0.0")
            self.assertEqual(health['total_capacity_gb'], 256.0)
            self.assertEqual(health['health_percent'], 90)  # 100 - 10
            self.assertEqual(health['temperature_celsius'], 55)
            self.assertTrue(health['write_booster_enabled'])
            self.assertTrue(health['background_ops_enabled'])
            
    @patch.object(UfsDevice, 'write_lba')
    @patch.object(UfsDevice, 'read_lba')
    @patch.object(UfsDevice, 'get_health_report')
    @patch.object(UfsDevice, 'query_descriptor')
    @patch.object(UfsDevice, 'open')
    def test_self_test(self, mock_open, mock_query_desc, mock_get_health, mock_read, mock_write):
        """测试自检功能"""
        mock_open.return_value = True
        mock_get_health.return_value = {'product_name': 'TestDevice'}
        mock_query_desc.return_value = b'\x00' * 100  # 足够长的描述符
        
        # 模拟写入成功
        mock_write.return_value = (True, 0.001)
        # 模拟读取成功且数据一致
        test_data = b"UFS_TEST_PATTERN_" * 32
        mock_read.return_value = (True, test_data)
        
        dev = UfsDevice(self.device_path)
        dev.is_open = True
        dev.device_info = Mock()
        
        results = dev.self_test(short_test=True)
        
        self.assertEqual(results['overall_result'], 'pass')
        self.assertEqual(len(results['tests']), 4)  # device_info, descriptor, write, read
        self.assertTrue(all(t['status'] == 'pass' for t in results['tests']))
        
        # 测试读取验证失败情况
        mock_read.return_value = (True, b'wrong_data' * 64)
        results = dev.self_test(short_test=True)
        self.assertEqual(results['overall_result'], 'fail')
        self.assertTrue(any('read_verify' in t['name'] and t['status'] == 'fail' for t in results['tests']))

class TestUfsDeviceIntegration(unittest.TestCase):
    """集成测试，需要实际UFS设备或模拟器"""
    
    def setUp(self):
        self.test_device = os.getenv('UFS_TEST_DEVICE', '/dev/ufs0')
        # 检查是否有测试设备
        if not os.path.exists(self.test_device):
            self.skipTest(f"测试设备 {self.test_device} 不存在，跳过集成测试")
            
        # 检查是否有访问权限
        try:
            with open(self.test_device, 'rb'):
                pass
        except PermissionError:
            self.skipTest(f"无权限访问测试设备 {self.test_device}，跳过集成测试")
            
    def test_device_open(self):
        """测试实际设备打开"""
        with UfsDevice(self.test_device) as dev:
            self.assertTrue(dev.is_open)
            self.assertIsNotNone(dev.device_info)
            self.assertGreater(dev.device_info.total_capacity, 0)
            print(f"\n设备: {dev.device_info.product_name}")
            print(f"容量: {dev.device_info.total_capacity / (1024**3):.2f} GB")
            print(f"版本: UFS {dev.device_info.spec_version}")
            
    def test_health_report(self):
        """测试健康报告读取"""
        with UfsDevice(self.test_device) as dev:
            health = dev.get_health_report()
            self.assertIn('product_name', health)
            self.assertIn('health_percent', health)
            self.assertIn('temperature_celsius', health)
            print(f"\n健康度: {health['health_percent']}%")
            print(f"温度: {health['temperature_celsius']}°C")
            print(f"电源模式: {health['power_mode']}")
            
    def test_basic_io(self):
        """测试基本IO操作"""
        test_lba = 1024 * 1024 * 2  # 2G位置，避免分区
        test_data = b"INTEGRATION_TEST_DATA_" * 256  # 4KB
        
        with UfsDevice(self.test_device) as dev:
            # 写入测试
            ok, write_time = dev.write_lba(test_lba, test_data)
            self.assertTrue(ok, "写入失败")
            print(f"\n写入4KB耗时: {write_time*1000:.2f}ms")
            
            # 读取验证
            ok, read_data = dev.read_lba(test_lba, 8)  # 8 * 512 = 4KB
            self.assertTrue(ok, "读取失败")
            self.assertEqual(read_data, test_data, "数据验证失败")
            print("数据验证通过")
            
    def test_perf_basic(self):
        """测试基础性能"""
        test_lba = 1024 * 1024 * 2
        block_size = 4096
        count = 100
        
        with UfsDevice(self.test_device) as dev:
            # 写入测试
            start = time.time()
            for i in range(count):
                data = os.urandom(block_size)
                ok, _ = dev.write_lba(test_lba + i * (block_size // 512), data)
                self.assertTrue(ok)
            write_time = time.time() - start
            write_speed = (count * block_size) / write_time / (1024 * 1024)
            print(f"\n顺序写入 {count * block_size / 1024} KB: {write_speed:.2f} MB/s")
            
            # 读取测试
            start = time.time()
            for i in range(count):
                ok, _ = dev.read_lba(test_lba + i * (block_size // 512), block_size // 512)
                self.assertTrue(ok)
            read_time = time.time() - start
            read_speed = (count * block_size) / read_time / (1024 * 1024)
            print(f"顺序读取 {count * block_size / 1024} KB: {read_speed:.2f} MB/s")

if __name__ == '__main__':
    import time
    unittest.main(verbosity=2)
