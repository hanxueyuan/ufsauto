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

    def __init__(self, mode='dev', verbose=False):
        self.mode = mode
        self.verbose = verbose
        self.items = []

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
        ufs_found = False

        # 1) ufshcd 内核模块
        rc, lsmod_out, _ = self._run(['lsmod'])
        ufshcd_loaded = 'ufshcd' in lsmod_out if rc == 0 else False
        self._record('storage', 'ufshcd 模块', '已加载' if ufshcd_loaded else '未加载')

        # 2) 通过 /sys 查找所有块设备，检查驱动是否包含 ufshcd
        for blk in sorted(glob.glob('/sys/block/*')):
            if ufs_found:
                break
            dev_name = os.path.basename(blk)
            try:
                # 不同拓扑结构，向上查找多个层级试一遍
                found_ufshcd = False
                for levels_up in [3, 2, 1]:
                    if found_ufshcd:
                        break
                    path_parts = [blk] + ['..'] * levels_up + ['driver']
                    host_link = os.path.join(*path_parts)
                    if os.path.islink(host_link):
                        driver = os.path.basename(os.readlink(host_link))
                        if 'ufs' in driver.lower() or 'ufshcd' in driver.lower():
                            found_ufshcd = True
                            break
                if found_ufshcd or ufshcd_loaded:
                    # 如果 ufshcd 已经加载，就算找不到驱动链，也认为这是 UFS 设备
                    ufs_found = True
                    dev_path = f'/dev/{dev_name}'
                    driver_name = driver if 'driver' in locals() else 'unknown'
                    self._record('storage', 'UFS 设备', f'{dev_path} (via {driver_name})')
                    # 容量
                    size_file = os.path.join(blk, 'size')
                    if os.path.exists(size_file):
                        with open(size_file) as f:
                            sectors = int(f.read().strip())
                            gb = sectors * 512 / (1024 ** 3)
                            self._record('storage', '设备容量', f'{gb:.0f} GB')
                    # vendor / model
                    for attr in ('vendor', 'model', 'rev'):
                        attr_path = os.path.join(blk, 'device', attr)
                        if os.path.exists(attr_path):
                            with open(attr_path) as f:
                                val = f.read().strip()
                                label = {'vendor': '厂商', 'model': '型号', 'rev': '固件版本'}[attr]
                                self._record('storage', label, val)
                    break  # 取第一个 UFS 设备
            except Exception:
                continue

        # 3) 回退 1：/dev/disk/by-id 中含 ufs
        if not ufs_found:
            try:
                for link in glob.glob('/dev/disk/by-id/*ufs*') + glob.glob('/dev/disk/by-id/*UFS*'):
                    real = os.path.realpath(link)
                    ufs_found = True
                    self._record('storage', 'UFS 设备', f'{real} (by-id: {os.path.basename(link)})')
                    break
            except Exception:
                pass

        # 4) 回退 2：列出所有 /dev/mmcblk* ，某些平台 UFS 暴露为 mmcblk
        if not ufs_found:
            try:
                for dev in sorted(glob.glob('/dev/mmcblk*')):
                    if 'p' in os.path.basename(dev):
                        continue  # 跳过分区
                    dev_name = os.path.basename(dev)
                    sys_path = f'/sys/block/{dev_name}'
                    if os.path.exists(sys_path):
                        ufs_found = True
                        self._record('storage', 'UFS 设备', f'/dev/{dev_name} (mmc format)')
                        # 容量
                        size_file = os.path.join(sys_path, 'size')
                        if os.path.exists(size_file):
                            with open(size_file) as f:
                                sectors = int(f.read().strip())
                                gb = sectors * 512 / (1024 ** 3)
                                self._record('storage', '设备容量', f'{gb:.0f} GB')
                        break
            except Exception:
                pass

        # 5) 回退 3：列出所有 /dev/nvme* ，某些平台 UFS 挂在 PCIe NVMe 下
        if not ufs_found:
            try:
                for dev in sorted(glob.glob('/dev/nvme*')):
                    if dev.endswith('n1'):  # 第一个命名空间
                        ufs_found = True
                        self._record('storage', 'UFS 设备', f'{dev} (NVMe format)')
                        break
            except Exception:
                pass

        # 6) 回退 4：调用 lsblk 列出所有块设备，从厂商/型号/类型识别 UFS
        if not ufs_found:
            try:
                rc, lsblk_out, _ = self._run(['lsblk', '-o', 'NAME,SIZE,MODEL,VENDOR,TYPE,FSTYPE,MOUNTPOINT', '-n'])
                if rc == 0:
                    lines = lsblk_out.strip().split('\n')
                    candidate_devices = []
                    for line in lines:
                        line = line.strip()
                        if not line or line.startswith('├─') or line.startswith('└─'):
                            continue  # 跳过分区，只看整块设备
                        parts = line.split()
                        # 解析各列
                        name = parts[0] if len(parts) >= 1 else ''
                        size_str = parts[1] if len(parts) >= 2 else ''
                        model = parts[2] if len(parts) >= 3 else ''
                        vendor = parts[3] if len(parts) >= 4 else ''
                        dev_type = parts[4] if len(parts) >= 5 else ''
                        
                        if dev_type != 'disk':
                            continue  # 只看整个磁盘设备
                        
                        # 判断是否为 UFS 设备
                        vendor_lower = (vendor or '').lower()
                        model_lower = (model or '').lower()
                        # UFS 常见厂商：SKhynix, Samsung, Micron, Western Digital, Toshiba
                        ufs_vendors = ['skhynix', 'hynix', 'samsung', 'micron', 'wd', 'western', 'toshiba']
                        is_ufs_vendor = any(v in vendor_lower for v in ufs_vendors)
                        has_ufs_in_name = 'ufs' in model_lower or 'ufs' in vendor_lower
                        
                        if is_ufs_vendor or has_ufs_in_name:
                            dev_path = f'/dev/{name}'
                            ufs_found = True
                            info = f'{dev_path}'
                            if vendor or model:
                                info += f' ({vendor} {model})'.strip()
                            self._record('storage', 'UFS 设备', info)
                            # 获取容量
                            try:
                                rc2, size_out, _ = self._run(['blockdev', '--getsize64', dev_path])
                                if rc2 == 0:
                                    bytes = int(size_out.strip())
                                    gb = bytes / (1024 ** 3)
                                    self._record('storage', '设备容量', f'{gb:.0f} GB')
                                    # 建议测试目录：选择最大的已挂载分区放测试文件
                                    # 查找该磁盘下最大的已挂载分区
                                    self._suggest_test_directory(name)
                            except Exception:
                                pass
                            break
            except Exception:
                pass

        # 7) 如果还是没找到，列出所有块设备供用户参考
        if not ufs_found:
            self._record('storage', 'UFS 设备', '未检测到')
            self._record('storage', '💡 提示', '如果确认设备存在，可以直接在 run 命令中用 --device 指定路径')
            try:
                rc, lsblk_out, _ = self._run(['lsblk', '-o', 'NAME,SIZE,MODEL,VENDOR,TYPE,FSTYPE,MOUNTPOINT'])
                if rc == 0:
                    self._record('storage', '📋 所有块设备', '\n' + lsblk_out)
            except Exception:
                pass
            if self.mode == 'deploy':
                self._record('storage', '⚠️  WARNING', 'UFS 设备未自动找到，但可以手动指定 --device 继续')

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
            return
        else:
            self._record('test_dir', 'findmnt 兼容性', '新版 (支持所有列)')
            use_simple = False
        
        if rc != 0 or not out.strip():
            self._record('test_dir', '建议测试目录', '/tmp/ufs_test (无挂载点)')
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
            self._record('test_dir', '建议测试目录', f'{best_mount}/ufs_test (可用 {max_avail_gb:.1f} GB)')
        else:
            self._record('test_dir', '建议测试目录', '/tmp/ufs_test (所有挂载点 < 2GB)')

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


def main():
    import argparse
    p = argparse.ArgumentParser(description='UFS SysTest 环境信息收集')
    p.add_argument('--mode', choices=['dev', 'deploy'], default='dev',
                   help='运行模式: dev(开发,默认) / deploy(部署)')
    p.add_argument('--report', action='store_true', help='生成 JSON 报告')
    p.add_argument('--output', default='env_report.json', help='报告输出路径')
    p.add_argument('-v', '--verbose', action='store_true', help='详细输出')
    args = p.parse_args()

    checker = EnvironmentChecker(mode=args.mode, verbose=args.verbose)
    checker.run()
    if args.report:
        checker.save_report(args.output)


if __name__ == '__main__':
    main()
