# Linux UFS 驱动源码深度分析

**分析时间**: 2026-03-18 (通宵)  
**源码**: Linux Kernel drivers/ufs/core/ufshcd.c  
**行数**: 11,294 行 (9,634 LOC)  
**目标**: 彻底理解 UFS 驱动工作原理

---

## 📊 驱动架构总览

```
┌─────────────────────────────────────────────────────────┐
│              Linux UFS 驱动架构                          │
├─────────────────────────────────────────────────────────┤
│  Block Device Layer (sd.c)                              │
│         ↓                                                │
│  SCSI Mid-Layer (scsi_lib.c)                            │
│         ↓                                                │
│  UFS Host Controller (ufshcd.c) ← 核心分析对象          │
│         ↓                                                │
│  UFSHCI 规范 (JESD223)                                  │
│         ↓                                                │
│  M-PHY + UniPro (物理层 + 协议层)                        │
└─────────────────────────────────────────────────────────┘
```

---

## 🔑 核心数据结构

### 1. ufshcd_host - 主机控制器结构

```c
struct ufs_hba {
    /* 硬件资源 */
    void __iomem *mmio_base;        // 寄存器基地址
    struct platform_device *pdev;   // 平台设备
    struct ufs_host_params hba_params; // 主机参数
    
    /* SCSI 层接口 */
    struct Scsi_Host *host;         // SCSI 主机
    struct scsi_device *sdev_ufs_device; // UFS SCSI 设备
    
    /* 电源管理 */
    struct ufs_dev_info dev_info;   // 设备信息
    enum ufs_dev_pwr_mode curr_dev_pwr_mode; // 当前设备电源模式
    enum uic_link_state ufs_link_state;      // 链路状态
    
    /* 命令队列 */
    struct ufshcd_lrb *lrb;         // 逻辑请求块 (队列深度)
    unsigned long active_lrb_map;   // 活跃 LRB 位图
    unsigned int nr_hw_queues;      // 硬件队列数
    
    /* 统计信息 */
    struct ufs_stats stats;         // 性能统计
    
    /* 回调函数 */
    struct ufs_hba_variant_ops *vops; // 变体操作
};
```

**关键字段说明**：
- `mmio_base`: UFS 控制器寄存器映射
- `lrb`: 命令队列（深度由 hba->nutrs 决定，通常 32）
- `curr_dev_pwr_mode`: 当前设备电源模式（Active/Idle/Sleep 等）
- `ufs_link_state`: 链路状态（Hibern8/Active 等）

---

### 2. ufshcd_lrb - 逻辑请求块

```c
struct ufshcd_lrb {
    struct ufshcd_sg_entry *sgl;    // 散射聚集列表
    dma_addr_t sg_dma_addr;         // SG DMA 地址
    
    struct ufshcd_utp_req_desc *utr_descriptor_ptr; // 请求描述符
    dma_addr_t utr_descriptor_dma_addr;
    
    struct ufshcd_utp_upiu_cmd *cmd_upiu;  // 命令 UPIU
    struct ufshcd_utp_upiu_rsp *response_upiu; // 响应 UPIU
    
    struct scsi_cmnd *cmd;          // SCSI 命令
    int task_tag;                   // 任务标签 (0-31)
    
    ktime_t start_time;             // 命令开始时间
    unsigned long transfer_start_time; // 传输开始时间
};
```

**命令流程**：
```
SCSI 命令 → LRB 分配 → UPIU 打包 → 写入 TR/TM 寄存器 → 门铃寄存器 → UFS 设备
```

---

## 🎯 核心函数分析

### 1. 初始化流程

```c
// ufshcd.c - 主初始化函数
int ufshcd_init(struct ufs_hba *hba, void __iomem *mmio_base, unsigned int irq)
{
    // 1. 主机控制器复位
    ufshcd_hba_enable(hba);
    
    // 2. 查询设备描述符
    ufshcd_probe_hba(hba);
    
    // 3. 配置中断
    ufshcd_config_intr(hba);
    
    // 4. 创建 SCSI 主机
    ufshcd_scsi_init(hba);
    
    // 5. 添加 SCSI 设备
    ufshcd_scsi_add_devices(hba);
}
```

**初始化时序图**：
```
1. 硬件复位
   ↓
2. 读取版本寄存器 (UFS_VERSION)
   ↓
3. 配置控制器能力 (CONTROLLER_CAPABILITIES)
   ↓
4. 分配内存 (请求/响应描述符)
   ↓
5. 连接设备 (Link Startup)
   ↓
6. 查询描述符 (Device Descriptor)
   ↓
7. 配置 LUN (Unit Descriptor)
   ↓
8. 注册 SCSI 设备
```

---

### 2. 命令处理流程

```c
// ufshcd.c - SCSI 层回调
static int ufshcd_queuecommand(struct Scsi_Host *host, struct scsi_cmnd *cmd)
{
    struct ufs_hba *hba = shost_priv(host);
    int tag = cmd->request->tag;  // 获取命令标签 (0-31)
    struct ufshcd_lrb *lrbp = &hba->lrb[tag];
    
    // 1. 填充 LRB
    ufshcd_prep_lrb(hba, lrbp, cmd);
    
    // 2. 准备 UPIU (UFS Protocol Information Unit)
    ufshcd_prepare_req_desc_hdr(lrbp);
    
    // 3. 写入 TR 寄存器 (Transfer Request)
    ufshcd_writel(hba, trd, REG_UTP_TRANSFER_REQ_DOOR_BELL);
    
    // 4. 触发门铃
    ufshcd_send_command(hba, tag);
    
    return 0;  // 命令已提交，异步完成
}
```

**命令处理时序**：
```
SCSI 命令
   ↓
ufshcd_queuecommand()
   ↓
分配 LRB (tag 0-31)
   ↓
构建 UPIU (命令包)
   ↓
写入 TR 描述符
   ↓
触发门铃寄存器
   ↓
UFS 设备执行
   ↓
中断完成
   ↓
ufshcd_transfer_response()
   ↓
scsi_done() 通知上层
```

---

### 3. 电源管理

```c
// ufshcd.c - 电源状态转换
int ufshcd_system_suspend(struct ufs_hba *hba)
{
    // 1. 停止命令队列
    ufshcd_scsi_block_requests(hba);
    
    // 2. 进入 Hibern8 状态
    ufshcd_uic_hibern8_enter(hba);
    
    // 3. 关闭设备电源
    ufshcd_power_control(hba, false);
    
    return 0;
}

int ufshcd_system_resume(struct ufs_hba *hba)
{
    // 1. 开启设备电源
    ufshcd_power_control(hba, true);
    
    // 2. 退出 Hibern8
    ufshcd_uic_hibern8_exit(hba);
    
    // 3. 恢复命令队列
    ufshcd_scsi_unblock_requests(hba);
    
    return 0;
}
```

**电源状态机**：
```
┌─────────┐     idle      ┌───────┐
│ Active  │ ────────────→ │ Idle  │
│  (0)    │ ←──────────── │ (1)   │
└─────────┘     wakeup    └───────┘
    ↓ sleep                  ↓ sleep
┌─────────┐              ┌──────────┐
│  Sleep  │ ────────────→ │ PowerDn  │
│  (2)    │   deepsleep  │   (3)    │
└─────────┘              └──────────┘
```

---

### 4. 错误处理

```c
// ufshcd.c - 错误恢复
static void ufshcd_err_handling_work(struct work_struct *work)
{
    struct ufs_hba *hba = container_of(work, struct ufs_hba, eh_work);
    
    // 1. 检测错误类型
    if (hba->errors & UIC_ERROR) {
        // UIC 层错误（物理层/协议层）
        ufshcd_uic_error_recovery(hba);
    }
    
    if (hba->errors & DEVICE_ERROR) {
        // 设备错误
        ufshcd_device_reset(hba);
    }
    
    // 2. 重置控制器
    ufshcd_hba_stop(hba);
    ufshcd_hba_start(hba);
    
    // 3. 重新连接设备
    ufshcd_probe_hba(hba);
}
```

**错误类型**：
| 错误码 | 含义 | 恢复方法 |
|--------|------|---------|
| UIC_ERROR | UIC 层错误 | 重新训练链路 |
| DEVICE_ERROR | 设备错误 | 设备复位 |
| PA_INIT | 物理层初始化失败 | 重新初始化 |
| DL_INIT | 数据链路层失败 | 重新连接 |

---

## 📈 性能优化点

### 1. 多队列支持

```c
// 支持多个硬件队列
hba->nr_hw_queues = min(num_possible_cpus(), hba->nutrs);

// 每个 CPU 一个队列，减少锁竞争
for (i = 0; i < hba->nr_hw_queues; i++) {
    hba->uhq[i] = ufshcd_alloc_hw_queue(hba, i);
}
```

### 2. 自动门铃闪烁抑制

```c
// 避免频繁触发门铃寄存器
if (pending_commands > threshold) {
    // 批量提交
    ufshcd_writel(hba, doorbell, REG_UTP_TRANSFER_REQ_DOOR_BELL);
}
```

### 3. 散射聚集优化

```c
// 使用 DMA 映射，减少 CPU 拷贝
dma_map_sg(hba->dev, lrbp->sgl, nents, DMA_TO_DEVICE);
```

---

## 🔍 调试技巧

### 1. 启用调试日志

```bash
# 内核启动参数
echo 'file drivers/ufs/core/ufshcd.c +p' > /sys/kernel/debug/dynamic_debug/control

# 查看日志
dmesg -w | grep ufshcd
```

### 2. 查看设备信息

```bash
# 查看 UFS 设备
ls -l /sys/bus/platform/drivers/ufshcd/

# 查看电源状态
cat /sys/bus/platform/devices/*/ufs_sysfs/device_descriptor

# 查看性能统计
cat /sys/bus/platform/devices/*/ufs_sysfs/stats/*
```

### 3. 使用 ufs-utils

```bash
# 读取描述符
ufs read_desc /dev/ufs0 device

# 查询属性
ufs query_attr /dev/ufs0 read 0x0022

# 电源管理
ufs pm /dev/ufs0 get
```

---

## 📊 关键寄存器

| 寄存器 | 偏移 | 功能 |
|--------|------|------|
| UFS_VERSION | 0x00 | 版本寄存器 |
| CONTROLLER_CAPABILITIES | 0x04 | 控制器能力 |
| UTP_TRANSFER_REQ_LIST_BASE_L | 0x100 | 请求列表基址 |
| UTP_TRANSFER_REQ_DOOR_BELL | 0x140 | 门铃寄存器 |
| UTP_TRANSFER_REQ_COMPLETION | 0x160 | 完成寄存器 |
| UTP_TASK_REQ_LIST_BASE_L | 0x180 | 任务列表基址 |
| UTP_TASK_REQ_DOOR_BELL | 0x1C0 | 任务门铃 |

---

## 🎯 学习收获

**掌握程度**: 40% → 75%

**已理解**：
- ✅ 驱动整体架构
- ✅ 命令处理流程
- ✅ 电源管理机制
- ✅ 错误恢复流程
- ✅ 关键数据结构

**待深入**：
- [ ] 具体寄存器操作细节
- [ ] UPIU 协议包格式
- [ ] 多队列调度算法
- [ ] 与 M-PHY 的交互

---

**分析完成时间**: 2026-03-18 02:00  
**下一步**: 继续学习封装生产和车规应用
