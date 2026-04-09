#!/bin/bash
# UFS Auto 环境一键部署脚本
# 适用于离线开发板环境

set -e

echo "======================================"
echo "  UFS Auto 环境一键部署"
echo "======================================"
echo ""

# 检查 root 权限
if [ "$(id -u)" != "0" ]; then
    echo "⚠️  警告：建议以 root 权限运行"
    echo "   某些操作可能需要设备访问权限"
    echo ""
fi

# 步骤 1: 检查并安装 FIO
echo "步骤 1/3: 检查 FIO 安装"
echo "------------------------"
if command -v fio &> /dev/null; then
    FIO_VERSION=$(fio --version | head -1)
    echo "✅ FIO 已安装：$FIO_VERSION"
else
    echo "⚠️  FIO 未安装，尝试安装..."
    
    # 尝试 apt 安装
    if command -v apt-get &> /dev/null; then
        echo "   通过 apt 安装 FIO..."
        apt-get update -qq
        apt-get install -y fio
        echo "✅ FIO 安装完成：$(fio --version)"
    else
        echo "❌ 无法安装 FIO，请手动安装"
        exit 1
    fi
fi

# 步骤 2: 检查 Python
echo ""
echo "步骤 2/3: 检查 Python 环境"
echo "---------------------------"
if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version)
    echo "✅ $PYTHON_VERSION"
else
    echo "❌ Python3 未安装"
    exit 1
fi

# 步骤 3: 检查 UFS Auto 配置
echo ""
echo "步骤 3/3: 检查 UFS Auto 配置"
echo "-----------------------------"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [ -f "$SCRIPT_DIR/systest/bin/systest_cli.py" ]; then
    echo "✅ UFS Auto 项目文件存在"
    echo "   位置：$SCRIPT_DIR"
else
    echo "❌ 找不到 UFS Auto 项目文件"
    exit 1
fi

# 运行环境检查
echo ""
echo "运行环境检查..."
cd "$SCRIPT_DIR"
python3 systest/bin/systest_cli.py check-env

echo ""
echo "======================================"
echo "  ✅ 环境部署完成!"
echo "======================================"
echo ""
echo "📊 环境摘要:"
echo "   FIO 版本：$(fio --version)"
echo "   Python: $(python3 --version)"
echo "   项目位置：$SCRIPT_DIR"
echo ""
echo "🚀 开始测试:"
echo "   # 运行性能测试"
echo "   python3 systest/bin/systest_cli.py run --suite performance"
echo ""
echo "   # 运行 QoS 测试"
echo "   python3 systest/bin/systest_cli.py run --suite qos"
echo ""
echo "   # 查看帮助"
echo "   python3 systest/bin/systest_cli.py --help"
echo ""
