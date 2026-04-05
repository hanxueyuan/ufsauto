# UFS Auto SysTest

UFS 存储性能自动化测试框架，专为离线开发板环境设计。

## 🚀 快速开始

```bash
cd systest

# 1. 检查环境
python3 bin/SysTest check-env

# 2. 查看可用测试
python3 bin/SysTest list

# 3. 快速测试 (日常开发)
python3 bin/SysTest run --suite=performance --quick

# 4. 完整测试 (版本发布)
python3 bin/SysTest run --all
```

## 📚 文档导航

### 核心文档
- **[测试知识](systest/docs/UFS_Testing_Knowledge.md)** - UFS 测试原理和指标详解
- **[使用示例](systest/docs/Usage_Examples.md)** - 15 个实际场景的使用指南
- **[故障诊断](systest/docs/Troubleshooting_Guide.md)** - 系统化的问题排查方法

### 专业参考
- **[AEC-Q100 检查单](systest/docs/AEC-Q100_Checklist.md)** - 车规级可靠性测试标准
- **[失效分析流程](systest/docs/FA_Process.md)** - FA 标准流程

## 🎯 核心功能

### 测试套件
| 套件 | 测试项 | 用途 |
|------|--------|------|
| Performance | 5 项 | 顺序/随机读写性能 |
| QoS | 4 项 | 延迟特性和稳定性 |
| Reliability | 3 项 | 长期健康监控 |

### 测试模式
- **快速模式** (`--quick`): ~10 分钟，日常开发验证
- **完整模式** (默认): ~2-3 小时，版本发布验证

### 核心命令
```bash
python3 bin/SysTest run              # 执行测试
python3 bin/SysTest list             # 列出测试
python3 bin/SysTest report           # 查看报告
python3 bin/SysTest check-env        # 检查环境
python3 bin/SysTest compare-baseline # 基线对比
python3 bin/SysTest config           # 配置管理
```

## 💡 设计理念

### 1. 统一入口
所有功能通过 `python3 bin/SysTest <command>` 访问

### 2. 两种模式协作
- **快速模式**: 最短时间验证流程 (~10 分钟)
- **完整模式**: 全面测试所有指标 (~2 小时+)
- 两者互补，不是对立

### 3. 理解优先
- 先理解测试模拟的场景
- 再理解指标的含义
- 最后才是执行和分析

### 4. 纯标准库
无第三方依赖，适合离线环境

## 📊 测试维度

```
性能测试 (Performance)
├─ 顺序读写 → 视频播放/录制、大文件拷贝
├─ 随机读写 → 应用启动、数据库操作
└─ 混合读写 → 日常多任务使用

服务质量 (QoS)
├─ 延迟百分位 → P50/P95/P99 分布
├─ 延迟抖动 → 波动范围
└─ 尾部延迟比 → P99/P50 健康度

可靠性 (Reliability)
├─ 坏块监控 → 坏块增长趋势
├─ ECC 错误率 → 纠错统计
└─ 耐久性测试 → 长期压力测试
```

## 🔧 典型使用场景

### 场景 1: 日常开发验证
```bash
# 代码变更后快速验证
python3 bin/SysTest run --suite=performance --quick
```

### 场景 2: 版本发布
```bash
# 完整测试所有套件
python3 bin/SysTest run --all --batch=3

# 保存基线
python3 bin/SysTest report --save-baseline
```

### 场景 3: 问题排查
```bash
# 1. 检查环境
python3 bin/SysTest check-env

# 2. 执行测试
python3 bin/SysTest run --full

# 3. 对比基线
python3 bin/SysTest compare-baseline
```

### 场景 4: 长期监控
```bash
# 每周运行一次
python3 bin/SysTest run --full

# 对比趋势
python3 bin/SysTest compare-baseline
```

## 📈 关键指标参考

### 健康判断
```
P99/P50 < 10    → 延迟分布均匀 ✓
P99/P50 > 20    → 延迟抖动大 ⚠
性能波动 < 20%  → 稳定性好 ✓
性能波动 > 50%  → 可能有问题 ⚠
```

**注意**: 具体性能指标因设备型号和容量而异，请参考设备规格书。

## 🛠️ 故障诊断速查

| 现象 | 可能原因 | 解决方法 |
|------|----------|----------|
| Permission denied | 权限不足 | 用 root 运行 |
| No space left | 空间不足 | 清理空间 |
| Device not found | 设备路径错 | lsblk 确认路径 |
| 性能远低于预期 | 缓存干扰 | 加 direct=1 |
| 性能波动大 | 热节流/GC | 检查温度 |

详细诊断流程见：[Troubleshooting_Guide.md](systest/docs/Troubleshooting_Guide.md)

## 📁 项目结构

```
ufsauto/
├── README.md                     # 本文件
└── systest/                      # 测试框架
    ├── bin/                      # 可执行脚本
    ├── core/                     # 核心模块
    ├── suites/                   # 测试套件
    ├── tools/                    # 工具模块
    ├── config/                   # 配置文件
    ├── docs/                     # 文档体系 ⭐
    ├── logs/                     # 测试日志
    └── results/                  # 测试结果
```

## 🎓 学习路径

### 快速上手
1. 运行 `python3 bin/SysTest check-env`
2. 运行 `python3 bin/SysTest run --quick`
3. 阅读 [UFS_Testing_Knowledge.md](systest/docs/UFS_Testing_Knowledge.md)

### 深入理解
1. 阅读 [Usage_Examples.md](systest/docs/Usage_Examples.md)
2. 尝试不同测试场景
3. 建立自己的 baseline

### 掌握诊断
1. 阅读 [Troubleshooting_Guide.md](systest/docs/Troubleshooting_Guide.md)
2. 学习分析测试结果
3. 实践故障排查流程

## 🔗 相关资源

- **FIO 文档**: https://fio.readthedocs.io/
- **UFS 标准**: JEDEC UFS 规范
- **AEC-Q100**: 车规级集成电路应力测试认证

## 📝 许可证

MIT License

---

**核心理念**: 测试不是目的，而是理解 UFS 行为、发现潜在问题、优化系统设计的手段。

**文档优先**: 遇到问题先查文档，理解原理后再深入分析。
