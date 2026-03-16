"""
测试基类
所有测试用例都继承自该基类
"""
import pytest
import logging
import time
from typing import Dict, List, Optional
from .ufs_controller import UFSController

logger = logging.getLogger(__name__)

class UFSTestBase:
    """UFS测试基类"""
    
    # 类级别的UFS控制器实例
    _ufs: Optional[UFSController] = None
    _device_info: Dict = {}
    
    @classmethod
    def setup_class(cls):
        """类级别初始化，所有测试用例执行前执行一次"""
        logger.info(f"开始执行测试类: {cls.__name__}")
        
        # 初始化UFS控制器
        cls._ufs = UFSController()
        if not cls._ufs.connect():
            pytest.fail("UFS设备连接失败，无法执行测试")
            
        cls._device_info = cls._ufs.get_device_info()
        logger.info(f"UFS设备信息: {cls._device_info}")
        
    @classmethod
    def teardown_class(cls):
        """类级别清理，所有测试用例执行后执行一次"""
        logger.info(f"测试类执行完成: {cls.__name__}")
        
        if cls._ufs and cls._ufs.is_connected:
            cls._ufs.disconnect()
            
    def setup_method(self, method):
        """方法级别初始化，每个测试用例执行前执行"""
        logger.info(f"开始执行测试用例: {method.__name__}")
        self.test_start_time = time.time()
        
        # 确保设备处于连接状态
        if not self._ufs.is_connected:
            if not self._ufs.connect():
                pytest.fail("UFS设备连接失败，无法执行测试")
                
    def teardown_method(self, method):
        """方法级别清理，每个测试用例执行后执行"""
        execution_time = time.time() - self.test_start_time
        logger.info(f"测试用例执行完成: {method.__name__}, 耗时: {execution_time:.3f}s")
        
    @property
    def ufs(self) -> UFSController:
        """获取UFS控制器实例"""
        return self._ufs
        
    @property
    def device_info(self) -> Dict:
        """获取设备信息"""
        return self._device_info
        
    def assert_success(self, result: bool, message: str = "操作失败"):
        """断言操作成功"""
        if not result:
            pytest.fail(message)
            
    def assert_equal(self, actual, expected, message: str = "值不相等"):
        """断言值相等"""
        if actual != expected:
            pytest.fail(f"{message}: 实际值={actual}, 期望值={expected}")
            
    def assert_greater_than(self, actual, expected, message: str = "值不大于期望值"):
        """断言实际值大于期望值"""
        if actual <= expected:
            pytest.fail(f"{message}: 实际值={actual}, 期望值={expected}")
            
    def assert_less_than(self, actual, expected, message: str = "值不小于期望值"):
        """断言实际值小于期望值"""
        if actual >= expected:
            pytest.fail(f"{message}: 实际值={actual}, 期望值={expected}")
            
    def assert_between(self, actual, min_val, max_val, message: str = "值不在期望范围内"):
        """断言值在指定范围内"""
        if not (min_val <= actual <= max_val):
            pytest.fail(f"{message}: 实际值={actual}, 范围=[{min_val}, {max_val}]")
            
    def assert_no_error(self, func, *args, **kwargs):
        """断言函数执行不抛出异常"""
        try:
            return func(*args, **kwargs)
        except Exception as e:
            pytest.fail(f"函数执行抛出异常: {str(e)}")
            
    def measure_time(self, func, *args, **kwargs) -> tuple:
        """测量函数执行时间"""
        start_time = time.time()
        result = func(*args, **kwargs)
        elapsed_time = time.time() - start_time
        return result, elapsed_time
        
    def generate_test_data(self, size: int, pattern: str = "random") -> bytes:
        """
        生成测试数据
        :param size: 数据大小（字节）
        :param pattern: 数据模式：random/zero/ff/incremental
        :return: 生成的测试数据
        """
        import random
        
        if pattern == "zero":
            return b'\x00' * size
        elif pattern == "ff":
            return b'\xff' * size
        elif pattern == "incremental":
            return bytes([i % 256 for i in range(size)])
        elif pattern == "random":
            return bytes([random.randint(0, 255) for _ in range(size)])
        else:
            raise ValueError(f"不支持的数据模式: {pattern}")
            
    def verify_data_pattern(self, data: bytes, pattern: str = "random", expected: bytes = None) -> bool:
        """
        验证数据模式
        :param data: 要验证的数据
        :param pattern: 数据模式
        :param expected: 预期数据（当pattern为自定义时使用）
        :return: 验证是否通过
        """
        if expected is not None:
            return data == expected
            
        if pattern == "zero":
            return all(b == 0 for b in data)
        elif pattern == "ff":
            return all(b == 0xff for b in data)
        elif pattern == "incremental":
            return all(data[i] == i % 256 for i in range(len(data)))
        elif pattern == "random":
            # 随机数据无法验证模式，只能验证长度
            return len(data) > 0
        else:
            raise ValueError(f"不支持的数据模式: {pattern}")
            
    def get_block_size(self) -> int:
        """获取块大小（4KB）"""
        return 4096
        
    def get_total_blocks(self) -> int:
        """获取总块数"""
        return self._device_info.get("capacity", 0) // self.get_block_size()
        
    def get_random_lba(self, max_blocks: int = 1) -> int:
        """
        获取随机LBA地址
        :param max_blocks: 要操作的最大块数，确保不会超出设备范围
        :return: 随机LBA地址
        """
        import random
        total_blocks = self.get_total_blocks()
        if max_blocks >= total_blocks:
            return 0
        return random.randint(0, total_blocks - max_blocks)
