# FIO 3.33 离线安装指南

## 📋 现状分析

| 项目 | 状态 |
|------|------|
| 当前 FIO 版本 | 未安装 |
| 目标版本 | 3.33 |
| 网络状态 | ❌ 受限（无法访问 GitHub/apt 源） |
| 编译工具 | ✅ 已安装 (gcc, make, git) |

---

## 🔧 安装方案

### 方案 A：在联网机器打包（推荐）

#### 1. 在联网机器上下载 FIO 源码包

```bash
# 下载 FIO 3.33 源码
cd /tmp
wget https://github.com/axboe/fio/archive/refs/tags/fio-3.33.tar.gz

# 或者使用 git 克隆
git clone --depth 1 --branch fio-3.33 https://github.com/axboe/fio.git fio-3.33
tar -czf fio-3.33.tar.gz fio-3.33
```

#### 2. 打包依赖（可选）

```bash
# 下载 apt 包（如果需要）
apt-get download fio libgfapi0 libglusterfs0 librbd1
```

#### 3. 传输到开发板

```bash
# 通过 U 盘/SCP 传输
cp fio-3.33.tar.gz /media/usb/
```

#### 4. 在开发板上编译安装

```bash
# 解压源码
cd /tmp
tar -xzf fio-3.33.tar.gz
cd fio-3.33

# 配置和编译
./configure
make -j$(nproc)

# 安装
make install

# 验证
fio --version  # 应输出 fio-3.33
```

---

### 方案 B：使用预编译二进制包

#### 1. 在联网机器下载 deb 包

```bash
# 创建下载目录
mkdir -p /tmp/fio-offline
cd /tmp/fio-offline

# 下载 FIO 及其依赖
apt-get download fio libgfapi0 libglusterfs0 libgfxdr0 libgfrpc0 \
    librados2 librbd1 libpmem1 libpmemobj1 libdaxctl1 libndctl6 \
    libibverbs1 librdmacm1 ibverbs-providers

# 打包
tar -czf fio-offline-packages.tar.gz *.deb
```

#### 2. 传输到开发板并安装

```bash
# 传输后解压安装
cd /tmp
tar -xzf fio-offline-packages.tar.gz
dpkg -i *.deb

# 验证
fio --version
```

---

### 方案 C：使用容器（如果开发板支持）

```bash
# 如果开发板有 Docker/Podman
docker run --rm -v /mapdata:/data ubuntu:24.04 bash -c "
  apt-get update && apt-get install -y fio && fio --version
"
```

---

## 📦 完整离线部署包结构

建议在联网机器准备以下文件：

```
ufsauto-deploy/
├── fio-3.33.tar.gz          # FIO 源码
├── ufsauto/                 # UFS Auto 项目
│   └── ...
├── install-fio.sh           # FIO 安装脚本
└── README.md                # 安装说明
```

### install-fio.sh 脚本

```bash
#!/bin/bash
set -e

echo "=== FIO 3.33 离线安装 ==="

# 检查是否已安装
if command -v fio &> /dev/null; then
    echo "FIO 已安装：$(fio --version)"
    exit 0
fi

# 检查源码包
if [ ! -f fio-3.33.tar.gz ]; then
    echo "错误：找不到 fio-3.33.tar.gz"
    exit 1
fi

# 解压
echo "解压源码..."
tar -xzf fio-3.33.tar.gz
cd fio-3.33

# 检查编译工具
if ! command -v make &> /dev/null; then
    echo "错误：需要安装 make"
    exit 1
fi

# 编译安装
echo "配置..."
./configure

echo "编译..."
make -j$(nproc)

echo "安装..."
make install

echo "验证..."
fio --version

echo "=== FIO 安装完成 ==="
```

---

## ✅ 验证安装

```bash
# 检查版本
fio --version

# 检查安装位置
which fio
ls -la $(which fio)

# 简单测试
fio --name=test --ioengine=libaio --rw=read --bs=4k --size=1M --numjobs=1
```

---

## 🎯 推荐操作流程

### 在联网机器上：

```bash
# 1. 准备部署目录
mkdir -p /tmp/ufsauto-deploy
cd /tmp/ufsauto-deploy

# 2. 下载 FIO 源码
wget https://github.com/axboe/fio/archive/refs/tags/fio-3.33.tar.gz

# 3. 复制 UFS Auto 项目
cp -r /workspace/projects/ufsauto ./

# 4. 创建安装脚本
cat > install-fio.sh << 'EOF'
#!/bin/bash
set -e
tar -xzf fio-3.33.tar.gz
cd fio-3.33
./configure && make -j$(nproc) && make install
fio --version
echo "FIO 安装完成!"
EOF
chmod +x install-fio.sh

# 5. 打包
cd /tmp
tar -czf ufsauto-complete-deploy.tar.gz ufsauto-deploy/

# 6. 传输到 U 盘
cp ufsauto-complete-deploy.tar.gz /media/usb/
```

### 在开发板上：

```bash
# 1. 解压部署包
cd /mapdata
tar -xzf /media/usb/ufsauto-complete-deploy.tar.gz
cd ufsauto-deploy

# 2. 安装 FIO
./install-fio.sh

# 3. 验证环境
cd ufsauto
python3 systest/bin/systest_cli.py check-env

# 4. 执行测试
python3 systest/bin/systest_cli.py run --suite performance
```

---

## 📝 注意事项

1. **编译依赖**：确保开发板有 gcc、make、libaio-dev
2. **安装位置**：FIO 默认安装到 `/usr/local/bin/fio`
3. **权限**：需要 root 权限安装
4. **空间**：编译过程需要约 100MB 临时空间

---

**准备好部署包后，我可以帮您创建自动化安装脚本！** ✅
