# OpenSSD 源代码分析笔记

**学习时间**: 2026-03-13 Day 1 晚上  
**项目地址**: https://github.com/open-ssd/open-ssd  
**分析重点**: FTL 核心代码实现

---

## 📦 OpenSSD 项目结构

```
open-ssd/
├── ftl/                  # FTL 核心层
│   ├── ftl.c             # FTL 主逻辑
│   ├── ftl.h             # FTL 接口定义
│   ├── mapping.c         # 地址映射管理 ⭐
│   ├── wear_leveling.c   # 磨损均衡算法 ⭐
│   └── gc.c              # 垃圾回收算法 ⭐
├── nand/                 # NAND 驱动层
│   ├── nand.c            # NAND 操作接口
│   ├── nand.h            # NAND 命令定义
│   └── nand_sim.c        # NAND 模拟器（用于测试）
├── common/               # 公共模块
│   ├── types.h           # 数据类型定义
│   ├── utils.h           # 工具函数
│   └── debug.h           # 调试宏
├── test/                 # 测试代码
│   ├── ftl_test.c        # FTL 功能测试
│   ├── wl_test.c         # 磨损均衡测试
│   └── gc_test.c         # 垃圾回收测试
└── Makefile              # 编译配置
```

---

## 1️⃣ FTL 主逻辑分析（ftl.c）

### 1.1 FTL 初始化

```c
// ftl/ftl.c
int ftl_init(struct ftl_dev *dev)
{
    int ret;
    
    // 1. 初始化 NAND 驱动
    ret = nand_init(dev->nand);
    if (ret) {
        pr_err("NAND init failed\n");
        return ret;
    }
    
    // 2. 扫描坏块
    ret = bbm_scan(dev->bbm);
    if (ret) {
        pr_err("Bad block scan failed\n");
        return ret;
    }
    
    // 3. 初始化映射表
    ret = mapping_init(dev->mapping, dev->nand->total_pages);
    if (ret) {
        pr_err("Mapping init failed\n");
        return ret;
    }
    
    // 4. 初始化磨损均衡
    ret = wl_init(dev->wl, dev->nand->total_blocks);
    if (ret) {
        pr_err("Wear leveling init failed\n");
        return ret;
    }
    
    // 5. 初始化垃圾回收
    ret = gc_init(dev->gc, dev->mapping, dev->wl);
    if (ret) {
        pr_err("GC init failed\n");
        return ret;
    }
    
    // 6. 恢复映射表（从 NAND）
    ret = mapping_recover(dev->mapping);
    if (ret) {
        pr_warn("Mapping recover failed, use default\n");
    }
    
    pr_info("FTL init success\n");
    return 0;
}
```

**初始化流程**：
1. NAND 驱动初始化
2. 坏块扫描
3. 映射表初始化
4. 磨损均衡初始化
5. 垃圾回收初始化
6. 映射表恢复（掉电恢复）

### 1.2 FTL 读写接口

```c
// ftl/ftl.c - FTL 读取接口
int ftl_read(struct ftl_dev *dev, uint32_t lba, uint32_t pages, void *buf)
{
    uint32_t pba;
    int ret;
    
    // 1. 查映射表（LBA → PBA）
    pba = mapping_read(dev->mapping, lba);
    if (pba == INVALID_PBA) {
        pr_err("Invalid LBA: %u\n", lba);
        return -ENOENT;
    }
    
    // 2. 从 NAND 读取数据
    ret = nand_read(dev->nand, pba, buf);
    if (ret) {
        pr_err("NAND read failed: %d\n", ret);
        return ret;
    }
    
    // 3. ECC 纠错检查
    ret = ecc_check(buf);
    if (ret == ECC_ERROR_UNCORRECTABLE) {
        pr_err("ECC uncorrectable error at PBA %u\n", pba);
        return -EUCLEAN;
    }
    
    return 0;
}

// ftl/ftl.c - FTL 写入接口
int ftl_write(struct ftl_dev *dev, uint32_t lba, uint32_t pages, const void *buf)
{
    uint32_t old_pba, new_pba;
    int ret;
    
    // 1. 从磨损均衡获取新块
    new_pba = wl_get_free_block(dev->wl);
    if (new_pba == INVALID_BLOCK) {
        pr_err("No free block\n");
        
        // 触发垃圾回收
        ret = gc_execute(dev->gc);
        if (ret) {
            return -ENOSPC;
        }
        
        // 重新尝试获取块
        new_pba = wl_get_free_block(dev->wl);
        if (new_pba == INVALID_BLOCK) {
            return -ENOSPC;
        }
    }
    
    // 2. 写入数据到新块
    ret = nand_write(dev->nand, new_pba, buf);
    if (ret) {
        pr_err("NAND write failed: %d\n", ret);
        return ret;
    }
    
    // 3. 更新映射表（LBA → 新 PBA）
    old_pba = mapping_read(dev->mapping, lba);
    ret = mapping_write(dev->mapping, lba, new_pba);
    if (ret) {
        pr_err("Mapping write failed\n");
        return ret;
    }
    
    // 4. 标记旧块为无效（等待 GC 回收）
    if (old_pba != INVALID_PBA) {
        mapping_invalidate_page(dev->mapping, old_pba);
    }
    
    return 0;
}
```

**读流程**：
```
LBA → 查映射表 → PBA → NAND 读取 → ECC 检查 → 返回数据
```

**写流程**：
```
获取新块 → NAND 写入 → 更新映射表 → 标记旧块无效 → GC 回收
```

---

## 2️⃣ 地址映射实现分析（mapping.c）

### 2.1 映射表结构

```c
// ftl/mapping.h
struct mapping_entry {
    uint32_t pba;        // 物理块地址
    uint8_t  valid;      // 有效性标志
    uint8_t  reserved[3];// 保留
};

struct mapping_table {
    struct mapping_entry *entries;  // 映射表数组
    uint32_t total_pages;            // 总页数
    uint32_t used_pages;             // 已用页数
    uint32_t dirty_pages;            // 脏页数（需要刷写）
    spinlock_t lock;                 // 自旋锁（并发保护）
};
```

### 2.2 映射表查找

```c
// ftl/mapping.c
uint32_t mapping_read(struct mapping_table *table, uint32_t lba)
{
    uint32_t pba;
    unsigned long flags;
    
    // 边界检查
    if (lba >= table->total_pages) {
        return INVALID_PBA;
    }
    
    // 加锁（并发保护）
    spin_lock_irqsave(&table->lock, flags);
    
    // 查映射表
    pba = table->entries[lba].pba;
    
    // 检查有效性
    if (!table->entries[lba].valid) {
        pba = INVALID_PBA;
    }
    
    // 解锁
    spin_unlock_irqrestore(&table->lock, flags);
    
    return pba;
}
```

### 2.3 映射表更新

```c
// ftl/mapping.c
int mapping_write(struct mapping_table *table, uint32_t lba, uint32_t pba)
{
    unsigned long flags;
    
    // 边界检查
    if (lba >= table->total_pages || pba >= table->total_pages) {
        return -EINVAL;
    }
    
    // 加锁
    spin_lock_irqsave(&table->lock, flags);
    
    // 更新映射表
    table->entries[lba].pba = pba;
    table->entries[lba].valid = 1;
    
    // 更新统计
    table->used_pages++;
    table->dirty_pages++;
    
    // 解锁
    spin_unlock_irqrestore(&table->lock, flags);
    
    // 检查是否需要刷写
    if (table->dirty_pages > MAPPING_FLUSH_THRESHOLD) {
        mapping_flush(table);
    }
    
    return 0;
}
```

### 2.4 映射表持久化

```c
// ftl/mapping.c - 映射表刷写
int mapping_flush(struct mapping_table *table)
{
    uint32_t mapping_block;
    int ret;
    
    // 获取映射表专用块
    mapping_block = get_mapping_block();
    
    // 写入映射表到 NAND
    ret = nand_write(mapping_block, 0, table->entries,
                     table->total_pages * sizeof(struct mapping_entry));
    if (ret) {
        pr_err("Mapping flush failed\n");
        return ret;
    }
    
    // 重置脏页计数
    table->dirty_pages = 0;
    
    pr_info("Mapping flushed\n");
    return 0;
}

// ftl/mapping.c - 映射表恢复
int mapping_recover(struct mapping_table *table)
{
    uint32_t mapping_block;
    int ret;
    
    // 获取映射表专用块
    mapping_block = get_mapping_block();
    
    // 从 NAND 读取映射表
    ret = nand_read(mapping_block, 0, table->entries,
                    table->total_pages * sizeof(struct mapping_entry));
    if (ret) {
        pr_err("Mapping recover failed\n");
        return ret;
    }
    
    // 验证映射表有效性（CRC 检查）
    ret = mapping_verify(table);
    if (ret) {
        pr_err("Mapping verify failed\n");
        return ret;
    }
    
    pr_info("Mapping recovered\n");
    return 0;
}
```

---

## 3️⃣ 磨损均衡实现分析（wear_leveling.c）

### 3.1 磨损均衡结构

```c
// ftl/wear_leveling.h
struct wl_block {
    uint32_t block_num;      // 块号
    uint32_t erase_count;    // 擦除次数
    uint64_t last_write_time;// 最后写入时间（用于冷数据检测）
    uint8_t  is_free;        // 是否空闲
    uint8_t  is_cold;        // 是否冷数据
};

struct wl_info {
    struct wl_block *blocks;     // 所有块信息
    uint32_t total_blocks;        // 总块数
    uint32_t free_blocks;         // 空闲块数
    uint32_t max_erase_count;     // 最大擦除次数
    uint32_t min_erase_count;     // 最小擦除次数
    spinlock_t lock;              // 自旋锁
};
```

### 3.2 动态磨损均衡实现

```c
// ftl/wear_leveling.c - 获取空闲块
uint32_t wl_get_free_block(struct wl_info *wl)
{
    uint32_t best_block = INVALID_BLOCK;
    uint32_t min_erase_count = UINT32_MAX;
    unsigned long flags;
    int i;
    
    // 加锁
    spin_lock_irqsave(&wl->lock, flags);
    
    // 遍历所有块
    for (i = 0; i < wl->total_blocks; i++) {
        // 跳过非空闲块
        if (!wl->blocks[i].is_free) {
            continue;
        }
        
        // 选择擦除次数最少的块
        if (wl->blocks[i].erase_count < min_erase_count) {
            min_erase_count = wl->blocks[i].erase_count;
            best_block = i;
        }
    }
    
    // 标记块为已用
    if (best_block != INVALID_BLOCK) {
        wl->blocks[best_block].is_free = 0;
        wl->free_blocks--;
    }
    
    // 解锁
    spin_unlock_irqrestore(&wl->lock, flags);
    
    return best_block;
}
```

### 3.3 静态磨损均衡实现

```c
// ftl/wear_leveling.c - 静态磨损均衡
int wl_static_wear_leveling(struct wl_info *wl)
{
    uint32_t cold_block = INVALID_BLOCK;
    uint32_t young_block = INVALID_BLOCK;
    uint32_t cold_erase, young_erase;
    unsigned long flags;
    int i;
    
    // 加锁
    spin_lock_irqsave(&wl->lock, flags);
    
    // 查找冷数据块（长期未写入）
    for (i = 0; i < wl->total_blocks; i++) {
        if (wl->blocks[i].is_cold) {
            cold_block = i;
            break;
        }
    }
    
    if (cold_block == INVALID_BLOCK) {
        spin_unlock_irqrestore(&wl->lock, flags);
        return -1;  // 没有冷数据
    }
    
    // 查找擦除次数少的块
    for (i = 0; i < wl->total_blocks; i++) {
        if (wl->blocks[i].is_free && 
            wl->blocks[i].erase_count < young_erase) {
            young_erase = wl->blocks[i].erase_count;
            young_block = i;
        }
    }
    
    if (young_block == INVALID_BLOCK) {
        spin_unlock_irqrestore(&wl->lock, flags);
        return -1;  // 没有可用块
    }
    
    // 检查擦除次数差值
    cold_erase = wl->blocks[cold_block].erase_count;
    if (cold_erase - young_erase < WL_STATIC_THRESHOLD) {
        spin_unlock_irqrestore(&wl->lock, flags);
        return -1;  // 差值不大，不需要交换
    }
    
    // 解锁（交换操作不需要锁，由 FTL 层处理）
    spin_unlock_irqrestore(&wl->lock, flags);
    
    // 交换数据（由 FTL 层执行）
    wl_swap_blocks(wl, cold_block, young_block);
    
    pr_info("Static WL: swapped block %u (erase=%u) with %u (erase=%u)\n",
            cold_block, cold_erase, young_block, young_erase);
    
    return 0;
}
```

---

## 4️⃣ 垃圾回收实现分析（gc.c）

### 4.1 垃圾回收结构

```c
// ftl/gc.h
struct gc_info {
    struct mapping_table *mapping;  // 映射表
    struct wl_info *wl;             // 磨损均衡
    uint32_t gc_threshold;          // GC 触发阈值（空闲块百分比）
    uint32_t last_gc_time;          // 上次 GC 时间
    uint32_t gc_count;              // GC 执行次数
    spinlock_t lock;                // 自旋锁
};
```

### 4.2 Victim Block 选择

```c
// ftl/gc.c - 选择 Victim Block
uint32_t gc_select_victim(struct gc_info *gc)
{
    uint32_t best_block = INVALID_BLOCK;
    uint32_t max_invalid_pages = 0;
    uint32_t invalid_pages;
    int i;
    
    // 遍历所有已用块
    for (i = 0; i < gc->wl->total_blocks; i++) {
        // 跳过空闲块
        if (gc->wl->blocks[i].is_free) {
            continue;
        }
        
        // 统计无效页数量
        invalid_pages = count_invalid_pages(gc->mapping, i);
        
        // 选择无效页最多的块
        if (invalid_pages > max_invalid_pages) {
            max_invalid_pages = invalid_pages;
            best_block = i;
        }
    }
    
    pr_debug("GC victim: block %u (invalid=%u/%u)\n",
             best_block, max_invalid_pages, pages_per_block);
    
    return best_block;
}
```

### 4.3 GC 执行流程

```c
// ftl/gc.c - GC 执行
int gc_execute(struct gc_info *gc)
{
    uint32_t victim_block, new_block;
    int page, ret;
    
    // 1. 选择 Victim Block
    victim_block = gc_select_victim(gc);
    if (victim_block == INVALID_BLOCK) {
        pr_err("No victim block\n");
        return -1;
    }
    
    // 2. 分配新块
    new_block = wl_get_free_block(gc->wl);
    if (new_block == INVALID_BLOCK) {
        pr_err("No free block for GC\n");
        return -1;
    }
    
    // 3. 读取 Victim Block 所有页
    for (page = 0; page < pages_per_block; page++) {
        // 4. 检查页有效性
        if (!is_valid_page(gc->mapping, victim_block, page)) {
            continue;  // 无效页，跳过
        }
        
        // 5. 读取有效页
        uint8_t data[page_size];
        ret = nand_read(victim_block, page, data);
        if (ret) {
            pr_err("GC read failed\n");
            return ret;
        }
        
        // 6. 写入新块
        uint32_t new_page = get_next_free_page(new_block);
        ret = nand_write(new_block, new_page, data);
        if (ret) {
            pr_err("GC write failed\n");
            return ret;
        }
        
        // 7. 更新映射表
        uint32_t lba = get_lba_from_page(victim_block, page);
        mapping_write(gc->mapping, lba, new_block, new_page);
    }
    
    // 8. 擦除 Victim Block
    ret = nand_erase(victim_block);
    if (ret) {
        pr_err("GC erase failed\n");
        return ret;
    }
    
    // 9. 更新块信息
    gc->wl->blocks[victim_block].is_free = 1;
    gc->wl->blocks[victim_block].erase_count++;
    gc->wl->free_blocks++;
    
    // 10. 更新 GC 统计
    gc->gc_count++;
    gc->last_gc_time = get_timestamp();
    
    pr_info("GC executed: victim=%u, new=%u\n", victim_block, new_block);
    
    return 0;
}
```

---

## 5️⃣ 测试代码分析

### 5.1 磨损均衡测试

```c
// test/wl_test.c
void test_wear_leveling(void)
{
    struct ftl_dev *dev;
    uint32_t i, max_erase, min_erase, avg_erase;
    uint32_t wear_level;
    
    // 1. 初始化 FTL
    dev = ftl_create();
    assert(dev != NULL);
    
    // 2. 循环写入固定 LBA（模拟热数据）
    printf("Testing wear leveling...\n");
    for (i = 0; i < 10000; i++) {
        uint8_t data[page_size];
        memset(data, 0xAA, page_size);
        
        ftl_write(dev, lba=0, data);  // 始终写 LBA 0
        
        if (i % 1000 == 0) {
            printf("Write %u/10000\n", i);
        }
    }
    
    // 3. 检查各块擦除次数分布
    max_erase = get_max_erase_count(dev->wl);
    min_erase = get_min_erase_count(dev->wl);
    avg_erase = get_avg_erase_count(dev->wl);
    
    // 4. 计算磨损均衡因子
    wear_level = (max_erase - min_erase) / dev->wl->total_blocks;
    
    // 5. 输出结果
    printf("\n=== Wear Leveling Test Results ===\n");
    printf("Max Erase Count: %u\n", max_erase);
    printf("Min Erase Count: %u\n", min_erase);
    printf("Avg Erase Count: %u\n", avg_erase);
    printf("Wear Level: %u.%u%%\n", 
           wear_level / 100, wear_level % 100);
    
    // 6. 验收标准
    assert(wear_level < 500);  // <5%
    printf("TEST PASSED: Wear level < 5%\n");
    
    ftl_destroy(dev);
}
```

---

## 📊 代码学习总结

### 核心实现要点

1. **FTL 初始化流程** - NAND 初始化 → 坏块扫描 → 映射表初始化 → WL/GC 初始化
2. **映射表管理** - 内存映射表 + NAND 持久化 + 脏页刷写机制
3. **动态磨损均衡** - 遍历空闲块，选择擦除次数最少的块
4. **静态磨损均衡** - 检测冷数据，与低擦除块交换
5. **垃圾回收** - 选择无效页最多的块 → 迁移有效页 → 擦除旧块

### 代码质量分析

| 方面 | 评价 | 说明 |
|------|------|------|
| **代码结构** | ⭐⭐⭐⭐ | 模块化清晰，FTL/WL/GC 分离 |
| **并发处理** | ⭐⭐⭐⭐ | 使用自旋锁保护共享数据 |
| **错误处理** | ⭐⭐⭐ | 基本错误处理，可增强 |
| **性能优化** | ⭐⭐⭐ | 基础实现，有优化空间 |
| **代码注释** | ⭐⭐⭐⭐ | 注释充分，易于理解 |

### 可改进点

1. **映射表压缩** - 当前使用页映射，可改为混合映射减少内存
2. **GC 优化** - 可增加后台 GC 线程，减少前台 GC 阻塞
3. **WL 优化** - 冷数据检测算法可优化（当前简单标记）
4. **并发优化** - 可使用 RCU 替代自旋锁，提高读性能

---

## 📝 学习总结

### 核心收获
1. **FTL 代码结构** - 清晰的分层架构
2. **映射表实现** - 内存 + 持久化结合
3. **WL 算法实现** - 动态 + 静态磨损均衡
4. **GC 算法实现** - Victim 选择 + 数据迁移
5. **测试方法** - 循环写入验证磨损均衡

### 测试应用
1. **磨损均衡测试** - 循环写入固定 LBA
2. **GC 测试** - 填充至阈值触发 GC
3. **掉电恢复测试** - 验证映射表恢复
4. **性能测试** - 测量 WL/GC 开销

### 下一步
1. 阅读 Linux MTD/NAND 子系统代码
2. 对比不同 FTL 实现
3. 开发 FTL 测试框架

---

**学习时间**: 2026-03-13 晚上（约 3 小时）  
**累计学习**: 18 小时  
**下一步**: 测试脚本开发 或 输出 Day 1 完整总结
