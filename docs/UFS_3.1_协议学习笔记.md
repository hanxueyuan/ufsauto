# UFS 3.1 协议学习笔记（JESD220E）

**文档版本**: V1.0  
**创建时间**: 2026-03-13  
**原始文档**: JEDEC JESD220E - Universal Flash Storage (UFS) Version 3.1  
**发布日期**: 2020 年 1 月  
**替代版本**: JESD220D (2018 年 1 月)

---

## 📑 文档结构概览

```
JESD220E UFS 3.1 标准（共 528 页）
├── 第 1 章：概述（Scope）
├── 第 2 章：参考文档（References）
├── 第 3 章：定义与缩略语（Definitions and abbreviations）
├── 第 4 章：UFS 系统架构（UFS System Architecture）
├── 第 5 章：UFS 互操作规范（UFS Interoperability）
├── 第 6 章：UFS 主机控制器接口（UFS Host Controller Interface）
├── 第 7 章：UFS 协议层（UFS Protocol Layer）
├── 第 8 章：UFS 应用层（UFS Application Layer）
├── 第 9 章：电源管理（Power Management）
├── 第 10 章：物理层（Physical Layer）
├── 第 11 章：时钟与信号（Clock and Signals）
├── 第 12 章：电气特性（Electrical Characteristics）
├── 第 13 章：测试与测量（Test and Measurement）
└── 附录 A-N：补充信息
```

---

## 🔑 核心章节要点

### 第 4 章：UFS 系统架构

**4.1 UFS 系统组成**：
```
┌─────────────────────────────────────────────────────────┐
│                    UFS 系统架构                          │
├─────────────────────────────────────────────────────────┤
│  UFS Host ←→ UFS Interconnect ←→ UFS Device             │
│     ↓              ↓                    ↓               │
│  HCI 层        M-PHY 物理层          设备控制器          │
│     ↓              ↓                    ↓               │
│  应用层       UniPro 协议层          存储介质            │
└─────────────────────────────────────────────────────────┘
```

**4.2 关键组件**：
| 组件 | 功能 | 协议层 |
|------|------|--------|
| UFS Host | 发起命令和控制 | 应用层 |
| UFS Device | 响应命令、管理存储 | 应用层 |
| UFS Interconnect | 物理连接和数据传输 | 物理层/协议层 |
| HCI | 主机控制器接口 | 主机接口层 |

**4.3 LUN 架构**：
- UFS 设备可包含多个 LUN（Logical Unit Number）
- 每个 LUN 独立寻址和管理
- 支持 LUN 级电源管理

---

### 第 7 章：UFS 协议层

**7.1 命令类型**：
| 命令类型 | 功能 | 示例 |
|----------|------|------|
| SCSI Command | 数据读写 | READ_10, WRITE_10 |
| UFS Command | 设备控制 | QUERY_REQUEST, NOP_OUT |
| Task Management | 任务管理 | ABORT_TASK, CLEAR_ACA |

**7.2 传输协议**：
```
命令传输流程：
Host → CMD_UFS → Device
Host → DATA_OUT → Device（写数据）
Host ← DATA_IN ← Device（读数据）
Host ← RESP_UFS ← Device（响应）
```

**7.3 队列管理**：
- 支持多队列深度（最高 32）
- 命令标签（Tag）管理（0-31）
- 支持乱序完成（Out-of-Order Completion）

---

### 第 8 章：UFS 应用层

**8.1 查询命令（Query Request）**：
| 功能 | Opcode | 说明 |
|------|--------|------|
| Read Descriptor | 0x01 | 读取设备描述符 |
| Write Descriptor | 0x02 | 写入设备描述符 |
| Read Attribute | 0x03 | 读取属性 |
| Write Attribute | 0x04 | 写入属性 |
| Read Flag | 0x05 | 读取标志位 |
| Write Flag | 0x06 | 写入标志位 |

**8.2 设备描述符**：
```
设备描述符层次结构：
Device Descriptor（设备描述符）
├── Configuration Descriptor（配置描述符）
│   └── Unit Descriptor（LUN 描述符）
├── Geometry Descriptor（几何描述符）
├── Health Descriptor（健康描述符）
└── String Descriptor（字符串描述符）
```

**8.3 关键属性**：
| 属性 | 地址 | 功能 |
|------|------|------|
| bBootLunEn | 0x00D5h | 启动 LUN 使能 |
| bActiveICCLevel | 0x0062h | ICC 电流级别 |
| dSegmentSize | 0x00E4h | 数据段大小 |
| bRefClkFreq | 0x00B6h | 参考时钟频率 |

---

### 第 9 章：电源管理 ⭐ 重点

**9.1 电源模式**：
| 模式 | 功耗 | 唤醒时间 | 说明 |
|------|------|----------|------|
| ACTIVE | 高 | - | 正常工作模式 |
| IDLE | 中 | <10μs | 空闲等待 |
| SLEEP | 低 | <50μs | 睡眠模式 |
| POWERDOWN | 极低 | <1ms | 掉电模式 |
| HIBERN8 | 最低 | <10ms | 休眠模式 |

**9.2 电源状态转换**：
```
ACTIVE ←→ IDLE ←→ SLEEP ←→ POWERDOWN
   ↓         ↓         ↓         ↓
HIBERN8 ←→ HIBERN8 ←→ HIBERN8 ←→ HIBERN8
```

**9.3 自适应电流控制（ICC）**：
- 根据负载动态调整电流
- 减少功耗和发热
- 支持多个 ICC 级别

---

### 第 10 章：物理层

**10.1 M-PHY 特性**：
| 特性 | 规格 |
|------|------|
| 版本 | M-PHY v4.0 |
| 车道数 | 1 或 2 车道 |
| 速率档位 | Gear 1-4 |
| 最大速率 | 11.6 Gbps/lane（Gear 4, 2 lanes） |

**10.2 UniPro 协议**：
- 网络层：L2 链路控制
- 传输层：L3 数据包传输
- 支持流量控制和错误恢复

---

## 🔧 测试相关章节

### 第 13 章：测试与测量

**13.1 一致性测试**：
- 电气特性测试
- 协议一致性测试
- 互操作性测试

**13.2 性能测试**：
| 测试项 | 方法 | 标准 |
|--------|------|------|
| 顺序读取 | 128KB 块，QD1-32 | ≥标称值 90% |
| 顺序写入 | 128KB 块，QD1-32 | ≥标称值 90% |
| 随机读取 | 4KB 块，QD1-32 | IOPS≥标称值 90% |
| 随机写入 | 4KB 块，QD1-32 | IOPS≥标称值 90% |
| 延迟 | 4KB 随机 | 符合 QoS 要求 |

---

## 📊 关键参数速查表

### 电气参数
| 参数 | 值 | 说明 |
|------|-----|------|
| VCC | 2.7-3.6V | 主电源 |
| VCCQ | 1.1-1.3V / 1.7-1.95V | I/O 电源 |
| VCCQ2 | 1.1-1.3V / 1.7-1.95V | 辅助 I/O 电源 |
| 工作温度 | -40°C ~ 85°C | 工业级 |

### 性能参数
| 参数 | UFS 3.1 规格 |
|------|-------------|
| 最大带宽 | 23.2 Gbps（2 lanes, Gear 4） |
| 最大队列深度 | 32 |
| 最大 LUN 数 | 8 |
| 参考时钟 | 19.2 / 26 / 38.4 / 52 MHz |

### 健康监控
| 属性 | 说明 |
|------|------|
| Pre-EOL Information | 寿命预警（10%/20% 剩余） |
| Device Life Time Estimation | 设备寿命估算（0-10 级） |
| Vendor Specific Info | 厂商特定健康信息 |

---

## 🎯 测试设计参考

### 基于协议的测试点

**1. 命令测试**：
- [ ] SCSI 读写命令（READ_10/WRITE_10）
- [ ] 查询命令（QUERY_REQUEST）
- [ ] 任务管理命令（ABORT_TASK）
- [ ] NOP 命令（NOP_OUT/NOP_IN）

**2. 电源管理测试**：
- [ ] ACTIVE→IDLE→SLEEP 转换
- [ ] HIBERN8 进入/退出
- [ ] 功耗测量（各模式）
- [ ] 唤醒时间测试

**3. LUN 测试**：
- [ ] 多 LUN 并发访问
- [ ] LUN 独立电源管理
- [ ] LUN 健康状态读取

**4. 健康监控测试**：
- [ ] 读取健康描述符
- [ ] 寿命估算验证
- [ ] 预失效预警测试

**5. 性能测试**：
- [ ] 不同队列深度性能（QD1-32）
- [ ] 混合负载性能（70% 读+30% 写）
- [ ] 延迟分布（P99/P99.99）

---

## 📚 学习建议

### 第 1 周：架构理解
- [ ] 阅读第 4 章（系统架构）
- [ ] 理解 UFS Host/Device/Interconnect 关系
- [ ] 掌握 LUN 概念

### 第 2 周：协议层
- [ ] 阅读第 7 章（协议层）
- [ ] 学习命令格式和传输流程
- [ ] 理解队列管理机制

### 第 3 周：应用层
- [ ] 阅读第 8 章（应用层）
- [ ] 掌握查询命令使用
- [ ] 学习描述符结构

### 第 4 周：电源管理
- [ ] 精读第 9 章（电源管理）⭐
- [ ] 理解各电源模式转换
- [ ] 设计电源管理测试用例

---

## 🔗 相关资源

- **官方文档**: JEDEC JESD220E（本文件）
- **UFS 3.0**: JESD220C
- **UFS 4.0**: JESD220F（2022 年发布）
- **HCI 标准**: JESD223C（UFSHCI）

---

**备注**: 本文档为学习笔记，详细内容请参考 JEDEC 官方标准原文。

**最后更新**: 2026-03-13
