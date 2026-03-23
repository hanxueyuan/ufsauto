"""
测试 ufs_utils.py - UFS 设备工具深度测试
"""
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

sys.path.insert(0, str(Path(__file__).parent.parent))

from tools.ufs_utils import UFSDevice, UFSDeviceInfo, UFSUtilsError


# --- UFSDeviceInfo 测试 ---

def test_device_info_dataclass():
    """测试 UFSDeviceInfo 数据类"""
    info = UFSDeviceInfo(
        device_path="/dev/ufs0",
        model="Samsung UFS 3.1",
        serial="ABC123",
        firmware="v2.0",
        capacity_gb=128,
        ufs_version="3.1",
        manufacturer="Samsung",
        health_status="OK",
    )
    assert info.device_path == "/dev/ufs0"
    assert info.model == "Samsung UFS 3.1"
    assert info.capacity_gb == 128
    assert info.ufs_version == "3.1"


def test_device_info_defaults():
    """测试设备信息不同容量"""
    for cap in [32, 64, 128, 256, 512]:
        info = UFSDeviceInfo(
            device_path="/dev/ufs0", model="UFS", serial="", firmware="",
            capacity_gb=cap, ufs_version="3.1", manufacturer="", health_status="OK",
        )
        assert info.capacity_gb == cap


# --- UFSUtilsError 测试 ---

def test_ufs_error():
    """测试 UFSUtilsError"""
    err = UFSUtilsError("device not found")
    assert str(err) == "device not found"


# --- UFSDevice 初始化测试 ---

def test_device_init_default():
    """测试默认路径"""
    device = UFSDevice()
    assert device.device_path == "/dev/ufs0"


def test_device_init_custom():
    """测试自定义路径"""
    device = UFSDevice("/dev/sda")
    assert device.device_path == "/dev/sda"


def test_device_init_with_logger():
    """测试自定义 logger"""
    logger = MagicMock()
    device = UFSDevice("/dev/ufs0", logger=logger)
    assert device is not None


# --- 方法存在性测试 ---

def test_device_has_exists():
    """测试有 exists 方法"""
    device = UFSDevice()
    assert callable(getattr(device, 'exists'))


def test_device_has_check_device():
    """测试有 check_device 方法"""
    device = UFSDevice()
    assert callable(getattr(device, 'check_device'))


def test_device_has_get_device_info():
    """测试有 get_device_info 方法"""
    device = UFSDevice()
    assert callable(getattr(device, 'get_device_info'))


def test_device_has_check_available_space():
    """测试有 check_available_space 方法"""
    device = UFSDevice()
    assert callable(getattr(device, 'check_available_space'))


def test_device_has_get_health_status():
    """测试有 get_health_status 方法"""
    device = UFSDevice()
    assert callable(getattr(device, 'get_health_status'))


def test_device_has_flush_cache():
    """测试有 flush_cache 方法"""
    device = UFSDevice()
    assert callable(getattr(device, 'flush_cache'))


def test_device_has_set_scheduler():
    """测试有 set_scheduler 方法"""
    device = UFSDevice()
    assert callable(getattr(device, 'set_scheduler'))


# --- 功能测试 ---

def test_device_exists_fake_path():
    """测试不存在的设备"""
    device = UFSDevice("/dev/ufs_nonexistent_99999")
    assert device.exists() == False


def test_device_check_available_space():
    """测试可用空间检查（/tmp 通常有空间）"""
    device = UFSDevice("/dev/ufs_nonexistent")
    # 检查 /tmp 空间，应该有足够空间
    result = device.check_available_space(min_gb=0.001)
    assert result == True


def test_device_check_available_space_huge():
    """测试可用空间不足"""
    device = UFSDevice("/dev/ufs_nonexistent")
    # 请求 999999 GB，肯定不够
    result = device.check_available_space(min_gb=999999)
    assert result == False


def test_device_parse_ufs_info():
    """测试 UFS 信息解析"""
    device = UFSDevice("/dev/ufs0")
    info = device._parse_ufs_info("dummy output")
    assert isinstance(info, UFSDeviceInfo)
    assert info.device_path == "/dev/ufs0"


def test_device_get_info_from_sysfs():
    """测试从 sysfs 获取信息"""
    device = UFSDevice("/dev/nonexistent")
    info = device._get_info_from_sysfs()
    assert isinstance(info, UFSDeviceInfo)
