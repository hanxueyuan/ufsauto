# 测试用例执行脚本指南

**创建日期**: 2026-03-16  
**版本**: v1.0  
**测试用例数**: 14 个

---

## 📋 概述

为每个测试用例创建了独立的 Python 执行脚本，方便单独执行和调试。

**脚本位置**: `systest/tests/t_*.py`

---

## 📂 测试脚本列表

### Performance 套件（9 个）

| 脚本 | 测试内容 | 运行时间 | 验收目标 |
|------|---------|---------|---------|
| `t_performance_SequentialReadBurst_001.py` | 顺序读带宽 (Burst) | 60 秒 | ≥2100 MB/s |
| `t_performance_SequentialReadSustained_002.py` | 顺序读带宽 (Sustained) | 300 秒 | ≥1800 MB/s |
| `t_performance_SequentialWriteBurst_003.py` | 顺序写带宽 (Burst) | 60 秒 | ≥1650 MB/s |
| `t_performance_SequentialWriteSustained_004.py` | 顺序写带宽 (Sustained) ⭐ | 300 秒 | ≥250 MB/s |
| `t_performance_RandomReadBurst_005.py` | 随机读 IOPS (Burst) | 60 秒 | ≥200 KIOPS |
| `t_performance_RandomReadSustained_006.py` | 随机读 IOPS (Sustained) | 300 秒 | ≥105 KIOPS |
| `t_performance_RandomWriteBurst_007.py` | 随机写 IOPS (Burst) | 60 秒 | ≥330 KIOPS |
| `t_performance_RandomWriteSustained_008.py` | 随机写 IOPS (Sustained) ⭐ | 300 秒 | ≥60 KIOPS |
| `t_performance_MixedRw_009.py` | 混合读写性能 | 60 秒 | ≥150 KIOPS |

### QoS 套件（2 个）

| 脚本 | 测试内容 | 运行时间 | 验收目标 |
|------|---------|---------|---------|
| `t_qos_LatencyPercentile_001.py` | 延迟百分位测试 | 300 秒 | p99.99<10ms |
| `t_qos_LatencyJitter_002.py` | 延迟抖动测试 | 300 秒 | stddev<500μs |

### Reliability 套件（1 个）

| 脚本 | 测试内容 | 运行时间 | 验收目标 |
|------|---------|---------|---------|
| `t_reliability_StabilityTest_001.py` | 长期稳定性测试 ⭐ | 24 小时 | 无错误，衰减<20% |

### Scenario 套件（2 个）

| 脚本 | 测试内容 | 运行时间 | 验收目标 |
|------|---------|---------|---------|
| `t_scenario_SensorWrite_001.py` | 传感器数据写入 | 300 秒 | ≥400 MB/s |
| `t_scenario_ModelLoad_002.py` | 算法模型加载 | 300 秒 | ≥1500 MB/s |

---

## 🚀 使用方式

### 执行单个测试

```bash
cd /home/gem/workspace/agent/workspace/ufsauto/systest

# 执行顺序读 Burst 测试
python3 tests/t_performance_SequentialReadBurst_001.py

# 执行随机写 Sustained 测试
python3 tests/t_performance_RandomWriteSustained_008.py

# 执行延迟百分位测试
python3 tests/t_qos_LatencyPercentile_001.py
```

### 执行整个套件

```bash
cd /home/gem/workspace/agent/workspace/ufsauto/systest/tests

# 执行 performance 套件所有测试
for f in t_performance_*.py; do
    echo "执行：$f"
    python3 $f
done

# 执行所有测试
for f in t_*.py; do
    echo "执行：$f"
    python3 $f
done
```

### 使用主入口执行

```bash
cd /home/gem/workspace/agent/workspace/ufsauto/systest

# 执行单个测试
python3 bin/systest run -t t_performance_SequentialReadBurst_001 -v

# 执行整个套件
python3 bin/systest run -s performance -v
```

---

## 📝 脚本特点

### 1. 完整注释

每个脚本都包含完整的注释：
- ✅ 测试目的
- ✅ Precondition（前置条件）
- ✅ Test Steps（测试步骤）
- ✅ Postcondition（后置条件）
- ✅ 验收标准
- ✅ 注意事项

### 2. 独立执行

每个脚本都可以独立运行：
- ✅ 不依赖其他脚本
- ✅ 使用 TestRunner 执行对应测试
- ✅ 输出清晰的测试结果

### 3. 统一格式

所有脚本使用统一的输出格式：
```
================================================================================
测试用例：t_performance_SequentialReadBurst_001
顺序读带宽 (Burst) 测试
================================================================================

开始执行测试...

================================================================================
测试结果
================================================================================
✅ PASS

测试指标:
  - 带宽：2150.5 MB/s

验收目标:
  - ≥ 2100 MB/s (容差：95%)
  - 即 ≥ 1995 MB/s

================================================================================
```

### 4. 统一返回值

- ✅ 返回 `0` 表示 PASS
- ✅ 返回 `1` 表示 FAIL
- ✅ 适合 CI/CD 集成

---

## ⚠️ 注意事项

### 1. 需要 UFS 设备

**这些脚本需要真实的 UFS 设备才能执行**：
- ❌ 在 GitHub Actions 环境无法执行（没有 UFS 设备）
- ❌ 在普通 PC 环境无法执行（没有 UFS 设备）
- ✅ 在开发板上可以正常执行（有 UFS 设备）

### 2. 需要 root 权限

访问 UFS 设备需要 root 权限：
```bash
sudo python3 tests/t_performance_SequentialReadBurst_001.py
```

### 3. 开发模式 vs 生产模式

**开发模式**（默认）：
- ✅ Precondition 检查只记录 warning
- ✅ 即使没有 UFS 设备也继续执行
- ✅ 适合开发调试

**生产模式**：
- ❌ Precondition 检查失败会抛出异常
- ❌ 没有 UFS 设备会立即停止
- ✅ 适合生产环境

修改模式：
```python
runner = TestRunner(
    device='/dev/ufs0',
    mode='production'  # 改为生产模式
)
```

---

## 🔍 故障排查

### 错误：FIO 执行失败：test: you need to specify size=

**原因**: 使用 `/dev/zero` 作为测试设备时需要指定 size 参数

**解决方案**:
1. 使用真实的 UFS 设备（`/dev/ufs0`）
2. 或者在开发模式下运行（会跳过实际执行）

### 错误：设备 /dev/ufs0 不存在

**原因**: 当前环境没有 UFS 设备

**解决方案**:
1. 在开发板上执行
2. 或者使用开发模式（只检查 Precondition，不执行实际测试）

### 错误：权限不足

**原因**: 访问 UFS 设备需要 root 权限

**解决方案**:
```bash
sudo python3 tests/t_performance_SequentialReadBurst_001.py
```

---

## 📊 测试结果查看

测试结果保存在 `results/` 目录：

```
results/
├── performance/
│   └── YYYYMMDD_HHMMSS/
│       ├── results.json
│       ├── report.html
│       └── summary.txt
├── qos/
├── reliability/
└── scenario/
```

---

## 🎯 总结

**14 个测试用例执行脚本已创建完成！**

- ✅ 每个测试用例都有独立的 Python 脚本
- ✅ 包含完整的注释和文档
- ✅ 统一的输出格式和返回值
- ✅ 适合 CI/CD 集成
- ⚠️ 需要真实的 UFS 设备才能执行

**在开发板上执行测试，获取真实的 UFS 性能数据！** 🚀
