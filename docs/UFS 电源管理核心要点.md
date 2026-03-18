# UFS 电源管理核心要点

## 1. Power Mode 切换流程

### 1.1 PWM → HS 切换
```
Power Mode = PWM → HS-G1 → HS-G2 → HS-G3 → HS-G4
每档速率翻倍，功耗递增
```

### 1.2 关键参数
- **gear**: HS-G1~G4 (G4=11.6Gbps)
- **lane**: 1~2 lane (车规常用 2 lane 冗余)
- **pwm**: PWM_G1~G7 (初始握手用)

## 2. Hibernation 机制 (H8)

### 2.1 H8 Enter 流程
```
Host 发送 HIBERNATE ENTER
Device 确认 → 进入 H8 状态
Link 关闭，保持连接上下文
```

### 2.2 H8 Exit 流程
```
Host 发送 HIBERNATE EXIT
Device 唤醒 → 恢复 Link
耗时：~10μs (远快于 Power Off)
```

### 2.3 车规注意事项
- **温度范围**: -40°C~125°C 下 H8 稳定性验证
- **唤醒延迟**: 关键实时场景需评估 10μs 延迟影响
- **功耗**: H8 状态 <1mW (符合车规待机要求)

## 3. Runtime PM vs System PM

| 类型 | 触发条件 | 恢复时间 | 功耗 |
|------|----------|----------|------|
| Runtime PM | 空闲超时 | ~10μs | 低 |
| System PM | 系统休眠 | ~100ms | 极低 |
| Power Off | 系统关机 | ~1s | 最低 |

## 4. 车规电源管理要求

### 4.1 ISO 26262 相关
- **ASIL-B**: 电源状态切换需有故障检测
- **Fail-Safe**: H8 失败时需 fallback 到 Active
- **监控**: 实时监测 VCC/VCCQ 电压波动

### 4.2 AEC-Q100 测试项
- Grade 2: -40°C~105°C 循环测试
- 电源瞬态响应测试
- 休眠/唤醒循环寿命 (≥10 万次)

## 5. Linux 调试命令

```bash
# 查看电源状态
cat /sys/bus/platform/drivers/ufshcd/*/device_descriptor/power_mode

# 强制进入 H8
echo auto > /sys/bus/platform/drivers/ufshcd/*/device_descriptor/power/control

# 监控功耗
cat /sys/class/scsi_device/*/device/power_usage

# 查看 runtime PM 状态
cat /sys/bus/platform/drivers/ufshcd/*/device_descriptor/runtime_status
```

## 6. 常见问题排查

| 问题 | 可能原因 | 解决方案 |
|------|----------|----------|
| H8 失败 | 固件 Bug | 更新 UFS 固件 |
| 唤醒超时 | Link 训练失败 | 检查差分线质量 |
| 功耗异常 | WLUN 未休眠 | 检查 SCSI 设备电源策略 |
| 温度保护 | 过热降频 | 优化散热设计 |

---

**生成时间**: 2026-03-18 10:27
**状态**: 核心要点版 (可扩展)
