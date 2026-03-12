# UFS 3.1 车规项目 Python 编码规范

## 1. 总则
- 符合 PEP 8 编码规范
- 符合车规级软件可靠性要求
- 代码必须可预测、可测试、可维护
- 优先使用 Python 3.10+ 版本

## 2. 语言特性限制
### 2.1 允许使用的特性
- 类型注解
- dataclasses
- enum.Enum
- contextlib
- 异常处理（有限制）
- 类型提示检查（mypy）

### 2.2 禁止使用的特性
- ❌ 动态类型修改（setattr, getattr 等）
- ❌ eval/exec 函数
- ❌ 猴子补丁
- ❌ 全局变量（除非是常量）
- ❌ 隐式类型转换
- ❌ 递归调用
- ❌ 反射机制（除非必要）
- ❌ 垃圾回收器手动干预
- ❌ 多线程（GIL 问题，优先使用多进程）
- ❌ 动态导入（__import__）

## 3. 命名规范
- **模块名**：小写字母 + 下划线，如 `ufs_test.py`, `perf_analyze.py`
- **类名**：大驼峰式，如 `UfsDevice`, `PerfTester`
- **函数名**：小写字母 + 下划线，如 `read_sector`, `run_perf_test`
- **变量名**：小写字母 + 下划线，如 `sector_count`, `transfer_len`
- **常量**：大写字母 + 下划线，如 `UFS_SECTOR_SIZE`, `MAX_TRANSFER_LEN`
- **异常名**：大驼峰式，后缀为 Error，如 `UfsTransferError`, `InvalidParamError`

## 4. 格式规范
- 缩进：4 个空格
- 行宽：最大 120 个字符
- 引号：优先使用单引号，多行字符串使用双引号
- 导入顺序：标准库 → 第三方库 → 项目内部库，空行分隔
- 每行最多一个语句
- 避免尾随空格

示例：
```python
import os
import sys
from dataclasses import dataclass
from typing import List, Optional

import serial
import pytest

from ufs.constants import UFS_SECTOR_SIZE, MAX_SECTOR_PER_TRANSFER
from ufs.exceptions import UfsTransferError

@dataclass
class UfsCommand:
    cmd: int
    lba: int
    length: int
    data: Optional[bytes] = None

def read_sector(dev: serial.Serial, lba: int, sector_count: int = 1) -> bytes:
    """读取UFS设备扇区"""
    if sector_count <= 0 or sector_count > MAX_SECTOR_PER_TRANSFER:
        raise ValueError(f"Invalid sector count: {sector_count}")
    
    cmd = UfsCommand(cmd=0x01, lba=lba, length=sector_count * UFS_SECTOR_SIZE)
    response = send_command(dev, cmd)
    
    if response.status != 0:
        raise UfsTransferError(f"Read failed, status: {response.status}")
    
    return response.data
```

## 5. 类型注解
- 所有函数参数必须有类型注解
- 函数返回值必须有类型注解
- 复杂类型使用 typing 模块
- 变量类型注解可选，但推荐使用

示例：
```python
from typing import List, Dict, Optional, Tuple

def process_data(data: bytes) -> Tuple[bool, int]:
    """处理数据，返回(成功, 处理长度)"""
    if len(data) < 4:
        return False, 0
    return True, len(data)

def get_device_info(dev: serial.Serial) -> Dict[str, str]:
    """获取设备信息"""
    info = {}
    info["model"] = read_model(dev)
    info["firmware"] = read_firmware_version(dev)
    return info
```

## 6. 注释规范
- 函数必须有 docstring，说明功能、参数、返回值、异常
- 复杂算法必须注释说明逻辑
- 关键变量注释说明含义和取值范围
- 禁止无用注释，禁止注释掉的代码提交
- docstring 遵循 Google 风格

示例：
```python
def read_sector(dev: serial.Serial, lba: int, sector_count: int = 1) -> bytes:
    """
    读取UFS设备扇区数据
    
    Args:
        dev: UFS设备串口句柄
        lba: 起始逻辑块地址
        sector_count: 要读取的扇区数量，默认1
    
    Returns:
        bytes: 读取到的数据
    
    Raises:
        ValueError: 参数无效
        UfsTransferError: 传输失败
        TimeoutError: 读取超时
    
    Note:
        最大支持单次读取256个扇区
    """
    pass
```

## 7. 错误处理
- 禁止使用裸 except 语句，必须捕获明确的异常类型
- 异常处理必须具体，禁止忽略异常
- 资源必须使用 with 语句管理
- 错误信息必须明确，便于定位问题
- 外部输入必须做严格校验

正确示例：
```python
def read_config(path: str) -> dict:
    try:
        with open(path, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        raise ConfigError(f"Config file not found: {path}")
    except json.JSONDecodeError as e:
        raise ConfigError(f"Invalid config format: {e}")
```

错误示例：
```python
def read_config(path: str) -> dict:
    try:
        f = open(path, 'r')
        return json.load(f)  # 没有关闭文件
    except:  # 裸except，捕获所有异常
        return {}  # 忽略错误，返回空字典
```

## 8. 安全规范
- 禁止硬编码敏感信息（密码、密钥等）
- 所有外部输入必须校验
- 禁止执行外部命令（subprocess 除非必要，且必须严格校验参数）
- 文件路径必须做校验，防止路径遍历攻击
- 禁止使用 pickle 序列化/反序列化不可信数据

## 9. 可测试性要求
- 所有函数必须可单元测试
- 硬件相关代码必须有抽象层
- 依赖注入方式，方便 Mock 测试
- 关键路径必须有测试点
- 日志记录规范，便于调试

## 10. 性能要求
- 避免不必要的对象创建
- 大数据处理使用生成器，避免内存占用过高
- 循环内避免重复计算
- 字符串拼接优先使用 f-string 或 join
- I/O 操作使用异步或批量处理

## 11. 工具配置
### flake8 配置
```ini
[flake8]
max-line-length = 120
exclude = .git,__pycache__,venv
ignore = E203, W503
```

### mypy 配置
```ini
[mypy]
python_version = 3.10
strict = True
ignore_missing_imports = True
disallow_untyped_defs = True
disallow_incomplete_defs = True
```

### bandit 配置
```ini
[bandit]
exclude_dirs = tests,venv
skips = B101
```
