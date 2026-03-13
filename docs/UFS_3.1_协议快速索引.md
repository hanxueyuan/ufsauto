# UFS 3.1 协议快速索引（JESD220E）

**用途**: 快速查找 UFS 3.1 协议关键信息  
**对应标准**: JEDEC JESD220E  
**创建时间**: 2026-03-13

---

## 🔍 按主题索引

### 命令与操作

| 主题 | 章节 | 页码 | 说明 |
|------|------|------|------|
| SCSI 命令 | 8.2 | TBD | READ_10, WRITE_10, SYNCHRONIZE_CACHE |
| 查询命令 | 8.3 | TBD | QUERY_REQUEST, 读写描述符/属性/标志位 |
| 任务管理 | 8.4 | TBD | ABORT_TASK, CLEAR_ACA, LUN RESET |
| UFS 命令 | 8.5 | TBD | NOP_OUT, NOP_IN |

### 电源管理

| 主题 | 章节 | 页码 | 说明 |
|------|------|------|------|
| 电源模式 | 9.2 | TBD | ACTIVE, IDLE, SLEEP, POWERDOWN, HIBERN8 |
| 模式转换 | 9.3 | TBD | 各模式间转换流程 |
| ICC 控制 | 9.4 | TBD | 自适应电流控制 |
| 唤醒时间 | 9.2.5 | TBD | 各模式唤醒时间要求 |

### 描述符与属性

| 主题 | 章节 | 页码 | 说明 |
|------|------|------|------|
| 设备描述符 | 8.5.1 | TBD | 设备基本信息 |
| 配置描述符 | 8.5.2 | TBD | 配置参数 |
| LUN 描述符 | 8.5.3 | TBD | 各 LUN 信息 |
| 健康描述符 | 8.5.7 | TBD | 寿命、预失效信息 |
| 属性列表 | 8.5.10 | TBD | 所有可读写属性 |

### 电气特性

| 主题 | 章节 | 页码 | 说明 |
|------|------|------|------|
| 电源要求 | 12.2 | TBD | VCC, VCCQ, VCCQ2 |
| 信号特性 | 12.3 | TBD | M-PHY 信号要求 |
| 时序要求 | 12.4 | TBD | 建立/保持时间 |

### 物理层

| 主题 | 章节 | 页码 | 说明 |
|------|------|------|------|
| M-PHY | 10.2 | TBD | Gear 1-4, 车道配置 |
| UniPro | 10.3 | TBD | 协议层规范 |
| 时钟 | 11.2 | TBD | 参考时钟频率 |

### 测试与验证

| 主题 | 章节 | 页码 | 说明 |
|------|------|------|------|
| 一致性测试 | 13.2 | TBD | 协议一致性 |
| 性能测试 | 13.3 | TBD | 读写性能、延迟 |
| 电气测试 | 13.4 | TBD | 信号质量、功耗 |

---

## 📋 常用命令速查

### 读命令
```
READ_10 (0x28)
  - LUN: bits[5:0] of LUN
  - LBA: 32-bit logical block address
  - Transfer Length: number of blocks
```

### 写命令
```
WRITE_10 (0x2A)
  - LUN: bits[5:0] of LUN
  - LBA: 32-bit logical block address
  - Transfer Length: number of blocks
```

### 查询命令
```
QUERY_REQUEST (0x01)
  - Opcode: Read/Write Descriptor/Attribute/Flag
  - IDN: Descriptor/Attribute/Flag ID
  - Index: LUN or selector
  - Selector: sub-selector
```

---

## 🔢 关键数值

| 参数 | 值 | 单位 |
|------|-----|------|
| 最大队列深度 | 32 | commands |
| 最大 LUN 数 | 8 | LUNs |
| 最大带宽 | 23.2 | Gbps (2 lanes, Gear 4) |
| VCC 范围 | 2.7-3.6 | V |
| VCCQ 范围 | 1.1-1.3 / 1.7-1.95 | V |
| 工作温度 | -40 ~ 85 | °C |
| 参考时钟 | 19.2/26/38.4/52 | MHz |

---

## 🏥 健康监控属性

| 属性 | 地址 | 大小 | 说明 |
|------|------|------|------|
| bDeviceLifeTimeEstA | 0x00E6h | 1 byte | LUN A 寿命估算 (1-10) |
| bDeviceLifeTimeEstB | 0x00E7h | 1 byte | LUN B 寿命估算 (1-10) |
| bPreEOLInfo | 0x00E8h | 1 byte | 预失效信息 (0x01=10%, 0x02=20%) |
| dVendorSpecificInfo | 0x00E9h | 4 bytes | 厂商特定信息 |

---

## ⚡ 电源模式功耗等级

| 模式 | 相对功耗 | 典型唤醒时间 |
|------|----------|--------------|
| ACTIVE | 100% | - |
| IDLE | ~30% | <10μs |
| SLEEP | ~10% | <50μs |
| POWERDOWN | ~5% | <1ms |
| HIBERN8 | ~1% | <10ms |

---

**使用说明**: 
- 此索引用于快速定位，详细规范请查阅 JESD220E 原文
- 页码待补充（根据实际 PDF 页码）
- 持续更新中...

**最后更新**: 2026-03-13
