# 离线环境测试方案（开发板无法联网）

## 🎯 核心约束：开发板无法联网，所有工具必须离线部署
**部署方式**：在 PC 上准备好所有需要的工具和脚本，打包后通过 scp 上传到开发板，解压即可运行。

---
## 🛠️ 最终开发方案：纯 Bash 脚本 + 预编译工具包
### 开发语言和工具选型
| 类型 | 选型 | 说明 |
|------|------|------|
| **测试脚本** | 纯 Bash 脚本 | 系统自带 Bash，无需安装任何依赖，直接运行 |
| **性能测试** | fio（aarch64 静态编译） | 提前在 PC 上编译好，上传到板上直接运行 |
| **压力测试** | stress-ng（aarch64 静态编译）或 Bash 脚本替代 | 静态编译版本或纯 Bash 实现 |
| **UFS 专用工具** | ufs-utils（aarch64 静态编译） | 提前编译好上传 |
| **报告生成** | Bash 脚本生成 Markdown/文本格式 | 在板上生成文本报告，PC 端生成可视化报告 |

### 为什么不用 Python？
- 系统可能没有预装 Python3 或 pip
- 无法联网安装依赖包
- Bash 脚本更轻量，资源占用更低，更适合嵌入式环境

---
## 📦 离线部署包结构
```
ufs_test_package/
├── bin/                        # 预编译的工具（aarch64 静态编译）
│   ├── fio
│   ├── stress-ng
│   └── ufs-utils
├── tests/                      # 测试脚本（纯 Bash）
│   ├── 01_system_check.sh      # 系统环境检查
│   ├── 02_function_test.sh     # 基础功能测试
│   ├── 03_performance_test.sh  # 性能测试
│   ├── 04_reliability_test.sh  # 可靠性测试
│   └── 05_scenario_test.sh     # 应用场景测试
├── config/                     # 配置文件
│   └── test_config.sh          # 测试路径、测试时长等配置
├── lib/                        # 公共函数库
│   └── common.sh               # 日志、断言、结果记录等公共函数
├── results/                    # 测试结果目录（运行时生成）
├── run_all.sh                  # 一键执行脚本（总入口）
├── clean.sh                    # 清理测试数据脚本
└── README.md                   # 使用说明
```

---
## 📋 测试脚本清单（全部纯 Bash 实现）
### 01_system_check.sh - 系统环境检查
```bash
#!/bin/bash
# 检查系统信息、UFS 设备识别情况、可用空间、工具是否齐全
# 输出：系统环境报告
```

### 02_function_test.sh - 基础功能测试
| 用例 ID | 测试内容 | 实现方式 |
|--------|----------|----------|
| F01 | 小文件读写 | 循环创建 1000 个 1KB 文件，md5sum 校验 |
| F02 | 大文件读写 | dd 创建 10GB 文件，md5sum 校验 |
| F03 | 文件拷贝/移动/删除 | cp/mv/rm 命令，验证操作正常 |
| F04 | 并发读写 | 多后台进程同时读写文件 |
| F05 | 满盘测试 | 写入文件直到磁盘满，删除后验证空间释放 |

### 03_performance_test.sh - 性能测试（使用预编译 fio）
| 用例 ID | 测试内容 | 验证指标 |
|--------|----------|----------|
| P01 | 顺序读 128K | ≥2100MB/s |
| P02 | 顺序写 128K | ≥1600MB/s |
| P03 | 随机读 4K | ≥400K IOPS |
| P04 | 随机写 4K | ≥300K IOPS |
| P05 | 混合读写 7:3 | 性能符合预期 |
| P06 | 延迟测试 | 平均延迟≤10ms |

### 04_reliability_test.sh - 可靠性测试
| 用例 ID | 测试内容 | 测试时长 |
|--------|----------|----------|
| R01 | 长时间压力测试 | 72 小时连续读写 |
| R02 | 数据完整性测试 | 7 天定期校验 md5 |
| R03 | 低空间测试 | 剩余空间<10% 时读写 |
| R04 | 温度监控 | 满负载运行，监控温度 |

### 05_scenario_test.sh - 应用场景测试
- 模拟用户实际使用场景（数据库、媒体处理、多任务等）
- 高 IO 负载下系统响应测试

---
## 🚀 部署和使用方式
### 1. 在 PC 上准备测试包
```bash
# 1. 交叉编译 fio（在 Ubuntu 或 Debian 上）
apt install gcc-aarch64-linux-gnu
cd fio && ./configure --host=aarch64-linux-gnu --enable-static && make

# 2. 交叉编译 stress-ng（可选，或用 Bash 脚本替代）
cd stress-ng && make CC=aarch64-linux-gnu-gcc LDFLAGS="-static"

# 3. 编译 ufs-utils（可选）
cd ufs-utils && make CC=aarch64-linux-gnu LDFLAGS="-static"

# 4. 打包所有文件
tar zcf ufs_test_package.tar.gz ufs_test_package/
```

### 2. 上传到开发板
```bash
# 通过 scp 上传
scp ufs_test_package.tar.gz root@192.168.195.3:/mapdata/

# 登录开发板
ssh root@192.168.195.3
```

### 3. 解压并运行
```bash
# 解压
cd /mapdata
tar zxf ufs_test_package.tar.gz
cd ufs_test_package

# 执行所有测试
./run_all.sh

# 或单独执行某个测试
./tests/01_system_check.sh
./tests/03_performance_test.sh
```

### 4. 获取测试结果
```bash
# 查看测试结果
cat results/report.md

# 下载到 PC 查看
scp root@192.168.195.3:/mapdata/ufs_test_package/results/* ./local_results/
```

---
## ⚡ 优势
1. **100% 离线可用**：不需要联网，所有工具和脚本都打包在一起
2. **部署简单**：一条 scp 命令上传，解压即可运行
3. **纯 Bash 脚本**：无依赖，系统自带 Bash 就能运行
4. **轻量高效**：脚本资源占用低，不影响系统性能
5. **易维护**：Bash 脚本简单易懂，团队成员都能修改
6. **可复现**：用户遇到问题可以用同样的脚本复现和定位

---
## 📅 开发计划
| 任务 | 完成时间 | 交付物 |
|------|----------|--------|
| 交叉编译 fio | 3 月 15 日 | aarch64 静态编译 fio |
| 交叉编译 stress-ng | 3 月 16 日 | aarch64 静态编译 stress-ng（可选） |
| 系统检查脚本 | 3 月 17 日 | 01_system_check.sh |
| 功能测试脚本 | 3 月 19 日 | 02_function_test.sh |
| 性能测试脚本 | 3 月 21 日 | 03_performance_test.sh |
| 可靠性测试脚本 | 3 月 25 日 | 04_reliability_test.sh |
| 应用场景脚本 | 3 月 27 日 | 05_scenario_test.sh |
| 一键测试框架 | 3 月 29 日 | run_all.sh + 完整测试包 |
| 交叉编译验证 | 3 月 30 日 | 在开发板上验证所有工具正常运行 |

所有脚本和工具都将在 3 月底前准备就绪，拿到样品后直接上传到板上即可开始测试。

---
## 📌 下一步行动
1. **确认开发板上已有的命令**：请执行以下命令，确认系统自带哪些工具
```bash
which bash dd md5sum grep awk sed lsblk dmesg df free cat head tail sort wc
python3 --version 2>/dev/null || echo "Python3 not found"
fio --version 2>/dev/null || echo "fio not found"
stress-ng --version 2>/dev/null || echo "stress-ng not found"
```

2. **开始交叉编译 fio**：我会在 PC 上交叉编译 aarch64 版本的 fio，然后提供给你上传到板上

需要我现在开始准备交叉编译 fio 吗？还是先确认下板上已有的工具？
