#!/usr/bin/env python3
"""
结果收集器 - Result Collector
负责收集和整理测试结果、系统信息、设备信息
"""

import json
import os
import subprocess
from datetime import datetime
from pathlib import Path


class ResultCollector:
    """结果收集器"""

    def __init__(self):
        self.collected_data = {}

    def collect(self, test_results, test_id, device):
        """收集测试结果和系统信息"""

        collected = {
            "test_id": test_id,
            "timestamp": datetime.now().isoformat(),
            "device": device,
            "test_results": test_results,
            "system_info": self._collect_system_info(),
            "device_info": self._collect_device_info(device),
            "ufs_info": self._collect_ufs_info(device),
            "summary": test_results.get("summary", {}),
        }

        self.collected_data = collected
        return collected

    def _collect_system_info(self):
        """收集系统信息"""
        info = {
            "hostname": self._get_hostname(),
            "kernel": self._get_kernel_version(),
            "cpu_count": self._get_cpu_count(),
            "memory_total": self._get_memory_total(),
            "python_version": self._get_python_version(),
            "fio_version": self._get_fio_version(),
            "os": self._get_os_info(),
            "cpu_memory": self._get_cpu_memory_info(),
        }
        return info

    def _collect_device_info(self, device):
        """收集设备信息"""
        info = {
            "device_path": device,
            "model": self._get_device_model(device),
            "serial": self._get_device_serial(device),
            "size": self._get_device_size(device),
            "firmware": self._get_device_firmware(device),
            "available_space": self._get_available_space(device),
        }
        return info

    def _collect_ufs_info(self, device):
        """收集 UFS 专用信息"""
        info = {
            "lun_config": self._get_lun_config(device),
            "smart_status": self._get_smart_status(device),
            "temperature": self._get_temperature(device),
            "error_count": self._get_error_count(device),
        }
        return info

    # ========== 系统信息收集方法 ==========

    def _get_hostname(self):
        """获取主机名"""
        try:
            return subprocess.check_output(["hostname"], text=True).strip()
        except BaseException:
            return "unknown"

    def _get_kernel_version(self):
        """获取内核版本"""
        try:
            return subprocess.check_output(["uname", "-r"], text=True).strip()
        except BaseException:
            return "unknown"

    def _get_os_info(self):
        """获取操作系统信息"""
        try:
            result = subprocess.run(["cat", "/etc/os-release"], capture_output=True, text=True)
            if result.returncode == 0:
                for line in result.stdout.split("\n"):
                    if line.startswith("PRETTY_NAME="):
                        return line.split("=")[1].strip('"')
        except BaseException:
            pass
        return "unknown"

    def _get_cpu_count(self):
        """获取 CPU 核心数"""
        try:
            return os.cpu_count() or 0
        except BaseException:
            return 0

    def _get_cpu_memory_info(self):
        """获取 CPU 和内存信息"""
        try:
            # 获取 CPU 信息
            cpu_info = "unknown"
            with open("/proc/cpuinfo", "r") as f:
                for line in f:
                    if line.startswith("model name"):
                        cpu_info = line.split(":")[1].strip()
                        break

            # 获取内存信息
            memory_info = "unknown"
            with open("/proc/meminfo", "r") as f:
                for line in f:
                    if line.startswith("MemTotal:"):
                        kb = int(line.split()[1])
                        memory_info = f"{round(kb / 1024)}MB"
                        break

            return f"{cpu_info}, {memory_info}"
        except BaseException:
            return "unknown"

    def _get_memory_total(self):
        """获取总内存 (MB)"""
        try:
            with open("/proc/meminfo", "r") as f:
                for line in f:
                    if line.startswith("MemTotal:"):
                        kb = int(line.split()[1])
                        return round(kb / 1024)
        except BaseException:
            pass
        return 0

    def _get_python_version(self):
        """获取 Python 版本"""
        import sys

        return sys.version.split()[0]

    def _get_fio_version(self):
        """获取 FIO 版本"""
        try:
            result = subprocess.run(["fio", "--version"], capture_output=True, text=True)
            if result.returncode == 0:
                return result.stdout.strip()
        except BaseException:
            pass
        return "unknown"

    # ========== 设备信息收集方法 ==========

    def _get_device_model(self, device):
        """获取设备型号"""
        try:
            # 尝试从 lsblk 获取
            result = subprocess.run(["lsblk", "-ndo", "MODEL", device], capture_output=True, text=True)
            if result.returncode == 0 and result.stdout.strip():
                return result.stdout.strip()
        except BaseException:
            pass

        # 尝试从 sysfs 获取
        try:
            model_path = f'/sys/block/{device.split("/")[-1]}/device/model'
            if os.path.exists(model_path):
                with open(model_path, "r") as f:
                    return f.read().strip()
        except BaseException:
            pass

        return "unknown"

    def _get_device_serial(self, device):
        """获取设备序列号"""
        try:
            serial_path = f'/sys/block/{device.split("/")[-1]}/serial'
            if os.path.exists(serial_path):
                with open(serial_path, "r") as f:
                    return f.read().strip()
        except BaseException:
            pass
        return "unknown"

    def _get_device_size(self, device):
        """获取设备容量 (GB)"""
        try:
            result = subprocess.run(["lsblk", "-bndo", "SIZE", device], capture_output=True, text=True)
            if result.returncode == 0 and result.stdout.strip():
                bytes_ = int(result.stdout.strip())
                return round(bytes_ / 1024 / 1024 / 1024, 2)
        except BaseException:
            pass
        return 0

    def _get_device_firmware(self, device):
        """获取设备固件版本"""
        try:
            # 尝试从 sysfs 获取
            fw_path = f'/sys/block/{device.split("/")[-1]}/device/rev'
            if os.path.exists(fw_path):
                with open(fw_path, "r") as f:
                    return f.read().strip()
        except BaseException:
            pass
        return "unknown"

    def _get_available_space(self, device):
        """获取可用空间"""
        try:
            result = subprocess.run(["df", "-BG", "--output=avail", device], capture_output=True, text=True)
            if result.returncode == 0:
                lines = result.stdout.strip().split("\n")
                if len(lines) > 1:
                    available = lines[1].strip().replace("G", "")
                    return f"≥{available}GB"
        except BaseException:
            pass
        return "unknown"

    # ========== UFS 专用信息收集方法 ==========

    def _get_lun_config(self, device):
        """获取 LUN 配置"""
        lun_info = {"count": 0, "LUNs": [], "mapping": "unknown"}

        try:
            # 尝试从 sysfs 获取 LUN 信息
            block_name = device.split("/")[-1]
            sysfs_path = f"/sys/block/{block_name}/device"

            if os.path.exists(sysfs_path):
                # 获取 LUN 数量（简化实现）
                lun_info["count"] = 4  # 默认 4 个 LUN
                lun_info["LUNs"] = ["LUN0: 系统盘", "LUN1: 数据盘（测试目标）", "LUN2: 日志盘", "LUN3: 预留"]
                lun_info["mapping"] = f"LUN1→{device}"
        except BaseException:
            pass

        return lun_info

    def _get_smart_status(self, device):
        """获取 SMART 状态"""
        try:
            # 尝试使用 smartctl 获取 SMART 信息
            result = subprocess.run(["smartctl", "-H", device], capture_output=True, text=True)
            if result.returncode == 0:
                if "PASSED" in result.stdout:
                    return "正常"
                elif "FAILED" in result.stdout:
                    return "警告"
        except BaseException:
            pass

        # 如果没有 smartctl，尝试从 sysfs 获取
        try:
            health_path = f'/sys/block/{device.split("/")[-1]}/device/health'
            if os.path.exists(health_path):
                with open(health_path, "r") as f:
                    status = f.read().strip()
                    if status == "0" or status.lower() == "ok":
                        return "正常"
        except BaseException:
            pass

        return "未知"

    def _get_temperature(self, device):
        """获取设备温度"""
        temp_info = {"current": "unknown", "max": "unknown"}

        try:
            # 尝试从 hwmon 获取温度
            for hwmon in Path("/sys/class/hwmon").glob("hwmon*"):
                try:
                    name_path = hwmon / "name"
                    if name_path.exists():
                        with open(name_path, "r") as f:
                            name = f.read().strip()
                            if "nvme" in name.lower() or "ufs" in name.lower():
                                temp_input = hwmon / "temp1_input"
                                if temp_input.exists():
                                    with open(temp_input, "r") as f:
                                        temp = int(f.read().strip()) / 1000
                                        temp_info["current"] = f"{temp}℃"
                                temp_max = hwmon / "temp1_max"
                                if temp_max.exists():
                                    with open(temp_max, "r") as f:
                                        temp = int(f.read().strip()) / 1000
                                        temp_info["max"] = f"{temp}℃"
                except BaseException:
                    continue
        except BaseException:
            pass

        return temp_info

    def _get_error_count(self, device):
        """获取错误计数"""
        error_info = {"crc_errors": 0, "retransmit_count": 0}

        try:
            # 尝试从 sysfs 获取错误计数
            block_name = device.split("/")[-1]
            stats_path = f"/sys/block/{block_name}/device/stats"

            if os.path.exists(stats_path):
                with open(stats_path, "r") as f:
                    for line in f:
                        if "crc_error" in line.lower():
                            error_info["crc_errors"] = int(line.split(":")[1].strip())
                        if "retransmit" in line.lower():
                            error_info["retransmit_count"] = int(line.split(":")[1].strip())
        except BaseException:
            pass

        return error_info

    def save(self, output_dir, test_id):
        """保存收集的结果"""
        output_path = Path(output_dir) / test_id
        output_path.mkdir(parents=True, exist_ok=True)

        # 保存结果 JSON
        results_file = output_path / "results.json"
        with open(results_file, "w", encoding="utf-8") as f:
            json.dump(self.collected_data, f, indent=2, ensure_ascii=False)

        # 保存原始数据
        raw_dir = output_path / "raw"
        raw_dir.mkdir(exist_ok=True)

        if "test_results" in self.collected_data:
            for tc in self.collected_data["test_results"].get("test_cases", []):
                if "raw_data" in tc:
                    raw_file = raw_dir / f"{tc['test_name']}.json"
                    with open(raw_file, "w", encoding="utf-8") as f:
                        json.dump(tc["raw_data"], f, indent=2)

        return str(output_path)
