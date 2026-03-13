# UFS/SSD 固件算法学习资源

## 📚 技术文章与博客

### 1. AnandTech - SSD 技术解析
- **链接**: https://www.anandtech.com/show/tag/ssd
- **重点内容**:
  - SSD 控制器架构解析
  - FTL 算法工作原理
  - 性能测试方法论

### 2. Tom's Hardware - SSD 深度评测
- **链接**: https://www.tomshardware.com/reviews/ssd
- **重点内容**:
  - 不同厂商固件策略对比
  - 缓存管理技术
  - 功耗优化技术

### 3. StorageReview
- **链接**: https://www.storagereview.com/
- **重点内容**:
  - 企业级 SSD 评测
  - 性能分析方法

---

## 📖 学术论文与会议

### 1. FAST 会议（USENIX Conference on File and Storage Technologies）
- **链接**: https://www.usenix.org/conference/fast
- **重点论文**:
  - "FTL 算法综述"
  - "3D NAND 可靠性研究"
  - "QLC/TLC 闪存管理"

### 2. IEEE 论文
- **搜索关键词**: "FTL algorithm survey", "SSD wear leveling", "NAND flash management"
- **推荐论文**:
  - "A Survey on Flash Translation Layer Techniques"
  - "Wear Leveling in SSDs: A Comprehensive Study"

---

## 💻 开源项目（GitHub）

### 1. Open-SSD 项目
- **链接**: https://github.com/open-ssd
- **内容**: 开源 SSD 固件实现
- **学习重点**:
  - FTL 核心算法
  - 坏块管理
  - 磨损均衡实现

### 2. Linux FTL 实现
- **链接**: https://github.com/torvalds/linux/tree/master/drivers/mtd/nand
- **内容**: Linux 内核 FTL 驱动
- **学习重点**:
  - NAND 驱动架构
  - ECC 纠错实现

### 3. FTL 模拟器
- **链接**: https://github.com/Cosmos+MinSung Kim/FTL_Simulator
- **内容**: FTL 算法仿真工具
- **学习重点**:
  - 算法性能评估
  - 不同策略对比

---

## 📋 厂商技术文档

### 1. Samsung
- **文档**: Samsung UFS 产品手册、应用笔记
- **获取**: 联系 Samsung FAE 或官网下载

### 2. Micron
- **文档**: Micron UFS Technical Note
- **获取**: https://www.micron.com/support

### 3. Kioxia（原 Toshiba）
- **文档**: Kioxia UFS 产品规格书
- **获取**: https://business.kioxia.com/

---

## 🎯 学习路径建议

### 第 1-2 周：UFS 基础
- [ ] 阅读 JEDEC UFS 3.1 标准（JESD220-3）
- [ ] 学习 UFS 协议层架构
- [ ] 理解 LUN、Command Queue 概念

### 第 3-4 周：FTL 算法
- [ ] 学习 FTL 基本架构（页映射/块映射/混合映射）
- [ ] 理解磨损均衡算法（动态/静态）
- [ ] 学习垃圾回收策略

### 第 5-6 周：固件实现
- [ ] 阅读开源 FTL 代码
- [ ] 学习坏块管理实现
- [ ] 理解 ECC 纠错原理

### 第 7-8 周：性能优化
- [ ] 学习缓存管理（SLC Cache、Data Cache）
- [ ] 理解读电压优化（Read Retry、VBAT）
- [ ] 分析性能测试数据

---

## 🔧 实践建议

1. **搭建测试环境**: 使用 UFS 测试板 + FIO 进行性能测试
2. **代码阅读**: 每周阅读 1-2 个 FTL 核心函数
3. **实验验证**: 对比不同负载下的性能表现
4. **文档总结**: 每周输出学习总结文档

---

**创建时间**: 2026-03-13  
**版本**: V1.0
