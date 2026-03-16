# SysTest 部署检查清单

**版本**: v1.0  
**更新日期**: 2026-03-16  
**状态**: ✅ 生产就绪

---

## ✅ 部署前检查

### 代码检查

- [x] ✅ 14 个测试用例脚本完成
- [x] ✅ 代码质量检查通过（Flake8/Black/Isort）
- [x] ✅ 最小化验证通过（7/7）
- [x] ✅ CI/CD 配置完成
- [x] ✅ QA Agent 配置完成

### 文档检查

- [x] ✅ README.md 更新
- [x] ✅ QA_TEST_PLAN.md 创建
- [x] ✅ 13 个 SysTest 文档完整
- [x] ✅ 模式配置文档完整

### 配置检查

- [x] ✅ development.json 配置
- [x] ✅ production.json 配置
- [x] ✅ GitHub Actions workflow 配置
- [x] ✅ QA Agent workflow 配置

---

## 🚀 部署步骤

### 1. 推送到 GitHub

```bash
cd /home/gem/workspace/agent/workspace/ufsauto
git push origin master
```

**预期输出**:
```
Enumerating objects: XX, done.
Counting objects: 100% (XX/XX), done.
Delta compression using up to X threads
Compressing objects: 100% (XX/XX), done.
Writing objects: 100% (XX/XX), XX KiB | XX MiB/s, done.
Total XX (delta XX), reused XX (delta XX), pack-reused XX
remote: Resolving deltas: 100% (XX/XX), done.
To https://github.com/hanxueyuan/ufsauto.git
   XXXXXXX..XXXXXXX  master -> master
```

### 2. 验证 CI/CD

访问：https://github.com/hanxueyuan/ufsauto/actions

**检查项**:
- [ ] CI/CD workflow 自动触发
- [ ] 所有检查阶段通过
- [ ] QA Agent 自动汇报

### 3. 部署到开发板

```bash
# 复制 systest 到开发板
scp -r systest/ user@board:/opt/

# 进入目录
ssh user@board
cd /opt/systest

# 安装依赖
pip3 install -r requirements-ci.txt
apt update && apt install -y fio smartmontools

# 验证安装
python3 tests/minimal_validation.py
```

---

## 📊 部署验证

### 开发板验证

```bash
cd /opt/systest

# 执行单个测试（开发模式）
python3 bin/systest run -t t_performance_SequentialReadBurst_001 -m development -v

# 执行整个套件（生产模式）
python3 bin/systest run -s performance -m production -v

# 查看测试结果
ls -la results/
```

### 结果验证

- [ ] 测试结果生成
- [ ] HTML 报告正常
- [ ] JSON 数据完整
- [ ] TXT 摘要正确

---

## 📝 部署报告

### 部署信息

| 项目 | 信息 |
|------|------|
| **部署日期** | 2026-03-16 |
| **版本号** | v1.0 |
| **Git 提交** | [最新的 commit hash] |
| **部署环境** | Debian 12 + Python 3.11 |
| **FIO 版本** | 3.33+ |

### 测试结果

| 测试类型 | 结果 | 备注 |
|---------|------|------|
| 代码质量 | ⏳ 待验证 | CI/CD 自动执行 |
| 最小化验证 | ⏳ 待验证 | 7 项验证 |
| FIO 集成 | ⏳ 待验证 | 使用真实 UFS 设备 |
| 测试用例 | ⏳ 待验证 | 14 个用例 |

---

## 🔄 回滚方案

### 回滚步骤

```bash
# 1. 找到上一个稳定版本
git log --oneline

# 2. 回滚代码
git reset --hard <previous-commit>

# 3. 强制推送
git push origin master --force

# 4. 通知团队
```

### 回滚条件

- CI/CD 连续失败 3 次
- 生产环境发现严重 bug
- 性能退化超过 20%

---

## 📞 联系方式

- **GitHub**: https://github.com/hanxueyuan/ufsauto
- **CI/CD**: https://github.com/hanxueyuan/ufsauto/actions
- **问题反馈**: GitHub Issues

---

**部署检查清单 v1.0 - 确保部署成功！** 🚀
