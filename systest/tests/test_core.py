"""
核心模块单元测试
"""
import sys
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))


def test_import_core_modules():
    """测试核心模块可以正常导入"""
    from core import runner
    from core import collector
    from core import reporter
    from core import logger
    from core import analyzer
    assert True


def test_runner_initialization():
    """测试 TestRunner 初始化"""
    from core.runner import TestRunner
    runner = TestRunner(dry_run=True)
    assert runner is not None


def test_list_suites():
    """测试列出测试套件"""
    from core.runner import TestRunner
    runner = TestRunner(dry_run=True)
    suites = runner.list_suites()
    assert 'performance' in suites
    assert len(suites['performance']) == 5


def test_config_loading():
    """测试配置文件加载"""
    import json
    config_path = Path(__file__).parent.parent / 'config' / 'production.json'
    with open(config_path) as f:
        config = json.load(f)
    assert 'thresholds' in config
    assert 'performance' in config['thresholds']


if __name__ == '__main__':
    test_import_core_modules()
    test_runner_initialization()
    test_list_suites()
    test_config_loading()
    print("✅ 所有测试通过")
