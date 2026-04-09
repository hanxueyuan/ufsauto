# UFS Auto 开发板部署指南

## ✅ 环境验证完成

当前环境已成功配置：

| 项目 | 版本/状态 |
|------|----------|
| **FIO** | ✅ 3.36 (已安装) |
| **Python** | ✅ 3.12.3 |
| **操作系统** | Ubuntu 24.04 LTS |
| **内核** | 6.8.0-55-generic |
| **用户权限** | ✅ root |

---

## 🚀 部署到开发板

### 方式一：使用部署脚本（推荐）

```bash
# 1. 打包项目
cd /workspace/projects
tar -czf ufsauto-deploy.tar.gz ufsauto/

# 2. 传输到开发板
# 通过 U 盘/SCP 等方式传输

# 3. 在开发板上解压
cd /mapdata
tar -xzf ufsauto-deploy.tar.gz
cd ufsauto

# 4. 运行部署脚本
./scripts/setup-environment.sh
```

### 方式二：手动安装 FIO

如果开发板没有 FIO，在开发板上执行：

```bash
# 更新 apt 源（阿里云镜像）
cat > /etc/apt/sources.list << 'EOF'
deb http://mirrors.aliyun.com/ubuntu/ noble main restricted universe multiverse
deb http://mirrors.aliyun.com/ubuntu/ noble-security main restricted universe multiverse
deb http://mirrors.aliyun.com/ubuntu/ noble-updates main restricted universe multiverse
deb http://mirrors.aliyun.com/ubuntu/ noble-backports main restricted universe multiverse
EOF

# 安装 FIO
apt-get update
apt-get install -y fio

# 验证
fio --version
```

---

## 📋 配置文件

配置文件位置：`systest/config/runtime.json`

```json
{
  "device": "/dev/sda",
  "test_dir": "/mapdata/ufs_test",
  "device_capacity_gb": 238.2,
  "toolchain": {
    "python": "3.11.2",
    "fio": "3.36"
  },
  "system": {
    "ufs_version": "UFS v",
    "ufs_gear": "4,4",
    "ufs_lane": "2,2"
  }
}
```

---

## 🧪 执行测试

### 快速验证

```bash
# Dry-run 模式（不执行实际 IO）
python3 systest/bin/systest_cli.py run --suite performance --dry-run
```

### 完整测试

```bash
# 性能测试（5 个用例）
python3 systest/bin/systest_cli.py run --suite performance

# QoS 测试
python3 systest/bin/systest_cli.py run --suite qos

# 单个测试
python3 systest/bin/systest_cli.py run --test t_perf_SeqReadBurst_001
```

### 批处理测试

```bash
# 批量执行 3 次，间隔 60 秒
python3 systest/bin/systest_cli.py run --suite performance --batch=3 --interval=60
```

---

## 📊 查看结果

```bash
# 查看最新报告
python3 systest/bin/systest_cli.py report --latest

# 报告位置
ls -la results/
```

---

## ⚠️ 开发板注意事项

### 1. 存储空间

确保测试目录有足够空间：

```bash
# 检查空间
df -h /mapdata

# 建议至少 50GB 可用空间
```

### 2. 设备路径

根据实际设备调整：

```bash
# 查看块设备
lsblk

# 如果设备不是 /dev/sda，修改配置
python3 systest/bin/systest_cli.py run --device=/dev/mmcblk0
```

### 3. 温度监控

长时间测试注意散热：

```bash
# 监控温度（如果支持）
cat /sys/class/thermal/thermal_zone*/temp

# 增加测试间隔
python3 systest/bin/systest_cli.py run --suite performance --interval=120
```

---

## 🔧 故障排查

### FIO 未安装

```bash
# 检查
which fio

# 安装
apt-get update
apt-get install -y fio
```

### 设备访问权限

```bash
# 确认 root 权限
whoami

# 检查设备
ls -la /dev/sda
```

### 空间不足

```bash
# 清理测试文件
rm -rf /mapdata/ufs_test/*

# 清理旧报告
rm -rf results/*
```

---

## 📈 性能基准

UFS Gear 4 Lane 2 预期性能：

| 测试 | 目标值 |
|------|--------|
| 顺序读 | ≥2100 MB/s |
| 顺序写 | ≥1650 MB/s |
| 随机读 | ≥120K IOPS |
| 延迟 p50 | <50 μs |
| 延迟 p99 | <200 μs |

---

**部署完成！可以开始测试了！** ✅
