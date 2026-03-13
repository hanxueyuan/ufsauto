# UFS 性能测试方法学习笔记

**学习时间**: 2026-03-13 Day 1 深夜  
**主题**: 性能测试方法（QoS 指标/稳态测试/测试工具）  
**状态**: 学习笔记

---

## 📑 学习内容概览

```
1. 性能指标定义
   - 带宽/IOPS/延迟
   - QoS 指标（P99/P99.99）

2. 稳态性能测试
   - 预条件处理
   - 稳态判断标准
   - 测试流程

3. 测试工具使用
   - FIO 配置
   - ufs-utils 使用
   - 数据分析方法

4. 性能分析方法
   - 瓶颈定位
   - 性能优化建议
```

---

## 1️⃣ 性能指标定义

### 1.1 基础性能指标

| 指标 | 定义 | 单位 | 测试方法 |
|------|------|------|----------|
| **带宽** | 单位时间传输数据量 | MB/s | 顺序读写测试 |
| **IOPS** | 每秒 IO 操作次数 | IO/s | 随机读写测试 |
| **延迟** | IO 请求响应时间 | μs | 延迟分布测试 |
| **队列深度** | 并发 IO 请求数 | - | QD1-QD32 测试 |

### 1.2 QoS（Quality of Service）指标

**QoS 定义**: 服务质量，衡量延迟分布的稳定性

**关键指标**:
| 指标 | 定义 | 说明 |
|------|------|------|
| **P50** | 50% 请求延迟 ≤ 此值 | 中位数延迟 |
| **P99** | 99% 请求延迟 ≤ 此值 | 尾部延迟 |
| **P99.9** | 99.9% 请求延迟 ≤ 此值 | 极端尾部延迟 |
| **P99.99** | 99.99% 请求延迟 ≤ 此值 | 极端情况延迟 |
| **Max** | 最大延迟 | 最坏情况 |

**验收标准**:
```
P99 ≤ 2 × P50
P99.99 ≤ 5 × P50
Max ≤ 10 × P50
```

### 1.3 性能指标计算

**带宽计算**:
```
带宽 (MB/s) = 传输数据量 (MB) / 时间 (s)

示例:
1GB 数据，耗时 0.5 秒
带宽 = 1024 MB / 0.5 s = 2048 MB/s
```

**IOPS 计算**:
```
IOPS = IO 操作次数 / 时间 (s)

示例:
10000 次 4K 读取，耗时 10 秒
IOPS = 10000 / 10 = 1000 IOPS
```

**延迟计算**:
```
平均延迟 = 总延迟 / IO 次数
P99 延迟 = 排序后第 99 百分位的延迟值
```

---

## 2️⃣ 稳态性能测试

### 2.1 为什么需要稳态测试？

**问题**: 瞬时性能可能虚高
```
- 新盘状态：缓存未填满，性能虚高
- 缓存用尽后：性能下降到真实水平
- 稳态测试：验证长时间负载下的真实表现
```

**稳态测试目的**:
- 避免瞬时性能假象
- 验证缓存用尽后的性能
- 验证长时间负载稳定性

### 2.2 稳态判断标准

**稳态条件**:
```
1. 性能波动 ≤ 15%
2. 连续 30 分钟性能稳定
3. 无周期性掉速
4. 无 IO 错误
```

**稳态判断公式**:
```
波动率 = (Max - Min) / Avg × 100%

验收标准：波动率 ≤ 15%
```

### 2.3 稳态测试流程

```
步骤 1：预条件处理
  - 填充磁盘至 90% 容量
  - 使缓存填满，进入稳态

步骤 2：稳态验证
  - 连续写入 30 分钟
  - 验证性能波动 ≤ 15%

步骤 3：正式测试
  - 执行 4 小时连续测试
  - 记录性能数据

步骤 4：数据分析
  - 计算平均性能
  - 计算波动率
  - 检查周期性掉速
```

### 2.4 稳态测试脚本

```bash
#!/bin/bash
# UFS 稳态性能测试脚本

set -e

echo "=========================================="
echo "UFS Steady State Performance Test"
echo "=========================================="

# 配置参数
TEST_DURATION=${1:-4}        # 测试时长（小时）
BLOCK_SIZE=${2:-128k}        # 块大小
NUMJOBS=${3:-1}              # 并发数
RW_TYPE=${4:-write}          # 读写类型

# 预条件处理 - 填充磁盘至 90%
echo "Preconditioning: Filling disk to 90%..."
fio --name=precond \
    --rw=write \
    --bs=1M \
    --size=90% \
    --numjobs=1 \
    --time_based \
    --runtime=3600 \
    --output=precond.log

# 稳态测试
echo "Starting steady state test..."
fio --name=steady_state \
    --rw=$RW_TYPE \
    --bs=$BLOCK_SIZE \
    --size=100% \
    --numjobs=$NUMJOBS \
    --time_based \
    --runtime=$(($TEST_DURATION * 3600)) \
    --log_avg_msec=1000 \
    --output=steady_state.log \
    --lat_percentiles=1

# 分析结果
echo "Analyzing results..."
python3 analyze_steady_state.py steady_state.log

echo "Test completed"
```

---

## 3️⃣ 测试工具使用

### 3.1 FIO 配置详解

**顺序读取测试**:
```ini
[seq_read]
rw=read
bs=128k
size=100%
numjobs=1
time_based
runtime=300
ioengine=libaio
direct=1
iodepth=32
lat_percentiles=1
```

**随机读取测试**:
```ini
[rand_read]
rw=randread
bs=4k
size=100%
numjobs=4
time_based
runtime=300
ioengine=libaio
direct=1
iodepth=32
lat_percentiles=1
```

**混合负载测试**:
```ini
[mixed_rw]
rw=randrw
rwmixread=70
bs=4k
size=100%
numjobs=4
time_based
runtime=300
ioengine=libaio
direct=1
iodepth=32
lat_percentiles=1
```

### 3.2 ufs-utils 使用

**读取设备信息**:
```bash
# 读取设备描述符
ufs-utils query -d /dev/ufs0 -o read_desc -i device

# 读取健康描述符
ufs-utils query -d /dev/ufs0 -o read_desc -i health

# 读取 ICC 级别
ufs-utils query -d /dev/ufs0 -o read_attr -a 0x0062
```

**性能测试**:
```bash
# 顺序读取测试
ufs-utils perf -d /dev/ufs0 -t seq_read -s 1G

# 随机读取测试
ufs-utils perf -d /dev/ufs0 -t rand_read -s 1G
```

### 3.3 数据分析方法

**延迟分布分析**:
```python
import json

# 读取 FIO 延迟数据
with open('fio_output.json', 'r') as f:
    data = json.load(f)

# 提取延迟百分位
latency = data['jobs'][0]['read']['lat_ns']
p50 = latency['percentile']['50.000000'] / 1000  # 转换为 us
p99 = latency['percentile']['99.000000'] / 1000
p99_99 = latency['percentile']['99.990000'] / 1000

print(f"P50: {p50:.2f} us")
print(f"P99: {p99:.2f} us")
print(f"P99.99: {p99_99:.2f} us")

# 验证 QoS 标准
if p99 <= 2 * p50:
    print("✓ P99 QoS OK")
else:
    print("✗ P99 QoS FAIL")
```

---

## 4️⃣ 性能分析方法

### 4.1 瓶颈定位流程

```
1. 检查性能指标
   - 带宽是否达标？
   - IOPS 是否达标？
   - 延迟是否超标？

2. 定位瓶颈层次
   - 物理层瓶颈？（M-PHY 速率）
   - 协议层瓶颈？（命令处理）
   - FTL 瓶颈？（映射/WL/GC）
   - NAND 瓶颈？（读写速度）

3. 分析根本原因
   - 队列深度不足？
   - 缓存用尽？
   - GC 频繁触发？
   - 磨损均衡影响？
```

### 4.2 性能优化建议

**带宽优化**:
```
1. 增加队列深度（QD32）
2. 使用大块大小（128K-1M）
3. 多 LUN 并发访问
4. 优化预取策略
```

**IOPS 优化**:
```
1. 增加队列深度
2. 使用小块大小（4K）
3. 优化映射表查找
4. 减少 GC 触发
```

**延迟优化**:
```
1. 减少队列深度（QD1-QD4）
2. 优化命令调度
3. 减少前台 GC
4. 使用低延迟模式
```

---

## 📊 性能测试用例设计

### 基础性能测试

| 用例 ID | 测试项 | 测试方法 | 验收标准 |
|---------|--------|----------|----------|
| PERF-001 | 顺序读取 128K | FIO seq_read bs=128k | ≥标称值 95% |
| PERF-002 | 顺序写入 128K | FIO seq_write bs=128k | ≥标称值 90% |
| PERF-003 | 随机读取 4K QD1 | FIO rand_read bs=4k depth=1 | IOPS≥标称值 |
| PERF-004 | 随机写入 4K QD1 | FIO rand_write bs=4k depth=1 | IOPS≥标称值 |

### QoS 测试

| 用例 ID | 测试项 | 测试方法 | 验收标准 |
|---------|--------|----------|----------|
| QOS-001 | P50 延迟 | FIO lat_percentile=50 | ≤标称值 |
| QOS-002 | P99 延迟 | FIO lat_percentile=99 | ≤2×P50 |
| QOS-003 | P99.99 延迟 | FIO lat_percentile=99.99 | ≤5×P50 |
| QOS-004 | 最大延迟 | FIO lat_percentile=100 | ≤10×P50 |

### 稳态测试

| 用例 ID | 测试项 | 测试方法 | 验收标准 |
|---------|--------|----------|----------|
| STEADY-001 | 4 小时顺序写入 | FIO 4h seq_write | 稳态≥90% |
| STEADY-002 | 4 小时混合负载 | FIO 4h randrw 70/30 | 波动≤15% |
| STEADY-003 | 满盘性能测试 | 填充 90% 后测试 | ≥空盘 80% |

---

## 📝 学习总结

### 核心要点
1. **性能指标** - 带宽/IOPS/延迟/QoS
2. **QoS 标准** - P99≤2×P50, P99.99≤5×P50
3. **稳态测试** - 预条件处理、稳态判断、4 小时测试
4. **测试工具** - FIO 配置、ufs-utils、数据分析
5. **性能分析** - 瓶颈定位、优化建议

### 测试应用
1. 基础性能测试 - 顺序/随机读写
2. QoS 测试 - 延迟分布验证
3. 稳态测试 - 长时间负载稳定性
4. 瓶颈分析 - 定位性能瓶颈

### 待深入学习
1. 车载场景性能优化
2. 多 LUN 并发性能
3. 温度对性能影响

---

**学习时间**: 2026-03-13 深夜（约 2 小时）  
**累计学习**: 22 小时  
**下一步**: 输出 Day 1 最终总结或继续学习
