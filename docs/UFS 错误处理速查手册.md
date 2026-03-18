# UFS 错误处理速查手册

## 1. 错误层级与类型

```
┌─────────────────────────────────────┐
│  TL 层 (Transport Layer)            │  ← 命令/任务管理错误
├─────────────────────────────────────┤
│  NL 层 (Network Layer)              │  ← 连接/路由错误
├─────────────────────────────────────┤
│  DL 层 (Data Link Layer)            │  ← 数据帧/CRC 错误
├─────────────────────────────────────┤
│  PA 层 (Physical Layer)             │  ← 物理信号错误
└─────────────────────────────────────┘
```

## 2. 关键错误码速查

| 错误码 | 层级 | 含义 | 处理措施 |
|--------|------|------|----------|
| 0x01 | TL | INVALID_OCS | 检查命令状态 |
| 0x05 | TL | DEVICE_ERROR | 设备故障，需复位 |
| 0x10 | DL | CRC_ERROR | 检查信号完整性 |
| 0x15 | DL | PA_INIT_ERROR | 物理层初始化失败 |
| 0x20 | NL | CONNECTION_ERROR | 连接丢失，重连 |
| 0x30 | PA | PHY_ERROR | 物理层故障 |

## 3. 错误恢复流程

### 3.1 Link Recovery (DL 层)
```
检测到错误 → 发送 LINK_STARTUP → 重新训练 Link
耗时：~1ms
适用：CRC 错误、帧错误
```

### 3.2 Logical Unit Reset (TL 层)
```
发送 UFS_RESET LU → 等待完成 → 恢复 I/O
耗时：~10ms
适用：设备错误、命令超时
```

### 3.3 Host Controller Reset (最严重)
```
停止 DMA → 复位 HC → 重新初始化 → 恢复 I/O
耗时：~100ms
适用：HC 挂死、严重错误
```

## 4. Linux 错误监控

### 4.1 查看错误计数
```bash
# UFS 错误统计
cat /sys/kernel/debug/ufshcd/*/ufshcd_stats

# SCSI 错误日志
dmesg | grep -i "ufshcd\|scsi"

# 查看设备健康
cat /sys/class/scsi_device/*/device/health/descriptor
```

### 4.2 关键日志关键词
```
- "ufshcd_abort"     → 命令中止
- "link_startup_fail"→ Link 启动失败
- "device_reset"     → 设备复位
- "timeout"          → 超时错误
- "ecc_error"        → ECC 纠错
```

## 5. 车规可靠性设计要点

### 5.1 错误预防
- **ECC**: 强制开启，单 bit 纠正，双 bit 检测
- **End-to-End 保护**: 应用层 CRC 验证
- **Watchdog**: 超时自动恢复机制

### 5.2 故障检测
- **Pre-Failure Notification**: 寿命/温度/错误率阈值告警
- **Health Monitoring**: 实时监控 NAND 健康度
- **Smart Log**: 记录错误历史用于分析

### 5.3 安全状态
- **Fail-Safe**: 错误时进入安全状态 (只读/降级)
- **冗余设计**: 关键数据双份存储
- **快速恢复**: 目标恢复时间≤100ms (ASIL-B)

## 6. 调试 Checklist

```markdown
## 错误发生时的排查步骤
- [ ] 1. 记录错误码和发生时间
- [ ] 2. 检查 dmesg 完整日志
- [ ] 3. 查看 UFS 统计计数
- [ ] 4. 确认温度/电压是否正常
- [ ] 5. 尝试软件复位
- [ ] 6. 如失败，硬件上电重启
- [ ] 7. 保存日志供分析

## 常见问题快速定位
- CRC 错误频发 → 检查 PCB 走线/端接
- 超时错误 → 检查负载/温度
- 设备消失 → 检查供电/复位电路
- 性能下降 → 检查热节流/写放大
```

## 7. 车规认证相关测试

| 测试项 | 标准要求 | 验证方法 |
|--------|----------|----------|
| 错误注入 | ISO 26262 | 注入错误验证恢复 |
| 故障覆盖率 | ≥90% | FMEA 分析 |
| 恢复时间 | ≤100ms | 计时测试 |
| 错误日志 | 完整记录 | 日志审计 |

---

**生成时间**: 2026-03-18 10:28
**用途**: 快速定位和解决 UFS 错误问题
**车规**: 符合 ISO 26262 错误处理要求
