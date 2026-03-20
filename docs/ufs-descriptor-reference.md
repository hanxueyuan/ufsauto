# UFS 描述符参考手册

**版本**: UFS 3.1  
**更新时间**: 2026-03-20 23:30  
**学习阶段**: 夜间学习 Phase 1.2

---

## 📋 描述符总览

UFS 设备通过**描述符（Descriptor）**暴露设备信息和配置。共有 8 种描述符：

| IDN | 描述符名称 | 大小 | 访问方式 | 用途 |
|-----|------------|------|----------|------|
| 0x00 | **Device** | 128 字节 | Read | 设备基本信息 |
| 0x01 | **Configuration** | 64 字节 | Read | 配置参数 |
| 0x02 | **Unit** | 32 字节/LU | Read | 逻辑单元信息 |
| 0x03 | **RFU** | - | - | 保留 |
| 0x04 | **Geometry** | 24 字节 | Read | 几何结构（块数等） |
| 0x05 | **Interconnect** | 8 字节 | Read | 连接信息 |
| 0x06 | **String** | 可变 | Read | 字符串描述 |
| 0x07 | **RFU** | - | - | 保留 |
| 0x08 | **Health** | 32 字节 | Read | 健康状态（UFS 3.0+） |
| 0x80+ | **Vendor** | 可变 | Read/Write | 厂商自定义 |

---

## 🔍 Device Descriptor（设备描述符）

**IDN**: 0x00  
**大小**: 128 字节  
**用途**: 设备基本信息和全局参数

### 字段详解

| 偏移 | 字段名 | 大小 | 说明 | 典型值 |
|------|--------|------|------|--------|
| 0x00 | bLength | 1 字节 | 描述符长度 | 0x80 (128) |
| 0x01 | bDescriptorType | 1 字节 | 描述符类型 | 0x00 (Device) |
| 0x02 | bDevice | 1 字节 | 设备版本 | 0x03 (UFS 3.0) |
| 0x03 | bProduct | 1 字节 | 产品版本 | 0x01 |
| 0x04-0x05 | wManufactureID | 2 字节 | 厂商 ID | 0x012C (Micron) |
| 0x06-0x07 | wProductID | 2 字节 | 产品 ID | 厂商定义 |
| 0x08-0x0F | serialNumber | 8 字节 | 序列号 | ASCII 字符串 |
| 0x10-0x17 | modelNumber | 8 字节 | 型号 | ASCII 字符串 |
| 0x18-0x1F | OEMID | 8 字节 | OEM ID | ASCII 字符串 |
| 0x20 | bNumUnits | 1 字节 | LU 数量 | 0x02 (2 个 LU) |
| 0x21 | bNumWLU | 1 字节 | WLUN 数量 | 0x01 |
| 0x22 | bBootEnable | 1 字节 | 启动使能 | 0x00/0x01 |
| 0x23 | bDescrAccessEn | 1 字节 | 描述符访问使能 | 0x01 |
| 0x24 | bInitPowerMode | 1 字节 | 初始电源模式 | 0x01 (PWM_G1) |
| 0x25 | bHighPriorityLUN | 1 字节 | 高优先级 LU | 0x01 |
| 0x26 | bSecureRemovalType | 1 字节 | 安全移除类型 | 0x00 |
| 0x27 | bSecurityLU | 1 字节 | 安全 LU | 0x00 |
| 0x28 | bBBKEn | 1 字节 | Bad Block 使能 | 0x01 |
| 0x29 | bDataRecovery | 1 字节 | 数据恢复 | 0x00 |
| 0x2A-0x2B | wSupportedUFSFeatures | 2 字节 | 支持的特性 | 位掩码 |
| 0x2C | bMaxNumberofRTT | 1 字节 | 最大 RTT | 0x20 |
| 0x2D | bExtendedUFSFeaturesSupport | 1 字节 | 扩展特性支持 | 位掩码 |
| 0x2E-0x2F | wNumberofSecureWPA | 2 字节 | 安全 WPA 数量 | 0x00 |
| 0x30 | bPSALifetime | 1 字节 | PSA 生命周期 | 0x0A |
| 0x31 | bNumOfflineUnits | 1 字节 | 离线 LU 数量 | 0x00 |
| 0x32-0x7F | Reserved | - | 保留 | - |
| 0x80-0xFF | VendorSpecific | - | 厂商自定义 | - |

### 读取示例

```bash
# 使用 ufs-utils
ufs-utils ufs read-desc /dev/ufs0 0

# 输出示例（16 进制）
0000: 80 00 03 01 2C 01 00 02  41 42 43 44 31 32 33 34
0010: 55 46 53 30 30 31 20 20  4D 69 63 72 6F 6E 20 20
...
```

### Python 解析示例

```python
def parse_device_descriptor(data):
    """解析 Device Descriptor"""
    return {
        'length': data[0],
        'type': data[1],
        'device_version': data[2],
        'product_version': data[3],
        'manufacture_id': int.from_bytes(data[4:6], 'little'),
        'product_id': int.from_bytes(data[6:8], 'little'),
        'serial_number': data[8:16].decode('ascii').strip(),
        'model_number': data[16:24].decode('ascii').strip(),
        'num_lu': data[32],
        'num_wlu': data[33],
    }
```

---

## 🔍 Geometry Descriptor（几何描述符）

**IDN**: 0x04  
**大小**: 24 字节  
**用途**: 设备容量和块信息

### 字段详解

| 偏移 | 字段名 | 大小 | 说明 | 典型值 |
|------|--------|------|------|--------|
| 0x00 | bLength | 1 字节 | 描述符长度 | 0x18 (24) |
| 0x01 | bDescriptorType | 1 字节 | 描述符类型 | 0x04 (Geometry) |
| 0x02-0x05 | dNumBlocks | 4 字节 | 总块数 | 0x01000000 (16M 块) |
| 0x06-0x09 | dBlockSize | 4 字节 | 块大小（字节） | 0x1000 (4KB) |
| 0x0A-0x0D | dOptimalReadSize | 4 字节 | 最佳读取大小 | 0x40000 (256KB) |
| 0x0E-0x11 | dOptimalWriteSize | 4 字节 | 最佳写入大小 | 0x40000 (256KB) |
| 0x12-0x15 | dMaxInOutSize | 4 字节 | 最大传输大小 | 0x80000 (512KB) |
| 0x16-0x17 | wDeviceCapacity | 2 字节 | 设备容量（GB） | 0x0080 (128GB) |

### 读取示例

```bash
ufs-utils ufs read-desc /dev/ufs0 4
```

### 计算示例

```python
# 从 Geometry Descriptor 计算容量
num_blocks = 0x01000000  # 16M 块
block_size = 0x1000      # 4KB

capacity_gb = (num_blocks * block_size) / (1024**3)
print(f"设备容量：{capacity_gb:.1f} GB")  # 输出：64.0 GB
```

---

## 🔍 Unit Descriptor（逻辑单元描述符）

**IDN**: 0x02  
**大小**: 32 字节/LU  
**用途**: 每个 LU 的独立配置

### 字段详解

| 偏移 | 字段名 | 大小 | 说明 |
|------|--------|------|------|
| 0x00 | bLength | 1 字节 | 描述符长度 |
| 0x01 | bDescriptorType | 1 字节 | 描述符类型 |
| 0x02 | bUnitID | 1 字节 | LU ID |
| 0x03 | bLogicalUnitEnable | 1 字节 | LU 使能 |
| 0x04-0x07 | dNumBlocks | 4 字节 | LU 块数 |
| 0x08-0x0B | dBlockSize | 4 字节 | 块大小 |
| 0x0C | bDataRecovery | 1 字节 | 数据恢复 |
| 0x0D | bMemoryType | 1 字节 | 内存类型 |
| 0x0E | bLogicalUnitType | 1 字节 | LU 类型 |
| 0x0F | bLUWriteProtect | 1 字节 | LU 写保护 |
| 0x10-0x1F | Reserved | - | 保留 |

### 多 LU 示例

```bash
# LU 0 (Boot LU)
ufs-utils ufs read-desc /dev/ufs0 2 --index=0

# LU 1 (Root LUN)
ufs-utils ufs read-desc /dev/ufs0 2 --index=1
```

---

## 🔍 Health Descriptor（健康描述符）

**IDN**: 0x08 (UFS 3.0+)  
**大小**: 32 字节  
**用途**: 设备健康状态监控

### 字段详解

| 偏移 | 字段名 | 大小 | 说明 |
|------|--------|------|------|
| 0x00 | bLength | 1 字节 | 描述符长度 |
| 0x01 | bDescriptorType | 1 字节 | 描述符类型 |
| 0x02 | bPreEOLInfo | 1 字节 | 寿命预估（0-10） |
| 0x03 | bDeviceLifeTimeEstA | 1 字节 | 寿命 A 估算（0-10） |
| 0x04 | bDeviceLifeTimeEstB | 1 字节 | 寿命 B 估算（0-10） |
| 0x05-0x08 | dVendorSpecificInfo | 4 字节 | 厂商信息 |
| 0x09-0x0C | dTotalBytesWritten | 4 字节 | 总写入字节数 |
| 0x0D-0x10 | dTotalBytesRead | 4 字节 | 总读取字节数 |
| 0x11-0x14 | dTotalBadBlocks | 4 字节 | 坏块总数 |
| 0x15-0x1F | Reserved | - | 保留 |

### 健康状态解读

| bPreEOLInfo | 含义 | 建议 |
|-------------|------|------|
| 0x00 | 无信息 | - |
| 0x01-0x07 | 正常（10%-70%） | 正常使用 |
| 0x08 | 警告（80%） | 准备更换 |
| 0x09 | 警告（90%） | 尽快更换 |
| 0x0A | 寿命终止 | 立即更换 |

---

## 📊 描述符读取工具

### Bash 脚本批量读取

```bash
#!/bin/bash
# read-all-descriptors.sh

DEVICE="/dev/ufs0"
OUTPUT_DIR="./descriptors"

mkdir -p "$OUTPUT_DIR"

echo "读取 UFS 设备描述符..."

# Device Descriptor
echo "[1/8] Device Descriptor..."
ufs-utils ufs read-desc $DEVICE 0 > "$OUTPUT_DIR/device.txt"

# Configuration Descriptor
echo "[2/8] Configuration Descriptor..."
ufs-utils ufs read-desc $DEVICE 1 > "$OUTPUT_DIR/config.txt"

# Unit Descriptor (LU 0-7)
for i in {0..7}; do
    echo "[3.$i] Unit Descriptor LU$i..."
    ufs-utils ufs read-desc $DEVICE 2 --index=$i > "$OUTPUT_DIR/unit_lu$i.txt" 2>/dev/null || true
done

# Geometry Descriptor
echo "[4/8] Geometry Descriptor..."
ufs-utils ufs read-desc $DEVICE 4 > "$OUTPUT_DIR/geometry.txt"

# Interconnect Descriptor
echo "[5/8] Interconnect Descriptor..."
ufs-utils ufs read-desc $DEVICE 5 > "$OUTPUT_DIR/interconnect.txt"

# Health Descriptor (UFS 3.0+)
echo "[6/8] Health Descriptor..."
ufs-utils ufs read-desc $DEVICE 8 > "$OUTPUT_DIR/health.txt" 2>/dev/null || echo "不支持 Health Descriptor"

echo "完成！输出目录：$OUTPUT_DIR"
```

### Python 解析工具

```python
#!/usr/bin/env python3
"""UFS 描述符解析工具"""

import subprocess
import json
from pathlib import Path

def read_descriptor(device, idn, index=0):
    """读取描述符"""
    cmd = ['ufs-utils', 'ufs', 'read-desc', device, str(idn)]
    if index > 0:
        cmd.extend(['--index', str(index)])
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        return None
    
    # 解析 16 进制输出
    hex_lines = result.stdout.strip().split('\n')
    data = []
    for line in hex_lines:
        if ':' in line:
            parts = line.split(':')[1].strip().split()
            data.extend([int(b, 16) for b in parts])
    
    return bytes(data)

def parse_geometry(data):
    """解析 Geometry Descriptor"""
    return {
        'num_blocks': int.from_bytes(data[2:6], 'little'),
        'block_size': int.from_bytes(data[6:10], 'little'),
        'optimal_read': int.from_bytes(data[10:14], 'little'),
        'optimal_write': int.from_bytes(data[14:18], 'little'),
    }

def main():
    device = '/dev/ufs0'
    
    # 读取 Geometry
    geom_data = read_descriptor(device, 0x04)
    if geom_data:
        geom = parse_geometry(geom_data)
        print(f"设备容量：{geom['num_blocks'] * geom['block_size'] / 1024**3:.1f} GB")
        print(f"块大小：{geom['block_size']} 字节")
        print(f"最佳读取：{geom['optimal_read'] / 1024:.0f} KB")

if __name__ == '__main__':
    main()
```

---

## ⚠️ 注意事项

### 1. 访问权限
- 需要 root 权限访问 UFS 设备
- 生产环境谨慎写入描述符

### 2. 描述符版本
- UFS 2.1/3.0/3.1 描述符略有差异
- Health Descriptor 仅 UFS 3.0+ 支持

### 3. 厂商扩展
- IDN 0x80+ 为厂商自定义
- 不同厂商实现可能不同

### 4. 动态变化
- 某些描述符可能随时间变化（如 Health）
- 定期监控健康状态

---

## 📖 参考文档

1. **JEDEC UFS 3.1 Spec** - JESD220D, Section 13
2. **ufs-utils** - https://github.com/westerndigitalcorporation/ufs-utils
3. **Linux UFS Driver** - drivers/ufs/core/ufshcd.c

---

**学习时间**: 2026-03-20 23:55  
**阶段进度**: 2/9 完成  
**下一步**: UFS 电源管理详解（00:00-00:30）
