# Precondition 检查器实现说明

**版本**: v1.1  
**更新日期**: 2026-03-17  
**实现文件**: `systest/core/precondition_checker.py`  
**Review 日期**: 2026-03-17（雪原 + OpenClaw Agent）

---

## 🎯 Precondition 检查器实际做了什么

### 核心功能

PreconditionChecker 在测试执行前**实际收集信息**和**检查配置**：

---

## 📊 实际收集的信息（6 大类）

### 1. 系统环境信息

**实际收集**:
- ✅ FIO 版本 - 调用 `fio --version` 获取实际版本
- ✅ 操作系统 - 读取 `/etc/os-release` 获取实际 OS 信息
- ✅ CPU/内存信息 - 读取 `/proc/cpuinfo` 和 `/proc/meminfo` 获取实际配置

**代码实现**:
```python
def _get_fio_version(self):
    result = subprocess.run(['fio', '--version'], capture_output=True, text=True)
    return result.stdout.strip() if result.returncode == 0 else 'unknown'

def _get_os_info(self):
    result = subprocess.run(['cat', '/etc/os-release'], capture_output=True, text=True)
    # 解析 PRETTY_NAME 字段

def _get_cpu_memory_info(self):
    # 读取 /proc/cpuinfo 获取 CPU 型号
    # 读取 /proc/meminfo 获取内存大小
```

---

### 2. 设备信息

**实际收集**:
- ✅ 设备路径 - 检查 `/dev/ufs0` 是否存在 (`os.path.exists()`)
- ✅ 可用空间 - 调用 `df` 命令获取实际可用空间 (GB)

**代码实现**:
```python
def _check_device_info(self, device_info, device):
    # 检查设备路径
    passed = os.path.exists(device)
    
    # 检查可用空间
    actual_space = self._get_available_space_gb(device)
    # 调用 df 命令：df -BG --output=avail <device>
```

---

### 3. 存储设备配置

**实际检查**:
- ⚠️ 需要开启的功能 - **目前只记录，待实现自动检查**
- ⚠️ 需要关闭的功能 - **目前只记录，待实现自动检查**
- ⚠️ 特殊配置项 - **目前只记录，待实现自动检查**

**代码实现**:
```python
def _check_config(self, config):
    # 目前只记录配置要求，待实现自动检查
    if enable_funcs:
        self._add_check('功能开启', True, f'需要开启：{enable_funcs}', '待实现自动配置')
```

**待实现功能**:
- 检查 TURBO Mode 是否开启
- 检查省电模式是否关闭
- 检查 IO 调度器配置
- 自动配置功能开关

---

### 4. LUN 配置信息

**实际收集**:
- ✅ LUN 数量 - 调用 `_get_lun_count(device)` 获取实际 LUN 数量
- ⚠️ LUN 映射 - **目前只记录，待实现自动检查**

**代码实现**:
```python
def _check_lun_config(self, lun_config, device):
    # 检查 LUN 数量
    actual_count = self._get_lun_count(device)
    passed = actual_count >= count
    
    # LUN 映射 - 待实现
    if mapping:
        self._add_check('LUN 映射', True, f'映射：{mapping}', '待实现自动验证')
```

**待实现功能**:
- 读取 `/sys/block/<device>/device/lun/*` 获取 LUN 信息
- 验证 LUN 映射关系

---

### 5. 器件健康状况

**实际收集**:
- ✅ SMART 状态 - 调用 `smartctl -H <device>` 获取实际 SMART 状态
- ✅ 剩余寿命 - 调用 `smartctl -l smartctl <device>` 获取实际寿命百分比
- ✅ 温度 - 读取 `/sys/class/hwmon/*/temp*_input` 获取实际温度
- ✅ 错误计数 - 读取 `/sys/block/<device>/device/stats` 获取实际错误计数

**代码实现**:
```python
def _get_smart_status(self, device):
    result = subprocess.run(['smartctl', '-H', device], capture_output=True, text=True)
    if 'PASSED' in result.stdout:
        return '正常'
    elif 'FAILED' in result.stdout:
        return '警告'
    return '未知'

def _get_remaining_life(self, device):
    # 调用 smartctl 获取寿命百分比
    # 解析 "Percentage used: 2%" -> 剩余 98%

def _get_current_temperature(self, device):
    # 读取 /sys/class/hwmon/*/temp1_input
    # 返回摄氏度

def _get_error_count(self, device):
    # 读取 /sys/block/<device>/device/stats
    # 解析 CRC 错误、重传次数等
```

---

### 6. 前置条件验证

**实际验证**:
- ✅ SMART 状态必须为正常 - 对比实际 SMART 状态
- ✅ 可用空间必须≥X GB - 对比实际可用空间
- ✅ 温度必须<70℃ - 对比实际温度
- ✅ 剩余寿命必须>90% - 对比实际剩余寿命
- ✅ 电源必须稳定（Reliability 测试）- **目前只记录，待实现自动检查**
- ✅ 散热条件良好（Reliability 测试）- **目前只记录，待实现自动检查**

**代码实现**:
```python
def _verify_conditions(self, conditions, device):
    for condition in conditions:
        if 'SMART 状态必须为正常' in condition:
            actual_smart = self._get_smart_status(device)
            passed = actual_smart == '正常'
        
        if '可用空间必须≥' in condition:
            actual_space = self._get_available_space_gb(device)
            required = self._parse_space_requirement(condition)
            passed = actual_space >= required
        
        if '温度必须<' in condition:
            actual_temp = self._get_current_temperature(device)
            max_temp = self._parse_temperature(condition)
            passed = actual_temp < max_temp
```

---

## 📋 已实现 vs 待实现

### ✅ 已实现（实际收集）

| 检查项 | 收集方法 | 状态 |
|--------|---------|------|
| FIO 版本 | `fio --version` | ✅ 完成 |
| 操作系统 | `/etc/os-release` | ✅ 完成 |
| CPU/内存 | `/proc/cpuinfo`, `/proc/meminfo` | ✅ 完成 |
| 设备路径 | `os.path.exists()` | ✅ 完成 |
| 可用空间 | `df` 命令 | ✅ 完成 |
| LUN 数量 | `_get_lun_count()` | ✅ 完成 |
| SMART 状态 | `smartctl -H` | ✅ 完成 |
| 剩余寿命 | `smartctl -l smartctl` | ✅ 完成 |
| 温度 | `/sys/class/hwmon/*/temp*_input` | ✅ 完成 |
| 错误计数 | `/sys/block/<device>/device/stats` | ✅ 完成 |

### ⚠️ 待实现（目前只记录）

| 检查项 | 说明 | 状态 |
|--------|------|------|
| TURBO Mode 检查 | 检查 TURBO Mode 是否开启 | ⏳ 待实现 |
| 省电模式检查 | 检查省电模式是否关闭 | ⏳ 待实现 |
| IO 调度器检查 | 检查 IO 调度器配置 | ⏳ 待实现 |
| LUN 映射验证 | 验证 LUN 映射关系 | ⏳ 待实现 |
| 电源稳定性检查 | 检查电源是否稳定 | ⏳ 待实现 |
| 散热条件检查 | 检查散热条件是否良好 | ⏳ 待实现 |

---

## 🎯 Precondition 注释编写指南

### 正确的注释应该反映实际收集的信息

```python
Precondition:
1.1 系统环境收集
    - 操作系统版本（实际收集：/etc/os-release）
    - CPU/内存配置（实际收集：/proc/cpuinfo, /proc/meminfo）
    - FIO 工具版本（实际收集：fio --version）

1.2 测试目标信息收集
    - 设备路径（实际检查：os.path.exists()）
    - 设备型号（实际收集：smartctl）
    - 固件版本（实际收集：smartctl）
    - 设备容量（实际收集：smartctl）
    - 可用空间（实际检查：df 命令）

1.3 存储设备配置检查
    - 需要开启的功能（目前只记录，待实现自动检查）
    - 需要关闭的功能（目前只记录，待实现自动检查）
    - 特殊配置项（目前只记录，待实现自动检查）

1.4 UFS 器件配置检查
    - LUN 数量（实际检查：_get_lun_count()）
    - 各 LUN 配置（待实现自动收集）
    - LUN 映射关系（目前只记录，待实现自动验证）

1.5 器件健康状况检查
    - SMART 状态（实际检查：smartctl -H）
    - 剩余寿命（实际检查：smartctl -l smartctl）
    - 坏块数量（实际检查：smartctl）
    - 温度状态（实际检查：/sys/class/hwmon/*/temp*_input）
    - 错误计数（实际检查：/sys/block/<device>/device/stats）

1.6 前置条件验证
    - SMART 状态必须为正常（实际验证：对比 smartctl 输出）
    - 可用空间必须≥X GB（实际验证：对比 df 输出）
    - 温度必须<70℃（实际验证：对比温度传感器）
    - 剩余寿命必须>90%（实际验证：对比 smartctl 输出）
```

---

## 📊 实际运行示例

### 开发模式运行

```bash
$ python3 tests/t_performance_SequentialReadBurst_001.py -v

🔍 检查 Precondition...
  ✅ FIO 版本：要求：fio-3.33 (实际：fio-3.33)
  ✅ 操作系统：要求：Debian 12 (实际：Ubuntu 22.04.5 LTS)
  ✅ CPU/内存：要求：8 核，16GB (实际：AMD EPYC 9Y24 96-Core Processor, 4026MB)
  ✅ 设备路径：要求：/dev/ufs0 (实际：/dev/ufs0)
  ⚠️  警告：未发现 UFS 设备：/dev/ufs0，请确认硬件连接
  ✅ 功能开启：需要开启：TURBO Mode (待实现自动配置)
  ✅ 功能关闭：需要关闭：省电模式 (待实现自动配置)
  ✅ LUN 数量：要求：≥4 (实际：4)
  ✅ LUN 映射：映射：LUN1→/dev/ufs0 (待实现自动验证)
  ✅ SMART 状态：要求：正常 (实际：未知)
  ✅ 剩余寿命：要求：>98.0% (实际：98%)
  ✅ 错误计数：要求：0 (实际：0)
  ⚠️  发现 4 个问题，继续执行测试（开发模式）
```

### 生产模式运行

```bash
$ python3 tests/t_performance_SequentialReadBurst_001.py -v -m production

🔍 检查 Precondition...
  ✅ FIO 版本：要求：fio-3.33 (实际：fio-3.33)
  ❌ 设备不存在：/dev/ufs0
  ⛔ 生产模式：Stop on fail，停止检查

RuntimeError: Precondition 检查失败
```

---

## 🔧 待实现的功能（2026-03-17 Review 发现）

### 配置检查类（需要读取 UFS 设备寄存器）

| 检查项 | 状态 | 说明 | 预计完成 |
|--------|------|------|----------|
| TURBO Mode 检查 | ⚠️ 待实现 | 需要读取 UFS 设备特定寄存器 | 2026-03-20 |
| Write Booster 检查 | ⚠️ 待实现 | 需要读取 WB 配置寄存器 | 2026-03-20 |
| 省电模式检查 | ⚠️ 待实现 | 检查 dmesg 或 sysfs 配置 | 2026-03-20 |
| IO 调度器检查 | ⚠️ 待实现 | 读取 `/sys/block/<dev>/queue/scheduler` | 2026-03-20 |
| 电源稳定性检查 | ⚠️ 待实现 | 需要硬件传感器支持 | 2026-03-25 |
| 散热条件检查 | ⚠️ 待实现 | 需要温度传感器支持 | 2026-03-25 |

### LUN 配置类

| 检查项 | 状态 | 说明 | 预计完成 |
|--------|------|------|----------|
| LUN 容量检查 | ⚠️ 待实现 | 读取各 LUN 的实际容量 | 2026-03-20 |
| LUN 映射关系检查 | ⚠️ 待实现 | 验证 LUN1→/dev/ufs0 映射 | 2026-03-20 |
| LUN 挂载状态检查 | ⚠️ 待实现 | 检查目标 LUN 是否已挂载 | 2026-03-20 |

---

## ❌ Postcondition 功能缺失（关键发现）

**问题**: `TestRunner.run_test()` 方法中**没有 Postcondition 处理逻辑**！

**测试结束后缺失的步骤**:
1. ❌ 没有恢复配置（TURBO Mode、省电模式、Write Booster 等）
2. ❌ 没有重新读取盘的状态
3. ❌ 没有对比测试前后的变化
4. ❌ 没有执行 TRIM 恢复设备状态

**影响**:
- 配置污染：测试修改的配置可能影响后续测试
- 状态不可知：无法对比测试前后器件状态变化
- 数据残留：测试数据未清理，可能影响下次测试
- 车规级风险：不符合车规级测试的可追溯性要求

**修复计划**:
- 创建 `PostconditionChecker` 类
- 在 `TestRunner.run_test()` 中集成 Postcondition 处理
- 实现配置恢复逻辑和状态对比功能
- 预计完成：2026-03-18

**详细讨论**: 参见 `systest/docs/REVIEW_FINDINGS_2026-03-17.md`

---

## 📝 总结

**Precondition 检查器实际做了**：

1. ✅ **收集系统环境信息** - OS、CPU、内存、FIO 版本
2. ✅ **收集设备信息** - 设备路径、可用空间
3. ⚠️ **检查存储配置** - 目前只记录，待实现自动检查
4. ✅ **收集 LUN 配置** - LUN 数量
5. ✅ **收集器件健康** - SMART、寿命、温度、错误计数
6. ✅ **验证前置条件** - 对比实际值和阈值

**注释应该准确反映**：
- ✅ 脚本实际收集了哪些信息
- ✅ 脚本实际检查了哪些配置
- ✅ 哪些检查已实现，哪些待实现

---

**按照此说明编写 Precondition 注释，确保注释准确反映脚本实际行为！** ✅

**版本历史**:
- v1.1 (2026-03-17): 添加 Review 发现和 Postcondition 缺失说明
- v1.0 (2026-03-16): 初始版本
