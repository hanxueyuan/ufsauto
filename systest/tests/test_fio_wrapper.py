"""
测试 fio_wrapper.py - FIO 配置和命令构建的深度测试
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from tools.fio_wrapper import FIO, FIOConfig, FIOMetrics, FIOError


# --- FIOConfig 测试 ---

import unittest


class TestFioWrapper(unittest.TestCase):
    def test_fio_config_basic(self):
        """测试基本配置"""
        config = FIOConfig(name="test", rw="read", bs="128k", size="1G", runtime=60)
        assert config.name == "test"
        assert config.rw == "read"
        assert config.bs == "128k"
        assert config.size == "1G"
        assert config.runtime == 60


    def test_fio_config_defaults(self):
        """测试默认值"""
        config = FIOConfig()
        assert config.ioengine == "sync"
        assert config.direct == True
        assert config.numjobs == 1
        assert config.iodepth == 1
        assert config.group_reporting == True
        assert config.output_format == "json"


    def test_fio_config_seq_read(self):
        """测试顺序读配置"""
        config = FIOConfig(name="seq_read", rw="read", bs="128k", size="1G")
        assert config.rw == "read"


    def test_fio_config_rand_write(self):
        """测试随机写配置"""
        config = FIOConfig(name="rand_write", rw="randwrite", bs="4k", iodepth=64)
        assert config.rw == "randwrite"
        assert config.iodepth == 64


    def test_fio_config_mixed_rw(self):
        """测试混合读写配置"""
        config = FIOConfig(name="mixed", rw="randrw", rwmixread=70)
        assert config.rw == "randrw"
        assert config.rwmixread == 70


    def test_fio_config_to_args(self):
        """测试命令行参数生成"""
        config = FIOConfig(name="test_cmd", rw="read", bs="4k", size="1G", runtime=30)
        args = config.to_args()
        assert isinstance(args, list)
        assert args[0] == "fio"
        assert "--name=test_cmd" in args
        assert "--rw=read" in args
        assert "--bs=4k" in args


    def test_fio_config_to_args_has_filename(self):
        """测试命令行包含 filename"""
        config = FIOConfig(filename="/dev/sda")
        args = config.to_args()
        assert any("/dev/sda" in a for a in args)


    def test_fio_config_to_args_has_direct(self):
        """测试命令行包含 direct"""
        config = FIOConfig(direct=True)
        args = config.to_args()
        assert any("direct" in a for a in args)


    def test_fio_config_advanced_params(self):
        """测试高级参数"""
        config = FIOConfig(
            ramp_time=5,
            time_based=True,
            rate_iops=50000,
        )
        assert config.ramp_time == 5
        assert config.time_based == True
        assert config.rate_iops == 50000


    def test_fio_config_various_block_sizes(self):
        """测试不同块大小"""
        for bs in ["4k", "8k", "16k", "32k", "64k", "128k", "256k", "512k", "1m"]:
            config = FIOConfig(bs=bs)
            assert config.bs == bs


    def test_fio_config_various_rw_types(self):
        """测试不同读写类型"""
        for rw in ["read", "write", "randread", "randwrite", "randrw", "readwrite"]:
            config = FIOConfig(rw=rw)
            assert config.rw == rw


    # --- FIO 类测试 ---

    def test_fio_init(self):
        """测试 FIO 初始化"""
        fio = FIO()
        assert fio is not None


    def test_fio_init_timeout(self):
        """测试自定义超时"""
        fio = FIO(timeout=600)
        assert fio is not None


    def test_fio_init_retries(self):
        """测试自定义重试"""
        fio = FIO(retries=3)
        assert fio is not None


    def test_fio_has_run(self):
        """测试有 run 方法"""
        fio = FIO()
        assert hasattr(fio, 'run')


    # --- FIOMetrics 测试 ---

    def test_fio_metrics_class(self):
        """测试 FIOMetrics 类存在"""
        assert FIOMetrics is not None


    # --- FIOError 测试 ---

    def test_fio_error(self):
        """测试 FIOError"""
        err = FIOError("test error")
        assert str(err) == "test error"


    def test_fio_error_with_returncode(self):
        """测试 FIOError 带返回码"""
        err = FIOError("failed", returncode=1)
        assert err.returncode == 1


    def test_fio_error_with_stderr(self):
        """测试 FIOError 带 stderr"""
        err = FIOError("failed", stderr="permission denied")
        assert err.stderr == "permission denied"



if __name__ == "__main__":
    unittest.main()
