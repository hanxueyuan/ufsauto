# SysTest - UFS 系统测试框架

统一测试入口、参数化执行、自动报告、失效分析

## 🚀 快速开始

### 1. 查看帮助

```bash
cd /path/to/SysTest
python3 bin/SysTest --help
```

### 2. 列出可用测试

```bash
python3 bin/SysTest list
```

### 3. 验证系统可用性

```bash
# 最小化验证（无需 FIO，验证核心功能）
python3 tests/minimal_validation.py

# 执行整个性能套件（需要 FIO 和 UFS 设备）
python3 bin/SysTest run -s performance -d /dev/ufs0

# 执行单个测试项
python3 bin/SysTest run -t seq_read_burst -d /dev/ufs0 -v
```

### 4. 查看报告

```bash
# 查看最新测试报告
python3 bin/SysTest report --latest

# 查看指定测试 ID 的报告
python3 bin/SysTest report --id=20260315_120000
```

### 5. 失效分析

```bash
python3 bin/SysTest analyze --id=20260315_120000
```

## 📋 命令参考

### run - 执行测试

```bash
python3 bin/SysTest run [选项]

选项:
  -t, --test      单个测试项名称
  -s, --suite     测试套件名称
  -d, --device    测试设备路径 (默认：/dev/ufs0)
  -o, --output    输出目录 (默认：./results)
  -f, --format    报告格式 (html/json) (默认：html)
  -c, --config    配置文件路径
  -v, --verbose   详细输出
  -n, --dry-run   模拟执行（不实际运行）
  -b, --background 后台执行
  --id            测试 ID (默认自动生成)
```

### list - 列出可用测试

```bash
python3 bin/SysTest list [-s 套件名称]
```

### report - 生成/查看报告

```bash
python3 bin/SysTest report [--id 测试 ID | --latest] [-f 格式]
```

### analyze - 失效分析

```bash
python3 bin/SysTest analyze --id 测试 ID [-o 输出路径]
```

### config - 配置管理

```bash
python3 bin/SysTest config --show   # 显示当前配置
python3 bin/SysTest config --init   # 初始化默认配置
```

## 📦 测试套件

| 套件名称 | 说明 | 测试项数 |
|---------|------|---------|
| performance | 性能测试 | 9 |
| qos | QoS 延迟测试 | 2 |
| reliability | 可靠性测试 | 1 |
| scenario | 场景化测试 | 2 |

## 📁 项目结构

```
SysTest/
├── bin/
│   └── SysTest              # 主入口脚本
├── core/
│   ├── runner.py            # 测试执行引擎
│   ├── collector.py         # 结果收集器
│   ├── reporter.py          # 报告生成器
│   └── analyzer.py          # 失效分析引擎
├── suites/
│   ├── performance/         # 性能测试套件
│   ├── qos/                 # QoS 测试套件
│   ├── reliability/         # 可靠性测试套件
│   └── scenario/            # 场景化测试套件
├── config/
│   └── default.json         # 默认配置
├── templates/               # 报告模板
├── utils/                   # 工具函数
└── results/                 # 测试结果输出
```

## ⚙️ 配置说明

编辑 `config/default.json` 自定义配置：

```json
{
  "execution": {
    "default_runtime": 60,      // 默认测试时间 (秒)
    "sustained_runtime": 300    // Sustained 测试时间 (秒)
  },
  "targets": {
    "seq_read_burst": 2100,     // 顺序读 Burst 目标 (MB/s)
    "seq_write_sustained": 250  // 顺序写 Sustained 目标 (MB/s)
  }
}
```

## 🔧 依赖

- Python 3.8+
- FIO 3.0+（性能测试工具）

### 安装 FIO

```bash
# Debian/Ubuntu
apt install fio

# CentOS/RHEL
yum install fio
```

## 📊 输出示例

### 测试结果目录

```
results/
└── 20260315_120000/
    ├── results.json          # 测试结果 JSON
    ├── report.html           # HTML 报告
    ├── summary.txt           # 文本摘要
    ├── analysis.md           # 失效分析报告
    └── raw/                  # 原始数据
        ├── seq_read_burst.json
        └── ...
```

### HTML 报告

包含：
- 测试摘要（总计/通过/失败/通过率）
- 测试结果表格
- 系统信息
- 设备信息

### 失效分析报告

包含：
- 根因分析（按置信度排序）
- 证据列表
- 建议措施

## 🎯 验收标准

基于产品开发目标：

| 性能指标 | Burst | Sustained | 单位 |
|---------|-------|-----------|------|
| 顺序读 | 2100 | 1800 | MB/s |
| 顺序写 | 1650 | 250 | MB/s |
| 随机读 | 200 | 105 | KIOPS |
| 随机写 | 330 | 60 | KIOPS |

## 📝 版本

v1.0.0 - 初始版本

## 📄 许可证

内部使用
