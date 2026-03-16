# UFS 3.1 车规级系统测试框架

**版本**: v1.0  
**更新日期**: 2026-03-16  
**状态**: ✅ 生产就绪

---

## 📋 项目概述

UFS 3.1 车规级系统测试框架（SysTest）是专为车规级 UFS 3.1 存储设备设计的自动化测试系统，符合 JEDEC UFS 3.1 标准和 AEC-Q100 车规级认证要求。

**核心功能**:
- ✅ 14 个测试用例，覆盖性能/QoS/可靠性/场景四大类
- ✅ 完整的 Precondition 检查，确保测试环境正确
- ✅ 开发模式/生产模式双模式支持
- ✅ 自动报告生成和失效分析
- ✅ GitHub Actions CI/CD 集成
- ✅ QA Agent 自动审查

---

## 🚀 快速开始

### 环境要求

**硬件**:
- UFS 3.1 兼容设备
- ARM64 架构处理器
- 支持 UFS 子系统的 Linux 内核 (4.19+)

**软件**:
- Debian 12 (ARM64)
- Python 3.11+
- FIO 3.33+
- root 权限

### 安装

```bash
# 进入项目目录
cd /home/gem/workspace/agent/workspace/ufsauto

# 安装依赖
cd systest
pip3 install -r requirements-ci.txt

# 安装 FIO
apt update && apt install -y fio smartmontools
```

### 运行测试

#### 开发模式（默认）

```bash
cd systest

# 执行单个测试
python3 bin/systest run -t t_performance_SequentialReadBurst_001 -v

# 执行整个套件
python3 bin/systest run -s performance -v

# 或使用测试脚本
python3 tests/t_performance_SequentialReadBurst_001.py
```

#### 生产模式

```bash
cd systest

# 使用生产模式
python3 bin/systest run -t t_performance_SequentialReadBurst_001 -m production -v

# 或使用配置文件
python3 bin/systest run -t t_performance_SequentialReadBurst_001 -c config/production.json
```

---

## 📊 测试套件

### 1. Performance 性能测试（9 个用例）

| 用例 | 描述 | 运行时间 | 验收目标 |
|------|------|---------|---------|
| `t_performance_SequentialReadBurst_001` | 顺序读带宽 (Burst) | 60s | ≥2100 MB/s |
| `t_performance_SequentialReadSustained_002` | 顺序读带宽 (Sustained) | 300s | ≥1800 MB/s |
| `t_performance_SequentialWriteBurst_003` | 顺序写带宽 (Burst) | 60s | ≥1650 MB/s |
| `t_performance_SequentialWriteSustained_004` | 顺序写带宽 (Sustained) ⭐ | 300s | ≥250 MB/s |
| `t_performance_RandomReadBurst_005` | 随机读 IOPS (Burst) | 60s | ≥200 KIOPS |
| `t_performance_RandomReadSustained_006` | 随机读 IOPS (Sustained) | 300s | ≥105 KIOPS |
| `t_performance_RandomWriteBurst_007` | 随机写 IOPS (Burst) | 60s | ≥330 KIOPS |
| `t_performance_RandomWriteSustained_008` | 随机写 IOPS (Sustained) ⭐ | 300s | ≥60 KIOPS |
| `t_performance_MixedRw_009` | 混合读写性能 | 60s | ≥150 KIOPS |

### 2. QoS 服务质量测试（2 个用例）

| 用例 | 描述 | 运行时间 | 验收目标 |
|------|------|---------|---------|
| `t_qos_LatencyPercentile_001` | 延迟百分位测试 | 300s | p99.99<10ms |
| `t_qos_LatencyJitter_002` | 延迟抖动测试 | 300s | stddev<500μs |

### 3. Reliability 可靠性测试（1 个用例）

| 用例 | 描述 | 运行时间 | 验收目标 |
|------|------|---------|---------|
| `t_reliability_StabilityTest_001` ⭐ | 长期稳定性测试 | 24 小时 | 无错误，衰减<20% |

### 4. Scenario 场景测试（2 个用例）

| 用例 | 描述 | 运行时间 | 验收目标 |
|------|------|---------|---------|
| `t_scenario_SensorWrite_001` | 传感器数据写入 | 300s | ≥400 MB/s |
| `t_scenario_ModelLoad_002` | 算法模型加载 | 300s | ≥1500 MB/s |

---

## 📁 项目结构

```
ufsauto/
├── systest/                 # 【主】SysTest 测试框架
│   ├── bin/
│   │   └── systest          # 主入口脚本
│   ├── core/
│   │   ├── runner.py        # 测试执行引擎
│   │   ├── collector.py     # 结果收集器
│   │   ├── reporter.py      # 报告生成器
│   │   ├── analyzer.py      # 失效分析引擎
│   │   └── precondition_checker.py # Precondition 检查器
│   ├── tests/
│   │   ├── t_performance_*.py   # 9 个性能测试脚本
│   │   ├── t_qos_*.py           # 2 个 QoS 测试脚本
│   │   ├── t_reliability_*.py   # 1 个可靠性测试脚本
│   │   ├── t_scenario_*.py      # 2 个场景测试脚本
│   │   └── validation_*.py      # 验证脚本
│   ├── suites/
│   │   ├── performance/tests.json
│   │   ├── qos/tests.json
│   │   ├── reliability/tests.json
│   │   └── scenario/tests.json
│   ├── config/
│   │   ├── development.json # 开发模式配置
│   │   └── production.json  # 生产模式配置
│   └── docs/                # 文档（13 个）
├── docs/                    # 项目文档
├── cli/                     # 命令行工具
├── examples/                # 示例代码
└── .github/
    └── workflows/
        ├── systest-ci.yml   # CI/CD 配置
        └── qa-agent.yml     # QA Agent 配置
```

---

## 🛠️ 核心特性

### 1. Precondition 检查

在测试执行前自动检查测试环境：
- ✅ 系统环境（OS/CPU/内存/FIO 版本）
- ✅ 设备信息（路径/型号/固件/容量）
- ✅ 存储配置（功能开关/特殊配置）
- ✅ LUN 配置（数量/映射关系）
- ✅ 器件健康（SMART/寿命/温度/错误计数）
- ✅ 前置条件验证

**开发模式**: 只记录问题，继续执行测试  
**生产模式**: Stop on fail，立即停止测试

### 2. 双模式支持

| 参数 | 开发模式 | 生产模式 |
|------|---------|---------|
| default_runtime | 10 秒 | 60 秒 |
| sustained_runtime | 60 秒 | 300 秒 |
| loop_count | 1 | 3 |
| Precondition | 只记录问题 | Stop on fail |
| 适用场景 | 开发调试 | 正式测试 |

### 3. 自动报告生成

测试完成后自动生成：
- HTML 可视化报告
- JSON 结构化数据
- TXT 文本摘要
- 失效分析报告

### 4. 失效分析

内置 15 种失效模式识别：
- SLC Cache 耗尽
- GC 干扰
- 热节流
- 延迟长尾
- 带宽/IOPS 未达标
- 等等...

### 5. CI/CD 集成

GitHub Actions 自动执行：
- 代码质量检查（Flake8/Black/Isort）
- 最小化验证（7 项验证）
- 测试用例配置验证
- 文档完整性检查
- QA Agent 自动审查和汇报

---

## 📚 文档

### SysTest 文档

| 文档 | 说明 |
|------|------|
| `systest/README.md` | SysTest 项目说明 |
| `systest/QUICKSTART.md` | 快速开始指南 |
| `systest/docs/TEST_SCRIPTS_GUIDE.md` | 测试脚本使用指南 |
| `systest/docs/MODE_CONFIGURATION.md` | 开发/生产模式配置 |
| `systest/docs/CI_CD_SETUP.md` | CI/CD 配置指南 |
| `systest/docs/QA_AGENT_GUIDE.md` | QA Agent 使用指南 |

### 项目文档

| 文档 | 说明 |
|------|------|
| `docs/` | 项目文档（109 个 Markdown 文件） |
| `docs/UFS_3.1_*.md` | UFS 3.1 协议学习笔记 |
| `docs/车规 UFS3.1 项目 - 系统测试团队角色设计.md` | 团队角色设计 |

---

## 🎯 使用场景

### 开发调试

```bash
cd systest

# 快速验证代码逻辑
python3 bin/systest run -t t_performance_SequentialReadBurst_001 -m development -v

# 运行最小化验证
python3 tests/minimal_validation.py
```

### 正式测试

```bash
cd systest

# 执行性能测试套件
python3 bin/systest run -s performance -m production -v

# 执行 24 小时稳定性测试
python3 bin/systest run -t t_reliability_StabilityTest_001 -m production -v
```

### CI/CD

```bash
# GitHub Actions 自动执行
# 查看：https://github.com/hanxueyuan/ufsauto/actions
```

---

## 📊 测试覆盖度

| 测试类型 | 用例数 | 覆盖率 |
|---------|-------|-------|
| 性能测试 | 9 | 100% |
| QoS 测试 | 2 | 100% |
| 可靠性测试 | 1 | 100% |
| 场景测试 | 2 | 100% |
| **总计** | **14** | **100%** |

---

## 🔧 故障排查

### 常见问题

#### 1. FIO 执行失败：test: you need to specify size=

**原因**: 使用 `/dev/zero` 作为测试设备时需要指定 size 参数

**解决方案**: 使用真实的 UFS 设备（`/dev/ufs0`）

#### 2. 设备 /dev/ufs0 不存在

**原因**: 当前环境没有 UFS 设备

**解决方案**: 
- 在开发板上执行
- 或使用开发模式（只检查 Precondition，不执行实际测试）

#### 3. 权限不足

**原因**: 访问 UFS 设备需要 root 权限

**解决方案**:
```bash
sudo python3 bin/systest run -t test_name
```

---

## 📈 项目统计

| 指标 | 数量 |
|------|------|
| **测试用例** | 14 个 |
| **测试脚本** | 14 个 |
| **验证脚本** | 7 个 |
| **配置文件** | 7 个 |
| **文档** | 122 个 |
| **Python 文件** | 29 个（systest） |

---

## 🎯 下一步

### 在开发板上执行测试

1. 将 systest 目录复制到开发板
2. 安装 FIO 和依赖
3. 执行测试脚本获取真实 UFS 性能数据
4. 查看测试结果和报告

### 持续改进

- 基于实际数据优化失效规则
- 添加更多测试用例
- 完善文档

---

## 📞 支持

- **GitHub**: https://github.com/hanxueyuan/ufsauto
- **文档**: `systest/docs/`
- **问题反馈**: GitHub Issues

---

**UFS 3.1 车规级系统测试框架 - 专业、可靠、高效！** 🚀
