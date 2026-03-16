# SysTest 部署指南

本文档指导如何将 SysTest 框架部署到开发板并进行实际测试。

## 📋 前置要求

### 硬件要求

- UFS 开发板或测试平台
- UFS 设备已正确连接并识别
- 稳定的电源供应
- 散热条件良好（建议加散热片或风扇）

### 软件要求

- Python 3.11+
- FIO 工具
- root 权限（访问 UFS 设备需要）

## 🚀 部署步骤

### 1. 检查开发板环境

```bash
# 检查 Python 版本
python3 --version
# 应输出：Python 3.11.x 或更高

# 检查 FIO 是否安装
which fio
fio --version

# 如果 FIO 未安装，执行：
apt update && apt install fio -y
```

### 2. 确认 UFS 设备

```bash
# 查看块设备
lsblk

# 查看 UFS 设备（示例）
ls -la /dev/ufs0
# 或
ls -la /dev/sda

# 确认设备型号
cat /sys/block/sda/device/model
```

### 3. 复制 SysTest 到开发板

```bash
# 方式 1: SCP 复制
scp -r SysTest/ user@board:/opt/

# 方式 2: Git 克隆（如果开发板能访问网络）
cd /opt
git clone <repository-url> SysTest
```

### 4. 设置执行权限

```bash
cd /opt/SysTest
chmod +x bin/SysTest
```

### 5. 验证部署

```bash
# 查看帮助
python3 bin/SysTest --help

# 列出测试
python3 bin/SysTest list

# 干跑验证
python3 bin/SysTest run -s performance --dry-run -v
```

## ⚙️ 配置调整

### 修改设备路径

如果 UFS 设备不是 `/dev/ufs0`，需要修改配置：

```bash
# 编辑配置文件
vi config/default.json
```

修改：
```json
{
  "device": {
    "default_path": "/dev/sda"  // 改为实际设备路径
  }
}
```

### 调整验收目标

根据产品规格调整验收标准：

```json
{
  "targets": {
    "seq_read_burst": 2100,      // 根据实际规格调整
    "seq_write_burst": 1650,
    // ...
  }
}
```

### 调整测试时间

Burst 测试默认 60 秒，Sustained 测试默认 300 秒：

```json
{
  "execution": {
    "default_runtime": 60,       // Burst 测试时间
    "sustained_runtime": 300     // Sustained 测试时间
  }
}
```

## 🧪 执行测试

### 执行单个测试套件

```bash
# 性能测试（约 25 分钟）
python3 bin/SysTest run -s performance -d /dev/sda -v

# QoS 测试（约 10 分钟）
python3 bin/SysTest run -s qos -d /dev/sda -v

# 场景测试（约 10 分钟）
python3 bin/SysTest run -s scenario -d /dev/sda -v
```

### 执行单个测试项

```bash
# 顺序读 Burst 测试
python3 bin/SysTest run -t seq_read_burst -d /dev/sda -v

# 随机写 Sustained 测试
python3 bin/SysTest run -t rand_write_sustained -d /dev/sda -v
```

### 执行全部测试

```bash
# 执行所有套件（约 45 分钟）
python3 bin/SysTest run -s performance -d /dev/sda --format html,json
python3 bin/SysTest run -s qos -d /dev/sda --format html,json
python3 bin/SysTest run -s scenario -d /dev/sda --format html,json
```

### 后台执行长时间测试

```bash
# 稳定性测试（24 小时）- 后台执行
python3 bin/SysTest run -t stability_test -d /dev/sda --background

# 查看进度
tail -f results/*/summary.txt
```

## 📊 查看结果

### 查看最新报告

```bash
# 查看文本摘要
python3 bin/SysTest report --latest

# 查看 HTML 报告（如果开发板有浏览器）
firefox results/*/report.html

# 或将报告复制到本地查看
scp -r user@board:/opt/SysTest/results/ ./
```

### 失效分析

```bash
# 分析最新测试结果
python3 bin/SysTest analyze --latest

# 分析指定测试 ID
python3 bin/SysTest analyze --id=20260316_090000
```

### 结果文件位置

```
results/
└── 20260316_090000/
    ├── results.json       # 完整测试结果（JSON）
    ├── report.html        # HTML 可视化报告
    ├── summary.txt        # 文本摘要
    └── raw/               # FIO 原始数据
        ├── seq_read_burst.json
        ├── seq_write_burst.json
        └── ...
```

## ⚠️ 注意事项

### 1. 数据安全

⚠️ **警告**: 测试会擦除 UFS 设备上的数据！

- 确保测试设备不包含重要数据
- 测试前备份必要数据
- 确认设备路径正确，避免误操作

### 2. 散热管理

长时间测试会产生大量热量：

- 确保散热片/风扇工作正常
- 监控设备温度（如果支持）
- 如温度超过 70℃，暂停测试

### 3. 电源稳定

- 使用稳定的电源适配器
- 避免测试过程中断电
- 建议使用 UPS（不间断电源）

### 4. 测试环境

- 关闭不必要的后台服务
- 避免其他进程访问 UFS 设备
- 保持系统负载稳定

## 🔧 故障排查

### FIO 命令找不到

```bash
# 检查 FIO 是否安装
which fio

# 安装 FIO
apt update && apt install fio -y
```

### 设备权限不足

```bash
# 使用 root 权限
sudo python3 bin/SysTest run -s performance -d /dev/sda

# 或修改设备权限
chmod 666 /dev/sda
```

### 测试超时

```bash
# 增加超时时间（在 runner.py 中修改）
timeout=1200  # 20 分钟
```

### 结果异常

```bash
# 检查 FIO 原始数据
cat results/*/raw/*.json | jq

# 查看系统日志
dmesg | grep -i error
```

## 📞 技术支持

如遇到问题，请提供以下信息：

1. 测试设备型号和配置
2. SysTest 版本号
3. 完整的错误信息
4. FIO 原始数据（results/*/raw/*.json）

---

**版本**: v1.0.0  
**最后更新**: 2026-03-16
