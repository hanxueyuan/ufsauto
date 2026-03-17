# 测试用例注释规范

**版本**: v3.0  
**创建时间**: 2026-03-16  
**最后更新**: 2026-03-17 11:30  
**更新人**: 雪原 + OpenClaw Agent  
**适用范围**: 所有 systest 测试用例

---

## 🎯 核心原则

### 注释的目的
**让其他工程师看到注释就能理解测试方法、复现测试、验证结果**

### 三写三不写

**三写** ✅：
1. ✅ 写**测试方法**（用什么命令、读什么文件、调用什么函数）
2. ✅ 写**预期结果**（期望得到什么结果、阈值是什么）
3. ✅ 写**验证条件**（必须满足的条件、不满足会怎样）

**三不写** ❌：
1. ❌ 不写**具体值**（如 Debian 12、8 核 16GB）
2. ❌ 不写**期望配置**（如 TURBO Mode 开启）
3. ❌ 不写**目标状态**（如 SMART 正常）

---

## 📋 注释结构（完整版）

```python
"""
测试用例：<文件名，不含.py>
<中文描述>

测试目的:
<清晰描述这个测试验证什么功能或指标，确保满足什么车规级要求>

Precondition:
1.1 系统环境收集
    - 操作系统：读取 /etc/os-release，收集 PRETTY_NAME 字段
    - CPU：读取 /proc/cpuinfo，收集 model name 和 cpu cores
    - 内存：读取 /proc/meminfo，收集 MemTotal
    - FIO 版本：执行 fio --version，收集版本号

1.2 测试目标信息收集
    - 设备路径：
      - 方法：ls -l /dev/ | grep ufs
      - 预期：找到 /dev/ufs0 设备节点
    - 设备型号：
      - 方法：cat /sys/block/ufs0/device/model
      - 预期：返回设备型号字符串（如 "UFS 3.1 128GB"）
    - 固件版本：
      - 方法：cat /sys/block/ufs0/device/rev
      - 预期：返回固件版本号（如 "v1.0.0"）
    - 设备容量：
      - 方法：fdisk -l /dev/ufs0 | grep "Disk"
      - 预期：返回设备总容量（如 "128GB"）
    - 可用空间：
      - 方法：df -BG /dev/ufs0 | tail -1 | awk '{print $4}'
      - 预期：可用空间≥10GB

1.3 存储设备配置检查
    - 查看支持的功能：
      - 方法：cat /sys/block/ufs0/device/features
      - 预期：列出设备支持的所有功能列表
    - 需要开启的功能：
      - TURBO Mode：
        - 检查方法：cat /sys/block/ufs0/device/turbo_mode
        - 预期值：1（开启）
        - 开启方法：echo 1 > /sys/block/ufs0/device/turbo_mode（如未开启）
    - 需要关闭的功能：
      - 省电模式：
        - 检查方法：cat /sys/block/ufs0/device/power_save
        - 预期值：0（关闭）
        - 关闭方法：echo 0 > /sys/block/ufs0/device/power_save（如未关闭）
    - 特殊配置项：
      - 如有，说明配置名称、检查方法、预期值

1.4 UFS 器件配置检查
    - LUN 数量：
      - 方法：调用 _get_lun_count() 函数
      - 预期：返回实际 LUN 数量（如 4）
    - LUN 配置详情：
      - 方法：读取 /sys/block/ufs0/device/lun/*/size 和 type
      - 预期：列出每个 LUN 的容量和用途
    - LUN 映射关系：
      - 方法：ls -l /dev/ | grep ufs
      - 预期：验证 LUN1 映射到 /dev/ufs0

1.5 器件健康状况检查
    - SMART 状态：
      - 方法：smartctl -H /dev/ufs0 | grep "SMART overall-health"
      - 预期：SMART overall-health self-assessment test result: PASSED
    - 剩余寿命：
      - 方法：smartctl -l smartctl /dev/ufs0 | grep "Percentage Used"
      - 预期：Percentage Used ≤ 2%（即剩余寿命≥98%）
    - 坏块数量：
      - 方法：smartctl -l smartctl /dev/ufs0 | grep "Available Spare"
      - 预期：Available Spare ≥ 90%
    - 温度：
      - 方法：cat /sys/class/hwmon/*/temp*_input
      - 预期：当前温度 < 70℃
    - 错误计数：
      - 方法：cat /sys/block/ufs0/device/stats
      - 预期：CRC 错误=0, 重传次数=0

1.6 前置条件验证
    - ✓ SMART 状态必须为 PASSED（否则跳过测试）
    - ✓ 可用空间必须≥10GB（否则跳过测试）
    - ✓ 温度必须<70℃（否则跳过测试）
    - ✓ 剩余寿命必须>90%（否则跳过测试）

Test Steps:
1. <步骤 1>：<详细操作，包括命令和参数>
2. <步骤 2>：<详细操作，包括预期结果>
3. <步骤 3>：<详细操作>
4. <步骤 4>：<数据收集>

Postcondition:
- 测试结果保存：results/<category>/目录
- 配置恢复：
  - 恢复 TURBO Mode 为原始状态
  - 恢复省电模式为原始状态
- 设备恢复：等待 5 秒，让设备回到空闲状态
- 数据清理：
  - 删除测试生成的临时文件
  - 执行 fstrim /dev/ufs0 清理未使用块
- 测试后状态检查：
  - 重新读取 SMART 状态
  - 重新读取温度
  - 重新读取错误计数
  - 对比测试前后变化

测试参数:
- rw: <读写模式，如 read, write, randread>
- bs: <块大小，如 128k, 4k>
- iodepth: <队列深度，如 32>
- numjobs: <并发线程数，如 1>
- runtime: <测试时长（秒），如 60, 300>

验收标准:
- PASS: <具体指标> ≥ <目标值>（允许 5% 误差，即≥<容差后值>）
- FAIL: <具体指标> < <容差后值>

注意事项:
- <注意事项 1>
- <注意事项 2>
- <注意事项 3>
- 建议重复测试 3 次取平均值
"""
```

---

## 💡 Precondition 核心要点

### 1.1 系统环境收集

**目的**：记录测试执行时的系统状态，确保测试可复现

**正确写法**：
```python
1.1 系统环境收集
    - 操作系统：读取 /etc/os-release，收集 PRETTY_NAME 字段
    - CPU：读取 /proc/cpuinfo，收集 model name 和 cpu cores
    - 内存：读取 /proc/meminfo，收集 MemTotal
    - FIO 版本：执行 fio --version，收集版本号
```

**错误写法** ❌：
```python
1.1 系统环境收集
    - 操作系统：Debian 12, kernel 5.15.120  # ❌ 写死具体值
    - CPU/内存：8 核，16GB  # ❌ 写死具体值
    - FIO 版本：fio-3.33  # ❌ 写死具体值
```

---

### 1.2 测试目标信息收集

**目的**：明确测试对象，说明如何获取设备信息

**正确写法**：
```python
1.2 测试目标信息收集
    - 设备路径：
      - 方法：ls -l /dev/ | grep ufs
      - 预期：找到 /dev/ufs0 设备节点
    - 设备型号：
      - 方法：cat /sys/block/ufs0/device/model
      - 预期：返回设备型号字符串
```

**错误写法** ❌：
```python
1.2 测试目标信息收集
    - 设备路径：/dev/ufs0  # ❌ 写死路径
    - 设备型号：UFS 3.1 128GB  # ❌ 写死型号
```

---

### 1.3 存储设备配置检查

**目的**：说明如何查看设备支持的功能，如何配置测试所需状态

**正确写法**：
```python
1.3 存储设备配置检查
    - 查看支持的功能：
      - 方法：cat /sys/block/ufs0/device/features
      - 预期：列出设备支持的所有功能列表
    - 需要开启的功能：
      - TURBO Mode：
        - 检查方法：cat /sys/block/ufs0/device/turbo_mode
        - 预期值：1（开启）
        - 开启方法：echo 1 > /sys/block/ufs0/device/turbo_mode
```

**错误写法** ❌：
```python
1.3 存储设备配置检查
    - 开启功能：TURBO Mode  # ❌ 没说明如何检查、如何开启
    - 关闭功能：省电模式  # ❌ 没说明如何检查、如何关闭
```

---

### 1.4 UFS 器件配置检查

**目的**：说明如何检查 LUN 配置，预期得到什么结果

**正确写法**：
```python
1.4 UFS 器件配置检查
    - LUN 数量：
      - 方法：调用 _get_lun_count() 函数
      - 预期：返回实际 LUN 数量
    - LUN 映射关系：
      - 方法：ls -l /dev/ | grep ufs
      - 预期：验证 LUN1 映射到 /dev/ufs0
```

**错误写法** ❌：
```python
1.4 UFS 器件配置检查
    - LUN 数量：4 个  # ❌ 写死数量
    - LUN 映射：LUN1→/dev/ufs0  # ❌ 写死映射
```

---

### 1.5 器件健康状况检查

**目的**：说明如何检查器件健康状态，确保测试前器件正常

**正确写法**：
```python
1.5 器件健康状况检查
    - SMART 状态：
      - 方法：smartctl -H /dev/ufs0 | grep "SMART overall-health"
      - 预期：SMART overall-health self-assessment test result: PASSED
    - 剩余寿命：
      - 方法：smartctl -l smartctl /dev/ufs0 | grep "Percentage Used"
      - 预期：Percentage Used ≤ 2%
```

**错误写法** ❌：
```python
1.5 器件健康状况检查
    - SMART 状态：正常  # ❌ 没说明如何检查
    - 剩余寿命：98%  # ❌ 写死值
```

---

### 1.6 前置条件验证

**目的**：明确必须满足的条件，不满足则跳过测试

**正确写法**：
```python
1.6 前置条件验证
    - ✓ SMART 状态必须为 PASSED（否则跳过测试）
    - ✓ 可用空间必须≥10GB（否则跳过测试）
    - ✓ 温度必须<70℃（否则跳过测试）
```

**错误写法** ❌：
```python
1.6 前置条件验证
    - SMART 状态正常  # ❌ 没说明不满足会怎样
    - 可用空间≥10GB  # ❌ 没说明是硬性要求
```

---

## 📊 注释完整性检查清单

在提交测试用例前，逐项检查：

| 检查项 | 要求 | 检查方法 |
|--------|------|----------|
| 测试目的 | 清晰说明验证什么 | 是否包含"验证"、"确保"等词 |
| Precondition 1.1 | 说明收集方法和字段 | 是否包含"读取"、"执行"、"收集" |
| Precondition 1.2 | 说明检查方法和预期 | 是否有"方法："和"预期：" |
| Precondition 1.3 | 说明功能检查和配置方法 | 是否有"检查方法"、"开启方法" |
| Precondition 1.4 | 说明 LUN 检查方法 | 是否说明如何获取 LUN 信息 |
| Precondition 1.5 | 说明健康检查命令 | 是否包含 smartctl 命令 |
| Precondition 1.6 | 说明验证条件和后果 | 是否有"必须"、"否则" |
| Test Steps | 步骤详细可复现 | 是否包含命令和参数 |
| Postcondition | 说明恢复和清理方法 | 是否说明如何恢复配置 |
| 验收标准 | 明确 PASS/FAIL 判断 | 是否有具体数值和容差 |
| 注意事项 | 至少 3 条实用建议 | 是否包含"建议重复测试" |

---

## 🎯 示例对比

### 完整示例

**✅ 正确示例**：参见 `t_performance_SequentialReadBurst_001.py`

**❌ 错误示例**：参见历史版本（写死具体值的版本）

---

## 📚 相关文档

- `PRECONDITION_CORRECT_GUIDE.md` - Precondition 正确写法指南
- `PRECONDITION_IMPLEMENTATION.md` - Precondition 检查器实现说明
- `ALL_TEST_CASES_COMMENTS.md` - 所有测试用例完整注释

---

**版本历史**:
- v3.0 (2026-03-17): 全面更新，强调测试方法而非具体值
- v2.0 (2026-03-16): 添加 Precondition 分级
- v1.0 (2026-03-16): 初始版本

---

**严格遵守此规范，确保测试用例注释的可读性、可复现性、可维护性！** ✅
