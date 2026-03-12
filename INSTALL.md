# 安装与部署指南

## 支持平台

### 硬件平台
- ✅ ARM64 (aarch64) - 推荐用于车规级平台
- ✅ x86_64 - 用于开发和仿真测试
- ⚠️ 其他架构未测试

### 操作系统
- ✅ Debian 12 (Bookworm) - 官方支持
- ✅ Ubuntu 22.04 LTS - 兼容支持
- ⚠️ 其他Linux发行版需要自行适配内核

### 内核要求
- Linux 4.19+
- 启用UFS子系统支持
- 启用UFS BSG接口 (CONFIG_SCSI_UFS_BSG=y)

## 快速安装

### 1. 下载代码
```bash
git clone <repository-url>
cd ufs31_test_suite
```

### 2. 运行自动化安装脚本
```bash
sudo ./scripts/env_setup.sh
```

该脚本会自动：
- 更新系统软件包
- 安装所有依赖包
- 配置Python环境
- 检查UFS内核支持
- 安装命令行工具到系统路径
- 配置udev规则（可选）

### 3. 验证安装
```bash
# 检查命令是否可用
ufs_test_cli --help

# 查看设备信息（需要root权限）
sudo ufs_test_cli info
```

## 手动安装

### 步骤1：安装系统依赖
```bash
# Debian/Ubuntu
sudo apt update
sudo apt install -y \
    build-essential \
    linux-headers-$(uname -r) \
    python3 \
    python3-pip \
    python3-dev \
    git \
    fio \
    blktrace \
    ufs-utils \
    lsscsi
```

### 步骤2：安装Python依赖
```bash
pip3 install -r requirements.txt
```

### 步骤3：安装命令行工具
```bash
# 安装到用户目录
cp cli/ufs_test_cli.py ~/.local/bin/ufs_test_cli
chmod +x ~/.local/bin/ufs_test_cli

# 或安装到系统目录
sudo cp cli/ufs_test_cli.py /usr/local/bin/ufs_test_cli
sudo chmod +x /usr/local/bin/ufs_test_cli
```

### 步骤4：配置udev规则（可选，非root访问）
```bash
sudo tee /etc/udev/rules.d/99-ufs.rules << 'EOF'
# UFS设备访问规则
KERNEL=="ufs[0-9]*", MODE="0666", GROUP="disk"
KERNEL=="bsg/ufs[0-9]*", MODE="0666", GROUP="disk"
EOF

sudo udevadm control --reload-rules
sudo udevadm trigger
```

## ARM Debian 12 镜像构建

### 构建自定义ARM镜像
```bash
# 下载Debian 12 ARM64基础镜像
wget https://cdimage.debian.org/debian-cd/current/arm64/iso-cd/debian-12.4.0-arm64-netinst.iso

# 定制镜像（可选）
# 使用live-build工具构建包含UFS工具的自定义镜像
```

### 内核配置
确保内核包含以下配置：
```bash
# 检查UFS支持
zcat /proc/config.gz | grep -i ufs

# 必需配置
CONFIG_SCSI_UFS=y
CONFIG_SCSI_UFS_BSG=y
CONFIG_SCSI_UFS_DEBUG=y

# 可选的平台特定驱动
CONFIG_SCSI_UFS_HISI=y  # 华为平台
CONFIG_SCSI_UFS_QCOM=y  # 高通平台
CONFIG_SCSI_UFS_TI_J721E=y  # TI平台
```

如果内核缺少UFS支持，需要重新编译内核：
```bash
# 下载内核源码
git clone https://git.kernel.org/pub/scm/linux/kernel/git/stable/linux.git
cd linux
git checkout v6.1.0  # 使用LTS版本

# 配置内核
make defconfig
make menuconfig
# 启用：Device Drivers -> SCSI device support -> SCSI UFS support

# 编译内核
make -j$(nproc)
make modules_install
make install
```

## Docker 部署

### 构建Docker镜像
```dockerfile
FROM debian:bookworm
WORKDIR /opt/ufs_test_suite
RUN apt update && apt install -y python3 python3-pip ufs-utils
COPY requirements.txt .
RUN pip3 install -r requirements.txt
COPY . .
RUN ln -s /opt/ufs_test_suite/cli/ufs_test_cli.py /usr/local/bin/ufs_test_cli
ENTRYPOINT ["ufs_test_cli"]
```

### 运行容器
```bash
# 构建镜像
docker build -t ufs-test-suite .

# 运行（需要特权模式访问硬件）
docker run --privileged -v /dev:/dev ufs-test-suite info
```

## 开发环境配置

### 开发依赖安装
```bash
pip3 install -r requirements-dev.txt
```

### 运行单元测试
```bash
cd tests
python -m pytest test_ufs_device.py -v
```

### 代码格式检查
```bash
# 安装代码检查工具
pip3 install black flake8 mypy

# 格式化代码
black src/ cli/ tests/

# 代码检查
flake8 src/ cli/ tests/

# 类型检查
mypy src/
```

## 常见安装问题

### 问题1：找不到UFS设备
```bash
# 检查设备节点
ls /dev/ufs*

# 检查SCSI设备
lsscsi | grep -i ufs

# 检查内核模块
lsmod | grep ufs

# 手动加载UFS模块
sudo modprobe ufs
```

### 问题2：权限被拒绝
```bash
# 方法1：使用sudo运行
sudo ufs_test_cli info

# 方法2：配置udev规则（参考上文）
# 确保当前用户在disk组中
sudo usermod -aG disk $USER
# 重新登录生效
```

### 问题3：IOCTL调用失败
```bash
# 检查内核是否支持BSG接口
zcat /proc/config.gz | grep CONFIG_SCSI_UFS_BSG

# 确认设备路径正确
# UFS设备节点通常是/dev/ufs0, /dev/ufs1等
# 对应的BSG节点是/dev/bsg/ufs0, /dev/bsg/ufs1等
```

### 问题4：ufs-utils安装失败
```bash
# 对于Debian 12，ufs-utils在官方源中
sudo apt install ufs-utils

# 如果源中没有，手动编译安装
git clone https://github.com/westerndigitalcorporation/ufs-utils.git
cd ufs-utils
make
sudo make install
```

## 验证安装成功

### 1. 基本功能验证
```bash
# 显示设备信息
sudo ufs_test_cli info

# 查看健康状态
sudo ufs_test_cli health

# 执行快速自检
sudo ufs_test_cli selftest --short
```

### 2. 性能测试验证
```bash
# 100MB性能测试
sudo ufs_test_cli perf --size 100
```

### 3. 压力测试验证
```bash
# 1分钟随机IO测试
sudo python scripts/stress_test.py random --duration 60
```

## 生产环境部署建议

### 安全配置
1. 禁止非授权用户访问UFS设备
2. 使用专用测试用户运行测试工具
3. 定期更新系统和工具版本
4. 配置日志审计

### 性能优化
1. 使用高性能ARM64平台
2. 配置CPU性能模式
3. 关闭不必要的后台服务
4. 启用UFS Write Booster功能

### 可靠性配置
1. 配置硬件看门狗
2. 实现错误监控和告警
3. 定期执行设备健康检查
4. 关键数据定期备份

## 卸载
```bash
# 删除命令行工具
sudo rm /usr/local/bin/ufs_test_cli

# 删除安装目录
sudo rm -rf /opt/ufs_test_suite

# 删除udev规则
sudo rm /etc/udev/rules.d/99-ufs.rules
sudo udevadm control --reload-rules
```

## 版本更新
```bash
cd ufs31_test_suite
git pull
sudo ./scripts/env_setup.sh
```
