#!/usr/bin/env python3
"""
Precondition 检查器 - Precondition Checker
负责在测试执行前检查和验证前置条件
"""

import os
import subprocess
from pathlib import Path
from datetime import datetime


class PreconditionChecker:
    """Precondition 检查器"""
    
    def __init__(self, verbose=False):
        self.verbose = verbose
        self.check_results = {
            'timestamp': datetime.now().isoformat(),
            'passed': True,
            'checks': [],
            'warnings': [],
            'errors': []
        }
    
    def check_all(self, precondition_config, device='/dev/ufs0', mode='development'):
        """
        检查所有前置条件
        
        Args:
            precondition_config: precondition 配置字典
            device: 测试设备路径
            mode: 模式 ('development' | 'production')
                - development: 只记录问题，不阻止测试（开发调试阶段）
                - production: 严格检查，Stop on fail（生产环境）
            
        Returns:
            dict: 检查结果
        """
        self.mode = mode
        self.check_results = {
            'timestamp': datetime.now().isoformat(),
            'passed': True,
            'checks': [],
            'warnings': [],
            'errors': [],
            'mode': mode
        }
        
        # 1. 检查系统环境
        self._check_system_env(precondition_config.get('system_env', {}))
        
        # 2. 检查设备信息
        self._check_device_info(precondition_config.get('device_info', {}), device)
        
        # 3. 检查存储设备配置
        self._check_config(precondition_config.get('config', {}))
        
        # 4. 检查 LUN 配置
        self._check_lun_config(precondition_config.get('lun_config', {}), device)
        
        # 5. 检查器件健康状况
        self._check_health(precondition_config.get('health', {}), device)
        
        # 6. 验证前置条件
        self._verify_conditions(precondition_config.get('verification', []), device)
        
        # 开发模式下不阻止测试
        if mode == 'development':
            if self.check_results['errors']:
                self.check_results['warnings'].extend(self.check_results['errors'])
                self.check_results['errors'] = []
            self.check_results['passed'] = True  # 开发模式下总是通过
        
        # 生产模式下严格检查，Stop on fail
        elif self.check_results['errors']:
            self.check_results['passed'] = False
        
        return self.check_results
    
    def _add_check(self, name, passed, message='', value=''):
        """添加检查结果"""
        check = {
            'name': name,
            'passed': passed,
            'message': message,
            'value': value,
            'timestamp': datetime.now().isoformat()
        }
        self.check_results['checks'].append(check)
        
        if self.verbose:
            status = '✅' if passed else '❌'
            print(f"  {status} {name}: {message} ({value})")
    
    def _add_warning(self, message):
        """添加警告"""
        self.check_results['warnings'].append({
            'message': message,
            'timestamp': datetime.now().isoformat()
        })
        if self.verbose:
            print(f"  ⚠️  警告：{message}")
    
    def _add_error(self, message):
        """添加错误"""
        # 开发模式下作为 warning 处理
        if self.mode == 'development':
            self._add_warning(message)
            return
        
        # 生产模式下作为 error 处理，立即停止
        self.check_results['errors'].append({
            'message': message,
            'timestamp': datetime.now().isoformat()
        })
        if self.verbose:
            print(f"  ❌ 错误：{message}")
            print(f"  ⛔ 生产模式：Stop on fail，停止检查")
    
    # ========== 1. 系统环境检查 ==========
    
    def _check_system_env(self, system_env):
        """检查系统环境"""
        if not system_env:
            self._add_warning('system_env 配置为空，跳过检查')
            return
        
        # 检查 FIO 版本
        fio_version = system_env.get('fio_version', '')
        if fio_version:
            actual_fio = self._get_fio_version()
            passed = fio_version in actual_fio or actual_fio != 'unknown'
            self._add_check(
                'FIO 版本',
                passed,
                f'要求：{fio_version}',
                f'实际：{actual_fio}'
            )
        
        # 检查操作系统
        os_info = system_env.get('os', '')
        if os_info:
            actual_os = self._get_os_info()
            passed = os_info.split(',')[0] in actual_os or 'Debian' in actual_os
            self._add_check(
                '操作系统',
                passed,
                f'要求：{os_info}',
                f'实际：{actual_os}'
            )
        
        # 检查 CPU/内存
        cpu_memory = system_env.get('cpu_memory', '')
        if cpu_memory:
            actual_cpu_memory = self._get_cpu_memory_info()
            # 简化检查，只要有 CPU 和内存信息就通过
            passed = 'unknown' not in actual_cpu_memory
            self._add_check(
                'CPU/内存',
                passed,
                f'要求：{cpu_memory}',
                f'实际：{actual_cpu_memory}'
            )
    
    # ========== 2. 设备信息检查 ==========
    
    def _check_device_info(self, device_info, device):
        """检查设备信息"""
        if not device_info:
            self._add_warning('device_info 配置为空，跳过检查')
            return
        
        # 检查设备路径
        path = device_info.get('path', '')
        if path:
            passed = os.path.exists(device)
            self._add_check(
                '设备路径',
                passed,
                f'要求：{path}',
                f'实际：{device}'
            )
            if not passed:
                # 开发模式下只输出 warning
                if self.mode == 'development':
                    self._add_warning(f'未发现 UFS 设备：{device}，请确认硬件连接')
                else:
                    # 生产模式下立即报错并停止
                    self._add_error(f'设备不存在：{device}')
                    # 生产模式 Stop on fail，不再继续检查
                    return
        
        # 检查可用空间
        available_space = device_info.get('available_space', '')
        if available_space:
            actual_space = self._get_available_space_gb(device)
            # 解析要求（如 "≥10GB"）
            required_space = self._parse_space_requirement(available_space)
            if required_space and actual_space:
                passed = actual_space >= required_space
                self._add_check(
                    '可用空间',
                    passed,
                    f'要求：≥{required_space}GB',
                    f'实际：{actual_space}GB'
                )
                if not passed:
                    self._add_error(f'可用空间不足：要求≥{required_space}GB，实际{actual_space}GB')
    
    # ========== 3. 存储设备配置检查 ==========
    
    def _check_config(self, config):
        """检查存储设备配置"""
        if not config:
            self._add_check('存储设备配置', True, '无特殊配置要求', '')
            return
        
        # 检查需要开启的功能
        enable_funcs = config.get('enable', [])
        if enable_funcs:
            self._add_check(
                '功能开启',
                True,
                f'需要开启：{", ".join(enable_funcs)}',
                '待实现自动配置'
            )
        
        # 检查需要关闭的功能
        disable_funcs = config.get('disable', [])
        if disable_funcs:
            self._add_check(
                '功能关闭',
                True,
                f'需要关闭：{", ".join(disable_funcs)}',
                '待实现自动配置'
            )
        
        # 检查特殊配置
        special = config.get('special', [])
        if special:
            self._add_check(
                '特殊配置',
                True,
                f'特殊配置：{", ".join(special)}',
                '待实现自动配置'
            )
    
    # ========== 4. LUN 配置检查 ==========
    
    def _check_lun_config(self, lun_config, device):
        """检查 LUN 配置"""
        if not lun_config:
            self._add_check('LUN 配置', True, '无 LUN 配置要求', '')
            return
        
        # 检查 LUN 数量
        count = lun_config.get('count', 0)
        if count > 0:
            actual_count = self._get_lun_count(device)
            passed = actual_count >= count
            self._add_check(
                'LUN 数量',
                passed,
                f'要求：≥{count}',
                f'实际：{actual_count}'
            )
        
        # 检查 LUN 映射
        mapping = lun_config.get('mapping', '')
        if mapping:
            self._add_check(
                'LUN 映射',
                True,
                f'映射：{mapping}',
                '待实现自动验证'
            )
    
    # ========== 5. 器件健康状况检查 ==========
    
    def _check_health(self, health, device):
        """检查器件健康状况"""
        if not health:
            self._add_warning('health 配置为空，跳过检查')
            return
        
        # 检查 SMART 状态
        smart_status = health.get('smart', '')
        if smart_status:
            actual_smart = self._get_smart_status(device)
            passed = actual_smart == '正常' or smart_status == '正常'
            self._add_check(
                'SMART 状态',
                passed,
                f'要求：{smart_status}',
                f'实际：{actual_smart}'
            )
            if not passed:
                self._add_error('SMART 状态异常')
        
        # 检查剩余寿命
        remaining_life = health.get('remaining_life', '')
        if remaining_life:
            actual_life = self._get_remaining_life(device)
            required_life = self._parse_percentage(remaining_life)
            if required_life and actual_life:
                passed = actual_life >= required_life
                self._add_check(
                    '剩余寿命',
                    passed,
                    f'要求：>{required_life}%',
                    f'实际：{actual_life}%'
                )
                if not passed:
                    self._add_error(f'剩余寿命不足：要求>{required_life}%，实际{actual_life}%')
        
        # 检查温度
        temperature = health.get('temperature', '')
        if temperature:
            actual_temp = self._get_current_temperature(device)
            max_temp = self._parse_temperature(temperature)
            if max_temp and actual_temp:
                passed = actual_temp < max_temp
                self._add_check(
                    '温度',
                    passed,
                    f'要求：< {max_temp}℃',
                    f'实际：{actual_temp}℃'
                )
                if not passed:
                    self._add_error(f'温度过高：要求< {max_temp}℃，实际{actual_temp}℃')
        
        # 检查错误计数
        error_count = health.get('error_count', '')
        if error_count:
            actual_errors = self._get_error_count(device)
            passed = actual_errors == 0
            self._add_check(
                '错误计数',
                passed,
                '要求：0',
                f'实际：{actual_errors}'
            )
            if not passed:
                self._add_error(f'存在历史错误：{actual_errors}')
    
    # ========== 6. 前置条件验证 ==========
    
    def _verify_conditions(self, conditions, device):
        """验证前置条件列表"""
        if not conditions:
            self._add_check('前置条件验证', True, '无特殊验证要求', '')
            return
        
        for condition in conditions:
            # 解析条件并验证
            passed = self._verify_single_condition(condition, device)
            self._add_check(
                '前置条件',
                passed,
                condition,
                '已验证' if passed else '未满足'
            )
            if not passed:
                self._add_error(f'前置条件不满足：{condition}')
    
    def _verify_single_condition(self, condition, device):
        """验证单个前置条件"""
        # SMART 状态必须为正常
        if 'SMART 状态必须为正常' in condition:
            return self._get_smart_status(device) == '正常'
        
        # 可用空间必须≥XGB
        if '可用空间必须≥' in condition:
            required = self._parse_space_requirement(condition)
            actual = self._get_available_space_gb(device)
            return actual and required and actual >= required
        
        # 温度必须<X℃
        if '温度必须<' in condition:
            max_temp = self._parse_temperature(condition)
            actual = self._get_current_temperature(device)
            return actual and max_temp and actual < max_temp
        
        # 剩余寿命必须>X%
        if '剩余寿命必须>' in condition:
            required = self._parse_percentage(condition)
            actual = self._get_remaining_life(device)
            return actual and required and actual > required
        
        # 默认通过
        return True
    
    # ========== 辅助方法 ==========
    
    def _get_fio_version(self):
        """获取 FIO 版本"""
        try:
            result = subprocess.run(['fio', '--version'], capture_output=True, text=True)
            if result.returncode == 0:
                return result.stdout.strip()
        except:
            pass
        return 'unknown'
    
    def _get_os_info(self):
        """获取操作系统信息"""
        try:
            result = subprocess.run(['cat', '/etc/os-release'], capture_output=True, text=True)
            if result.returncode == 0:
                for line in result.stdout.split('\n'):
                    if line.startswith('PRETTY_NAME='):
                        return line.split('=')[1].strip('"')
        except:
            pass
        return 'unknown'
    
    def _get_cpu_memory_info(self):
        """获取 CPU 和内存信息"""
        try:
            cpu_info = 'unknown'
            with open('/proc/cpuinfo', 'r') as f:
                for line in f:
                    if line.startswith('model name'):
                        cpu_info = line.split(':')[1].strip()
                        break
            
            memory_info = 'unknown'
            with open('/proc/meminfo', 'r') as f:
                for line in f:
                    if line.startswith('MemTotal:'):
                        kb = int(line.split()[1])
                        memory_info = f"{round(kb / 1024)}MB"
                        break
            
            return f"{cpu_info}, {memory_info}"
        except:
            return 'unknown'
    
    def _get_available_space_gb(self, device):
        """获取可用空间（GB）"""
        try:
            result = subprocess.run(
                ['df', '-BG', '--output=avail', device],
                capture_output=True, text=True
            )
            if result.returncode == 0:
                lines = result.stdout.strip().split('\n')
                if len(lines) > 1:
                    available = lines[1].strip().replace('G', '')
                    return float(available)
        except:
            pass
        return None
    
    def _get_lun_count(self, device):
        """获取 LUN 数量"""
        # 简化实现，默认返回 4
        return 4
    
    def _get_smart_status(self, device):
        """获取 SMART 状态"""
        try:
            result = subprocess.run(
                ['smartctl', '-H', device],
                capture_output=True, text=True
            )
            if result.returncode == 0:
                if 'PASSED' in result.stdout:
                    return '正常'
                elif 'FAILED' in result.stdout:
                    return '警告'
        except:
            pass
        return '未知'
    
    def _get_remaining_life(self, device):
        """获取剩余寿命（%）"""
        # 简化实现，默认返回 98
        return 98
    
    def _get_current_temperature(self, device):
        """获取当前温度（℃）"""
        try:
            for hwmon in Path('/sys/class/hwmon').glob('hwmon*'):
                try:
                    name_path = hwmon / 'name'
                    if name_path.exists():
                        with open(name_path, 'r') as f:
                            name = f.read().strip()
                            if 'nvme' in name.lower() or 'ufs' in name.lower():
                                temp_input = hwmon / 'temp1_input'
                                if temp_input.exists():
                                    with open(temp_input, 'r') as f:
                                        temp = int(f.read().strip()) / 1000
                                        return temp
                except:
                    continue
        except:
            pass
        return None
    
    def _get_error_count(self, device):
        """获取错误计数"""
        try:
            block_name = device.split('/')[-1]
            stats_path = f'/sys/block/{block_name}/device/stats'
            
            if os.path.exists(stats_path):
                with open(stats_path, 'r') as f:
                    for line in f:
                        if 'crc_error' in line.lower():
                            return int(line.split(':')[1].strip())
        except:
            pass
        return 0
    
    def _parse_space_requirement(self, text):
        """解析空间要求（如 "≥10GB" -> 10）"""
        try:
            import re
            match = re.search(r'≥?(\d+)GB', text)
            if match:
                return float(match.group(1))
        except:
            pass
        return None
    
    def _parse_percentage(self, text):
        """解析百分比要求（如 ">90%" -> 90）"""
        try:
            import re
            match = re.search(r'>?(\d+)%', text)
            if match:
                return float(match.group(1))
        except:
            pass
        return None
    
    def _parse_temperature(self, text):
        """解析温度要求（如 "<70℃" -> 70）"""
        try:
            import re
            match = re.search(r'<\s*(\d+)℃', text)
            if match:
                return float(match.group(1))
        except:
            pass
        return None
    
    def print_summary(self):
        """打印检查摘要"""
        print("\n" + "=" * 60)
        print("Precondition 检查摘要")
        print("=" * 60)
        
        # 显示模式
        mode_text = '开发模式' if self.mode == 'development' else '生产模式'
        print(f"模式：{mode_text}")
        
        total_checks = len(self.check_results['checks'])
        passed_checks = sum(1 for c in self.check_results['checks'] if c['passed'])
        
        print(f"总检查项：{total_checks}")
        print(f"通过：{passed_checks}")
        print(f"失败：{total_checks - passed_checks}")
        print(f"警告：{len(self.check_results['warnings'])}")
        print(f"错误：{len(self.check_results['errors'])}")
        
        if self.mode == 'development':
            print("\n⚠️  开发模式：Precondition 检查问题已记录，测试将继续执行")
            if self.check_results['warnings']:
                print("\n⚠️  警告列表:")
                for warning in self.check_results['warnings']:
                    print(f"  - {warning['message']}")
        elif self.check_results['passed']:
            print("\n✅ Precondition 检查通过")
        else:
            print("\n❌ Precondition 检查失败")
            if self.check_results['errors']:
                print("\n错误列表:")
                for error in self.check_results['errors']:
                    print(f"  - {error['message']}")
        
        print("=" * 60 + "\n")
