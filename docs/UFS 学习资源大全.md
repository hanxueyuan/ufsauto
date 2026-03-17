# UFS 学习资源大全

**创建时间**: 2026-03-18  
**目标**: 收集所有可用的 UFS 学习资源和渠道

---

## 📚 官方规范文档

### 1. JEDEC 标准（必须阅读）

| 文档编号 | 标题 | 获取方式 | 优先级 |
|----------|------|----------|--------|
| JESD220E | UFS 3.1 标准 | JEDEC 官网（需注册） | 🔴 必须 |
| JESD223C | UFS Host Controller Interface | JEDEC 官网 | 🔴 必须 |
| JESD84 | eMMC 标准（参考） | JEDEC 官网 | 🟡 参考 |
| JESD22-A114 | ESD 测试标准 | JEDEC 官网 | 🟡 参考 |

**获取链接**：
- https://www.jedec.org/standards-documents (搜索 "JESD220")
- 费用：JEDEC 会员免费，非会员需购买

---

### 2. MIPI 联盟标准

| 文档 | 内容 | 获取方式 |
|------|------|----------|
| M-PHY v4.1 | 物理层规范 | MIPI 官网（需会员） |
| UniPro v1.8 | 协议层规范 | MIPI 官网 |

**获取链接**：
- https://www.mipi.org/specifications

---

## 💻 GitHub 开源项目

### 1. Linux 内核 UFS 驱动

**仓库**: https://github.com/torvalds/linux/tree/master/drivers/ufs

**关键文件**：
```
drivers/ufs/
├── core/ufshcd.c          # 核心驱动（重点阅读）
├── core/ufshcd.h          # 头文件
├── host/ufshcd-pltfrm.c   # 平台驱动
└── host/ufs-qcom.c        # 高通平台实现
```

**学习重点**：
- [ ] ufshcd_probe() - 设备初始化流程
- [ ] ufshcd_queuecommand() - 命令处理流程
- [ ] ufshcd_power_management() - 电源管理

---

### 2. U-Boot UFS 支持

**仓库**: https://github.com/u-boot/u-boot/tree/master/drivers/ufs

**学习价值**：
- 理解 UFS 初始化流程
- 简化的驱动实现

---

### 3. 开源工具

| 工具 | 仓库 | 用途 |
|------|------|------|
| ufs-utils | https://github.com/junwoo80/ufs-utils | UFS 设备管理工具 |
| fio | https://github.com/axboe/fio | 性能测试工具 |
| smartmontools | https://github.com/smartmontools/smartmontools | SMART 信息读取 |

---

## 📖 推荐书籍

### 1. 闪存基础

| 书名 | 作者 | ISBN | 推荐度 |
|------|------|------|--------|
| Flash Memory Guide | Michael L. Smith | - | ⭐⭐⭐⭐⭐ |
| NAND Flash Memory Technologies | 业界白皮书 | - | ⭐⭐⭐⭐ |

### 2. 存储系统

| 书名 | 作者 | ISBN | 推荐度 |
|------|------|------|--------|
| Storage Systems and Solutions | Richard Barker | - | ⭐⭐⭐⭐ |
| Understanding SSDs | Steven Zimmerman | - | ⭐⭐⭐⭐⭐ |

### 3. UFS 专项

**目前市面没有专门的 UFS 书籍**，建议：
- 阅读 JEDEC 规范
- 阅读厂商白皮书（Samsung、SK Hynix、Kioxia）

---

## 🌐 在线课程与教程

### 1. 厂商技术文档

**Samsung**:
- https://www.samsung.com/semiconductor/minisite/ufs/
- 产品规格书
- 应用笔记

**SK Hynix**:
- https://www.skhynix.com/products/ufs.do
- 技术白皮书

**Kioxia (原 Toshiba)**:
- https://business.kioxia.com/en-apac/products/ufs.html
- 技术文档

### 2. 技术论坛

| 论坛 | 链接 | 价值 |
|------|------|------|
| EETimes | https://www.eetimes.com/ | 行业新闻 |
| AnandTech | https://www.anandtech.com/ | 深度评测 |
| Storage Review | https://www.storagereview.com/ | 存储专项 |

### 3. 视频资源

**YouTube 频道**：
- The Memory Guy - https://www.youtube.com/c/TheMemoryGuy
- Flash Memory Summit - https://www.flashmemorystummit.org/

**B 站**：
- 搜索"UFS 协议"、"FTL 算法"
- 关注存储技术 UP 主

---

## 📊 行业报告

### 1. 市场研究

| 机构 | 报告 | 获取方式 |
|------|------|----------|
| TrendForce | 存储市场报告 | 官网购买 |
| Yole Développement | 存储技术报告 | 官网购买 |
| Gartner | 半导体报告 | 官网购买 |

### 2. 技术峰会

| 会议 | 时间 | 资料获取 |
|------|------|----------|
| Flash Memory Summit | 每年 8 月 | 官网下载 PPT |
| IEEE IEDM | 每年 12 月 | IEEE Xplore |
| VLSI Symposium | 每年 6 月 | IEEE Xplore |

---

## 🔬 学术研究

### 1. 论文数据库

| 数据库 | 链接 | 关键词 |
|--------|------|--------|
| IEEE Xplore | https://ieeexplore.ieee.org/ | "UFS", "FTL", "NAND" |
| ACM Digital Library | https://dl.acm.org/ | "Flash Storage" |
| Google Scholar | https://scholar.google.com/ | "UFS protocol" |

### 2. 重点论文

搜索关键词：
- "UFS performance analysis"
- "FTL algorithms survey"
- "3D NAND reliability"
- "Storage for autonomous driving"

---

## 🏭 厂商资源

### 1. 主控厂商

| 厂商 | 官网 | 资源 |
|------|------|------|
| Phison | https://www.phison.com/ | 技术白皮书 |
| Silicon Motion | https://www.siliconmotion.com/ | 产品文档 |
| Realtek | https://www.realtek.com/ | 产品规格 |

### 2. 测试设备厂商

| 厂商 | 官网 | 设备 |
|------|------|------|
| Keysight | https://www.keysight.com/ | UFS 协议分析仪 |
| Teledyne LeCroy | https://teledynelecroy.com/ | 协议分析工具 |

---

## 📝 学习计划

### 第 1 周：官方规范
- [ ] 阅读 JESD220E 第 1-4 章
- [ ] 阅读 JESD220E 第 7-8 章
- [ ] 整理命令集笔记

### 第 2 周：Linux 驱动
- [ ] 阅读 ufshcd.c 核心代码
- [ ] 绘制初始化流程图
- [ ] 绘制命令处理流程图

### 第 3 周：厂商文档
- [ ] 阅读 Samsung UFS 产品规格
- [ ] 阅读 SK Hynix 技术白皮书
- [ ] 对比不同厂商实现差异

### 第 4 周：行业前沿
- [ ] 观看 Flash Memory Summit 视频
- [ ] 阅读 3 篇学术论文
- [ ] 总结技术发展趋势

---

## 📌 每日学习打卡模板

```markdown
## Day X - 学习记录

**日期**: 2026-03-XX
**主题**: [例如：UFS 命令集]
**资料来源**: [例如：JESD220E 第 8 章]

### 学习内容
1. ...
2. ...

### 关键收获
- ...

### 待深入问题
- [ ] ...

### 参考链接
- ...
```

---

## 🎯 下一步行动

1. **立即注册 JEDEC 账号** - 获取官方规范
2. **Clone Linux 内核仓库** - 开始阅读驱动源码
3. **收藏厂商官网** - 定期查看新技术
4. **订阅 YouTube 频道** - 利用碎片时间学习

---

**持续更新中...** 🚀
