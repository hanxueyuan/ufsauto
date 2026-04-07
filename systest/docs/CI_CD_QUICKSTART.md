# CI/CD 环境配置快速指南

## 目标

确保 CI/CD 测试环境与开发板环境一致，减少"在我机器上能跑"的问题。

---

## 快速开始

### 1. 检查当前环境

```bash
cd ufsauto/systest
python3 bin/SysTest check-env -v
```

输出示例：
```
============================================================
UFS SysTest 环境检查
============================================================

✅ Python 版本：当前：3.10.12, 要求：≥3.10, 基线：3.10.12
✅ FIO 版本：当前：3.33, 要求：≥3.30, 基线：3.33
✅ Linux 内核版本：当前：5.15.0-76-generic, 要求：≥5.10, 基线：5.15.0
✅ Ubuntu 版本：当前：22.04.3 LTS, 基线：22.04
✅ 系统包：sg3-utils: 已安装
✅ 系统包：hdparm: 已安装
✅ Kernel 模块：ufshcd: 已加载
✅ 用户权限：用户：testuser, 组：testuser, disk, disk 组：✓, root: ✗
✅ 设备访问：/dev/ufs0: 可读写
✅ FIO 权限：FIO 可正常运行

============================================================
总计：9 项检查
通过：9/9
警告：0
错误：0

✅ 环境检查通过
```

---

## 环境配置步骤

### 方案 A：使用 Docker 镜像（推荐）

最一致的方式，确保每次测试环境完全相同。

#### 1. 构建镜像

```bash
cd ufsauto
docker build -t ufsauto/systest:1.0 -f Dockerfile.ci .
```

#### 2. 运行测试

```bash
docker run --rm -v /dev:/dev --privileged \
  ufsauto/systest:1.0 \
  "python3 /workspace/systest/bin/SysTest run --suite=performance --device=/dev/ufs0"
```

#### 3. CI/CD 集成

在 GitHub Actions 中：

```yaml
- name: Run tests in Docker
  run: |
    docker run --rm -v /dev:/dev --privileged \
      ghcr.io/${{ github.repository }}/systest:latest \
      "python3 /workspace/systest/bin/SysTest run --suite=performance"
```

---

### 方案 B：自托管 Runner

适用于需要访问实际 UFS 硬件的场景。

#### 1. 准备测试机器

使用与开发板相同的硬件/虚拟化环境：

- 相同的 SoC 平台（Qualcomm/MediaTek 等）
- 相同的 Linux 内核版本
- 相同的 UFS 驱动版本

#### 2. 安装依赖

```bash
# Ubuntu 22.04
sudo apt-get update
sudo apt-get install -y python3 python3-pip fio sg3-utils hdparm

# 安装 Python 依赖
pip3 install -r systest/requirements.txt
```

#### 3. 配置 GitHub Runner

```bash
# 下载 Runner
cd /opt
sudo mkdir actions-runner && cd actions-runner
curl -O -L https://github.com/actions/runner/releases/download/v2.311.0/actions-runner-linux-x64-2.311.0.tar.gz
tar xzf ./actions-runner-linux-x64-2.311.0.tar.gz

# 注册 Runner
./config.sh --url https://github.com/your-org/ufsauto --token YOUR_TOKEN

# 启动 Runner
./run.sh
```

---

### 方案 C：虚拟机/QEMU 模拟

当无法使用实际硬件时。

#### 1. 创建 QEMU 虚拟机

```bash
# 安装 QEMU
sudo apt-get install -y qemu-system-x86 qemu-utils

# 创建虚拟 UFS 设备（使用普通磁盘模拟）
qemu-img create -f qcow2 ufs_test.qcow2 10G

# 启动 VM
qemu-system-x86_64 \
  -hda ufs_test.qcow2 \
  -m 4G \
  -cpu host \
  -enable-kvm
```

#### 2. 在 VM 中安装测试环境

参考方案 B 的步骤。

---

## 环境对齐检查清单

### 开发板信息收集

在开发板上运行：

```bash
# 1. 系统信息
uname -a
cat /etc/os-release

# 2. 内核版本
uname -r
modinfo ufshcd

# 3. UFS 驱动信息
dmesg | grep -i ufs
ls -la /sys/class/ufs_device/

# 4. 工具版本
fio --version
python3 --version

# 5. 设备信息
lsblk
hdparm -I /dev/ufs0  # 如果有
```

保存输出到 `docs/dev-board-env.txt`。

### CI/CD 环境验证

在 CI/CD 环境运行相同命令，对比输出。

**关键对齐项：**

| 项目 | 开发板 | CI/CD | 容差 |
|------|--------|-------|------|
| Ubuntu 版本 | 22.04 | 22.04 | 必须一致 |
| Linux 内核 | 5.15.x | 5.15.x | 次版本一致 |
| fio 版本 | 3.33 | 3.33+ | 主版本一致 |
| Python | 3.10.x | 3.10+ | 主版本一致 |
| UFS 驱动 | ufshcd | ufshcd | 必须一致 |

---

## 性能基线校准

首次配置时，在开发板和 CI/CD 环境运行相同测试，建立性能基线。

### 步骤

1. **开发板测试**
   ```bash
   cd systest
   python3 bin/SysTest run --suite=performance --device=/dev/ufs0 --baseline
   ```

2. **CI/CD 测试**
   ```bash
   python3 bin/SysTest run --suite=performance --device=/dev/sda --baseline
   ```

3. **对比结果**
   ```bash
   python3 bin/SysTest compare-baseline \
     --dev results/board_20260322/ \
     --ci results/ci_20260322/
   ```

4. **调整阈值**

   如果性能差异 > 10%，更新 `config/production.json` 中的阈值：

   ```json
   {
     "thresholds": {
       "performance": {
         "seq_read_burst_001": {
           "metric": "bandwidth",
           "target": 2100,
           "unit": "MB/s",
           "tolerance": 0.10  // 调整容差
         }
       }
     }
   }
   ```

---

## 故障排查

### 问题 1: FIO 权限不足

**症状：**
```
fio: io_u error on file /dev/ufs0: Permission denied
```

**解决：**
```bash
# 添加用户到 disk 组
sudo usermod -aG disk $USER

# 或调整设备权限
sudo chmod 660 /dev/ufs0
sudo chown root:disk /dev/ufs0

# 重新登录生效
newgrp disk
```

### 问题 2: 内核模块缺失

**症状：**
```
modprobe: FATAL: Module ufshcd not found
```

**解决：**
```bash
# 检查内核配置
zcat /proc/config.gz | grep CONFIG_UFS

# 如果未编译，需要更换内核或使用开发板相同内核
```

### 问题 3: 性能差异过大

**症状：**
```
❌ 阈值未达标:
  - seq_read_burst_001: 1500.0 MB/s < 2100 MB/s
```

**解决：**

1. 检查 CI/CD 机器负载
2. 确认使用相同的 fio 参数
3. 检查磁盘类型（SSD vs HDD）
4. 调整阈值容差

---

## 维护

### 每月检查

```bash
# 运行环境审计
python3 bin/SysTest check-env --report

# 查看报告
cat env_check_report.json | jq '.checks[] | select(.passed == false)'
```

### 镜像更新

当开发板环境升级时：

1. 更新 `Dockerfile.ci` 中的版本
2. 重建镜像：`docker build -t ufsauto/systest:2.0 -f Dockerfile.ci .`
3. 推送：`docker push ghcr.io/your-org/systest:2.0`
4. 更新 CI/CD 配置

---

## 参考

- [ENVIRONMENT_SETUP.md](./ENVIRONMENT_SETUP.md) - 详细环境配置文档
- [Dockerfile.ci](../../Dockerfile.ci) - CI/CD 镜像配置
- [check_env.py](./check_env.py) - 环境检查脚本
