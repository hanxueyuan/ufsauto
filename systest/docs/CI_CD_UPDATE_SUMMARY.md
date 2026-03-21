# CI/CD 环境配置更新总结

## 问题

你提到"模拟实际环境"不是让我创建软件模拟器，而是指 **CI/CD 环境配置应该与实际开发板环境接近**，包括：

- ✅ Linux 系统环境（内核版本、发行版）
- ✅ UFS 驱动版本
- ✅ 工具链版本（fio、sg3_utils 等）
- ✅ 权限配置

## 已完成的更新

### 1. 📄 环境配置文档

**文件：** `systest/docs/ENVIRONMENT_SETUP.md`

完整的环境配置指南，包括：
- 硬件环境要求
- CI/CD 环境要求
- Docker 镜像配置
- 环境检查清单
- 故障排查指南

### 2. 🐳 Docker 镜像配置

**文件：** `Dockerfile.ci`

创建与开发板一致的测试环境镜像：
- Ubuntu 22.04 LTS 基础镜像
- FIO 3.33（可配置版本）
- sg3_utils、hdparm 等工具
- Python 3.10+
- 预装所有测试依赖

**使用方法：**
```bash
# 构建镜像
docker build -t ufsauto/systest:1.0 -f Dockerfile.ci .

# 运行测试
docker run --rm -v /dev:/dev --privileged \
  ufsauto/systest:1.0 \
  "python3 /workspace/systest/bin/SysTest run --suite=performance"
```

### 3. 🔍 环境检查脚本

**文件：** `systest/bin/check_env.py`

自动化检查 CI/CD 环境与开发板环境的一致性：

**检查项目：**
- ✅ Python 版本
- ✅ FIO 版本
- ✅ Linux 内核版本
- ✅ Ubuntu 版本
- ✅ 系统包（sg3-utils、hdparm）
- ✅ Kernel 模块（ufshcd）
- ✅ 用户权限（disk 组）
- ✅ 设备访问权限
- ✅ FIO 运行权限

**使用方法：**
```bash
cd systest
python3 bin/SysTest check-env -v
```

**输出示例：**
```
============================================================
UFS SysTest 环境检查
============================================================

✅ Python 版本：当前：3.10.12, 要求：≥3.10, 基线：3.10.12
✅ FIO 版本：当前：3.33, 要求：≥3.30, 基线：3.33
✅ Linux 内核版本：当前：5.15.0-76-generic, 要求：≥5.10, 基线：5.15.0
✅ Ubuntu 版本：当前：22.04.3 LTS, 基线：22.04
❌ 系统包：sg3-utils: 未安装
❌ 用户权限：disk 组：✗

总计：9 项检查
通过：7/9
❌ 环境检查失败，请修复以下问题:
  - 用户权限：disk 组：✗
```

### 4. 📝 CI/CD 快速指南

**文件：** `systest/docs/CI_CD_QUICKSTART.md`

快速上手指南，包括：
- 三种部署方案（Docker、自托管 Runner、QEMU）
- 环境对齐检查清单
- 性能基线校准步骤
- 故障排查

### 5. 🔄 更新 GitHub Actions

**文件：** `.github/workflows/ci.yml`

主要改进：
- ✅ 固定 Ubuntu 版本（22.04）
- ✅ 添加环境检查作业
- ✅ 分离单元测试和性能测试
- ✅ 支持 dry-run 和 hardware 两种模式
- ✅ 自动构建和推送 Docker 镜像
- ✅ 性能阈值自动检查
- ✅ 失败通知

### 6. 🔧 更新 SysTest 入口

**文件：** `systest/bin/SysTest`

添加新命令：
```bash
SysTest check-env -v        # 检查环境配置
SysTest check-env --report  # 生成 JSON 报告
```

---

## 下一步行动

### 1. 收集开发板环境信息

在开发板上运行：
```bash
# 保存输出到 docs/dev-board-env.txt
uname -a
cat /etc/os-release
uname -r
modinfo ufshcd
fio --version
python3 --version
dmesg | grep -i ufs
```

### 2. 更新基线配置

编辑 `systest/bin/check_env.py` 中的 `BASELINE` 字典：

```python
BASELINE = {
    "kernel_version": "5.15.0",      # 开发板内核版本
    "fio_version": "3.33",           # 开发板 fio 版本
    "python_version": "3.10.12",     # 开发板 Python 版本
    "ubuntu_version": "22.04",       # 开发板 Ubuntu 版本
}
```

### 3. 首次环境校准

在开发板和 CI/CD 环境分别运行：
```bash
python3 bin/SysTest run --suite=performance --baseline
```

对比结果，调整 `config/production.json` 中的阈值。

### 4. 部署自托管 Runner（可选）

如果需要访问实际 UFS 硬件：

1. 准备与开发板相同的硬件
2. 安装 GitHub Runner
3. 配置 Docker 或本地环境

---

## 文件结构

```
ufsauto/
├── Dockerfile.ci                          # 新增：CI/CD 镜像配置
├── .github/workflows/
│   └── ci.yml                             # 更新：GitHub Actions 配置
└── systest/
    ├── bin/
    │   ├── SysTest                        # 更新：添加 check-env 命令
    │   └── check_env.py                   # 新增：环境检查脚本
    ├── docs/
    │   ├── ENVIRONMENT_SETUP.md           # 新增：环境配置指南
    │   └── CI_CD_QUICKSTART.md            # 新增：快速指南
    └── config/
        └── production.json                # 现有：性能阈值配置
```

---

## 关键改进

| 改进项 | 之前 | 现在 |
|--------|------|------|
| 环境一致性 | ❌ 未检查 | ✅ 自动化检查 |
| 镜像管理 | ❌ 无 | ✅ Docker 镜像 |
| 版本对齐 | ❌ 手动 | ✅ 基线配置 |
| 故障排查 | ❌ 困难 | ✅ 详细报告 |
| CI/CD 流程 | ❌ 基础 | ✅ 完整流程 |

---

## 测试验证

运行环境检查：
```bash
cd ufsauto/systest
python3 bin/SysTest check-env -v
```

运行 dry-run 测试：
```bash
python3 bin/SysTest run --suite=performance --dry-run
```

构建 Docker 镜像：
```bash
cd ..
docker build -t ufsauto/systest:1.0 -f Dockerfile.ci .
```

---

## 参考文档

- [ENVIRONMENT_SETUP.md](./systest/docs/ENVIRONMENT_SETUP.md) - 详细环境配置
- [CI_CD_QUICKSTART.md](./systest/docs/CI_CD_QUICKSTART.md) - 快速开始指南
- [Dockerfile.ci](./Dockerfile.ci) - Docker 镜像配置
