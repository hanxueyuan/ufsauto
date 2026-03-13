# UFS 3.1 描述符详解（JESD220E 第 8 章）

**学习时间**: 2026-03-13 Day 1 继续  
**章节**: 第 8 章 应用层 - 描述符  
**状态**: 学习笔记

---

## 📋 描述符层次结构

```
Device Descriptor（设备描述符）
├── Configuration Descriptor（配置描述符）
│   └── Unit Descriptor（LUN 描述符）
├── Geometry Descriptor（几何描述符）
├── Health Descriptor（健康描述符）
└── String Descriptor（字符串描述符）
```

---

## 1️⃣ Device Descriptor（设备描述符）

**用途**：描述 UFS 设备基本信息

**结构**（48 字节）：
```
Offset  Size  Field                  Description
------  ----  -----                  -----------
0x00    1     bLength                描述符长度
0x01    1     bDescriptorType        描述符类型（0x01）
0x02    1     bDevice                UFS 版本
0x03    1     bManufacturerID        厂商 ID
0x04    1     bNumLUs                LUN 数量
0x05    1     bNumWLU                写增强 LUN 数量
0x06    1     bBootEnable            启动使能
0x07    1     bDescrAccessEn         描述符访问使能
0x08    1     bInitPowerMode         初始电源模式
0x09    1     bHighPriorityLUSupport 高优先级 LUN 支持
0x0A    1     bSecureRemovalSupport  安全移除支持
0x0B    1     bSecurityLU            安全 LUN
0x0C    1     bBGOperationSupport    后台操作支持
0x0D    1     bSupportedMode         支持模式
0x0E    1     bMaxPowerMode          最大电源模式
0x0F    4     dVersion               版本号
0x13    4     dNumSecureEraseUnits   安全擦除单元数
0x17    4     dSecureEraseTimeout    安全擦除超时
0x1B    4     dSecureEraseUnitSize   安全擦除单元大小
0x1F    4     dMaxDataSizePerLUN     每 LUN 最大数据大小
0x23    4     dRefClkFreq            参考时钟频率
0x27    2     wManufacturerID        厂商 ID（扩展）
0x29    1     bUFSDeviceType         UFS 设备类型
```

**读取命令**：
```
QUERY_REQUEST (Opcode=0x01, IDN=0x00, Index=0x00)
```

**测试设计**：
- [ ] 读取设备描述符
- [ ] 验证 LUN 数量
- [ ] 验证 UFS 版本
- [ ] 验证厂商 ID

---

## 2️⃣ Configuration Descriptor（配置描述符）

**用途**：描述设备配置信息

**结构**：
```
Offset  Size  Field              Description
------  ----  -----              -----------
0x00    1     bLength            描述符长度
0x01    1     bDescriptorType    描述符类型（0x02）
0x02    1     bConfFlags         配置标志
0x03    1     bNumberConfigUnits 配置单元数量
```

**读取命令**：
```
QUERY_REQUEST (Opcode=0x01, IDN=0x01, Index=0x00)
```

---

## 3️⃣ Unit Descriptor（LUN 描述符）

**用途**：描述每个 LUN 的详细信息

**结构**（32 字节）：
```
Offset  Size  Field                  Description
------  ----  -----                  -----------
0x00    1     bLength                描述符长度
0x01    1     bDescriptorType        描述符类型（0x03）
0x02    1     bLUNFlags              LUN 标志
0x03    1     bLUEnable              LUN 使能
0x04    1     bBootLUNID             启动 LUN ID
0x05    1     bLUWriteProtect        LUN 写保护
0x06    8     bLogicalBlockSize      逻辑块大小
0x0E    8     bProvisionedSize       配置大小
0x16    8     bDataTagUnitSize       数据标签单元大小
0x1E    1     bDataTagSupport        数据标签支持
0x1F    1     bLUHybridInterface     LUN 混合接口
```

**读取命令**：
```
QUERY_REQUEST (Opcode=0x01, IDN=0x02, Index=LUN 编号)
```

**测试设计**：
- [ ] 读取所有 LUN 描述符
- [ ] 验证 LUN 容量
- [ ] 验证逻辑块大小
- [ ] 验证写保护状态

---

## 4️⃣ Geometry Descriptor（几何描述符）

**用途**：描述存储介质几何结构

**结构**：
```
Offset  Size  Field              Description
------  ----  -----              -----------
0x00    1     bLength            描述符长度
0x01    1     bDescriptorType    描述符类型（0x04）
0x02    1     bMediaTechnology   介质技术类型
0x03    8     bTotalRawCapacity  总原始容量
0x0B    8     bRawCapacityPerLUN 每 LUN 原始容量
```

**读取命令**：
```
QUERY_REQUEST (Opcode=0x01, IDN=0x04, Index=0x00)
```

---

## 5️⃣ Health Descriptor（健康描述符）⭐ 重点

**用途**：描述设备健康状态和寿命信息

**结构**（20 字节）：
```
Offset  Size  Field                      Description
------  ----  -----                      -----------
0x00    1     bLength                    描述符长度
0x01    1     bDescriptorType            描述符类型（0x07）
0x02    1     bPreEOLInfo                预失效信息
0x03    1     bDeviceLifeTimeEstA        设备寿命估算 A
0x04    1     bDeviceLifeTimeEstB        设备寿命估算 B
0x05    4     dVendorSpecificInfo        厂商特定信息
0x09    2     wVendorSpecificInfo        厂商特定信息
0x0B    4     dDeviceLifeTimeEstA        设备寿命估算 A（扩展）
0x0F    4     dDeviceLifeTimeEstB        设备寿命估算 B（扩展）
```

**关键字段详解**：

### bPreEOLInfo（预失效信息）
| 值 | 含义 |
|----|------|
| 0x00 | 未定义 |
| 0x01 | 剩余寿命<10% |
| 0x02 | 剩余寿命<20% |
| 0xFF | 厂商特定 |

### bDeviceLifeTimeEstA/B（设备寿命估算）
| 值 | 含义 |
|----|------|
| 0x00 | 未定义 |
| 0x01 | 0-10% 寿命已用 |
| 0x02 | 10-20% 寿命已用 |
| ... | ... |
| 0x0A | 90-100% 寿命已用 |
| 0x0B | 100% 寿命已用（超期） |
| 0xFF | 厂商特定 |

**读取命令**：
```
QUERY_REQUEST (Opcode=0x01, IDN=0x07, Index=0x00)
```

**测试设计**：
- [ ] 读取健康描述符
- [ ] 验证寿命估算值
- [ ] 验证预失效信息
- [ ] 模拟寿命耗尽测试（需要特殊工具）

---

## 6️⃣ String Descriptor（字符串描述符）

**用途**：描述厂商名称、产品型号等字符串信息

**结构**：
```
Offset  Size  Field              Description
------  ----  -----              -----------
0x00    1     bLength            描述符长度
0x01    1     bDescriptorType    描述符类型（0x05）
0x02    N     bString            Unicode 字符串
```

**类型**：
| IDN | 字符串类型 |
|-----|------------|
| 0x00 | 制造商名称 |
| 0x01 | 产品名称 |
| 0x02 | 序列号 |
| 0x03 | OEM 信息 |

**读取命令**：
```
QUERY_REQUEST (Opcode=0x01, IDN=0x05, Index=字符串 ID)
```

---

## 📊 描述符测试用例设计

### 基础读取测试

| 用例 ID | 测试项 | 命令 | 预期结果 |
|---------|--------|------|----------|
| DESC-001 | 读设备描述符 | QUERY (IDN=0x00) | 返回 48 字节 |
| DESC-002 | 读配置描述符 | QUERY (IDN=0x01) | 返回配置信息 |
| DESC-003 | 读 LUN 描述符 0 | QUERY (IDN=0x02, Index=0) | 返回 LUN0 信息 |
| DESC-004 | 读几何描述符 | QUERY (IDN=0x04) | 返回容量信息 |
| DESC-005 | 读健康描述符 | QUERY (IDN=0x07) | 返回健康信息 |
| DESC-006 | 读制造商名称 | QUERY (IDN=0x05, Index=0) | 返回 Unicode 字符串 |
| DESC-007 | 读产品名称 | QUERY (IDN=0x05, Index=1) | 返回 Unicode 字符串 |
| DESC-008 | 读序列号 | QUERY (IDN=0x05, Index=2) | 返回 Unicode 字符串 |

### 健康监控测试

| 用例 ID | 测试项 | 测试方法 | 验收标准 |
|---------|--------|----------|----------|
| DESC-101 | 寿命读取 | 读取健康描述符 | 值在 0x01-0x0A |
| DESC-102 | 预失效信息 | 读取 bPreEOLInfo | 值在正常范围 |
| DESC-103 | 厂商信息 | 读取厂商特定字段 | 数据有效 |
| DESC-104 | 寿命监控 | 定期读取并记录 | 数据稳定 |

### 异常测试

| 用例 ID | 测试项 | 测试方法 | 预期结果 |
|---------|--------|----------|----------|
| DESC-201 | 无效 IDN | 读取未定义 IDN | 返回错误 |
| DESC-202 | 无效 Index | 读取不存在的 LUN | 返回错误 |
| DESC-203 | 写只读描述符 | 尝试写入设备描述符 | 返回错误 |

---

## 🔧 描述符调试技巧

### 1. 使用 ufs-utils 工具

```bash
# 读取设备描述符
ufs-utils query -d /dev/ufs0 -o read_desc -i device

# 读取 LUN 描述符
ufs-utils query -d /dev/ufs0 -o read_desc -i unit -l 0

# 读取健康描述符
ufs-utils query -d /dev/ufs0 -o read_desc -i health

# 读取字符串描述符
ufs-utils query -d /dev/ufs0 -o read_desc -i string -s 0
```

### 2. 使用 sg3_utils

```bash
# 读取 VPD 页（包含描述符信息）
sg_vpd --page=0xb0 /dev/sdX

# 读取设备信息
sg_inq /dev/sdX
```

### 3. 解析健康描述符脚本

```python
#!/usr/bin/env python3
# 解析健康描述符

import struct

def parse_health_descriptor(data):
    bPreEOLInfo = data[0x02]
    bLifeTimeEstA = data[0x03]
    bLifeTimeEstB = data[0x04]
    
    print(f"预失效信息：0x{bPreEOLInfo:02X}")
    if bPreEOLInfo == 0x01:
        print("  警告：剩余寿命<10%")
    elif bPreEOLInfo == 0x02:
        print("  警告：剩余寿命<20%")
    
    print(f"LUN A 寿命估算：0x{bLifeTimeEstA:02X}")
    if bLifeTimeEstA <= 0x0A:
        print(f"  已用寿命：{(bLifeTimeEstA-1)*10}-{bLifeTimeEstA*10}%")
    
    print(f"LUN B 寿命估算：0x{bLifeTimeEstB:02X}")
    if bLifeTimeEstB <= 0x0A:
        print(f"  已用寿命：{(bLifeTimeEstB-1)*10}-{bLifeTimeEstB*10}%")

# 使用示例
data = bytes.fromhex("14 07 00 03 03 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00")
parse_health_descriptor(data)
```

---

## 📝 学习总结

### 核心要点
1. **描述符层次**：设备→配置→LUN→几何→健康→字符串
2. **设备描述符**：48 字节，包含基本信息
3. **LUN 描述符**：每个 LUN 独立描述符
4. **健康描述符**：寿命估算和预失效信息（重点）
5. **读取方式**：QUERY_REQUEST (Opcode=0x01, IDN=类型)

### 测试应用
1. 基础读取测试验证描述符可读
2. 健康监控测试验证寿命读取
3. 异常测试验证错误处理
4. 定期监控验证数据稳定性

### 待深入学习
1. 描述符写入流程（如支持）
2. 描述符更新机制
3. 厂商特定描述符
4. 描述符与属性关系

---

**学习时间**: 2026-03-13 又 1.5 小时  
**累计学习**: 6 小时  
**下一步**: 创建综合测试用例文档（继续工作中）
