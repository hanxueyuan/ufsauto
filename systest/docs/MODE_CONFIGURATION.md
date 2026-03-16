# 开发模式 vs 生产模式配置指南

**版本**: v1.0  
**更新日期**: 2026-03-16

---

## 📋 概述

SysTest 支持两种运行模式，通过不同的配置文件区分：

| 模式 | 配置文件 | 用途 |
|------|---------|------|
| **开发模式** | `config/development.json` | 开发调试 |
| **生产模式** | `config/production.json` | 正式测试 |

---

## 📊 配置对比

### 主要参数对比

| 参数 | 开发模式 | 生产模式 | 说明 |
|------|---------|---------|------|
| **default_runtime** | 10 秒 | 60 秒 | Burst 测试运行时间 |
| **sustained_runtime** | 60 秒 | 300 秒 | Sustained 测试运行时间 |
| **retry_count** | 1 | 3 | 失败重试次数 |
| **loop_count** | 1 | 3 | 循环执行次数 |
| **Precondition 模式** | development | production | 检查行为 |
| **fail_on_error** | false | true | Precondition 失败是否停止 |
| **输出目录** | `results/dev` | `results/prod` | 结果保存位置 |

### 可靠性测试时间对比

| 测试 | 开发模式 | 生产模式 |
|------|---------|---------|
| StabilityTest | 300 秒（5 分钟） | 86400 秒（24 小时） |

---

## 🚀 使用方式

### 开发模式

```bash
cd systest

# 使用开发配置执行单个测试
python3 bin/systest run -t t_performance_SequentialReadBurst_001 \
  --config config/development.json -v

# 或使用默认开发配置（默认就是 development）
python3 tests/t_performance_SequentialReadBurst_001.py
```

**特点**:
- ✅ 测试时间短（10-60 秒）
- ✅ 只执行 1 次循环
- ✅ Precondition 只记录问题，不阻止测试
- ✅ 适合快速验证代码逻辑

### 生产模式

```bash
cd systest

# 使用生产配置执行单个测试
python3 bin/systest run -t t_performance_SequentialReadBurst_001 \
  --config config/production.json -v

# 执行整个套件
python3 bin/systest run -s performance \
  --config config/production.json -v
```

**特点**:
- ✅ 测试时间长（60-300 秒）
- ✅ 执行 3 次循环取平均值
- ✅ Precondition 失败会立即停止（Stop on fail）
- ✅ 符合车规级测试要求

---

## 📝 配置文件说明

### development.json

```json
{
  "mode": "development",
  "execution": {
    "default_runtime": 10,      // Burst 测试 10 秒
    "sustained_runtime": 60,    // Sustained 测试 60 秒
    "loop_count": 1             // 只执行 1 次
  },
  "precondition": {
    "mode": "development",
    "fail_on_error": false      // 不阻止测试
  }
}
```

### production.json

```json
{
  "mode": "production",
  "execution": {
    "default_runtime": 60,      // Burst 测试 60 秒
    "sustained_runtime": 300,   // Sustained 测试 300 秒
    "loop_count": 3             // 执行 3 次
  },
  "precondition": {
    "mode": "production",
    "fail_on_error": true       // Stop on fail
  }
}
```

---

## 📊 测试结果对比

### 开发模式输出

```
================================================================================
测试结果
================================================================================
✅ PASS

测试指标:
  - 带宽：2150.5 MB/s

验收目标:
  - ≥ 2100 MB/s (容差：95%)

执行时间：10 秒
循环次数：1
模式：开发模式
================================================================================
```

### 生产模式输出

```
================================================================================
测试结果
================================================================================
✅ PASS

测试指标:
  - 带宽：2150.5 MB/s (平均)
  - 第 1 次：2145.2 MB/s
  - 第 2 次：2152.8 MB/s
  - 第 3 次：2153.5 MB/s

验收目标:
  - ≥ 2100 MB/s (容差：95%)

执行时间：60 秒 × 3 次 = 180 秒
循环次数：3
模式：生产模式
================================================================================
```

---

## 🎯 使用场景

### 开发模式适用场景

1. **代码开发阶段**
   - 验证代码逻辑是否正确
   - 快速迭代开发

2. **调试阶段**
   - 定位问题原因
   - 验证修复方案

3. **日常开发**
   - 每日构建验证
   - 代码提交前自检

### 生产模式适用场景

1. **正式测试**
   - 产品发布前验证
   - 车规级认证测试

2. **性能评估**
   - 获取准确的性能数据
   - 对比不同版本性能

3. **可靠性测试**
   - 24 小时稳定性测试
   - 长期运行验证

---

## ⚠️ 注意事项

### 开发模式

- ✅ 测试时间短，结果仅供参考
- ✅ 不执行完整的 Precondition 检查
- ❌ 不能用于正式测试报告
- ❌ 不能用于车规级认证

### 生产模式

- ✅ 测试时间长，结果准确可靠
- ✅ 执行完整的 Precondition 检查
- ✅ 可用于正式测试报告
- ✅ 符合车规级认证要求
- ⚠️ 可靠性测试需要 24 小时，确保电源稳定

---

## 🔄 模式切换

### 在脚本中切换

```python
from core.runner import TestRunner

# 开发模式（默认）
runner = TestRunner(
    device='/dev/ufs0',
    mode='development'
)

# 生产模式
runner = TestRunner(
    device='/dev/ufs0',
    mode='production'
)
```

### 在命令行中切换

```bash
# 开发模式（默认）
python3 bin/systest run -t test_name

# 生产模式
python3 bin/systest run -t test_name --config config/production.json
```

---

## 📈 测试时间对比

### 完整测试套件时间

| 套件 | 开发模式 | 生产模式 |
|------|---------|---------|
| performance (9 个用例) | ~5 分钟 | ~45 分钟 |
| qos (2 个用例) | ~2 分钟 | ~10 分钟 |
| reliability (1 个用例) | 5 分钟 | 24 小时 |
| scenario (2 个用例) | ~2 分钟 | ~10 分钟 |

**注意**: 生产模式会执行 3 次循环，时间约为开发模式的 3-6 倍。

---

## 🎯 总结

| 特性 | 开发模式 | 生产模式 |
|------|---------|---------|
| **测试时间** | 短（10-60 秒） | 长（60-300 秒） |
| **循环次数** | 1 次 | 3 次 |
| **Precondition** | 只记录问题 | Stop on fail |
| **适用场景** | 开发调试 | 正式测试 |
| **结果准确性** | 仅供参考 | 准确可靠 |
| **车规认证** | ❌ 不适用 | ✅ 适用 |

**开发调试用开发模式，正式测试用生产模式！** 🎉
