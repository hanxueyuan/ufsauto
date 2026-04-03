# SysTest - UFS 系统测试框架

车规级 UFS 3.1 存储设备系统测试框架。

## 项目结构

```
systest/
├── bin/           # 入口脚本
├── core/          # 核心框架（runner/collector/reporter/logger/analyzer）
├── tools/         # 工具层（fio_wrapper/ufs_utils/latency_analyzer）
├── suites/        # 测试套件（performance/qos/reliability）
└── tests/         # 单元测试
```

## 快速开始

```bash
cd systest/bin

# 运行测试
python3 SysTest run --suite=performance
python3 SysTest run --suite=qos
python3 SysTest run --suite=reliability

# 查看帮助
python3 SysTest --help
```

## 环境要求

- Python 3.10+
- FIO 3.33+
- UFS 设备

## 详细文档

测试参数、指标定义、架构设计详见 `systest/docs/`。

---

**项目状态**: ✅ 生产就绪

**默认设备**: `/dev/ufs0`