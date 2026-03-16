# systest 快速参考卡片

## 🚀 常用命令

### 基础命令

```bash
# 查看帮助
python3 bin/systest --help

# 查看版本
python3 bin/systest --version

# 列出所有测试
python3 bin/systest list
```

### 执行测试

```bash
# 最小化验证（验证核心功能，无需 FIO）
python3 tests/minimal_validation.py

# 执行性能测试套件
python3 bin/systest run -s performance -d /dev/ufs0 -v

# 执行单个测试项
python3 bin/systest run -t t_performance_sequential_read_burst_001 -d /dev/ufs0 -v

# 执行并生成多种格式报告
python3 bin/systest run -s performance -d /dev/ufs0 --format html,json,text
```

### 查看结果

```bash
# 查看最新测试摘要
python3 bin/systest report --latest

# 查看指定测试 ID 的报告
python3 bin/systest report --id=20260316_090000

# 失效分析
python3 bin/systest analyze --id=20260316_090000
```

### 配置管理

```bash
# 查看当前配置
python3 bin/systest config --show

# 初始化默认配置
python3 bin/systest config --init
```

---

## 📁 测试套件

| 套件 | 命令 | 测试项数 | 预计时间 |
|------|------|---------|---------|
| 性能测试 | `-s performance` | 9 | 25 分钟 |
| QoS 测试 | `-s qos` | 2 | 10 分钟 |
| 可靠性测试 | `-s reliability` | 1 | 24 小时 |
| 场景测试 | `-s scenario` | 2 | 10 分钟 |

---

## 🎯 验收标准（性能套件）

| 测试项 | 目标值 | 单位 |
|--------|--------|------|
| t_performance_sequential_read_burst_001 | ≥2100 | MB/s |
| t_performance_sequential_read_sustained_002 | ≥1800 | MB/s |
| t_performance_sequential_write_burst_003 | ≥1650 | MB/s |
| t_performance_sequential_write_sustained_004 | ≥250 | MB/s |
| t_performance_random_read_burst_005 | ≥200 | KIOPS |
| t_performance_random_read_sustained_006 | ≥105 | KIOPS |
| t_performance_random_write_burst_007 | ≥330 | KIOPS |
| t_performance_random_write_sustained_008 | ≥60 | KIOPS |

---

## 📊 结果位置

```
results/
└── YYYYMMDD_HHMMSS/
    ├── results.json    # 完整结果
    ├── report.html     # HTML 报告
    ├── summary.txt     # 文本摘要
    └── raw/            # FIO 原始数据
```

---

## 🔧 常用参数

| 参数 | 简写 | 说明 |
|------|------|------|
| `--suite` | `-s` | 测试套件名称 |
| `--test` | `-t` | 单个测试项名称 |
| `--device` | `-d` | 测试设备路径 |
| `--output` | `-o` | 输出目录 |
| `--format` | `-f` | 报告格式 |
| `--verbose` | `-v` | 详细输出 |
| `--background` | `-b` | 后台执行 |

---

## ⚠️ 注意事项

1. **需要 root 权限**访问 UFS 设备
2. **测试会擦除数据**，确保设备无重要数据
3. **干跑模式**用于验证配置，不实际执行
4. **长时间测试**注意散热和电源稳定

---

## 💡 快速开始

```bash
# 1. 最小化验证（无需 FIO）
python3 tests/minimal_validation.py

# 2. 执行实际测试
python3 bin/systest run -s performance -d /dev/ufs0 -v

# 3. 查看结果
python3 bin/systest report --latest

# 4. 失效分析（如果有失败）
python3 bin/systest analyze --latest
```

---

**版本**: v1.0.0  
**打印建议**: 此文档适合打印为 A4 快速参考卡片
