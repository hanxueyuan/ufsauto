#!/usr/bin/env python3
"""
测试公共函数库 - Test Helpers
提供 Precondition/Postcondition 信息收集、FIO 执行与解析等公共函数。

所有测试脚本共享此模块，避免重复代码。
脚本中 import 方式:
    from test_helpers import (
        find_test_dir, collect_system_info, collect_device_info,
        collect_storage_config, collect_ufs_config, collect_health_status,
        run_fio, parse_fio_output, try_fstrim,
    )
"""

import glob
import os
import re
import shutil
import subprocess


# ============================================================
# Precondition 信息收集
# ============================================================

def find_test_dir(min_free_gb=5):
    """
    查找可用空间≥min_free_gb 的目录，创建临时测试目录。

    遍历候选目录列表，找到第一个满足空间要求的目录，
    在其下创建以 PID 命名的临时目录。

    Args:
        min_free_gb: 最小可用空间 (GB)

    Returns:
        str: 临时测试目录路径，未找到返回 None
    """
    candidates = ["/data", "/home", "/opt", "/tmp", "/mapdata"]
    for d in candidates:
        if os.path.isdir(d):
            usage = shutil.disk_usage(d)
            free_gb = usage.free / (1024 ** 3)
            if free_gb >= min_free_gb:
                test_dir = os.path.join(d, f"ufs_test_{os.getpid()}")
                os.makedirs(test_dir, exist_ok=True)
                return test_dir
    return None


def collect_system_info():
    """
    1.1 系统环境收集

    收集内容:
        - 操作系统：读取 /etc/os-release，收集 PRETTY_NAME 字段
        - CPU：读取 /proc/cpuinfo，收集 model name 和 cpu cores
        - 内存：读取 /proc/meminfo，收集 MemTotal
        - FIO 版本：执行 fio --version，收集版本号

    Returns:
        dict: 系统环境信息
    """
    info = {}

    # 操作系统
    try:
        with open("/etc/os-release") as f:
            for line in f:
                if line.startswith("PRETTY_NAME="):
                    info["os"] = line.split("=", 1)[1].strip().strip('"')
                    break
    except Exception:
        info["os"] = "unknown"

    # CPU
    try:
        with open("/proc/cpuinfo") as f:
            content = f.read()
            model_match = re.search(r"model name\s*:\s*(.*)", content)
            info["cpu_model"] = model_match.group(1).strip() if model_match else "unknown"
            info["cpu_cores"] = content.count("processor\t:")
    except Exception:
        info["cpu_model"] = "unknown"
        info["cpu_cores"] = 0

    # 内存
    try:
        with open("/proc/meminfo") as f:
            for line in f:
                if line.startswith("MemTotal:"):
                    mem_kb = int(line.split()[1])
                    info["mem_total_gb"] = round(mem_kb / (1024 * 1024), 1)
                    break
    except Exception:
        info["mem_total_gb"] = 0

    # FIO 版本
    try:
        result = subprocess.run(["fio", "--version"], capture_output=True, text=True, timeout=5)
        info["fio_version"] = result.stdout.strip()
    except Exception:
        info["fio_version"] = "not installed"

    return info


def collect_device_info(device):
    """
    1.2 测试目标信息收集

    收集内容:
        - 设备路径：检查设备是否存在 (os.path.exists)
        - 设备型号：读取 /sys/block/<dev>/device/model
        - 固件版本：读取 /sys/block/<dev>/device/rev
        - 设备容量：执行 lsblk -b -d -o SIZE /dev/<dev>，收集容量信息

    Args:
        device: 设备路径 (如 /dev/ufs0 或 /dev/sda)

    Returns:
        dict: 设备信息
    """
    info = {"device": device, "device_exists": os.path.exists(device)}
    dev_name = os.path.basename(device)
    sysfs_base = f"/sys/block/{dev_name}"

    for field, path_suffix in [("model", "device/model"), ("firmware", "device/rev")]:
        fpath = f"{sysfs_base}/{path_suffix}"
        if os.path.exists(fpath):
            with open(fpath) as f:
                info[field] = f.read().strip()
        else:
            info[field] = "unknown"

    try:
        result = subprocess.run(
            ["lsblk", "-b", "-d", "-o", "SIZE", "-n", device],
            capture_output=True, text=True, timeout=5,
        )
        info["capacity_gb"] = round(int(result.stdout.strip()) / (1024 ** 3), 1)
    except Exception:
        info["capacity_gb"] = 0

    return info


def collect_storage_config(device):
    """
    1.3 存储设备配置检查

    收集内容:
        - Write Booster 状态：检查 sysfs 路径 (wb_enabled)
        - 省电模式状态：检查 device/power/control

    Args:
        device: 设备路径

    Returns:
        dict: 存储配置信息
    """
    config = {}
    dev_name = os.path.basename(device)

    # Write Booster
    wb_paths = glob.glob(f"/sys/block/{dev_name}/device/wb_enabled") + \
               glob.glob("/sys/class/scsi_device/*/device/wb_enabled")
    config["write_booster"] = "unknown"
    for wp in wb_paths:
        if os.path.exists(wp):
            with open(wp) as f:
                config["write_booster"] = f.read().strip()
            break

    # 省电模式
    power_path = f"/sys/block/{dev_name}/device/power/control"
    if os.path.exists(power_path):
        with open(power_path) as f:
            config["power_mode"] = f.read().strip()
    else:
        config["power_mode"] = "unknown"

    return config


def collect_ufs_config(device):
    """
    1.4 UFS 器件配置检查

    收集内容:
        - UFS 版本：读取 sysfs ufs_version 或 device_descriptor
        - LUN 数量：遍历 /sys/class/scsi_device/*/device/lun/ 统计

    Args:
        device: 设备路径

    Returns:
        dict: UFS 器件配置
    """
    config = {}
    dev_name = os.path.basename(device)

    # UFS 版本
    ufs_ver_paths = glob.glob(f"/sys/block/{dev_name}/device/ufs_version") + \
                    glob.glob("/sys/class/scsi_device/*/device/ufs_version")
    config["ufs_version"] = "unknown"
    for vp in ufs_ver_paths:
        if os.path.exists(vp):
            with open(vp) as f:
                config["ufs_version"] = f.read().strip()
            break

    # LUN 数量
    lun_paths = glob.glob("/sys/class/scsi_device/*/device/lun/*")
    config["lun_count"] = len(lun_paths) if lun_paths else 0

    return config


def collect_health_status(device):
    """
    1.5 器件健康状况检查

    收集内容:
        - SMART 状态：执行 smartctl -H，检查 overall-health
        - 温度：读取 /sys/class/hwmon/hwmon*/temp*_input
        - 块设备统计：读取 /sys/block/<dev>/stat
        - UFS 错误计数：解析 dmesg 中 ufshcd 错误

    Args:
        device: 设备路径

    Returns:
        dict: 健康状况信息
    """
    health = {}

    # SMART 状态
    try:
        result = subprocess.run(["smartctl", "-H", device], capture_output=True, text=True, timeout=10)
        health["smart_passed"] = "PASSED" in result.stdout
        health["smart_output"] = result.stdout[:500]
    except Exception:
        health["smart_passed"] = None
        health["smart_output"] = "smartctl not available"

    # 温度
    temp_paths = glob.glob("/sys/class/hwmon/hwmon*/temp*_input")
    health["temperature_c"] = None
    for tp in temp_paths:
        try:
            with open(tp) as f:
                health["temperature_c"] = int(f.read().strip()) / 1000
                break
        except Exception:
            continue

    # 块设备统计
    dev_name = os.path.basename(device)
    stat_path = f"/sys/block/{dev_name}/stat"
    if os.path.exists(stat_path):
        with open(stat_path) as f:
            health["block_stat"] = f.read().strip()
    else:
        health["block_stat"] = "unknown"

    # dmesg 中的 UFS 错误
    try:
        result = subprocess.run(["dmesg"], capture_output=True, text=True, timeout=5)
        ufs_errors = [
            l for l in result.stdout.splitlines()
            if "ufshcd" in l.lower() and "error" in l.lower()
        ]
        health["ufs_error_count"] = len(ufs_errors)
    except Exception:
        health["ufs_error_count"] = -1

    return health


# ============================================================
# FIO 执行与解析
# ============================================================

def run_fio(test_dir, fio_params, job_name="fio_test"):
    """
    执行 FIO 测试

    Args:
        test_dir: 测试文件目录
        fio_params: FIO 参数字典，必须包含 rw, bs, iodepth, numjobs, runtime
        job_name: FIO job 名称

    Returns:
        tuple: (success, stdout, stderr)
    """
    test_file = os.path.join(test_dir, "fio_test_file")
    cmd = [
        "fio",
        f"--name={job_name}",
        f"--filename={test_file}",
        f"--rw={fio_params['rw']}",
        f"--bs={fio_params['bs']}",
        f"--iodepth={fio_params['iodepth']}",
        f"--numjobs={fio_params['numjobs']}",
        f"--runtime={fio_params['runtime']}",
        f"--size={fio_params.get('size', '4G')}",
        "--time_based",
        "--direct=1",
        "--output-format=normal",
    ]

    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True,
            timeout=fio_params["runtime"] + 120,
        )
        return result.returncode == 0, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return False, "", "FIO 执行超时"
    except Exception as e:
        return False, "", str(e)


def parse_fio_output(output, rw_type="READ"):
    """
    解析 FIO 输出，提取带宽、IOPS、延迟

    Args:
        output: FIO stdout 输出
        rw_type: 解析目标 "READ" 或 "WRITE"

    Returns:
        dict: {"bandwidth_mbs": float, "iops": int, "latency_avg_us": float}
    """
    result = {"bandwidth_mbs": 0.0, "iops": 0, "latency_avg_us": 0.0}

    # 解析带宽
    bw_match = re.search(rf"{rw_type}:.*bw=(\d+(?:\.\d+)?)\s*(KiB|MiB|GiB)/s", output)
    if bw_match:
        bw_val = float(bw_match.group(1))
        bw_unit = bw_match.group(2)
        if bw_unit == "KiB":
            result["bandwidth_mbs"] = round(bw_val / 1024, 2)
        elif bw_unit == "MiB":
            result["bandwidth_mbs"] = round(bw_val, 2)
        elif bw_unit == "GiB":
            result["bandwidth_mbs"] = round(bw_val * 1024, 2)

    # 解析 IOPS
    iops_match = re.search(r"IOPS=(\d+(?:\.\d+)?)(k)?", output)
    if iops_match:
        iops_val = float(iops_match.group(1))
        if iops_match.group(2) == "k":
            iops_val *= 1000
        result["iops"] = int(iops_val)

    # 解析平均延迟
    lat_match = re.search(r"lat\s*\(usec\).*avg=\s*(\d+(?:\.\d+)?)", output)
    if lat_match:
        result["latency_avg_us"] = float(lat_match.group(1))
    else:
        lat_match = re.search(r"lat\s*\(msec\).*avg=\s*(\d+(?:\.\d+)?)", output)
        if lat_match:
            result["latency_avg_us"] = float(lat_match.group(1)) * 1000

    return result


# ============================================================
# Postcondition 工具
# ============================================================

def try_fstrim(path):
    """
    尝试执行 fstrim 清理未使用块

    Args:
        path: 任意路径，自动查找其挂载点

    Returns:
        bool: 是否执行成功
    """
    try:
        mount_point = path
        while mount_point != "/" and not os.path.ismount(mount_point):
            mount_point = os.path.dirname(mount_point)
        subprocess.run(["fstrim", mount_point], capture_output=True, timeout=30)
        return True
    except Exception:
        return False


def compare_health(before, after):
    """
    对比测试前后健康状况

    Args:
        before: 测试前 collect_health_status() 结果
        after: 测试后 collect_health_status() 结果

    Returns:
        dict: 变化情况 {"error_increase": int, "temp_rise": float}
    """
    changes = {}

    # 错误计数变化
    if before.get("ufs_error_count", -1) >= 0 and after.get("ufs_error_count", -1) >= 0:
        changes["error_increase"] = after["ufs_error_count"] - before["ufs_error_count"]
    else:
        changes["error_increase"] = 0

    # 温度变化
    if before.get("temperature_c") and after.get("temperature_c"):
        changes["temp_rise"] = round(after["temperature_c"] - before["temperature_c"], 1)
    else:
        changes["temp_rise"] = None

    return changes
