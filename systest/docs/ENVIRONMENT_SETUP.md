# UFS SysTest 测试环境配置指南

## 目标

确保 CI/CD 测试环境与目标开发板环境保持一致，包括：
- Linux 内核版本
- UFS 驱动版本
- 工具链版本（fio、sg3_utils 等）
- 系统配置和权限

---

## 环境要求

### 硬件环境（开发板）

```
- 平台：Qualcomm / MediaTek / Hisilicon 等 SoC
- UFS 版本：UFS 3.1 / 4.0
- 存储容量：≥ 128GB
- Linux 内核：≥ 5.10
```

### CI/CD 环境要求

```yaml
操作系统：Ubuntu 22.04 LTS (与开发板一致)
Linux 内核：≥ 5.15 (LTS)
Python: 3.10+
FIO: 3.33+
sg3_utils: 1.46+
```

---

## Docker 镜像配置

### 基础镜像选择

使用与开发板相同的基础镜像：

```dockerfile
# 如果开发板使用 Ubuntu 22.04
FROM ubuntu:22.04

# 如果开发板使用 Yocto/Buildroot，使用 QEMU 模拟
FROM ubuntu:22.04  # 基础系统 + QEMU
```

### Dockerfile 示例

见 `Dockerfile.ci` - 包含完整的测试环境配置

---

## 环境检查清单

### 运行前检查

```bash
# 1. 检查 Linux 内核版本
uname -r  # 应 ≥ 5.10

# 2. 检查 UFS 驱动
lsmod | grep ufs  # 应加载 ufshcd 模块

# 3. 检查设备节点
ls -la /dev/ufs* /dev/sd*  # 应有对应设备

# 4. 检查 fio 版本
fio --version  # 应 ≥ 3.33

# 5. 检查权限
id  # 应在 disk 组或有 root 权限
```

### 自动化检查脚本

```bash
# 运行环境检查
cd systest
python3 bin/SysTest check-env
```

---

## CI/CD 配置

### GitHub Actions

1. 使用自托管 Runner（推荐）
   - 部署在与开发板相同硬件/虚拟化环境
   - 预装所有依赖

2. 使用 Docker 镜像
   - 确保镜像版本与开发板环境匹配
   - 定期更新镜像

### Jenkins/GitLab CI

```yaml
# .gitlab-ci.yml 示例
stages:
  - check
  - test

variables:
  UFS_TEST_IMAGE: registry.example.com/ufsauto/systest:latest

environment_check:
  stage: check
  script:
    - python3 systest/bin/SysTest check-env
    - python3 systest/bin/SysTest validate-config

performance_test:
  stage: test
  script:
    - python3 systest/bin/SysTest run --suite=performance
  only:
    - master
    - develop
```

---

## 环境一致性验证

### 版本对齐

| 组件 | 开发板 | CI/CD | 容差 |
|------|--------|-------|------|
| Linux 内核 | 5.15.0 | 5.15.x | 次版本一致 |
| UFS 驱动 | ufshcd-pltfrm | 相同 | 完全一致 |
| fio | 3.33 | 3.33+ | 主版本一致 |
| Python | 3.10 | 3.10+ | 主版本一致 |

### 性能基线校准

首次部署时，在开发板和 CI/CD 环境运行相同测试：

```bash
# 开发板
python3 bin/SysTest run --suite=performance --device=/dev/ufs0 --baseline

# CI/CD
python3 bin/SysTest run --suite=performance --device=/dev/ufs0 --baseline

# 对比结果
python3 bin/SysTest compare-baseline --dev results/board/ --ci results/ci/
```

允许的性能差异：≤ 10%

---

## 故障排查

### 常见问题

1. **设备权限不足**
   ```bash
   sudo usermod -aG disk $USER
   sudo chmod 660 /dev/ufs0
   ```

2. **fio 版本不匹配**
   ```bash
   # 从源码编译特定版本
   git clone https://github.com/axboe/fio.git
   cd fio && git checkout fio-3.33
   ./configure && make && sudo make install
   ```

3. **内核模块缺失**
   ```bash
   sudo modprobe ufshcd
   sudo modprobe ufs-qcom  # 根据平台
   ```

---

## 维护

### 镜像更新

当开发板环境升级时：

1. 更新 `Dockerfile.ci`
2. 重建镜像：`docker build -t ufsauto/systest:2.0 -f Dockerfile.ci .`
3. 推送镜像：`docker push ufsauto/systest:2.0`
4. 更新 CI/CD 配置引用新镜像

### 定期验证

每月运行一次环境一致性检查：

```bash
python3 bin/SysTest audit-environment --report
```

---

## 参考文档

- [FIO 文档](https://fio.readthedocs.io/)
- [Linux UFS 驱动文档](https://www.kernel.org/doc/html/latest/scsi/ufs.html)
- [JEDEC UFS 标准](https://www.jedec.org/standards-documents/results/jesd220)
