# SysTest - UFS 系统测试框架

车规级 UFS 3.1 存储设备系统测试框架。

## 快速开始

```bash
# 查看可用测试
python3 bin/SysTest list

# 执行测试套件
python3 bin/SysTest run --suite=performance --device=/dev/ufs0
python3 bin/SysTest run --suite=qos --device=/dev/ufs0
python3 bin/SysTest run --suite=reliability --device=/dev/ufs0

# 执行单个测试
python3 bin/SysTest run --test=t_perf_SeqReadBurst_001 -v

# 查看帮助
python3 bin/SysTest --help
```

## 目录结构

```
systest/
├── bin/           # 入口脚本
├── core/          # 核心框架（runner/collector/reporter/logger/analyzer）
├── tools/         # 工具层（fio_wrapper/ufs_utils）
├── suites/        # 测试套件（performance/qos/reliability）
└── tests/         # 单元测试
```

## 测试套件

| 套件 | 功能 | 用例数 |
|------|------|--------|
| performance | 性能测试 | 5 |
| qos | QoS 延迟测试 | 4 |
| reliability | 可靠性测试 | 3 |

## 环境要求

- Python 3.10+
- FIO 3.33+
- UFS 设备（默认 `/dev/ufs0`）

## 详细文档

测试参数、指标定义、配置说明详见 `docs/` 目录。

---

**状态**: ✅ 生产就绪