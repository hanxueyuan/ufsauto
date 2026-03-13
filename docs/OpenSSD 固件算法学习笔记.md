# OpenSSD 开源项目学习笔记

**学习时间**: 2026-03-13 Day 1 下午  
**项目地址**: https://github.com/open-ssd/open-ssd  
**学习目标**: 理解 FTL 核心算法实现（WL/GC/坏块管理）

---

## 📦 OpenSSD 项目概览

### 项目结构
```
open-ssd/
├── ftl/              # FTL 核心层
│   ├── ftl.c         # FTL 主逻辑
│   ├── ftl.h         # FTL 接口定义
│   ├── mapping.c     # 地址映射管理
│   ├── wear_leveling.c # 磨损均衡算法
│   └── gc.c          # 垃圾回收算法
├── nand/             # NAND 驱动层
│   ├── nand.c        # NAND 操作接口
│   └── nand.h        # NAND 命令定义
├── common/           # 公共模块
│   ├── types.h       # 数据类型定义
│   └── utils.h       # 工具函数
└── test/             # 测试代码
    └── ftl_test.c    # FTL 功能测试
```

---

## 1️⃣ FTL 核心架构

### 1.1 FTL 层次结构

```
┌─────────────────────────────────────────────────────────┐
│                    Host Interface                        │
│                    (SCSI/UFS 命令)                        │
├─────────────────────────────────────────────────────────┤
│                      FTL Layer                           │
│  ┌─────────────┬─────────────┬─────────────────────┐   │
│  │ 地址映射     │ 磨损均衡     │ 垃圾回收             │   │
│  │ Mapping     │ Wear Level  │ Garbage Collection  │   │
│  └─────────────┴─────────────┴─────────────────────┘   │
├─────────────────────────────────────────────────────────┤
│                    NAND Driver                           │
│                    (读写擦除操作)                          │
├─────────────────────────────────────────────────────────┤
│                    NAND Flash                            │
│                    (物理存储介质)                          │
└─────────────────────────────────────────────────────────┘
```

### 1.2 FTL 主要功能

| 功能模块 | 职责 | 关键算法 |
|----------|------|----------|
| **地址映射** | LBA→PBA 转换 | 页映射/块映射/混合映射 |
| **磨损均衡** | 平衡各块擦除次数 | 动态 WL/静态 WL |
| **垃圾回收** | 回收无效页空间 | 前台 GC/后台 GC |
| **坏块管理** | 管理坏块 | 工厂坏块/生长坏块 |
| **ECC 纠错** | 数据纠错 | BCH/LDPC |

---

## 2️⃣ 地址映射算法（Mapping）

### 2.1 映射类型对比

| 映射类型 | 粒度 | 优点 | 缺点 | 适用场景 |
|----------|------|------|------|----------|
| **页映射** | Page | 随机写入性能好 | 映射表大，内存占用高 | 高性能 SSD |
| **块映射** | Block | 映射表小，内存占用低 | 随机写入性能差 | 低成本 SSD |
| **混合映射** | Page+Block | 平衡性能和内存 | 算法复杂 | 主流方案 |

### 2.2 OpenSSD 映射实现

**页映射结构**：
```c
// ftl/mapping.h
typedef struct {
    uint32_t lba;    // 逻辑块地址
    uint32_t pba;    // 物理块地址
    uint8_t  valid;  // 有效性标志
} mapping_entry_t;

typedef struct {
    mapping_entry_t *entries;  // 映射表
    uint32_t total_pages;       // 总页数
    uint32_t used_pages;        // 已用页数
} mapping_table_t;
```

**映射表查找**：
```c
// ftl/mapping.c
uint32_t mapping_read(mapping_table_t *table, uint32_t lba)
{
    // 边界检查
    if (lba >= table->total_pages) {
        return INVALID_PBA;
    }
    
    // 查找映射表
    mapping_entry_t *entry = &table->entries[lba];
    
    // 检查有效性
    if (entry->valid) {
        return entry->pba;
    } else {
        return INVALID_PBA;
    }
}

void mapping_write(mapping_table_t *table, uint32_t lba, uint32_t pba)
{
    // 更新映射表
    mapping_entry_t *entry = &table->entries[lba];
    entry->pba = pba;
    entry->valid = 1;
    
    // 标记旧 PBA 为无效（需要 GC 回收）
    // ...
}
```

### 2.3 映射表持久化

**问题**: 映射表存储在内存中，掉电会丢失

**解决方案**:
1. **定期刷写到 NAND** - 每隔 N 次写入同步一次
2. **日志式更新** - 记录映射表变更日志
3. **恢复机制** - 上电后从 NAND 恢复映射表

**OpenSSD 实现**：
```c
// ftl/mapping.c
int mapping_flush(mapping_table_t *table)
{
    // 将映射表写入 NAND 特定区域
    uint32_t mapping_block = get_mapping_block();
    
    // 写入映射表
    nand_write(mapping_block, 0, table->entries, 
               table->total_pages * sizeof(mapping_entry_t));
    
    return 0;
}

int mapping_recover(mapping_table_t *table)
{
    // 从 NAND 读取映射表
    uint32_t mapping_block = get_mapping_block();
    
    // 读取映射表
    nand_read(mapping_block, 0, table->entries,
              table->total_pages * sizeof(mapping_entry_t));
    
    return 0;
}
```

---

## 3️⃣ 磨损均衡算法（Wear Leveling）

### 3.1 磨损均衡原理

**问题**: NAND Flash 有 P/E Cycle 限制（SLC: 10 万次，MLC: 3 千次，TLC: 1 千次）

**目标**: 让所有块的擦除次数均匀分布，避免个别块过早损坏

**磨损均衡因子**：
```
Wear Level = (Max_Erase_Count - Min_Erase_Count) / Total_Blocks
理想值：< 5%
```

### 3.2 动态磨损均衡（Dynamic WL）

**原理**: 写入数据时，优先选择擦除次数少的块

**算法流程**：
```
1. 收到写入请求
2. 从空闲块列表中选择
3. 按擦除次数排序
4. 选择擦除次数最少的块
5. 写入数据
6. 更新块的擦除计数
```

**OpenSSD 实现**：
```c
// ftl/wear_leveling.c
uint32_t wl_get_free_block(wear_level_t *wl)
{
    uint32_t best_block = INVALID_BLOCK;
    uint32_t min_erase_count = UINT32_MAX;
    
    // 遍历空闲块列表
    for (int i = 0; i < wl->free_block_count; i++) {
        uint32_t block = wl->free_blocks[i];
        uint32_t erase_count = get_erase_count(block);
        
        // 选择擦除次数最少的块
        if (erase_count < min_erase_count) {
            min_erase_count = erase_count;
            best_block = block;
        }
    }
    
    return best_block;
}
```

### 3.3 静态磨损均衡（Static WL）

**问题**: 动态 WL 无法移动冷数据（长期不更新的数据）

**原理**: 定期检查冷数据块，将其与擦除次数少的块交换

**算法流程**：
```
1. 定期检查（如每 1000 次写入）
2. 查找冷数据块（长期未更新）
3. 查找擦除次数少的块
4. 如果差值超过阈值，交换数据
5. 更新映射表
```

**OpenSSD 实现**：
```c
// ftl/wear_leveling.c
int wl_static_wear_leveling(wear_level_t *wl)
{
    // 查找冷数据块
    uint32_t cold_block = find_cold_block();
    if (cold_block == INVALID_BLOCK) {
        return -1;
    }
    
    // 查找擦除次数少的块
    uint32_t young_block = find_young_block();
    if (young_block == INVALID_BLOCK) {
        return -1;
    }
    
    // 检查差值是否超过阈值
    uint32_t cold_erase = get_erase_count(cold_block);
    uint32_t young_erase = get_erase_count(young_block);
    
    if (cold_erase - young_erase < WL_THRESHOLD) {
        return -1;  // 差值不大，不需要交换
    }
    
    // 交换数据
    swap_blocks(cold_block, young_block);
    
    // 更新映射表
    mapping_update_for_swap(cold_block, young_block);
    
    return 0;
}
```

### 3.4 磨损均衡测试

**测试用例设计**：
```c
// test/wl_test.c
void test_wear_leveling()
{
    // 1. 初始化 FTL
    ftl_init();
    
    // 2. 循环写入固定 LBA（模拟热数据）
    for (int i = 0; i < 10000; i++) {
        ftl_write(lba=0, data);  // 始终写 LBA 0
    }
    
    // 3. 检查各块擦除次数分布
    uint32_t max_erase = get_max_erase_count();
    uint32_t min_erase = get_min_erase_count();
    uint32_t avg_erase = get_avg_erase_count();
    
    // 4. 验证磨损均衡效果
    uint32_t wear_level = (max_erase - min_erase) / total_blocks;
    
    printf("Max Erase: %u\n", max_erase);
    printf("Min Erase: %u\n", min_erase);
    printf("Avg Erase: %u\n", avg_erase);
    printf("Wear Level: %u%%\n", wear_level * 100);
    
    // 5. 验收标准：wear_level < 5%
    assert(wear_level < 0.05);
}
```

---

## 4️⃣ 垃圾回收算法（Garbage Collection）

### 4.1 GC 原理

**问题**: NAND Flash 不能原地更新，必须先擦除再写入

**GC 触发条件**:
1. **空闲块不足** - 空闲块低于阈值（如 10%）
2. **前台 GC** - 写入时没有可用块
3. **后台 GC** - 空闲时后台回收

### 4.2 GC 算法流程

```
1. 选择 victim block（待回收块）
2. 读取 block 中的所有页
3. 检查每页有效性（查映射表）
4. 将有效页复制到新 block
5. 更新映射表（指向新位置）
6. 擦除 victim block
7. 加入空闲块列表
```

### 4.3 OpenSSD GC 实现

**Victim Block 选择**：
```c
// ftl/gc.c
uint32_t gc_select_victim_block(gc_t *gc)
{
    uint32_t best_block = INVALID_BLOCK;
    uint32_t max_invalid_pages = 0;
    
    // 遍历所有已用块
    for (int i = 0; i < gc->total_blocks; i++) {
        uint32_t block = gc->blocks[i];
        
        // 跳过空闲块
        if (is_free_block(block)) {
            continue;
        }
        
        // 统计无效页数量
        uint32_t invalid_pages = count_invalid_pages(block);
        
        // 选择无效页最多的块（回收效率最高）
        if (invalid_pages > max_invalid_pages) {
            max_invalid_pages = invalid_pages;
            best_block = block;
        }
    }
    
    return best_block;
}
```

**GC 执行**：
```c
// ftl/gc.c
int gc_execute(gc_t *gc, uint32_t victim_block)
{
    // 1. 分配新 block
    uint32_t new_block = wl_get_free_block(&gc->wl);
    if (new_block == INVALID_BLOCK) {
        return -1;  // 没有可用块
    }
    
    // 2. 读取 victim block 所有页
    for (int page = 0; page < pages_per_block; page++) {
        // 3. 检查页有效性
        if (!is_valid_page(victim_block, page)) {
            continue;  // 无效页，跳过
        }
        
        // 4. 读取有效页
        uint8_t data[page_size];
        nand_read(victim_block, page, data);
        
        // 5. 写入新 block
        uint32_t new_page = get_next_free_page(new_block);
        nand_write(new_block, new_page, data);
        
        // 6. 更新映射表
        uint32_t lba = get_lba_from_page(victim_block, page);
        mapping_write(&gc->mapping, lba, new_block, new_page);
    }
    
    // 7. 擦除 victim block
    nand_erase(victim_block);
    
    // 8. 加入空闲块列表
    add_to_free_list(victim_block);
    
    return 0;
}
```

### 4.4 GC 性能优化

**问题**: GC 会影响写入性能（尤其是前台 GC）

**优化策略**：
1. **后台 GC** - 空闲时提前回收
2. **Over-Provisioning** - 预留更多空闲块
3. **多 GC 线程** - 并行 GC
4. **GC 阈值调优** - 平衡性能和寿命

---

## 5️⃣ 坏块管理（Bad Block Management）

### 5.1 坏块类型

| 类型 | 产生时间 | 处理方法 |
|------|----------|----------|
| **工厂坏块** | 生产时产生 | 出厂时标记，跳过使用 |
| **生长坏块** | 使用过程中产生 | 动态标记，数据迁移 |

### 5.2 坏块管理策略

**工厂坏块处理**：
```c
// nand/bbm.c
int bbm_scan_factory_bad_blocks(bbm_t *bbm)
{
    // 扫描所有块
    for (int block = 0; block < total_blocks; block++) {
        // 读取坏块标记（通常在 block 的第 1 页或最后 1 页）
        uint8_t oob_data[oob_size];
        nand_read_oob(block, 0, oob_data);
        
        // 检查坏块标记
        if (is_bad_block_mark(oob_data)) {
            // 标记为坏块
            bbm_mark_bad(bbm, block);
            printf("Factory bad block: %u\n", block);
        }
    }
    
    return 0;
}
```

**生长坏块处理**：
```c
// nand/bbm.c
int bbm_handle_runtime_bad_block(bbm_t *bbm, uint32_t block)
{
    // 1. 标记为坏块
    bbm_mark_bad(bbm, block);
    
    // 2. 写入坏块标记到 NAND
    uint8_t oob_data[oob_size] = {BAD_BLOCK_MARK};
    nand_write_oob(block, 0, oob_data);
    
    // 3. 迁移数据（如果有有效数据）
    migrate_data_from_block(block);
    
    // 4. 更新映射表
    mapping_update_for_bad_block(block);
    
    return 0;
}
```

---

## 📊 算法性能对比

### 映射算法对比

| 算法 | 内存占用 | 随机写入 | 顺序写入 | 适用场景 |
|------|----------|----------|----------|----------|
| 页映射 | 高 | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | 高性能 SSD |
| 块映射 | 低 | ⭐⭐ | ⭐⭐⭐⭐ | 低成本 SSD |
| 混合映射 | 中 | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | 主流方案 |

### 磨损均衡算法对比

| 算法 | 复杂度 | 均衡效果 | 性能影响 | 适用场景 |
|------|--------|----------|----------|----------|
| 动态 WL | 低 | ⭐⭐⭐ | 小 | 所有 SSD |
| 静态 WL | 高 | ⭐⭐⭐⭐⭐ | 中 | 长寿命 SSD |

### GC 算法对比

| 策略 | 触发时机 | 性能影响 | 实现复杂度 |
|------|----------|----------|------------|
| 前台 GC | 写入时无空闲块 | 大（阻塞写入） | 低 |
| 后台 GC | 空闲时提前回收 | 小 | 中 |
| 混合 GC | 前台 + 后台结合 | 中 | 高 |

---

## 📝 学习总结

### 核心要点
1. **FTL 三大核心算法**: 地址映射、磨损均衡、垃圾回收
2. **映射类型**: 页映射（高性能）、块映射（低成本）、混合映射（平衡）
3. **磨损均衡**: 动态 WL（必选）+ 静态 WL（可选，提升寿命）
4. **垃圾回收**: 前台 GC（紧急）+ 后台 GC（优化性能）
5. **坏块管理**: 工厂坏块（出厂标记）+ 生长坏块（动态处理）

### 测试应用
1. 磨损均衡测试 - 循环写入固定 LBA，验证擦除次数分布
2. GC 性能测试 - 测量 GC 触发频率和对写入性能的影响
3. 坏块管理测试 - 模拟坏块产生，验证数据迁移和映射更新
4. 掉电恢复测试 - 验证映射表持久化和恢复机制

### 待深入学习
1. OpenSSD 完整代码阅读
2. 实际 FTL 性能测试
3. 不同 FTL 算法对比实验
4. 商用 SSD FTL 逆向分析

---

**学习时间**: 2026-03-13 下午（约 3 小时）  
**下一步**: 阅读 OpenSSD 完整源代码，设计 FTL 测试用例
