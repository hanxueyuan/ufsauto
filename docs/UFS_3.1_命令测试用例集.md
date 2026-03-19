# UFS 3.1 命令测试用例集

**文档版本**: V1.0  
**创建时间**: 2026-03-19  
**参考标准**: JEDEC JESD220E - UFS 3.1  
**适用产品**: 群联 PS8363 + 长存 SQS 128GB UFS 3.1  
**用途**: 系统级命令一致性与功能验证

---

## 1. 概述

本文档基于 JESD220E 第 7 章（协议层）和第 8 章（应用层）的命令规范，设计完整的 UFS 命令测试用例集。覆盖 SCSI 数据命令、UFS 原生查询命令、任务管理命令三大类，同时包含边界条件和异常场景测试。

**测试工具**：
- `sg3_utils`（sg_raw / sg_inq / sg_vpd）
- `ufs-utils`（UFS 查询命令）
- `fio`（性能类读写）
- `dd`（基础块读写）
- 自研 SysTest 框架

**通用前置条件**：
- UFS 设备已枚举（/dev/sdX 或 /dev/bsgX 可见）
- 设备处于 ACTIVE 电源模式
- 无其他进程占用设备

---

## 2. SCSI 数据读写命令测试

### TC-CMD-001: READ_10 单块读取

| 项目 | 内容 |
|------|------|
| **用例 ID** | TC-CMD-001 |
| **测试目标** | 验证 READ_10 命令能正确读取单个逻辑块 |
| **前置条件** | 设备就绪，LBA 0 有合法数据 |
| **测试步骤** | 1. 构造 READ_10 CDB：`28 00 00 00 00 00 00 00 01 00`（LBA=0, Length=1）<br>2. 通过 sg_raw 发送命令<br>3. 接收返回数据（512B 或 4096B，取决于扇区大小） |
| **预期结果** | SCSI Status=GOOD (0x00)，返回 1 个逻辑块数据 |
| **Pass 标准** | 命令成功完成，返回数据长度等于逻辑块大小 |
| **Fail 标准** | 返回 CHECK CONDITION 或数据长度不匹配 |

### TC-CMD-002: READ_10 多块连续读取

| 项目 | 内容 |
|------|------|
| **用例 ID** | TC-CMD-002 |
| **测试目标** | 验证 READ_10 命令能正确读取连续多个逻辑块 |
| **前置条件** | 设备就绪 |
| **测试步骤** | 1. 构造 READ_10 CDB：LBA=0, Transfer Length=256<br>2. 发送命令<br>3. 验证返回数据长度 = 256 × 逻辑块大小 |
| **预期结果** | 成功返回 256 个逻辑块数据 |
| **Pass 标准** | 数据完整，无 SCSI 错误 |
| **Fail 标准** | 返回数据不完整或 SCSI 错误 |

### TC-CMD-003: READ_10 最大 Transfer Length

| 项目 | 内容 |
|------|------|
| **用例 ID** | TC-CMD-003 |
| **测试目标** | 验证 READ_10 最大传输长度（65535 块） |
| **前置条件** | 设备就绪，可用容量 ≥ 65535 块 |
| **测试步骤** | 1. 构造 READ_10 CDB：LBA=0, Transfer Length=65535 (0xFFFF)<br>2. 发送命令<br>3. 验证返回数据 |
| **预期结果** | 成功返回全部数据，或返回合理错误（如超过设备 Max Transfer Size） |
| **Pass 标准** | 成功完成或返回 ILLEGAL REQUEST（如超限） |
| **Fail 标准** | 设备挂死或返回非预期错误码 |

### TC-CMD-004: READ_10 FUA 强制读取

| 项目 | 内容 |
|------|------|
| **用例 ID** | TC-CMD-004 |
| **测试目标** | 验证 FUA=1 时绕过缓存直接从介质读取 |
| **前置条件** | 先写入已知数据到目标 LBA |
| **测试步骤** | 1. 写入数据到 LBA=0x1000<br>2. 发送 SYNCHRONIZE_CACHE<br>3. 构造 READ_10 CDB：FUA=1, LBA=0x1000, Length=1<br>4. 验证读回数据与写入一致 |
| **预期结果** | 数据一致，命令成功 |
| **Pass 标准** | FUA 读取数据与原始写入数据逐字节一致 |
| **Fail 标准** | 数据不一致或命令失败 |

### TC-CMD-005: WRITE_10 单块写入

| 项目 | 内容 |
|------|------|
| **用例 ID** | TC-CMD-005 |
| **测试目标** | 验证 WRITE_10 命令能正确写入单个逻辑块 |
| **前置条件** | 设备就绪，目标 LBA 可写 |
| **测试步骤** | 1. 生成随机数据（1 个逻辑块大小）<br>2. 构造 WRITE_10 CDB：LBA=0x2000, Length=1<br>3. 发送命令+数据<br>4. 用 READ_10 读回验证 |
| **预期结果** | 写入成功，读回数据一致 |
| **Pass 标准** | 写入+读回数据 MD5 一致 |
| **Fail 标准** | 写入失败或数据不一致 |

### TC-CMD-006: WRITE_10 多块连续写入

| 项目 | 内容 |
|------|------|
| **用例 ID** | TC-CMD-006 |
| **测试目标** | 验证连续多块写入的正确性 |
| **前置条件** | 设备就绪 |
| **测试步骤** | 1. 生成 256 块随机数据<br>2. WRITE_10 写入 LBA=0x3000, Length=256<br>3. READ_10 读回全部 256 块<br>4. 逐块比较 |
| **预期结果** | 全部 256 块数据一致 |
| **Pass 标准** | 每块数据校验通过 |
| **Fail 标准** | 任意块数据不一致 |

### TC-CMD-007: WRITE_10 FUA 强制写入

| 项目 | 内容 |
|------|------|
| **用例 ID** | TC-CMD-007 |
| **测试目标** | 验证 FUA=1 时数据直接写入非易失性介质 |
| **前置条件** | 设备就绪 |
| **测试步骤** | 1. 生成已知数据<br>2. WRITE_10 (FUA=1) 写入目标 LBA<br>3. **不发送** SYNCHRONIZE_CACHE<br>4. READ_10 (FUA=1) 读回<br>5. 比较数据 |
| **预期结果** | 数据一致（FUA 保证数据已落盘） |
| **Pass 标准** | 数据完全一致 |
| **Fail 标准** | 数据不一致（说明 FUA 未生效） |

### TC-CMD-008: WRITE_10 + READ_10 数据完整性全盘验证

| 项目 | 内容 |
|------|------|
| **用例 ID** | TC-CMD-008 |
| **测试目标** | 全盘写入后读回验证数据完整性 |
| **前置条件** | 设备就绪，**警告：此测试会覆盖全盘数据** |
| **测试步骤** | 1. 按 1MB 粒度生成带 LBA 标记的数据<br>2. 顺序写入全盘<br>3. 顺序读回全盘<br>4. 逐块校验 LBA 标记和数据 |
| **预期结果** | 全盘数据一致 |
| **Pass 标准** | 0 个坏块，100% 数据一致 |
| **Fail 标准** | 存在数据不一致的块 |

### TC-CMD-009: SYNCHRONIZE_CACHE_10 缓存同步

| 项目 | 内容 |
|------|------|
| **用例 ID** | TC-CMD-009 |
| **测试目标** | 验证 SYNCHRONIZE_CACHE 命令将缓存数据刷入介质 |
| **前置条件** | 设备就绪 |
| **测试步骤** | 1. WRITE_10 写入数据（不带 FUA）<br>2. 发送 SYNCHRONIZE_CACHE_10：`35 00 00 00 00 00 00 00 00 00`<br>3. 验证命令成功完成<br>4. 记录 Flush 延迟 |
| **预期结果** | 命令成功，延迟在合理范围内（<100ms） |
| **Pass 标准** | SCSI Status=GOOD，延迟 <100ms |
| **Fail 标准** | 命令失败或延迟超过 500ms |

### TC-CMD-010: UNMAP（Trim/Discard）命令

| 项目 | 内容 |
|------|------|
| **用例 ID** | TC-CMD-010 |
| **测试目标** | 验证 UNMAP 命令正确释放逻辑块 |
| **前置条件** | 设备支持 UNMAP（检查 VPD 页 0xB0 的 Maximum Unmap LBA Count） |
| **测试步骤** | 1. 先写入已知数据到目标范围<br>2. 发送 UNMAP 命令释放该范围<br>3. 读回目标范围数据<br>4. 验证数据为全 0 或全 FF（取决于实现） |
| **预期结果** | UNMAP 成功，读回数据为确定性值 |
| **Pass 标准** | 命令成功，读回数据符合预期 |
| **Fail 标准** | 命令失败或读回数据不确定 |

### TC-CMD-011: TEST UNIT READY

| 项目 | 内容 |
|------|------|
| **用例 ID** | TC-CMD-011 |
| **测试目标** | 验证设备就绪状态检测 |
| **前置条件** | 设备已枚举 |
| **测试步骤** | 1. 发送 TEST UNIT READY：`00 00 00 00 00 00`<br>2. 检查返回状态 |
| **预期结果** | SCSI Status=GOOD（设备就绪） |
| **Pass 标准** | Status=GOOD |
| **Fail 标准** | 返回 NOT READY 或其他错误 |

### TC-CMD-012: INQUIRY 设备信息查询

| 项目 | 内容 |
|------|------|
| **用例 ID** | TC-CMD-012 |
| **测试目标** | 验证 INQUIRY 命令返回正确的设备信息 |
| **前置条件** | 设备就绪 |
| **测试步骤** | 1. 发送标准 INQUIRY：`12 00 00 00 24 00`<br>2. 解析返回数据：Vendor ID、Product ID、Revision<br>3. 发送 VPD INQUIRY（Page 0x00）获取支持的 VPD 页列表<br>4. 发送 VPD INQUIRY（Page 0x80）获取序列号<br>5. 发送 VPD INQUIRY（Page 0xB0）获取块限制信息 |
| **预期结果** | 返回正确的设备信息 |
| **Pass 标准** | Vendor/Product/Revision 与规格一致，VPD 页解析正确 |
| **Fail 标准** | 返回信息与规格不符 |

### TC-CMD-013: REQUEST SENSE 错误信息获取

| 项目 | 内容 |
|------|------|
| **用例 ID** | TC-CMD-013 |
| **测试目标** | 验证 REQUEST SENSE 能正确报告设备状态 |
| **前置条件** | 设备就绪 |
| **测试步骤** | 1. 发送 REQUEST SENSE：`03 00 00 00 FC 00`<br>2. 解析 Sense Data：Sense Key、ASC、ASCQ<br>3. 在正常状态下应返回 NO SENSE (0x00) |
| **预期结果** | Sense Key=0x00 (NO SENSE) |
| **Pass 标准** | 正确返回当前设备状态 |
| **Fail 标准** | Sense Data 解析错误 |

### TC-CMD-014: MODE SENSE / MODE SELECT

| 项目 | 内容 |
|------|------|
| **用例 ID** | TC-CMD-014 |
| **测试目标** | 验证模式页读取和设置功能 |
| **前置条件** | 设备就绪 |
| **测试步骤** | 1. MODE SENSE(10) 读取 Cache Mode Page (0x08)<br>2. 记录 WCE (Write Cache Enable) 和 RCD (Read Cache Disable) 位<br>3. MODE SELECT(10) 修改 WCE 位<br>4. MODE SENSE(10) 验证修改生效 |
| **预期结果** | 模式页读写正确 |
| **Pass 标准** | 读取/修改/验证全部成功 |
| **Fail 标准** | 模式页修改不生效或读取错误 |

### TC-CMD-015: START STOP UNIT

| 项目 | 内容 |
|------|------|
| **用例 ID** | TC-CMD-015 |
| **测试目标** | 验证 START STOP UNIT 命令的电源控制功能 |
| **前置条件** | 设备就绪 |
| **测试步骤** | 1. 发送 START STOP UNIT (Power Condition=ACTIVE)<br>2. 验证设备处于 ACTIVE 模式<br>3. 发送 START STOP UNIT (Power Condition=SLEEP)<br>4. 验证设备进入 SLEEP<br>5. 发送 START STOP UNIT (Power Condition=ACTIVE) 唤醒 |
| **预期结果** | 电源模式切换正常 |
| **Pass 标准** | 模式切换成功，唤醒后功能正常 |
| **Fail 标准** | 模式切换失败或唤醒后功能异常 |

---

## 3. UFS 原生查询命令测试

### TC-CMD-101: 读取 Device Descriptor

| 项目 | 内容 |
|------|------|
| **用例 ID** | TC-CMD-101 |
| **测试目标** | 验证 QUERY REQUEST 读取设备描述符 |
| **前置条件** | 设备就绪 |
| **测试步骤** | 1. 发送 QUERY REQUEST (Opcode=0x01, IDN=0x00, Index=0)<br>2. 解析返回的 Device Descriptor<br>3. 验证关键字段：bLength、bDescriptorType、bNumberLU、wSpecVersion |
| **预期结果** | 返回合法的 Device Descriptor |
| **Pass 标准** | wSpecVersion=0x0310 (UFS 3.1)，bNumberLU ≤ 8 |
| **Fail 标准** | 描述符字段不合法 |

### TC-CMD-102: 读取 Unit Descriptor（全部 LUN）

| 项目 | 内容 |
|------|------|
| **用例 ID** | TC-CMD-102 |
| **测试目标** | 遍历读取所有 LUN 描述符 |
| **前置条件** | 已从 Device Descriptor 获取 bNumberLU |
| **测试步骤** | 1. 循环 Index=0 到 bNumberLU-1<br>2. 对每个 LUN 发送 QUERY REQUEST (Opcode=0x01, IDN=0x02, Index=i)<br>3. 解析 bLUEnable、qLogicalBlockSize、qLogicalBlockCount |
| **预期结果** | 每个启用的 LUN 返回合法描述符 |
| **Pass 标准** | 所有启用 LUN 的容量之和与设备总容量一致 |
| **Fail 标准** | LUN 描述符不合法或容量不一致 |

### TC-CMD-103: 读取 Health Descriptor

| 项目 | 内容 |
|------|------|
| **用例 ID** | TC-CMD-103 |
| **测试目标** | 验证健康描述符读取，评估设备寿命状态 |
| **前置条件** | 设备就绪 |
| **测试步骤** | 1. QUERY REQUEST (Opcode=0x01, IDN=0x09, Index=0)<br>2. 解析 bPreEOLInfo：0x01=正常, 0x02=警告, 0x03=紧急<br>3. 解析 bDeviceLifeTimeEstA/B：0x01-0x0A (10%-100% 已消耗) |
| **预期结果** | 返回合法的健康信息 |
| **Pass 标准** | 新设备：bPreEOLInfo=0x01, LifeTimeEst ≤ 0x02 |
| **Fail 标准** | 健康数据超出合理范围 |

### TC-CMD-104: 读取 Geometry Descriptor

| 项目 | 内容 |
|------|------|
| **用例 ID** | TC-CMD-104 |
| **测试目标** | 验证几何描述符中的存储参数 |
| **前置条件** | 设备就绪 |
| **测试步骤** | 1. QUERY REQUEST (Opcode=0x01, IDN=0x07, Index=0)<br>2. 解析 qTotalRawDeviceCapacity<br>3. 解析 bMaxNumberLU<br>4. 解析 dSegmentSize |
| **预期结果** | 容量与 128GB 规格一致 |
| **Pass 标准** | 总容量在 128GB ± 5% 范围内 |
| **Fail 标准** | 容量偏差超过 5% |

### TC-CMD-105: 读取 Configuration Descriptor

| 项目 | 内容 |
|------|------|
| **用例 ID** | TC-CMD-105 |
| **测试目标** | 验证配置描述符正确反映 LUN 配置 |
| **前置条件** | 设备就绪 |
| **测试步骤** | 1. QUERY REQUEST (Opcode=0x01, IDN=0x01, Index=0)<br>2. 解析 bConfDescContinue、bBootEnable<br>3. 逐个解析 Unit Descriptor Configurable Parameters |
| **预期结果** | 配置信息与实际 LUN 布局一致 |
| **Pass 标准** | 配置参数合法且与 Unit Descriptor 一致 |
| **Fail 标准** | 配置不一致 |

### TC-CMD-106: 读取 String Descriptor

| 项目 | 内容 |
|------|------|
| **用例 ID** | TC-CMD-106 |
| **测试目标** | 验证字符串描述符（厂商名/产品名/序列号） |
| **前置条件** | 设备就绪 |
| **测试步骤** | 1. 从 Device Descriptor 获取 iManufacturerName/iProductName/iSerialNumber 索引<br>2. 分别读取对应 String Descriptor<br>3. 验证字符串内容 |
| **预期结果** | 返回正确的厂商名/产品名/序列号 |
| **Pass 标准** | 字符串非空且内容合法（UTF-16 编码） |
| **Fail 标准** | 字符串为空或编码错误 |

### TC-CMD-107: 读写 Attribute - bActiveICCLevel

| 项目 | 内容 |
|------|------|
| **用例 ID** | TC-CMD-107 |
| **测试目标** | 验证 ICC 级别属性的读写功能 |
| **前置条件** | 设备就绪 |
| **测试步骤** | 1. Read Attribute (Opcode=0x03, IDN=0x0062) 读取当前 ICC 级别<br>2. Write Attribute (Opcode=0x04, IDN=0x0062) 设置新级别<br>3. 再次读取验证修改生效 |
| **预期结果** | ICC 级别读写正确 |
| **Pass 标准** | 写入值与回读值一致 |
| **Fail 标准** | 回读值与写入值不一致 |

### TC-CMD-108: 读写 Flag - fDeviceInit

| 项目 | 内容 |
|------|------|
| **用例 ID** | TC-CMD-108 |
| **测试目标** | 验证标志位读写功能 |
| **前置条件** | 设备就绪 |
| **测试步骤** | 1. Read Flag (Opcode=0x05, IDN=0x01) 读取 fDeviceInit<br>2. 验证初始化完成后值为 0<br>3. 测试 fPermanentWPEn 等只读标志位，验证写入被拒绝 |
| **预期结果** | 可读写标志位正常，只读标志位拒绝写入 |
| **Pass 标准** | 读写权限符合规范定义 |
| **Fail 标准** | 权限控制异常 |

### TC-CMD-109: NOP OUT / NOP IN 链路保活

| 项目 | 内容 |
|------|------|
| **用例 ID** | TC-CMD-109 |
| **测试目标** | 验证 NOP 命令链路保活功能和往返延迟 |
| **前置条件** | 设备就绪 |
| **测试步骤** | 1. 发送 NOP_OUT (Transaction Code=0x08)<br>2. 等待接收 NOP_IN (Transaction Code=0x28)<br>3. 测量往返延迟<br>4. 重复 100 次，统计延迟分布 |
| **预期结果** | 全部 NOP 响应正常 |
| **Pass 标准** | 100% 响应成功，平均延迟 < 100μs |
| **Fail 标准** | 存在超时或无响应 |

---

## 4. 任务管理命令测试

### TC-CMD-201: ABORT TASK

| 项目 | 内容 |
|------|------|
| **用例 ID** | TC-CMD-201 |
| **测试目标** | 验证 ABORT TASK 能中止指定命令 |
| **前置条件** | 设备就绪 |
| **测试步骤** | 1. 发送一个大块写入命令（如 WRITE_10, Length=65535）<br>2. 在命令执行期间发送 ABORT TASK (Function=0x01, Tag=目标命令 Tag)<br>3. 检查命令是否被成功中止<br>4. 验证设备仍可正常工作 |
| **预期结果** | 目标命令被中止，设备状态正常 |
| **Pass 标准** | 返回 TMF Response=Task Aborted，后续命令正常 |
| **Fail 标准** | 中止失败或设备异常 |

### TC-CMD-202: QUERY TASK

| 项目 | 内容 |
|------|------|
| **用例 ID** | TC-CMD-202 |
| **测试目标** | 验证 QUERY TASK 能查询命令执行状态 |
| **前置条件** | 设备就绪 |
| **测试步骤** | 1. 发送一个读取命令<br>2. 立即发送 QUERY TASK (Function=0x20, Tag=目标 Tag)<br>3. 解析返回的任务状态 |
| **预期结果** | 返回正确的任务状态 |
| **Pass 标准** | 状态码合法（Complete/Not Found/In Progress） |
| **Fail 标准** | 返回非法状态码 |

### TC-CMD-203: LUN RESET

| 项目 | 内容 |
|------|------|
| **用例 ID** | TC-CMD-203 |
| **测试目标** | 验证 LUN RESET 能复位指定 LUN |
| **前置条件** | 设备就绪，多个命令排队中 |
| **测试步骤** | 1. 向 LUN 0 发送多个命令填满队列<br>2. 发送 LUN RESET (Function=0x10, LUN=0)<br>3. 验证所有排队命令被取消<br>4. 验证 LUN 恢复正常<br>5. 发送新的读写命令验证功能 |
| **预期结果** | LUN 复位成功，功能恢复 |
| **Pass 标准** | 复位后新命令正常执行 |
| **Fail 标准** | 复位失败或 LUN 不可用 |

### TC-CMD-204: ABORT TASK SET

| 项目 | 内容 |
|------|------|
| **用例 ID** | TC-CMD-204 |
| **测试目标** | 验证 ABORT TASK SET 能中止一个 LUN 的全部任务 |
| **前置条件** | 设备就绪 |
| **测试步骤** | 1. 向 LUN 0 发送 8 个并发写入命令<br>2. 发送 ABORT TASK SET (Function=0x02, LUN=0)<br>3. 验证所有 8 个命令被中止<br>4. 发送新命令验证 LUN 正常 |
| **预期结果** | 全部任务被中止 |
| **Pass 标准** | 所有命令返回 Aborted，LUN 功能正常 |
| **Fail 标准** | 部分命令未被中止或 LUN 异常 |

### TC-CMD-205: CLEAR TASK SET

| 项目 | 内容 |
|------|------|
| **用例 ID** | TC-CMD-205 |
| **测试目标** | 验证 CLEAR TASK SET 清除任务集 |
| **前置条件** | 设备就绪 |
| **测试步骤** | 1. 发送多个命令到队列<br>2. 发送 CLEAR TASK SET (Function=0x08)<br>3. 验证队列被清空<br>4. 验证设备功能正常 |
| **预期结果** | 任务集清除成功 |
| **Pass 标准** | 队列清空，后续操作正常 |
| **Fail 标准** | 清除失败 |

---

## 5. 边界条件与异常场景测试

### TC-CMD-301: 越界 LBA 读取

| 项目 | 内容 |
|------|------|
| **用例 ID** | TC-CMD-301 |
| **测试目标** | 验证读取超出设备容量的 LBA 时的错误处理 |
| **前置条件** | 已知设备最大 LBA（从 Read Capacity 获取） |
| **测试步骤** | 1. READ_10：LBA = Max LBA + 1, Length=1<br>2. 检查返回状态 |
| **预期结果** | 返回 ILLEGAL REQUEST (Sense Key=0x05)，ASC=0x21 (LBA out of range) |
| **Pass 标准** | 正确返回错误码 |
| **Fail 标准** | 返回数据或设备异常 |

### TC-CMD-302: 零长度传输

| 项目 | 内容 |
|------|------|
| **用例 ID** | TC-CMD-302 |
| **测试目标** | 验证 Transfer Length=0 的处理 |
| **前置条件** | 设备就绪 |
| **测试步骤** | 1. READ_10：LBA=0, Transfer Length=0<br>2. WRITE_10：LBA=0, Transfer Length=0<br>3. 检查返回状态 |
| **预期结果** | 命令成功但不传输数据（SCSI 规范定义） |
| **Pass 标准** | Status=GOOD，无数据传输 |
| **Fail 标准** | 返回错误或传输了数据 |

### TC-CMD-303: 读取无效描述符 IDN

| 项目 | 内容 |
|------|------|
| **用例 ID** | TC-CMD-303 |
| **测试目标** | 验证查询无效描述符 ID 时的错误处理 |
| **前置条件** | 设备就绪 |
| **测试步骤** | 1. QUERY REQUEST (Opcode=0x01, IDN=0xFF)<br>2. 检查返回状态 |
| **预期结果** | 返回 INVALID PARAMETER 错误 |
| **Pass 标准** | 正确拒绝非法请求 |
| **Fail 标准** | 返回数据或设备异常 |

### TC-CMD-304: 写保护 LUN 写入测试

| 项目 | 内容 |
|------|------|
| **用例 ID** | TC-CMD-304 |
| **测试目标** | 验证写保护 LUN 拒绝写入操作 |
| **前置条件** | 设备有写保护的 LUN |
| **测试步骤** | 1. 通过 QUERY REQUEST 设置 fPowerOnWPEn=1<br>2. 尝试 WRITE_10 写入该 LUN<br>3. 检查返回状态 |
| **预期结果** | 返回 DATA PROTECT (Sense Key=0x07) |
| **Pass 标准** | 写入被拒绝，数据未被修改 |
| **Fail 标准** | 写入成功（写保护失效） |

### TC-CMD-305: 队列满（Queue Full）处理

| 项目 | 内容 |
|------|------|
| **用例 ID** | TC-CMD-305 |
| **测试目标** | 验证命令队列满时的处理 |
| **前置条件** | 设备就绪 |
| **测试步骤** | 1. 同时发送 33 个命令（超过最大队列深度 32）<br>2. 检查第 33 个命令的处理方式 |
| **预期结果** | 返回 TASK SET FULL 或排队等待 |
| **Pass 标准** | 正确处理队列溢出，不丢失命令 |
| **Fail 标准** | 命令丢失或设备挂死 |

### TC-CMD-306: 并发多 LUN 访问

| 项目 | 内容 |
|------|------|
| **用例 ID** | TC-CMD-306 |
| **测试目标** | 验证多个 LUN 并发访问的隔离性 |
| **前置条件** | 设备有 2+ 个启用的 LUN |
| **测试步骤** | 1. 同时向 LUN 0 和 LUN 1 发送读写命令<br>2. 对 LUN 0 执行 LUN RESET<br>3. 验证 LUN 1 不受影响<br>4. 验证两个 LUN 的数据完整性 |
| **预期结果** | LUN 间完全隔离 |
| **Pass 标准** | LUN 0 复位不影响 LUN 1 |
| **Fail 标准** | LUN 间相互影响 |

### TC-CMD-307: 命令超时处理

| 项目 | 内容 |
|------|------|
| **用例 ID** | TC-CMD-307 |
| **测试目标** | 验证命令超时后的恢复机制 |
| **前置条件** | 设备就绪 |
| **测试步骤** | 1. 发送命令并设置极短超时（如 1ms）<br>2. 等待超时触发<br>3. 执行 ABORT TASK<br>4. 验证设备恢复正常<br>5. 发送新命令验证功能 |
| **预期结果** | 超时后可通过任务管理恢复 |
| **Pass 标准** | 恢复成功，后续命令正常 |
| **Fail 标准** | 设备不可恢复 |

### TC-CMD-308: RPMB（Replay Protected Memory Block）访问

| 项目 | 内容 |
|------|------|
| **用例 ID** | TC-CMD-308 |
| **测试目标** | 验证 RPMB 分区的安全访问机制 |
| **前置条件** | 设备支持 RPMB（W-LUN RPMB） |
| **测试步骤** | 1. 发送 SECURITY PROTOCOL IN 读取 RPMB 计数器<br>2. 验证返回的计数器值合法<br>3. 尝试无认证写入 RPMB<br>4. 验证被拒绝 |
| **预期结果** | RPMB 安全机制正常 |
| **Pass 标准** | 无认证写入被拒绝 |
| **Fail 标准** | 安全机制被绕过 |

---

## 6. 测试执行脚本参考

### 6.1 使用 sg3_utils

```bash
#!/bin/bash
# UFS 命令基础测试脚本
DEVICE="/dev/sdX"  # 替换为实际设备

# TC-CMD-011: TEST UNIT READY
echo "=== TC-CMD-011: TEST UNIT READY ==="
sg_turs $DEVICE
echo "Return code: $?"

# TC-CMD-012: INQUIRY
echo "=== TC-CMD-012: INQUIRY ==="
sg_inq $DEVICE
sg_vpd --page=0xb0 $DEVICE

# TC-CMD-013: REQUEST SENSE
echo "=== TC-CMD-013: REQUEST SENSE ==="
sg_requests $DEVICE

# TC-CMD-001: READ_10 单块
echo "=== TC-CMD-001: READ_10 ==="
sg_raw -r 4096 $DEVICE 28 00 00 00 00 00 00 00 01 00

# TC-CMD-005: WRITE_10 单块
echo "=== TC-CMD-005: WRITE_10 ==="
dd if=/dev/urandom bs=4096 count=1 of=/tmp/test_block.bin
sg_raw -s 4096 -i /tmp/test_block.bin $DEVICE 2a 00 00 00 20 00 00 00 01 00
```

### 6.2 使用 ufs-utils

```bash
#!/bin/bash
# UFS 查询命令测试脚本
UFS_DEV="/dev/ufs-bsg0"  # 替换为实际 BSG 设备

# TC-CMD-101: 读取 Device Descriptor
echo "=== TC-CMD-101: Device Descriptor ==="
ufs-utils desc -a -p $UFS_DEV -t device

# TC-CMD-103: 读取 Health Descriptor
echo "=== TC-CMD-103: Health Descriptor ==="
ufs-utils desc -a -p $UFS_DEV -t health

# TC-CMD-107: 读取 ICC Level
echo "=== TC-CMD-107: ICC Level ==="
ufs-utils attr -a -p $UFS_DEV -t bActiveICCLevel
```

---

## 7. 测试覆盖度矩阵

| 命令类别 | 用例数 | 覆盖范围 |
|----------|--------|----------|
| SCSI 读写命令 | 15 | READ/WRITE/SYNC CACHE/UNMAP/TUR/INQUIRY/REQUEST SENSE/MODE SENSE/START STOP |
| UFS 查询命令 | 9 | 描述符(Device/Unit/Health/Geometry/Config/String) + 属性 + 标志位 + NOP |
| 任务管理命令 | 5 | ABORT TASK/QUERY TASK/LUN RESET/ABORT SET/CLEAR SET |
| 边界与异常 | 8 | 越界LBA/零长度/无效IDN/写保护/队列满/并发LUN/超时/RPMB |
| **总计** | **37** | **全面覆盖 JESD220E 第 7/8 章核心命令** |

---

**文档完成时间**: 2026-03-19  
**下一步**: 在实际 UFS 硬件上执行测试，收集真实数据
