# UFS Auto - UFS 存储设备自动化测试框架

基于 Python 的 UFS 存储设备性能和质量测试自动化框架。

[![Status: Production Ready](https://img.shields.io/badge/status-production--ready-green)](.)
[![Python](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![FIO](https://img.shields.io/badge/fio-3.20+-orange.svg)](https://github.com/axboe/fio)

**特性：**
- ✅ 开发/生产模式切换
- ✅ 毫秒级时间戳日志
- ✅ 性能量化分析
- ✅ 自动生成测试报告
- ✅ 健康状态监控

---

## 🚀 快速开始

### 环境要求
- Python 3.8+
- FIO 3.20+
- Linux (ARM/x86)

### 检查环境

```bash
cd ufsauto
python3 systest/bin/systest.py check-env --save-config
```

### 运行测试

```bash
# 开发模式（快速验证，~2 分钟）
python3 systest/bin/systest.py run --suite performance

# 生产模式（完整测试，~50 分钟）
python3 systest/bin/systest.py run --suite performance --mode=production

# 单个测试
python3 systest/bin/systest.py run --test t_perf_SeqReadBurst_001
```

---

## 📋 使用示例

### 环境配置

```bash
# 查看当前配置
python3 systest/bin/systest.py config --show

# 设置设备路径
python3 systest/bin/systest.py config --device=/dev/sda

# 设置测试目录
python3 systest/bin/systest.py config --test-dir=/mapdata/ufs_test

# 重置配置
python3 systest/bin/systest.py config --reset
```

### 模式切换

```bash
# 查看当前模式
python3 systest/bin/systest.py mode

# 切换到开发模式（默认）
python3 systest/bin/systest.py mode --set=development

# 切换到生产模式
python3 systest/bin/systest.py mode --set=production

# 临时使用生产模式（不影响配置）
python3 systest/bin/systest.py run --suite performance --mode=production
```

### 运行测试

```bash
# 列出所有测试
python3 systest/bin/systest.py list

# 按套件列出测试
python3 systest/bin/systest.py list --suite performance
python3 systest/bin/systest.py list --suite qos

# 运行性能测试套件
python3 systest/bin/systest.py run --suite performance

# 运行 QoS 测试套件
python3 systest/bin/systest.py run --suite qos

# 运行单个测试
python3 systest/bin/systest.py run --test t_perf_SeqReadBurst_001

# 详细日志模式
python3 systest/bin/systest.py run --suite performance --verbose

# 自定义设备和测试目录
python3 systest/bin/systest.py run --suite performance \
  --device=/dev/sda \
  --test-dir=/mapdata/ufs_test

# 批量测试（运行 3 次，间隔 60 秒）
python3 systest/bin/systest.py run --suite performance \
  --batch=3 --interval=60

# 使用预设配置文件
python3 systest/bin/systest.py run --suite performance \
  --config=configs/ufs31_128GB.json
```

### 查看报告

```bash
# 查看最新报告
python3 systest/bin/systest.py report --latest

# 列出所有历史报告
python3 systest/bin/systest.py report --list

# 打开 HTML 报告（需要浏览器）
firefox results/systest_performance_*/report.html
```

### 健康状态检查

```bash
# 检查 UFS 设备健康状态
python3 systest/tools/health_monitor.py --device /dev/sda

# 扫描所有 UFS 设备
python3 systest/tools/health_monitor.py --scan
```

---

## 🧪 开发模式 vs 生产模式

| 特性 | 开发模式 | 生产模式 |
|------|----------|----------|
| 循环次数 | 2 次 | 10 次 |
| 测试时长 | 60 秒/次 | 300 秒/次 |
| 总测试时间 | ~2 分钟 | ~50 分钟 |
| 日志级别 | DEBUG | INFO |
| 保留文件 | 是 | 否 |
| 适用场景 | 开发调试 | 生产验证 |

---

## 📁 项目结构

```
ufsauto/
├── README.md              # 本文件
├── systest/               # 测试框架核心
│   ├── bin/              # 命令行入口
│   ├── config/           # 配置文件
│   ├── core/             # 核心模块
│   ├── suites/           # 测试套件
│   └── tools/            # 工具模块
├── scripts/              # 脚本工具
│   └── tools/           # 工具脚本
├── demos/                # 演示脚本
├── docs/                 # 文档
├── tools/                # Shell 工具
├── results/              # 测试结果
└── logs/                 # 日志文件
```

### 目录说明

| 目录 | 说明 |
|------|------|
| `systest/bin/` | 命令行入口 (systest.py) |
| `systest/core/` | 核心框架 (runner, collector, reporter, logger) |
| `systest/suites/` | 测试套件 (performance, qos) |
| `systest/tools/` | 工具模块 (health_monitor, fio_wrapper, ufs_utils) |
| `systest/config/` | 配置文件 (runtime.json) |
| `scripts/` | 辅助脚本 |
| `scripts/tools/` | 工具脚本 (chart_generator, report_generator) |
| `demos/` | 演示脚本 |
| `docs/` | 文档 |
| `results/` | 测试结果输出 |
| `logs/` | 日志文件 |

---

## 🆘 故障排查

### 常见问题

**Q: 测试失败，显示 "Device not found"**

```bash
# 检查设备路径
ls -la /dev/sd*

# 设置正确的设备路径
python3 systest/bin/systest.py config --device=/dev/sda
```

**Q: 显示 "Permission denied"**

```bash
# 使用 sudo 运行
sudo python3 systest/bin/systest.py run --suite performance

# 或者将用户加入 disk 组
sudo usermod -aG disk $USER
```

**Q: 显示 "FIO not found"**

```bash
# 请确认 FIO 已正确安装
which fio
```

**Q: 健康状态显示 "数据不完整"**

```bash
# 检查 UFS 设备是否存在
ls /sys/bus/ufs/devices/

# 查看设备健康信息
cat /sys/bus/ufs/devices/*/health_descriptor/*
```

---

## 📖 CLI 帮助

```bash
# 查看主帮助
python3 systest/bin/systest.py --help

# 查看 run 命令帮助
python3 systest/bin/systest.py run --help

# 查看 list 命令帮助
python3 systest/bin/systest.py list --help

# 查看 report 命令帮助
python3 systest/bin/systest.py report --help

# 查看 config 命令帮助
python3 systest/bin/systest.py config --help

# 查看 mode 命令帮助
python3 systest/bin/systest.py mode --help

# 查看 check-env 命令帮助
python3 systest/bin/systest.py check-env --help
```

---

## 📚 更多文档

- [模式切换演示](docs/MODE_SWITCH_DEMO.md)
- [改进报告](docs/IMPROVEMENT_REPORT.md)
- [UFS 健康状态调查报告](docs/ufs_health_investigation_report.md)
- [健康状态快速参考](docs/health_status_quick_reference.md)

---

**最后更新**: 2026-04-10  
**版本**: 1.0  
**状态**: Production Ready ✅
