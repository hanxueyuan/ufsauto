# 测试模式切换功能演示

## 📋 功能概述

实现了开发模式/生产模式切换功能，支持三种配置方式：
1. **配置文件**：`config/runtime.json`（持久化）
2. **环境变量**：`SYSTEST_MODE`（会话级）
3. **命令行参数**：`--mode`（一次性覆盖）

**优先级**：CLI 参数 > 环境变量 > 配置文件 > 默认值（development）

## 🚀 快速开始

### 1. 查看当前模式

```bash
cd systest
./bin/systest.py mode
```

输出示例：
```
=== Current Test Mode ===
Mode: Development
Config file: /path/to/systest/config/runtime.json

To change mode:
  python3 bin/systest.py mode --set=development
  python3 bin/systest.py mode --set=production

Or use environment variable:
  export SYSTEST_MODE=production

Or use command line argument:
  python3 bin/systest.py run --suite performance --mode=production
```

### 2. 切换到生产模式

```bash
./bin/systest.py mode --set=production
```

输出：
```
Test mode set to: Production
Configuration file: /path/to/systest/config/runtime.json
```

### 3. 切换回开发模式

```bash
./bin/systest.py mode --set=development
```

## 📊 模式差异对比

| 特性 | 开发模式 (Development) | 生产模式 (Production) |
|------|------------------------|------------------------|
| **测试时长** | 60s（短） | 300s+（长） |
| **测试次数** | 单次运行 | 多次迭代（3 次） |
| **日志级别** | DEBUG（详细） | INFO（简洁） |
| **报告详细度** | 简略摘要 | 完整详细报告 |
| **预检查** | 跳过部分验证 | 全部执行 |
| **清理行为** | 保留测试文件（便于调试） | 自动清理 |
| **适用场景** | 开发阶段快速迭代 | 部署前最终验证 |

## 💡 使用场景

### 场景 1：开发阶段快速测试

```bash
# 确保使用开发模式（默认）
./bin/systest.py mode --set=development

# 运行性能测试（快速，60s）
./bin/systest.py run --suite performance
```

### 场景 2：部署前最终验证

```bash
# 切换到生产模式
./bin/systest.py mode --set=production

# 运行完整的性能测试（300s+，更严格）
./bin/systest.py run --suite performance
```

### 场景 3：临时使用不同模式

```bash
# 当前是开发模式，临时用生产模式跑一次
./bin/systest.py run --suite performance --mode=production

# 或者使用环境变量
export SYSTEST_MODE=production
./bin/systest.py run --suite performance
unset SYSTEST_MODE
```

### 场景 4：查看模式信息

```bash
# 查看当前模式
./bin/systest.py mode

# 查看 run 命令帮助（包含 mode 参数说明）
./bin/systest.py run --help
```

## 🔧 配置文件示例

`config/runtime.json`：

```json
{
  "mode": "development",
  "device": "/dev/sda",
  "test_dir": "/mapdata/ufs_test",
  "device_capacity_gb": null,
  "env_checked_at": null,
  "system": {},
  "toolchain": {}
}
```

生产模式时修改为：

```json
{
  "mode": "production",
  "device": "/dev/sda",
  "test_dir": "/mapdata/ufs_test",
  ...
}
```

## 📝 启动日志示例

开发模式启动：
```
2026-04-10 10:16:00.123 [INFO] 测试模式：Development
2026-04-10 10:16:00.124 [INFO] Executing test suite: performance (Mode: Development)
2026-04-10 10:16:00.125 [INFO]   Test duration: 60s
2026-04-10 10:16:00.126 [INFO]   Iterations: 1
2026-04-10 10:16:00.127 [INFO]   Auto cleanup: False
```

生产模式启动：
```
2026-04-10 10:16:00.123 [INFO] 测试模式：Production
2026-04-10 10:16:00.124 [INFO] Executing test suite: performance (Mode: Production)
2026-04-10 10:16:00.125 [INFO]   Test duration: 300s
2026-04-10 10:16:00.126 [INFO]   Iterations: 3
2026-04-10 10:16:00.127 [INFO]   Auto cleanup: True
```

## ✅ 验证标准

- [x] **默认开发模式** - 不配置时默认为 development
- [x] **配置切换** - 修改 runtime.json 可以切换模式
- [x] **命令行切换** - `mode --set=production` 命令有效
- [x] **模式显示** - 启动时显示当前模式
- [x] **行为差异** - 开发和生产模式的测试参数确实不同
- [x] **环境变量支持** - `export SYSTEST_MODE=production` 有效
- [x] **CLI 参数覆盖** - `--mode=production` 可以临时覆盖配置

## 📚 相关文件

- `systest/config/runtime.json` - 配置文件（添加 mode 字段）
- `systest/bin/systest.py` - 主入口（添加 mode 子命令和--mode 参数）
- `systest/core/runner.py` - 测试执行器（根据模式调整参数）
- `systest/suites/performance/base.py` - 性能测试基类（根据模式调整测试时长）
