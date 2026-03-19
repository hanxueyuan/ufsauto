# UFS 3.1 QoS 指标与性能基准

**文档版本**: V1.0  
**创建时间**: 2026-03-19  
**参考标准**: JEDEC JESD220E / SNIA PTS / AEC-Q100  
**适用产品**: 群联 PS8363 + 长存 SQS 128GB UFS 3.1

---

## 1. UFS 3.1 性能指标体系

### 1.1 核心性能指标

| 指标 | 定义 | 单位 | 测试块大小 | 意义 |
|------|------|------|-----------|------|
| **顺序读带宽** | 连续读取的数据吞吐量 | MB/s | 128KB/256KB | 大文件读取能力（地图加载、媒体播放） |
| **顺序写带宽** | 连续写入的数据吞吐量 | MB/s | 128KB/256KB | 大文件写入能力（行车记录、OTA） |
| **随机读 IOPS** | 每秒随机读取操作次数 | IOPS | 4KB | 小文件读取能力（应用启动、数据库查询） |
| **随机写 IOPS** | 每秒随机写入操作次数 | IOPS | 4KB | 小文件写入能力（日志记录、数据库更新） |
| **读延迟** | 单次读取的响应时间 | μs | 4KB | 实时性要求（ADAS 传感器数据） |
| **写延迟** | 单次写入的响应时间 | μs | 4KB | 数据持久化速度 |

### 1.2 UFS 3.1 标称性能（2 Lane, HS-Gear 3/4）

| 指标 | HS-Gear 3 (2 Lane) | HS-Gear 4 (2 Lane) | 说明 |
|------|--------------------|--------------------|------|
| 接口带宽 | 11.6 Gbps | 23.2 Gbps | 理论最大值 |
| 顺序读 | ~1800 MB/s | ~2400 MB/s | 实际受 NAND 速度限制 |
| 顺序写 | ~800 MB/s | ~1200 MB/s | SLC Cache 模式 |
| 随机读 (QD32) | ~60 KIOPS | ~80 KIOPS | 取决于 FTL 效率 |
| 随机写 (QD32) | ~40 KIOPS | ~60 KIOPS | 取决于 GC 效率 |
| 读延迟 (QD1) | ~100 μs | ~80 μs | 包含协议开销 |
| 写延迟 (QD1) | ~200 μs | ~150 μs | SLC Cache 模式 |

---

## 2. QoS（服务质量）指标详解

### 2.1 QoS 的定义

QoS 衡量的不是平均性能，而是**延迟的一致性和可预测性**。在车规级应用中，QoS 比峰值性能更重要——ADAS 系统不能容忍偶发的长延迟。

### 2.2 延迟百分位指标

| 百分位 | 含义 | 车规要求 | 说明 |
|--------|------|----------|------|
| **P50** | 50% 的请求延迟 ≤ 此值 | 参考值 | 中位数延迟，反映典型体验 |
| **P90** | 90% 的请求延迟 ≤ 此值 | ≤ 2× P50 | 大部分请求的延迟上限 |
| **P99** | 99% 的请求延迟 ≤ 此值 | ≤ 5× P50 | 尾部延迟，反映 GC/WL 影响 |
| **P99.9** | 99.9% 的请求延迟 ≤ 此值 | ≤ 10× P50 | 极端尾部延迟 |
| **P99.99** | 99.99% 的请求延迟 ≤ 此值 | ≤ 20× P50 | 最坏情况（可能触发超时） |
| **Max** | 最大延迟 | < 100ms | 绝对不能超过系统超时阈值 |

### 2.3 车规级 QoS 需求分析

不同车载应用对 QoS 的要求差异巨大：

#### ADAS（高级驾驶辅助系统）
```
场景：摄像头/雷达数据实时存储和回放
数据模式：顺序写为主（录像），随机读（地图/模型加载）
QoS 要求：
  - 顺序写 P99 延迟 < 5ms（保证帧不丢）
  - 随机读 P99 延迟 < 1ms（模型推理输入）
  - 最大延迟 < 50ms（系统超时阈值）
  - 稳态写入带宽 ≥ 200 MB/s（4 路摄像头 @ 50MB/s 每路）
```

#### 数字仪表盘
```
场景：启动动画、仪表数据、诊断日志
数据模式：顺序读为主（启动），小量随机写（日志）
QoS 要求：
  - 顺序读 P99 延迟 < 2ms
  - 冷启动读取带宽 ≥ 500 MB/s（快速显示）
  - 随机写 P99 延迟 < 10ms
```

#### 信息娱乐系统（IVI）
```
场景：导航、音乐、应用
数据模式：混合读写
QoS 要求：
  - 顺序读 P99 延迟 < 5ms
  - 随机读 P99 延迟 < 2ms
  - 混合读写带宽 ≥ 300 MB/s
  - 对延迟尖峰容忍度较高
```

#### 数据记录仪（EDR/黑匣子）
```
场景：事件数据持续记录
数据模式：持续顺序写入
QoS 要求：
  - 稳态顺序写带宽 ≥ 100 MB/s（不能中断）
  - 写入 P99.99 延迟 < 50ms
  - 掉电保护：断电前数据必须落盘
```

---

## 3. 稳态性能测试方法

### 3.1 为什么需要稳态测试

UFS 设备（特别是 TLC/QLC NAND）存在**性能衰减**现象：

```
                    ┌── SLC Cache 区域 ──┐
性能 (MB/s)         │                    │
  1000 ─────────────┤                    │
                    │    SLC Cache       │
                    │    性能区间         │
                    │                    │
   300 ─────────────┤                    ├──── Write Cliff（写入悬崖）
                    │                    │
                    │                    │  TLC/QLC 直写
                    │                    │  性能区间
   200 ─────────────┤                    │
                    └────────────────────┘
                    0    SLC Cache      总容量
                         边界
```

- **Fresh State**：SLC Cache 空，写入速度 ~1000 MB/s
- **Dirty State**：SLC Cache 满，触发 Write Cliff，写入速度骤降到 ~200-300 MB/s
- **Steady State**：GC/Flush 达到动态平衡后的稳定性能

### 3.2 SNIA PTS（Performance Test Specification）方法

参考 SNIA Solid State Storage Performance Test Specification (PTS) v2.0.1：

#### 预条件处理（Preconditioning）

```bash
# 步骤 1: 清理（Purge）
# 全盘顺序写入 2 次，确保 SLC Cache 耗尽

fio --name=purge --filename=/dev/sdX \
    --rw=write --bs=128k --size=100% \
    --numjobs=1 --iodepth=32 \
    --loops=2

# 步骤 2: 预条件循环
# 执行目标负载，直到性能达到稳态

for round in $(seq 1 25); do
    fio --name=precon_${round} --filename=/dev/sdX \
        --rw=randwrite --bs=4k --size=100% \
        --numjobs=1 --iodepth=32 \
        --runtime=60 --time_based \
        --output=precon_${round}.json --output-format=json
done
```

#### 稳态判定标准

SNIA 定义的稳态条件（Steady State）：
- 取最近 5 轮测试数据
- 计算这 5 轮数据的线性回归斜率
- **斜率 < 平均值的 10%** → 达到稳态
- 最大值与最小值的差 < 平均值的 20%

```python
def check_steady_state(data_points, window=5):
    """判断是否达到稳态"""
    if len(data_points) < window:
        return False
    
    recent = data_points[-window:]
    avg = sum(recent) / window
    
    # 线性回归斜率
    x = list(range(window))
    slope = linear_regression_slope(x, recent)
    
    # 极差
    range_val = max(recent) - min(recent)
    
    # 判定条件
    slope_ok = abs(slope) < avg * 0.10
    range_ok = range_val < avg * 0.20
    
    return slope_ok and range_ok
```

### 3.3 稳态性能测试流程

```
┌─────────────────┐
│  1. Purge       │  全盘写入 2 次，清除 SLC Cache
│  (全盘清理)      │
└────────┬────────┘
         ↓
┌─────────────────┐
│  2. Precon      │  执行目标负载，每轮 60 秒
│  (预条件)        │  记录每轮 IOPS/BW/Latency
└────────┬────────┘
         ↓
┌─────────────────┐
│  3. 稳态判定     │  检查最近 5 轮数据
│                  │  满足 SNIA 稳态条件？
└────────┬────────┘
    Yes ↓     ↑ No (继续预条件)
┌─────────────────┐
│  4. 测试执行     │  在稳态下执行正式测试
│  (Steady State)  │  记录 IOPS/BW/Latency/QoS
└────────┬────────┘
         ↓
┌─────────────────┐
│  5. 数据分析     │  计算 P50/P99/P99.9/P99.99
│                  │  生成性能报告
└─────────────────┘
```

---

## 4. Write Cliff 测试

### 4.1 什么是 Write Cliff

Write Cliff（写入悬崖）是 UFS 设备中最重要的性能现象之一：

- SLC Cache 空间耗尽后，设备必须直接向 TLC/QLC 区域写入
- TLC 编程速度约为 SLC 的 1/3，QLC 约为 1/6
- 同时设备还需要执行 GC（垃圾回收）释放空间
- **结果**：写入性能骤降 3-5 倍

### 4.2 SLC Cache 边界测试

```bash
#!/bin/bash
# SLC Cache 边界探测测试
# 目的：找到 SLC Cache 耗尽的精确时机

DEVICE="/dev/sdX"
BS="128k"
TOTAL_SIZE="128G"  # 全盘大小
STEP_SIZE="1G"     # 每步写入量

echo "timestamp,written_gb,bw_mbps,avg_lat_us" > slc_cache_test.csv

written=0
while [ $written -lt 128 ]; do
    result=$(fio --name=slc_probe \
        --filename=$DEVICE \
        --rw=write \
        --bs=$BS \
        --offset=${written}G \
        --size=$STEP_SIZE \
        --numjobs=1 \
        --iodepth=32 \
        --output-format=json 2>/dev/null)
    
    bw=$(echo $result | jq '.jobs[0].write.bw / 1024' 2>/dev/null)
    lat=$(echo $result | jq '.jobs[0].write.lat_ns.mean / 1000' 2>/dev/null)
    
    echo "$(date +%s),$written,$bw,$lat" >> slc_cache_test.csv
    echo "Written: ${written}GB, BW: ${bw} MB/s, Lat: ${lat} μs"
    
    written=$((written + 1))
done
```

**预期结果**：
```
Written: 0GB,  BW: 950 MB/s   ← SLC Cache 区域
Written: 1GB,  BW: 940 MB/s
Written: 2GB,  BW: 920 MB/s
...
Written: 10GB, BW: 900 MB/s   ← SLC Cache 接近耗尽
Written: 11GB, BW: 350 MB/s   ← Write Cliff！
Written: 12GB, BW: 280 MB/s   ← TLC 直写
Written: 13GB, BW: 260 MB/s   ← 稳态
```

### 4.3 SLC Cache 恢复测试

```bash
# 写满 SLC Cache 后，测试恢复时间
# 1. 全盘写入触发 Write Cliff
fio --name=fill --filename=$DEVICE --rw=write --bs=128k --size=100% --iodepth=32

# 2. 空闲等待（让后台 GC 执行）
for wait in 1 5 10 30 60 120 300; do
    sleep $wait
    
    # 3. 测试写入性能是否恢复
    fio --name=recovery_${wait}s --filename=$DEVICE \
        --rw=write --bs=128k --size=1G --iodepth=32 \
        --output=recovery_${wait}s.json --output-format=json
done
```

---

## 5. 混合负载性能测试

### 5.1 车载典型混合负载模型

| 场景 | 读写比 | 块大小分布 | QD | 说明 |
|------|--------|-----------|-----|------|
| **ADAS 录像** | 10R/90W | 90% 128KB + 10% 4KB | 4-8 | 以写入为主 |
| **导航** | 80R/20W | 60% 4KB + 40% 64KB | 1-4 | 以随机读为主 |
| **系统启动** | 95R/5W | 50% 4KB + 50% 128KB | 8-16 | 大量小文件读取 |
| **OTA 升级** | 5R/95W | 95% 128KB + 5% 4KB | 1-4 | 大文件写入 |
| **日常使用** | 70R/30W | 40% 4KB + 30% 64KB + 30% 128KB | 1-8 | 混合场景 |

### 5.2 FIO 混合负载配置

```ini
; ADAS 录像场景模拟
[adas-recording]
filename=/dev/sdX
runtime=300
time_based=1

; 顺序写入流（模拟视频录制）
[video-stream]
rw=write
bs=128k
size=50G
iodepth=4
rate=200m     ; 限速 200MB/s（4 路摄像头）

; 随机读取流（模拟地图/模型加载）
[map-read]
rw=randread
bs=4k
size=10G
iodepth=2
rate_iops=5000  ; 限制 5000 IOPS
```

```ini
; 导航场景模拟
[navigation]
filename=/dev/sdX
runtime=300
time_based=1

; 地图瓦片读取
[map-tiles]
rw=randread
bs=64k
size=20G
iodepth=4

; 路线计算缓存
[route-cache]
rw=randrw
rwmixread=80
bs=4k
size=5G
iodepth=2
```

---

## 6. 温度对性能的影响

### 6.1 温度-性能关系

NAND Flash 性能受温度影响显著：

| 温度范围 | 对读取的影响 | 对写入的影响 | 对擦除的影响 |
|----------|-------------|-------------|-------------|
| -40°C ~ -20°C | 延迟增加 10-20% | 延迟增加 20-50% | 擦除时间增加 30-80% |
| -20°C ~ 0°C | 延迟增加 5-10% | 延迟增加 10-20% | 擦除时间增加 10-30% |
| 0°C ~ 40°C | 基准性能 | 基准性能 | 基准性能 |
| 40°C ~ 85°C | 延迟增加 5-10% | 基本不变 | 擦除时间减少 5-10% |
| 85°C ~ 105°C | 延迟增加 10-20% | 延迟增加 5-10% | 保持较快 |

> **关键发现**：低温对写入和擦除的影响远大于高温。这是因为 NAND 编程/擦除依赖电子隧穿效应，低温下电子活性降低。

### 6.2 温度性能测试矩阵

```
温度点: -40°C, -20°C, 0°C, 25°C, 50°C, 85°C, 105°C
测试项: 顺序读/写 + 随机读/写 + 混合负载
QD:     1, 4, 16, 32
块大小: 4KB, 64KB, 128KB

总测试组合: 7 × 4 × 4 × 3 = 336 组
每组测试: 60 秒（稳态）
总测试时间: ~6 小时（不含温度切换时间）
```

### 6.3 Thermal Throttling（热节流）

当设备温度超过阈值时，UFS 控制器会主动降低性能以减少发热：

```
温度阈值（典型值）：
  - Warning (80°C): 开始降低后台 GC 频率
  - Critical (95°C): 限制 I/O 队列深度
  - Emergency (105°C): 大幅降低性能（可能降至 50%）
  - Shutdown (115°C): 设备进入保护模式

测试方法：
  1. 在温箱中逐步升温
  2. 持续执行 I/O 负载
  3. 监测性能变化拐点
  4. 记录 Thermal Throttling 触发温度和性能影响
```

---

## 7. 性能基准测试脚本

### 7.1 完整性能基准测试

```bash
#!/bin/bash
# UFS 3.1 完整性能基准测试
# 包含：顺序读写 + 随机读写 + 混合负载 + QoS 分析

DEVICE="/dev/sdX"
RESULT_DIR="perf_baseline_$(date +%Y%m%d_%H%M)"
mkdir -p $RESULT_DIR

echo "=== UFS 3.1 Performance Baseline Test ==="
echo "Device: $DEVICE"
echo "Time: $(date)"
echo "Results: $RESULT_DIR"

# 1. 顺序读写
for bs in 128k 256k 1m; do
    for rw in read write; do
        echo "--- Sequential $rw, BS=$bs ---"
        fio --name=seq_${rw}_${bs} \
            --filename=$DEVICE \
            --rw=$rw --bs=$bs \
            --size=10G --numjobs=1 --iodepth=32 \
            --runtime=60 --time_based \
            --lat_percentiles=1 \
            --percentile_list=50:90:99:99.9:99.99 \
            --output=$RESULT_DIR/seq_${rw}_${bs}.json \
            --output-format=json
    done
done

# 2. 随机读写
for qd in 1 4 16 32; do
    for rw in randread randwrite; do
        echo "--- Random $rw, QD=$qd ---"
        fio --name=rand_${rw}_qd${qd} \
            --filename=$DEVICE \
            --rw=$rw --bs=4k \
            --size=10G --numjobs=1 --iodepth=$qd \
            --runtime=60 --time_based \
            --lat_percentiles=1 \
            --percentile_list=50:90:99:99.9:99.99 \
            --output=$RESULT_DIR/rand_${rw}_qd${qd}.json \
            --output-format=json
    done
done

# 3. 混合读写
for mix in 70 50 30; do
    echo "--- Mixed RW, ReadMix=${mix}% ---"
    fio --name=mixed_r${mix} \
        --filename=$DEVICE \
        --rw=randrw --rwmixread=$mix --bs=4k \
        --size=10G --numjobs=1 --iodepth=16 \
        --runtime=60 --time_based \
        --lat_percentiles=1 \
        --percentile_list=50:90:99:99.9:99.99 \
        --output=$RESULT_DIR/mixed_r${mix}.json \
        --output-format=json
done

echo "=== Test Complete ==="
echo "Results saved to $RESULT_DIR/"
```

### 7.2 QoS 分析脚本

```python
#!/usr/bin/env python3
"""UFS QoS 分析脚本 - 从 FIO JSON 结果中提取延迟分布"""

import json
import sys
import os

def analyze_qos(json_file):
    """分析单个 FIO 结果文件的 QoS"""
    with open(json_file) as f:
        data = json.load(f)
    
    for job in data['jobs']:
        name = job['jobname']
        
        for io_type in ['read', 'write']:
            if job[io_type]['total_ios'] == 0:
                continue
            
            lat = job[io_type]['lat_ns']
            clat = job[io_type]['clat_ns']
            
            print(f"\n{'='*60}")
            print(f"Job: {name} | Type: {io_type}")
            print(f"{'='*60}")
            print(f"  IOPS:     {job[io_type]['iops']:.0f}")
            print(f"  BW:       {job[io_type]['bw'] / 1024:.1f} MB/s")
            print(f"  Avg Lat:  {lat['mean'] / 1000:.1f} μs")
            print(f"  P50 Lat:  {clat['percentile'].get('50.000000', 0) / 1000:.1f} μs")
            print(f"  P90 Lat:  {clat['percentile'].get('90.000000', 0) / 1000:.1f} μs")
            print(f"  P99 Lat:  {clat['percentile'].get('99.000000', 0) / 1000:.1f} μs")
            print(f"  P99.9:    {clat['percentile'].get('99.900000', 0) / 1000:.1f} μs")
            print(f"  P99.99:   {clat['percentile'].get('99.990000', 0) / 1000:.1f} μs")
            print(f"  Max Lat:  {lat['max'] / 1000:.1f} μs")
            
            # QoS 评估
            p50 = clat['percentile'].get('50.000000', 1)
            p99 = clat['percentile'].get('99.000000', 1)
            p9999 = clat['percentile'].get('99.990000', 1)
            
            qos_ratio_99 = p99 / p50 if p50 > 0 else float('inf')
            qos_ratio_9999 = p9999 / p50 if p50 > 0 else float('inf')
            
            print(f"\n  QoS Assessment:")
            print(f"    P99/P50:    {qos_ratio_99:.1f}x {'✅ PASS' if qos_ratio_99 <= 5 else '❌ FAIL'} (target: ≤5x)")
            print(f"    P99.99/P50: {qos_ratio_9999:.1f}x {'✅ PASS' if qos_ratio_9999 <= 20 else '❌ FAIL'} (target: ≤20x)")

if __name__ == '__main__':
    result_dir = sys.argv[1] if len(sys.argv) > 1 else '.'
    for f in sorted(os.listdir(result_dir)):
        if f.endswith('.json'):
            analyze_qos(os.path.join(result_dir, f))
```

---

## 8. 性能验收标准

### 8.1 128GB UFS 3.1 车规级性能基准

| 测试项 | 最低要求 | 目标值 | 测试条件 |
|--------|----------|--------|----------|
| 顺序读 | ≥ 1500 MB/s | ≥ 2000 MB/s | 128KB, QD32, 25°C |
| 顺序写（SLC） | ≥ 600 MB/s | ≥ 900 MB/s | 128KB, QD32, 25°C |
| 顺序写（稳态） | ≥ 200 MB/s | ≥ 300 MB/s | 128KB, QD32, 25°C, 全盘预写 |
| 随机读 | ≥ 40 KIOPS | ≥ 60 KIOPS | 4KB, QD32, 25°C |
| 随机写 | ≥ 20 KIOPS | ≥ 35 KIOPS | 4KB, QD32, 25°C |
| 读延迟 P99 | ≤ 500 μs | ≤ 200 μs | 4KB, QD1, 25°C |
| 写延迟 P99 | ≤ 2 ms | ≤ 500 μs | 4KB, QD1, 25°C |
| 写延迟 P99.99 | ≤ 50 ms | ≤ 10 ms | 4KB, QD1, 25°C, 稳态 |

### 8.2 温度降额标准

| 温度 | 性能降额允许 | 说明 |
|------|-------------|------|
| -40°C | 最多降 50% | 低温 NAND 编程慢 |
| -20°C | 最多降 30% | |
| 0°C ~ 50°C | 无降额 | 正常工作范围 |
| 85°C | 最多降 20% | |
| 105°C | 最多降 40% | Thermal Throttling |

---

**文档完成时间**: 2026-03-19  
**关联文档**: UFS 性能测试方法详解.md、UFS_3.1_ICC控制机制详解.md
