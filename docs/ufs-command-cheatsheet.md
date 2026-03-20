# UFS 命令集速查表

**版本**: UFS 3.1  
**更新时间**: 2026-03-20 23:00  
**学习阶段**: 夜间学习 Phase 1

---

## 📋 命令分类总览

### 1. SCSI 读/写命令（最常用）

| 命令 | 操作码 | 长度 | 用途 | 典型场景 |
|------|--------|------|------|----------|
| **READ(10)** | 0x28 | 10 字节 | 读取逻辑块 | 小数据量读取 |
| **READ(16)** | 0x88 | 16 字节 | 读取逻辑块 | 大数据量/64 位 LBA |
| **WRITE(10)** | 0x2A | 10 字节 | 写入逻辑块 | 小数据量写入 |
| **WRITE(16)** | 0x8A | 16 字节 | 写入逻辑块 | 大数据量/64 位 LBA |
| **WRITE_SAME(10)** | 0x41 | 10 字节 | 重复写入相同数据 | 快速擦除/初始化 |
| **WRITE_SAME(16)** | 0x93 | 16 字节 | 重复写入相同数据 | 快速擦除/初始化 |
| **SYNCHRONIZE_CACHE(10)** | 0x35 | 10 字节 | 刷新缓存到介质 | 数据持久化 |
| **SYNCHRONIZE_CACHE(16)** | 0x91 | 16 字节 | 刷新缓存到介质 | 数据持久化 |

### 2. Query Request 命令（UFS 特有）

| 命令 | Opcode | 用途 | 访问描述符 |
|------|--------|------|------------|
| **QUERY_REQUEST** | 0x01 | 读/写/擦除描述符 | Device, Geometry, Unit, Interconnect |

### 3. Task Management 命令

| 命令 | 功能 | 使用场景 |
|------|------|----------|
| **ABORT_TASK** | 中止指定任务 | 超时任务清理 |
| **ABORT_TASK_SET** | 中止任务集 | LU 重置前清理 |
| **CLEAR_ACA** | 清除自动队列仲裁 | 错误恢复 |
| **CLEAR_TASK_SET** | 清除任务集 | LU 重置 |
| **LOGICAL_UNIT_RESET** | LU 复位 | 错误恢复 |
| **TARGET_RESET** | Target 复位 | 严重错误恢复 |
| **QUERY_TASK** | 查询任务状态 | 任务监控 |
| **QUERY_TASK_SET** | 查询任务集 | 任务集监控 |
| **I_T_NEXUS_LOSS** | I-T Nexus 丢失 | 连接异常处理 |
| **MANAGE_WLUN** | 管理 WLUN | 特殊 LU 管理 |

### 4. NOP 命令

| 命令 | 用途 | 说明 |
|------|------|------|
| **NOP_OUT** | 主机→设备 | 链路保持、超时检测 |
| **NOP_IN** | 设备→主机 | 响应 NOP_OUT |

---

## 🔍 命令详解

### READ(10) 命令格式

```
Byte:  0    1    2    3    4    5    6    7    8    9
      +----+----+----+----+----+----+----+----+----+----+
      | 0x | 0x | LBA(31-24) | LBA(23-16) | LBA(15-8)  | LBA(7-0)   | 0x | Transfer Length (H) | Transfer Length (L) | Control |
      +----+----+----+----+----+----+----+----+----+----+
```

**字段说明**:
- **LBA**: 逻辑块地址（32 位，最大 2TB）
- **Transfer Length**: 传输长度（以逻辑块为单位）
- **Control**: 控制字段（通常为 0）

**示例**: 读取 LBA=0x1000, 长度=256 块
```python
cmd = [0x28, 0x00, 0x00, 0x00, 0x00, 0x10, 0x00, 0x00, 0x01, 0x00]
#        ^Opcode  ^     ^----LBA----^   ^--长度--^  ^控制^
```

### READ(16) 命令格式

```
Byte:  0    1    2    3    4    5    6    7    8    9   10   11   12   13   14   15
      +----+----+----+----+----+----+----+----+----+----+----+----+----+----+----+----+
      | 0x | 0x | LBA(63-56) | ... | LBA(7-0)   | Transfer Length (31-24)| ... | Control |
      +----+----+----+----+----+----+----+----+----+----+----+----+----+----+----+----+
```

**优势**: 支持 64 位 LBA，最大支持 8EB

### QUERY_REQUEST UPIU

**用途**: 访问 UFS 描述符和设备信息

```
Transaction Specific Fields:
- Opcode: 0x01
- Query Function: Read/Write/NoOp
- IDN: 描述符 ID
- Index: 索引
- Selector: 选择器
- Length: 数据长度
```

**常用 Query 操作**:
1. **Read Descriptor** - 读取设备信息
2. **Write Attribute** - 写入属性
3. **Read Flag** - 读取标志位

---

## 📊 命令使用频率统计

### 典型工作负载分布

| 命令类型 | 读取密集型 | 写入密集型 | 混合型 |
|----------|------------|------------|--------|
| READ(10/16) | 80% | 10% | 50% |
| WRITE(10/16) | 5% | 80% | 40% |
| WRITE_SAME | 1% | 5% | 2% |
| SYNC_CACHE | 1% | 1% | 1% |
| 其他 | 13% | 4% | 7% |

---

## 🛠️ 实践命令

### 使用 sg3-utils 测试

```bash
# 读取设备信息
sg_inq /dev/ufs0

# 读取容量
sg_readcap /dev/ufs0

# 直接发送 READ 命令
sg_read --length=4096 --lba=0 /dev/ufs0 > data.bin

# 直接发送 WRITE 命令
sg_write --length=4096 --lba=0 /dev/ufs0 < data.bin

# 刷新缓存
sg_sync /dev/ufs0
```

### 使用 ufs-utils 测试

```bash
# 读取 Device Descriptor
ufs-utils ufs read-desc /dev/ufs0 0

# 读取 Geometry Descriptor
ufs-utils ufs read-desc /dev/ufs0 1

# 读取 Unit Descriptor
ufs-utils ufs read-desc /dev/ufs0 2

# 读取设备属性
ufs-utils ufs read-attr /dev/ufs0 0x00D0

# 写入设备属性
ufs-utils ufs write-attr /dev/ufs0 0x00D0 0x01
```

---

## ⚠️ 注意事项

### 1. 命令对齐
- READ/WRITE 命令需要 512 字节对齐（或设备物理块大小）
- 未对齐会导致性能下降或错误

### 2. 队列深度
- UFS 支持多队列（典型 32-256）
- 高队列深度可提升并发性能

### 3. 超时设置
- 典型超时：30 秒
- 长时间操作（如擦除）需增加超时

### 4. 错误处理
- 检查 SCSI Sense Data
- 重试机制（典型 3 次）
- 记录错误日志

---

## 📖 参考文档

1. **JEDEC UFS 3.1 Spec** - JESD220D
2. **SCSI Primary Commands-4** - INCITS 532
3. **SCSI Block Commands-3** - INCITS 530
4. **Linux UFS Driver** - drivers/ufs/core/ufshcd.c

---

**学习时间**: 2026-03-20 23:30  
**阶段进度**: 1/9 完成  
**下一步**: UFS 描述符详解（23:30-00:00）
