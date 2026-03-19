# UFS 3.1 电源模式转换时序详解

**文档版本**: V1.0  
**创建时间**: 2026-03-19  
**参考标准**: JEDEC JESD220E 第 9 章 / MIPI M-PHY v4.0 / MIPI UniPro v1.8  
**适用产品**: 群联 PS8363 + 长存 SQS 128GB UFS 3.1

---

## 1. 电源模式状态机

### 1.1 完整状态转换图

```
                          ┌──────────────────────────────┐
                          │          POWERDOWN            │
                          │  (M-PHY OFF, UniPro OFF)      │
                          │  功耗: ~5% ACTIVE             │
                          └──────────┬───────────────────┘
                                     ↑ SSU(PowerDown)
                                     │ SSU(Active) ↓
                          ┌──────────┴───────────────────┐
        ┌────────────────→│          ACTIVE               │←────────────────┐
        │                 │  (M-PHY ACTIVE, UniPro ACTIVE) │                 │
        │                 │  功耗: 100%                    │                 │
        │                 └──┬──────────┬──────────┬──────┘                 │
        │                    │          │          │                         │
        │  命令到达          │          │          │                         │
        │  (<10μs)           │          │          │                         │
        │                    │ Idle     │ SSU      │ H8_Enter               │
        │                    │ Timeout  │ (Sleep)  │                         │
        │                    ↓          ↓          ↓                         │
   ┌────┴────────┐   ┌──────────┐   ┌──────────────┐                       │
   │    IDLE     │   │  SLEEP   │   │   HIBERN8    │                       │
   │ (M-PHY     │   │ (M-PHY   │   │ (M-PHY H8,   │                       │
   │  STALL)    │   │  H8)     │   │  UniPro H8)  │                       │
   │ 功耗: ~30% │   │ 功耗:~10%│   │ 功耗: ~1%    │                       │
   └─────────────┘   └────┬─────┘   └──────┬───────┘                       │
                          │                 │                                │
                          │ 唤醒请求         │ H8_Exit                       │
                          │ (<50μs)          │ (<10ms)                       │
                          └────────────────→│←───────────────────────────────┘
```

### 1.2 合法转换路径

| 源模式 | 目标模式 | 触发方式 | 时间 |
|--------|----------|----------|------|
| ACTIVE → IDLE | 自动（空闲超时） | Host Controller 自动触发 | ~0（配置延迟） |
| IDLE → ACTIVE | 自动（新命令） | 命令到达自动唤醒 | < 10μs |
| ACTIVE → SLEEP | SSU 命令 | START STOP UNIT (Power=SLEEP) | < 100μs |
| SLEEP → ACTIVE | 唤醒请求 | Host 发送唤醒 | < 50μs |
| ACTIVE → HIBERN8 | H8_Enter | Host 发起 HIBERN8 请求 | < 100μs |
| HIBERN8 → ACTIVE | H8_Exit | Host 发起退出请求 | < 10ms |
| ACTIVE → POWERDOWN | SSU 命令 | START STOP UNIT (Power=POWERDOWN) | < 1ms |
| POWERDOWN → ACTIVE | 唤醒/复位 | 硬件复位或唤醒命令 | < 1ms |

### 1.3 非法转换路径

以下转换在 UFS 3.1 规范中**未定义**或**不允许**：

- IDLE → SLEEP（必须先回到 ACTIVE）
- IDLE → HIBERN8（必须先回到 ACTIVE）
- SLEEP → HIBERN8（必须先回到 ACTIVE）
- HIBERN8 → SLEEP（必须先回到 ACTIVE）
- POWERDOWN → HIBERN8（必须先回到 ACTIVE）

---

## 2. 各模式转换详细时序

### 2.1 ACTIVE → IDLE 转换

这是最常见的转换，由 UFS Host Controller (UFSHCI) 自动管理：

```
Host Controller                           UFS Device
     │                                         │
     │  最后一个命令完成                        │
     │  ↓ 启动空闲计时器                       │
     │                                         │
     │  ══════ 空闲超时 (可配置) ═══════       │
     │                                         │
     │  关闭不必要的 TX Lane                    │
     │──── M-PHY: HS → STALL ────────────→    │
     │                                    ←────│ Device 检测到 STALL
     │                                         │ 降低内部时钟
     │                                         │ 关闭空闲电路
     │                                         │
     │  ═══ IDLE 模式 ═══                      │
     │                                         │
```

**Linux ufshcd 实现**：
```c
/* drivers/ufs/core/ufshcd.c */
static void ufshcd_idle_handler(struct work_struct *work)
{
    struct ufs_hba *hba = container_of(work, struct ufs_hba,
                                        idle_work.work);
    /* 检查是否有未完成的命令 */
    if (hba->outstanding_reqs || hba->outstanding_tasks)
        return;
    
    /* 执行链路状态转换 */
    ufshcd_link_state_transition(hba, UIC_LINK_HIBERN8_STATE, 
                                  false);
}
```

### 2.2 IDLE → ACTIVE 转换

```
Host Controller                           UFS Device
     │                                         │
     │  ═══ IDLE 模式 ═══                      │
     │                                         │
     │  新命令到达 Host Queue                   │
     │  ↓ 检测到命令等待                        │
     │                                         │
     │──── M-PHY: STALL → HS ────────────→    │
     │  t=0                                    │
     │                               ←────────│ Device 检测到 HS 恢复
     │                                         │ 恢复内部时钟
     │                                         │ t ≈ 5-8μs
     │                                         │
     │←── READY 信号 ────────────────────────  │
     │  t < 10μs                               │
     │                                         │
     │──── 发送命令 UPIU ────────────────→     │
     │                                         │
```

**时间参数**：
| 参数 | 典型值 | 最大值 | 来源 |
|------|--------|--------|------|
| M-PHY STALL → HS | 2-5 μs | 10 μs | M-PHY v4.0 |
| Device 内部恢复 | 1-3 μs | 5 μs | 设备实现 |
| 总唤醒时间 | 3-8 μs | **< 10 μs** | JESD220E |

### 2.3 ACTIVE → HIBERN8 转换（重点）

HIBERN8 是车载最常用的深度休眠模式，其转换流程涉及 M-PHY 和 UniPro 两层：

```
Host (UFSHCI)          UniPro (L3)           M-PHY (L1.5)         Device
     │                      │                      │                  │
     │ 1. 停止发送命令       │                      │                  │
     │ 2. 等待所有命令完成    │                      │                  │
     │ 3. 发送 SYNC CACHE    │                      │                  │
     │──────────────────────────────────────────────────────────→     │
     │                      │                      │                  │
     │←── SYNC CACHE Done ──────────────────────────────────────     │
     │                      │                      │                  │
     │ 4. 触发 H8_Enter     │                      │                  │
     │──→ DME_HIBERNATE_ENTER│                      │                  │
     │                      │                      │                  │
     │                      │ 5. UniPro 停止流量     │                  │
     │                      │    控制帧              │                  │
     │                      │──→ PA_HIBERNATE_REQ   │                  │
     │                      │                      │                  │
     │                      │                      │ 6. M-PHY 发送     │
     │                      │                      │    HIBERN8 序列    │
     │                      │                      │──────────────→   │
     │                      │                      │                  │
     │                      │                      │        7. Device │
     │                      │                      │        M-PHY 确认│
     │                      │                      │←──────────────   │
     │                      │                      │                  │
     │                      │ 8. PA_HIBERNATE_CNF   │                  │
     │                      │←─────────────────────│                  │
     │                      │                      │                  │
     │←── H8_Enter Complete │                      │                  │
     │                      │                      │                  │
     │  ═══ HIBERN8 模式 ═══                       │                  │
     │  M-PHY: 断电                                │                  │
     │  UniPro: 保持状态                            │                  │
     │  功耗: ~1% ACTIVE                           │                  │
```

**时间参数**：
| 步骤 | 参数 | 典型值 | 最大值 |
|------|------|--------|--------|
| 步骤 4-5 | DME_HIBERNATE_ENTER 处理 | 1-5 μs | 10 μs |
| 步骤 6 | M-PHY HIBERN8 序列 | 5-20 μs | 50 μs |
| 步骤 7 | Device M-PHY 确认 | 5-10 μs | 20 μs |
| **总计** | **tHIBERN8_ENTER** | **15-40 μs** | **< 100 μs** |

### 2.4 HIBERN8 → ACTIVE 转换（重点）

```
Host (UFSHCI)          UniPro (L3)           M-PHY (L1.5)         Device
     │                      │                      │                  │
     │  ═══ HIBERN8 模式 ═══                       │                  │
     │                      │                      │                  │
     │ 1. 触发 H8_Exit      │                      │                  │
     │──→ DME_HIBERNATE_EXIT │                      │                  │
     │                      │                      │                  │
     │                      │ 2. UniPro 准备恢复    │                  │
     │                      │──→ PA_EXIT_HIBERNATE  │                  │
     │                      │                      │                  │
     │                      │                      │ 3. M-PHY 上电     │
     │                      │                      │    PLL 锁定       │
     │                      │                      │    (1-5 ms)       │
     │                      │                      │──────────────→   │
     │                      │                      │                  │
     │                      │                      │        4. Device │
     │                      │                      │        M-PHY 上电│
     │                      │                      │        PLL 锁定  │
     │                      │                      │        (1-5 ms)  │
     │                      │                      │←──────────────   │
     │                      │                      │                  │
     │                      │                      │ 5. 链路训练       │
     │                      │                      │    (Burst 交换)   │
     │                      │                      │    (0.5-2 ms)     │
     │                      │                      │←────────────→    │
     │                      │                      │                  │
     │                      │ 6. UniPro 链路恢复    │                  │
     │                      │    流量控制恢复        │                  │
     │                      │←─────────────────────│                  │
     │                      │                      │                  │
     │←── H8_Exit Complete  │                      │                  │
     │                      │                      │                  │
     │ 7. 验证链路状态       │                      │                  │
     │    发送 NOP_OUT       │                      │                  │
     │──────────────────────────────────────────────────────────→     │
     │←── NOP_IN ──────────────────────────────────────────────      │
     │                      │                      │                  │
     │ 8. 恢复正常命令发送   │                      │                  │
```

**时间参数**：
| 步骤 | 参数 | 典型值 | 最大值 | 说明 |
|------|------|--------|--------|------|
| 步骤 3 | Host M-PHY PLL 锁定 | 1-3 ms | 5 ms | PLL 频率稳定 |
| 步骤 4 | Device M-PHY PLL 锁定 | 1-3 ms | 5 ms | PLL 频率稳定 |
| 步骤 5 | 链路训练 | 0.5-1 ms | 2 ms | Burst 同步 |
| 步骤 6 | UniPro 恢复 | 0.1-0.5 ms | 1 ms | 流量控制 |
| **总计** | **tHIBERN8_EXIT** | **3-7 ms** | **< 10 ms** | JESD220E 要求 |

> **关键瓶颈**：M-PHY PLL 重新锁定是 HIBERN8 唤醒时间的主要组成部分（占 60-80%）。

### 2.5 ACTIVE → SLEEP 转换

```
Host                                              Device
  │                                                  │
  │ 1. START STOP UNIT (Power Condition = SLEEP)     │
  │──────────────────────────────────────────────→   │
  │                                                  │
  │                                     2. Device    │
  │                                     完成待处理命令│
  │                                     刷新缓存     │
  │                                                  │
  │←── Command Complete ──────────────────────────   │
  │                                                  │
  │ 3. Host 发起 HIBERN8 (作为 SLEEP 的物理层实现)    │
  │──── H8_Enter ────────────────────────────────→   │
  │                                                  │
  │←── H8_Enter_Confirm ─────────────────────────    │
  │                                                  │
  │  ═══ SLEEP 模式 ═══                              │
  │  物理层: 等效 HIBERN8                             │
  │  逻辑层: SLEEP 状态                               │
  │  区别: SLEEP 时设备保持更多内部状态                │
```

**SLEEP vs HIBERN8 的区别**：

| 特性 | SLEEP | HIBERN8 |
|------|-------|---------|
| 触发方式 | SSU 命令 | H8_Enter 原语 |
| 物理层状态 | M-PHY HIBERN8 | M-PHY HIBERN8 |
| 设备内部状态 | 保持更多上下文 | 最小化状态保持 |
| 唤醒时间 | < 50μs | < 10ms |
| 唤醒后 | 可立即执行命令 | 可能需要重新初始化 |
| 典型功耗 | ~10% ACTIVE | ~1% ACTIVE |
| 适用场景 | 短暂休眠（秒级） | 长时间休眠（分钟级） |

---

## 3. M-PHY 和 UniPro 在电源转换中的角色

### 3.1 M-PHY 电源状态

M-PHY v4.0 定义了以下电源状态：

```
M-PHY 电源状态机：

  ┌─────────┐   ACTIVATE   ┌─────────┐
  │  SLEEP  │ ───────────→ │  ACTIVE │
  │(LS Mode)│ ←─────────── │(HS Mode)│
  └─────────┘   SLEEP_REQ  └────┬────┘
                                 │
                    STALL_REQ    │   HIBERN8_REQ
                    ┌────────────┤────────────────┐
                    ↓            │                ↓
              ┌─────────┐       │          ┌──────────┐
              │  STALL  │       │          │ HIBERN8  │
              │(暂停TX) │       │          │(断电)    │
              └─────────┘       │          └──────────┘
                                │
                         DISABLED_REQ
                                │
                                ↓
                          ┌──────────┐
                          │ DISABLED │
                          │(完全关闭)│
                          └──────────┘
```

| M-PHY 状态 | UFS 电源模式 | TX 状态 | RX 状态 | PLL 状态 |
|------------|-------------|---------|---------|----------|
| ACTIVE (HS) | ACTIVE | 发送数据 | 接收数据 | 锁定 |
| STALL | IDLE | 暂停 | 监听 | 锁定 |
| HIBERN8 | SLEEP/HIBERN8 | 关闭 | 关闭 | 关闭 |
| DISABLED | POWERDOWN | 完全关闭 | 完全关闭 | 关闭 |

### 3.2 UniPro 电源状态

UniPro v1.8 在 M-PHY 之上管理链路层电源：

```
UniPro 链路状态：

  ┌──────────┐  DME_HIBERNATE_ENTER  ┌──────────────┐
  │  ACTIVE  │ ────────────────────→ │  HIBERN8     │
  │          │ ←──────────────────── │              │
  └──────────┘  DME_HIBERNATE_EXIT   └──────────────┘
       ↓                                    ↓
  流量控制正常                          流量控制暂停
  TC0/TC1 活跃                          所有 TC 暂停
  AFC 帧交换                            无 AFC 帧
```

### 3.3 三层协同转换

以 HIBERN8 Enter 为例，三层的协同工作：

```
时间轴 →

应用层:  [停止命令] [等待完成] [SYNC CACHE]     [IDLE]
              │           │         │               │
UniPro层:     │           │         │  [停止AFC]    [H8状态]
              │           │         │      │         │
M-PHY层:      │           │         │      │  [H8序列] [断电]
              ↓           ↓         ↓      ↓    ↓      ↓
时间:         t0          t1        t2     t3   t4     t5

t0: Host 决定进入 HIBERN8
t1: 所有未完成命令返回
t2: SYNC CACHE 完成（数据安全）
t3: UniPro 停止流量控制
t4: M-PHY 发送 HIBERN8 序列
t5: M-PHY 断电，进入 HIBERN8
```

---

## 4. 异常场景处理

### 4.1 转换超时

```
正常流程:
  Host ──→ H8_Enter ──→ Device
  Host ←── H8_Enter_CNF ← Device (< 100μs)

超时场景:
  Host ──→ H8_Enter ──→ Device
  Host     等待...      Device 无响应
  Host     超时（100ms-1s，可配置）
  
恢复流程:
  Host ──→ UniPro Reset
  Host ──→ M-PHY Reset
  Host ──→ Device Reset（最终手段）
```

**Linux ufshcd 超时处理**：
```c
/* drivers/ufs/core/ufshcd.c */
static int ufshcd_uic_hibern8_enter(struct ufs_hba *hba)
{
    int ret;
    
    /* 发送 HIBERN8 Enter */
    ret = ufshcd_uic_pwr_ctrl(hba, UIC_CMD_DME_HIBER_ENTER);
    
    if (ret) {
        /* 超时或失败 */
        dev_err(hba->dev, "hibern8 enter failed: %d\n", ret);
        
        /* 尝试链路恢复 */
        ret = ufshcd_link_recovery(hba);
        if (ret)
            /* 最终手段：Host Reset */
            ufshcd_host_reset_and_restore(hba);
    }
    
    return ret;
}
```

### 4.2 转换中断电

```
场景: ACTIVE → HIBERN8 过程中 VCC 断电

风险分析:
  - SYNC CACHE 已完成: 数据安全（已落盘）
  - SYNC CACHE 未完成: 缓存中的数据可能丢失
  - M-PHY 转换中断: 上电后需要 M-PHY 重新初始化

恢复流程:
  1. 重新上电
  2. M-PHY 初始化（PLL 锁定）
  3. UniPro 链路建立
  4. UFS Device 枚举
  5. 读取 Health Descriptor 检查设备状态
  6. 执行 TEST UNIT READY 验证功能
```

### 4.3 链路错误恢复

```
错误类型          严重度     恢复方法
────────────────────────────────────────────────
PA_ERROR          低        UniPro 自动重传
DL_ERROR          中        链路层重置
NL_ERROR          中        网络层重置  
TL_ERROR          高        传输层重置
DME_ERROR         高        DME 重置
FATAL_ERROR       致命      Host Controller 重置
```

---

## 5. Linux 内核 ufshcd 电源管理实现

### 5.1 关键数据结构

```c
/* UFS 电源模式定义 */
enum ufs_pm_op {
    UFS_RUNTIME_PM,        /* 运行时电源管理 */
    UFS_SYSTEM_PM,         /* 系统级电源管理 */
    UFS_SHUTDOWN_PM,       /* 关机电源管理 */
};

/* 链路状态 */
enum uic_link_state {
    UIC_LINK_OFF_STATE     = 0,  /* 链路关闭 */
    UIC_LINK_ACTIVE_STATE  = 1,  /* 链路活跃 */
    UIC_LINK_HIBERN8_STATE = 2,  /* HIBERN8 */
    UIC_LINK_BROKEN_STATE  = 3,  /* 链路断裂（错误） */
};

/* UFS 设备电源模式 */
enum ufs_dev_pwr_mode {
    UFS_ACTIVE_PWR_MODE    = 1,
    UFS_SLEEP_PWR_MODE     = 2,
    UFS_POWERDOWN_PWR_MODE = 3,
    UFS_DEEPSLEEP_PWR_MODE = 4,
};
```

### 5.2 Runtime PM 流程

```c
/* 运行时挂起（进入 HIBERN8） */
static int ufshcd_runtime_suspend(struct ufs_hba *hba)
{
    int ret;
    
    /* 1. 停止发送新命令 */
    ufshcd_hold(hba, false);
    
    /* 2. 等待未完成命令完成 */
    ret = ufshcd_wait_for_doorbell_clr(hba, TIMEOUT_MS);
    
    /* 3. 进入 HIBERN8 */
    ret = ufshcd_link_state_transition(hba, 
            UIC_LINK_HIBERN8_STATE, false);
    
    /* 4. 关闭 Host Controller 时钟（可选） */
    if (ufshcd_can_disable_clks(hba))
        ufshcd_disable_clocks(hba);
    
    return ret;
}

/* 运行时恢复（退出 HIBERN8） */
static int ufshcd_runtime_resume(struct ufs_hba *hba)
{
    int ret;
    
    /* 1. 恢复 Host Controller 时钟 */
    ufshcd_enable_clocks(hba);
    
    /* 2. 退出 HIBERN8 */
    ret = ufshcd_link_state_transition(hba,
            UIC_LINK_ACTIVE_STATE, false);
    
    /* 3. 验证设备状态 */
    ret = ufshcd_verify_dev_init(hba);
    
    /* 4. 允许发送命令 */
    ufshcd_release(hba);
    
    return ret;
}
```

### 5.3 sysfs 接口

Linux 提供了 sysfs 接口用于监控和控制 UFS 电源状态：

```bash
# UFS 设备电源状态
/sys/bus/platform/drivers/ufshcd/*/power/runtime_status
# 可能的值: active, suspended, suspending, resuming

# Runtime PM 自动挂起延迟
/sys/bus/platform/drivers/ufshcd/*/power/autosuspend_delay_ms
# 默认值: 3000 (3秒)
# 设置为 -1 禁用 Runtime PM

# UFS 链路状态
/sys/bus/platform/drivers/ufshcd/*/link_state
# 可能的值: active, hibern8, off, broken

# UFS 设备电源模式
/sys/bus/platform/drivers/ufshcd/*/device_power_mode
# 可能的值: active, sleep, powerdown

# 强制进入/退出 HIBERN8（调试用）
echo 1 > /sys/bus/platform/drivers/ufshcd/*/hibern8_on_idle
echo 0 > /sys/bus/platform/drivers/ufshcd/*/hibern8_on_idle
```

---

## 6. 电源模式转换测试要点

### 6.1 时序验证测试矩阵

| 测试项 | 测量参数 | 规格要求 | 测量方法 |
|--------|----------|----------|----------|
| IDLE 唤醒 | tIDLE_EXIT | < 10μs | 示波器 + 逻辑分析仪 |
| SLEEP 进入 | tSLEEP_ENTER | < 100μs | 示波器 |
| SLEEP 唤醒 | tSLEEP_EXIT | < 50μs | 示波器 |
| H8 进入 | tHIBERN8_ENTER | < 100μs | 逻辑分析仪 |
| H8 唤醒 | tHIBERN8_EXIT | < 10ms | 示波器 + 逻辑分析仪 |
| H8 PLL 锁定 | tPLL_LOCK | < 5ms | 示波器（PLL 输出） |
| POWERDOWN 唤醒 | tPOWERDOWN_EXIT | < 1ms | 示波器 |

### 6.2 关键测试场景

1. **正常转换验证**：每条合法路径执行 100 次
2. **快速往返**：H8_Enter 后立即 H8_Exit（最小间隔）
3. **并发转换**：转换期间有命令到达
4. **错误注入**：模拟 M-PHY 链路错误后的恢复
5. **温度极端**：-40°C 和 +105°C 下的转换时序
6. **电压边界**：VCC=2.7V（下限）时的转换可靠性

---

**文档完成时��**: 2026-03-19  
**关联文档**: UFS_3.1_电源管理详解.md、UFS_3.1_电源管理测试用例集.md、UFS_3.1_ICC控制机制详解.md
