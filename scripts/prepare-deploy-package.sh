#!/bin/bash
# UFS Auto 离线部署打包脚本
# 用法：./prepare-deploy-package.sh

set -e

DEPLOY_DIR="/tmp/ufsauto-deploy-$(date +%Y%m%d_%H%M%S)"
OUTPUT_PKG="ufsauto-offline-deploy.tar.gz"

echo "======================================"
echo "  UFS Auto 离线部署包准备工具"
echo "======================================"
echo ""

# 创建部署目录
echo "📦 创建部署目录..."
mkdir -p "$DEPLOY_DIR"
cd "$DEPLOY_DIR"

# 1. 下载 FIO 源码
echo "📥 下载 FIO 3.33 源码..."
if command -v wget &> /dev/null; then
    wget -q https://github.com/axboe/fio/archive/refs/tags/fio-3.33.tar.gz
    echo "   ✅ FIO 源码下载完成"
elif command -v curl &> /dev/null; then
    curl -sLO https://github.com/axboe/fio/archive/refs/tags/fio-3.33.tar.gz
    echo "   ✅ FIO 源码下载完成"
else
    echo "   ⚠️  缺少 wget/curl，请手动下载 fio-3.33.tar.gz"
    echo "   下载地址：https://github.com/axboe/fio/archive/refs/tags/fio-3.33.tar.gz"
fi

# 2. 复制 UFS Auto 项目
echo "📁 复制 UFS Auto 项目..."
if [ -d "/workspace/projects/ufsauto" ]; then
    cp -r /workspace/projects/ufsauto ./
    echo "   ✅ UFS Auto 项目已复制"
else
    echo "   ❌ 找不到 /workspace/projects/ufsauto"
    exit 1
fi

# 3. 创建 FIO 安装脚本
echo "📝 创建 FIO 安装脚本..."
cat > install-fio.sh << 'INSTALL_SCRIPT'
#!/bin/bash
set -e

echo "=== FIO 3.33 离线安装 ==="

# 检查是否已安装
if command -v fio &> /dev/null; then
    CURRENT_VERSION=$(fio --version | head -1)
    echo "✓ FIO 已安装：$CURRENT_VERSION"
    if echo "$CURRENT_VERSION" | grep -q "3.33"; then
        echo "✓ 版本符合要求，无需重新安装"
        exit 0
    else
        echo "⚠ 版本不符，继续安装 3.33"
    fi
fi

# 检查源码包
if [ ! -f fio-3.33.tar.gz ]; then
    echo "❌ 错误：找不到 fio-3.33.tar.gz"
    exit 1
fi

# 检查编译工具
echo "检查编译工具..."
for cmd in gcc make; do
    if ! command -v $cmd &> /dev/null; then
        echo "❌ 错误：需要安装 $cmd"
        exit 1
    fi
done
echo "✓ 编译工具检查通过"

# 解压
echo "解压源码..."
tar -xzf fio-3.33.tar.gz
cd fio-3.33

# 配置
echo "配置编译选项..."
./configure --prefix=/usr/local

# 编译
echo "编译中... (这可能需要几分钟)"
make -j$(nproc)

# 安装
echo "安装 FIO..."
make install

# 验证
echo ""
echo "验证安装..."
fio --version

# 创建符号链接（如果 /usr/local/bin 不在 PATH 中）
if ! command -v fio &> /dev/null; then
    ln -sf /usr/local/bin/fio /usr/bin/fio
    echo "✓ 已创建符号链接 /usr/bin/fio"
fi

echo ""
echo "=== FIO 3.33 安装完成! ==="
INSTALL_SCRIPT

chmod +x install-fio.sh
echo "   ✅ FIO 安装脚本已创建"

# 4. 创建快速部署脚本
echo "📝 创建快速部署脚本..."
cat > quick-deploy.sh << 'DEPLOY_SCRIPT'
#!/bin/bash
set -e

echo "======================================"
echo "  UFS Auto 快速部署"
echo "======================================"

# 检查 root 权限
if [ "$(id -u)" != "0" ]; then
    echo "⚠️  需要 root 权限，请切换到 root 用户"
    exit 1
fi

# 安装 FIO
echo ""
echo "步骤 1/3: 安装 FIO"
echo "-------------------"
./install-fio.sh

# 验证环境
echo ""
echo "步骤 2/3: 验证 UFS Auto 环境"
echo "-----------------------------"
cd ufsauto
python3 systest/bin/systest.py check-env

# 提示
echo ""
echo "步骤 3/3: 准备就绪"
echo "-------------------"
echo ""
echo "✅ 部署完成！可以开始测试了"
echo ""
echo "常用命令:"
echo "  # 运行性能测试"
echo "  python3 systest/bin/systest.py run --suite performance"
echo ""
echo "  # 运行 QoS 测试"
echo "  python3 systest/bin/systest.py run --suite qos"
echo ""
echo "  # 查看报告"
echo "  python3 systest/bin/systest.py report --latest"
echo ""
DEPLOY_SCRIPT

chmod +x quick-deploy.sh
echo "   ✅ 快速部署脚本已创建"

# 5. 创建 README
echo "📝 创建部署说明..."
cat > DEPLOY_README.md << README_CONTENT
# UFS Auto 离线部署说明

## 📦 部署包内容

- \`fio-3.33.tar.gz\` - FIO 3.33 源码
- \`install-fio.sh\` - FIO 安装脚本
- \`ufsauto/\` - UFS Auto 测试框架
- \`quick-deploy.sh\` - 一键部署脚本

## 🚀 快速开始

### 方式一：一键部署（推荐）

\`\`\`bash
# 切换到 root 用户
sudo -i

# 进入部署目录
cd /mapdata/ufsauto-deploy

# 执行一键部署
./quick-deploy.sh
\`\`\`

### 方式二：分步部署

\`\`\`bash
# 1. 安装 FIO
sudo -i
cd /mapdata/ufsauto-deploy
./install-fio.sh

# 2. 验证环境
cd ufsauto
python3 systest/bin/systest.py check-env

# 3. 执行测试
python3 systest/bin/systest.py run --suite performance
\`\`\`

## 📋 环境要求

- **操作系统**: Linux (嵌入式开发板)
- **Python**: 3.8+ (推荐 3.11+)
- **编译工具**: gcc, make
- **存储空间**: 至少 50GB 可用空间
- **权限**: root

## ✅ 验证安装

\`\`\`bash
# 检查 FIO 版本
fio --version  # 应输出 fio-3.33

# 检查 Python 版本
python3 --version

# 检查 UFS Auto 环境
cd ufsauto
python3 systest/bin/systest.py check-env
\`\`\`

## 📖 详细文档

- \`ufsauto/README.md\` - UFS Auto 使用说明
- \`ufsauto/DEPLOYMENT_GUIDE.md\` - 开发板部署指南
- \`ufsauto/FIO_OFFLINE_INSTALL.md\` - FIO 离线安装指南

## 🆘 故障排查

如果遇到问题，请检查：

1. **root 权限**: 确保以 root 用户运行
2. **存储空间**: \`df -h\` 检查可用空间
3. **编译工具**: \`gcc --version\` 和 \`make --version\`
4. **设备权限**: \`ls -la /dev/sda\` 确认设备可访问

---

**部署时间**: $(date '+%Y-%m-%d %H:%M:%S')
**FIO 版本**: 3.33
**UFS Auto**: 最新版
README_CONTENT

echo "   ✅ 部署说明已创建"

# 6. 打包
echo ""
echo "📦 打包部署文件..."
cd /tmp
tar -czf "$OUTPUT_PKG" ufsauto-deploy-*/

# 显示结果
echo ""
echo "======================================"
echo "  ✅ 部署包准备完成!"
echo "======================================"
echo ""
echo "📦 部署包位置：/tmp/$OUTPUT_PKG"
echo "📦 部署包大小：$(du -h /tmp/$OUTPUT_PKG | cut -f1)"
echo ""
echo "📋 部署步骤:"
echo "   1. 将部署包复制到 U 盘或传输到开发板"
echo "   2. 在开发板上解压：tar -xzf $OUTPUT_PKG"
echo "   3. 进入目录：cd ufsauto-deploy-*"
echo "   4. 执行部署：./quick-deploy.sh"
echo ""
echo "📖 详细说明请查看部署包内的 DEPLOY_README.md"
echo ""

# 清理临时目录
# rm -rf "$DEPLOY_DIR"

echo "完成!"
