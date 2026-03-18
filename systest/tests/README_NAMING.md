# 测试脚本命名规范

## 📋 命名规则

**格式**: `t_<模块>_<用例名称>_<编号>.py`

| 要素 | 格式 | 说明 | 示例 |
|------|------|------|------|
| 前缀 | `t_` | 固定前缀 | t_ |
| 模块 | 缩写 | 模块类别缩写 | perf/func/rel/scen/qos |
| 用例名称 | 驼峰命名 | 功能描述 | SeqReadBurst, RandomIops |
| 编号 | 3 位数字 | 用例序号 | 001, 002, 003 |

## 📁 模块缩写对照表

| 模块全称 | 缩写 | 说明 |
|---------|------|------|
| performance | perf | 性能测试 |
| function | func | 功能测试 |
| reliability | rel | 可靠性测试 |
| scenario | scen | 场景测试 |
| qos | qos | QoS 测试 |

## ✅ 正确示例

```
t_perf_SeqReadBurst_001.py       # 性能 - 顺序读 Burst
t_perf_SeqReadSustained_002.py   # 性能 - 顺序读 Sustained
t_perf_SeqWriteBurst_003.py      # 性能 - 顺序写 Burst
t_perf_RandReadBurst_005.py      # 性能 - 随机读 Burst
t_perf_RandWriteSustained_008.py # 性能 - 随机写 Sustained
t_perf_MixedRw_009.py            # 性能 - 混合读写

t_qos_LatencyPercentile_001.py   # QoS - 延迟百分位
t_qos_LatencyJitter_002.py       # QoS - 延迟抖动

t_rel_StabilityTest_001.py       # 可靠性 - 稳定性测试

t_scen_SensorWrite_001.py        # 场景 - 传感器写入
t_scen_ModelLoad_002.py          # 场景 - 模型加载
```

## ❌ 错误示例

```
t_performance_SeqReadBurst_001.py  # ❌ 模块名未缩写（应为 perf）
t_perf_seqreadburst_001.py         # ❌ 用例名称未驼峰命名
t_perf_SeqReadBurst_1.py           # ❌ 编号不是 3 位数字
t_SeqReadBurst_001.py              # ❌ 缺少模块名
```

## 📊 完整测试用例清单

### Performance 套件（9 个用例）

| 用例 ID | 脚本文件名 | 测试内容 | 验收标准 |
|--------|-----------|---------|---------|
| TC-001 | t_perf_SeqReadBurst_001.py | 顺序读 Burst | ≥2100 MB/s |
| TC-002 | t_perf_SeqReadSustained_002.py | 顺序读 Sustained | ≥1800 MB/s |
| TC-003 | t_perf_SeqWriteBurst_003.py | 顺序写 Burst | ≥1650 MB/s |
| TC-004 | t_perf_SeqWriteSustained_004.py | 顺序写 Sustained | ≥250 MB/s |
| TC-005 | t_perf_RandReadBurst_005.py | 随机读 Burst | ≥200 KIOPS |
| TC-006 | t_perf_RandReadSustained_006.py | 随机读 Sustained | ≥105 KIOPS |
| TC-007 | t_perf_RandWriteBurst_007.py | 随机写 Burst | ≥330 KIOPS |
| TC-008 | t_perf_RandWriteSustained_008.py | 随机写 Sustained | ≥60 KIOPS |
| TC-009 | t_perf_MixedRw_009.py | 混合读写 | ≥150 KIOPS |

### QoS 套件（2 个用例）

| 用例 ID | 脚本文件名 | 测试内容 | 验收标准 |
|--------|-----------|---------|---------|
| TC-001 | t_qos_LatencyPercentile_001.py | 延迟百分位 | p99.99<10ms |
| TC-002 | t_qos_LatencyJitter_002.py | 延迟抖动 | stddev<500μs |

### Reliability 套件（1 个用例）

| 用例 ID | 脚本文件名 | 测试内容 | 验收标准 |
|--------|-----------|---------|---------|
| TC-001 | t_rel_StabilityTest_001.py | 稳定性测试 | 无错误，衰减<20% |

### Scenario 套件（2 个用例）

| 用例 ID | 脚本文件名 | 测试内容 | 验收标准 |
|--------|-----------|---------|---------|
| TC-001 | t_scen_SensorWrite_001.py | 传感器写入 | ≥400 MB/s |
| TC-002 | t_scen_ModelLoad_002.py | 模型加载 | ≥1500 MB/s |

## 🔧 脚本头部注释规范

每个测试脚本必须包含以下字段：

```python
#!/usr/bin/env python3
"""
测试目的：[一句话说明测试目标]
测试模块：[perf/func/rel/scen/qos]
测试用例 ID：[t_module_Name_001]
测试优先级：[P0/P1/P2]
前置条件：[运行测试的前提条件]
测试步骤：
    1. [步骤 1]
    2. [步骤 2]
预期结果：
    1. [结果 1]
    2. [结果 2]
测试耗时：[预计时间]
特殊说明：[注意事项]

修改记录：
    YYYY-MM-DD 姓名 修改内容
"""
```

## 📝 修改历史

| 日期 | 版本 | 修改内容 | 修改人 |
|------|------|---------|--------|
| 2026-03-18 | v1.0 | 初始版本，统一使用模块缩写命名 | QA Agent |

---

**文档维护**: UFS 项目组  
**最后更新**: 2026-03-18
