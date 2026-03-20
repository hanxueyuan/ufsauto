# SysTest - UFS 系统测试框架

**版本**: MVP v0.1  
**创建时间**: 2026-03-20  
**状态**: 开发中

---

## 🚀 快速开始

### 1. 查看可用测试

```bash
cd /path/to/ufsauto/systest
python3 bin/SysTest list
```

### 2. 执行性能测试

```bash
# 执行完整性能测试套件
python3 bin/SysTest run --suite=performance --device=/dev/ufs0

# 执行单个测试
python3 bin/SysTest run --test=seq_read_burst --device=/dev/ufs0 -v

# 模拟执行（不实际运行）
python3 bin/SysTest run --suite=performance --dry-run
```

### 3. 查看报告

```bash
# 查看最新报告
python3 bin/SysTest report --latest

# 在浏览器中打开
python3 bin/SysTest report --latest --open

# 查看指定测试报告
python3 bin/SysTest report --id=20260320_123456
```

---

## 📋 当前功能

### ✅ 已实现

- [x] SysTest 主入口（argparse 命令行）
- [x] 测试执行引擎（runner.py）
- [x] 结果收集器（collector.py）
- [x] 基础报告生成（reporter.py - HTML/JSON）
- [x] 性能测试套件（1 个测试用例：seq_read）
- [x] 配置文件（default.json）
- [x] 纯 Python 标准库（零依赖）

### ⏳ 开发中

- [ ] 完整性能测试套件（9 项）
- [ ] QoS 测试套件
- [ ] 场景化测试套件
- [ ] 失效分析引擎
- [ ] FIO 工具封装
- [ ] 图表生成

---

## 📁 目录结构

```
systest/
├── bin/
│   └── SysTest              # 主入口脚本 ✅
├── core/
│   ├── runner.py            # 测试执行引擎 ✅
│   ├── collector.py         # 结果收集器 ✅
│   └── reporter.py          # 报告生成器 ✅
├── suites/
│   └── performance/         # 性能测试套件
│       ├── __init__.py
│       └── test_seq_read.py # 顺序读测试 ✅
├── config/
│   └── default.json         # 默认配置 ✅
├── results/                 # 测试结果输出
└── README.md                # 本文档
```

---

## 🔧 命令行参考

### run - 执行测试

```bash
SysTest run --suite=<suite_name> [options]

必选参数:
  --suite, -s          测试套件名称

可选参数:
  --test, -t           单个测试项名称
  --device, -d         测试设备路径（默认：/dev/ufs0）
  --output, -o         输出目录（默认：./results）
  --format, -f         报告格式（默认：html,json）
  --verbose, -v        详细输出
  --dry-run, -n        模拟执行
```

### list - 列出测试

```bash
SysTest list
```

### report - 查看报告

```bash
SysTest report --latest              # 最新报告
SysTest report --id=<test_id>        # 指定报告
SysTest report --latest --open       # 浏览器打开
```

### config - 查看配置

```bash
SysTest config --show                # 显示配置内容
```

---

## 📊 输出示例

### 测试结果（JSON）

```json
{
  "test_id": "20260320_143022",
  "timestamp": "2026-03-20T14:30:22",
  "suite": "performance",
  "device": "/dev/ufs0",
  "test_cases": [
    {
      "name": "seq_read_burst",
      "status": "PASS",
      "metrics": {
        "bandwidth": {"value": 2150, "unit": "MB/s"},
        "iops": {"value": 520, "unit": "IOPS"},
        "latency_avg": {"value": 45, "unit": "μs"}
      },
      "duration": 60.5
    }
  ],
  "summary": {
    "total": 1,
    "passed": 1,
    "failed": 0,
    "pass_rate": 100.0
  }
}
```

### HTML 报告

打开 `results/<test_id>/report.html` 查看可视化报告。

---

## 🛠️ 开发新测试用例

### 1. 创建测试文件

```python
# suites/performance/test_seq_write.py
from core.runner import TestCase

class Test(TestCase):
    name = "seq_write_burst"
    description = "顺序写入性能测试"
    
    def execute(self) -> dict:
        # 实现测试逻辑
        return {'bandwidth': {'value': 1680, 'unit': 'MB/s'}}
    
    def validate(self, result: dict) -> bool:
        # 验证结果
        return result['bandwidth']['value'] >= 1650
```

### 2. 更新套件__init__.py

```python
# suites/performance/__init__.py
from .test_seq_read import SeqReadTest
from .test_seq_write import SeqWriteTest

__all__ = ['SeqReadTest', 'SeqWriteTest']
```

### 3. 测试新用例

```bash
SysTest list
SysTest run --test=seq_write_burst
```

---

## 📝 注意事项

1. **FIO 依赖**: 性能测试需要安装 FIO 工具
   ```bash
   sudo apt-get install fio
   ```

2. **设备权限**: 确保有权限访问测试设备
   ```bash
   sudo chmod 666 /dev/ufs0
   ```

3. **测试文件清理**: 测试会自动清理临时文件，但建议定期清理 `results/` 目录

---

## 🎯 下一步计划

### 第一阶段（MVP）- ✅ 完成
- [x] SysTest 主入口
- [x] 测试执行引擎
- [x] 结果收集器
- [x] 基础报告生成
- [x] 1 个性能测试用例

### 第二阶段（完整功能）- 进行中
- [ ] 完整性能测试套件（9 项）
- [ ] QoS 测试套件（4 项）
- [ ] FIO 工具封装
- [ ] 配置文件加载

### 第三阶段（高级功能）- 计划中
- [ ] 失效分析引擎
- [ ] 场景化测试套件
- [ ] 图表生成
- [ ] 通知功能

---

## 📞 问题反馈

如有问题或建议，请联系测试开发团队。

---

**最后更新**: 2026-03-20
