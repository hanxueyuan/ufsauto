#!/usr/bin/env python3
"""
批量添加 Precondition 注释到测试用例
"""

import re
from pathlib import Path

# 标准 Precondition 模板
PRECONDITION_TEMPLATES = {
    'default': """Precondition:
1.1 系统环境收集
    - 操作系统：Debian 12, kernel 5.15.120
    - CPU/内存：8 核，16GB
    - FIO 版本：fio-3.33

1.2 测试目标信息收集
    - 设备路径：/dev/ufs0
    - 设备型号：UFS 3.1 128GB
    - 固件版本：v1.0.0
    - 设备容量：128GB
    - 可用空间：≥10GB

1.3 存储设备配置检查
    - 开启功能：TURBO Mode（提升峰值性能）
    - 关闭功能：省电模式（避免性能限制）
    - 特殊配置：无

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
    - ✓ 可用空间必须≥10GB
    - ✓ 温度必须<70℃
    - ✓ 剩余寿命必须>90%""",
    
    'sustained_write': """Precondition:
1.1 系统环境收集
    - 操作系统：Debian 12, kernel 5.15.120
    - CPU/内存：8 核，16GB
    - FIO 版本：fio-3.33

1.2 测试目标信息收集
    - 设备路径：/dev/ufs0
    - 设备型号：UFS 3.1 128GB
    - 固件版本：v1.0.0
    - 设备容量：128GB
    - 可用空间：≥20GB（长时间测试需要更多空间）

1.3 存储设备配置检查
    - 开启功能：无特殊开启
    - 关闭功能：省电模式（避免性能限制）
    - 特殊配置：无

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
    - ✓ 可用空间必须≥20GB
    - ✓ 温度必须<70℃
    - ✓ 剩余寿命必须>90%""",
    
    'reliability': """Precondition:
1.1 系统环境收集
    - 操作系统：Debian 12, kernel 5.15.120
    - CPU/内存：8 核，16GB
    - FIO 版本：fio-3.33

1.2 测试目标信息收集
    - 设备路径：/dev/ufs0
    - 设备型号：UFS 3.1 128GB
    - 固件版本：v1.0.0
    - 设备容量：128GB
    - 可用空间：≥20GB（长时间测试需要更多空间）

1.3 存储设备配置检查
    - 开启功能：无特殊开启
    - 关闭功能：自动休眠（避免影响长时间测试）
    - 特殊配置：IO 调度器设置为 none（减少调度延迟）

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
    - ✓ 可用空间必须≥20GB
    - ✓ 温度必须<70℃
    - ✓ 电源必须稳定（建议使用 UPS）
    - ✓ 散热条件良好（建议加散热片或风扇）""",
    
    'scenario': """Precondition:
1.1 系统环境收集
    - 操作系统：Debian 12, kernel 5.15.120
    - CPU/内存：8 核，16GB
    - FIO 版本：fio-3.33

1.2 测试目标信息收集
    - 设备路径：/dev/ufs0
    - 设备型号：UFS 3.1 128GB
    - 固件版本：v1.0.0
    - 设备容量：128GB
    - 可用空间：≥5GB

1.3 存储设备配置检查
    - 开启功能：无特殊开启
    - 关闭功能：省电模式（避免性能限制）
    - 特殊配置：无

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
    - ✓ 可用空间必须≥5GB
    - ✓ 温度必须<70℃
    - ✓ 剩余寿命必须>90%"""
}

# 文件到模板的映射
FILE_TEMPLATE_MAP = {
    't_performance_SequentialWriteBurst_003.py': 'default',
    't_performance_SequentialWriteSustained_004.py': 'sustained_write',
    't_performance_RandomReadBurst_005.py': 'default',
    't_performance_RandomReadSustained_006.py': 'default',
    't_performance_RandomWriteBurst_007.py': 'default',
    't_performance_RandomWriteSustained_008.py': 'sustained_write',
    't_performance_MixedRw_009.py': 'default',
    't_qos_LatencyPercentile_001.py': 'default',
    't_qos_LatencyJitter_002.py': 'default',
    't_scenario_SensorWrite_001.py': 'scenario',
    't_scenario_ModelLoad_002.py': 'default',
}

def add_precondition(filepath, template_name):
    """添加 Precondition 到文件"""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    precondition = PRECONDITION_TEMPLATES[template_name]
    
    # 查找测试目的后的位置
    pattern = r'(测试目的:.*?)(Test Steps:|测试流程：)'
    
    def replacement(match):
        return match.group(1) + '\n\n' + precondition + '\n\n' + match.group(2)
    
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
    
    for filename, template_name in FILE_TEMPLATE_MAP.items():
        filepath = tests_dir / filename
        if filepath.exists():
            print(f"修复 {filename}...")
            if add_precondition(filepath, template_name):
                fixed_count += 1
                print(f"  ✅ 已添加 Precondition")
            else:
                print(f"  ⚠️  无需修复或修复失败")
        else:
            print(f"  ❌ 文件不存在：{filename}")
    
    print(f"\n修复完成！共修复 {fixed_count}/{len(FILE_TEMPLATE_MAP)} 个文件")

if __name__ == '__main__':
    main()
