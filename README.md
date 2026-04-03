# UFS Auto - UFS 3.1 车规级存储系统测试自动化框架

**版本**: v1.1.0  
**状态**: 生产就绪 ✅  
**适用范围**: UFS 3.1 车规级存储系统

---

## 🚀 快速开始

### 1. 克隆项目

```bash
git clone https://github.com/hanxueyuan/ufsauto.git
cd ufsauto/systest
```

### 2. 安装依赖

```bash
# 安装系统依赖
sudo apt-get update
sudo apt-get install -y fio python3 python3-pip

# 验证安装
fio --version  # 应该输出：fio-3.33 或更高
python3 --version  # 应该输出：Python 3.11.2 或更高
```

### 3. 检查环境

```bash
# 检查环境配置
python3 bin/SysTest check-env -v

# 生成环境报告
python3 bin/SysTest check-env --report
```

输出示例：
```
UFS SysTest 环境信息
====================
模式：开发模式

[系统信息]
  操作系统          Debian GNU/Linux 12 (bookworm)
  内核版本          6.1.112-rt43-gb90e520cd120
  CPU 架构           aarch64
  CPU 核心数           6
  内存              8.3 GB

[工具链]
  Python           3.11.2
  FIO               3.33

[存储设备]
  ufshcd 模块       未加载
  UFS 设备          /dev/sda (SKhynix HN8T15DJHQX109)
  设备容量          238 GB
  建议测试目录    /mapdata/ufs_test (可用 232.5 GB)
  默认测试目录    /mapdata/ufs_test
  默认测试文件路径  /mapdata/ufs_test/test.file

[用户权限]
  当前用户          root
  用户组           root
  设备访问         可读写 (root)
```

### 4. 查看可用测试

```bash
python3 bin/SysTest list
```

输出示例：
```
=== 可用测试套件 ===

📦 performance
   • t_perf_SeqReadBurst_001
   • t_perf_SeqWriteBurst_002
   • t_perf_RandReadBurst_003
   • t_perf_RandWriteBurst_004
   • t_perf_MixedRw_005

📦 qos
   • t_qos_LatencyPercentile_001
   • t_qos_LatencyJitter_002
   • t_qos_TailLatencyRatio_003
   • t_qos_LatencyStability_004

📦 reliability
   • t_reliability_BadBlockMonitor_001
   • t_reliability_ECCErrorRate_002
   • t_reliability_EnduranceTest_003

共计 12 个测试项，3 个套件
```

### 5. 执行测试

#### 方式 A：跑完整性能测试套件（推荐首次）

```bash
# 自动选择测试目录（基于设备挂载点）
python3 bin/SysTest run --suite=performance --device=/dev/sda -v

# 或者手动指定测试目录
python3 bin/SysTest run --suite=performance --device=/dev/sda --test-dir=/mapdata/ufs_test -v
```

#### 方式 B：只跑单个测试

```bash
# 只跑顺序读测试
python3 bin/SysTest run --test=t_perf_SeqReadBurst_001 --device=/dev/sda -v
```

#### 方式 C：模拟运行（无硬件时验证框架）

```bash
# 模拟模式不需要真实硬件，可以验证框架能否正常运行
python3 bin/SysTest run --suite=performance --device=/dev/sda -v --simulate
```

### 6. 查看测试报告

```bash
# 查看最新报告（终端输出摘要）
python3 bin/SysTest report --latest

# 在浏览器中打开完整报告（开发板有图形界面时）
python3 bin/SysTest report --latest --open
```

报告包含：
- 测试概览（通过率、执行时间）
- 每个测试用例详细结果
- 性能指标对比
- 失效分析建议（如果测试不通过）

---

## 📋 测试套件

### Performance（性能测试）✅

| 用例 ID | 测试名称 | 目标 | 验收标准 |
|--------|---------|------|---------|
| t_perf_SeqReadBurst_001 | 顺序读突发性能 | ≥ 2100 MB/s | ≥ 90% 目标值 |
| t_perf_SeqWriteBurst_002 | 顺序写突发性能 | ≥ 1650 MB/s | ≥ 90% 目标值 |
| t_perf_RandReadBurst_003 | 随机读突发性能 | ≥ 200 KIOPS | ≥ 90% 目标值 |
| t_perf_RandWriteBurst_004 | 随机写突发性能 | ≥ 330 KIOPS | ≥ 90% 目标值 |
| t_perf_MixedRw_005 | 混合读写 70/30 | ≥ 150 KIOPS | ≥ 90% 目标值 |

### QoS（质量保证）✅

| 用例 ID | 测试名称 | 目标 |
|--------|---------|------|
| t_qos_LatencyPercentile_001 | 延迟百分位分布测试 | p99.99 < 10ms |
| t_qos_LatencyJitter_002 | 延迟抖动测试 | 标准差 < 500μs |
| t_qos_TailLatencyRatio_003 | 尾延迟比测试 | p99.999/p50 < 100x |
| t_qos_LatencyStability_004 | 延迟稳定性测试 | 抖动系数 < 50% |

### Reliability（可靠性）✅

| 用例 ID | 测试名称 | 目标 |
|--------|---------|------|
| t_reliability_BadBlockMonitor_001 | 坏块监控测试 | 坏块不增加 |
| t_reliability_ECCErrorRate_002 | ECC 错误率监测 | UBER < 10^-15 |
| t_reliability_EnduranceTest_003 | 耐久性（寿命）测试 | TBW 达标 |

---

## 🔧 命令行参考

### 主帮助

```bash
python3 bin/SysTest --help
```

### run - 执行测试

```bash
python3 bin/SysTest run --suite=<suite_name> [options]

必选参数:
  --suite, -s          测试套件名称
  --test, -t           单个测试用例名称（与 --suite 互斥）

可选参数:
  --device, -d         UFS 设备路径（默认：/dev/ufs0）
  --test-dir, -tdir    测试文件目录（默认自动选择，所有测试共用）
  --output, -o         输出目录（默认：./results）
  --format, -f         报告格式（默认：html,json）
  --verbose, -v        详细输出
  --dry-run, -n        模拟执行（不实际运行）
  --simulate           模拟模式（无硬件）

示例:
  # 跑完整性能套件
  python3 bin/SysTest run --suite=performance --device=/dev/sda -v
  
  # 跑单个测试
  python3 bin/SysTest run --test=t_perf_SeqReadBurst_001 --device=/dev/sda -v
  
  # 手动指定测试目录
  python3 bin/SysTest run --suite=performance --device=/dev/sda --test-dir=/mapdata/ufs_test -v
  
  # 模拟模式（无硬件）
  python3 bin/SysTest run --suite=performance --simulate -v
```

### list - 列出测试

```bash
python3 bin/SysTest list
```

### report - 查看报告

```bash
python3 bin/SysTest report --latest          # 最新报告
python3 bin/SysTest report --id=<test_id>    # 指定报告
python3 bin/SysTest report --latest --open   # 浏览器打开
```

### check-env - 检查环境

```bash
python3 bin/SysTest check-env -v             # 详细输出
python3 bin/SysTest check-env --report       # 生成 JSON 报告
```

### compare-baseline - 对比性能基线

```bash
python3 bin/SysTest compare-baseline --dev results/dev/ --ci results/ci/
```

---

## 📁 项目结构

```
ufsauto/
├── systest/                       # SysTest 测试框架
│   ├── bin/
│   │   ├── SysTest               ← 唯一统一入口脚本
│   │   ├── check_env.py           # 环境检查
│   │   └── compare_baseline.py    # 性能基线对比
│   ├── core/                      # 核心框架
│   │   ├── runner.py              # 测试执行引擎
│   │   ├── collector.py           # 结果收集器
│   │   ├── reporter.py            # 报告生成器
│   │   ├── logger.py              # 日志管理器
│   │   └── analyzer.py            # 失效分析引擎
│   ├── tools/                     # 工具模块
│   │   ├── fio_wrapper.py         # FIO 工具封装
│   │   ├── ufs_utils.py           # UFS 设备工具
│   │   ├── ufs_simulator.py       # UFS 模拟器
│   │   ├── latency_analyzer.py    # QoS 延迟分析器
│   │   └── reliability_calculator.py # 可靠性计算工具
│   ├── suites/                    # 测试套件
│   │   ├── performance/           # 性能测试套件
│   │   ├── qos/                   # QoS 测试套件
│   │   └── reliability/           # 可靠性测试套件
│   ├── config/
│   │   └── default.json           # 配置文件
│   ├── tests/                     # 框架单元测试
│   ├── docs/                      # 项目文档
│   ├── logs/                      # 日志输出（运行时生成）
│   └── results/                   # 测试结果（运行时生成）
├── docs/                          # 项目文档
├── .github/workflows/             # GitHub Actions CI/CD
├── Dockerfile.ci                  # CI 镜像 Dockerfile
└── README.md                      # 本文档
```

---

## 🎯 自动化特性

### 1. 自动选择测试目录

不指定 `--test-dir` 时，框架会：
1. 列出所有已挂载的挂载点
2. 选择**可用空间最大**的那个（至少 2GB）
3. 自动创建 `ufs_test/` 目录
4. 所有测试用例共用这个目录

### 2. 自动清理测试文件

每个测试用例跑完后，框架会自动删除测试文件，不会堆积占用空间。

### 3. 自动设备识别

### 4. 自动化管理

- **智能目录管理**：自动选择空间最大的挂载点，避免系统盘占用
- **自动创建删除**：测试文件用完即删，不留下垃圾文件
- **模拟模式支持**：无硬件时也能验证框架功能
- **完整报告生成**：HTML + JSON 格式，便于分析
- **失效自动分析**：测试不通过时自动提供根因分析

`check-env` 会自动识别 UFS 设备：
- 支持 `/dev/sd*` 格式
- 支持 `/dev/mmcblk*` 格式
- 支持 `/dev/nvme*` 格式
- 通过厂商名称自动识别（SKhynix/Samsung/Micron/Toshiba 等）

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
2. 遵循命名规范：`t_<module>_<CamelCaseDescription>_<NNN>.py`
3. 继承 `TestCase` 基类
4. 实现 `setup()`, `execute()`, `validate()`, `teardown()`

### 示例

```python
from runner import TestCase
from fio_wrapper import FIO

class Test(TestCase):
    name = "my_test"
    description = "我的测试"
    
    def __init__(self, device, test_dir=None, verbose=False, logger=None):
        super().__init__(device, test_dir, verbose, logger)
        self.test_file = self.get_test_file_path('my_test')
    
    def setup(self) -> bool:
        # 前置条件检查
        return True
    
    def execute(self) -> dict:
        fio = FIO(logger=self.logger)
        metrics = fio.run_seq_read(...)
        return metrics
    
    def validate(self, result: dict) -> bool:
        # 验证结果
        return True
    
    def teardown(self) -> bool:
        # 清理工作（基类会自动删除测试文件）
        return super().teardown()
```

---

## 📚 相关文档

- [快速参考卡](docs/QUICK_REFERENCE.md) - 5 分钟快速上手
- [实战指南](docs/PRACTICAL_GUIDE.md) - 完整测试流程
- [环境配置指南](docs/ENVIRONMENT_SETUP.md) - CI/CD 环境配置
- [测试用例命名规范](docs/README_NAMING.md)
- [Precondition 检查指南](docs/PRECONDITION_GUIDE.md)
- [日志系统使用指南](docs/LOGGER_GUIDE.md)

---

## 📝 版本历史

| 版本 | 日期 | 变更 |
|------|------|------|
| v1.1.0 | 2026-04-02 | 修复所有测试用例 test_dir 参数、简化 config 目录、改进 help 信息 |
| v1.0.0 | 2026-03-21 | 生产就绪版本 |
| v0.1.0 | 2026-03-20 | MVP 版本 |

---

## 📞 联系信息

| 项目 | 信息 |
|------|------|
| **仓库地址** | https://github.com/hanxueyuan/ufsauto |
| **项目负责人** | UFS 项目组 |
| **许可证** | Proprietary |

---

**维护团队**: UFS 项目组  
**最后更新**: 2026-04-02
