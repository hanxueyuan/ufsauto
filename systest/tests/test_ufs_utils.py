"""
测试 ufs_utils.py - UFS 设备工具
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from tools.ufs_utils import UFSDevice


def test_ufs_device_class():
    """测试 UFSDevice 类存在"""
    assert UFSDevice is not None


def test_ufs_device_init():
    """测试 UFSDevice 初始化"""
    device = UFSDevice("/dev/null")
    assert device is not None


def test_ufs_device_init_default():
    """测试 UFSDevice 默认路径"""
    device = UFSDevice()
    assert device is not None


def test_ufs_device_has_exists():
    """测试 UFSDevice 有 exists 方法"""
    device = UFSDevice("/dev/null")
    assert hasattr(device, 'exists')


def test_ufs_device_has_check_device():
    """测试 UFSDevice 有 check_device 方法"""
    device = UFSDevice("/dev/null")
    assert hasattr(device, 'check_device')


def test_ufs_device_has_health():
    """测试 UFSDevice 有 get_health_status 方法"""
    device = UFSDevice("/dev/null")
    assert hasattr(device, 'get_health_status')


def test_ufs_device_has_space_check():
    """测试 UFSDevice 有 check_available_space 方法"""
    device = UFSDevice("/dev/null")
    assert hasattr(device, 'check_available_space')


def test_ufs_device_has_flush():
    """测试 UFSDevice 有 flush_cache 方法"""
    device = UFSDevice("/dev/null")
    assert hasattr(device, 'flush_cache')


def test_ufs_device_has_scheduler():
    """测试 UFSDevice 有 set_scheduler 方法"""
    device = UFSDevice("/dev/null")
    assert hasattr(device, 'set_scheduler')


def test_ufs_device_exists_on_fake():
    """测试不存在的设备路径"""
    device = UFSDevice("/dev/ufs_nonexistent_12345")
    assert device.exists() == False


def test_ufs_device_path_attribute():
    """测试设备路径属性"""
    device = UFSDevice("/dev/ufs0")
    assert device.device_path == "/dev/ufs0"
