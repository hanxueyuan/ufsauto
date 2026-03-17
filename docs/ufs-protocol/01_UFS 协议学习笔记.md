# UFS 协议学习笔记 - 启动报告

**日期**: 2026-03-18  
**阶段**: 第 1 周 - UFS 协议基础  
**学习目标**: 掌握 UFS 3.1 协议架构和基础概念

---

## 📚 现有资料整理

### 1. UFS 3.1 协议学习笔记.md
**内容概要**：
- UFS 发展历史（UFS 1.0 → 2.0 → 2.1 → 3.0 → 3.1）
- UFS 架构（应用层、网络层、链路层、物理层）
- UFS 与 PCIe/NVMe 对比

**关键知识点**：
```
UFS 3.1 主要特性:
- 速率：11.6 Gbps/lane (HS-G4)
- 车道数：2 lane (读 + 写分离)
- 理论带宽：~23.2 Gbps ≈ 2.9 GB/s
- 功耗：优于 UFS 3.0
```

---

### 2. UFS 3.1_命令详解.md
**内容概要**：
- SCSI 命令集（读/写/查询）
- UFS 特定命令（Device Management）
- 命令队列（Tag 机制）

**关键命令**：
```
读命令：
- SCSI Read(10), Read(16)
- 支持 LBA 寻址
- 支持多队列

写命令:
- SCSI Write(10), Write(16)
- 支持 FUA (Force Unit Access)
- 支持写入缓存控制

管理命令:
- Query Request (读取描述符/属性)
- NOP Request (链路检测)
```

---

### 3. UFS 3.1_描述符详解.md
**内容概要**：
- 设备描述符（Device Descriptor）
- 配置描述符（Configuration Descriptor）
- 单元描述符（Unit Descriptor）
- 几何描述符（Geometry Descriptor）
- 电源描述符（Power Descriptor）

**关键参数**：
```
设备描述符:
- bDeviceType: 设备类型
- bDeviceClass: 设备类
- bDeviceSubClass: 设备子类
- bProtocol: 协议版本

几何描述符:
- dNumAllocUnits: 分配单元数
- bAllocationUnitSize: 分配单元大小
- bMinAddrAlignSize: 最小对齐大小
```

---

### 4. UFS 3.1_电源管理详解.md
**内容概要**：
- 5 种电源模式
- 电源状态转换
- 低功耗机制

**电源模式**：
```
Mode 0: Active (全速运行)
Mode 1: Idle (空闲，时钟停止)
Mode 2: Sleep (睡眠，部分电路关闭)
Mode 3: Power-Down (掉电，保留配置)
Mode 4: Deep-Stall (深度休眠)
```

---

### 5. UFS 3.1_物理层与电气特性.md
**内容概要**：
- MIPI M-PHY 物理层
- 差分信号传输
- 电气特性要求

**关键参数**：
```
M-PHY 特性:
- 差分电压：200-600mV
- 阻抗：100Ω ±15%
- 速率档位：HS-G1 ~ HS-G4
```

---

## 🎯 今日学习重点

### 1. UFS 协议栈架构
```
┌─────────────────────────────────┐
│     Application Layer (UIC)     │  SCSI 命令、UFS 命令
├─────────────────────────────────┤
│      Network Layer (ULP)        │  数据打包、流控制
├─────────────────────────────────┤
│       Link Layer (ULP)          │  链路管理、错误恢复
├─────────────────────────────────┤
│    Physical Layer (M-PHY)       │  信号传输、时钟恢复
└─────────────────────────────────┘
```

### 2. UFS 3.1 关键特性
- ✅ HS-G4 速率（11.6 Gbps/lane）
- ✅ 双车道设计（读 + 写分离）
- ✅ Write Booster（SLC 缓存加速）
- ✅ HPB（Host Performance Booster）
- ✅ 深度睡眠模式

### 3. 与 NVMe 对比
| 特性 | UFS 3.1 | NVMe 1.4 |
|------|---------|----------|
| 接口 | MIPI M-PHY | PCIe |
| 速率 | 2.9 GB/s | 3.9 GB/s (PCIe 3.0 x4) |
| 功耗 | 低 | 中 |
| 封装 | BGA | M.2/U.2 |
| 应用 | 移动/嵌入式 | 服务器/PC |

---

## 📝 待深入学习

- [ ] UFS 链路层状态机
- [ ] UFS 流量控制机制
- [ ] UFS 错误恢复流程
- [ ] UFS 与 SCSI 命令映射关系
- [ ] UFS 描述符详细结构

---

## 📅 明日计划

1. 深入学习 UFS 命令集
2. 整理 SCSI 命令与 UFS 命令映射
3. 学习 Query 命令和描述符读取

---

**学习进度**: 第 1 天 / 第 1 周  
**完成度**: 10%
