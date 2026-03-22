# 开发板环境配置

**最后更新**: 2026-03-22  
**来源**: 夜间学习计划文档

---

## 硬件配置

| 项目 | 配置 |
|------|------|
| 架构 | ARM64 (aarch64) |
| 平台 | 车规级 SoC |
| UFS 版本 | UFS 3.1 |
| 存储容量 | ≥ 128GB |

---

## 软件环境

### 操作系统

```bash
$ cat /etc/os-release
PRETTY_NAME="Debian GNU/Linux 12 (bookworm)"
NAME="Debian GNU/Linux"
VERSION_ID="12"
VERSION="12 (bookworm)"
ID=debian
```

### 内核版本

```bash
$ uname -r
6.1.0-xx-arm64  # Debian 12 默认内核
```

### Python 版本

```bash
$ python3 --version
Python 3.11.x  # Debian 12 默认版本
```

### FIO 版本

```bash
$ fio --version
fio-3.33
```

---

## 已安装工具

| 工具 | 版本 | 用途 |
|------|------|------|
| fio | 3.33 | 性能测试 |
| sg3-utils | 1.46+ | SCSI/UFS 工具 |
| hdparm | 9.65+ | 硬盘参数工具 |
| lsblk | 2.38+ | 块设备列表 |
| ufs-utils | 最新 | UFS 专用工具 |

---

## 设备节点

```bash
# UFS 设备
/dev/ufs0          # 主 UFS 设备
/sys/block/sda/    # 块设备 sysfs 路径
/sys/class/ufs_device/  # UFS 设备类

# 典型路径
ls -la /dev/ufs0
# brw-rw---- 1 root disk 179, 0 Mar 21 10:00 /dev/ufs0
```

---

## 权限配置

### 用户组

```bash
# 测试用户需要在 disk 组
groups testuser
# testuser : testuser disk sudo
```

### 设备权限

```bash
# 推荐权限设置
ls -la /dev/ufs0
# brw-rw---- 1 root disk 179, 0 Mar 21 10:00 /dev/ufs0

# 或添加 udev 规则
cat /etc/udev/rules.d/99-ufs.rules
# KERNEL=="ufs0", GROUP="disk", MODE="0660"
```

---

## 内核模块

```bash
# 加载的 UFS 相关模块
$ lsmod | grep ufs
ufshcd                102400  0
ufshcd_core           81920  1 ufshcd
scsi_mod             245760  3 ufs,ufshcd,libata
```

---

## 性能基线

### 顺序读 Burst

```
目标：≥ 2100 MB/s
实测：_______ MB/s
```

### 顺序写 Burst

```
目标：≥ 1650 MB/s
实测：_______ MB/s
```

### 随机读 Burst

```
目标：≥ 200 KIOPS
实测：_______ KIOPS
```

### 随机写 Burst

```
目标：≥ 330 KIOPS
实测：_______ KIOPS
```

---

## 环境检查

在开发板上运行：

```bash
cd ufsauto/systest
python3 bin/SysTest check-env -v
```

预期输出：
```
✅ Python 版本：当前：3.11.x, 要求：≥3.11, 基线：3.11
✅ FIO 版本：当前：3.33, 要求：≥3.33, 基线：3.33
✅ Linux 内核版本：当前：6.1.0-xx-arm64, 要求：≥6.1, 基线：6.1
✅ Debian 版本：当前：12, 基线：12
✅ CPU 架构：当前：aarch64, 基线：arm64
✅ 系统包：sg3-utils: 已安装
✅ 系统包：hdparm: 已安装
✅ Kernel 模块：ufshcd: 已加载
✅ 用户权限：disk 组：✓
✅ 设备访问：/dev/ufs0: 可读写
✅ FIO 权限：FIO 可正常运行
```

---

## CI/CD 对齐

### Docker 镜像

使用 `Dockerfile.ci` 构建与开发板一致的环境：

```bash
docker build -t ufsauto/systest:1.0 -f Dockerfile.ci .
```

镜像配置：
- 基础镜像：debian:12-slim
- Python: 3.11
- FIO: 3.33
- 架构：arm64 (或 x86_64 模拟)

### GitHub Actions

使用自托管 Runner 或 QEMU 模拟 ARM 环境：

```yaml
runs-on: [self-hosted, arm64]
# 或
runs-on: ubuntu-22.04  # x86_64，性能测试使用 QEMU
```

---

## 故障排查

### 问题 1: 设备权限

```bash
# 症状：Permission denied
# 解决：
sudo usermod -aG disk $USER
sudo chmod 660 /dev/ufs0
newgrp disk
```

### 问题 2: 内核模块缺失

```bash
# 症状：modprobe: FATAL: Module ufshcd not found
# 解决：检查内核配置
zcat /proc/config.gz | grep CONFIG_UFS
# 需要 CONFIG_UFS=y 或 CONFIG_UFS=m
```

### 问题 3: FIO 版本不匹配

```bash
# 症状：fio 版本不是 3.33
# 解决：从源码编译
wget https://github.com/axboe/fio/archive/fio-3.33.tar.gz
tar -xzf fio-3.33.tar.gz
cd fio-fio-3.33
./configure && make && sudo make install
```

---

## 参考文档

- [ENVIRONMENT_SETUP.md](./ENVIRONMENT_SETUP.md) - 环境配置指南
- [CI_CD_QUICKSTART.md](./CI_CD_QUICKSTART.md) - CI/CD 快速指南
- [Dockerfile.ci](../../Dockerfile.ci) - Docker 镜像配置
