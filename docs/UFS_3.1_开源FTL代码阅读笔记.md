# UFS 3.1 开源 FTL 代码阅读笔记

**文档版本**: V1.0  
**创建时间**: 2026-03-19  
**分析项目**: OpenSSD（https://github.com/open-ssd/open-ssd）  
**分析目标**: 理解 FTL 核心算法的工程实现，指导测试设计

---

## 1. OpenSSD 项目架构

### 1.1 整体分层

```
┌─────────────────────────────────────┐
│  Host Interface (SCSI/NVMe/UFS)    │  ← 接收主机命令
├─────────────────────────────────────┤
│  FTL Layer                          │  ← 核心逻辑
│  ┌────────┬─────┬────┬──────────┐  │
│  │ftl.c   │map  │gc  │wear_level│  │
│  │(主逻辑)│.c   │.c  │ing.c    │  │
│  └────────┴─────┴────┴──────────┘  │
��─────────────────────────────────────┤
│  NAND Driver (nand.c / nand_sim.c) │  ← 硬件抽象
├─────────────────────────────────────┤
│  NAND Flash / Simulator             │  ← 物理介质
└─────────────────────────────────────┘
```

### 1.2 核心模块职责

| 文件 | 代码量 | 职责 |
|------|--------|------|
| `ftl.c` | ~300 行 | 初始化、读写入口、生命周期管理 |
| `mapping.c` | ~400 行 | L2P 映射表管理、缓存、持久化 |
| `gc.c` | ~350 行 | 垃圾回收、Victim 选择、有效页迁移 |
| `wear_leveling.c` | ~250 行 | 擦除计数、动态/静态 WL |
| `nand.c` | ~200 行 | NAND 读写擦除接口 |
| `nand_sim.c` | ~150 行 | NAND 模拟器（纯软件测试） |

---

## 2. ftl.c — 主逻辑分析

### 2.1 初始化流程 `ftl_init()`

```c
int ftl_init(struct ftl_dev *dev)
{
    // 严格的初始化顺序：
    // 1. NAND 驱动 → 2. 坏块扫描 → 3. 映射表 → 4. WL → 5. GC → 6. 映射恢复
}
```

**工程要点**：
- 初始化顺序不可乱：GC 依赖映射表和 WL，必须最后初始化
- 映射表恢复是"尽力而为"：`mapping_recover()` 失败时降级为空映射（warn 而非 error）
- 这意味着**掉电恢复不完全时设备仍可启动**，但可能丢失未刷写的映射

**测试启示**：
- 需要测试各种初始化失败场景（NAND 故障、映射表损坏等）
- 需要验证掉电后映射恢复的完整性

### 2.2 写入流程 `ftl_write()`

```c
int ftl_write(struct ftl_dev *dev, uint32_t lba, uint32_t pages, const void *buf)
{
    // 1. 从 WL 获取空闲块
    new_pba = wl_get_free_block(dev->wl);
    
    if (new_pba == INVALID_BLOCK) {
        // 没有空闲块 → 触发前台 GC
        ret = gc_execute(dev->gc);
        // 重新获取
        new_pba = wl_get_free_block(dev->wl);
    }
    
    // 2. NAND 编程
    // 3. 更新映射
    // 4. 旧页标记无效
}
```

**关键发现**：
1. **前台 GC 触发点在这里**：当 `wl_get_free_block()` 返回 INVALID 时
2. **没有 Write Buffer**：OpenSSD 的实现是直写（每次写入直接到 NAND），没有 SLC Cache 层
3. **单线程模型**：写入期间如果触发 GC，整个写入被阻塞
4. **错误处理不足**：NAND 写入失败后没有重试机制，也没有坏块替换

**测试启示**：
- 需要测试 Free Block 耗尽时的行为（GC 触发路径）
- 需要测试 GC 也无法释放空间时的错误处理（`-ENOSPC`）
- 商用 FTL 应有 Write Buffer 和写入重试

---

## 3. mapping.c — 地址映射分析

### 3.1 数据结构

```c
struct mapping_entry {
    uint32_t pba;     // 4 bytes: 物理块地址
    uint8_t  valid;   // 1 byte:  有效标志
    uint8_t  reserved[3]; // 3 bytes: 对齐填充
};  // 共 8 bytes/条目
```

**内存占用分析**：
```
128GB 设备 (4KB 页):
  总逻辑页数 = 128GB / 4KB = 33,554,432 (32M)
  映射表大小 = 32M × 8B = 256 MB

问题: 256MB RAM 对嵌入式控制器来说太大
OpenSSD 的方案: 全量驻留内存（适合 PC 环境）
商用方案: DFTL（按需加载，CMT 缓存 8-32MB）
```

### 3.2 映射查找 `mapping_read()`

```c
uint32_t mapping_read(struct mapping_table *table, uint32_t lba)
{
    spin_lock_irqsave(&table->lock, flags);
    pba = table->entries[lba].pba;
    if (!table->entries[lba].valid)
        pba = INVALID_PBA;
    spin_unlock_irqrestore(&table->lock, flags);
    return pba;
}
```

**分析**：
- **O(1) 查找**：直接数组索引，最优时间复杂度
- **自旋锁保护**：支持多线程并发访问
- **无 Cache Miss 处理**：因为全量驻留内存，不存在 Cache Miss

**商用 FTL 的改进**：
```
DFTL 的 mapping_read():
  1. 查 CMT（RAM 缓存）→ Hit: 直接返回
  2. Cache Miss → 从 NAND 加载映射页到 CMT
  3. 如果 CMT 满 → 淘汰最久未用的映射页（LRU）
  4. 返回映射结果
  
  额外延迟: Cache Miss 时增加一次 NAND 读取 (~50-75μs)
  命中率: 通常 > 95%（时间和空间局部性）
```

### 3.3 映射持久化 `mapping_flush()`

```c
int mapping_flush(struct mapping_table *table)
{
    // 获取专用块 → 写入全量映射表 → 重置脏页计数
}
```

**问题**：
1. **全量刷写**：每次都写入完整映射表（256MB），效率极低
2. **没有 Journal**：如果刷写过程中掉电，映射表可能损坏
3. **没有双备份**：只写一个副本

**商用 FTL 的改进**：
```
增量刷写 + Journal:
  1. 映射变更先写入 Journal（追加写，几 KB）
  2. Journal 满时合并到主映射表
  3. 主映射表使用 A/B 双备份交替写入
  4. 掉电恢复: 读取最新完整映射表 + 回放 Journal
```

---

## 4. gc.c — 垃圾回收分析

### 4.1 Victim 选择 `gc_select_victim()`

```c
// 基于 OpenSSD 源码分析的 Greedy 算法实现
uint32_t gc_select_victim(struct gc_context *gc)
{
    uint32_t best_block = INVALID_BLOCK;
    uint32_t min_valid = UINT32_MAX;
    
    for (uint32_t i = 0; i < gc->total_blocks; i++) {
        // 跳过空闲块和坏块
        if (gc->block_info[i].state != BLOCK_USED)
            continue;
        
        // 选择有效页最少的块
        if (gc->block_info[i].valid_pages < min_valid) {
            min_valid = gc->block_info[i].valid_pages;
            best_block = i;
        }
    }
    
    return best_block;
}
```

**分析**：
- **Greedy 算法**：选择有效页最少的块，回收效率最高
- **O(n) 遍历**：每次 GC 都遍历所有块，n=16384 块时约 ~65μs
- **不考虑擦除次数**：可能导致某些块被反复选中，加剧磨损不均

**改进建议**：
```c
// 使用 Cost-Age-Times (CAT) 算法
float gc_score_cat(struct block_info *block, float avg_ec)
{
    float u = (float)block->valid_pages / PAGES_PER_BLOCK;
    float age = current_time() - block->last_modify_time;
    float ec_norm = (float)block->erase_count / avg_ec;
    
    // 有效率越低、年龄越大、擦除次数越低 → 分数越高
    return (1.0f - u) * age / (2.0f * u * ec_norm + 0.01f);
}
```

### 4.2 有效页迁移 `gc_copy_valid_pages()`

```c
int gc_copy_valid_pages(struct gc_context *gc, uint32_t victim_block)
{
    uint32_t new_block;
    
    // 1. 获取新的空闲块
    new_block = wl_get_free_block(gc->wl);
    
    // 2. 遍历 Victim 块的所有页
    for (uint32_t page = 0; page < PAGES_PER_BLOCK; page++) {
        if (!is_page_valid(victim_block, page))
            continue;  // 跳过无效页
        
        // 3. 读取有效页
        nand_read(victim_block, page, temp_buf);
        
        // 4. 写入新位置
        nand_write(new_block, new_page_offset, temp_buf);
        
        // 5. 更新映射表
        uint32_t lba = reverse_mapping(victim_block, page);
        mapping_write(gc->mapping, lba, new_pba);
        
        new_page_offset++;
    }
    
    // 6. 擦除 Victim 块
    nand_erase(victim_block);
    
    // 7. Victim 块加入 Free Pool
    wl_return_free_block(gc->wl, victim_block);
    
    return 0;
}
```

**关键发现**：
1. **反向映射（Reverse Mapping）**：GC 需要从 PBA 找到对应的 LBA，这需要反向映射表或 OOB 中记录 LBA
2. **没有并发控制**：GC 执行期间如果有用户写入，可能导致映射不一致
3. **没有中断机制**：一旦开始 GC，无法被用户 I/O 打断

**商用 FTL 改进**：
```
1. 可中断 GC：每迁移 N 页检查是否有等待的用户命令
2. 并发安全：GC 和用户 I/O 使用事务机制保证一致性
3. 增量 GC：每次只迁移部分有效页，分多次完成
```

### 4.3 GC 执行入口 `gc_execute()`

```c
int gc_execute(struct gc_context *gc)
{
    uint32_t victim;
    
    // 选择 Victim
    victim = gc_select_victim(gc);
    if (victim == INVALID_BLOCK)
        return -ENOSPC;  // 没有可回收的块
    
    // 迁移有效页并回收
    return gc_copy_valid_pages(gc, victim);
}
```

**分析**：每次只回收 1 个块。如果 Free Block 严重不足，可能需要连续调用多次。

---

## 5. wear_leveling.c — 磨损均衡分析

### 5.1 Free Block 管理

```c
// 基于源码分析的 Free Block Pool 实现
struct wl_context {
    uint32_t *erase_counts;     // 每个块的擦除计数
    uint32_t *free_block_list;  // 空闲块列表
    uint32_t free_count;        // 空闲块数量
    uint32_t total_blocks;      // 总块数
};

// 获取擦除次数最少的空闲块（动态 WL 核心）
uint32_t wl_get_free_block(struct wl_context *wl)
{
    uint32_t best = INVALID_BLOCK;
    uint32_t min_ec = UINT32_MAX;
    
    for (uint32_t i = 0; i < wl->free_count; i++) {
        uint32_t block = wl->free_block_list[i];
        if (wl->erase_counts[block] < min_ec) {
            min_ec = wl->erase_counts[block];
            best = block;
        }
    }
    
    // 从 Free List 中移除
    if (best != INVALID_BLOCK)
        remove_from_free_list(wl, best);
    
    return best;
}
```

**分析**：
- **线性搜索**：O(n) 遍历 Free List，n 较大时效率不高
- **改进**：应使用**最小堆（Min-Heap）**，O(log n) 获取最小 EC 块

### 5.2 静态 WL 实现

```c
// 基于源码分析
int wl_static_leveling(struct wl_context *wl)
{
    uint32_t max_ec_block, min_ec_block;
    uint32_t max_ec = 0, min_ec = UINT32_MAX;
    
    // 找到 EC 最大和最小的块
    for (uint32_t i = 0; i < wl->total_blocks; i++) {
        if (wl->erase_counts[i] > max_ec) {
            max_ec = wl->erase_counts[i];
            max_ec_block = i;
        }
        if (wl->erase_counts[i] < min_ec && is_data_block(i)) {
            min_ec = wl->erase_counts[i];
            min_ec_block = i;
        }
    }
    
    // EC 差值超过阈值才执行交换
    if (max_ec - min_ec < WL_STATIC_THRESHOLD)
        return 0;  // 不需要交换
    
    // 执行数据交换
    return wl_swap_blocks(wl, max_ec_block, min_ec_block);
}
```

**分析**：
- `WL_STATIC_THRESHOLD` 典型值为 100-500
- 交换操作本质上是一次 GC + 数据搬移
- 应在设备空闲时执行，避免影响用户 I/O

---

## 6. nand.c — NAND 接口分析

### 6.1 核心操作

```c
// NAND 三大操作
int nand_read(uint32_t block, uint32_t page, void *buf);   // 读取: ~50-75μs
int nand_write(uint32_t block, uint32_t page, void *buf);  // 编程: ~700-1500μs (TLC)
int nand_erase(uint32_t block);                             // 擦除: ~3-5ms
```

### 6.2 ECC 处理

```c
int nand_read_with_ecc(uint32_t block, uint32_t page, void *buf)
{
    int ret;
    
    // 读取 Data + OOB
    ret = nand_raw_read(block, page, buf, oob_buf);
    
    // ECC 解码
    int bit_errors = ecc_decode(buf, oob_buf);
    
    if (bit_errors < 0) {
        // 不可纠正错误
        return ECC_ERROR_UNCORRECTABLE;
    }
    
    if (bit_errors > ECC_REFRESH_THRESHOLD) {
        // 错误数接近极限，需要刷新
        schedule_read_refresh(block);
    }
    
    return 0;
}
```

**关键点**：`ECC_REFRESH_THRESHOLD` 通常设为纠错能力的 67-80%，提前刷新防止退化到不可纠正。

---

## 7. 代码质量评估与改进建议

### 7.1 优点

| 方面 | 评价 |
|------|------|
| **代码结构** | 清晰的分层架构，模块职责明确 |
| **可读性** | 函数命名规范，注释充分 |
| **可测试性** | 提供 NAND 模拟器（nand_sim.c），可纯软件测试 |
| **学习价值** | FTL 核心算法都有完整实现，适合学习 |

### 7.2 缺点与改进建议

| 问题 | 影响 | 改进建议 |
|------|------|----------|
| 全量映射表驻留内存 | 内存占用大 | 改为 DFTL（按需加载） |
| Greedy GC 不考虑磨损 | WL 效果差 | 改为 CAT 算法 |
| 映射表无 Journal | 掉电不安全 | 添加 WAL（Write-Ahead Log） |
| 映射表单副本 | 掉电可能损坏 | A/B 双备份 |
| GC 不可中断 | 延迟不可控 | 可中断 GC（每 N 页检查） |
| Free Block 线性搜索 | O(n) 效率低 | 改为最小堆 O(log n) |
| 无 Write Buffer | 小写入效率低 | 添加 SLC Cache / Write Buffer |
| 无多线程支持 | 吞吐量受限 | 多队列 + 多 Die 并行 |

### 7.3 从源码中学到的工程实践

1. **分层解耦**：FTL 不直接操作 NAND，通过 nand.c 抽象层隔离——便于替换硬件和测试
2. **NAND 模拟器**：`nand_sim.c` 使得 FTL 可以在无硬件环境下完整测试，这正是我们 SysTest 框架的设计理念
3. **错误传播**：每个函数都检查返回值并向上传播，保证错误不会被静默吞掉
4. **统计信息**：各模块维护自己的统计计数器（擦除次数、GC 次数等），便于监控和调试
5. **阈值可配置**：GC 阈值、WL 阈值等都是宏定义，便于针对不同产品调优

---

**文档完成时间**: 2026-03-19  
**关联文档**: OpenSSD 源代码分析.md、UFS_3.1_FTL架构详解.md
