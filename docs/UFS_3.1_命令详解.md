# UFS 3.1 命令详解（JESD220E 第 7/8 章）

**学习时间**: 2026-03-13 Day 1  
**章节**: 第 7 章（协议层）、第 8 章（应用层）  
**状态**: 学习笔记

---

## 📋 命令分类总览

UFS 支持 4 大类命令：

```
┌─────────────────────────────────────────────────────────┐
│                    UFS 命令体系                          │
├─────────────────────────────────────────────────────────┤
│  1. SCSI 命令      → 数据读写操作（READ/WRITE 等）       │
│  2. UFS 命令       → 设备控制（QUERY/NOP 等）            │
│  3. 任务管理命令   → 任务控制（ABORT/RESET 等）          │
│  4. 厂商命令       → 厂商特定功能                        │
└─────────────────────────────────────────────────────────┘
```

---

## 1️⃣ SCSI 命令（数据读写）

### 1.1 READ_10（0x28）- 10 字节读命令

**命令格式**（10 字节）：
```
Byte 0: Operation Code (0x28)
Byte 1: RDPROTECT | DPO | FUA | Reserved | LUN
Byte 2-5: Logical Block Address (32-bit)
Byte 6: Reserved
Byte 7-8: Transfer Length (16-bit)
Byte 9: Control
```

**字段详解**：
| 字段 | 位宽 | 说明 |
|------|------|------|
| RDPROTECT | 3 bits | 读取保护类型（0-7） |
| DPO | 1 bit | Disable Page Out（禁用页面换出） |
| FUA | 1 bit | Force Unit Access（强制单元访问） |
| LUN | 5 bits | 逻辑单元号（0-31） |
| LBA | 32 bits | 逻辑块地址 |
| Transfer Length | 16 bits | 传输块数（最大 65535） |

**使用示例**：
```
读取 LUN 0，LBA=0x1000，长度=256 块

命令：28 00 00 00 10 00 00 01 00 00
解析：
  28       = READ_10
  00       = RDPROTECT=0, DPO=0, FUA=0, LUN=0
  00 00 10 00 = LBA=0x1000
  00       = Reserved
  01 00    = Transfer Length=256 (0x0100)
  00       = Control
```

**测试设计**：
- [ ] 单块读取（Transfer Length=1）
- [ ] 多块读取（Transfer Length=256/1024）
- [ ] 最大 LBA 读取测试
- [ ] 跨 LUN 读取测试
- [ ] FUA=1 强制读取测试

---

### 1.2 WRITE_10（0x2A）- 10 字节写命令

**命令格式**（10 字节）：
```
Byte 0: Operation Code (0x2A)
Byte 1: WRPROTECT | DPO | FUA | Reserved | LUN
Byte 2-5: Logical Block Address (32-bit)
Byte 6: Reserved
Byte 7-8: Transfer Length (16-bit)
Byte 9: Control
```

**字段详解**：
| 字段 | 位宽 | 说明 |
|------|------|------|
| WRPROTECT | 3 bits | 写入保护类型（0-7） |
| DPO | 1 bit | Disable Page Out |
| FUA | 1 bit | Force Unit Access |
| LUN | 5 bits | 逻辑单元号 |
| LBA | 32 bits | 逻辑块地址 |
| Transfer Length | 16 bits | 传输块数 |

**测试设计**：
- [ ] 单块写入测试
- [ ] 多块连续写入
- [ ] 跨 LUN 写入测试
- [ ] WRPROTECT 保护测试
- [ ] FUA=1 强制写入测试

---

### 1.3 SYNCHRONIZE_CACHE_10（0x35）- 同步缓存

**用途**：强制将缓存数据写入非易失性介质

**命令格式**：
```
Byte 0: Operation Code (0x35)
Byte 1: Reserved | LUN
Byte 2-5: Logical Block Address (32-bit)
Byte 6: Reserved
Byte 7-8: Number of Blocks (16-bit)
Byte 9: Control
```

**使用场景**：
- 数据落盘保证
- 掉电保护测试
- 性能测试（flush 延迟）

**测试设计**：
- [ ] 写入后同步缓存测试
- [ ] 掉电前同步缓存测试
- [ ] 同步缓存延迟测量

---

## 2️⃣ UFS 命令（设备控制）

### 2.1 QUERY_REQUEST（0x01）- 查询请求

**用途**：读写设备描述符、属性、标志位

**命令格式**（UPIU 格式）：
```
Header:
  Transaction Code: 0x01 (QUERY_REQUEST)
  Flags: Opcode 选择
  Data Segment Length: 可变

Payload:
  Opcode (1 byte)
  IDN (1 byte)
  Index (1 byte)
  Selector (2 bytes)
  Reserved (3 bytes)
  Data (可变)
```

**Opcode 类型**：
| Opcode | 名称 | 功能 |
|--------|------|------|
| 0x01 | Read Descriptor | 读取描述符 |
| 0x02 | Write Descriptor | 写入描述符 |
| 0x03 | Read Attribute | 读取属性 |
| 0x04 | Write Attribute | 写入属性 |
| 0x05 | Read Flag | 读取标志位 |
| 0x06 | Write Flag | 写入标志位 |
| 0x17 | Read Descriptor (Long) | 长描述符读取 |

**IDN 类型**（Identifier）：
| IDN | 类型 | 说明 |
|-----|------|------|
| 0x00 | Device Descriptor | 设备描述符 |
| 0x01 | Configuration Descriptor | 配置描述符 |
| 0x02 | Unit Descriptor | LUN 描述符 |
| 0x03 | RFU | 保留 |
| 0x04 | Interconnect Descriptor | 互连描述符 |
| 0x05 | String Descriptor | 字符串描述符 |
| 0x06 | RFU | 保留 |
| 0x07 | Health Descriptor | 健康描述符 |

**测试设计**：
- [ ] 读取设备描述符
- [ ] 读取 LUN 描述符
- [ ] 读取健康描述符
- [ ] 读写属性测试
- [ ] 读写标志位测试

---

### 2.2 NOP_OUT（0x08）/ NOP_IN（0x28）- 空操作

**用途**：
- 链路保活
- 超时测试
- 命令响应测试

**命令格式**：
```
NOP_OUT (Host → Device):
  Transaction Code: 0x08
  Data Segment Length: 0

NOP_IN (Device → Host):
  Transaction Code: 0x28
  Data Segment Length: 0
```

**测试设计**：
- [ ] NOP 命令往返延迟测试
- [ ] 超时保活测试
- [ ] 链路状态检测

---

## 3️⃣ 任务管理命令

### 3.1 任务管理功能列表

| 功能码 | 名称 | 功能 |
|--------|------|------|
| 0x01 | ABORT_TASK | 中止指定任务 |
| 0x02 | ABORT_TASK_SET | 中止任务集 |
| 0x04 | CLEAR_ACA | 清除自动队列仲裁 |
| 0x08 | CLEAR_TASK_SET | 清除任务集 |
| 0x10 | LUN RESET | LUN 复位 |
| 0x20 | QUERY TASK | 查询任务状态 |
| 0x40 | QUERY TASK SET | 查询任务集状态 |

### 3.2 LUN_RESET（0x10）- LUN 复位

**用途**：复位指定 LUN，中止所有未完成命令

**测试设计**：
- [ ] LUN 复位后状态检查
- [ ] 复位中中止命令验证
- [ ] 多 LUN 独立复位测试

---

## 📊 命令测试用例设计

### 基础读写测试

| 用例 ID | 测试项 | 命令 | 预期结果 |
|---------|--------|------|----------|
| CMD-001 | 单块读取 | READ_10 (LBA=0, Len=1) | 成功返回数据 |
| CMD-002 | 多块读取 | READ_10 (LBA=0, Len=256) | 成功返回数据 |
| CMD-003 | 单块写入 | WRITE_10 (LBA=0, Len=1) | 成功写入 |
| CMD-004 | 多块写入 | WRITE_10 (LBA=0, Len=256) | 成功写入 |
| CMD-005 | 写入后验证 | WRITE + READ | 数据一致 |
| CMD-006 | 跨 LUN 读写 | READ/WRITE (多 LUN) | 各 LUN 独立 |

### 查询命令测试

| 用例 ID | 测试项 | 命令 | 预期结果 |
|---------|--------|------|----------|
| CMD-101 | 读设备描述符 | QUERY (Opcode=0x01, IDN=0x00) | 返回设备信息 |
| CMD-102 | 读 LUN 描述符 | QUERY (Opcode=0x01, IDN=0x02) | 返回 LUN 信息 |
| CMD-103 | 读健康描述符 | QUERY (Opcode=0x01, IDN=0x07) | 返回健康信息 |
| CMD-104 | 读属性 | QUERY (Opcode=0x03) | 返回属性值 |
| CMD-105 | 写属性 | QUERY (Opcode=0x04) | 属性更新成功 |

### 电源管理测试

| 用例 ID | 测试项 | 命令 | 预期结果 |
|---------|--------|------|----------|
| CMD-201 | 进入 HIBERN8 | 电源模式切换 | 功耗降低 |
| CMD-202 | 唤醒测试 | 电源模式切换 | 唤醒时间<10ms |
| CMD-203 | 模式循环 | ACTIVE↔HIBERN8 | 功能正常 |

### 任务管理测试

| 用例 ID | 测试项 | 命令 | 预期结果 |
|---------|--------|------|----------|
| CMD-301 | 中止任务 | ABORT_TASK | 任务中止成功 |
| CMD-302 | LUN 复位 | LUN_RESET | LUN 复位成功 |
| CMD-303 | 查询任务 | QUERY_TASK | 返回任务状态 |

---

## 🔧 命令调试技巧

### 1. 使用 FIO 测试命令

```bash
# 顺序读取测试
fio --name=seq_read --rw=read --bs=128k --size=1G --numjobs=1

# 随机写入测试
fio --name=rand_write --rw=randwrite --bs=4k --size=1G --numjobs=4

# 延迟测试
fio --name=lat_test --rw=randread --bs=4k --size=1G --latency_percentile=99.99
```

### 2. 使用 sg3_utils 工具

```bash
# 读取设备信息
sg_inq /dev/sdX

# 读取 VPD 页
sg_vpd --page=0xb0 /dev/sdX

# 发送 SCSI 命令
sg_raw -s 512 /dev/sdX 28 00 00 00 00 00 00 00 01 00
```

### 3. 使用 UFS 工具

```bash
# 读取 UFS 描述符（需要 ufs-utils）
ufs-utils query -d /dev/ufs0 -o read_desc -i device

# 读取 UFS 属性
ufs-utils query -d /dev/ufs0 -o read_attr -a 0x0062
```

---

## 📝 学习总结

### 核心要点
1. **SCSI 命令**用于数据读写，最常用 READ_10/WRITE_10
2. **UFS 命令**用于设备控制，QUERY_REQUEST 最常用
3. **任务管理命令**用于异常处理，LUN_RESET 重要
4. **命令格式**遵循 UPIU 协议，Header+Payload 结构
5. **队列管理**支持 32 深度，乱序完成

### 测试应用
1. 基础读写测试验证数据通路
2. 查询命令测试验证设备状态读取
3. 电源管理测试验证功耗控制
4. 任务管理测试验证异常处理

### 待深入学习
1. UPIU 协议详细格式
2. 命令超时和重试机制
3. 错误处理和状态码
4. 多队列调度机制

---

**学习时间**: 2026-03-13 2.5 小时  
**下一章**: 第 9 章 电源管理（继续学习中）
