#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
临时文件清理脚本
清理 UFS Auto 项目中的临时文件和不需要的中间产物

用法:
    python3 cleanup_temp_files.py
    python3 cleanup_temp_files.py --dry-run  # 只预览，不实际删除
"""

import os
import sys
import shutil
from pathlib import Path
from datetime import datetime, timedelta


def find_and_clean_temp_files(root_dir, dry_run=False):
    """查找并清理临时文件"""
    root = Path(root_dir).absolute()
    temp_files = []
    
    print(f"🔍 扫描目录：{root}")
    
    # 定义要清理的文件模式
    patterns = [
        # 临时文件
        '*.tmp', '*.temp', '*.temp.*', '*.tmp.*',
        # 日志文件
        '*.log', 'logs/*.log', 'systest/logs/*.log',
        # Python 缓存
        '__pycache__', '*.pyc', '*.pyo', '*.pyd', '*$py.class',
        # 测试文件
        'ufs_test_*', 'test_*', 'systest/ufs_test_*',
        # 备份文件
        '*.bak', '*.backup', '*.swp', '*.swo', '*~',
        # 环境检查报告
        'env_check_report.json', 'env_report.json',
        # 性能基线对比结果
        'compare_report.json', 'baseline_*.json',
        # 旧配置备份
        'config/*.backup', 'config/*_backup.json',
        # 测试结果目录
        'results/', 'systest/results/',
        # 其他临时目录
        '.tmp/', '.temp/', '.cache/',
    ]
    
    # 搜索临时文件
    for pattern in patterns:
        for item in root.glob(pattern):
            if item.is_file() or item.is_dir():
                # 排除 .git 目录和 .gitignore 本身
                if '.git' in str(item.parts):
                    continue
                temp_files.append(item)
    
    print(f"📊 找到 {len(temp_files)} 个临时文件/目录")
    
    if not temp_files:
        print("✅ 没有发现临时文件需要清理")
        return 0
    
    # 显示将要删除的文件
    print("\n🗑️  将要删除的文件/目录：")
    for f in temp_files:
        size_str = ""
        if f.is_file():
            size_str = f" ({f.stat().st_size} bytes)"
        elif f.is_dir():
            try:
                size = sum(file.stat().st_size for file in f.rglob('*') if file.is_file())
                size_str = f" ({size} bytes)"
            except:
                size_str = " (directory)"
        print(f"  • {f}{size_str}")
    
    if dry_run:
        print("\n📋 --dry-run 模式：仅显示，不实际删除")
        return 0
    
    # 确认删除
    response = input(f"\n⚠️  确认删除这 {len(temp_files)} 个文件/目录吗？(y/N): ")
    if response.lower() != 'y':
        print("❌ 取消删除")
        return 1
    
    # 执行删除
    deleted_count = 0
    errors = []
    for f in temp_files:
        try:
            if f.is_file():
                f.unlink()
                print(f"  ✅ 删除文件: {f}")
            elif f.is_dir():
                shutil.rmtree(f)
                print(f"  ✅ 删除目录: {f}")
            deleted_count += 1
        except Exception as e:
            errors.append((f, str(e)))
            print(f"  ❌ 删除失败: {f} ({e})")
    
    print(f"\n✅ 完成！删除了 {deleted_count} 个项目")
    if errors:
        print(f"⚠️  {len(errors)} 个项目删除失败:")
        for path, error in errors:
            print(f"   • {path}: {error}")
    
    return len(errors)


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='UFS Auto 项目临时文件清理')
    parser.add_argument('--dry-run', action='store_true', help='预览模式，不实际删除')
    parser.add_argument('--root', default='.', help='项目根目录 (默认: .)')
    
    args = parser.parse_args()
    
    if args.dry_run:
        print("🔍 预览模式：扫描临时文件...")
    
    return find_and_clean_temp_files(args.root, dry_run=args.dry_run)


if __name__ == '__main__':
    sys.exit(main())