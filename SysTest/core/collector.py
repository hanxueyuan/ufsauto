#!/usr/bin/env python3
"""
结果收集器 - Result Collector
负责收集和整理测试结果
"""

import os
import json
import subprocess
from pathlib import Path
from datetime import datetime


class ResultCollector:
    """结果收集器"""
    
    def __init__(self):
        self.collected_data = {}
    
    def collect(self, test_results, test_id, device):
        """收集测试结果和系统信息"""
        
        collected = {
            'test_id': test_id,
            'timestamp': datetime.now().isoformat(),
            'device': device,
            'test_results': test_results,
            'system_info': self._collect_system_info(),
            'device_info': self._collect_device_info(device),
            'summary': test_results.get('summary', {})
        }
        
        self.collected_data = collected
        return collected
    
    def _collect_system_info(self):
        """收集系统信息"""
        info = {
            'hostname': self._get_hostname(),
            'kernel': self._get_kernel_version(),
            'cpu_count': self._get_cpu_count(),
            'memory_total': self._get_memory_total(),
            'python_version': self._get_python_version(),
        }
        return info
    
    def _collect_device_info(self, device):
        """收集设备信息"""
        info = {
            'device_path': device,
            'model': self._get_device_model(device),
            'serial': self._get_device_serial(device),
            'size': self._get_device_size(device),
            'firmware': '',  # 需要特定工具
        }
        return info
    
    def _get_hostname(self):
        """获取主机名"""
        try:
            return subprocess.check_output(['hostname'], text=True).strip()
        except:
            return 'unknown'
    
    def _get_kernel_version(self):
        """获取内核版本"""
        try:
            return subprocess.check_output(['uname', '-r'], text=True).strip()
        except:
            return 'unknown'
    
    def _get_cpu_count(self):
        """获取 CPU 核心数"""
        try:
            return os.cpu_count() or 0
        except:
            return 0
    
    def _get_memory_total(self):
        """获取总内存 (MB)"""
        try:
            with open('/proc/meminfo', 'r') as f:
                for line in f:
                    if line.startswith('MemTotal:'):
                        kb = int(line.split()[1])
                        return round(kb / 1024)
        except:
            pass
        return 0
    
    def _get_python_version(self):
        """获取 Python 版本"""
        import sys
        return sys.version.split()[0]
    
    def _get_device_model(self, device):
        """获取设备型号"""
        try:
            # 尝试从 lsblk 获取
            result = subprocess.run(
                ['lsblk', '-ndo', 'MODEL', device],
                capture_output=True, text=True
            )
            if result.returncode == 0 and result.stdout.strip():
                return result.stdout.strip()
        except:
            pass
        
        # 尝试从 sysfs 获取
        try:
            model_path = f'/sys/block/{device.split("/")[-1]}/device/model'
            if os.path.exists(model_path):
                with open(model_path, 'r') as f:
                    return f.read().strip()
        except:
            pass
        
        return 'unknown'
    
    def _get_device_serial(self, device):
        """获取设备序列号"""
        try:
            serial_path = f'/sys/block/{device.split("/")[-1]}/serial'
            if os.path.exists(serial_path):
                with open(serial_path, 'r') as f:
                    return f.read().strip()
        except:
            pass
        return 'unknown'
    
    def _get_device_size(self, device):
        """获取设备容量 (GB)"""
        try:
            result = subprocess.run(
                ['lsblk', '-bndo', 'SIZE', device],
                capture_output=True, text=True
            )
            if result.returncode == 0 and result.stdout.strip():
                bytes_ = int(result.stdout.strip())
                return round(bytes_ / 1024 / 1024 / 1024, 2)
        except:
            pass
        return 0
    
    def save(self, output_dir, test_id):
        """保存收集的结果"""
        output_path = Path(output_dir) / test_id
        output_path.mkdir(parents=True, exist_ok=True)
        
        # 保存结果 JSON
        results_file = output_path / 'results.json'
        with open(results_file, 'w', encoding='utf-8') as f:
            json.dump(self.collected_data, f, indent=2, ensure_ascii=False)
        
        # 保存原始数据
        raw_dir = output_path / 'raw'
        raw_dir.mkdir(exist_ok=True)
        
        if 'test_results' in self.collected_data:
            for tc in self.collected_data['test_results'].get('test_cases', []):
                if 'raw_data' in tc:
                    raw_file = raw_dir / f"{tc['test_name']}.json"
                    with open(raw_file, 'w', encoding='utf-8') as f:
                        json.dump(tc['raw_data'], f, indent=2)
        
        return str(output_path)
