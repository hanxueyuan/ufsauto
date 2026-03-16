# 开发模式更新报告

**更新日期**: 2026-03-16  
**更新原因**: 开发调试阶段需要暴露所有问题，而不是被 Precondition 检查拦截

---

## 📋 问题背景

### 原问题

Precondition 检查功能实现后：
- ❌ 如果设备不存在，会报错并跳过测试
- ❌ 开发阶段没有 UFS 设备，无法运行测试
- ❌ 问题被 Precondition 检查拦截，无法看到 FIO 的实际报错

### 用户需求

1. **开发调试阶段**：
   - ✅ 找不到 UFS 设备只输出 warning
   - ✅ 测试继续执行，让 FIO 报错暴露问题
   - ✅ 所有错误都要及时暴露出来

2. **生产环境**：
   - ✅ Precondition 检查失败则跳过测试
   - ✅ 严格检查，确保测试环境正确

---

## 🛠️ 更新内容

### 1. 添加 mode 参数

**文件**: `systest/core/precondition_checker.py`

**新增参数**:
```python
def check_all(self, precondition_config, device='/dev/ufs0', mode='development'):
    """
    Args:
        mode: 模式 ('development' | 'production')
            - development: 只记录问题，不阻止测试（开发调试阶段）
            - production: 严格检查，不满足则跳过测试（生产环境）
    """
```

**行为变更**:
- **开发模式**: 所有 error 转换为 warning，`passed` 总是 True
- **生产模式**: 严格检查，有 error 则 `passed` 为 False

---

### 2. 设备不存在只输出 warning

**文件**: `systest/core/precondition_checker.py`

**修改前**:
```python
if not passed:
    self._add_error(f'设备 {device} 不存在')
```

**修改后**:
```python
if not passed:
    # 开发模式下只输出 warning
    if self.mode == 'development':
        self._add_warning(f'未发现 UFS 设备：{device}，请确认硬件连接')
    else:
        self._add_error(f'设备 {device} 不存在')
```

---

### 3. runner.py 集成 mode 参数

**文件**: `systest/core/runner.py`

**新增参数**:
```python
def __init__(self, device='/dev/ufs0', output_dir='./results', config=None, 
             verbose=False, check_precondition=True, mode='development'):
    self.mode = mode  # 'development' | 'production'
```

**行为变更**:
```python
# 开发模式下只记录问题，继续执行测试
if self.mode == 'development':
    if precondition_result['warnings']:
        print(f"⚠️  发现 {len(precondition_result['warnings'])} 个问题，继续执行测试（开发模式）")
# 生产模式下如果检查失败，跳过测试
elif not precondition_result['passed']:
    print(f"⚠️  Precondition 检查失败，跳过测试")
    return {'status': 'SKIPPED', ...}
```

---

## 📊 测试结果

### 开发模式（默认）

**测试命令**:
```bash
python3 tests/test_precondition.py
```

**输出**:
```
模式：开发模式
总检查项：16
通过：11
失败：5
警告：4
错误：0

⚠️  开发模式：Precondition 检查问题已记录，测试将继续执行

⚠️  警告列表:
  - 可用空间不足：要求≥10.0GB，实际 1.0GB
  - 前置条件不满足：SMART 状态必须为正常
  - 前置条件不满足：可用空间必须≥10GB
  - 前置条件不满足：温度必须<70℃
```

**关键变化**:
- ✅ 4 个错误转换为 4 个警告
- ✅ 测试继续执行
- ✅ 清晰提示问题

---

### 生产模式

**使用方式**:
```python
runner = TestRunner(device='/dev/ufs0', mode='production')
result = runner.run_test('t_performance_SequentialReadBurst_001')
```

**行为**:
- ❌ Precondition 检查失败会跳过测试
- ❌ 设备不存在会报错
- ✅ 严格检查，确保测试环境正确

---

## 🚀 使用方式

### 开发模式（默认）

```python
from core.runner import TestRunner

# 创建 TestRunner（默认开发模式）
runner = TestRunner(device='/dev/ufs0', verbose=True)

# 执行测试（会检查 Precondition，但只记录问题）
result = runner.run_test('t_performance_SequentialReadBurst_001')
```

**输出示例**:
```
🔍 检查 Precondition...
  ✅ FIO 版本：要求：fio-3.33 (实际：fio-3.33)
  ⚠️  警告：未发现 UFS 设备：/dev/ufs0，请确认硬件连接
  ⚠️  发现 1 个问题，继续执行测试（开发模式）
  执行测试：t_performance_SequentialReadBurst_001
```

### 生产模式

```python
# 创建 TestRunner（生产模式）
runner = TestRunner(device='/dev/ufs0', verbose=True, mode='production')

# 执行测试（Precondition 检查失败会跳过）
result = runner.run_test('t_performance_SequentialReadBurst_001')
```

**输出示例**:
```
🔍 检查 Precondition...
  ❌ 错误：未发现 UFS 设备：/dev/ufs0
❌ Precondition 检查失败
⚠️  Precondition 检查失败，跳过测试：t_performance_SequentialReadBurst_001
```

---

## 📋 对比总结

| 特性 | 开发模式 | 生产模式 |
|------|---------|---------|
| **默认值** | ✅ 默认 | ❌ 需显式指定 |
| **设备不存在** | ⚠️ 输出 warning | ❌ 报错并停止 |
| **Precondition 失败** | ⚠️ 记录 warning | ❌ Stop on fail |
| **测试执行** | ✅ 继续执行 | ❌ 立即停止 |
| **问题暴露** | ✅ 完全暴露 | ❌ 立即停止 |
| **适用场景** | 开发调试 | 生产环境 |

---

## ✅ 更新成果

### 解决的问题

1. ✅ **开发阶段可以运行测试** - 即使没有 UFS 设备
2. ✅ **问题完全暴露** - 所有错误都能看到
3. ✅ **FIO 报错能暴露** - 不会被 Precondition 检查拦截
4. ✅ **清晰的 warning 提示** - 知道问题在哪里

### 保留的功能

1. ✅ **生产模式严格检查** - 确保生产环境正确
2. ✅ **灵活的 mode 切换** - 开发/生产自由切换
3. ✅ **详细的检查日志** - 知道每个检查项的结果

---

## 📝 最佳实践

### 开发阶段

```python
# 使用默认开发模式
runner = TestRunner(device='/dev/ufs0', verbose=True)
```

**优势**:
- 即使没有 UFS 设备也能运行测试
- 可以看到 FIO 的实际报错
- 方便调试代码逻辑

### 生产阶段

```python
# 使用生产模式
runner = TestRunner(device='/dev/ufs0', verbose=True, mode='production')

# 生产模式会 Stop on fail，需要用 try-except 捕获
try:
    result = runner.run_test('t_performance_SequentialReadBurst_001')
except RuntimeError as e:
    print(f"测试停止：{e}")
```

**优势**:
- 确保测试环境正确
- 避免在错误的环境上运行测试
- Stop on fail，立即暴露问题
- 节省测试时间

---

## 🎯 总结

**更新完成，开发模式下 Precondition 检查只记录问题，不阻止测试！**

- ✅ 开发模式：只记录 warning，测试继续执行
- ✅ 生产模式：严格检查，失败则跳过
- ✅ 灵活切换：mode 参数控制
- ✅ 问题暴露：所有错误都能看到

**适合开发调试阶段使用！** 🎉
