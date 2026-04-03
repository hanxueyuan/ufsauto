# SysTest - UFS 系统测试框架

车规级 UFS 3.1 存储设备系统测试框架，支持性能、QoS、可靠性测试。

## 项目结构

```
systest/
├── bin/
│   ├── SysTest          # 主入口脚本
│   ├── check_env.py     # 环境检查
│   └── compare_baseline.py  # 性能基线对比
├── core/
│   ├── runner.py        # 测试执行引擎
│   ├── collector.py     # 结果收集器
│   ├── reporter.py      # 报告生成器
│   ├── logger.py        # 日志系统
│   └── analyzer.py      # 数据分析器
├── tools/
│   ├── fio_wrapper.py   # FIO 封装
│   ├── ufs_utils.py     # UFS 设备工具
│   ├── latency_analyzer.py  # 延迟分析
│   └── reliability_calculator.py  # 可靠性计算
└── suites/
    ├── performance/     # 性能测试套件（5 个测试用例）
    ├── qos/            # QoS 测试套件（4 个测试用例）
    └ reliability/    # 可靠性测试套件（3 个测试用例）
```

## 快速开始

### 环境要求

- Python 3.10+
- FIO 3.33+
- UFS 设备（`/dev/ufs0`）

### 运行测试

```bash
# 运行性能测试套件
cd systest/bin
python3 SysTest run --suite=performance

# 运行 QoS 测试套件
python3 SysTest run --suite=qos

# 运行可靠性测试套件
python3 SysTest run --suite=reliability

# 运行所有测试
python3 SysTest run --suite=all

# 查看帮助
python3 SysTest --help
```

### 测试输出

- **日志**: `logs/{test_id}/` 目录
- **报告**: `reports/{test_id}/` 目录（HTML/JSON/PDF）
- **数据**: `results/{test_id}/` 目录

## 测试套件

### 性能测试（Performance）

| 测试用例 | 描述 | 预期指标 |
|---------|------|---------|
| SeqReadBurst | 顺序读性能 | 带宽 ≥ 2100 MB/s |
| SeqWriteBurst | 顺序写性能 | 带宽 ≥ 800 MB/s |
| RandReadBurst | 随机读性能 | IOPS ≥ 50K |
| RandWriteBurst | 随机写性能 | IOPS ≥ 30K |
| MixedRW | 混合读写性能 | 带宽/IOPS 综合达标 |

### QoS 测试（Quality of Service）

| 测试用例 | 描述 | 预期指标 |
|---------|------|---------|
| LatencyPercentile | 延迟百分位分布 | p99.99 < 10ms |
| LatencyJitter | 延迟抖动 | 标准差 < 500 μs |
| TailLatencyRatio | 尾部发散度 | p99.99/p50 < 100× |
| LatencyStability | 延迟稳定性 | CV < 10% |

### 可靠性测试（Reliability）

| 测试用例 | 描述 | 预期指标 |
|---------|------|---------|
| BadBlockMonitor | 坏块监控 | 坏块增长 ≤ 预设阈值 |
| ECCErrorRate | ECC 错误率 | UBER < 10^-15 |
| EnduranceTest | 耐久性测试 | P/E 周期 ≥ 3000 |

## 代码统计

- 总代码量：~6,863 行 Python
- 测试用例：12 个
- 核心框架：5 个模块
- 工具：6 个模块

## 文档

详细技术文档位于 `systest/docs/` 目录。

## License

MIT License

---

**项目状态**: ✅ 生产就绪

**默认设备**: `/dev/ufs0`（车规 UFS 3.1）