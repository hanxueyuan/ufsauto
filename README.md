# UFS Auto - UFS 性能测试自动化框架

[![CI/CD](https://github.com/hanxueyuan/ufsauto/actions/workflows/ci.yml/badge.svg)](https://github.com/hanxueyuan/ufsauto/actions)

## 快速开始

### 1. 环境准备

```bash
# 安装 FIO（必需）
sudo apt install fio

# 安装可选工具
sudo apt install sg3-utils
```

### 2. 首次使用

```bash
# 环境检测并保存配置
python3 systest/bin/SysTest check-env --save-config

# 运行性能测试
python3 systest/bin/SysTest run --suite=performance

# 快速模式（时间减半）
python3 systest/bin/SysTest run --suite=performance --quick
```

## 命令参考

### 执行测试

```bash
# 运行性能测试套件
python3 systest/bin/SysTest run --suite=performance

# 快速性能验证
python3 systest/bin/SysTest run --suite=performance --quick

# 运行单个测试项
python3 systest/bin/SysTest run --test=t_perf_SeqReadBurst_001

# 批量测试 3 次
python3 systest/bin/SysTest run --suite=performance --batch=3 --interval=60

# 指定设备和测试目录
python3 systest/bin/SysTest run --suite=performance --device=/dev/sda --test-dir=/mapdata/ufs_test

# 模拟执行（不实际运行）
python3 systest/bin/SysTest run --suite=performance --dry-run
```

### 查看信息

```bash
# 列出所有测试
python3 systest/bin/SysTest list

# 查看最新报告
python3 systest/bin/SysTest report --latest
```

### 环境管理

```bash
# 检查环境
python3 systest/bin/SysTest check-env

# 保存配置
python3 systest/bin/SysTest check-env --save-config
```

## 项目结构

```
ufsauto/
├── bin/                    # 入口脚本
│   ├── SysTest            # 主入口
│   └── check_env.py       # 环境检测
├── core/                   # 核心模块
│   ├── runner.py          # 测试执行器
│   ├── collector.py       # 结果收集
│   ├── reporter.py        # 报告生成
│   └── logger.py          # 日志系统
├── tools/                  # 工具模块
│   ├── fio_wrapper.py     # FIO 封装
│   └── ufs_utils.py       # UFS 工具
├── suites/performance/     # 性能测试套件
│   ├── t_perf_SeqReadBurst_001.py
│   ├── t_perf_SeqWriteBurst_002.py
│   ├── t_perf_RandReadBurst_003.py
│   ├── t_perf_RandWriteBurst_004.py
│   └── t_perf_MixedRw_005.py
└── config/                 # 配置文件
    └── runtime.json.example
```

## CI/CD

项目配置了自动化 CI/CD 流程：

- **GitHub Actions**: `.github/workflows/ci.yml`
- **GitLab CI**: `.gitlab-ci.yml`

每次提交自动执行：
1. ✅ Python 语法检查
2. ✅ 类型检查（mypy）
3. ✅ 代码规范检查
4. ✅ Dry-run 测试
5. ✅ 环境检测测试
6. ✅ 帮助文档测试

## 安全说明

- 设备路径验证：防止路径遍历攻击
- 测试目录验证：确保在安全目录内
- 文件清理：测试结束后自动清理临时文件

## 许可证

MIT License
