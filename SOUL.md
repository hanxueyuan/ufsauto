# UFS Auto 项目原则

**版本**: 2.2  
**最后更新**: 2026-04-10  
**状态**: Production Ready ✅

---

## 🎯 核心原则

### 1. 简洁优先
- ✅ 删除冗余文件，保持目录清晰
- ✅ 代码注释精简，只保留必要说明
- ✅ 文档统一位置（docs/），避免散落
- ✅ 一个测试用例一个日志文件

### 2. 工程师友好
- ✅ 终端直接显示错误和调试建议
- ✅ 颜色区分状态（绿✅/红❌/黄⚠️/蓝🔵）
- ✅ 测试开始/结束显示摘要信息
- ✅ 错误信息包含堆栈和调试建议

### 3. 开发/生产分离
- ✅ 开发模式：60 秒/次，DEBUG 日志
- ✅ 生产模式：300 秒/次，INFO 日志
- ✅ 一个 flag 切换，逻辑完全一致
- ✅ 每个测试执行 1 次，不循环

### 4. 量化分析
- ✅ 性能结果：实际值/目标值/百分比
- ✅ 三级阈值：≥100% 达标，90-100% 可接受，<90% 不达标
- ✅ 日志毫秒级时间戳 + 文件行号
- ✅ 所有魔法数字定义在 constants.py

---

## 📁 目录结构原则

```
ufsauto/
├── README.md              # 唯一根目录文档
├── SOUL.md                # 项目原则（本文件）
├── systest/               # 测试框架核心
│   ├── bin/              # 命令行入口
│   ├── config/           # 配置文件
│   ├── core/             # 核心模块
│   ├── suites/           # 测试套件
│   └── tools/            # 工具模块
├── scripts/              # 脚本工具
│   └── tools/           # Python 工具脚本
├── demos/                # 演示脚本
├── docs/                 # 所有文档
├── tools/                # Shell 工具
├── results/              # 测试结果
└── logs/                 # 日志文件
```

**原则**:
- 根目录只保留 README.md 和 SOUL.md
- 代码按功能分层（core/tools/suites）
- 文档统一在 docs/
- 演示脚本在 demos/

---

## 🛠️ 开发规范

### 1. 导入路径
```python
# ✅ 正确：使用完整路径
from systest.core.runner import TestCase
from systest.tools.ufs_utils import UFSDevice

# ❌ 错误：相对导入
from runner import TestCase
from ufs_utils import UFSDevice
```

### 2. 日志输出
```python
# ✅ 终端摘要 + 文件详细
print("=" * 60)
print("📊 测试开始摘要")
logger.info("详细执行步骤")

# ❌ 避免：重复输出
print("...")
logger.info("...")  # 同一内容输出两次
```

### 3. 错误处理
```python
# ✅ 显示调试建议
if 'device' in error:
    print("💡 调试建议:")
    print("  1. 检查设备路径")
    print("  2. 运行 lsblk 查看设备")
    logger.error(f"测试执行失败：{e}", exc_info=True)

# ❌ 避免：只报错不给建议
print("Error: Device not found")
```

### 4. 常量定义
```python
# ✅ 正确：定义在 constants.py
from systest.core.constants import Config

if free_gb < Config.MIN_AVAILABLE_SPACE_GB:
    logger.warning("空间不足")

# ❌ 错误：硬编码魔法数字
if free_gb < 2.0:  # 2.0 是魔法数字
    logger.warning("空间不足")
```

### 5. 安全验证
```python
# ✅ 正确：路径验证
def _validate_and_resolve_test_dir(self, path: Path) -> Path:
    allowed_prefixes = Config.ALLOWED_TEST_DIR_PREFIXES
    path.mkdir(parents=True, exist_ok=True)  # 先创建
    real_path = path.resolve()  # 再验证
    if not any(str(real_path).startswith(p) for p in allowed_prefixes):
        raise RuntimeError("路径不在允许范围内")
    return real_path

# ❌ 错误：跳过验证
try:
    real_path = path.resolve()
except FileNotFoundError:
    path.mkdir()  # ⚠️ 异常处理跳过了验证
```

---

## 📋 测试用例设计原则

### 1. 四阶段生命周期
```
setup() → execute() → validate() → teardown()
```

### 2. Precondition 检查
- 检查设备存在（支持自动检测）
- 检查可用空间（≥2GB）
- 检查 FIO 工具
- 检查权限
- **记录健康基线**
- 返回 False → SKIP 状态

### 3. Postcondition 检查
- **设备健康状态**: OK → 非 OK = 记录失败
- **Critical Warning**: 新增警告 = 记录失败
- **Pre-EOL**: 从 0x00 → 非 0x00 = 记录失败
- **坏块增加 = FailStop**（最高优先级）

### 4. 失败处理模式
- **Fail-Continue**（软失败）: 性能测试，record_failure() 记录
- **Fail-Stop**（硬失败）: 硬件故障，抛出 FailStop

### 5. 量化达标比例
```
带宽/IOPS: 实际值/目标值
≥100%: 达标 ✅
90%-100%: 可接受 ⚠️
<90%: 显著不达标 ❌

延迟：实际值/限制值
≤100%: 达标 ✅
>100%: 超出限制 ❌
```

---

## 🔒 安全原则

### 1. 路径安全
- 测试目录必须在允许前缀内（/tmp, /mapdata）
- 路径验证逻辑：先创建目录，再验证路径
- 防止路径遍历攻击

### 2. 输入验证
- 所有外部输入视为不可信
- 命令行参数需要验证
- 配置文件需要验证

### 3. 错误信息
- 错误信息不泄露敏感数据
- 堆栈跟踪只记录到日志文件
- 终端输出简洁的调试建议

---

## 📊 日志系统规范

### 1. 日志文件
- 只创建 .log 文件（不再创建 _error.log）
- 每个测试运行一个日志文件
- 日志文件包含所有级别信息

### 2. 日志格式
```
# 终端输出
2026-04-10 12:15:30.123 [INFO] [systest.py:100] 测试模式：Development

# 文件输出
2026-04-10 12:15:30.123 - systest.test - INFO - [/workspace/.../systest.py:100] - 测试模式：Development
```

### 3. 错误记录
- ERROR 级别自动输出堆栈跟踪
- 错误信息同时通过 print() 和 logger.error() 输出
- 包含调试建议

---

## 🚀 Coding Agent 使用规范

### 1. 代码开发原则
- ✅ 遵循四层架构（入口层/核心层/工具层/套件层）
- ✅ 使用完整导入路径（systest.core.*）
- ✅ 常量定义在 constants.py
- ✅ 代码注释精简，只保留必要说明

### 2. 代码审查要点
- ✅ 检查导入路径是否正确
- ✅ 检查是否有魔法数字
- ✅ 检查错误处理是否完善
- ✅ 检查日志输出是否规范
- ✅ 检查安全验证是否充分

### 3. 测试验证要求
- ✅ 语法检查通过（py_compile）
- ✅ 导入测试通过
- ✅ 功能测试通过
- ✅ 日志格式验证通过

### 4. 提交规范
- ✅ 提交信息清晰描述修改内容
- ✅ 关联相关问题和需求
- ✅ 推送到远程仓库

---

## 💡 经验总结

1. **终端输出比日志文件更重要** - 工程师调试时第一眼看到
2. **开发模式要快** - 2 分钟内验证逻辑，生产模式充分测试
3. **错误信息要有调试建议** - 不只是报错，要告诉怎么修
4. **目录结构要清晰** - 新人 5 分钟找到文件位置
5. **文档要实用** - README.md 包含所有常用命令示例
6. **每个测试执行 1 次** - 不再循环 10 次，使用 --batch 实现多次测试
7. **一个日志文件** - 不再创建空 error.log，所有信息在一个文件
8. **对结果尽量验证** - 对所做的代码变更尽量进行review or try run 尽量段的时间去验证可用性
---

## 📋 违反原则的检查清单

在代码审查时，检查以下问题：

- [ ] 是否有硬编码的魔法数字？→ 移到 constants.py
- [ ] 是否使用相对导入？→ 改为 systest.core.*
- [ ] 是否有重复的 print() 和 logger.info()？→ 统一使用 logger
- [ ] 是否有空 error.log 文件？→ 移除
- [ ] 是否有循环测试逻辑？→ 改为 1 次
- [ ] 是否有路径遍历风险？→ 添加验证
- [ ] 错误信息是否有调试建议？→ 添加建议
- [ ] 日志是否包含毫秒时间戳？→ 添加毫秒
- [ ] 是否包含文件行号？→ 添加行号

---

**文档维护**: 随框架迭代同步更新  
**负责人**: 雪原  
**最后更新**: 2026-04-10
