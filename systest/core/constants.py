"""UFS Auto 常量配置"""

from dataclasses import dataclass


@dataclass
class Config:
    """UFS Auto 配置常量"""
    
    # 路径安全
    ALLOWED_TEST_DIR_PREFIXES = ['/tmp', '/mapdata']
    
    # 日志阈值
    LARGE_LOG_THRESHOLD_MB = 100
    HUGE_LOG_THRESHOLD_MB = 500
    
    # 空间要求
    MIN_AVAILABLE_SPACE_GB = 2.0
    
    # 测试模式
    DEFAULT_MODE = 'development'
    PRODUCTION_RUNTIME = 300
    DEVELOPMENT_RUNTIME = 60
    PRODUCTION_LOOP_COUNT = 1
    DEVELOPMENT_LOOP_COUNT = 1
