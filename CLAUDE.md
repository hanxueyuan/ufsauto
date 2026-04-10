# UFS Auto 项目开发规范

**Claude Code 专用配置文件**

---

## 🎯 核心原则

1. **导入路径** - 使用完整路径 `systest.core.*` 和 `systest.tools.*`
2. **常量定义** - 所有魔法数字定义在 `constants.py`
3. **日志规范** - 统一使用 logger，毫秒时间戳 + 文件行号
4. **错误处理** - 包含调试建议和堆栈跟踪

---

## ⛔ 禁止事项

- ❌ 不使用相对导入（如 `from runner import`）
- ❌ 不硬编码魔法数字（如 `2.0`、`100`）
- ❌ 不创建空 `error.log` 文件
- ❌ 不循环执行测试用例（每个测试执行 1 次）
- ❌ 不使用 `print()` 重复 logger 输出

---

## ✅ 验证要求

开发完成后必须通过以下验证：

```bash
# 1. 语法检查
python3 -m py_compile systest/core/*.py

# 2. 导入测试
python3 -c "from systest.core.runner import TestRunner; print('✅ 导入成功')"

# 3. 功能测试
python3 systest/bin/systest.py run --test t_perf_SeqReadBurst_001
```

---

## 📋 开发流程

1. **接收任务** - 理解需求和验收标准
2. **代码开发** - 遵循本规范
3. **代码验证** - 通过所有验证
4. **提交推送** - 清晰提交信息，推送到 GitHub

---

## 📚 相关文档

- **项目原则**: SOUL.md（人类阅读）
- **快速上手**: README.md
- **Agent 规范**: CODING_AGENT.md

---

**最后更新**: 2026-04-11  
**状态**: Production Ready ✅
