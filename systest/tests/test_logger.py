"""
测试 logger.py - 日志管理器
"""
import sys
import tempfile
import os
import logging
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.logger import get_logger, close_all_loggers, TestLogger


import unittest


class TestLoggerUnit(unittest.TestCase):
    def test_get_logger(self):
        """测试获取日志实例"""
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = get_logger(
                test_id="test_log_001",
                log_dir=tmpdir,
                console_level=logging.WARNING,
                file_level=logging.DEBUG,
            )
            assert logger is not None
            close_all_loggers()


    def test_logger_write(self):
        """测试日志写入"""
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = get_logger(
                test_id="test_log_002",
                log_dir=tmpdir,
                console_level=logging.WARNING,
                file_level=logging.DEBUG,
            )
            logger.info("测试信息")
            logger.warning("测试警告")
            logger.error("测试错误")

            log_file = logger.get_log_file()
            assert log_file is not None
            assert os.path.exists(log_file)
            close_all_loggers()


    def test_logger_log_file_content(self):
        """测试日志文件内容"""
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = get_logger(
                test_id="test_log_003",
                log_dir=tmpdir,
                console_level=logging.WARNING,
                file_level=logging.DEBUG,
            )
            logger.info("hello_marker")

            log_file = logger.get_log_file()
            with open(log_file, 'r') as f:
                content = f.read()
            assert "hello_marker" in content
            close_all_loggers()


    def test_test_logger_class(self):
        """测试 TestLogger 类"""
        tl = TestLogger("unit_test")
        assert tl is not None
        assert tl.test_id == "unit_test"



if __name__ == "__main__":
    unittest.main()
