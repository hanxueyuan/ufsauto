"""
测试 fio_wrapper.py - FIO 工具封装
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from tools.fio_wrapper import FIO, FIOConfig, FIOMetrics, FIOError


def test_fio_class_exists():
    """测试 FIO 类存在"""
    assert FIO is not None


def test_fio_config_class():
    """测试 FIOConfig 数据类"""
    config = FIOConfig(
        name="test",
        rw="read",
        bs="128k",
        size="1G",
        runtime=60,
    )
    assert config.name == "test"
    assert config.rw == "read"
    assert config.bs == "128k"


def test_fio_config_defaults():
    """测试 FIOConfig 默认值"""
    config = FIOConfig(name="test", rw="read", bs="4k", size="1G")
    assert config is not None


def test_fio_initialization():
    """测试 FIO 初始化"""
    fio = FIO()
    assert fio is not None


def test_fio_initialization_with_timeout():
    """测试 FIO 初始化带超时"""
    fio = FIO(timeout=600)
    assert fio is not None


def test_fio_metrics_class():
    """测试 FIOMetrics 数据类"""
    assert FIOMetrics is not None


def test_fio_error_class():
    """测试 FIOError 异常类"""
    err = FIOError("test error")
    assert str(err) == "test error"


def test_fio_has_run_methods():
    """测试 FIO 有执行方法"""
    fio = FIO()
    assert hasattr(fio, 'run') or hasattr(fio, 'run_seq_read')
