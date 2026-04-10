# UFS Auto 日志系统修复报告

## 📋 修复概述

根据用户反馈，修复了日志系统设计的两个主要问题：
1. Error Log 文件为空
2. 日志文件过于分散（每个测试创建 3 个文件）

## ✅ 修复内容

### 1. 移除 Error Log Handler

**文件**: `systest/core/logger.py`

**修改内容**:
- ✅ 删除 `_add_error_handler()` 方法
- ✅ 删除 `self.error_file` 相关代码
- ✅ 删除 `get_error_file()` 方法
- ✅ 所有日志统一输出到同一个 `.log` 文件

**修改前**:
```python
self.log_file = self.log_dir / f"{test_id}.log"
self.error_file = self.log_dir / f"{test_id}_error.log"

self._add_console_handler(console_level)
self._add_file_handler(file_level, max_bytes, backup_count)
self._add_error_handler(file_level, max_bytes, backup_count)  # ❌ 删除
```

**修改后**:
```python
self.log_file = self.log_dir / f"{test_id}.log"

self._add_console_handler(console_level)
self._add_file_handler(file_level, max_bytes, backup_count)
# ✅ 只保留两个 handler
```

### 2. 新增 FileFormatter 类

**文件**: `systest/core/logger.py`

**新增内容**:
```python
class FileFormatter(logging.Formatter):
    """File log formatter (with enhanced detail)

    格式：2024-08-26 21:04:50.123 - logger_name - LEVEL - [完整路径：行号] - 消息
    ERROR 级别及以上自动输出完整堆栈信息
    """
    
    def format(self, record: logging.LogRecord) -> str:
        # 包含完整路径、毫秒级时间戳
        # ERROR 级别自动附加堆栈跟踪
```

**优势**:
- ✅ 包含完整文件路径（pathname 而非 filename）
- ✅ 毫秒级时间戳
- ✅ ERROR 级别自动记录堆栈跟踪
- ✅ 统一的日志格式

### 3. 增强错误信息记录

**文件**: `systest/bin/systest.py`

**修改内容**:
```python
# 修改前
logger.error(f"Error log: {logger.get_error_file()}")  # ❌ 引用不存在的 error_file

# 修改后
logger.error(f"测试执行失败：{e}", exc_info=True)  # ✅ 记录到日志文件
logger.critical(f"Test execution failed: {e}", exc_info=True)  # ✅ 双重记录
```

**文件**: `systest/core/runner.py`

**修改内容**:
```python
# 修改前
self.logger.error(f"Test execution failed {self.name}: {e}", exc_info=True)

# 修改后
self.logger.error(f"测试执行失败 {self.name}: {e}", exc_info=True)  # ✅ 中文错误信息
self.logger.critical(f"Test execution failed {self.name}: {type(e).__name__}: {e}", exc_info=True)  # ✅ 详细错误
```

### 4. 优化日志格式

**文件**: `systest/core/logger.py`

**ConsoleFormatter** (终端输出):
```
2024-08-26 21:04:50.123 [INFO] [base.py:156] 消息内容
```
- ✅ 彩色输出（不同级别不同颜色）
- ✅ 简洁格式（只显示文件名）
- ✅ 毫秒级时间戳

**FileFormatter** (文件输出):
```
2024-08-26 21:04:50.123 - systest.test - INFO - [/path/to/file.py:156] - 消息内容
```
- ✅ 详细信息（完整路径）
- ✅ 包含 logger 名称
- ✅ 毫秒级时间戳
- ✅ ERROR 级别自动附加堆栈跟踪

## 📊 修复效果对比

### 修复前

```bash
$ ls -la logs/
-rw-r--r-- 1 user user 10240 SysTest_performance_20260410_120000.log
-rw-r--r-- 1 user user     0 SysTest_performance_20260410_120000_error.log  # ❌ 空文件
-rw-r--r-- 1 user user  5120 SysTest_performance_20260410_120000.json
```

**问题**:
- ❌ `_error.log` 文件为空
- ❌ 需要查看多个文件
- ❌ 错误信息可能只通过 print() 输出

### 修复后

```bash
$ ls -la logs/
-rw-r--r-- 1 user user 15360 SysTest_performance_20260410_120000.log  # ✅ 所有日志
-rw-r--r-- 1 user user  5120 SysTest_performance_20260410_120000.json
```

**优势**:
- ✅ 只创建 `.log` 文件（不再创建 `_error.log`）
- ✅ 所有级别日志都在同一个文件中
- ✅ 日志文件包含完整信息（包括 ERROR 级别堆栈）

## 📝 日志内容样例

### 终端输出 (ConsoleFormatter)

```
2026-04-10 12:15:30.123 [INFO] [systest.py:100] 测试模式：Development
2026-04-10 12:15:30.456 [DEBUG] [runner.py:250] 执行测试：t_perf_SeqRead_001
2026-04-10 12:15:31.789 [WARNING] [base.py:89] 设备路径未指定，使用默认值
2026-04-10 12:15:32.012 [ERROR] [runner.py:320] 测试执行失败：Permission denied
Traceback (most recent call last):
  File "/workspace/projects/ufsauto/systest/core/runner.py", line 320, in run_suite
    result = test_instance.run()
  ...
```

### 文件输出 (FileFormatter)

```
2026-04-10 12:15:30.123 - systest.test - INFO - [/workspace/projects/ufsauto/systest/bin/systest.py:100] - 测试模式：Development
2026-04-10 12:15:30.456 - systest.test - DEBUG - [/workspace/projects/ufsauto/systest/core/runner.py:250] - 执行测试：t_perf_SeqRead_001
2026-04-10 12:15:31.789 - systest.test - WARNING - [/workspace/projects/ufsauto/systest/core/base.py:89] - 设备路径未指定，使用默认值
2026-04-10 12:15:32.012 - systest.test - ERROR - [/workspace/projects/ufsauto/systest/core/runner.py:320] - 测试执行失败：Permission denied
Traceback (most recent call last):
  File "/workspace/projects/ufsauto/systest/core/runner.py", line 320, in run_suite
    result = test_instance.run()
  ...
```

## ✅ 验收标准完成情况

### 1. 日志文件
- [x] 只创建 .log 文件（不再创建 _error.log）
- [x] 所有级别日志都在同一个文件中
- [x] 日志文件包含完整信息

### 2. 错误记录
- [x] 错误信息通过 logger.error() 记录
- [x] 错误信息包含堆栈跟踪 (exc_info=True)
- [x] 终端输出和日志文件都有错误信息

### 3. 日志格式
- [x] 包含时间戳（毫秒级）
- [x] 包含日志级别
- [x] 包含来源文件和行号
- [x] 格式统一（ConsoleFormatter 和 FileFormatter）

## 🔧 修改的文件列表

1. **systest/core/logger.py**
   - 删除 `_add_error_handler()` 方法
   - 删除 `self.error_file` 初始化
   - 删除 `get_error_file()` 方法
   - 新增 `FileFormatter` 类
   - 更新 `_add_file_handler()` 使用 FileFormatter

2. **systest/bin/systest.py**
   - 移除 `logger.get_error_file()` 引用
   - 增强异常处理中的 `logger.error()` 调用
   - 更新错误提示信息

3. **systest/core/runner.py**
   - 增强异常处理中的 `logger.error()` 和 `logger.critical()` 调用
   - 更新 `print_debug_tips()` 函数移除 error.log 引用
   - 改进错误信息格式（包含异常类型）

## 🚀 后续建议

1. **日志轮转**: 当前已支持 RotatingFileHandler，可根据需要调整 `max_bytes` 和 `backup_count`
2. **日志级别控制**: 通过 `console_level` 和 `file_level` 参数灵活控制
3. **JSON 格式**: 保留 `enable_json` 选项，可用于结构化日志分析
4. **日志分析**: 可考虑集成 ELK 或其他日志分析工具

## 📌 Git 提交

```bash
cd /workspace/projects/ufsauto
git add systest/core/logger.py systest/bin/systest.py systest/core/runner.py
git commit -m "fix: 统一日志输出，移除空 error.log 文件

- 删除 _add_error_handler() 方法和 error_file 相关代码
- 新增 FileFormatter 类，提供更详细的文件日志格式
- 所有日志统一输出到同一个 .log 文件
- 增强错误信息记录，确保 ERROR 级别包含堆栈跟踪
- 优化日志格式，包含毫秒级时间戳和完整路径
- 更新 systest.py 和 runner.py 中的错误处理"
git push origin master
```

## 🎯 总结

本次修复成功解决了日志系统的两个主要问题：
1. **消除了空的 error.log 文件** - 通过移除独立的 Error Handler
2. **简化了日志文件结构** - 从 3 个文件减少到 2 个（.log + .json）

同时增强了日志系统的功能：
- ✅ 统一的日志格式
- ✅ 更详细的文件日志（完整路径、毫秒级时间戳）
- ✅ 改进的错误记录（自动堆栈跟踪）
- ✅ 更好的用户体验（终端彩色输出、简洁格式）

修复后的日志系统更简洁、更高效、更易于维护。
