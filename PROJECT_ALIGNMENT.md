# UFS 项目本地路径与 GitHub 仓库对齐文档

**更新时间**: 2026-03-20  
**项目**: UFS 3.1 车规级存储系统测试

---

## 📁 本地项目结构

### 根目录
```
/home/gem/workspace/agent/workspace/
├── ufsauto/                    # UFS 测试自动化项目
│   ├── .git/                   # Git 仓库
│   ├── docs/                   # 项目文档
│   ├── examples/               # 示例代码
│   └── systest/               # 系统测试框架（新增）
│       ├── bin/               # 可执行脚本
│       ├── core/              # 核心引擎
│       ├── suites/            # 测试套件
│       ├── config/            # 配置文件
│       ├── results/           # 测试结果
│       └── README.md          # 框架文档
```

### 关键路径
| 用途 | 本地路径 | 说明 |
|------|----------|------|
| **项目根目录** | `/home/gem/workspace/agent/workspace/ufsauto/` | Git 仓库根目录 |
| **测试框架** | `/home/gem/workspace/agent/workspace/ufsauto/systest/` | SysTest 框架 |
| **测试结果** | `/home/gem/workspace/agent/workspace/ufsauto/systest/results/` | 测试输出 |
| **配置文件** | `/home/gem/workspace/agent/workspace/ufsauto/systest/config/` | 配置目录 |
| **测试套件** | `/home/gem/workspace/agent/workspace/ufsauto/systest/suites/` | 测试用例 |

---

## 🌐 GitHub 仓库信息

### 仓库详情
| 项目 | 信息 |
|------|------|
| **仓库地址** | https://github.com/hanxueyuan/ufsauto |
| **仓库名称** | `hanxueyuan/ufsauto` |
| **分支** | `master` |
| **协议** | HTTPS（带 Token 认证） |
| **最近提交** | `6d0b418` - docs: 完成 4 周 UFS 3.1 加速学习计划 |

### Git 配置
```ini
[remote "origin"]
    url = https://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@github.com/hanxueyuan/ufsauto.git
    fetch = +refs/heads/*:refs/remotes/origin/*

[branch "master"]
    remote = origin
    merge = refs/heads/master
```

### Git 操作示例
```bash
# 进入项目目录
cd /home/gem/workspace/agent/workspace/ufsauto

# 查看状态
git status

# 拉取最新代码
git pull origin master

# 提交更改
git add systest/
git commit -m "feat: 完成 SysTest 框架 MVP"
git push origin master

# 查看提交历史
git log --oneline -10
```

---

## 🔄 同步策略

### 本地 → GitHub
```bash
# 1. 提交 systest 框架
cd /home/gem/workspace/agent/workspace/ufsauto
git add systest/
git commit -m "feat: 添加 SysTest 测试框架 MVP"
git push origin master

# 2. 提交测试结果（可选）
git add systest/results/
git commit -m "test: 添加性能测试结果"
git push origin master
```

### GitHub → 本地
```bash
# 拉取他人提交
cd /home/gem/workspace/agent/workspace/ufsauto
git pull origin master

# 强制同步（谨慎使用）
git fetch origin
git reset --hard origin/master
```

---

## 🏗️ CI/CD 环境配置

### 当前状态
**⚠️ 未配置 CI/CD**

GitHub 仓库目前没有 `.github/workflows/` 目录，需要配置 CI/CD。

### 推荐 CI/CD 方案

#### 方案 A: GitHub Actions（推荐）

**文件**: `.github/workflows/test.yml`

```yaml
name: SysTest CI

on:
  push:
    branches: [ master ]
  pull_request:
    branches: [ master ]

jobs:
  test:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.11'
    
    - name: Install FIO
      run: |
        sudo apt-get update
        sudo apt-get install -y fio
    
    - name: Run Framework Tests
      run: |
        cd systest
        python3 test_framework.py
    
    - name: Run Performance Tests (Mock)
      run: |
        cd systest
        python3 bin/SysTest run --suite=performance --dry-run
    
    - name: Upload Test Results
      uses: actions/upload-artifact@v3
      with:
        name: test-results
        path: systest/results/
```

#### 方案 B: GitLab CI（如迁移到 GitLab）

**文件**: `.gitlab-ci.yml`

```yaml
stages:
  - test
  - report

test:
  stage: test
  image: python:3.11
  script:
    - apt-get update && apt-get install -y fio
    - cd systest
    - python3 test_framework.py
    - python3 bin/SysTest run --suite=performance --dry-run
  artifacts:
    paths:
      - systest/results/
    expire_in: 1 week
```

### CI/CD 配置步骤

1. **创建 workflows 目录**
   ```bash
   cd /home/gem/workspace/agent/workspace/ufsauto
   mkdir -p .github/workflows
   ```

2. **添加 workflow 文件**
   ```bash
   # 创建 test.yml（见上方配置）
   vim .github/workflows/test.yml
   ```

3. **提交并推送**
   ```bash
   git add .github/workflows/
   git commit -m "ci: 添加 GitHub Actions CI 配置"
   git push origin master
   ```

4. **验证 CI/CD**
   - 访问 https://github.com/hanxueyuan/ufsauto/actions
   - 查看 workflow 运行状态
   - 下载测试报告 artifacts

---

## 📊 项目对齐检查清单

### ✅ 已完成
- [x] 本地 Git 仓库初始化
- [x] GitHub 远程仓库配置
- [x] 基础文档（README.md）
- [x] SysTest 框架 MVP
- [x] 测试用例（1 个）

### ⏳ 待完成
- [ ] CI/CD 配置（GitHub Actions）
- [ ] 剩余 8 个性能测试用例
- [ ] QoS 测试套件
- [ ] 失效分析引擎
- [ ] 完整文档（API Reference）

---

## 🎯 下一步行动

### 1. 提交当前代码到 GitHub
```bash
cd /home/gem/workspace/agent/workspace/ufsauto
git status
git add systest/
git commit -m "feat: SysTest 框架 MVP 完成"
git push origin master
```

### 2. 配置 CI/CD
```bash
mkdir -p .github/workflows
# 创建 test.yml 文件（见上方配置）
git add .github/workflows/
git commit -m "ci: 添加 GitHub Actions 配置"
git push origin master
```

### 3. 验证 CI 运行
- 访问 GitHub Actions 页面
- 确认测试通过
- 查看测试报告

---

## 📞 联系信息

| 项目 | 信息 |
|------|------|
| **仓库所有者** | hanxueyuan |
| **仓库地址** | https://github.com/hanxueyuan/ufsauto |
| **本地路径** | `/home/gem/workspace/agent/workspace/ufsauto/` |
| **项目负责人** | 待确认 |

---

**最后更新**: 2026-03-20  
**状态**: 开发中
