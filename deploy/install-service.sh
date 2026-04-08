#!/bin/bash
# UFS SysTest systemd 部署脚本

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
SYSTEMD_DIR="/etc/systemd/system"

echo "=== UFS SysTest systemd 部署 ==="
echo ""

# 1. 检查权限
if [ "$EUID" -ne 0 ]; then 
    echo "❌ 请使用 sudo 运行此脚本"
    echo "   sudo bash $0"
    exit 1
fi

echo "✅ 权限检查通过"

# 2. 安装项目
echo ""
echo "📦 安装项目到 /opt/ufsauto..."
mkdir -p /opt/ufsauto
cp -r "$PROJECT_DIR"/* /opt/ufsauto/
chown -R root:root /opt/ufsauto
chmod +x /opt/ufsauto/systest/bin/*

echo "✅ 项目安装完成"

# 3. 创建测试目录
echo ""
echo "📁 创建测试目录..."
mkdir -p /mapdata/ufs_test
chmod 755 /mapdata/ufs_test

echo "✅ 测试目录已创建"

# 4. 安装 systemd 服务
echo ""
echo "🔧 安装 systemd 服务..."
cp "$SCRIPT_DIR/ufs-systest.service" "$SYSTEMD_DIR/"
cp "$SCRIPT_DIR/ufs-systest.timer" "$SYSTEMD_DIR/"
systemctl daemon-reload

echo "✅ systemd 服务已安装"

# 5. 启用定时任务
echo ""
echo "⏰ 启用定时任务..."
systemctl enable ufs-systest.timer
systemctl start ufs-systest.timer

echo "✅ 定时任务已启用"

# 6. 显示状态
echo ""
echo "=== 服务状态 ==="
systemctl status ufs-systest.timer --no-pager

echo ""
echo "=== 部署完成 ==="
echo ""
echo "常用命令:"
echo "  # 查看服务状态"
echo "  systemctl status ufs-systest.timer"
echo ""
echo "  # 手动运行测试"
echo "  systemctl start ufs-systest.service"
echo ""
echo "  # 查看日志"
echo "  journalctl -u ufs-systest.service -f"
echo ""
echo "  # 禁用定时任务"
echo "  systemctl disable ufs-systest.timer"
echo ""
