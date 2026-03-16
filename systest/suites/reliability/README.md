# 可靠性测试套件

长期稳定性测试，验证 UFS 设备在持续负载下的可靠性。

## 测试项列表

- `t_reliability_StabilityTest_001` - 长期稳定性测试
  - 24 小时连续读写测试
  - 监控性能衰减和错误率
  - 验收标准：无错误，性能衰减 < 20%

## FIO 参数配置

### t_reliability_StabilityTest_001

```bash
fio --name=stability \
    --filename=/dev/ufs0 \
    --rw=randrw \
    --rwmixread=70 \
    --bs=4k \
    --iodepth=32 \
    --numjobs=2 \
    --runtime=86400 \
    --time_based \
    --verify=0 \
    --output-format=json
```

## 验收标准

| 指标 | 目标值 | 单位 | 说明 |
|------|--------|------|------|
| 测试时长 | 24 | 小时 | 连续运行 |
| 错误数 | 0 | 次 | 无 IO 错误 |
| 性能衰减 | < 20% | - | 初始 vs 最终 |
| 平均延迟 | < 500 | μs | 全程平均 |
| 温度 | < 70 | ℃ | 最高温度 |

## 监控指标

### 性能监控

- 每 5 分钟记录一次带宽/IOPS
- 绘制性能随时间变化曲线
- 识别性能下降拐点

### 健康监控

- SMART 状态检查
- 温度监控
- 错误计数 (CRC、重传等)

## 执行示例

```bash
# 执行稳定性测试 (24 小时)
SysTest run -t t_reliability_StabilityTest_001 -d /dev/ufs0

# 后台执行
SysTest run -t t_reliability_StabilityTest_001 -d /dev/ufs0 --background

# 查看进度
SysTest report --latest
```

## 失效分析

### 常见失效模式

1. **性能逐渐下降** - SLC Cache 耗尽，需要更多 OP
2. **突发错误** - 固件 Bug 或硬件问题
3. **温度过高** - 散热不足，需要改善环境
4. **延迟突增** - GC 或后台操作干扰
