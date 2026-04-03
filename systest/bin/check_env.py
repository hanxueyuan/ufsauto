#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
环境信息收集脚本 - 纯信息输出，不做 pass/fail 判断

使用方法:
    python3 bin/SysTest check-env
    python3 bin/SysTest check-env -v
    python3 bin/SysTest check-env --mode deploy
    python3 bin/SysTest check-env --report
"""

import sys
import os
import json
import subprocess
import platform
import glob
from pathlib import Path
from datetime import datetime


class EnvironmentChecker:
    """环境信息收集器 — 只报事实，不做判断"""

    def __init__(self, mode='dev', verbose=False, config_dir=None):
        self.mode = mode
        self.verbose = verbose
        self.items = []
        # config 目录在 systest/config/（bin/../config/），而不是 bin/config/
        if config_dir:
            self.config_dir = Path(config_dir)
        else:
            self.config_dir = Path(__file__).parent.parent / 'config'
        # 收集到的关键配置（用于写入 runtime.json）
        self.runtime_config = {
            'device': None,
            'test_dir': None,
            'device_capacity_gb': None,
            'env_checked_at': None,
            'system': {},
            'toolchain': {},
        }

    # ── 内部工具 ──────────────────────────────────────────

    def _record(self, category, name, value):
        self.items.append({'category': category, 'name': name, 'value': value})

    @staticmethod
    def _run(cmd, timeout=10):
        try:
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
            return r.returncode, r.stdout.strip(), r.stderr.strip()
        except FileNotFoundError:
            return -1, '', 'not found'
        except Exception as e:
            return -2, '', str(e)

    # ── 信息采集 ──────────────────────────────────────────

    def collect_system(self):
        # 操作系统
        os_pretty = 'Unknown'
        try:
            with open('/etc/os-release') as f:
                for line in f:
                    if line.startswith('PRETTY_NAME='):
                        os_pretty = line.split('=', 1)[1].strip().strip('"')
                        break
        except Exception:
            pass
        self._record('system', '操作系统', os_pretty)

        self._record('system', '内核版本', platform.release())
        self._record('system', 'CPU 架构', platform.machine())
        self._record('system', 'CPU 核心数', str(os.cpu_count() or '?'))

        # 内存
        mem_str = '?'
        try:
            with open('/proc/meminfo') as f:
                for line in f:
                    if line.startswith('MemTotal:'):
                        kb = int(line.split()[1])
                        mem_str = f'{kb / 1048576:.1f} GB'
                        break
        except Exception:
            pass
        self._record('system', '内存', mem_str)

    def collect_toolchain(self):
        vi = sys.version_info
        self._record('toolchain', 'Python', f'{vi.major}.{vi.minor}.{vi.micro}')

        # FIO
        rc, out, _ = self._run(['fio', '--version'])
        fio_ver = out.replace('fio-', '') if rc == 0 else ('未安装' if rc == -1 else '检查失败')
        self._record('toolchain', 'FIO', fio_ver)

    def collect_storage(self):
        """检测存储设备
        
        设备类型判断方法（辅助判断，不阻断测试）：
        1. dmesg 中查找 ufshcd 关键字（最可靠）
        2. 列出所有块设备供用户参考
        
        注意：不管设备类型如何，测试都应该继续
        """
        import re
        ufs_found = False
        ufs_info = {}

        # ========== 方法 1: dmesg 检测 ufshcd（最可靠）==========
        rc, out, _ = self._run(['dmesg'])
        if rc == 0:
            for line in out.split('\n'):
                line_lower = line.lower()
                if 'ufshcd' in line_lower:
                    ufs_found = True
                    # 提取设备地址 (如 39410000.ufs)
                    match = re.search(r'([0-9a-f]+\.ufs)', line)
                    if match:
                        ufs_info['address'] = match.group(1)
                    # 提取 SCSI host (如 scsi host0)
                    match = re.search(r'scsi host([0-9]+)', line_lower)
                    if match:
                        ufs_info['scsi_host'] = f'host{match.group(1)}'
                    # 提取 gear/lane 配置 (如 gear[4, 4], lane[2, 2])
                    match = re.search(r'gear\[([0-9, ]+)\], lane\[([0-9, ]+)\]', line_lower)
                    if match:
                        ufs_info['gear'] = match.group(1).replace(' ', '')
                        ufs_info['lane'] = match.group(2).replace(' ', '')
                    # 提取 rate (如 rate(1))
                    match = re.search(r'rate\(([0-9]+)\)', line_lower)
                    if match:
                        ufs_info['rate'] = match.group(1)
        
        if ufs_found:
            self._record('storage', '设备类型', 'UFS ✓')
            if 'address' in ufs_info:
                self._record('storage', 'UFS 地址', ufs_info['address'])
            if 'scsi_host' in ufs_info:
                self._record('storage', 'SCSI Host', ufs_info['scsi_host'])
            if 'gear' in ufs_info and 'lane' in ufs_info:
                self._record('storage', 'UFS 配置', f'Gear {ufs_info["gear"]}, Lane {ufs_info["lane"]}')
            if 'rate' in ufs_info:
                self._record('storage', 'Rate', f'Rate {ufs_info["rate"]}')
        else:
            self._record('storage', '设备类型', '未检测到 UFS（dmesg 无 ufshcd）')
            self._record('storage', '💡 提示', '设备类型检测仅作辅助参考，不影响测试执行')

        # ========== 方法 2: 列出所有块设备 ==========
        rc, out, _ = self._run(['lsblk', '-d', '-o', 'NAME,SIZE,TYPE,ROTA', '--noheadings'])
        if rc == 0:
            self._record('storage', '📋 块设备', '\n' + out)
        else:
            # 备选方案：/proc/scsi/ufs/ 目录
            proc_ufs_dir = '/proc/scsi/ufs'
            has_proc_ufs = os.path.isdir(proc_ufs_dir)
            self._record('storage', '/proc/scsi/ufs', '存在 ✓' if has_proc_ufs else '不存在')
    
    def collect_permissions(self):
        try:
            import pwd, grp
            user = pwd.getpwuid(os.getuid()).pw_name
            gids = os.getgroups()
            group_names = []
            for gid in gids:
                try:
                    group_names.append(grp.getgrgid(gid).gr_name)
                except KeyError:
                    group_names.append(str(gid))
            self._record('permissions', '当前用户', user)
            self._record('permissions', '用户组', ', '.join(group_names) if group_names else '(无)')
            is_root = os.getuid() == 0
            has_disk = 'disk' in group_names
            access_str = '可读写 (root)' if is_root else ('可读写 (disk 组)' if has_disk else '权限可能不足')
            self._record('permissions', '设备访问', access_str)
        except Exception as e:
            self._record('permissions', '权限检查', f'检查失败: {e}')
    
    def collect_test_directory(self):
        """检查测试目录可用性"""
        # 检查 findmnt 命令兼容性
        rc, out, err = self._run(['findmnt', '--version'])
        findmnt_ver = out if rc == 0 else ('未安装' if rc == -1 else '检查失败')
        self._record('test_dir', 'findmnt 版本', findmnt_ver)
        
        # 尝试新版 findmnt
        rc, out, err = self._run(['findmnt', '-n', '-o', 'TARGET,SIZE,FSUSED,FSAVAIL', '-t', 'ext4,xfs,btrfs'])
        
        if rc != 0 and 'unknown column' in (err or '').lower():
            self._record('test_dir', 'findmnt 兼容性', '旧版 (不支持 FSUSED/FSAVAIL)')
            # 尝试旧版格式
            rc, out, err = self._run(['findmnt', '-n', '-o', 'TARGET,AVAIL', '-t', 'ext4,xfs,btrfs'])
            use_simple = True
        elif rc != 0:
            self._record('test_dir', 'findmnt 兼容性', f'不可用: {err}')
            self._record('test_dir', '建议测试目录', '/tmp/ufs_test (findmnt 不可用，回退)')
            self.runtime_config['test_dir'] = '/tmp/ufs_test'
            return
        else:
            self._record('test_dir', 'findmnt 兼容性', '新版 (支持所有列)')
            use_simple = False

        if rc != 0 or not out.strip():
            self._record('test_dir', '建议测试目录', '/tmp/ufs_test (无挂载点)')
            self.runtime_config['test_dir'] = '/tmp/ufs_test'
            return
        
        # 找可用空间最大的挂载点
        max_avail_gb = 0
        best_mount = None
        for line in out.strip().split('\n'):
            parts = line.strip().split()
            if use_simple:
                if len(parts) >= 2:
                    mount, avail_str = parts[0], parts[1]
                else:
                    continue
            else:
                if len(parts) >= 4:
                    mount, avail_str = parts[0], parts[3]
                else:
                    continue
            
            # 解析可用大小
            avail_gb = 0
            try:
                if avail_str.endswith('G'):
                    avail_gb = float(avail_str[:-1])
                elif avail_str.endswith('T'):
                    avail_gb = float(avail_str[:-1]) * 1024
                elif avail_str.endswith('M'):
                    avail_gb = float(avail_str[:-1]) / 1024
            except Exception:
                continue
            
            if avail_gb >= 2 and avail_gb > max_avail_gb:
                max_avail_gb = avail_gb
                best_mount = mount
        
        if best_mount:
            # 修复：当 mount 是 '/' 时，避免变成 '//ufs_test'
            if best_mount == '/':
                test_dir = '/ufs_test'
            else:
                test_dir = f'{best_mount}/ufs_test'
            self._record('test_dir', '建议测试目录', f'{test_dir} (可用 {max_avail_gb:.1f} GB)')
            self.runtime_config['test_dir'] = test_dir
        else:
            self._record('test_dir', '建议测试目录', '/tmp/ufs_test (所有挂载点 < 2GB)')
            self.runtime_config['test_dir'] = '/tmp/ufs_test'

    # ── 内部工具 ──────────────────────────────────────────

    def _suggest_test_directory(self, disk_name):
        """建议测试目录：找到该磁盘上最大的已挂载分区"""
        try:
            rc, lsblk_out, _ = self._run(['lsblk', '-o', 'NAME,SIZE,MOUNTPOINT', '-n'])
            if rc != 0:
                return
            
            lines = lsblk_out.strip().split('\n')
            max_size_gb = 0
            best_mount = None
            free_gb = 0

            for line in lines:
                line = line.strip()
                if not line:
                    continue
                # 只看这个磁盘的分区
                if not (line.startswith(disk_name + 'p') or line.startswith(disk_name + ' ')):
                    continue
                parts = line.split()
                if len(parts) >= 3:
                    mount = parts[-1]
                    if mount == '/' or mount == '[SWAP]' or not mount.startswith('/'):
                        continue
                    # 解析大小
                    size_str = parts[1]
                    size_gb = 0
                    try:
                        if size_str.endswith('G'):
                            size_gb = float(size_str[:-1])
                        elif size_str.endswith('T'):
                            size_gb = float(size_str[:-1]) * 1024
                    except Exception:
                        pass
                    # 检查可用空间
                    if os.path.exists(mount):
                        stat = os.statvfs(mount)
                        current_free = (stat.f_bavail * stat.f_frsize) / (1024 ** 3)
                        # 选择最大的且至少有 2GB 可用空间的挂载点
                        if size_gb > max_size_gb and current_free >= 2:
                            max_size_gb = size_gb
                            free_gb = current_free
                            best_mount = mount
            
            if best_mount:
                self._record('storage', '建议测试目录', f'{best_mount}/ufs_test (可用 {free_gb:.1f} GB)')
                self._record('storage', '默认测试文件路径', f'{best_mount}/ufs_test/test.file')
        except Exception:
            pass

    # ── 输出 ─────────────────────────────────────────────

    def run(self):
        print('=' * 60)
        print('UFS SysTest 环境信息')
        print('=' * 60)
        print(f'模式: {"开发模式" if self.mode == "dev" else "部署模式"}')

        self.collect_system()
        self.collect_toolchain()
        self.collect_storage()
        self.collect_permissions()
        self.collect_test_directory()

        # 按 category 分组输出
        current_cat = None
        cat_labels = {
            'system': '系统信息',
            'toolchain': '工具链',
            'storage': '存储设备',
            'permissions': '用户权限',
            'test_dir': '测试目录',
        }
        for item in self.items:
            cat = item['category']
            if cat != current_cat:
                current_cat = cat
                print(f'\n[{cat_labels.get(cat, cat)}]')
            print(f'  {item["name"]:<15} {item["value"]}')

        print()
        print(f'共检测 {len(self.items)} 项')
        print('=' * 60)

    def to_dict(self):
        return {
            'timestamp': datetime.now().isoformat(),
            'mode': self.mode,
            'items': self.items,
            'total': len(self.items),
        }

    def save_report(self, path='env_report.json'):
        with open(path, 'w') as f:
            json.dump(self.to_dict(), f, indent=2, ensure_ascii=False)
        print(f'\n报告已保存：{path}')

    def save_runtime_config(self):
        """将关键配置写入 runtime.json，供后续脚本读取"""
        self.runtime_config['env_checked_at'] = datetime.now().isoformat()

        config_path = self.config_dir / 'runtime.json'

        # 确保目录存在
        if not self.config_dir.exists():
            self.config_dir.mkdir(parents=True, exist_ok=True)

        # 读取现有配置（如果存在），合并更新
        existing = {}
        if config_path.exists():
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    existing = json.load(f)
            except Exception:
                pass

        # 合并配置：runtime_config 覆盖现有
        merged = {**existing, **self.runtime_config}

        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(merged, f, indent=2, ensure_ascii=False)

        print(f'\n✅ 配置已保存：{config_path}')
        print(f'   设备路径: {self.runtime_config.get("device", "未检测到")}')
        print(f'   测试目录: {self.runtime_config.get("test_dir", "未检测到")}')

        return config_path


def main():
    import argparse
    p = argparse.ArgumentParser(description='UFS SysTest 环境信息收集')
    p.add_argument('--mode', choices=['dev', 'deploy'], default='dev',
                   help='运行模式: dev(开发,默认) / deploy(部署)')
    p.add_argument('--report', action='store_true', help='生成 JSON 报告')
    p.add_argument('--output', default='env_report.json', help='报告输出路径')
    p.add_argument('--save-config', action='store_true', help='将检测结果保存为 runtime.json 配置文件')
    p.add_argument('-v', '--verbose', action='store_true', help='详细输出')
    args = p.parse_args()

    checker = EnvironmentChecker(mode=args.mode, verbose=args.verbose)
    checker.run()
    if args.report:
        checker.save_report(args.output)
    if args.save_config:
        checker.save_runtime_config()


if __name__ == '__main__':
    main()
