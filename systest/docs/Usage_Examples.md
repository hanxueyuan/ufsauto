# UFS Auto 使用场景深度指南

---

## 目录

1. [日常开发验证](#一日常开发验证)
2. [版本发布测试](#二版本发布测试)
3. [性能回归分析](#三性能回归分析)
4. [问题复现与调试](#四问题复现与调试)
5. [长期稳定性监控](#五长期稳定性监控)
6. [不同负载条件测试](#六不同负载条件测试)
7. [温度敏感性测试](#七温度敏感性测试)
8. [对比不同配置](#八对比不同配置)
9. [故障排查流程](#九故障排查流程)
10. [生成客户报告](#十生成客户报告)
11. [产线快速测试](#十一产线快速测试)
12. [研发深度分析](#十二研发深度分析)
13. [竞品对比测试](#十三竞品对比测试)
14. [自动化 CI/CD](#十四自动化 cicd)
15. [长期健康追踪](#十五长期健康追踪)

---

## 一、日常开发验证

### 场景描述
代码变更后，快速验证功能正常，性能无明显退化。

### 测试目标
- ✓ 测试流程跑通
- ✓ 无明显性能退化 (<10%)
- ✓ 无新增错误
- ✓ 耗时 <10 分钟

### 测试命令
```bash
cd systest

# 快速模式 - 验证流程
python3 bin/SysTest run --suite=performance --quick

# 查看结果
python3 bin/SysTest report --latest
```

### 预期输出
```
[10:30:00] [INFO] UFS Auto SysTest v1.0
[10:30:00] [INFO] ============================================================
[10:30:01] [INFO] 快速模式 - 流程验证 (~10 分钟)
[10:30:01] [INFO] ============================================================
[10:30:02] [INFO] 执行测试：seq_read_burst
[10:31:05] [INFO]   读取：2156.8 MB/s, 17188 IOPS, 148.6 μs
[10:31:06] [INFO] 执行测试：seq_write_burst
[10:32:10] [INFO]   写入：1723.4 MB/s, 13678 IOPS, 186.2 μs
[10:32:11] [INFO] 执行测试：rand_read_burst
[10:33:15] [INFO]   读取：62341 IOPS, 243.5 MB/s, 512.3 μs
[10:33:16] [INFO] 执行测试：rand_write_burst
[10:34:20] [INFO]   写入：51234 IOPS, 200.1 MB/s, 623.4 μs
[10:34:21] [INFO] ============================================================
[10:34:21] [INFO] 测试完成
[10:34:21] [INFO] 总计：4 项
[10:34:21] [INFO] 通过：4 项
[10:34:21] [INFO] 失败：0 项
[10:34:21] [INFO] 通过率：100.0%
[10:34:21] [INFO] ============================================================
```

### 结果解读
```
✓ 所有测试通过 → 功能正常
✓ 性能数值在正常范围 → 无明显退化
✓ 耗时~10 分钟 → 符合预期
```

### 下一步
- 如果通过 → 继续开发/提交代码
- 如果失败 → 查看日志，排查问题

### 最佳实践
```bash
# 1. 每次代码变更后运行
git commit -m "feat: xxx"
python3 bin/SysTest run --suite=performance --quick

# 2. 保存关键结果
python3 bin/SysTest report --latest > dev_check_$(date +%Y%m%d).txt

# 3. 发现异常立即排查
# 不要累积问题
```

---

## 二、版本发布测试

### 场景描述
版本发布前，全面验证所有功能和性能指标。

### 测试目标
- ✓ 所有测试套件通过
- ✓ 性能符合规格要求
- ✓ 稳定性验证 (多次循环)
- ✓ 生成完整报告

### 测试命令
```bash
# 完整测试 - 所有套件
python3 bin/SysTest run --all --batch=3 --interval=60

# 生成 HTML 报告
python3 bin/SysTest report --generate-html

# 保存基线 (如果这是新版本基线)
python3 bin/SysTest report --save-baseline
```

### 测试配置
```json
{
  "test_mode": "full",
  "suites": ["performance", "qos", "reliability"],
  "runtime": 300,
  "loops": 3,
  "batch": 3,
  "interval": 60
}
```

### 预期耗时
```
Performance: ~30 分钟 (5 项 × 5 分钟 × 3 loops)
QoS:         ~20 分钟 (4 项 × 5 分钟)
Reliability: ~60 分钟 (3 项 × 20 分钟)
Batch ×3:    ~330 分钟 (含间隔)

总计：~5.5 小时
```

### 报告内容
```markdown
# 版本发布测试报告

## 版本信息
- 固件版本：v2.1.0
- 测试日期：2026-04-05
- 设备型号：UFS 3.1 256GB

## 测试结果
- 总计：12 项
- 通过：12 项
- 失败：0 项
- 通过率：100%

## 关键指标
| 测试项 | 结果 | 规格 | 状态 |
|--------|------|------|------|
| 顺序读取 | 2156 MB/s | ≥2000 | ✓ |
| 顺序写入 | 1723 MB/s | ≥1200 | ✓ |
| 随机读 IOPS | 62341 | ≥50000 | ✓ |
| 随机写 IOPS | 51234 | ≥40000 | ✓ |
| P99.99 延迟 | 1.8ms | <5ms | ✓ |

## 稳定性
- 3 次循环结果一致性：±2%
- 无性能衰减
- 无硬件错误

## 结论
✅ 所有测试通过，可以发布
```

### 最佳实践
```bash
# 1. 发布前 1 天开始测试
# 留出时间处理意外

# 2. 使用完整配置
# 不要跳过 reliability

# 3. 保存完整日志
cp -r logs/ release_logs_v2.1.0/

# 4. 生成多种格式报告
python3 bin/SysTest report --generate-html
python3 bin/SysTest report --generate-pdf
```

---

## 三、性能回归分析

### 场景描述
发现性能下降，需要分析原因和幅度。

### 测试目标
- ✓ 量化性能下降幅度
- ✓ 定位下降的测试项
- ✓ 分析可能原因
- ✓ 对比历史基线

### 测试命令
```bash
# 1. 执行当前测试
python3 bin/SysTest run --full

# 2. 对比基线
python3 bin/SysTest compare-baseline

# 3. 深入分析特定测试项
python3 bin/SysTest run --test=seq_write --time=300
```

### 分析方法
```python
# 对比数据
baseline = {
    'seq_read': 2180,   # MB/s
    'seq_write': 1750,
    'rand_read': 63000, # IOPS
    'rand_write': 52000
}

current = {
    'seq_read': 2156,
    'seq_write': 1723,
    'rand_read': 62341,
    'rand_write': 51234
}

# 计算变化
for test in baseline:
    delta = (current[test] - baseline[test]) / baseline[test] * 100
    print(f"{test}: {delta:+.1f}%")

# 输出:
# seq_read: -1.1%
# seq_write: -1.5%
# rand_read: -1.0%
# rand_write: -1.5%
```

### 判定标准
```
变化幅度 | 判定 | 行动
---------|------|------
±5% 以内  | 正常波动 | 无需行动
5-10%    | 需关注 | 持续监控
10-20%   | 可能回归 | 深入分析
>20%     | 严重回归 | 立即排查
```

### 深入分析
```bash
# 1. 检查测试条件
python3 bin/SysTest check-env

# 2. 查看系统日志
dmesg | grep -i "scsi"

# 3. 检查温度
cat /sys/class/thermal/thermal_zone*/temp

# 4. 重复测试验证
for i in {1..5}; do
    python3 bin/SysTest run --test=seq_write --time=60
done
```

### 最佳实践
```bash
# 1. 建立可靠基线
# 在已知良好状态保存 baseline

# 2. 定期对比
# 每周运行 compare-baseline

# 3. 记录环境
# 保存 check-env 输出

# 4. 多次验证
# 异常结果重复测试 3 次
```

---

## 四、问题复现与调试

### 场景描述
用户报告问题，需要复现和调试。

### 测试目标
- ✓ 复现用户问题
- ✓ 收集详细数据
- ✓ 定位根因
- ✓ 验证解决方案

### 测试命令
```bash
# 1. 记录当前状态
python3 bin/SysTest check-env > env_info.txt
dmesg > dmesg.log

# 2. 执行标准测试
python3 bin/SysTest run --full --time=120

# 3. 手动复现 (更详细输出)
fio --name=debug \
    --rw=randread \
    --bs=4k \
    --iodepth=32 \
    --runtime=60 \
    --filename=/tmp/test \
    --direct=1 \
    --output-format=json+ \
    --latency-log=latency.log
```

### 调试技巧
```bash
# 1. 增加详细输出
python3 bin/SysTest run -vvv

# 2. 保存中间结果
python3 bin/SysTest run --save-intermediate

# 3. 实时日志监控
tail -f logs/latest.log

# 4. 系统日志同步
dmesg -w > dmesg_trace.log &
```

### 数据收集清单
```
□ SysTest 完整日志
□ FIO 详细输出 (json+)
□ 延迟日志 (latency.log)
□ 系统日志 (dmesg)
□ 环境信息 (check-env)
□ 温度记录
□ I/O 统计 (iostat)
□ 用户复现步骤
```

### 最佳实践
```bash
# 1. 精确记录复现步骤
cat > reproduce_steps.txt << EOF
1. 执行命令：...
2. 等待时间：...
3. 观察现象：...
EOF

# 2. 保存所有日志
tar -czf debug_logs_$(date +%Y%m%d_%H%M%S).tar.gz \
    logs/ env_info.txt dmesg.log

# 3. 尝试不同配置复现
# 确认问题边界条件
```

---

## 五、长期稳定性监控

### 场景描述
长期监控设备健康状态，预测潜在故障。

### 测试目标
- ✓ 每周自动运行测试
- ✓ 追踪性能趋势
- ✓ 检测健康状态变化
- ✓ 预警潜在问题

### 自动化脚本
```bash
#!/bin/bash
# weekly_health_check.sh

# 1. 执行测试
cd /workspace/projects/hermes/projects/ufsauto/systest
python3 bin/SysTest run --full --time=300

# 2. 保存结果
TIMESTAMP=$(date +%Y%m%d)
cp results/latest.json results/weekly_${TIMESTAMP}.json

# 3. 对比基线
python3 bin/SysTest compare-baseline > comparison_${TIMESTAMP}.txt

# 4. 检查异常
python3 << EOF
import json

with open('results/latest.json') as f:
    data = json.load(f)

# 检查性能下降
for result in data['results']:
    if 'delta' in result and result['delta'] < -10:
        print(f"⚠️  警告：{result['name']} 性能下降 {result['delta']:.1f}%")

# 检查失败
if data['summary']['failed'] > 0:
    print(f"🚨 警报：{data['summary']['failed']} 项测试失败")
EOF

# 5. 发送报告 (邮件/消息)
# (集成通知系统)
```

### 监控指标
```python
metrics = {
    'performance_decay': {
        'threshold': 20,  # %
        'action': 'alert'
    },
    'bad_block_growth': {
        'threshold': 20,  # 个
        'action': 'alert'
    },
    'ecc_error_rate': {
        'threshold': 10**-12,
        'action': 'alert'
    },
    'temperature_max': {
        'threshold': 85,  # °C
        'action': 'alert'
    }
}
```

### 趋势分析
```python
import pandas as pd
import matplotlib.pyplot as plt

# 加载历史数据
data = []
for f in glob('results/weekly_*.json'):
    with open(f) as fp:
        result = json.load(fp)
        data.append({
            'date': extract_date(f),
            'seq_read': result['results'][0]['read_bw_mb'],
            'seq_write': result['results'][1]['write_bw_mb'],
            # ...
        })

df = pd.DataFrame(data)

# 绘制趋势图
plt.figure(figsize=(12, 6))
plt.plot(df['date'], df['seq_read'], label='Seq Read')
plt.plot(df['date'], df['seq_write'], label='Seq Write')
plt.axhline(y=2000*0.9, color='r', linestyle='--', label='Warning')
plt.legend()
plt.title('Performance Trend')
plt.savefig('trend.png')
```

### 最佳实践
```bash
# 1. 固定测试时间
# 每周二凌晨 2 点

# 2. 保存原始数据
# 便于后续分析

# 3. 设置合理阈值
# 避免误报

# 4. 定期回顾趋势
# 每月分析一次
```

---

## 六、不同负载条件测试

### 场景描述
测试设备在不同负载条件下的性能表现。

### 测试配置

#### 轻负载 (空闲状态)
```bash
python3 bin/SysTest run \
    --test=rand_read_4k \
    --iodepth=1 \
    --numjobs=1 \
    --time=60
```

#### 中负载 (日常使用)
```bash
python3 bin/SysTest run \
    --test=mixed_rw \
    --iodepth=4 \
    --numjobs=2 \
    --rwmixread=70 \
    --time=120
```

#### 重负载 (压力测试)
```bash
python3 bin/SysTest run \
    --test=rand_rw \
    --iodepth=64 \
    --numjobs=8 \
    --rwmixread=50 \
    --time=300
```

### 预期结果
```
负载条件 | IOPS | 延迟 | 说明
---------|------|------|------
轻负载   | ~15K | ~100μs | 单线程应用
中负载   | ~40K | ~200μs | 日常多任务
重负载   | ~60K | ~500μs | 服务器负载
```

### 分析要点
```
1. IOPS 随 QD 增长曲线
   - 理想：线性增长
   - 实际：逐渐饱和

2. 延迟随 QD 变化
   - 理想：缓慢上升
   - 异常：急剧上升

3. 性能饱和点
   - 找到最佳 QD
   - 避免过度并发
```

### 最佳实践
```bash
# 1. 测试多个 QD 点
for qd in 1 4 8 16 32 64; do
    fio --iodepth=$qd ...
done

# 2. 绘制 IOPS vs QD 曲线
# 找到饱和点

# 3. 选择合适 QD
# 日常使用：QD4-8
# 性能测试：QD32
```

---

## 七、温度敏感性测试

### 场景描述
测试设备在不同温度下的性能表现，检测热节流。

### 测试命令
```bash
# 1. 记录初始温度
cat /sys/class/thermal/thermal_zone*/temp > temp_initial.txt

# 2. 执行长时间测试
python3 bin/SysTest run \
    --test=seq_write \
    --time=600 \
    --interval=60

# 3. 监控温度 (另开终端)
watch -n 5 'cat /sys/class/thermal/thermal_zone*/temp' > temp_trace.txt
```

### 分析方法
```python
import pandas as pd

# 加载温度和性能数据
temp = pd.read_csv('temp_trace.txt', names=['time', 'temp'])
perf = pd.read_csv('perf_log.csv')

# 合并数据
merged = pd.merge(temp, perf, on='time')

# 分析温度 - 性能相关性
correlation = merged['temp'].corr(merged['bandwidth'])
print(f"温度 - 性能相关性：{correlation:.2f}")

# 识别热节流点
thermal_throttle = merged[merged['bandwidth'] < merged['bandwidth'].mean() * 0.8]
if len(thermal_throttle) > 0:
    throttle_temp = thermal_throttle['temp'].min()
    print(f"热节流起始温度：{throttle_temp/1000:.1f}°C")
```

### 预期现象
```
温度范围 | 性能 | 说明
---------|------|------
<60°C    | 正常 | 无影响
60-75°C  | 正常 | 警告范围
75-85°C  | 下降 | 开始节流
>85°C    | 大幅下降 | 严重节流
```

### 最佳实践
```bash
# 1. 改善散热
# - 加散热片
# - 增加风道
# - 降低环境温度

# 2. 优化测试
# - 增加测试间隔
# - 降低测试强度

# 3. 监控温度
# - 设置温度告警
# - 自动停止过热测试
```

---

## 八、对比不同配置

### 场景描述
测试不同系统配置对性能的影响。

### 测试场景

#### 1. I/O 调度器对比
```bash
# 测试 none 调度器
echo none > /sys/block/sda/queue/scheduler
python3 bin/SysTest run --quick
cp results/latest.json results/scheduler_none.json

# 测试 mq-deadline 调度器
echo mq-deadline > /sys/block/sda/queue/scheduler
python3 bin/SysTest run --quick
cp results/latest.json results/scheduler_deadline.json

# 对比
python3 bin/SysTest compare-baseline \
    --baseline1 results/scheduler_none.json \
    --baseline2 results/scheduler_deadline.json
```

#### 2. CPU Governor 对比
```bash
# performance 模式
echo performance | tee /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor
python3 bin/SysTest run --quick

# ondemand 模式
echo ondemand | tee /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor
python3 bin/SysTest run --quick
```

#### 3. 测试路径对比
```bash
# /tmp (可能是 tmpfs)
python3 bin/SysTest run --path=/tmp

# /data (UFS 上)
python3 bin/SysTest run --path=/data

# 直接设备
python3 bin/SysTest run --device=/dev/sda
```

### 最佳实践
```bash
# 1. 控制变量
# 一次只改一个配置

# 2. 多次测试
# 每次配置测试 3 次取平均

# 3. 记录配置
# 保存系统配置快照
```

---

## 九、故障排查流程

### 场景描述
系统化的故障排查流程。

### 排查步骤

#### Step 1: 确认现象
```bash
# 复现问题
python3 bin/SysTest run --test=<problematic_test>

# 记录现象
cat > issue_report.txt << EOF
问题：[描述]
复现步骤：[步骤]
发生频率：[偶尔/持续]
影响范围：[单台/批量]
EOF
```

#### Step 2: 收集信息
```bash
# 环境信息
python3 bin/SysTest check-env > env.txt

# 系统日志
dmesg > dmesg.txt

# 测试日志
cp logs/latest.log issue_log.txt
```

#### Step 3: 初步分析
```bash
# 检查常见错误
grep -i "error\|fail" issue_log.txt

# 检查温度
cat temp.txt

# 检查空间
df -h /
```

#### Step 4: 深入诊断
```bash
# 手动 FIO 测试
fio --name=debug --rw=randread --bs=4k \
    --iodepth=32 --runtime=60 \
    --filename=/tmp/test --direct=1 \
    --output-format=json+
```

#### Step 5: 定位根因
```
根据收集的信息，分析可能原因:
- 配置问题？
- 系统干扰？
- 硬件故障？
- 正常行为？
```

#### Step 6: 实施解决
```bash
# 根据根因采取相应措施
# 然后重新测试验证
```

### 最佳实践
```bash
# 1. 使用检查清单
# 确保不遗漏步骤

# 2. 记录所有操作
# 便于回溯

# 3. 一次只改一个变量
# 确认效果

# 4. 验证解决方案
# 确保问题真正解决
```

---

## 十、生成客户报告

### 场景描述
为客户生成专业的测试报告。

### 报告模板
```markdown
# UFS 性能测试报告

## 客户信息
- 客户名称：[客户名]
- 设备型号：[型号]
- 测试日期：[日期]

## 测试概述
- 测试模式：完整模式
- 测试套件：Performance + QoS + Reliability
- 测试标准：JEDEC UFS 3.1

## 测试结果

### 性能测试
| 测试项 | 结果 | 规格 | 判定 |
|--------|------|------|------|
| 顺序读取 | 2156 MB/s | ≥2000 | ✓ |
| 顺序写入 | 1723 MB/s | ≥1200 | ✓ |
| 随机读 IOPS | 62341 | ≥50000 | ✓ |
| 随机写 IOPS | 51234 | ≥40000 | ✓ |

### QoS 测试
| 测试项 | 结果 | 规格 | 判定 |
|--------|------|------|------|
| P50 延迟 | 100 μs | - | - |
| P99 延迟 | 500 μs | <1ms | ✓ |
| P99.99 延迟 | 1.8ms | <5ms | ✓ |

### 可靠性测试
| 测试项 | 结果 | 判定 |
|--------|------|------|
| 坏块数量 | 3 | ✓ |
| ECC 错误率 | <10⁻¹⁵ | ✓ |
| 耐久性测试 | 通过 | ✓ |

## 结论
✅ 所有测试通过，设备符合规格要求

## 附件
- 完整测试日志
- 原始数据文件
- 测试环境说明
```

### 生成命令
```bash
# 执行测试
python3 bin/SysTest run --full

# 生成报告
python3 scripts/generate_customer_report.py \
    --input results/latest.json \
    --output report_customer.md \
    --template templates/customer_report.md
```

### 最佳实践
```
1. 使用客户模板
2. 包含所有关键指标
3. 清晰的判定标准
4. 专业的格式
5. 附上原始数据
```

---

## 十一、产线快速测试

### 场景描述
生产线上快速测试每台设备。

### 测试要求
- 耗时：<3 分钟/台
- 覆盖：关键指标
- 判定：Pass/Fail

### 测试配置
```bash
python3 bin/SysTest run \
    --test=seq_read,seq_write,rand_read \
    --time=30 \
    --quick
```

### 自动化脚本
```bash
#!/bin/bash
# production_test.sh

DEVICE=$1
SERIAL=$2

echo "=== 产线测试 ==="
echo "设备：$DEVICE"
echo "序列号：$SERIAL"
echo

# 执行测试
python3 bin/SysTest run \
    --device=$DEVICE \
    --test=seq_read,seq_write,rand_read \
    --time=30

# 检查结果
if [ $? -eq 0 ]; then
    echo "✅ PASS"
    echo "$SERIAL,PASS,$(date)" >> production_log.csv
else
    echo "❌ FAIL"
    echo "$SERIAL,FAIL,$(date)" >> production_log.csv
fi
```

### 最佳实践
```
1. 最小化测试项
2. 缩短测试时间
3. 自动化判定
4. 记录每台结果
5. 不良品隔离
```

---

## 十二、研发深度分析

### 场景描述
研发阶段深入分析设备性能特性。

### 测试配置
```bash
# 详细延迟分析
fio --name=analysis \
    --rw=randread \
    --bs=4k \
    --iodepth=1 \
    --runtime=300 \
    --filename=/dev/sda \
    --direct=1 \
    --output-format=json+ \
    --latency-log=lat_log \
    --log_hist_msec=1000 \
    --write_hist_log=hist_log
```

### 分析方法
```python
# 延迟分布分析
import numpy as np

latencies = np.loadtxt('lat_log.1.log', usecols=[1])

print(f"Mean: {np.mean(latencies):.1f} μs")
print(f"StdDev: {np.std(latencies):.1f} μs")
print(f"CV: {np.std(latencies)/np.mean(latencies)*100:.1f}%")
print(f"P50: {np.percentile(latencies, 50):.1f} μs")
print(f"P99: {np.percentile(latencies, 99):.1f} μs")
print(f"P99.99: {np.percentile(latencies, 99.99):.1f} μs")
```

### 最佳实践
```
1. 长时间测试 (300s+)
2. 高采样率 (1s)
3. 详细日志
4. 统计分析
5. 可视化展示
```

---

## 十三、竞品对比测试

### 场景描述
对比多个竞品的性能。

### 测试方法
```bash
# 测试设备 A
python3 bin/SysTest run --device=/dev/sda --full
cp results/latest.json results/device_A.json

# 测试设备 B
python3 bin/SysTest run --device=/dev/sdb --full
cp results/latest.json results/device_B.json

# 测试设备 C
python3 bin/SysTest run --device=/dev/sdc --full
cp results/latest.json results/device_C.json
```

### 对比分析
```python
import pandas as pd

# 加载数据
devices = ['A', 'B', 'C']
data = []

for d in devices:
    with open(f'results/device_{d}.json') as f:
        result = json.load(f)
    data.append({
        'device': d,
        'seq_read': result['results'][0]['read_bw_mb'],
        'seq_write': result['results'][1]['write_bw_mb'],
        'rand_read': result['results'][2]['iops'],
        # ...
    })

df = pd.DataFrame(data)
print(df)

# 绘制对比图
df.plot(x='device', kind='bar', figsize=(12,6))
plt.savefig('comparison.png')
```

### 最佳实践
```
1. 相同测试条件
2. 相同环境温度
3. 多次测试取平均
4. 公平对比
5. 完整报告
```

---

## 十四、自动化 CI/CD

### 场景描述
集成到 CI/CD 流程自动测试。

### GitHub Actions 示例
```yaml
name: UFS Test

on: [push, pull_request]

jobs:
  test:
    runs-on: self-hosted
    steps:
    - uses: actions/checkout@v2
    
    - name: Run UFS Test
      run: |
        cd systest
        python3 bin/SysTest run --suite=performance --quick
    
    - name: Upload Results
      uses: actions/upload-artifact@v2
      with:
        name: test-results
        path: systest/results/
```

### Jenkins 示例
```groovy
pipeline {
    agent any
    stages {
        stage('Test') {
            steps {
                sh 'cd systest && python3 bin/SysTest run --quick'
            }
        }
        stage('Report') {
            steps {
                sh 'python3 bin/SysTest report --generate-html'
            }
        }
    }
}
```

### 最佳实践
```
1. 快速测试 (quick 模式)
2. 失败即停止
3. 保存测试结果
4. 通知机制
5. 历史趋势
```

---

## 十五、长期健康追踪

### 场景描述
追踪设备长期健康状态。

### 监控脚本
```bash
#!/bin/bash
# health_tracker.sh

while true; do
    TIMESTAMP=$(date +%Y%m%d_%H%M%S)
    
    # 执行测试
    python3 bin/SysTest run --quick
    
    # 提取关键指标
    python3 << EOF
import json
from datetime import datetime

with open('results/latest.json') as f:
    data = json.load(f)

# 保存到数据库
with open('health_db.csv', 'a') as f:
    f.write(f"{datetime.now().isoformat()},")
    for result in data['results']:
        if 'read_bw_mb' in result:
            f.write(f"{result['read_bw_mb']},")
        if 'iops' in result:
            f.write(f"{result['iops']},")
    f.write("\\n")
EOF
    
    # 等待下次测试 (每天)
    sleep 86400
done
```

### 趋势分析
```python
import pandas as pd
import matplotlib.pyplot as plt

# 加载数据
df = pd.read_csv('health_db.csv', names=['date', 'seq_read', 'rand_iops'])
df['date'] = pd.to_datetime(df['date'])

# 绘制趋势
fig, ax = plt.subplots(2, 1, figsize=(12, 8))

ax[0].plot(df['date'], df['seq_read'])
ax[0].set_title('Sequential Read Trend')
ax[0].set_ylabel('MB/s')

ax[1].plot(df['date'], df['rand_iops'])
ax[1].set_title('Random IOPS Trend')
ax[1].set_ylabel('IOPS')

plt.tight_layout()
plt.savefig('health_trend.png')
```

### 最佳实践
```
1. 固定测试时间
2. 保存原始数据
3. 定期分析趋势
4. 设置预警阈值
5. 及时响应异常
```

---

## 总结

通过这 15 个场景，我们展示了 UFS Auto 测试框架在各种实际情况下的应用。关键要点：

1. **选择合适的测试模式**
   - 日常开发：quick 模式
   - 版本发布：full 模式
   - 产线测试：最小化配置

2. **理解测试目的**
   - 功能验证 vs 性能分析
   - 快速反馈 vs 深度分析
   - 单次测试 vs 长期监控

3. **遵循最佳实践**
   - 控制变量
   - 多次验证
   - 记录环境
   - 对比基线

4. **善用工具**
   - SysTest 内置命令
   - 系统级工具 (iostat, dmesg)
   - 自定义脚本

5. **持续改进**
   - 积累经验
   - 完善流程
   - 优化配置

---

*版本：1.0*  
*最后更新：2026-04-05*  
*维护者：UFS Auto Team*
