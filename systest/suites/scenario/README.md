# 场景测试套件

模拟真实应用场景的测试用例，验证 UFS 在实际工作负载下的表现。

## 测试项列表

### sensor_write - 传感器数据写入

模拟智驾系统传感器持续写入场景：
- 多路摄像头数据流
- 激光雷达点云数据
- IMU/GPS 传感器数据
- 写入模式：顺序 + 小文件混合

### model_load - 算法模型加载

模拟 AI 模型加载和推理场景：
- 大文件顺序读取 (模型权重)
- 随机读取 (特征图/中间结果)
- 混合负载 (加载 + 推理并发)

## FIO 参数配置

### sensor_write

```bash
# 模拟 8 路摄像头数据写入 (每路 50MB/s)
fio --name=sensor \
    --filename=/dev/ufs0 \
    --rw=write \
    --bs=64k \
    --iodepth=8 \
    --numjobs=8 \
    --rate=50M \
    --runtime=300 \
    --time_based \
    --output-format=json
```

### model_load

```bash
# 模拟模型加载 (70% 读 + 30% 写)
fio --name=model \
    --filename=/dev/ufs0 \
    --rw=randrw \
    --rwmixread=70 \
    --bs=128k \
    --iodepth=16 \
    --numjobs=4 \
    --runtime=300 \
    --time_based \
    --output-format=json
```

## 验收标准

| 测试项 | 指标 | 目标值 | 单位 |
|--------|------|--------|------|
| sensor_write | 总写入带宽 | ≥ 400 | MB/s |
| sensor_write | 延迟 p99 | < 1,000 | μs |
| sensor_write | 丢包率 | 0 | % |
| model_load | 读取带宽 | ≥ 1,500 | MB/s |
| model_load | 加载时间 | < 5 | 秒 |

## 场景说明

### 智驾传感器负载特征

```
摄像头 (8 路):  8 × 50MB/s  = 400MB/s  持续写入
激光雷达：     1 × 20MB/s  = 20MB/s   持续写入
IMU/GPS:       1 × 1MB/s   = 1MB/s    持续写入
-------------------------------------------
总计：~420MB/s 持续写入，低延迟要求
```

### AI 模型负载特征

```
模型加载：     2GB 顺序读，突发高带宽
推理执行：     随机读权重 + 随机写特征图
并发度：       4-8 个模型同时推理
```

## 执行示例

```bash
# 执行场景测试套件
SysTest run -s scenario -d /dev/ufs0

# 执行单个场景
SysTest run -t sensor_write -d /dev/ufs0 -v
SysTest run -t model_load -d /dev/ufs0 -v
```

## 失效分析

### sensor_write 失效

1. **带宽不足** - 无法支持所有传感器
2. **延迟过高** - 数据积压，影响实时性
3. **丢包** - 写入速度跟不上采集速度

### model_load 失效

1. **加载过慢** - 影响系统启动时间
2. **推理卡顿** - 随机读取性能不足
3. **并发能力差** - 多模型同时加载失败
