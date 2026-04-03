# 临时文件清理指南

## 🧹 自动清理机制

### 1. 测试框架自动清理
- 所有测试用例继承 `TestCase` 基类
- 基类 `teardown()` 方法自动删除测试文件
- 测试完成后不留临时文件

### 2. 测试目录自动管理
- 自动选择最大可用空间挂载点作为测试目录
- 测试文件统一放在 `ufs_test/` 目录下
- 测试结束后自动清理

## 📁 需要清理的文件类型

### 临时文件
```
*.tmp          # 临时文件
*.temp         # 临时文件
*.log          # 日志文件
*.bak          # 备份文件
*.backup       # 备份文件
*.swp          # Vim 交换文件
*~             # Emacs 临时文件
```

### Python 临时文件
```
__pycache__/   # Python 缓存目录
*.pyc          # Python 编译文件
*.pyo          # Python 优化编译文件
*.pyd          # Python 动态库
```

### 测试结果文件
```
results/       # 测试结果目录
systest/results/  # 测试结果目录
logs/          # 日志目录
systest/logs/  # 日志目录
*.log          # 单个日志文件
```

### 环境检查文件
```
env_check_report.json    # 环境检查报告
env_report.json          # 环境报告
compare_report.json      # 性能对比报告
```

## 🚀 清理脚本使用

### 自动清理
```bash
# 预览将要删除的文件
python3 cleanup_temp_files.py --dry-run

# 实际执行清理
python3 cleanup_temp_files.py
```

### 手动清理
```bash
# 清理 Python 缓存
find . -name "__pycache__" -exec rm -rf {} +
find . -name "*.pyc" -delete
find . -name "*.pyo" -delete

# 清理测试结果
rm -rf results/
rm -rf systest/results/
rm -rf logs/
rm -rf systest/logs/

# 清理临时测试文件
find . -name "ufs_test_*" -delete
find . -name "test_*" -delete
```

## ⚠️ 注意事项

1. **保留重要文件**：
   - `.gitignore` - 不要删除
   - `README.md` - 不要删除
   - `systest/config/default.json` - 不要删除

2. **安全删除**：
   - 删除前确认不是源代码文件
   - 避免删除 `.git` 目录

3. **定期清理**：
   - 测试结果文件会累积，建议定期清理
   - 日志文件会占用空间，建议定期清理

## 📋 检查清单

- [ ] 临时文件已清理
- [ ] 日志文件已清理
- [ ] Python 缓存已清理
- [ ] 测试结果已清理
- [ ] 备份文件已清理
- [ ] 重要源文件保留

## 📦 .gitignore 完整配置

当前 .gitignore 已包含以下规则：

```gitignore
# Python
__pycache__/
*.py[cod]
*$py.class
**/__pycache__/**/*.pyc

# 测试结果
systest/results/
systest/logs/
*.log

# 临时文件
*.tmp
*.temp
*.bak
*.backup
*.swp
*~

# 环境检查报告
env_check_report.json
env_report.json

# IDE
.idea/
.vscode/
```

---

**最后更新**: 2026-04-03  
**维护者**: UFS Auto 项目组