# SysTest 模拟模式使用指南

**适用场景**: 无实际 UFS 硬件环境下的开发和验证

---

## 🎯 模拟模式功能

在没有实际 UFS 设备的情况下，提供：
- ✅ UFS 设备模拟（文件/loop device）
- ✅ 性能指标模拟（基于 UFS 3.1 规格）
- ✅ 健康状态模拟
- ✅ 测试框架完整验证

---

## 🚀 快速开始

### 1. 创建模拟设备

```bash
cd systest

# 创建 128GB 模拟设备（稀疏文件，不实际占用空间）
python3 -c "
from tools.ufs_simulator import UFSSimulator
sim = UFSSimulator()
sim.create_device(128)
"
```

### 2. 运行模拟测试

```bash
# 性能测试套件（模拟模式）
python3 bin/SysTest run --suite=performance --simulate -v

# QoS 测试套件（模拟模式）
python3 bin/SysTest run --suite=qos --simulate -v

# 单个测试（模拟模式）
python3 bin/SysTest run --test=t_perf_SeqReadBurst_001 --simulate -v
```

### 3. 查看报告

```bash
# 查看最新报告
python3 bin/SysTest report --latest
```

---

## 📊 模拟性能指标

基于 UFS 3.1 规格，模拟真实设备的性能表现：

### 性能测试

| 测试用例 | 模拟目标 | 波动范围 |
|--------|---------|---------|
| SeqReadBurst | 2100 MB/s | ±5% |
| SeqWriteBurst | 1650 MB/s | ±5% |
| RandReadBurst | 200 KIOPS | ±5% |
| RandWriteBurst | 330 KIOPS | ±5% |
| MixedRw | 150 KIOPS | ±5% |

### QoS 测试

| 测试用例 | 模拟目标 | 单位 |
|--------|---------|------|
| LatencyPercentile | p99.99 < 10ms | 延迟 |
| LatencyJitter | stddev < 500μs | 抖动 |

---

## 🔧 模拟模式原理

### 设备模拟

```python
from tools.ufs_simulator import UFSSimulator

# 创建模拟设备
sim = UFSSimulator(device_path='/tmp/ufs_sim.img')
sim.create_device(size_gb=128)

# 获取设备信息
info = sim.get_device_info()
print(f"设备：{info['model']}")
print(f"容量：{info['capacity_gb']}GB")
```

### 性能模拟

```python
# 模拟性能测试
metrics = sim.simulate_performance('seq_read')
print(f"带宽：{metrics['bandwidth']['value']} MB/s")
print(f"IOPS: {metrics['iops']['value']}")
```

### 健康状态模拟

```python
health = sim.get_health_status()
print(f"健康状态：{health['status']}")
print(f"预 EOL: {health['pre_eol_info']}")
```

---

## 📝 模拟模式 vs 实际硬件

| 特性 | 模拟模式 | 实际硬件 |
|------|---------|---------|
| **设备** | 文件模拟 | 真实 UFS 设备 |
| **性能** | 基于规格模拟 | 真实测量 |
| **延迟** | 统计模型 | 实际测量 |
| **健康状态** | 固定值 | 实时读取 |
| **用途** | 开发验证 | 生产测试 |

---

## 🎯 使用场景

### ✅ 适合模拟模式

- 测试框架开发
- CI/CD 流水线验证
- 代码逻辑测试
- 报告生成验证
- 日志系统测试

### ❌ 不适合模拟模式

- 真实性能测试
- 设备兼容性验证
- 驱动问题排查
- 硬件故障分析

---

## 🔍 验证模拟模式

### 1. 检查模拟设备

```bash
ls -lh /tmp/ufs_sim.img
# 应显示 128G（稀疏文件，实际占用很小）
```

### 2. 检查测试输出

```bash
python3 bin/SysTest run --suite=performance --simulate -v

# 输出应包含：
# 🔧 模拟模式：使用 UFS 模拟器
# ✅ 性能达标：2150.5 MB/s ≥ 2100 MB/s
```

### 3. 检查报告

```bash
cat results/*/results.json | jq '.test_cases[] | {name, status, metrics}'
```

---

## 🛠️ 自定义模拟配置

```python
from tools.ufs_simulator import UFSSimulator, UFSDeviceConfig

# 自定义设备配置
config = UFSDeviceConfig(
    model="UFS 3.1 256GB",
    capacity_gb=256,
    seq_read_mbps=2200,
    seq_write_mbps=1700,
    rand_read_iops=210000,
    rand_write_iops=350000
)

# 创建模拟器
sim = UFSSimulator(config=config)
sim.create_device(256)
```

---

## 📚 相关文档

- [SysTest 使用指南](README.md)
- [FIO 工具封装](docs/FIO_WRAPPER.md)
- [UFS 设备工具](docs/UFS_UTILS.md)

---

**最后更新**: 2026-03-22  
**版本**: v1.0.0
