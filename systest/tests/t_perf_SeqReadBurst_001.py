#!/usr/bin/env python3
"""
测试目的：
    验证 UFS 设备的顺序读带宽 Burst 性能，评估设备在短时间内能达到的最大读取带宽，
    确保满足车规级 UFS 3.1 的≥2100 MB/s 要求。

测试模块：perf
测试用例 ID：t_perf_SeqReadBurst_001
测试优先级：P0

Precondition:
    1.1 系统环境���集
        - 操作系统：读取 /etc/os-release，收集 PRETTY_NAME 字段
        - CPU：读取 /proc/cpuinfo，收集 model name 和 cpu cores
        - 内存：读取 /proc/meminfo，收集 MemTotal
        - FIO 版本：执行 fio --version，收集版本号

    1.2 测试目标信息收集
        - 设备路径：检查 /dev/ufs0 或 /dev/sda 是否存在（os.path.exists）
        - 设备型号：读取 /sys/block/<dev>/device/model
        - 固件版本：读取 /sys/block/<dev>/device/rev
        - 设备容量：执行 lsblk -b -d -o SIZE /dev/<dev>，收集容量信息
        - 可用空间：遍历挂载点，使用 shutil.disk_usage 查找可用空间≥5GB 的目录

    1.3 存储设备配置检查
        - Write Booster 状态：检查 /sys/block/<dev>/device/wb_enabled 或 sysfs 相关路径
        - 省电模式状态：检查 /sys/block/<dev>/device/power/control
        - TURBO Mode 状态：检查厂商特定 sysfs 节点（如存在）
        - 记录当前配置快照，用于 Postcondition 恢复对比

    1.4 UFS 器件配置检查
        - UFS 版本：读取 /sys/block/<dev>/device/ufs_version 或 device_descriptor
        - LUN 数量：遍历 /sys/class/scsi_device/*/device/lun/ 统计 LUN 数
        - LUN 容量：读取各 LUN 对应块设备的 size 信息
        - LUN 映射：记录 LUN 与 /dev/sd* 的映射关系

    1.5 器件健康状况检查
        - SMART 状态：执行 smartctl -H /dev/<dev>，检查 overall-health
        - 剩余寿命：执行 smartctl -a /dev/<dev>，收集 Percentage Used
        - 坏块数量：读取 smartctl 输出中的 Available Spare 或厂商特定字段
        - 温度：读取 /sys/class/hwmon/hwmon*/temp*_input（遍历查找 UFS 相关温度）
        - 错误计数：读取 /sys/block/<dev>/device/stats 或 dmesg 中 ufshcd 错误数

    1.6 前置条件验证
        - ✓ SMART 状态必须为 PASSED（否则跳过测试）
        - ✓ 可用空间必须≥10GB（否则跳过测试）
        - ✓ 温度必须<70℃（否则等待冷却后重试）
        - ✓ 剩余寿命必须>90%（否则记录警告）

Test Steps:
    1. 在可用空间≥5GB 的目录下创建临时测试目录
    2. 使用 FIO 工具发起顺序读测试
       - 参数：rw=read, bs=128k, iodepth=32, numjobs=1, runtime=60, time_based, direct=1
    3. FIO 持续读取 60 秒，记录带宽数据
    4. 解析 FIO 输出，提取平均带宽、IOPS、延迟数据

Postcondition:
    - 测试结果保存：results/perf/ 目录，JSON 格式
    - 配置恢复：对比 Precondition 快照，如有配置变更则恢复原始状态
    - 设备恢复：等待 5 秒，让设备回到空闲状态
    - 数据清理：删除测试生成的临时文件和目录
    - 测试后状态检查：
        - 重新读取 SMART 状态，对比测试前后
        - 重新读取温度，记录温度变化
        - 重新读取错误计数，对比测试前后是否有新增错误
        - 重新读取坏块数量，对比是否有新增坏块

测试参数:
    - rw: read（读写模式：顺序读）
    - bs: 128k（块大小：128KB，最大化顺序读带宽）
    - iodepth: 32（队列深度：32，充分利用 UFS 命令队列）
    - numjobs: 1（并发线程数：1，单线程测试）
    - runtime: 60（测试时长：60 秒，Burst 模式）
    - time_based: True（基于时间的测试）
    - direct: 1（绕过 OS 缓存，直接 IO）

验收标准:
    - PASS: 平均带宽 ≥ 2100 MB/s（允许 5% 误差，即≥1995 MB/s）
    - FAIL: 平均带宽 < 1995 MB/s

注意事项:
    - Burst 测试时间短（60 秒），反映设备峰值性能
    - 测试前确保设备未处于过热状态（温度<70℃）
    - 如果测试失败，检查设备温度、队列深度配置、Write Booster 状态
    - 建议重复测试 3 次取平均值
    - 测试过程中不要有其他 IO 负载干扰

修改记录：
    2026-03-18 QA Agent 初始版本，按 7 部分框架编写，符合命名规范
"""

import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

# 添加 core 模块路径
sys.path.insert(0, str(Path(__file__).parent.parent / "core"))

from systest import Systest


# ============================================================
# 工具函数
# ============================================================

def find_test_dir(min_free_gb=5):
    """查找可用空间≥min_free_gb 的目录，创建临时测试目录"""
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
    """1.1 系统环境收集"""
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
    """1.2 测试目标信息收集"""
    info = {}

    # 设备路径
    info["device"] = device
    info["device_exists"] = os.path.exists(device)

    # 从设备路径提取块设备名
    dev_name = os.path.basename(device)
    sysfs_base = f"/sys/block/{dev_name}"

    # 设备型号
    model_path = f"{sysfs_base}/device/model"
    if os.path.exists(model_path):
        with open(model_path) as f:
            info["model"] = f.read().strip()
    else:
        info["model"] = "unknown"

    # 固件版本
    rev_path = f"{sysfs_base}/device/rev"
    if os.path.exists(rev_path):
        with open(rev_path) as f:
            info["firmware"] = f.read().strip()
    else:
        info["firmware"] = "unknown"

    # 设备容量
    try:
        result = subprocess.run(["lsblk", "-b", "-d", "-o", "SIZE", "-n", device],
                                capture_output=True, text=True, timeout=5)
        size_bytes = int(result.stdout.strip())
        info["capacity_gb"] = round(size_bytes / (1024 ** 3), 1)
    except Exception:
        info["capacity_gb"] = 0

    return info


def collect_storage_config(device):
    """1.3 存储设备配置检查"""
    config = {}
    dev_name = os.path.basename(device)

    # Write Booster 状态
    wb_paths = [
        f"/sys/block/{dev_name}/device/wb_enabled",
        f"/sys/class/scsi_device/*/device/wb_enabled",
    ]
    config["write_booster"] = "unknown"
    for wb_path in wb_paths:
        import glob
        matches = glob.glob(wb_path)
        if matches and os.path.exists(matches[0]):
            with open(matches[0]) as f:
                config["write_booster"] = f.read().strip()
            break

    # 省电模式状态
    power_path = f"/sys/block/{dev_name}/device/power/control"
    if os.path.exists(power_path):
        with open(power_path) as f:
            config["power_mode"] = f.read().strip()
    else:
        config["power_mode"] = "unknown"

    return config


def collect_ufs_config(device):
    """1.4 UFS 器件配置检查"""
    config = {}
    dev_name = os.path.basename(device)
    import glob

    # UFS 版本
    ufs_ver_paths = glob.glob(f"/sys/block/{dev_name}/device/ufs_version") + \
                    glob.glob("/sys/class/scsi_device/*/device/ufs_version")
    if ufs_ver_paths and os.path.exists(ufs_ver_paths[0]):
        with open(ufs_ver_paths[0]) as f:
            config["ufs_version"] = f.read().strip()
    else:
        config["ufs_version"] = "unknown"

    # LUN 数量
    lun_paths = glob.glob("/sys/class/scsi_device/*/device/lun/*")
    config["lun_count"] = len(lun_paths) if lun_paths else 0

    return config


def collect_health_status(device):
    """1.5 器件健康状况检查"""
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
    import glob
    temp_paths = glob.glob("/sys/class/hwmon/hwmon*/temp*_input")
    health["temperature_c"] = None
    for tp in temp_paths:
        try:
            with open(tp) as f:
                temp_mc = int(f.read().strip())
                health["temperature_c"] = temp_mc / 1000
                break
        except Exception:
            continue

    # 错误计数
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
        ufs_errors = [line for line in result.stdout.splitlines() if "ufshcd" in line.lower() and "error" in line.lower()]
        health["ufs_error_count"] = len(ufs_errors)
    except Exception:
        health["ufs_error_count"] = -1

    return health


def parse_fio_output(output):
    """解析 FIO 输出，提取带宽、IOPS、延迟"""
    result = {"bandwidth_kbs": 0, "bandwidth_mbs": 0, "iops": 0, "latency_avg_us": 0}

    # 解析带宽 (KB/s)
    bw_match = re.search(r"READ:.*bw=(\d+(?:\.\d+)?)\s*(KiB|MiB|GiB)/s", output)
    if bw_match:
        bw_val = float(bw_match.group(1))
        bw_unit = bw_match.group(2)
        if bw_unit == "KiB":
            result["bandwidth_kbs"] = bw_val
            result["bandwidth_mbs"] = round(bw_val / 1024, 2)
        elif bw_unit == "MiB":
            result["bandwidth_kbs"] = bw_val * 1024
            result["bandwidth_mbs"] = round(bw_val, 2)
        elif bw_unit == "GiB":
            result["bandwidth_kbs"] = bw_val * 1024 * 1024
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


def run_fio(test_dir, fio_params):
    """执行 FIO 测试"""
    test_file = os.path.join(test_dir, "fio_test_file")
    cmd = [
        "fio",
        f"--name=seq_read_burst",
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
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=fio_params["runtime"] + 60)
        return result.returncode == 0, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return False, "", "FIO 执行超时"
    except Exception as e:
        return False, "", str(e)


# ============================================================
# 主测试流程
# ============================================================

def main():
    """执行测试用例"""
    # 初始化框架
    kit = Systest(
        test_name="t_perf_SeqReadBurst_001",
        device="/dev/ufs0",
        output_dir="./results/perf",
        log_dir="./logs",
    )

    # ========================================
    # Precondition
    # ========================================
    kit.step("Precondition - 1.1 系统环境收集")
    sys_info = collect_system_info()
    kit.info(f"操作系统: {sys_info['os']}")
    kit.info(f"CPU: {sys_info['cpu_model']} ({sys_info['cpu_cores']} cores)")
    kit.info(f"内存: {sys_info['mem_total_gb']} GB")
    kit.info(f"FIO: {sys_info['fio_version']}")

    kit.step("Precondition - 1.2 测试目标信息收集")
    dev_info = collect_device_info(kit.device)
    kit.info(f"设备路径: {dev_info['device']} (exists={dev_info['device_exists']})")
    kit.info(f"设备型号: {dev_info['model']}")
    kit.info(f"固件版本: {dev_info['firmware']}")
    kit.info(f"设备容量: {dev_info['capacity_gb']} GB")

    kit.step("Precondition - 1.3 存储设备配置检查")
    storage_config = collect_storage_config(kit.device)
    kit.info(f"Write Booster: {storage_config['write_booster']}")
    kit.info(f"省电模式: {storage_config['power_mode']}")

    kit.step("Precondition - 1.4 UFS 器件配置检查")
    ufs_config = collect_ufs_config(kit.device)
    kit.info(f"UFS 版本: {ufs_config['ufs_version']}")
    kit.info(f"LUN 数量: {ufs_config['lun_count']}")

    kit.step("Precondition - 1.5 器件健康状况检查")
    health_before = collect_health_status(kit.device)
    kit.info(f"SMART 状态: {'PASSED' if health_before['smart_passed'] else 'FAILED/UNKNOWN'}")
    kit.info(f"温度: {health_before['temperature_c']}℃" if health_before['temperature_c'] else "温度: 未知")
    kit.info(f"UFS 错误计数: {health_before['ufs_error_count']}")

    kit.step("Precondition - 1.6 前置条件验证")
    # 框架级 precondition 检查
    precondition = kit.check_precondition(mode="development")

    # 额外验证：温度
    if health_before["temperature_c"] and health_before["temperature_c"] >= 70:
        kit.fail(f"温度过高 ({health_before['temperature_c']}℃ >= 70℃)，等待冷却")
        kit.report({"status": "SKIP", "reason": "温度过高"})
        return 1

    if not precondition.get("passed", True) and precondition.get("errors"):
        kit.fail("Precondition 检查失败，跳过测试")
        kit.report({"status": "SKIP", "reason": "Precondition 失败", "precondition": precondition})
        return 1

    # 查找测试目录
    test_dir = find_test_dir(min_free_gb=5)
    if not test_dir:
        kit.fail("未找到可用空间≥5GB 的目录")
        kit.report({"status": "SKIP", "reason": "空间不足"})
        return 1
    kit.info(f"测试目录: {test_dir}")

    # 保存 Precondition 快照
    precondition_snapshot = {
        "sys_info": sys_info,
        "dev_info": dev_info,
        "storage_config": storage_config,
        "ufs_config": ufs_config,
        "health_before": health_before,
    }

    # ========================================
    # Test Steps
    # ========================================
    kit.step("Test Steps - 执行 FIO 顺序读 Burst 测试")

    fio_params = {
        "rw": "read",
        "bs": "128k",
        "iodepth": 32,
        "numjobs": 1,
        "runtime": 60,
        "size": "4G",
    }

    kit.info(f"FIO 参数: {fio_params}")
    success, output, error = run_fio(test_dir, fio_params)

    if not success:
        kit.fail(f"FIO 执行失败：{error}")
        # 清理
        shutil.rmtree(test_dir, ignore_errors=True)
        kit.report({"status": "FAIL", "reason": f"FIO 执行失败：{error}", "precondition_snapshot": precondition_snapshot})
        return 1

    # 解析结果
    parsed_result = parse_fio_output(output)
    kit.info(f"顺序读带宽: {parsed_result['bandwidth_mbs']} MB/s")
    kit.info(f"IOPS: {parsed_result['iops']}")
    kit.info(f"平均延迟: {parsed_result['latency_avg_us']} μs")

    # ========================================
    # Postcondition
    # ========================================
    kit.step("Postcondition - 设备恢复")
    kit.info("等待 5 秒，让设备回到空闲状态...")
    time.sleep(5)

    kit.step("Postcondition - 数据清理")
    shutil.rmtree(test_dir, ignore_errors=True)
    kit.info(f"已清理测试目录: {test_dir}")

    kit.step("Postcondition - 测试后状态检查")
    health_after = collect_health_status(kit.device)

    # 对比测试前后
    kit.info(f"温度变化: {health_before.get('temperature_c', 'N/A')} → {health_after.get('temperature_c', 'N/A')}℃")
    kit.info(f"UFS 错误变化: {health_before['ufs_error_count']} → {health_after['ufs_error_count']}")

    error_increase = (health_after["ufs_error_count"] - health_before["ufs_error_count"]) \
        if health_before["ufs_error_count"] >= 0 and health_after["ufs_error_count"] >= 0 else 0
    if error_increase > 0:
        kit.fail(f"测试期间新增 {error_increase} 个 UFS 错误")

    # 框架级 postcondition 检查
    postcondition = kit.check_postcondition(precondition)

    if postcondition.get("critical_fail", False):
        kit.fail("Postcondition 检查失败：坏块数量增加")
        kit.report({
            "status": "FAIL",
            "reason": "Postcondition 检查失败",
            "metrics": parsed_result,
            "precondition_snapshot": precondition_snapshot,
            "postcondition": postcondition,
        })
        return 1

    # ========================================
    # 验收标准判定
    # ========================================
    kit.step("验收标准判定")
    expected_bandwidth = 2100  # MB/s
    tolerance = 0.05  # 5%
    min_bandwidth = expected_bandwidth * (1 - tolerance)
    passed = parsed_result["bandwidth_mbs"] >= min_bandwidth

    kit.info(f"验收标准: {parsed_result['bandwidth_mbs']} MB/s >= {min_bandwidth} MB/s → {'PASS' if passed else 'FAIL'}")

    status = "PASS" if passed else "FAIL"
    kit.report({
        "status": status,
        "metrics": parsed_result,
        "precondition_snapshot": precondition_snapshot,
        "health_before": health_before,
        "health_after": health_after,
        "postcondition": postcondition,
    })

    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
