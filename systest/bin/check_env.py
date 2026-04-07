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
        2. 列出所有块设备，识别 UFS 设备路径
        
        注意：不管设备类型如何，测试都应该继续
        """
        import re
        ufs_found = False
        ufs_info = {}
        device_path = None

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

        # ========== 方法 2: 列出所有块设备，检测 UFS 设备路径 ==========
        rc, out, _ = self._run(['lsblk', '-d', '-o', 'NAME,SIZE,TYPE,ROTA', '--noheadings'])
        if rc == 0:
            self._record('storage', '📋 块设备', '\n' + out)
            
            # 解析块设备列表，找到 UFS 设备
            first_disk = None
            for line in out.strip().split('\n'):
                parts = line.split()
                if len(parts) >= 3 and parts[2] == 'disk':
                    dev_name = parts[0]
                    # 保存第一个磁盘，供后面回退使用
                    if first_disk is None:
                        first_disk = dev_name
                    # 检查是否是 UFS 设备（通过 /sys/block 检查驱动）
                    driver_path = f'/sys/block/{dev_name}/device/driver'
                    if os.path.exists(driver_path):
                        try:
                            driver = os.path.basename(os.readlink(driver_path))
                            if 'ufs' in driver.lower() or 'ufshcd' in driver.lower():
                                device_path = f'/dev/{dev_name}'
                                self._record('storage', 'UFS 设备路径', f'{device_path} (via {driver})')
                                break
                        except Exception:
                            pass
            
            # 如果已经通过 dmesg 找到了 UFS 主机控制器，但没通过驱动匹配到
            # 直接使用第一个块设备（UFS 通常是第一个磁盘）
            if ufs_found and not device_path and first_disk:
                device_path = f'/dev/{first_disk}'
                self._record('storage', 'UFS 设备路径', f'{device_path} (auto-detected: UFS host found, using first disk)')
        
        # 如果没找到 UFS 设备，尝试通过 SCSI host 查找
        if not device_path and 'scsi_host' in ufs_info:
            # SCSI host0 通常对应 /dev/sda
            host_num = ufs_info['scsi_host'].replace('host', '')
            # 尝试查找对应的块设备
            rc, out, _ = self._run(['lsblk', '-d', '-o', 'NAME,MAJ:MIN', '--noheadings'])
            if rc == 0:
                for line in out.strip().split('\n'):
                    parts = line.split()
                    if len(parts) >= 2:
                        dev_name = parts[0]
                        # 检查设备是否通过 SCSI host 连接
                        sys_path = f'/sys/block/{dev_name}'
                        if os.path.exists(sys_path):
                            try:
                                # 向上查找 host
                                for _ in range(5):
                                    sys_path = os.path.dirname(sys_path)
                                    if 'host' in os.path.basename(sys_path):
                                        if f'host{host_num}' in os.path.basename(sys_path):
                                            device_path = f'/dev/{dev_name}'
                                            self._record('storage', 'UFS 设备路径', f'{device_path} (via SCSI {ufs_info["scsi_host"]})')
                                            break
                            except Exception:
                                pass
                    if device_path:
                        break
        
        # 保存设备路径到配置
        if device_path:
            self.runtime_config['device'] = device_path
        else:
            # 如果仍然没找到，使用默认值 /dev/sda（开发板 UFS 通常是 sda）
            self._record('storage', '⚠️  设备路径', f'未自动检测到，将使用默认值 /dev/sda')
            self._record('storage', '💡 提示', '请手动指定设备路径: --device=/dev/sdX')
            self.runtime_config['device'] = '/dev/sda'
    
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
        # 不限制文件系统类型：任何可挂载的可写文件系统都可以用
        rc, out, err = self._run(['findmnt', '-n', '-o', 'TARGET,SIZE,FSUSED,FSAVAIL'])
        
        if rc != 0 and 'unknown column' in (err or '').lower():
            self._record('test_dir', 'findmnt 兼容性', '旧版 (不支持 FSUSED/FSAVAIL)')
            # 尝试旧版格式
            rc, out, err = self._run(['findmnt', '-n', '-o', 'TARGET,AVAIL'])
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
            if len(parts) < 2:
                continue  # 至少需要两列
            
            # 健壮解析：
            # use_simple = True  -> -o TARGET,AVAIL => 总是 TARGET=第一列 AVAIL=最后一列
            # use_simple = False -> -o TARGET,SIZE,FSUSED,FSAVAIL => TARGET=第一列 FSAVAIL=最后一列
            mount = parts[0]
            avail_str = parts[-1]  # AVAIL / FSAVAIL 总是最后一列
            
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
            
            # 跳过根目录（通常是只读的）
            if mount == '/':
                continue
            
            # 检查挂载点是否可读写
            if not os.access(mount, os.W_OK):
                continue
            
            # 优先选可用空间最大的，至少 2GB 比较理想
            # 如果找不到 ≥2GB 的，就用最大的那个（有空间总比没空间好）
            if avail_gb > max_avail_gb:
                max_avail_gb = avail_gb
                best_mount = mount
        
        if best_mount:
            # 不管空间大小，只要找到一个可用的，就用它
            # 如果空间小于 2GB 会在日志里提示，但仍然使用它
            if max_avail_gb >= 2:
                self._record('test_dir', '建议测试目录', f'{best_mount}/ufs_test (可用 {max_avail_gb:.1f} GB)')
            else:
                self._record('test_dir', '建议测试目录', f'{best_mount}/ufs_test (可用 {max_avail_gb:.1f} GB，小于推荐的 2GB)')
            self.runtime_config['test_dir'] = f'{best_mount}/ufs_test'
        else:
            # 实在找不到，才回退到默认 /mapdata/ufs_test（开发板常用挂载点）
            self._record('test_dir', '建议测试目录', '/mapdata/ufs_test (未找到其他可写挂载点，使用开发板默认)')
            self.runtime_config['test_dir'] = '/mapdata/ufs_test'

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


def check_ci_environment(config_path=None):
    """CI/CD 环境验证 - 检测常见低级配置错误

    专门用于 GitHub Actions 等CI 环境中，快速验证环境是否合规。
    返回码: 0 = 合规, 1 = 存在问题
    """
    import sys
    from pathlib import Path

    errors = []
    warnings = []

    # 1. 检查 runtime.json 是否存在
    if config_path:
        runtime_path = Path(config_path)
    else:
        runtime_path = Path(__file__).parent.parent / 'config' / 'runtime.json'

    if not runtime_path.exists():
        warnings.append(f"runtime.json 不存在 (CI 使用 dry-run 模式，可忽略)")
    # CI 环境不需要检查配置文件内容 - 使用 dry-run 模式验证框架

    # 2. 检查关键工具是否安装
    required_tools = ['fio', 'python3']
    for tool in required_tools:
        rc, _, _ = EnvironmentChecker._run([tool, '--version'])
        if rc != 0: errors.append(f"关键工具未安装: {tool}")

    # 输出结果
    print("" + "=" * 60)
    print("CI 环境验证 (dry-run 模式)")
    print("=" * 60)

    if errors:
        print("❌ 验证失败:")
        for i, err in enumerate(errors, 1):
            print(f"   {i}. {err}")

    if warnings:
        print("⚠️  警告:")
        for i, warn in enumerate(warnings, 1):
            print(f"   {i}. {warn}")

    if not errors and not warnings:
        print("✅ CI 环境验证通过 (dry-run 模式可用)")

    print("=" * 60)

    # 返回码：有问题则返回 1
    return 1 if errors else 0


def main():
    import argparse
    import sys
    p = argparse.ArgumentParser(description='UFS SysTest 环境信息收集')
    p.add_argument('--mode', choices=['dev', 'deploy'], default='dev',
                   help='运行模式: dev(开发,默认) / deploy(部署)')
    p.add_argument('--report', action='store_true', help='生成 JSON 报告')
    p.add_argument('--output', default='env_report.json', help='报告输出路径')
    p.add_argument('--save-config', action='store_true', help='将检测结果保存为 runtime.json 配置文件')
    p.add_argument('--ci', action='store_true', help='CI/CD 环境验证模式 (快速检查配置合规性)')
    p.add_argument('-v', '--verbose', action='store_true', help='详细输出')
    args = p.parse_args()

    # CI 模式：快速验证环境合规性
    if args.ci:
        sys.exit(check_ci_environment())

    # 正常模式：收集环境信息
    checker = EnvironmentChecker(mode=args.mode, verbose=args.verbose)
    checker.run()
    if args.report:
        checker.save_report(args.output)
    if args.save_config:
        checker.save_runtime_config()


if __name__ == '__main__':
    main()
