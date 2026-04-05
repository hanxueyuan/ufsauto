# UFS 测试故障诊断深度指南

---

## 目录

1. [诊断方法论](#一诊断方法论)
2. [诊断工具与命令](#二诊断工具与命令)
3. [典型故障案例分析](#三典型故障案例分析)
4. [性能问题分析](#四性能问题分析)
5. [可靠性问题分析](#五可靠性问题分析)
6. [QoS 问题分析](#六 qos 问题分析)
7. [系统级问题分析](#七系统级问题分析)
8. [故障诊断检查清单](#八故障诊断检查清单)

---

## 一、诊断方法论

### 1.1 诊断思维框架

```
                    故障现象
                       │
         ┌─────────────┼─────────────┐
         │             │             │
    ┌────▼────┐   ┌────▼────┐   ┌────▼────┐
    │ 是什么？ │   │ 为什么？ │   │ 怎么办？ │
    │ (What)  │   │ (Why)   │   │ (How)   │
    └─────────┘   └─────────┘   └─────────┘
         │             │             │
    确认现象      分析根因      实施解决
    收集数据      验证假设      验证效果
```

### 1.2 诊断五步法

#### 第一步：现象确认 (5W1H)

```
What:   什么问题？(性能低/波动大/延迟高/测试失败)
When:   什么时候发生？(首次/偶尔/持续)
Where:  在哪里发生？(特定测试/所有测试)
Who:    谁遇到？(单台设备/批量)
Why:    为什么现在？(变更后/自然发生)
How:    如何复现？(具体步骤)
```

#### 第二步：数据收集

```
┌─────────────────────────────────────────────────────────┐
│  数据收集清单                                            │
├─────────────────────────────────────────────────────────┤
│  □ 测试日志 (SysTest logs)                              │
│  □ 系统日志 (dmesg, syslog)                             │
│  □ 设备信息 (型号、固件、容量)                          │
│  □ 环境信息 (温度、系统负载)                            │
│  □ 测试结果 (完整 JSON 输出)                              │
│  □ Baseline 对比数据                                     │
│  □ 复现步骤记录                                          │
└─────────────────────────────────────────────────────────┘
```

#### 第三步：假设建立

```
基于现象提出假设:

现象：写入性能低
├─ 假设 1: SLC cache 耗尽
├─ 假设 2: 热节流
├─ 假设 3: 测试配置错误
├─ 假设 4: 设备故障
└─ 假设 5: 系统干扰

针对每个假设设计验证方法
```

#### 第四步：验证排除

```
假设验证矩阵:

| 假设 | 验证方法 | 预期结果 | 实际结果 | 结论 |
|------|----------|----------|----------|------|
| SLC 耗尽 | 延长测试观察 | 性能先高后低 | 符合 | 可能 |
| 热节流 | 监控温度 | 温度>80°C | 45°C | 排除 |
| 配置错误 | 检查 direct | direct=0 | 符合 | 确认 |
```

#### 第五步：根因定位

```
确认根因 → 实施解决 → 验证效果 → 更新 Baseline
```

### 1.3 诊断原则

#### 原则 1: 从简单到复杂

```
先检查:
✓ 测试配置 (direct=1?)
✓ 设备路径 (正确？)
✓ 权限 (root?)
✓ 空间 (足够？)

再深入:
→ 系统日志
→ 硬件诊断
→ 固件分析
```

#### 原则 2: 控制变量

```
一次只改变一个变量:

错误做法:
同时改 QD、bs、runtime → 无法确定哪个因素影响

正确做法:
只改 QD: QD1 → QD4 → QD32
只改 bs: 4k → 64k → 128k
```

#### 原则 3: 对比分析

```
三个维度对比:

1. 时间维度: vs Baseline (是否退化)
2. 空间维度: vs 同型号 (是否个体差异)
3. 规格维度: vs 规格书 (是否达标)
```

#### 原则 4: 数据驱动

```
用数据说话:

❌ "感觉性能低"
✓ "顺序写入 800 MB/s，低于 Baseline 1200 MB/s 33%"

❌ "延迟有点高"
✓ "P99 延迟 2ms，规格要求<1ms，超标 100%"
```

---

## 二、诊断工具与命令

### 2.1 SysTest 内置工具

#### 环境检查
```bash
# 完整环境检查
SysTest check-env

# 保存配置
SysTest check-env --save-config
```

#### 测试执行
```bash
# 快速诊断
SysTest run --quick -v

# 完整诊断
SysTest run --full --loops=3

# 特定测试
SysTest run --test=seq_write -v
```

#### 结果分析
```bash
# 查看最新报告
SysTest report --latest

# 对比 Baseline
SysTest compare-baseline

# 生成 HTML 报告
SysTest report --generate-html
```

### 2.2 系统级工具

#### 设备信息
```bash
# 块设备列表
lsblk -o NAME,MODEL,SIZE,TYPE,MOUNTPOINT

# 设备详细信息
cat /sys/block/sda/device/model
cat /sys/block/sda/device/rev

# 设备统计
cat /sys/block/sda/stat
```

#### 文件系统
```bash
# 挂载信息
df -Th

# 挂载选项
mount | grep sda

# 文件系统类型
blkid /dev/sda
```

#### 系统日志
```bash
# 实时日志
dmesg -w

# 最近错误
dmesg --level=err

# UFS 相关
dmesg | grep -iE "ufs|scsi|sd"

# 搜索特定错误
dmesg | grep -i "I/O error"
dmesg | grep -i "timeout"
dmesg | grep -i "reset"
```

#### 性能监控
```bash
# I/O 统计 (每秒刷新)
iostat -x 1

# 进程 I/O
iotop

# 实时延迟
blktrace -d /dev/sda -o - | blkparse -i -
```

#### 温度监控
```bash
# 读取温度
cat /sys/class/thermal/thermal_zone*/temp

# 持续监控
watch -n 1 'cat /sys/class/thermal/thermal_zone*/temp'

# 温度历史
for i in {1..60}; do
    cat /sys/class/thermal/thermal_zone*/temp
    sleep 1
done
```

### 2.3 FIO 高级诊断

#### 详细输出模式
```bash
fio --name=debug \
    --rw=randread \
    --bs=4k \
    --iodepth=32 \
    --runtime=60 \
    --filename=/tmp/test \
    --direct=1 \
    --output-format=json+ \
    --latency-log=lat_log \
    --bandwidth_log=bw_log \
    --iops_log=iops_log
```

#### 延迟直方图
```bash
fio --name=histogram \
    --rw=randread \
    --bs=4k \
    --iodepth=1 \
    --runtime=60 \
    --filename=/tmp/test \
    --direct=1 \
    --lat_percentiles=1 \
    --log_hist_msec=1000 \
    --write_hist_log=hist_log
```

#### 压力测试
```bash
# 长时间压力
fio --name=stress \
    --rw=randrw \
    --rwmixread=50 \
    --bs=4k \
    --iodepth=64 \
    --runtime=3600 \
    --size=10G \
    --filename=/tmp/test \
    --direct=1 \
    --verify=md5
```

### 2.4 诊断脚本

#### 快速诊断脚本
```bash
#!/bin/bash
# quick_diagnose.sh

echo "=== UFS 快速诊断 ==="

# 1. 设备检查
echo -e "\n[1] 设备信息:"
lsblk | grep -E "NAME|sda"

# 2. 空间检查
echo -e "\n[2] 空间使用:"
df -h / | tail -1

# 3. 温度检查
echo -e "\n[3] 温度:"
cat /sys/class/thermal/thermal_zone*/temp 2>/dev/null || echo "N/A"

# 4. 系统负载
echo -e "\n[4] 系统负载:"
uptime

# 5. 最近错误
echo -e "\n[5] 最近 I/O 错误:"
dmesg | grep -i "I/O error" | tail -5 || echo "无"

# 6. FIO 快速测试
echo -e "\n[6] FIO 快速测试 (10s):"
fio --name=quick --rw=randread --bs=4k --iodepth=32 \
    --runtime=10 --filename=/tmp/test --direct=1 \
    --output-format=normal 2>&1 | grep -E "READ|WRITE"

echo -e "\n=== 诊断完成 ==="
```

#### 性能对比脚本
```bash
#!/bin/bash
# perf_compare.sh

BASELINE=$1
CURRENT=$2

if [ -z "$BASELINE" ] || [ -z "$CURRENT" ]; then
    echo "用法：$0 <baseline.json> <current.json>"
    exit 1
fi

echo "=== 性能对比 ==="
echo "Baseline: $BASELINE"
echo "Current:  $CURRENT"
echo

# 使用 Python 解析 JSON 对比
python3 << EOF
import json

with open('$BASELINE') as f:
    baseline = json.load(f)
with open('$CURRENT') as f:
    current = json.load(f)

# 对比各项指标
for test in current['results']:
    name = test['name']
    # 找到 baseline 对应项
    for base in baseline['results']:
        if base['name'] == name:
            if 'read_bw_mb' in test and test['read_bw_mb'] > 0:
                delta = (test['read_bw_mb'] - base['read_bw_mb']) / base['read_bw_mb'] * 100
                print(f"{name}: {test['read_bw_mb']:.1f} vs {base['read_bw_mb']:.1f} MB/s ({delta:+.1f}%)")
            break
EOF
```

---

## 三、典型故障案例分析

### 案例 1: 写入性能突然下降 70%

#### 现象
```
报告：顺序写入从 1200 MB/s 降至 350 MB/s
发生时间：持续写入 30 秒后
复现：100% 可复现
```

#### 诊断过程

**Step 1: 确认现象**
```bash
# 复现测试
SysTest run --test=seq_write --time=120

# 观察性能曲线
# 结果：前 30 秒~1200 MB/s，之后降至~350 MB/s
```

**Step 2: 收集数据**
```bash
# 检查温度
watch -n 1 'cat /sys/class/thermal/thermal_zone*/temp'
# 结果：45°C → 52°C (正常)

# 检查系统日志
dmesg | grep -i "scsi"
# 结果：无错误

# 详细 FIO 测试
fio --name=debug --rw=write --bs=128k --iodepth=32 \
    --runtime=120 --filename=/tmp/test --direct=1 \
    --output-format=json+
```

**Step 3: 建立假设**
```
假设 1: SLC cache 耗尽 (最可能)
假设 2: 热节流 (温度正常，排除)
假设 3: 设备故障 (无错误，可能性低)
```

**Step 4: 验证假设**
```bash
# 验证 SLC cache
# 方法：空闲 30 分钟后重测

sleep 1800  # 空闲 30 分钟

SysTest run --test=seq_write --time=120
# 结果：恢复 1200 MB/s

# 结论：SLC cache 耗尽确认
```

**Step 5: 根因分析**
```
根因：SLC write cache 容量有限

机制:
1. 初始写入使用 SLC cache (快)
2. SLC cache 用尽后切换到 TLC 直写 (慢)
3. 空闲时 GC 回收 SLC cache

这是正常行为，非故障
```

#### 解决方案
```
1. 增加 ramp_time，等待性能稳定
   fio --ramp_time=30 ...

2. 测试前空闲设备，让 GC 完成

3. 在报告中注明 SLC cache 特性

4. 如需持续高性能，选择更大 SLC cache 的设备
```

#### 经验教训
```
✓ SLC cache 耗尽是正常现象
✓ 测试写入性能需考虑 SLC cache 大小
✓ 长时间写入测试需增加 ramp_time
✓ 区分"故障"和"特性"
```

---

### 案例 2: 随机读 IOPS 波动大 (±30%)

#### 现象
```
报告：随机读 IOPS 在 40K-70K 之间波动
发生时间：每次测试结果不同
复现：100% 可复现波动
```

#### 诊断过程

**Step 1: 确认现象**
```bash
# 连续测试 5 次
for i in {1..5}; do
    SysTest run --test=rand_read --time=60
done

# 结果：
# Run 1: 42341 IOPS
# Run 2: 68234 IOPS
# Run 3: 45123 IOPS
# Run 4: 65432 IOPS
# Run 5: 41234 IOPS
# 波动：±30%
```

**Step 2: 收集数据**
```bash
# 检查系统负载
uptime
# 结果：load average 波动大

# 检查后台进程
ps aux --sort=-%cpu | head -10
# 结果：发现后台备份进程

# 检查 I/O 干扰
iostat -x 1
# 结果：其他进程 I/O 活动
```

**Step 3: 建立假设**
```
假设 1: 系统负载干扰 (可能)
假设 2: 后台进程 I/O (确认)
假设 3: 设备问题 (可能性低)
```

**Step 4: 验证假设**
```bash
# 停止后台进程
systemctl stop backup-service

# 重新测试 5 次
for i in {1..5}; do
    SysTest run --test=rand_read --time=60
done

# 结果：
# Run 1: 62341 IOPS
# Run 2: 63124 IOPS
# Run 3: 61897 IOPS
# Run 4: 62543 IOPS
# Run 5: 62876 IOPS
# 波动：±2%

# 结论：系统干扰确认
```

**Step 5: 根因分析**
```
根因：后台进程占用 I/O 资源

机制:
1. 备份进程读取大量文件
2. 占用 I/O 带宽和 IOPS
3. 测试进程资源被抢占
4. 结果波动大
```

#### 解决方案
```
1. 测试前停止非必要服务
   systemctl stop backup-service
   systemctl stop unnecessary-services

2. 使用 ionice 提升测试进程优先级
   ionice -c 1 -n 0 fio ...

3. 在隔离环境测试 (单用户模式)

4. 建立标准测试流程 (SOP)
```

#### 经验教训
```
✓ 测试前清理系统负载
✓ 识别并停止后台干扰进程
✓ 使用 ionice/cpulimit 控制资源
✓ 多次测试取平均
```

---

### 案例 3: P99.99 延迟超标 10 倍

#### 现象
```
报告：P99.99 延迟 15ms，规格要求<1.5ms
发生时间：持续出现
复现：100% 可复现
```

#### 诊断过程

**Step 1: 确认现象**
```bash
# 延迟详细测试
fio --name=latency --rw=randread --bs=4k --iodepth=1 \
    --runtime=120 --filename=/tmp/test --direct=1 \
    --output-format=json+ --lat_percentiles=1

# 结果:
# P50:    100 μs
# P99:    500 μs
# P99.99: 15000 μs (15ms) ← 超标
# P99.999: 50000 μs (50ms)
```

**Step 2: 收集数据**
```bash
# 延迟日志分析
fio --latency-log=lat_log ...

# 分析延迟分布
cat lat_log.1.log | awk '{print $2}' | sort -n | tail -100

# 结果：发现周期性延迟尖峰 (~10ms 间隔)
```

**Step 3: 建立假设**
```
假设 1: 系统定时器中断 (可能)
假设 2: 设备 GC 操作 (可能)
假设 3: CPU 频率调节 (可能)
假设 4: 网络中断 (可能)
```

**Step 4: 验证假设**
```bash
# 检查 CPU governors
cat /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor
# 结果：ondemand (动态调频)

# 切换到 performance
echo performance | tee /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor

# 重新测试
fio --name=latency ...

# 结果：P99.99 降至 2ms (仍超标)

# 检查中断
cat /proc/interrupts | grep -E "eth|mmc"
# 结果：网络中断频繁

# 禁用网络
ifconfig eth0 down

# 重新测试
fio --name=latency ...

# 结果：P99.99 降至 0.8ms (合格)

# 结论：网络中断干扰确认
```

**Step 5: 根因分析**
```
根因：网络中断导致延迟尖峰

机制:
1. 网络数据包到达
2. 触发硬件中断
3. CPU 暂停当前任务处理中断
4. I/O 请求被延迟 (10-50ms)
```

#### 解决方案
```
1. 测试时禁用网络
   ifconfig eth0 down

2. 使用 IRQ 亲和性隔离
   # 将网络中断绑定到特定 CPU
   echo 2 > /proc/irq/XX/smp_affinity

3. 使用实时内核
   # PREEMPT_RT 补丁

4. 禁用 CPU 频率调节
   echo performance > /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor
```

#### 经验教训
```
✓ 延迟测试需在隔离环境
✓ 网络中断是延迟杀手
✓ CPU 频率调节影响延迟
✓ QoS 测试需严格控制环境
```

---

### 案例 4: 测试失败 - I/O Error

#### 现象
```
报告：测试中途失败，报错"I/O error"
发生时间：运行 5 分钟后
复现：偶尔复现 (30%)
```

#### 诊断过程

**Step 1: 确认现象**
```bash
# 查看详细错误
SysTest run --test=endurance -v

# 日志:
# [ERROR] FIO 执行失败：I/O error
# [ERROR] 设备：/dev/sda, 扇区：12345678
```

**Step 2: 收集数据**
```bash
# 系统日志
dmesg | tail -50

# 结果:
# [12345.678] sd 0:0:0:0: [sda] tag#0 FAILED Result: hostbyte=DID_OK driverbyte=DRIVER_SENSE
# [12345.679] sd 0:0:0:0: [sda] tag#0 Sense Key : Medium Error [current]
# [12345.680] sd 0:0:0:0: [sda] tag#0 Add. Sense: Unrecovered read error
```

**Step 3: 建立假设**
```
假设 1: 坏块 (可能)
假设 2: 连接问题 (可能)
假设 3: 电源问题 (可能)
假设 4: 设备故障 (可能)
```

**Step 4: 验证假设**
```bash
# 检查坏块
badblocks -v /dev/sda

# 结果：发现 3 个坏块

# 检查连接
# 重新插拔设备

# 重新测试
SysTest run --test=endurance

# 结果：仍然失败

# 更换设备测试
SysTest run --device=/dev/sdb --test=endurance

# 结果：通过

# 结论：设备硬件故障确认
```

**Step 5: 根因分析**
```
根因：NAND 闪存坏块

机制:
1. NAND 单元达到 P/E 寿命极限
2. 形成坏块
3. FTL 无法映射
4. I/O 操作失败
```

#### 解决方案
```
1. 立即停止使用该设备

2. 备份重要数据

3. 更换设备

4. 分析故障设备:
   - 发送厂商 FA
   - 分析根本原因
   - 评估批次风险
```

#### 经验教训
```
✓ I/O error 是严重错误
✓ 立即停止测试，避免数据丢失
✓ 检查系统日志定位根因
✓ 准备备用设备
```

---

## 四、性能问题分析

### 4.1 顺序读写性能低

#### 症状
```
顺序读取 < 1500 MB/s (UFS 3.1)
顺序写入 < 800 MB/s (UFS 3.1)
```

#### 诊断树
```
性能低
├─ 检查测试配置
│  ├─ direct=1? → 否 → 修正
│  └─ bs 足够大？(128k+) → 否 → 修正
├─ 检查设备状态
│  ├─ 温度过高？ → 是 → 改善散热
│  └─ 空间不足？ → 是 → 清理空间
├─ 检查系统干扰
│  ├─ 后台 I/O? → 是 → 停止干扰
│  └─ CPU 瓶颈？ → 是 → 优化系统
└─ 检查硬件
   ├─ 设备故障？ → 是 → 更换
   └─ 连接问题？ → 是 → 重新连接
```

#### 检查清单
```bash
# 1. 测试配置
fio --showcmd  # 查看实际命令

# 2. 设备温度
cat /sys/class/thermal/thermal_zone*/temp

# 3. 可用空间
df -h /

# 4. 系统负载
uptime
top -bn1 | head -10

# 5. 后台 I/O
iostat -x 1 5
```

### 4.2 随机读写 IOPS 低

#### 症状
```
随机读 IOPS < 40K (UFS 3.1, QD32)
随机写 IOPS < 30K (UFS 3.1, QD32)
```

#### 诊断树
```
IOPS 低
├─ 检查 QD (iodepth)
│  └─ QD < 32? → 是 → 增加 QD
├─ 检查 numjobs
│  └─ numjobs = 1? → 是 → 增加到 2-4
├─ 检查 bs
│  └─ bs != 4k? → 是 → 改为 4k
├─ 检查设备性能上限
│  └─ 对比规格书 → 已达上限 → 正常
└─ 检查系统限制
   ├─ 队列深度限制？ → 是 → 调整
   └─ 中断限制？ → 是 → 优化
```

#### 检查清单
```bash
# 1. 检查 QD 配置
grep iodepth test_config.json

# 2. 检查系统队列限制
cat /sys/block/sda/queue/nr_requests

# 3. 增加 numjobs 测试
fio --numjobs=4 --iodepth=32 ...

# 4. 对比规格书
# UFS 3.1 256GB: ~60K IOPS (rand read)
```

### 4.3 写入性能远低于读取

#### 症状
```
写入/读取 < 0.5 (正常应>0.6)
```

#### 诊断分析
```
正常情况:
- UFS 写入通常比读取慢 20-40%
- 原因：编程时间 > 读取时间

异常情况:
- 写入/读取 < 0.5
- 可能原因：
  1. SLC cache 耗尽
  2. 写缓存禁用
  3. 设备故障
```

#### 诊断步骤
```bash
# 1. 检查是否 SLC cache 耗尽
# 方法：空闲 30 分钟后重测写入

# 2. 检查写缓存
hdparm -W0 /dev/sda  # 禁用
hdparm -W1 /dev/sda  # 启用

# 3. 对比同型号设备
# 如果差异>30%，可能故障
```

---

## 五、可靠性问题分析

### 5.1 坏块增长

#### 症状
```
坏块数量持续增加
```

#### 诊断步骤
```bash
# 1. 确认坏块数量
smartctl -a /dev/sda | grep -i "reallocated"

# 2. 检查增长趋势
# 对比历史记录

# 3. 压力测试验证
SysTest run --test=bad_block_monitor --loops=10

# 4. 评估风险
if new_bad_blocks > 20:
    status = "高风险"
elif new_bad_blocks > 5:
    status = "需关注"
else:
    status = "正常"
```

### 5.2 ECC 错误率高

#### 症状
```
ECC 校正次数异常高
```

#### 诊断步骤
```bash
# 1. 读取 ECC 统计
# (需要设备支持)

# 2. 执行数据完整性测试
SysTest run --test=ecc_error_rate --verify=md5

# 3. 计算 UBER
UBER = uncorrectable_errors / total_bits_read

# 4. 判定
if UBER > 10**-12:
    status = "不合格"
```

---

## 六、QoS 问题分析

### 6.1 延迟抖动大

#### 症状
```
CV > 30% (延迟变异系数)
```

#### 诊断步骤
```bash
# 1. 多次测试计算 CV
latencies = []
for i in range(10):
    result = run_latency_test()
    latencies.append(result['p99'])

cv = std(latencies) / mean(latencies) * 100

# 2. 分析原因
# - 系统干扰？
# - 温度变化？
# - 电源波动？

# 3. 针对性解决
```

### 6.2 尾部延迟发散

#### 症状
```
P99.999 / P50 > 50
```

#### 诊断步骤
```bash
# 1. 分析延迟分布
fio --latency-log=lat_log ...

# 2. 识别尖峰
cat lat_log.*.log | awk '{print $2}' | sort -n | tail -100

# 3. 关联分析
# - 尖峰时刻的系统事件
# - 中断、GC、调度等
```

---

## 七、系统级问题分析

### 7.1 I/O 调度器影响

#### 检查当前调度器
```bash
cat /sys/block/sda/queue/scheduler
# 输出：[mq-deadline] kyber none
```

#### 测试不同调度器
```bash
# 切换到 none (推荐 for NVMe/UFS)
echo none > /sys/block/sda/queue/scheduler

# 测试性能
SysTest run --quick

# 切换回 mq-deadline
echo mq-deadline > /sys/block/sda/queue/scheduler

# 对比结果
```

### 7.2 CPU 频率调节影响

#### 检查当前 governor
```bash
cat /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor
```

#### 切换到 performance
```bash
echo performance | tee /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor
```

#### 对比测试
```bash
# ondemand 模式
SysTest run --quick
# 记录结果

# performance 模式
echo performance | tee /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor
SysTest run --quick
# 记录结果

# 对比差异
```

---

## 八、故障诊断检查清单

### 8.1 快速检查清单 (5 分钟)

```
□ 设备路径正确？
□ 权限足够 (root)?
□ 空间充足 (≥2GB)?
□ FIO 工具安装？
□ direct=1 配置？
□ 温度正常 (<70°C)?
□ 无 I/O error 日志？
```

### 8.2 标准检查清单 (30 分钟)

```
□ 执行 SysTest check-env
□ 查看 dmesg 日志
□ 检查系统负载
□ 识别后台干扰进程
□ 测试不同 QD 配置
□ 对比 Baseline
□ 检查调度器配置
□ 检查 CPU governor
□ 温度监控测试
□ 重复测试验证
```

### 8.3 深度检查清单 (2 小时)

```
□ 完整 FIO 测试套件
□ 延迟分布分析
□ 温度 - 性能关联分析
□ 系统中断分析
□ 电源稳定性测试
□ 长时间压力测试
□ 数据完整性验证
□ 对比同型号设备
□ 厂商规格书对比
□ FA 分析 (如需要)
```

### 8.4 诊断报告模板

```markdown
# 故障诊断报告

## 基本信息
- 报告日期：2026-04-05
- 设备型号：UFS 3.1 256GB
- 固件版本：00001.00
- 问题类型：性能/可靠性/QoS

## 问题描述
[详细描述问题现象]

## 诊断过程
[逐步记录诊断步骤]

## 根因分析
[确定的根本原因]

## 解决方案
[实施的解决措施]

## 验证结果
[解决后的测试结果]

## 经验教训
[总结的经验]

## 附件
- 测试日志
- 系统日志
- 对比数据
```

---

## 附录：诊断命令速查

```bash
# 环境检查
SysTest check-env

# 快速测试
SysTest run --quick -v

# 查看日志
dmesg | grep -iE "ufs|scsi|sd"

# I/O 监控
iostat -x 1

# 温度监控
watch -n 1 'cat /sys/class/thermal/thermal_zone*/temp'

# 延迟分析
fio --latency-log=lat_log ...

# 调度器
cat /sys/block/sda/queue/scheduler

# CPU governor
cat /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor
```

---

*版本：1.0*  
*最后更新：2026-04-05*  
*维护者：UFS Auto Team*
