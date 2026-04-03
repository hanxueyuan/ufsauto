# 开发板环境配置已更新

## 📋 开发板实际环境

根据文档记录 (`docs/night-learning-plan-20260320.md`)，开发板配置如下：

### 硬件
- **架构**: ARM64 (aarch64)
- **平台**: 车规级 SoC
- **UFS 版本**: UFS 3.1
- **存储**: ≥ 128GB

### 软件
- **操作系统**: Debian 12 (bookworm)
- **Linux 内核**: 6.1.x (Debian 12 默认)
- **Python**: 3.11.x (Debian 12 默认)
- **FIO**: 3.33

---

## ✅ 已完成的更新

### 1. 环境检查脚本 (`systest/bin/check_env.py`)

**更新内容**:
```python
BASELINE = {
    "kernel_version": "6.1",        # Debian 12 默认内核
    "fio_version": "3.33",          # 开发板 FIO 版本
    "python_version": "3.11",       # Debian 12 默认 Python
    "debian_version": "12",         # Debian 12 (bookworm)
    "arch": "arm64",                # ARM64 架构
}

ENV_REQUIREMENTS = {
    "python_min_version": (3, 11),  # 从 3.10 升级到 3.11
    "fio_min_version": "3.33",      # 从 3.30 升级到 3.33
    "kernel_min_version": (6, 1),   # 从 5.10 升级到 6.1
    ...
}
```

**新增检查项**:
- ✅ Debian 版本检查 (替代 Ubuntu 检查)
- ✅ CPU 架构检查 (arm64 vs x86_64)

### 2. Docker 镜像 (`Dockerfile.ci`)

**更新内容**:
```dockerfile
# 基础镜像从 Ubuntu 22.04 改为 Debian 12
FROM debian:12-slim  # 之前：ubuntu:22.04

# 添加 Debian 版本环境变量
ENV UFS_TEST_DEBIAN_VERSION=12
```

**关键变化**:
| 项目 | 之前 | 现在 |
|------|------|------|
| 基础镜像 | ubuntu:22.04 | debian:12-slim |
| Python | 3.10 | 3.11 |
| 内核要求 | 5.15 | 6.1 |
| 架构 | x86_64 | arm64 |

### 3. 环境配置文档 (`systest/docs/ENVIRONMENT_SETUP.md`)

**更新内容**:
```yaml
# 开发板环境
平台：ARM64 (车规级 SoC)
操作系统：Debian 12 (Bookworm)
Linux 内核：≥ 6.1
Python: 3.11
FIO: 3.33
```

### 4. 新增开发板环境文档 (`systest/docs/DEV_BOARD_ENV.md`)

**包含内容**:
- 硬件配置详情
- 软件环境版本
- 已安装工具列表
- 设备节点路径
- 权限配置说明
- 内核模块信息
- 性能基线模板
- 故障排查指南

---

## 🔍 环境检查测试

### 在开发板上运行

```bash
cd systest
python3 bin/SysTest check-env -v
```

**预期输出** (开发板环境):
```
============================================================
UFS SysTest 环境检查
============================================================

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

总计：11 项检查
通过：11/11
✅ 环境检查通过
```

### 在 CI/CD 环境运行

**Docker 环境** (使用 `Dockerfile.ci` 构建):
```bash
docker build -t ufsauto/systest:1.0 -f Dockerfile.ci .
docker run --rm ufsauto/systest:1.0 "python3 /workspace/systest/bin/SysTest check-env -v"
```

**GitHub Actions**:
- 使用自托管 ARM64 Runner → ✅ 完全一致
- 使用 Ubuntu Runner → ⚠️ 架构不同，性能测试需要 QEMU

---

## 📊 环境对齐检查清单

| 项目 | 开发板 | CI/CD (Docker) | 状态 |
|------|--------|----------------|------|
| 操作系统 | Debian 12 | Debian 12 | ✅ 一致 |
| Python | 3.11 | 3.11 | ✅ 一致 |
| FIO | 3.33 | 3.33 | ✅ 一致 |
| Linux 内核 | 6.1 | 6.1+ | ✅ 一致 |
| 架构 | ARM64 | ARM64 | ✅ 一致 |
| 工具链 | sg3-utils, hdparm | sg3-utils, hdparm | ✅ 一致 |

---

## 🚀 使用指南

### 1. 在开发板上验证环境

```bash
# 检查环境
python3 bin/SysTest check-env -v

# 生成报告
python3 bin/SysTest check-env --report

# 查看报告
cat env_check_report.json | jq
```

### 2. 构建 Docker 镜像

```bash
cd ufsauto
docker build -t ufsauto/systest:1.0 -f Dockerfile.ci .
```

### 3. 运行测试

```bash
# Docker 环境
docker run --rm -v /dev:/dev --privileged \
  ufsauto/systest:1.0 \
  "python3 /workspace/systest/bin/SysTest run --suite=performance --device=/dev/ufs0"

# 开发板环境
python3 bin/SysTest run --suite=performance --device=/dev/ufs0 -v
```

### 4. 性能基线校准

```bash
# 开发板
python3 bin/SysTest run --suite=performance --baseline
cp -r results/baseline_dev_board/ results/

# CI/CD
python3 bin/SysTest run --suite=performance --baseline
cp -r results/baseline_ci/ results/

# 对比
python3 -c "
import json
with open('results/baseline_dev_board/results.json') as f:
    dev = json.load(f)
with open('results/baseline_ci/results.json') as f:
    ci = json.load(f)
# 对比逻辑...
"
```

---

## 📁 文件变更

### 修改的文件
- `systest/bin/check_env.py` - 更新基线配置和检查项
- `Dockerfile.ci` - 改用 Debian 12 基础镜像
- `systest/docs/ENVIRONMENT_SETUP.md` - 更新环境要求

### 新增的文件
- `systest/docs/DEV_BOARD_ENV.md` - 开发板完整环境配置文档

### Git 提交
```
b65dd50 fix: 更新环境基线配置为开发板实际环境 (Debian 12, ARM64)
5af8b1f feat: 添加 CI/CD 环境配置和检查工具
```

---

## ⚠️ 注意事项

### 1. 架构差异

如果 CI/CD 使用 x86_64 Runner：
- 功能测试：✅ 可以运行
- 性能测试：⚠️ 数据仅供参考，需 QEMU 模拟 ARM
- 建议：使用自托管 ARM64 Runner

### 2. 内核版本

Debian 12 默认内核 6.1，如果开发板使用其他版本：
```bash
# 检查开发板内核
uname -r

# 更新基线配置
# 编辑 systest/bin/check_env.py
BASELINE["kernel_version"] = "x.x"
```

### 3. Python 版本

Debian 12 默认 Python 3.11，如果开发板使用其他版本：
```bash
# 检查开发板 Python
python3 --version

# 更新基线配置
BASELINE["python_version"] = "3.x"
```

---

## 🔗 参考文档

- [DEV_BOARD_ENV.md](./DEV_BOARD_ENV.md) - 开发板完整环境配置
- [ENVIRONMENT_SETUP.md](./ENVIRONMENT_SETUP.md) - 环境配置指南
- [CI_CD_QUICKSTART.md](./CI_CD_QUICKSTART.md) - CI/CD 快速指南
- [Dockerfile.ci](../../Dockerfile.ci) - Docker 镜像配置
- [night-learning-plan-20260320.md](../../docs/night-learning-plan-20260320.md) - 原始环境信息

---

**更新时间**: 2026-03-22  
**版本**: v1.1.0
