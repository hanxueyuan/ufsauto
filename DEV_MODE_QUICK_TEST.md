# 开发模式快速验证指南

## ✅ 验证完成

测试框架已成功运行，验证结果：

```
测试结果:
  带宽：51189.8 MB/s
  IOPS: 409518
  延迟：2.3 μs
  运行时间：6 秒
```

**框架状态**: ✅ 正常工作

---

## 🚀 开发模式配置

### 配置文件

`systest/config/runtime.json`:

```json
{
  "test_mode": {
    "mode": "development",
    "quick_test": true,
    "runtime_seconds": 5,
    "ramp_time_seconds": 0,
    "test_size": "64M",
    "skip_prefill": true
  }
}
```

### 开发模式特点

| 参数 | 生产模式 | 开发模式 | 说明 |
|------|----------|----------|------|
| **测试时间** | 60 秒 | 5 秒 | 快速验证 |
| **测试大小** | 1-10GB | 64MB | 减少 IO |
| **预热时间** | 10 秒 | 0 秒 | 跳过预热 |
| **预填充** | 是 | 否 | 跳过 dd 预填充 |
| **循环次数** | 多次 | 1 次 | 单次验证 |

---

## 📝 快速测试命令

### 方式一：使用快速测试脚本

```bash
cd /workspace/projects/ufsauto
python3 quick_test.py
```

**输出示例**:
```
============================================================
  UFS Auto 开发模式快速测试
============================================================

测试模式：development
快速测试：True
设备：/dev/vda
测试目录：/tmp/ufs_test

开始测试...

✓ 设备存在：/dev/vda
✓ 可用空间：26.7GB
✓ FIO 已安装：fio-3.36
✓ 测试文件创建完成
✓ 前置检查通过

=== 执行 FIO 测试 ===
  带宽：51189.8 MB/s
  IOPS: 409518
  延迟：2.3 μs

✅ 快速测试完成！
框架验证通过！可以开始正式测试了
```

### 方式二：使用 CLI 工具

```bash
# Dry-run 模式（不执行实际 IO，验证框架）
python3 systest/bin/systest_cli.py run --suite performance --dry-run

# 快速模式（测试时间减半）
python3 systest/bin/systest_cli.py run --suite performance --quick

# 单个测试用例验证
python3 systest/bin/systest_cli.py run --test t_perf_SeqReadBurst_001
```

---

## 🎯 验证检查清单

开发模式验证通过的标准：

- [x] ✅ FIO 工具已安装并可用
- [x] ✅ Python 环境正常
- [x] ✅ 测试框架能加载配置
- [x] ✅ 测试文件能创建和清理
- [x] ✅ FIO 命令能正常执行
- [x] ✅ 结果能正确解析和验证
- [x] ✅ 日志能正常输出
- [x] ✅ 报告能生成

---

## 📊 测试结果分析

### 当前环境测试结果

```
设备：/dev/vda (虚拟磁盘)
带宽：51189.8 MB/s  (虚拟设备，性能非常高)
IOPS: 409518
延迟：2.3 μs
```

**注意**: 这是虚拟磁盘的性能，实际 UFS 设备性能会低很多：

| 设备类型 | 顺序读 | 顺序写 | 随机读 |
|----------|--------|--------|--------|
| **虚拟磁盘 (vda)** | ~50GB/s | ~50GB/s | ~400K IOPS |
| **UFS Gear4 Lane2** | ~2100 MB/s | ~1650 MB/s | ~120K IOPS |

### 开发板预期结果

在真实 UFS 开发板上：

```
设备：/dev/sda (UFS 238GB)
预期带宽：2000-2200 MB/s (顺序读)
预期 IOPS: 100K-150K (随机读)
预期延迟：30-100 μs
```

---

## 🔧 切换到生产模式

验证完成后，修改配置进行正式测试：

### 1. 更新配置文件

```json
{
  "test_mode": {
    "mode": "production",
    "quick_test": false,
    "runtime_seconds": 60,
    "ramp_time_seconds": 10,
    "test_size": "1G",
    "skip_prefill": false
  }
}
```

### 2. 执行完整测试

```bash
# 完整性能测试（5 个用例，约 5-10 分钟）
python3 systest/bin/systest_cli.py run --suite performance

# 完整 QoS 测试（约 2-5 分钟）
python3 systest/bin/systest_cli.py run --suite qos

# 批处理测试（3 次循环）
python3 systest/bin/systest_cli.py run --suite performance --batch=3 --interval=60
```

---

## 📁 相关文件

| 文件 | 说明 |
|------|------|
| `quick_test.py` | 开发模式快速测试脚本 |
| `systest/config/runtime.json` | 运行时配置 |
| `systest/bin/systest_cli.py` | CLI 主入口 |
| `logs/` | 日志目录 |
| `results/` | 测试结果目录 |

---

## 🆘 故障排查

### 问题 1: FIO 未找到

```bash
# 检查
which fio

# 安装
apt-get update
apt-get install -y fio
```

### 问题 2: 设备不存在

```bash
# 查看可用设备
lsblk

# 更新配置
# 编辑 systest/config/runtime.json
# 修改 device 为实际设备路径
```

### 问题 3: 空间不足

```bash
# 检查空间
df -h

# 清理测试目录
rm -rf /tmp/ufs_test/*
```

---

**框架验证完成！可以开始正式测试了！** ✅
