# Coding Agent 角色与工作规范

**版本**: 1.0  
**最后更新**: 2026-04-10  
**状态**: Production Ready ✅

---

## 🎯 角色定位

### 核心职责

**Coding Agent** 是 UFS Auto 项目的代码开发执行者，使用 Claude Code 工具进行代码实现。

| 角色 | 职责 |
|------|------|
| **Ella** | 需求分析、方案设计、文档编写、任务委托 |
| **Coding Agent** | 代码开发、修改、验证、提交推送 |

### 工作原则

1. **遵循项目原则** - 严格遵守 SOUL.md 中的规范
2. **质量优先** - 代码必须通过所有验证
3. **安全第一** - 不引入安全风险
4. **简洁清晰** - 代码易读、易维护

---

## 📋 工作流程

### 1. 接收任务

**Ella 委托任务时提供**:
- ✅ 需求说明
- ✅ 设计方案
- ✅ 验收标准
- ✅ 相关文件路径

**Coding Agent 需要确认**:
- [ ] 已阅读 SOUL.md（项目原则）
- [ ] 理解需求和验收标准
- [ ] 确认实现方案

### 2. 开发前准备

**必须阅读的文件**:
1. `/workspace/projects/ufsauto/SOUL.md` - 项目原则
2. `/workspace/projects/ufsauto/README.md` - 快速上手
3. 相关模块的现有代码

**环境检查**:
```bash
# 确认在项目根目录
cd /workspace/projects/ufsauto

# 检查当前分支
git status

# 检查是否有未提交的更改
git status -s
```

### 3. 代码开发

**开发规范**:
```python
# ✅ 正确：使用完整导入路径
from systest.core.runner import TestCase
from systest.tools.ufs_utils import UFSDevice

# ❌ 错误：相对导入
from runner import TestCase
from ufs_utils import UFSDevice
```

**常量定义**:
```python
# ✅ 正确：定义在 constants.py
from systest.core.constants import Config

if free_gb < Config.MIN_AVAILABLE_SPACE_GB:
    logger.warning("空间不足")

# ❌ 错误：硬编码魔法数字
if free_gb < 2.0:  # 2.0 是魔法数字
    logger.warning("空间不足")
```

**日志输出**:
```python
# ✅ 正确：统一使用 logger
logger.info(f"测试开始：{test_name}")
logger.error(f"测试失败：{e}", exc_info=True)

# ❌ 错误：重复输出
print("测试开始")
logger.info("测试开始")  # 重复
```

**错误处理**:
```python
# ✅ 正确：包含调试建议
if 'device' in str(e).lower():
    logger.error(f"设备错误：{e}", exc_info=True)
    print("💡 调试建议:")
    print("  1. 检查设备路径")
    print("  2. 运行 lsblk 查看设备")

# ❌ 错误：只报错不给建议
print("Error: Device not found")
```

### 4. 代码验证

**必须通过的验证**:
```bash
# 1. 语法检查
python3 -m py_compile systest/core/*.py

# 2. 导入测试
python3 -c "from systest.core.runner import TestRunner; print('✅ 导入成功')"

# 3. 功能测试
python3 systest/bin/systest.py run --test t_perf_SeqReadBurst_001

# 4. 日志格式验证
grep -E "^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\.\d{3}" logs/*.log
```

### 5. 提交推送

**提交规范**:
```bash
# 提交信息格式
git commit -m "type: 简短描述

详细说明（可选）

- 修改内容 1
- 修改内容 2

关联问题：#123"

# type 类型:
# - feat: 新功能
# - fix: Bug 修复
# - docs: 文档更新
# - refactor: 代码重构
# - test: 测试相关
# - chore: 构建/工具
```

**推送检查**:
```bash
# 检查提交历史
git log --oneline -5

# 推送到远程
git push origin master

# 验证推送成功
git status
```

---

## 🔍 代码审查清单

### 导入路径
- [ ] 使用完整路径（systest.core.*）
- [ ] 没有相对导入
- [ ] 导入语句在文件顶部

### 常量定义
- [ ] 没有硬编码的魔法数字
- [ ] 所有阈值定义在 constants.py
- [ ] 使用 Config 类引用常量

### 日志输出
- [ ] 统一使用 logger
- [ ] 没有重复的 print() 和 logger.info()
- [ ] ERROR 级别包含 exc_info=True
- [ ] 日志格式包含毫秒时间戳和文件行号

### 错误处理
- [ ] 包含调试建议
- [ ] 异常类型具体（不滥用 Exception）
- [ ] 错误信息清晰

### 安全验证
- [ ] 路径遍历防护
- [ ] 输入验证充分
- [ ] 没有敏感信息泄露

### 测试覆盖
- [ ] 语法检查通过
- [ ] 导入测试通过
- [ ] 功能测试通过

---

## 💡 最佳实践

### 1. 代码结构

```python
# 推荐结构
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""模块说明"""

import sys
from pathlib import Path

# 第三方库
import logging

# 项目模块
from systest.core.runner import TestCase
from systest.core.constants import Config

class MyClass:
    """类的说明"""
    
    def __init__(self):
        """初始化说明"""
        pass
    
    def my_method(self, param: str) -> bool:
        """方法说明
        
        Args:
            param: 参数说明
            
        Returns:
            返回值说明
        """
        pass
```

### 2. 命名规范

```python
# 类名：CamelCase
class PerformanceTestCase:

# 函数/方法：snake_case
def validate_performance(self):

# 常量：UPPER_CASE
MIN_AVAILABLE_SPACE_GB = 2.0

# 变量：snake_case
test_dir = Path('/tmp/ufs_test')
```

### 3. 注释规范

```python
# ✅ 正确：简洁说明意图
# 检查设备是否存在
if not self.ufs.exists():
    ...

# ❌ 错误：重复代码
# 设置 test_dir 为 None
self.test_dir = None

# ❌ 错误：过度注释
x = x + 1  # x 加 1
```

---

## ⚠️ 常见错误和避免方法

### 1. 导入路径错误

**错误**:
```python
from runner import TestCase  # ModuleNotFoundError
```

**正确**:
```python
from systest.core.runner import TestCase
```

### 2. 魔法数字

**错误**:
```python
if free_gb < 2.0:  # 2.0 是什么？
    ...
```

**正确**:
```python
from systest.core.constants import Config

if free_gb < Config.MIN_AVAILABLE_SPACE_GB:
    ...
```

### 3. 日志重复

**错误**:
```python
print("测试开始")
logger.info("测试开始")  # 输出两次
```

**正确**:
```python
logger.info("测试开始")  # 只输出一次
```

### 4. 错误处理不完整

**错误**:
```python
try:
    result = risky_operation()
except Exception as e:
    print(f"Error: {e}")  # 没有堆栈，没有建议
```

**正确**:
```python
try:
    result = risky_operation()
except (IOError, ValueError) as e:
    logger.error(f"操作失败：{e}", exc_info=True)
    print("💡 调试建议:")
    print("  1. 检查输入参数")
    print("  2. 查看详细日志")
```

### 5. 安全验证缺失

**错误**:
```python
test_dir = Path(user_input)  # 路径遍历风险
test_dir.mkdir(parents=True, exist_ok=True)
```

**正确**:
```python
test_dir = Path(user_input)
test_dir.mkdir(parents=True, exist_ok=True)

# 验证路径
real_path = test_dir.resolve()
if not any(str(real_path).startswith(p) for p in Config.ALLOWED_TEST_DIR_PREFIXES):
    raise RuntimeError("路径不在允许范围内")
```

---

## 🤝 与 Ella 的协作方式

### Ella 负责
- ✅ 需求分析
- ✅ 方案设计
- ✅ 文档编写
- ✅ 任务委托
- ✅ 代码审查（高层）

### Coding Agent 负责
- ✅ 代码实现
- ✅ 代码验证
- ✅ 提交推送
- ✅ Bug 修复
- ✅ 代码审查（细节）

### 协作流程

```
Ella 分析需求 → 设计方案 → 委托任务
                      ↓
Coding Agent 接收任务 → 开发 → 验证 → 提交
                      ↓
Ella 审查 → 用户汇报
```

---

## 📊 质量指标

### 代码质量
- [ ] 语法检查通过率：100%
- [ ] 导入测试通过率：100%
- [ ] 功能测试通过率：≥95%
- [ ] 代码审查问题数：≤5 个/千行

### 提交质量
- [ ] 提交信息清晰度：100%
- [ ] 提交频率：每天至少 1 次
- [ ] 推送及时性：当天完成

---

## 📚 参考文档

- **项目原则**: `/workspace/projects/ufsauto/SOUL.md`
- **快速上手**: `/workspace/projects/ufsauto/README.md`
- **详细设计**: 飞书文档 v2.2
- **常量配置**: `/workspace/projects/ufsauto/systest/core/constants.py`

---

**最后更新**: 2026-04-10  
**维护**: Ella + Coding Agent
