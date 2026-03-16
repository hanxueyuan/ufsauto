# QoS 测试套件

服务质量 (Quality of Service) 测试，关注延迟、抖动等性能一致性指标。

## 测试项列表

- `t_qos_LatencyPercentile_001` - 延迟百分位测试
  - 测试 p50/p99/p99.9/p99.99 延迟
  - 验收标准：p99.99 < 10ms
  
- `t_qos_LatencyJitter_002` - 延迟抖动测试
  - 测试延迟标准差和抖动
  - 验收标准：抖动 < 500μs

## FIO 参数配置

### t_qos_LatencyPercentile_001

```bash
fio --name=lat_test \
    --filename=/dev/ufs0 \
    --rw=randread \
    --bs=4k \
    --iodepth=32 \
    --numjobs=1 \
    --runtime=300 \
    --time_based \
    --lat_percentiles=1 \
    --output-format=json
```

### t_qos_LatencyJitter_002

```bash
fio --name=jitter_test \
    --filename=/dev/ufs0 \
    --rw=randread \
    --bs=4k \
    --iodepth=16 \
    --numjobs=4 \
    --runtime=300 \
    --time_based \
    --lat_percentiles=1 \
    --output-format=json
```

## 验收标准

| 测试项 | 指标 | 目标值 | 单位 |
|--------|------|--------|------|
| t_qos_LatencyPercentile_001 | p50 | < 200 | μs |
| t_qos_LatencyPercentile_001 | p99 | < 1,000 | μs |
| t_qos_LatencyPercentile_001 | p99.9 | < 5,000 | μs |
| t_qos_LatencyPercentile_001 | p99.99 | < 10,000 | μs |
| t_qos_LatencyJitter_002 | stddev | < 500 | μs |

## 执行示例

```bash
# 执行 QoS 套件
SysTest run -s qos -d /dev/ufs0

# 执行单个测试
SysTest run -t t_qos_LatencyPercentile_001 -d /dev/ufs0 -v
```

## 失效分析

### 延迟超标可能原因

1. **GC 干扰** - p99.99 延迟突增
2. **系统负载** - 后台进程干扰
3. **队列深度不足** - 无法充分利用并行性
4. **热节流** - 持续高负载导致降频
