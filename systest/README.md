# SysTest - UFS 3.1 车规级存储系统测试框架

**版本**: v1.0.0  
**状态**: 生产就绪 ✅  
**适用范围**: UFS 3.1 车规级存储系统

---

## 🚀 快速开始

### 1. 环境准备

```bash
# 安装依赖
sudo apt-get update
sudo apt-get install -y fio python3 python3-pip

# 克隆项目
git clone https://github.com/hanxueyuan/ufsauto.git
cd ufsauto/systest
```

### 0. 环境检查（推荐）

```bash
# 检查环境配置（开发板：Debian 12, ARM64, FIO 3.33）
python3 bin/SysTest check-env -v

# 生成环境报告
python3 bin/SysTest check-env --report
```

### 2. 查看可用测试

```bash
python3 bin/SysTest list
```

### 3. 执行测试

```bash
# 执行完整性能测试套件
python3 bin/SysTest run --suite=performance --device=/dev/ufs0 -v

# 执行单个测试
python3 bin/SysTest run --test=t_perf_SeqReadBurst_001 --device=/dev/ufs0 -v

# 模拟执行（不实际运行）
python3 bin/SysTest run --suite=performance --dry-run
```

### 4. 查看报告

```bash
# 查看最新报告
python3 bin/SysTest report --latest

# 在浏览器打开
python3 bin/SysTest report --latest --open
```

---

## 📋 测试套件

### Performance（性能测试）

| 用例 ID | 测试名称 | 目标 | 验收标准 |
|--------|---------|------|---------|
| t_perf_SeqReadBurst_001 | 顺序读 Burst | ≥2100 MB/s | 带宽达标 |
| t_perf_SeqWriteBurst_003 | 顺序写 Burst | ≥1650 MB/s | 带宽达标 |
| t_perf_RandReadBurst_005 | 随机读 Burst | ≥200 KIOPS | IOPS 达标 |
| t_perf_RandWriteBurst_007 | 随机写 Burst | ≥330 KIOPS | IOPS 达标 |
| t_perf_MixedRw_009 | 混合读写 70/30 | ≥150 KIOPS | IOPS 达标 |

### QoS（待实现）

- [ ] t_qos_LatencyPercentile_001 - 延迟百分位
- [ ] t_qos_LatencyJitter_002 - 延迟抖动

### Reliability（待实现）

- [ ] t_rel_StabilityTest_001 - 稳定性测试

### Scenario（待实现）

- [ ] t_scen_SensorWrite_001 - 传感器写入场景
- [ ] t_scen_ModelLoad_002 - 模型加载场景

---

## 🔧 命令行参考

### run - 执行测试

```bash
SysTest run --suite=<suite_name> [options]

必选参数:
  --suite, -s          测试套件名称
  --device, -d         UFS 设备路径（默认：/dev/ufs0）

可选参数:
  --test, -t           单个测试用例名称
  --dry-run            模拟执行（不实际运行）
  --verbose, -v        详细输出
  --output, -o         输出目录（默认：results/）
  --format, -f         报告格式（默认：html,json）
```

### list - 列出测试

```bash
SysTest list
```

### report - 查看报告

```bash
SysTest report --latest          # 最新报告
SysTest report --id=<test_id>    # 指定报告
SysTest report --latest --open   # 浏览器打开
```

### config - 查看配置

```bash
SysTest config --show            # 显示当前配置
```

---

## 📁 目录结构

```
systest/
├── bin/
│   └── SysTest              # 主入口脚本
├── core/
│   ├── runner.py            # 测试执行引擎
│   ├── collector.py         # 结果收集器
│   ├── reporter.py          # 报告生成器
│   ├── logger.py            # 日志管理器
│   └── analyzer.py          # 失效分析引擎
├── tools/
│   ├── fio_wrapper.py       # FIO 工具封装
│   └── ufs_utils.py         # UFS 设备工具
├── suites/
│   ├── performance/         # 性能测试套件
│   ├── qos/                 # QoS 测试套件
│   ├── reliability/         # 可靠性测试套件
│   └── scenario/            # 场景测试套件
├── config/
│   ├── default.json         # 默认配置
│   └── production.json      # 生产环境配置
├── docs/                    # 文档
├── logs/                    # 日志输出
├── results/                 # 测试结果
└── README.md                # 本文档
```

---

## 🎯 生产环境部署

### 1. 配置文件

编辑 `config/production.json`:

```json
{
  "test": {
    "default_device": "/dev/ufs0",
    "default_runtime": 60
  },
  "thresholds": {
    "performance": {
      "seq_read_burst_001": {
        "target": 2100,
        "unit": "MB/s"
      }
    }
  }
}
```

### 2. CI/CD 集成

项目已包含 GitHub Actions 配置：

```yaml
# .github/workflows/ci.yml
- 自动测试（push/PR）
- 每日定时测试
- 阈值自动检查
- 测试结果上传
```

### 3. 日志管理

日志自动输出到 `logs/` 目录：

```
logs/
├── 20260321_075600.log        # 完整日志
└── 20260321_075600_error.log  # 错误日志
```

---

## 📊 测试报告

### HTML 报告

包含：
- 测试概览（通过率、执行时间）
- 详细结果（每个测试用例）
- 性能指标图表
- 失效分析建议

### JSON 报告

结构化数据，便于自动化处理：

```json
{
  "test_id": "20260321_075600",
  "timestamp": "2026-03-21T07:56:00",
  "suite": "performance",
  "summary": {
    "total": 5,
    "passed": 4,
    "failed": 1,
    "pass_rate": 80.0
  },
  "test_cases": [...]
}
```

---

## 🔍 失效分析

测试失败时，自动提供根因分析：

### 示例：带宽不足

```
❌ 失效模式：LOW_BANDWIDTH
📊 严重程度：major
🔍 根因：带宽低于预期阈值

💡 建议:
1. 检查 I/O 调度器设置（建议：none 或 mq-deadline）
2. 检查设备固件版本，必要时升级
3. 检查 PCIe/NVMe 链路宽度和速度
4. 确保测试期间无其他进程访问设备
5. 检查 CPU frequency governor 设置
```

---

## 🛠️ 开发指南

### 添加新测试用例

1. 在 `suites/<suite_name>/` 创建测试文件
2. 遵循命名规范：`t_<module>_<Name>_<NNN>.py`
3. 继承 `TestCase` 基类
4. 实现 `setup()`, `execute()`, `validate()`, `teardown()`

### 示例

```python
from runner import TestCase
from fio_wrapper import FIO

class Test(TestCase):
    name = "my_test"
    
    def execute(self) -> dict:
        fio = FIO(logger=self.logger)
        metrics = fio.run_seq_read(...)
        return metrics
    
    def validate(self, result: dict) -> bool:
        return result['bandwidth']['value'] >= 2000
```

---

## 📚 相关文档

### 快速开始
- [快速参考卡](docs/QUICK_REFERENCE.md) - 5 分钟快速上手
- [实战指南](docs/PRACTICAL_GUIDE.md) - 完整测试流程

### 环境配置
- [开发板环境](docs/DEV_BOARD_ENV.md) - 开发板配置详情 (Debian 12, ARM64)
- [环境配置指南](docs/ENVIRONMENT_SETUP.md) - CI/CD 环境配置详解
- [CI/CD 快速指南](docs/CI_CD_QUICKSTART.md) - Docker 和 GitHub Actions

### 开发文档
- [测试用例命名规范](docs/README_NAMING.md)
- [Precondition 检查指南](docs/PRECONDITION_GUIDE.md)
- [日志系统使用指南](docs/LOGGER_GUIDE.md)

### 更新日志
- [CI/CD 更新总结](docs/CI_CD_UPDATE_SUMMARY.md)
- [开发板配置更新](docs/DEV_BOARD_CONFIG_UPDATE.md)

---

## 📝 版本历史

| 版本 | 日期 | 变更 |
|------|------|------|
| v1.1.0 | 2026-03-22 | CI/CD 环境配置、环境检查工具、基线对比 |
| v1.0.0 | 2026-03-21 | 生产就绪版本 |
| v0.1.0 | 2026-03-20 | MVP 版本 |

---

**维护团队**: UFS 项目组  
**联系方式**: ufs-team@example.com  
**许可证**: Proprietary
