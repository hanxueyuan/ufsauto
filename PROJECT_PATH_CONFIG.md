# UFS Auto 项目目录配置

## 📁 项目存放路径规划
### 1. 主项目目录
**路径：** `/home/gem/workspace/agent/workspace/ufsauto/`
**原因：**
- 位于 `/home/workspace` 下，属于S3持久化存储，数据安全不会丢失
- 是当前工作目录，符合开发习惯
- 已初始化Git仓库，和GitHub远程仓库同步
- 空间充足，S3存储无容量限制

### 2. 测试执行目录（开发板上的部署路径）
**路径：** `/mapdata/ufs_test/`
**原因：**
- 该分区可用空间36GB，足够存放测试文件和临时数据
- 独立分区，测试不会影响系统分区和其他业务数据
- 是用户指定的测试专用目录
- 分区类型为ext4，适合IO密集型测试

---
## 📂 项目目录结构
```
/home/gem/workspace/agent/workspace/ufsauto/
├── .github/workflows/       # GitHub CI/CD 配置
├── docs/                    # 项目文档
│   ├── requirement/         # 需求文档
│   ├── design/              # 设计文档
│   ├── test_spec/           # 测试规范
│   └── report/              # 测试报告模板
├── src/                     # 核心源代码
│   ├── lib/                 # 公共库
│   │   ├── common.py        # 通用函数
│   │   ├── fio_wrapper.py   # fio封装
│   │   ├── report.py        # 报告生成
│   │   └── stress_wrapper.py # stress-ng封装
│   ├── tests/               # 测试模块
│   │   ├── system/          # 系统测试用例
│   │   ├── function/        # 功能测试用例
│   │   ├── performance/     # 性能测试用例
│   │   ├── reliability/     # 可靠性测试用例
│   │   └── scenario/        # 场景测试用例
│   ├── config/              # 配置文件
│   └── run_all.py           # 一键执行入口
├── scripts/                 # 辅助脚本
│   ├── deploy.sh            # 部署脚本
│   ├── package.sh           # 打包脚本
│   └── sync_github.sh       # GitHub同步脚本
├── examples/                # 使用示例
├── tests/                   # 单元测试
├── README.md                # 项目说明
├── USAGE_GUIDE.md           # 使用指南
├── CHANGELOG.md             # 变更记录
└── requirements.txt         # Python依赖
```

---
## 🔄 同步机制
1. **本地开发**：所有代码在 `/home/gem/workspace/agent/workspace/ufsauto/` 下开发
2. **Git提交**：代码提交到本地Git仓库
3. **自动同步**：每日01:00自动同步到GitHub远程仓库 `https://github.com/hanxueyuan/ufsauto`
4. **部署到开发板**：需要测试时，将代码打包上传到开发板的 `/mapdata/ufs_test_package/` 目录下解压运行

---
## 📊 空间使用规划
| 目录 | 预计占用空间 | 用途 |
|------|--------------|------|
| 代码和文档 | < 100MB | 存放所有源代码、文档、配置 |
| 测试临时文件 | < 30GB | 开发板上测试时生成的临时文件 |
| 测试报告和日志 | < 1GB | 每次测试生成的报告和日志 |

空间完全充足，完全满足项目开发和测试需求。
