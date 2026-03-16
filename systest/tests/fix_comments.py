#!/usr/bin/env python3
"""
批量修复测试用例注释脚本
统一 Precondition 分级格式
"""

import os
from pathlib import Path

# 标准的 Precondition 模板
STANDARD_PRECONDITION = """Precondition:
1.1 系统环境收集
    - 操作系统：Debian 12, kernel 5.15.120
    - CPU/内存：8 核，16GB
    - FIO 版本：fio-3.33

1.2 测试目标信息收集
    - 设备路径：/dev/ufs0
    - 设备型号：UFS 3.1 128GB
    - 固件版本：v1.0.0
    - 设备容量：128GB
    - 可用空间：≥{available_space}

1.3 存储设备配置检查
    - 开启功能：{enable_funcs}
    - 关闭功能：{disable_funcs}
    - 特殊配置：{special_config}

1.4 UFS 器件配置检查
    - LUN 数量：4 个
    - LUN0：64GB 系统盘（已挂载）
    - LUN1：32GB 数据盘（测试目标）
    - LUN2：16GB 日志盘
    - LUN3：16GB 预留
    - LUN 映射：LUN1→/dev/ufs0

1.5 器件健康状况检查
    - SMART 状态：正常
    - 剩余寿命：98%
    - 坏块数量：0
    - 温度状态：35℃（当前）/ 45℃（最高）
    - 错误计数：CRC 错误=0, 重传次数=0

1.6 前置条件验证
    - ✓ SMART 状态必须为正常
    - ✓ 可用空间必须≥{verify_space}
    - ✓ 温度必须<70℃
    - ✓ 剩余寿命必须>90%"""

# 每个测试用例的配置
TEST_CONFIGS = {
    't_performance_SequentialReadBurst_001.py': {
        'available_space': '10GB',
        'verify_space': '10GB',
        'enable_funcs': 'TURBO Mode（提升峰值性能）',
        'disable_funcs': '省电模式（避免性能限制）',
        'special_config': '无'
    },
    't_performance_SequentialReadSustained_002.py': {
        'available_space': '10GB',
        'verify_space': '10GB',
        'enable_funcs': 'TURBO Mode（提升峰值性能）',
        'disable_funcs': '省电模式（避免性能限制）',
        'special_config': '无'
    },
    't_performance_SequentialWriteBurst_003.py': {
        'available_space': '10GB',
        'verify_space': '10GB',
        'enable_funcs': 'TURBO Mode（提升峰值性能）',
        'disable_funcs': '省电模式（避免性能限制）',
        'special_config': '无'
    },
    't_performance_SequentialWriteSustained_004.py': {
        'available_space': '20GB（长时间测试需要更多空间）',
        'verify_space': '20GB',
        'enable_funcs': '无特殊开启',
        'disable_funcs': '省电模式（避免性能限制）',
        'special_config': '无'
    },
    't_performance_RandomReadBurst_005.py': {
        'available_space': '10GB',
        'verify_space': '10GB',
        'enable_funcs': 'TURBO Mode（提升峰值性能）',
        'disable_funcs': '省电模式（避免性能限制）',
        'special_config': '无'
    },
    't_performance_RandomReadSustained_006.py': {
        'available_space': '10GB',
        'verify_space': '10GB',
        'enable_funcs': 'TURBO Mode（提升峰值性能）',
        'disable_funcs': '省电模式（避免性能限制）',
        'special_config': '无'
    },
    't_performance_RandomWriteBurst_007.py': {
        'available_space': '10GB',
        'verify_space': '10GB',
        'enable_funcs': 'TURBO Mode（提升峰值性能）',
        'disable_funcs': '省电模式（避免性能限制）',
        'special_config': '无'
    },
    't_performance_RandomWriteSustained_008.py': {
        'available_space': '20GB（长时间测试需要更多空间）',
        'verify_space': '20GB',
        'enable_funcs': '无特殊开启',
        'disable_funcs': '省电模式（避免性能限制）',
        'special_config': '无'
    },
    't_performance_MixedRw_009.py': {
        'available_space': '10GB',
        'verify_space': '10GB',
        'enable_funcs': 'TURBO Mode（提升峰值性能）',
        'disable_funcs': '省电模式（避免性能限制）',
        'special_config': '无'
    },
    't_qos_LatencyPercentile_001.py': {
        'available_space': '10GB',
        'verify_space': '10GB',
        'enable_funcs': '无特殊开启',
        'disable_funcs': '省电模式（避免性能限制）',
        'special_config': '无'
    },
    't_qos_LatencyJitter_002.py': {
        'available_space': '10GB',
        'verify_space': '10GB',
        'enable_funcs': '无特殊开启',
        'disable_funcs': '省电模式（避免性能限制）',
        'special_config': '无'
    },
    't_reliability_StabilityTest_001.py': {
        'available_space': '20GB（长时间测试需要更多空间）',
        'verify_space': '20GB',
        'enable_funcs': '无特殊开启',
        'disable_funcs': '自动休眠（避免影响长时间测试）',
        'special_config': 'IO 调度器设置为 none（减少调度延迟）'
    },
    't_scenario_SensorWrite_001.py': {
        'available_space': '5GB',
        'verify_space': '5GB',
        'enable_funcs': '无特殊开启',
        'disable_funcs': '省电模式（避免性能限制）',
        'special_config': '无'
    },
    't_scenario_ModelLoad_002.py': {
        'available_space': '10GB',
        'verify_space': '10GB',
        'enable_funcs': 'TURBO Mode（提升峰值性能）',
        'disable_funcs': '省电模式（避免性能限制）',
        'special_config': '无'
    }
}

def fix_test_file(filepath, config):
    """修复单个测试文件的注释"""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 生成标准 Precondition
    precondition = STANDARD_PRECONDITION.format(**config)
    
    # 查找并替换 Precondition 部分
    # 简单策略：找到 "Precondition:" 到 "Test Steps:" 之间的内容并替换
    import re
    
    # 匹配旧的 Precondition 部分
    pattern = r'(Precondition:).*?(Test Steps:)'
    replacement = precondition + '\n\n' + r'\2'
    
    new_content = re.sub(pattern, replacement, content, flags=re.DOTALL)
    
    if new_content != content:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(new_content)
        return True
    return False

def main():
    """主函数"""
    tests_dir = Path(__file__).parent
    fixed_count = 0
    
    for filename, config in TEST_CONFIGS.items():
        filepath = tests_dir / filename
        if filepath.exists():
            print(f"修复 {filename}...")
            if fix_test_file(filepath, config):
                fixed_count += 1
                print(f"  ✅ 已修复")
            else:
                print(f"  ⚠️  无需修复或修复失败")
        else:
            print(f"  ❌ 文件不存在：{filename}")
    
    print(f"\n修复完成！共修复 {fixed_count}/{len(TEST_CONFIGS)} 个文件")

if __name__ == '__main__':
    main()
