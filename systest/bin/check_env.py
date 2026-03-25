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

        # sg3-utils
        rc, _, _ = self._run(['which', 'sg_readcap'])
        self._record('toolchain', 'sg3-utils', '已安装' if rc == 0 else '未安装')

        # hdparm
        rc, _, _ = self._run(['which', 'hdparm'])
        self._record('toolchain', 'hdparm', '已安装' if rc == 0 else '未安装')

    def collect_storage(self):
        ufs_found = False

        # 1) ufshcd 内核模块
        rc, lsmod_out, _ = self._run(['lsmod'])
        ufshcd_loaded = 'ufshcd' in lsmod_out if rc == 0 else False
        self._record('storage', 'ufshcd 模块', '已加载' if ufshcd_loaded else '未加载')

        # 2) 通过 /sys 查找 UFS 块设备
        if ufshcd_loaded:
            for blk in sorted(glob.glob('/sys/block/sd*')):
                dev_name = os.path.basename(blk)
                try:
                    # 检查 host 驱动是否包含 ufshcd
                    host_link = os.path.join(blk, 'device', '..', '..', '..', 'driver')
                    if os.path.islink(host_link):
                        driver = os.path.basename(os.readlink(host_link))
                        if 'ufshcd' in driver:
                            ufs_found = True
                            dev_path = f'/dev/{dev_name}'
                            self._record('storage', 'UFS 设备', f'{dev_path} (via {driver})')
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

        # 3) 回退：/dev/disk/by-id 中含 ufs
        if not ufs_found:
            try:
                for link in glob.glob('/dev/disk/by-id/*ufs*'):
                    real = os.path.realpath(link)
                    ufs_found = True
                    self._record('storage', 'UFS 设备', f'{real} (by-id: {os.path.basename(link)})')
                    break
            except Exception:
                pass

        if not ufs_found:
            self._record('storage', 'UFS 设备', '未检测到')
            if self.mode == 'deploy':
                self._record('storage', '⚠️  WARNING', 'UFS 设备未找到，部署模式下需要可用的 UFS 设备')

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

        # 按 category 分组输出
        current_cat = None
        cat_labels = {
            'system': '系统信息',
            'toolchain': '工具链',
            'storage': '存储设备',
            'permissions': '用户权限',
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
