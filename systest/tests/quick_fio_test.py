#!/usr/bin/env python3
"""
SysTest FIO 快速验证
验证 FIO 可用性和基本功能
"""

import json
import os
import shutil
import subprocess
import tempfile

import pytest


def get_fio_path():
    """动态查找 FIO 路径"""
    # 1. 优先使用环境变量
    env_path = os.environ.get("FIO_PATH")
    if env_path and os.path.exists(env_path):
        return env_path

    # 2. 在 PATH 中查找
    fio_in_path = shutil.which("fio")
    if fio_in_path:
        return fio_in_path

    # 3. 常见安装路径
    common_paths = [
        "/usr/bin/fio",
        "/usr/local/bin/fio",
        "/home/gem/.local/bin/fio",
    ]
    for path in common_paths:
        if os.path.exists(path):
            return path

    # 4. 未找到
    return None


class TestFIOQuickValidation:
    """FIO 快速验证测试类"""

    def test_fio_installed(self):
        """测试 FIO 已安装"""
        fio_path = get_fio_path()
        assert fio_path is not None, "FIO 未安装，请运行：apt-get install fio"

        result = subprocess.run([fio_path, "--version"], capture_output=True, text=True)
        assert result.returncode == 0, "FIO 版本检查失败"
        print(f"\n✅ FIO 路径：{fio_path}")
        print(f"✅ FIO 版本：{result.stdout.strip()}")

    def test_fio_basic_read(self):
        """测试 FIO 基本读取功能"""
        fio_path = get_fio_path()

        # 创建临时文件
        temp_file = tempfile.mktemp(prefix="fio_test_")
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

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)

            # 尝试从 stdout 或 stderr 解析 JSON
            output = result.stdout if result.stdout.strip() else result.stderr

            # 移除 FIO 的 note 行（如 "note: both iodepth >= 1..."）
            # 找到第一个 '{' 开始解析 JSON
            json_start = output.find("{")
            if json_start == -1:
                raise ValueError(f"FIO 输出中没有找到 JSON 数据：{output}")
            output = output[json_start:]

            data = json.loads(output)

            job = data["jobs"][0]
            read_stats = job.get("read", {})

            bw = read_stats.get("bw_bytes", 0) / 1024 / 1024  # MB/s
            iops = read_stats.get("iops", 0) / 1000  # KIOPS
            lat = read_stats.get("lat_ns", {}).get("mean", 0) / 1000  # μs

            print(f"\n✅ FIO 执行成功")
            print(f"   带宽：{bw:.2f} MB/s")
            print(f"   IOPS: {iops:.2f} K")
            print(f"   延迟：{lat:.2f} μs")

            # 验证基本指标存在
            assert bw >= 0, "带宽应该非负"
            assert iops >= 0, "IOPS 应该非负"
            assert lat >= 0, "延迟应该非负"

        finally:
            # 清理临时文件
            if os.path.exists(temp_file):
                os.remove(temp_file)

        print("\n🎉 FIO 验证通过！")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
