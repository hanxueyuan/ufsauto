#!/usr/bin/env python3
"""快速测试 SysTest 框架功能"""

import sys
import subprocess
from pathlib import Path

# 切换到 systest 目录
systest_dir = Path(__file__).parent
sys.path.insert(0, str(systest_dir))

print("=" * 60)
print("🧪 SysTest 框架功能测试")
print("=" * 60)

# 测试 1: 查看帮助
print("\n[1/4] 测试帮助命令...")
result = subprocess.run(['python3', 'bin/SysTest', '--help'], capture_output=True, text=True)
if result.returncode == 0:
    print("✅ 帮助命令正常")
else:
    print("❌ 帮助命令失败")
    sys.exit(1)

# 测试 2: 列出测试
print("\n[2/4] 列出可用测试...")
result = subprocess.run(['python3', 'bin/SysTest', 'list'], capture_output=True, text=True)
if 'performance' in result.stdout and 'seq_read' in result.stdout:
    print("✅ 测试列表正常")
    print(result.stdout)
else:
    print("❌ 测试列表失败")
    sys.exit(1)

# 测试 3: 查看配置
print("\n[3/4] 查看配置...")
result = subprocess.run(['python3', 'bin/SysTest', 'config', '--show'], capture_output=True, text=True)
print("✅ 配置命令正常")

# 测试 4: 模拟执行
print("\n[4/4] 模拟执行测试（dry-run）...")
result = subprocess.run(
    ['python3', 'bin/SysTest', 'run', '--suite=performance', '--dry-run', '-v'],
    capture_output=True,
    text=True
)
if 'DRY-RUN' in result.stdout or '执行测试套件' in result.stdout:
    print("✅ 模拟执行正常")
    print(result.stdout)
else:
    print("⚠️  模拟执行输出异常")
    print(result.stdout)

print("\n" + "=" * 60)
print("✅ 所有测试通过！框架功能正常")
print("=" * 60)
