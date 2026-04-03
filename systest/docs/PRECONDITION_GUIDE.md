# Precondition 检查器设计说明

**文档状态**: 设计说明  
**创建时间**: 2026-03-21  
**适用范围**: SysTest 测试框架

---

## 📋 设计定位澄清

### ❌ 错误理解（已废弃）

Precondition 检查器 **不是** 运行时组件，即：
- ❌ 不是测试执行时的依赖模块
- ❌ 不是每个测试用例必须导入的检查器
- ❌ 不是测试框架的核心组件

### ✅ 正确理解（当前设计）

Precondition 相关功能分为两个层面：

---

## 1️⃣ 测试脚本内部的 Precondition 检查

**位置**: 每个测试用例的 `setup()` 方法中

**职责**: 测试前确保环境满足要求

**示例**:
```python
class Test(TestCase):
    def setup(self) -> bool:
        """测试前准备 - 检查前置条件"""
        self.logger.info("检查前置条件...")
        
        # 1.1 检查设备是否存在
        if not Path(self.device).exists():
            self.logger.error(f"设备不存在：{self.device}")
            return False
        
        # 1.2 检查空间是否足够（至少 2GB）
        stat = os.statvfs('/tmp')
        available_gb = (stat.f_bavail * stat.f_frsize) / (1024**3)
        if available_gb < 2:
            self.logger.error(f"可用空间不足：{available_gb:.1f}GB < 2GB")
            return False
        
        # 1.3 检查 FIO 是否安装
        result = subprocess.run(['which', 'fio'], capture_output=True)
        if result.returncode != 0:
            self.logger.error("FIO 工具未安装")
            return False
        
        # 1.4 检查权限
        if not os.access(self.device, os.R_OK | os.W_OK):
            self.logger.error(f"设备权限不足：{self.device}")
            return False
        
        self.logger.info("前置条件检查通过")
        return True
```

**设计原则**:
- ✅ 每个测试用例对自己的 precondition 负责
- ✅ 检查逻辑写在 `setup()` 方法中
- ✅ 使用 `self.logger` 记录检查过程
- ✅ 检查失败返回 `False`，测试自动跳过

---

## 2️⃣ Precondition 检查器（QA 静态检查工具）

**位置**: 独立的 QA 工具（如 `tools/check_precondition.py`）

**职责**: 静态分析测试脚本，验证是否包含必要的 precondition 检查

**使用场景**:
- CI/CD 流水线中的代码质量检查
- 提交前的自动化审查
- 测试用例规范性验证

**检查内容**:
```python
# 伪代码示例
def check_test_script(script_path: str) -> Checklist:
    """检查测试脚本是否包含必要的 precondition 检查"""
    
    checks = {
        'has_setup_method': False,      # 是否有 setup() 方法
        'checks_device': False,         # 是否检查设备存在
        'checks_space': False,          # 是否检查可用空间
        'checks_fio': False,            # 是否检查 FIO 工具
        'checks_permission': False,     # 是否检查权限
        'has_logging': False,           # 是否有日志记录
        'has_error_handling': False,    # 是否有错误处理
    }
    
    # 静态分析代码...
    
    return checks
```

**输出示例**:
```
=== Precondition 检查报告 ===

测试脚本：t_perf_SeqReadBurst_001.py

✅ 有 setup() 方法
✅ 检查设备存在性
✅ 检查可用空间
❌ 未检查 FIO 工具
✅ 检查权限
✅ 有日志记录
✅ 有错误处理

通过率：6/7 (85.7%)
建议：添加 FIO 工具检查
```

**设计原则**:
- ✅ 独立工具，不影响测试执行
- ✅ 可选运行，不强制
- ✅ 提供改进建议，而非强制失败
- ✅ 集成到 CI/CD，而非开发流程

---

## 📊 两者对比

| 维度 | 脚本内部检查 | QA 静态检查器 |
|------|------------|-------------|
| **执行时机** | 测试运行时 | 代码审查/CI 时 |
| **位置** | `setup()` 方法 | 独立工具 |
| **目的** | 确保测试环境正常 | 确保代码质量 |
| **失败后果** | 测试跳过 | 警告/建议 |
| **必要性** | 必须 | 可选 |

---

## 🎯 当前实现状态

### ✅ 已完成
- [x] 日志系统（`core/logger.py`）
- [x] 测试用例基类支持 logger 注入
- [x] 示例脚本（`t_perf_SeqReadBurst_001.py`）

### ⏳ 待完成
- [ ] 更新其他 4 个测试用例，添加完整的 precondition 检查
- [ ] 创建 QA 静态检查器工具（可选）
- [ ] 集成到 CI/CD 流水线

---

## 📝 测试脚本 Precondition 检查清单

每个测试用例的 `setup()` 应该包含以下检查（适用时）：

### 基础检查（所有测试）
- [ ] 设备文件存在 (`/dev/ufs0`)
- [ ] 可用空间足够（至少 2GB）
- [ ] FIO 工具已安装
- [ ] 当前用户有读写权限

### 性能测试特有检查
- [ ] 设备未挂载为只读
- [ ] 没有其他 FIO 进程在运行
- [ ] CPU 频率 governor 设置为 performance（可选）

### QoS 测试特有检查
- [ ] 系统负载较低（可选）
- [ ] 温度在正常范围内（可选）

---

## 🔧 示例代码模板

```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试用例：t_perf_SeqReadBurst_001
测试目的：验证顺序读 Burst 性能
"""

import os
import subprocess
from pathlib import Path
from runner import TestCase


class Test(TestCase):
    def setup(self) -> bool:
        """测试前准备 - 检查前置条件"""
        self.logger.info("开始检查前置条件...")
        
        # 1.1 检查设备是否存在
        if not Path(self.device).exists():
            self.logger.error(f"设备不存在：{self.device}")
            return False
        self.logger.debug(f"设备存在：{self.device}")
        
        # 1.2 检查可用空间（至少 2GB）
        stat = os.statvfs('/tmp')
        available_gb = (stat.f_bavail * stat.f_frsize) / (1024**3)
        if available_gb < 2:
            self.logger.error(f"可用空间不足：{available_gb:.1f}GB")
            return False
        self.logger.debug(f"可用空间：{available_gb:.1f}GB")
        
        # 1.3 检查 FIO 工具
        result = subprocess.run(['which', 'fio'], capture_output=True)
        if result.returncode != 0:
            self.logger.error("FIO 工具未安装")
            return False
        self.logger.debug("FIO 工具已安装")
        
        # 1.4 检查权限
        if not os.access(self.device, os.R_OK | os.W_OK):
            self.logger.error(f"设备权限不足：{self.device}")
            return False
        self.logger.debug(f"设备权限正常：{self.device}")
        
        self.logger.info("前置条件检查通过")
        return True
```

---

## 📚 相关文档

- [测试用例命名规范](../../docs/README_NAMING.md)
- [测试框架设计文档](README.md)
- [日志系统使用指南](LOGGER_GUIDE.md)

---

**文档维护**: UFS 项目组  
**最后更新**: 2026-03-21
