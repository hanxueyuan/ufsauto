#!/usr/bin/env python3
"""
SysTest FIO 快速验证
验证 FIO 可用性和基本功能
"""

import subprocess
import tempfile
import os
import json

print("🔍 SysTest FIO 快速验证")
print("=" * 60)

# 1. 检查 FIO
fio_path = "/home/gem/.local/bin/fio"
print(f"\n✅ FIO 路径：{fio_path}")

result = subprocess.run([fio_path, "--version"], capture_output=True, text=True)
print(f"✅ FIO 版本：{result.stdout.strip()}")

# 2. 创建临时文件测试
temp_file = tempfile.mktemp(prefix="fio_test_")
print(f"✅ 测试文件：{temp_file}")

try:
    # 创建 1MB 测试文件
    with open(temp_file, "wb") as f:
        f.write(b"\x00" * 1024 * 1024)

    # 执行 FIO 测试
    cmd = [
        fio_path,
        "--name=quick_test",
        f"--filename={temp_file}",
        "--rw=read",
        "--bs=4k",
        "--iodepth=16",
        "--runtime=1",
        "--time_based",
        "--output-format=json",
    ]

    print(f"✅ 执行 FIO 测试...")
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)

    # 尝试从 stdout 或 stderr 解析 JSON
    output = result.stdout if result.stdout.strip() else result.stderr
    data = json.loads(output)

    job = data["jobs"][0]
    read_stats = job.get("read", {})

    bw = read_stats.get("bw_bytes", 0) / 1024 / 1024  # MB/s
    iops = read_stats.get("iops", 0) / 1000  # KIOPS
    lat = read_stats.get("lat_ns", {}).get("mean", 0) / 1000  # μs

    print(f"✅ FIO 执行成功")
    print(f"   带宽：{bw:.2f} MB/s")
    print(f"   IOPS: {iops:.2f} K")
    print(f"   延迟：{lat:.2f} μs")
    print("\n🎉 FIO 验证通过！")

finally:
    # 清理临时文件
    if os.path.exists(temp_file):
        os.remove(temp_file)
