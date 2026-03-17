# Precondition 正确写法指南

**更新日期**: 2026-03-17  
**适用范围**: 所有 SysTest 测试用例

---

## ❌ 错误理解

### 错误 1：写死具体值
```python
Precondition:
1.1 系统环境收集
    - 操作系统：Debian 12, kernel 5.15.120  # ❌ 错误！
    - CPU/内存：8 核，16GB  # ❌ 错误！
```

**为什么错**：
- Precondition 不是"期望值"
- 脚本会在实际环境中收集**真实信息**
- 注释应该说明**收集什么**，而不是**期望什么**

---

## ✅ 正确理解

### Precondition 的作用

Precondition 说明测试执行前，脚本会：
1. **收集哪些信息**（信息类别）
2. **通过什么命令收集**（具体命令/文件路径）
3. **收集哪些字段**（具体字段名）

### 正确格式

```python
Precondition:
1.1 系统环境收集
    - <信息类别>：<命令/文件>，收集 <字段>
```

---

## 📋 标准模板

### 1.1 系统环境收集

```python
1.1 系统环境收集
    - 操作系统：读取 /etc/os-release，收集 PRETTY_NAME 字段
    - CPU：读取 /proc/cpuinfo，收集 model name 和 cpu cores
    - 内存：读取 /proc/meminfo，收集 MemTotal
    - FIO 版本：执行 fio --version，收集版本号
```

**说明**：
- ✅ 说明读取什么文件/执行什么命令
- ✅ 说明收集什么字段
- ❌ 不写具体值（如"Debian 12"）

---

### 1.2 测试目标信息收集

```python
1.2 测试目标信息收集
    - 设备路径：检查 /dev/ufs0 是否存在（os.path.exists）
    - 设备型号：读取 /sys/block/ufs0/device/model
    - 固件版本：读取 /sys/block/ufs0/device/rev
    - 设备容量：执行 fdisk -l /dev/ufs0，收集容量信息
    - 可用空间：执行 df -BG /dev/ufs0，收集 Available 字段
```

**说明**：
- ✅ 说明检查方法（os.path.exists）
- ✅ 说明读取什么 sysfs 文件
- ✅ 说明执行什么命令
- ❌ 不写具体值（如"128GB"）

---

### 1.3 存储设备配置检查

```python
1.3 存储设备配置检查
    - 开启功能：检查 TURBO Mode 状态（待实现自动检查）
    - 关闭功能：检查省电模式状态（待实现自动检查）
    - 特殊配置：检查并记录特殊配置
```

**说明**：
- ✅ 说明检查什么功能
- ✅ 标注"待实现"如果功能未完成
- ❌ 不写"开启"或"关闭"（这是期望值）

---

### 1.4 UFS 器件配置检查

```python
1.4 UFS 器件配置检查
    - LUN 数量：调用 _get_lun_count() 获取实际 LUN 数量
    - LUN 配置：读取并记录各 LUN 容量和用途
    - LUN 映射：验证 LUN 与/dev/ufs0 映射关系（待实现）
```

**说明**：
- ✅ 说明调用什么函数
- ✅ 说明读取什么信息
- ❌ 不写具体值（如"4 个"、"LUN1→/dev/ufs0"）

---

### 1.5 器件健康状况检查

```python
1.5 器件健康状况检查
    - SMART 状态：执行 smartctl -H /dev/ufs0，检查 SMART overall-health
    - 剩余寿命：执行 smartctl -l smartctl /dev/ufs0，收集 Percentage Used
    - 坏块数量：执行 smartctl -l smartctl /dev/ufs0，收集 Available Spare
    - 温度：读取 /sys/class/hwmon/*/temp*_input，转换为摄氏度
    - 错误计数：读取 /sys/block/ufs0/device/stats，收集 CRC 错误和重传次数
```

**说明**：
- ✅ 说明执行什么 smartctl 命令
- ✅ 说明读取什么 sysfs 文件
- ✅ 说明收集什么字段
- ❌ 不写具体值（如"98%"、"35℃"）

---

### 1.6 前置条件验证

```python
1.6 前置条件验证
    - ✓ SMART 状态验证（必须为 PASS）
    - ✓ 可用空间验证（必须≥10GB）
    - ✓ 温度验证（必须<70℃）
    - ✓ 剩余寿命验证（必须>90%）
```

**说明**：
- ✅ 说明验证什么条件
- ✅ 说明阈值（这是验证条件，不是收集值）
- ✅ 使用"必须"强调硬性要求

---

## 🔑 核心原则

### ✅ 应该写的
1. **收集方法**：读取什么文件、执行什么命令、调用什么函数
2. **收集字段**：收集什么具体字段（PRETTY_NAME、MemTotal 等）
3. **验证条件**：必须满足的阈值（≥10GB、<70℃等）

### ❌ 不应该写的
1. **具体值**：Debian 12、8 核 16GB、fio-3.33
2. **期望结果**：SMART 正常、剩余寿命 98%
3. **配置状态**：TURBO Mode 开启、省电模式关闭

---

## 📝 记忆口诀

**"三写三不写"**

**三写**：
1. ✅ 写收集方法（命令/文件）
2. ✅ 写收集字段（字段名）
3. ✅ 写验证条件（阈值）

**三不写**：
1. ❌ 不写具体值
2. ❌ 不写期望结果
3. ❌ 不写配置状态

---

## 🎯 示例对比

### ❌ 错误示例
```python
1.1 系统环境收集
    - 操作系统：Debian 12, kernel 5.15.120
    - CPU/内存：8 核，16GB
    - FIO 版本：fio-3.33
```

### ✅ 正确示例
```python
1.1 系统环境收集
    - 操作系统：读取 /etc/os-release，收集 PRETTY_NAME 字段
    - CPU：读取 /proc/cpuinfo，收集 model name 和 cpu cores
    - 内存：读取 /proc/meminfo，收集 MemTotal
    - FIO 版本：执行 fio --version，收集版本号
```

---

## 📚 参考文档

- 《测试用例注释规范》v2.0
- `systest/core/precondition_checker.py` - Precondition 检查器实现
- `systest/docs/PRECONDITION_IMPLEMENTATION.md` - 实现说明

---

**最后更新**: 2026-03-17 11:25  
**状态**: 必须严格遵守
