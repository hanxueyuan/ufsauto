# 离线开发板部署指南

## 📋 目标环境配置

| 项目 | 配置 |
|------|------|
| **Python** | 3.11.2 |
| **FIO** | 3.33 |
| **UFS 设备** | /dev/sda (238.2G) |
| **UFS 规格** | Gear 4,4 / Lane 2,2 |
| **测试目录** | /mapdata/ufs_test |
| **用户权限** | root |

---

## 🚀 部署步骤

### 1. 文件传输（离线环境）

由于开发板离线，需要从联网机器打包传输：

```bash
# 在联网机器上打包项目
cd /workspace/projects
tar -czf ufsauto_deploy.tar.gz ufsauto/

# 通过 U 盘/SCP/其他方式传输到开发板
# 示例：使用 U 盘
cp ufsauto_deploy.tar.gz /media/usb/

# 在开发板上解压
cd /mapdata
tar -xzf ufsauto_deploy.tar.gz
cd ufsauto
```

### 2. 环境验证

```bash
# 检查 Python 版本
python3 --version  # 应输出 3.11.2

# 检查 FIO 版本
fio --version  # 应输出 3.33

# 检查设备访问权限
ls -la /dev/sda  # root 应可读写

# 检查测试目录空间
df -h /mapdata  # 确保有足够空间（建议 >50G）
```

### 3. 配置文件确认

```bash
# 验证配置文件
cat systest/config/runtime.json

# 应包含：
# - device: /dev/sda
# - test_dir: /mapdata/ufs_test
# - toolchain.python: 3.11.2
# - toolchain.fio: 3.33
```

---

## 📝 测试执行

### 快速测试（验证框架）

```bash
# Dry-run 模式（不执行实际 IO，验证框架）
python3 systest/bin/systest_cli.py run --suite performance --dry-run
```

### 完整性能测试

```bash
# 运行全部性能测试（5 个用例）
python3 systest/bin/systest_cli.py run --suite performance

# 运行 QoS 测试
python3 systest/bin/systest_cli.py run --suite qos

# 运行所有测试
python3 systest/bin/systest_cli.py run --suite all
```

### 单个测试用例

```bash
# 顺序读测试
python3 systest/bin/systest_cli.py run --test t_perf_SeqReadBurst_001

# 随机读测试
python3 systest/bin/systest_cli.py run --test t_perf_RandReadBurst_003

# 延迟测试
python3 systest/bin/systest_cli.py run --test t_qos_LatencyPercentile_001
```

### 批处理测试

```bash
# 批量执行 3 次，每次间隔 60 秒
python3 systest/bin/systest_cli.py run --suite performance --batch=3 --interval=60
```

---

## 📊 查看结果

### 测试报告

```bash
# 查看最新 HTML 报告
python3 systest/bin/systest_cli.py report --latest

# 查看指定报告
python3 systest/bin/systest_cli.py report --id SysTest_performance_20260409_071100

# 报告位置：results/ 目录
ls -la results/
```

### 日志文件

```bash
# 查看最新日志
ls -la logs/
tail -f logs/systest_*.log
```

---

## ⚠️ 注意事项

### 1. 存储空间

- **测试目录**: `/mapdata/ufs_test` 需要至少 **50GB** 可用空间
- **FIO 测试文件**: 每个测试用例会创建约 10-20GB 的测试文件
- **日志文件**: 单个测试日志约 10-50MB

```bash
# 检查空间
df -h /mapdata

# 清理旧测试文件
rm -rf /mapdata/ufs_test/*
```

### 2. 权限要求

- **必须以 root 运行**: 需要直接访问 `/dev/sda` 设备
- **设备锁**: 确保没有其他进程占用 UFS 设备

```bash
# 检查设备占用
lsof /dev/sda
fuser -v /dev/sda
```

### 3. 温度监控

长时间测试可能导致设备发热，建议：

```bash
# 监控温度（如果开发板支持）
cat /sys/class/thermal/thermal_zone*/temp

# 测试间隔建议
# 批量测试时设置 --interval=120（2 分钟间隔）
```

### 4. findmnt 兼容性

当前 `findmnt` 版本不支持 `FSUSED/FSAVAIL`，框架已适配：

- ✅ 使用传统方式检查挂载点
- ✅ 使用 `df` 命令检查可用空间
- ⚠️ 部分高级功能受限

### 5. 离线环境限制

- ❌ 无法自动更新依赖
- ❌ 无法在线下载报告
- ✅ 所有报告本地生成（HTML/JSON）
- ✅ 所有日志本地保存

---

## 🔧 故障排查

### 问题 1: FIO 找不到命令

```bash
# 检查 FIO 安装
which fio

# 如果未安装，需要离线安装
# 在联网机器下载 FIO 包，传输到开发板安装
```

### 问题 2: 设备访问被拒绝

```bash
# 确认 root 权限
whoami  # 应输出 root

# 检查设备权限
ls -la /dev/sda  # 应为 brw-rw---- root disk
```

### 问题 3: 空间不足

```bash
# 清理测试目录
rm -rf /mapdata/ufs_test/*

# 清理旧报告
rm -rf results/*
```

### 问题 4: 测试超时

```bash
# 增加超时时间（秒）
python3 systest/bin/systest_cli.py run --suite performance --timeout=3600
```

---

## 📈 性能基准参考

根据 UFS Gear 4 Lane 2 规格，预期性能：

| 测试类型 | 预期值 | 说明 |
|----------|--------|------|
| 顺序读 | ≥2100 MB/s | 128K 块大小 |
| 顺序写 | ≥1650 MB/s | 128K 块大小 |
| 随机读 | ≥120K IOPS | 4K 块大小，QD32 |
| 随机写 | - | 4K 块大小，QD32 |
| 延迟 p50 | <50 μs | 4K 块大小，QD1 |
| 延迟 p99 | <200 μs | 4K 块大小，QD1 |

---

## 📦 项目文件清单

部署到开发板的必要文件：

```
ufsauto/
├── systest/
│   ├── bin/                  # 必须
│   ├── core/                 # 必须
│   ├── tools/                # 必须
│   ├── suites/               # 必须
│   └── config/
│       └── runtime.json      # 必须（已配置）
├── results/                  # 运行时生成
├── logs/                     # 运行时生成
└── README.md                 # 参考
```

---

## 🎯 推荐测试流程

```bash
# 1. 环境验证
python3 systest/bin/systest_cli.py check-env

# 2. Dry-run 验证框架
python3 systest/bin/systest_cli.py run --suite performance --dry-run

# 3. 执行性能测试
python3 systest/bin/systest_cli.py run --suite performance

# 4. 执行 QoS 测试
python3 systest/bin/systest_cli.py run --suite qos

# 5. 查看报告
python3 systest/bin/systest_cli.py report --latest

# 6. 导出结果（复制到 U 盘）
cp results/*.html /media/usb/
cp results/*.json /media/usb/
```

---

**配置完成！现在可以在离线开发板上执行测试了！** ✅
