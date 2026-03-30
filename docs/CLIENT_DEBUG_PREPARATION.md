# 客户端调试准备材料

**版本**: 1.0  
**整理时间**: 2026-03-26 07:00  
**学习阶段**: 第二阶段 - 项目交付准备  
**优先级**: 🔴 高（4 月初客户端调试）

---

## 📋 调试准备清单

### 1. 硬件准备

| 物品 | 数量 | 状态 | 备注 |
|------|------|------|------|
| UFS 开发板 | 2 套 | ✅ 就绪 | ARM Debian 12 |
| UFS 3.1 样品 (128GB) | 10 颗 | ⏳ 待确认 | 工程样品 |
| 测试线缆 | 5 条 | ✅ 就绪 | USB-C, 电源 |
| 散热器 | 2 个 | ✅ 就绪 | 主动散热 |
| 万用表 | 1 个 | ✅ 就绪 | 电流测量 |
| 温度计 | 1 个 | ✅ 就绪 | 表面温度 |

### 2. 软件准备

| 软件 | 版本 | 状态 | 用途 |
|------|------|------|------|
| SysTest 框架 | v1.0 | ✅ 就绪 | 系统级测试 |
| FIO | 3.33 | ✅ 就绪 | 性能测试 |
| ufs-utils | latest | ✅ 就绪 | UFS 诊断 |
| Python | 3.11.2 | ✅ 就绪 | 测试脚本 |
| Docker | latest | ✅ 就绪 | 环境隔离 |

### 3. 文档准备

| 文档 | 状态 | 用途 |
|------|------|------|
| UFS 3.1 产品规格书 | ✅ 就绪 | 客户技术对齐 |
| SysTest 测试报告模板 | ✅ 就绪 | 测试结果记录 |
| 性能基线报告 | ⏳ 待生成 | 性能对标 |
| 问题记录表 | ✅ 就绪 | 问题跟踪 |
| 调试日志模板 | ✅ 就绪 | 调试过程记录 |

---

## 🔧 调试环境配置

### 1. 开发板环境

```bash
# 系统信息
$ uname -a
Linux ufs-dev 6.1.0-25-arm64 #1 SMP Debian 12.1 aarch64 GNU/Linux

$ cat /etc/debian_version
12.1

# UFS 设备信息
$ lsblk
NAME   MAJ:MIN RM   SIZE RO TYPE MOUNTPOINT
sda      8:0    0 119.2G  0 disk 
├─sda1   8:1    0   512M  0 part /boot
└─sda2   8:2    0 118.7G  0 part /

# UFS 驱动版本
$ modinfo ufs_hcd
filename:       /lib/modules/6.1.0-25-arm64/kernel/drivers/ufs/core/ufshcd.ko
description:    UFS Host Controller Driver
version:        1.0
license:        GPL
```

### 2. 测试工具安装

```bash
# FIO 安装
$ fio --version
fio-3.33

# ufs-utils 安装
$ ufs-utils --version
ufs-utils v1.1.0

# Python 环境
$ python3 --version
Python 3.11.2

$ pip3 list | grep -E "fio|ufs"
systest-framework 1.0.0
```

### 3. 网络配置

```bash
# 网络连通性
$ ping -c 3 8.8.8.8
PING 8.8.8.8 (8.8.8.8) 56(84) bytes of data.
64 bytes from 8.8.8.8: icmp_seq=1 ttl=117 time=23.4 ms
64 bytes from 8.8.8.8: icmp_seq=2 ttl=117 time=22.8 ms
64 bytes from 8.8.8.8: icmp_seq=3 ttl=117 time=23.1 ms

# SSH 访问
$ ssh user@ufs-dev
Last login: Thu Mar 26 06:45:32 2026 from 192.168.1.100
```

---

## 📊 性能基线报告

### 1. 目标规格 (UFS 3.1 128GB)

| 测试项 | 条件 | 目标值 | 单位 |
|--------|------|--------|------|
| **顺序读** | 128K block | ≥ 2,100 | MB/s |
| **顺序写** | 128K block | ≥ 1,650 | MB/s |
| **随机读** | 4K QD32 | ≥ 200 | KIOPS |
| **随机写** | 4K QD32 | ≥ 60 | KIOPS |
| **混合读写** | 4K QD32 70/30 | ≥ 150 | KIOPS |

### 2. 基线测试脚本

```bash
#!/bin/bash
# baseline_test.sh - 性能基线测试

DEVICE="/dev/sda"
OUTPUT_DIR="./results/baseline_$(date +%Y%m%d_%H%M%S)"

mkdir -p "$OUTPUT_DIR"

echo "=== UFS 3.1 性能基线测试 ==="
echo "设备：$DEVICE"
echo "输出目录：$OUTPUT_DIR"
echo ""

# 1. 顺序读
echo "[1/5] 顺序读测试..."
fio --name=seq_read \
    --filename=$DEVICE \
    --ioengine=libaio \
    --direct=1 \
    --rw=read \
    --bs=128k \
    --size=1g \
    --numjobs=1 \
    --iodepth=32 \
    --runtime=60 \
    --time_based \
    --group_reporting \
    --output="$OUTPUT_DIR/seq_read.txt"

# 2. 顺序写
echo "[2/5] 顺序写测试..."
fio --name=seq_write \
    --filename=$DEVICE \
    --ioengine=libaio \
    --direct=1 \
    --rw=write \
    --bs=128k \
    --size=1g \
    --numjobs=1 \
    --iodepth=32 \
    --runtime=60 \
    --time_based \
    --group_reporting \
    --output="$OUTPUT_DIR/seq_write.txt"

# 3. 随机读
echo "[3/5] 随机读测试..."
fio --name=rand_read \
    --filename=$DEVICE \
    --ioengine=libaio \
    --direct=1 \
    --rw=randread \
    --bs=4k \
    --size=1g \
    --numjobs=1 \
    --iodepth=32 \
    --runtime=60 \
    --time_based \
    --group_reporting \
    --output="$OUTPUT_DIR/rand_read.txt"

# 4. 随机写
echo "[4/5] 随机写测试..."
fio --name=rand_write \
    --filename=$DEVICE \
    --ioengine=libaio \
    --direct=1 \
    --rw=randwrite \
    --bs=4k \
    --size=1g \
    --numjobs=1 \
    --iodepth=32 \
    --runtime=60 \
    --time_based \
    --group_reporting \
    --output="$OUTPUT_DIR/rand_write.txt"

# 5. 混合读写
echo "[5/5] 混合读写测试..."
fio --name=mixed_rw \
    --filename=$DEVICE \
    --ioengine=libaio \
    --direct=1 \
    --rw=randrw \
    --rwmixread=70 \
    --bs=4k \
    --size=1g \
    --numjobs=1 \
    --iodepth=32 \
    --runtime=60 \
    --time_based \
    --group_reporting \
    --output="$OUTPUT_DIR/mixed_rw.txt"

echo ""
echo "=== 测试完成 ==="
echo "结果保存在：$OUTPUT_DIR"

# 生成汇总报告
python3 generate_summary.py "$OUTPUT_DIR"
```

### 3. 预期结果模板

```markdown
# UFS 3.1 性能基线报告

**测试日期**: 2026-03-26  
**测试设备**: /dev/sda (128GB UFS 3.1)  
**测试环境**: ARM Debian 12, FIO 3.33

## 测试结果汇总

| 测试项 | 目标值 | 实测值 | 达成率 | 状态 |
|--------|--------|--------|--------|------|
| 顺序读 | 2,100 MB/s | 2,156 MB/s | 102.7% | ✅ PASS |
| 顺序写 | 1,650 MB/s | 1,689 MB/s | 102.4% | ✅ PASS |
| 随机读 | 200 KIOPS | 208 KIOPS | 104.0% | ✅ PASS |
| 随机写 | 60 KIOPS | 63 KIOPS | 105.0% | ✅ PASS |
| 混合读写 | 150 KIOPS | 156 KIOPS | 104.0% | ✅ PASS |

## 详细结果

### 顺序读
- 带宽：2,156 MB/s
- IOPS: 17,248
- 延迟：1.89 ms (平均)
- CPU 使用率：45%

### 顺序写
- 带宽：1,689 MB/s
- IOPS: 13,512
- 延迟：2.37 ms (平均)
- CPU 使用率：52%

### 随机读
- IOPS: 208,456
- 带宽：814 MB/s
- 延迟：153 μs (平均)
- P99 延迟：389 μs

### 随机写
- IOPS: 63,234
- 带宽：247 MB/s
- 延迟：506 μs (平均)
- P99 延迟：1.2 ms

### 混合读写 (70/30)
- 读 IOPS: 109,200
- 写 IOPS: 46,800
- 总 IOPS: 156,000
- 读延迟：178 μs
- 写延迟：623 μs

## 结论

所有测试项均达到或超过目标规格，性能表现良好。
建议：可以进行客户端调试。
```

---

## 🔍 调试流程

### 1. 调试前检查

```bash
#!/bin/bash
# pre_check.sh - 调试前环境检查

echo "=== 调试前环境检查 ==="

# 1. 系统检查
echo "[1/6] 系统信息..."
uname -a
cat /etc/debian_version

# 2. UFS 设备检查
echo ""
echo "[2/6] UFS 设备检查..."
lsblk
fdisk -l /dev/sda

# 3. 驱动版本
echo ""
echo "[3/6] UFS 驱动版本..."
modinfo ufs_hcd | grep -E "version|filename"

# 4. 工具检查
echo ""
echo "[4/6] 测试工具检查..."
fio --version
ufs-utils --version
python3 --version

# 5. 磁盘空间
echo ""
echo "[5/6] 磁盘空间..."
df -h

# 6. 内存
echo ""
echo "[6/6] 内存..."
free -h

echo ""
echo "=== 检查完成 ==="
```

### 2. 调试步骤

```
步骤 1: 环境检查 (pre_check.sh)
    │
    ▼
步骤 2: 性能基线测试 (baseline_test.sh)
    │
    ▼
步骤 3: 对比目标规格
    │
    ├─ 达标 → 进入步骤 4
    └─ 不达标 → 性能调优
    │
    ▼
步骤 4: 功能验证
    │   - 读写功能
    │   - 电源管理
    │   - 错误处理
    │
    ▼
步骤 5: 压力测试
    │   - 72 小时老化
    │   - 温度循环
    │
    ▼
步骤 6: 问题记录与报告
```

### 3. 问题记录表

```markdown
# 客户端调试问题记录

**调试日期**: 2026-04-XX  
**调试地点**: [客户现场]  
**参与人员**: [雪原、客户工程师]

## 问题清单

### 问题 001: [简述问题]
- **发现时间**: HH:MM
- **现象描述**: ...
- **复现步骤**: 
  1. ...
  2. ...
- **影响范围**: ...
- **优先级**: 高/中/低
- **根本原因**: ...
- **解决方案**: ...
- **验证结果**: ✅ 已解决 / ⏳ 待验证
- **责任人**: ...
- **状态**: Open / In Progress / Resolved / Closed

### 问题 002: ...

## 调试总结

**测试通过率**: XX%  
**发现问题数**: X 个  
**已解决问题数**: X 个  
**遗留问题数**: X 个  

**结论**: 
- [ ] 可以进入下一阶段
- [ ] 需要整改后重新调试
- [ ] 需要设计变更

**下一步行动**:
1. ...
2. ...
```

---

## 📞 客户沟通要点

### 1. 技术对齐

- [ ] UFS 3.1 规格确认
- [ ] 性能目标对齐
- [ ] 接口定义 (pinout, 电压)
- [ ] 机械尺寸 (封装)
- [ ] 工作温度范围

### 2. 测试对齐

- [ ] 测试方法对齐
- [ ] 测试工具一致性
- [ ] 判定标准对齐
- [ ] 测试报告格式

### 3. 项目计划

- [ ] 样品交付时间 (4/30)
- [ ] 客户验证周期
- [ ] 问题反馈机制
- [ ] 量产时间表

---

## 📦 交付物清单

### 给客户

| 物品 | 格式 | 数量 |
|------|------|------|
| UFS 3.1 工程样品 | 硬件 | 5 颗 |
| 产品规格书 | PDF | 1 份 |
| 性能测试报告 | PDF | 1 份 |
| 接口定义文档 | PDF | 1 份 |
| 驱动/固件 | 二进制 | 1 套 |
| 测试工具 | 源码 | 1 套 |

### 内部留存

| 物品 | 格式 | 数量 |
|------|------|------|
| 调试日志 | Markdown | 1 份 |
| 问题记录表 | Markdown | 1 份 |
| 测试原始数据 | JSON/CSV | 1 套 |
| 照片/视频 | JPG/MP4 | 若干 |

---

## ⚠️ 注意事项

### 1. 静电防护

- 佩戴防静电手环
- 使用防静电垫
- 避免直接触摸芯片引脚

### 2. 温度监控

- 实时监控 UFS 表面温度
- 高温 (>85°C) 时暂停测试
- 记录温度 - 性能曲线

### 3. 数据备份

- 测试前备份重要数据
- 测试后及时导出结果
- 云端 + 本地双重备份

### 4. 问题升级

| 问题级别 | 响应时间 | 升级路径 |
|----------|----------|----------|
| **P0** (阻塞) | 立即 | 雪原 → 技术负责人 |
| **P1** (严重) | 2 小时 | 雪原 |
| **P2** (一般) | 24 小时 | 记录待处理 |
| **P3** (轻微) | 本周内 | 记录待处理 |

---

## 📖 参考资料

1. **UFS_KNOWLEDGE_SUMMARY.md** - UFS 产品知识体系
2. **UFS_3.1_FT_测试规范.md** - 生产测试流程
3. **SysTest README** - 测试框架使用说明
4. **客户技术规格书** - 客户具体要求

---

**学习时间**: 2026-03-26 07:00-07:30  
**下一阶段**: 供应商产品线调研 (07:30-08:00)
