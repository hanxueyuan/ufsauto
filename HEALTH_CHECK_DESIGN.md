# 存储设备健康检查设计说明

## 📊 问题背景

### 当前问题

开发板上频繁出现警告：
```
UFS health directory not found
Postcondition check skipped: Health status data incomplete
```

### 根本原因

1. **强依赖 UFS sysfs 路径** ❌
   - 代码试图读取 `/sys/class/ufs/*/health_descriptor/`
   - 很多开发板没有这个目录结构
   - UFS 驱动不一定暴露健康信息

2. **设备类型判断困难** ❌
   - 无法可靠判断设备是否为 UFS
   - eMMC、NVMe、SATA 设备没有 UFS 健康信息
   - 不同平台 sysfs 路径不同

3. **健康检查过于频繁** ❌
   - 每个测试用例前后都检查
   - 每次找不到都打印警告
   - 干扰正常测试日志

---

## ✅ 设计原则

### 1. 健康检查是可选功能

**设计决策**：
- ✅ 健康检查不应阻塞测试执行
- ✅ 找不到健康信息时静默处理
- ✅ 默认假设设备健康状态为 OK

**理由**：
- 不是所有平台都支持 UFS 健康信息
- 健康检查是"锦上添花"，不是"必需功能"
- 测试框架应该在不支持的设备上也能正常工作

---

### 2. 通用设备支持

**设计决策**：
- ✅ 支持多种存储设备类型（UFS、eMMC、NVMe、SATA）
- ✅ 不强制依赖特定设备的健康信息
- ✅ 使用通用的设备检测方法

**理由**：
- 测试框架应该适用于不同硬件平台
- 不同设备类型有不同的健康信息接口
- 统一抽象，避免设备类型硬编码

---

### 3. 静默失败原则

**设计决策**：
- ✅ 健康信息获取失败时不打印警告
- ✅ 只在调试模式下记录详细日志
- ✅ 只在检测到实际健康问题时报告

**理由**：
- 避免日志污染
- 减少用户困惑
- 关注真正重要的问题

---

## 🔧 实现方案

### 修改前

```python
def get_health_status(self) -> Dict[str, Any]:
    self.logger.info("Getting UFS device health status...")  # ❌ 每次都记录
    
    health_dir = self._find_ufs_health_dir()
    if not health_dir:
        self.logger.warning("UFS health directory not found")  # ❌ 警告干扰
    
    # ... 读取健康信息
```

### 修改后

```python
def get_health_status(self) -> Dict[str, Any]:
    # 默认健康状态（假设 OK）
    health = {
        'status': 'OK',
        'pre_eol_info': 'N/A',
        'device_life_time_est_a': 'N/A',
        'device_life_time_est_b': 'N/A',
        'critical_warning': 0
    }
    
    # 尝试读取 sysfs（可选功能）
    health_dir = self._find_ufs_health_dir()
    if health_dir:
        try:
            # 读取健康信息
            ...
        except Exception as e:
            self.logger.debug(f"Failed to read health status: {e}")  # ✅ 调试级别
    
    # 只在有实际信息时记录
    if health['status'] != 'OK' or health['pre_eol_info'] != 'N/A':
        self.logger.debug(f"Health status: {health['status']}")  # ✅ 静默
```

---

## 📋 健康检查流程

### 测试前检查

```python
# 记录健康基线（可选）
self._pre_test_health = ufs.get_health_status()
# 返回：{'status': 'OK', 'pre_eol_info': 'N/A', ...}
```

**行为**：
- ✅ 总是返回数据（至少有默认值）
- ✅ 不阻塞测试执行
- ✅ 静默处理（无警告）

---

### 测试后检查

```python
# 检查健康状态变化
self._check_postcondition()
```

**检查内容**：
- ✅ 健康状态是否恶化（OK → WARNING）
- ✅ 是否有新的 critical warning
- ✅ pre-EOL 状态是否变化

**行为**：
- ✅ 只在检测到问题时记录失败
- ✅ 健康信息缺失时跳过检查（不警告）
- ✅ 记录失败但不阻塞测试（Fail-Continue 模式）

---

## 🎯 设备类型判断

### 当前方法（不可靠）

```bash
# 尝试从 dmesg 判断
dmesg | grep ufshcd  # 不一定有输出
```

**问题**：
- ❌ dmesg 可能被清空
- ❌ 驱动可能不打印启动信息
- ❌ 不同平台输出格式不同

---

### 改进方法（推荐）

```bash
# 1. 检查 sysfs 路径
ls /sys/class/ufs/  # UFS 设备

ls /sys/class/mmc_host/  # eMMC 设备

ls /sys/class/nvme/  # NVMe 设备
```

**但**：
- ✅ 即使知道设备类型，也不强制要求健康信息
- ✅ 健康检查仍然是可选功能

---

## 📊 日志输出对比

### 修改前（每个测试用例）

```
INFO  Getting UFS device health status...
WARNING  UFS health directory not found
INFO  Health status: OK
...
WARNING  Postcondition check skipped: Health status data incomplete
```

### 修改后（静默）

```
# 无输出（健康信息不可用时）
```

**或**（有健康信息时）：
```
DEBUG  Health status: OK
DEBUG  Postcondition check passed
```

---

## ✅ 预期效果

### 开发板测试

**修改前**：
```
每个测试用例打印 2 次警告
5 个用例 = 10 次警告
```

**修改后**：
```
无警告输出
```

### 支持 UFS 健康信息的平台

**修改前**：
```
INFO  Getting UFS device health status...
INFO  Health status: OK
```

**修改后**：
```
DEBUG  Health status: OK  # 只在调试模式可见
```

---

## 🔄 未来扩展

### 可选的健康检查接口

```python
class HealthChecker:
    """可插拔的健康检查器"""
    
    def check(self) -> Dict[str, Any]:
        raise NotImplementedError
    
    def is_available(self) -> bool:
        """检查此平台是否支持健康检查"""
        raise NotImplementedError


class UFSHealthChecker(HealthChecker):
    """UFS 健康检查器"""
    ...


class NVMeHealthChecker(HealthChecker):
    """NVMe 健康检查器（通过 SMART）"""
    ...


class DummyHealthChecker(HealthChecker):
    """空实现（不支持健康检查的平台）"""
    def check(self):
        return {'status': 'OK'}
    
    def is_available(self):
        return False
```

---

## 📝 总结

### 设计决策

| 问题 | 旧设计 | 新设计 |
|------|--------|--------|
| **健康检查** | 必需功能 | 可选功能 |
| **失败处理** | 打印警告 | 静默处理 |
| **设备类型** | 强依赖 UFS | 通用支持 |
| **日志输出** | 每次都记录 | 只在必要时 |

### 核心原则

1. **不阻塞** - 健康检查不应阻塞测试执行
2. **不干扰** - 不输出无意义的警告
3. **不强制** - 支持不同硬件平台
4. **可扩展** - 易于添加新的健康检查器

---

**设计文档完成时间**: 2026-04-09 10:23  
**适用范围**: 所有存储设备测试平台
