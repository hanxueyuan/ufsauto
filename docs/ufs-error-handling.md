# UFS 错误处理详解

**版本**: UFS 3.1  
**更新时间**: 2026-03-21 00:30  
**学习阶段**: 夜间学习 Phase 1.4

---

## 📋 错误处理总览

UFS 采用**分层错误处理**架构，共 4 层：

```
┌─────────────────────────────────────────────────────────┐
│                    UFS 协议栈                            │
├─────────────────────────────────────────────────────────┤
│  应用层 (Application Layer)                              │
│  - SCSI 命令错误                                         │
│  - 任务管理错误                                          │
├─────────────────────────────────────────────────────────┤
│  传输层 (Transport Layer - TL)                           │
│  - UPIU 错误                                            │
│  - 序列错误                                              │
├─────────────────────────────────────────────────────────┤
│  网络层 (Network Layer - NL)                             │
│  - 连接管理错误                                          │
│  - 流量控制错误                                          │
├─────────────────────────────────────────────────────────┤
│  数据链路层 (Data Link Layer - DL)                       │
│  - CRC 错误                                              │
│  - 重传错误                                              │
├─────────────────────────────────────────────────────────┤
│  物理层 (Physical Layer - PA)                            │
│  - 信号完整性错误                                        │
│  - 时钟错误                                              │
└─────────────────────────────────────────────────────────┘
```

---

## 🔍 各层错误详解

### 1. 物理层 (PA) 错误

**最常见错误类型**，占所有错误的 60-70%

| 错误码 | 错误名称 | 说明 | 恢复方法 |
|--------|----------|------|----------|
| PA_ERR_RX_LINE_RESET | RX 线复位 | 接收端检测到线复位 | 自动恢复 |
| PA_ERR_TX_LINE_RESET | TX 线复位 | 发送端线复位 | 自动恢复 |
| PA_ERR_DIF_ERROR | DIF 错误 | 数据完整性错误 | 重试/报告 |
| PA_CRC_ERROR | CRC 错误 | 循环冗余校验错误 | 自动重传 |
| PA_PAUSED | PA 暂停 | 物理层暂停 | 等待恢复 |
| PA_ERROR | 通用 PA 错误 | 其他物理层错误 | 复位 PHY |

**典型场景**:
- 连接器松动
- 信号干扰
- 温度过高

### 2. 数据链路层 (DL) 错误

| 错误码 | 错误名称 | 说明 | 恢复方法 |
|--------|----------|------|----------|
| DL_NAC_RECEIVED | NAC 收到 | 未确认收到 | 重传 |
| DL_TC_ERROR | TC 错误 | 传输计数器错误 | 重置 TC |
| DL_AFC_ERROR | AFC 错误 | 流控错误 | 调整 AFC |
| DL_CRC_ERROR | DL CRC 错误 | 数据链路层 CRC | 重传 |
| DL_PAUSED | DL 暂停 | 数据链路层暂停 | 等待恢复 |

**典型场景**:
- 缓冲区溢出
- 流控失配
- 重传超限

### 3. 网络层 (NL) 错误

| 错误码 | 错误名称 | 说明 | 恢复方法 |
|--------|----------|------|----------|
| NL_CONNECTION_FAILURE | 连接失败 | 连接建立失败 | 重连 |
| NL_CONNECTION_LOST | 连接丢失 | 连接意外断开 | 重连 |
| NL_BAD_OCS | 坏 OCS | 输出控制状态错误 | 重置连接 |
| NL_PAUSED | NL 暂停 | 网络层暂停 | 等待恢复 |

**典型场景**:
- 设备移除
- 链路训练失败
- 协议不匹配

### 4. 传输层 (TL) 错误

| 错误码 | 错误名称 | 说明 | 恢复方法 |
|--------|----------|------|----------|
| TL_INVALID_UPIU | 无效 UPIU | UPIU 格式错误 | 丢弃/报告 |
| TL_WRONG_DIRECTION | 方向错误 | 数据传输方向错误 | 中止命令 |
| TL_WRONG_SEGMENT | 段错误 | 段类型错误 | 中止命令 |
| TL_EXCESS_RX | 接收超限 | 接收数据超限 | 丢弃 |
| TL_PAUSED | TL 暂停 | 传输层暂停 | 等待恢复 |

**典型场景**:
- 命令格式错误
- 数据长度不匹配
- 协议违规

### 5. 应用层错误（SCSI 错误）

**最常见的是 SCSI Sense Data**

| Sense Key | 说明 | 典型场景 |
|-----------|------|----------|
| 0x00 NO_SENSE | 无错误 | 正常 |
| 0x01 RECOVERED_ERROR | 已恢复错误 | 重试成功 |
| 0x02 NOT_READY | 设备未就绪 | 初始化中 |
| 0x03 MEDIUM_ERROR | 介质错误 | 坏块/读取失败 |
| 0x04 HARDWARE_ERROR | 硬件错误 | 设备故障 |
| 0x05 ILLEGAL_REQUEST | 非法请求 | 无效命令/LBA |
| 0x06 UNIT_ATTENTION | 设备注意 | 设备状态变化 |
| 0x07 DATA_PROTECT | 数据保护 | 写保护 |
| 0x08 BLANK_CHECK | 空白检查 | 未格式化 |
| 0x09 VENDOR_SPECIFIC | 厂商特定 | 厂商自定义 |
| 0x0A COPY_ABORTED | 复制中止 | 复制命令失败 |
| 0x0B ABORTED_COMMAND | 命令中止 | 命令被中止 |
| 0x0C MISCOMPARE | 比较不匹配 | 校验失败 |

**ASC/ASCQ 详解**（Additional Sense Code）:

| ASC | ASCQ | 说明 |
|-----|------|------|
| 0x00 | 0x00 | 无额外信息 |
| 0x11 | 0x00 | 读取错误（LBA） |
| 0x31 | 0x00 | 写入错误（LBA） |
| 0x3C | 0x00 | 介质超时 |
| 0x55 | 0x00 | 系统资源不足 |

---

## 🛠️ 错误恢复流程

### 标准恢复流程

```
错误检测
    │
    ▼
记录错误日志
    │
    ▼
┌───────────────────┐
│ 错误分类          │
│ - PA/DL 错误      │
│ - NL/TL 错误      │
│ - SCSI 错误       │
└─────────┬─────────┘
          │
    ┌─────┴─────┬──────────┐
    │           │          │
    ▼           ▼          ▼
自动重传    命令重试    设备复位
(1-3 次)     (1-3 次)     (最后手段)
    │           │          │
    └─────┬─────┴──────────┘
          │
          ▼
    成功？
    │
    ├─YES─→ 恢复正常操作
    │
    └─NO──→ 上报错误
              │
              ▼
         记录失效分析
```

### Linux UFS 驱动错误恢复

```c
// drivers/ufs/core/ufshcd.c 简化版

static void ufshcd_handle_error(struct ufs_hba *hba)
{
    // 1. 记录错误寄存器
    ufshcd_dump_regs(hba, REG_ERROR, ...);
    
    // 2. 根据错误类型恢复
    if (error & PA_ERROR) {
        // 物理层错误：重置 PHY
        ufshcd_phy_reset(hba);
    }
    
    if (error & DL_ERROR) {
        // 数据链路层错误：重置 DL
        ufshcd_dl_reset(hba);
    }
    
    if (error & TL_ERROR) {
        // 传输层错误：中止命令
        ufshcd_abort_commands(hba);
    }
    
    // 3. 如果恢复失败，执行设备复位
    if (!recovered) {
        ufshcd_device_reset(hba);
    }
    
    // 4. 记录错误日志
    dev_err(hba->dev, "UFS error recovered: %d\n", error);
}
```

---

## 📊 错误日志分析

### dmesg 错误日志示例

```bash
# 查看 UFS 错误日志
dmesg | grep -i ufs | grep -i error

# 示例输出
[12345.678] ufs 1d84000.ufshc: ufshcd_print_trs: tag 0x00 is occupied
[12345.679] ufs 1d84000.ufshc: ufshcd_handle_error: error code 0x00000002
[12345.680] ufs 1d84000.ufshc: DL error - NAC received
[12345.681] ufs 1d84000.ufshc: Error recovery started
[12345.700] ufs 1d84000.ufshc: Error recovery completed
```

### 使用 ufs-utils 查看错误

```bash
# 读取错误计数器
ufs-utils ufs read-attr /dev/ufs0 0x00D2  # dAvailablePhysicalResources
ufs-utils ufs read-attr /dev/ufs0 0x00D3  # dRawPhysicalResources

# 读取健康状态（包含错误信息）
ufs-utils ufs read-desc /dev/ufs0 8

# 清除错误计数器
ufs-utils ufs write-attr /dev/ufs0 0x00D2 0x00
```

### Python 错误日志分析工具

```python
#!/usr/bin/env python3
"""UFS 错误日志分析工具"""

import re
from collections import defaultdict
from datetime import datetime

def parse_dmesg_errors(log_file):
    """解析 dmesg 错误日志"""
    errors = defaultdict(list)
    
    with open(log_file, 'r') as f:
        for line in f:
            if 'ufs' in line.lower() and 'error' in line.lower():
                # 提取时间戳
                match = re.search(r'\[(\d+\.\d+)\]', line)
                if match:
                    timestamp = float(match.group(1))
                    errors[timestamp].append(line.strip())
    
    return errors

def analyze_errors(errors):
    """分析错误模式"""
    print(f"发现 {len(errors)} 个错误事件\n")
    
    # 统计错误类型
    error_types = defaultdict(int)
    for timestamp, lines in errors.items():
        for line in lines:
            if 'PA error' in line:
                error_types['PA'] += 1
            elif 'DL error' in line:
                error_types['DL'] += 1
            elif 'TL error' in line:
                error_types['TL'] += 1
            elif 'SCSI' in line:
                error_types['SCSI'] += 1
    
    print("错误类型统计:")
    for etype, count in sorted(error_types.items()):
        print(f"  {etype}: {count} 次")
    
    # 检测错误突发
    print("\n错误突发检测:")
    prev_time = None
    burst_count = 0
    for timestamp in sorted(errors.keys()):
        if prev_time and (timestamp - prev_time) < 1.0:  # 1 秒内
            burst_count += 1
        else:
            if burst_count > 3:
                print(f"  错误突发：{burst_count} 个错误/秒 @ {prev_time:.1f}s")
            burst_count = 1
        prev_time = timestamp

if __name__ == '__main__':
    import sys
    log_file = sys.argv[1] if len(sys.argv) > 1 else '/var/log/dmesg'
    errors = parse_dmesg_errors(log_file)
    analyze_errors(errors)
```

---

## ⚠️ 常见错误场景与解决方案

### 场景 1: CRC 错误频繁

**现象**: `dmesg` 中出现大量 `PA_CRC_ERROR`

**原因**:
- 连接器接触不良
- 信号干扰
- PCB 走线问题

**解决方案**:
1. 检查连接器
2. 增加屏蔽
3. 降低链路速度（临时方案）

```bash
# 强制降低到 G2 速度
echo 2 > /sys/class/ufs/ufs0/gear
```

### 场景 2: 命令超时

**现象**: SCSI 命令超时，`dmesg` 中出现 `Command timeout`

**原因**:
- 设备繁忙
- 固件 bug
- 温度过高导致降频

**解决方案**:
1. 增加超时时间
2. 检查设备温度
3. 更新固件

```bash
# 增加超时到 60 秒
echo 60 > /sys/block/sda/timeout
```

### 场景 3: 坏块增加

**现象**: `MEDIUM_ERROR` 频繁，坏块计数器增加

**原因**:
- NAND 寿命耗尽
- 写入放大过高
- 温度过高

**解决方案**:
1. 检查健康状态
2. 减少写入量
3. 改善散热
4. 准备更换设备

```bash
# 读取健康状态
ufs-utils ufs read-desc /dev/ufs0 8
```

---

## 📖 参考文档

1. **JEDEC UFS 3.1 Spec** - JESD220D, Section 15
2. **SCSI Primary Commands-4** - INCITS 532
3. **Linux UFS Driver** - drivers/ufs/core/ufshcd.c

---

**学习时间**: 2026-03-21 00:55  
**阶段进度**: 4/9 完成 ✅ 协议学习阶段完成  
**下一阶段**: 测试框架实现（01:00-03:00）

---

## 📚 协议学习阶段总结

### 已完成文档
1. ✅ `ufs-command-cheatsheet.md` - 命令速查表
2. ✅ `ufs-descriptor-reference.md` - 描述符参考
3. ✅ `ufs-power-management.md` - 电源管理详解
4. ✅ `ufs-error-handling.md` - 错误处理详解

### 下一步
**01:00 开始**: 测试框架代码实现
- 性能测试用例（4 个）
- QoS 测试套件（4 个）
- 失效分析引擎
