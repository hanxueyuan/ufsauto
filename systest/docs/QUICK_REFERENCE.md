# UFS SysTest 快速参考卡

## 🚀 5 分钟快速开始

```bash
# 1. 环境检查
cd ufsauto/systest
python3 bin/SysTest check-env -v

# 2. 运行测试
python3 bin/SysTest run --suite=performance --device=/dev/ufs0 -v

# 3. 查看报告
python3 bin/SysTest report --latest
```

---

## 📋 常用命令

### 环境检查
```bash
SysTest check-env -v                    # 详细检查
SysTest check-env --report              # 生成 JSON 报告
```

### 执行测试
```bash
SysTest run --suite=performance -d /dev/ufs0    # 性能套件
SysTest run --test=t_perf_SeqReadBurst_001      # 单个测试
SysTest run --suite=performance --dry-run       # 模拟运行
```

### 查看结果
```bash
SysTest report --latest                 # 最新报告
SysTest report --id 20260322_133000     # 指定报告
```

### 基线对比
```bash
SysTest compare-baseline --dev results/dev/ --ci results/ci/
```

---

## 📁 目录结构

```
systest/
├── bin/
│   ├── SysTest              # 主入口
│   ├── check_env.py         # 环境检查
│   └── compare_baseline.py  # 基线对比
├── suites/
│   └── performance/         # 性能测试套件 (5 项)
├── config/
│   ├── default.json         # 默认配置
│   └── production.json      # 生产配置
├── results/                 # 测试结果
├── logs/                    # 日志文件
└── docs/                    # 文档
```

---

## 🎯 性能阈值

| 测试项 | 目标值 | 容差 |
|--------|--------|------|
| 顺序读 Burst | ≥2100 MB/s | 5% |
| 顺序写 Burst | ≥1650 MB/s | 5% |
| 随机读 Burst | ≥200 KIOPS | 5% |
| 随机写 Burst | ≥330 KIOPS | 5% |
| 混合读写 70/30 | ≥150 KIOPS | 5% |

---

## 🖥️ 开发板环境

```yaml
操作系统：Debian 12 (bookworm)
内核：6.1.x
Python: 3.11
FIO: 3.33
架构：ARM64
设备：/dev/ufs0
```

---

## 🐳 Docker 使用

```bash
# 构建镜像
docker build -t ufsauto/systest:1.0 -f Dockerfile.ci .

# 运行测试
docker run --rm -v /dev:/dev --privileged \
  ufsauto/systest:1.0 \
  "python3 /workspace/systest/bin/SysTest run --suite=performance"
```

---

## 🔧 故障排查

### 权限问题
```bash
sudo usermod -aG disk $USER
newgrp disk
```

### 设备不存在
```bash
ls -la /dev/ufs* /dev/sd*
dmesg | grep -i ufs
```

### FIO 未安装
```bash
sudo apt-get install fio
```

---

## 📖 文档索引

| 文档 | 用途 |
|------|------|
| [README.md](./README.md) | 完整使用手册 |
| [PRACTICAL_GUIDE.md](./PRACTICAL_GUIDE.md) | 实战流程指南 |
| [DEV_BOARD_ENV.md](./DEV_BOARD_ENV.md) | 开发板环境配置 |
| [ENVIRONMENT_SETUP.md](./ENVIRONMENT_SETUP.md) | 环境配置详解 |
| [CI_CD_QUICKSTART.md](./CI_CD_QUICKSTART.md) | CI/CD 集成 |

---

**打印版本**: 建议 A4 纸打印，贴在工作区
