#!/bin/bash
# ARM Debian 12 UFS测试环境搭建脚本
# 适用于车规级ARM64平台

set -e

echo "====================================="
echo "UFS 3.1 测试环境搭建脚本"
echo "适用于 ARM Debian 12"
echo "====================================="

# 检查是否为root用户
if [ "$EUID" -ne 0 ]
  then echo "请以root权限运行此脚本"
  exit 1
fi

# 检查架构
ARCH=$(uname -m)
if [ "$ARCH" != "aarch64" ]; then
    echo "警告：当前架构为 $ARCH，推荐使用ARM64(aarch64)架构"
    read -p "是否继续？(y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]
    then
        exit 1
    fi
fi

echo "步骤1：更新系统软件包..."
apt update -y
apt upgrade -y

echo "步骤2：安装基础依赖..."
apt install -y \
    build-essential \
    linux-headers-$(uname -r) \
    python3 \
    python3-pip \
    python3-dev \
    python3-venv \
    git \
    curl \
    wget \
    vim \
    tmux \
    htop \
    iotop \
    fio \
    blktrace \
    smartmontools \
    nvme-cli \
    ufs-utils \
    lsscsi \
    pciutils \
    usbutils

echo "步骤3：安装Python依赖..."
pip3 install --upgrade pip
pip3 install -r ../requirements.txt

echo "步骤4：检查UFS内核支持..."
echo "检查内核配置..."

# 检查UFS相关内核配置
CONFIGS=(
    "CONFIG_SCSI_UFS"
    "CONFIG_SCSI_UFS_BSG"
    "CONFIG_SCSI_UFS_DEBUG"
    "CONFIG_SCSI_UFS_HISI"
    "CONFIG_SCSI_UFS_QCOM"
    "CONFIG_SCSI_UFS_TI_J721E"
)

for config in "${CONFIGS[@]}"; do
    if zcat /proc/config.gz | grep -q "$config=y"; then
        echo "✅ $config: 已启用"
    else
        echo "⚠️  $config: 未启用（可能影响功能）"
    fi
done

echo "步骤5：检查UFS设备..."
echo "UFS设备列表："
ls -la /dev/ufs* 2>/dev/null || echo "未检测到UFS设备"

echo "SCSI设备列表："
lsscsi | grep -i ufs || echo "未检测到UFS SCSI设备"

echo "步骤6：配置udev规则（可选）..."
read -p "是否配置UFS设备非root访问权限？(y/N) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]
then
    cat > /etc/udev/rules.d/99-ufs.rules << 'EOF'
# UFS设备访问规则
KERNEL=="ufs[0-9]*", MODE="0666", GROUP="disk"
KERNEL=="bsg/ufs[0-9]*", MODE="0666", GROUP="disk"
EOF
    udevadm control --reload-rules
    udevadm trigger
    echo "udev规则已配置，属于disk组的用户可以访问UFS设备"
fi

echo "步骤7：验证安装..."
echo "Python版本："
python3 --version

echo "UFS工具版本："
ufs-utils --version 2>/dev/null || echo "ufs-utils未安装"

echo "fio版本："
fio --version

echo "步骤8：创建测试目录..."
mkdir -p /opt/ufs_test
cp -r ../* /opt/ufs_test/
chmod +x /opt/ufs_test/cli/ufs_test_cli.py
ln -sf /opt/ufs_test/cli/ufs_test_cli.py /usr/local/bin/ufs_test_cli

echo "====================================="
echo "环境搭建完成！"
echo "====================================="
echo ""
echo "快速开始："
echo "1. 检查设备信息：ufs_test_cli info"
echo "2. 查看健康状态：ufs_test_cli health"
echo "3. 执行自检：ufs_test_cli selftest --short"
echo "4. 性能测试：ufs_test_cli perf --size 100"
echo ""
echo "注意：操作UFS设备需要root权限或正确的udev规则配置"
echo "文档位置：/opt/ufs_test/README.md"
