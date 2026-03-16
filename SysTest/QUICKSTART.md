# SysTest 快速开始指南

## 1. 项目位置

```
/home/gem/workspace/agent/workspace/SysTest/
```

## 2. 立即使用

### 查看帮助

```bash
cd /home/gem/workspace/agent/workspace/SysTest
python3 bin/SysTest --help
```

### 列出测试

```bash
python3 bin/SysTest list
```

### 执行测试（干跑模式）

```bash
# 干跑模式 - 不实际执行，只验证配置
python3 bin/SysTest run -s performance --dry-run -v
```

### 实际执行测试

⚠️ **注意**：实际执行需要开发板上有 `/dev/ufs0` 设备和 FIO 工具

```bash
# 检查 FIO 是否安装
which fio

# 检查 UFS 设备
ls -la /dev/ufs0

# 执行性能测试
python3 bin/SysTest run -s performance -d /dev/ufs0 -v
```

## 3. 框架代码结构

已创建的核心文件：

```
SysTest/
├── bin/SysTest              ✅ 主入口 (12.6KB)
├── core/
│   ├── runner.py            ✅ 测试执行引擎 (13.1KB)
│   ├── collector.py         ✅ 结果收集器 (5.0KB)
│   ├── reporter.py          ✅ 报告生成器 (9.7KB)
│   └── analyzer.py          ✅ 失效分析引擎 (9.2KB)
├── suites/performance/
│   └── README.md            ✅ 性能测试套件说明
├── config/
│   └── default.json         ✅ 默认配置
└── README.md                ✅ 项目说明文档
```

## 4. 下一步工作

### 立即可做（无需开发板）

1. **代码审查**
   - 阅读 `bin/SysTest` 主入口
   - 理解 `core/runner.py` 测试执行逻辑
   - 检查配置项是否完整

2. **本地测试**
   ```bash
   # 干跑模式验证
   python3 bin/SysTest run -s performance --dry-run -v
   
   # 初始化配置
   python3 bin/SysTest config --init
   
   # 查看配置
   python3 bin/SysTest config --show
   ```

3. **完善测试套件**
   - 添加更多测试用例到 `suites/` 目录
   - 自定义验收标准到 `config/default.json`

### 需要开发板

1. **部署到开发板**
   ```bash
   # 复制整个项目到开发板
   scp -r SysTest/ user@board:/opt/
   
   # 添加执行权限
   chmod +x /opt/SysTest/bin/SysTest
   ```

2. **验证环境**
   ```bash
   # 检查 Python
   python3 --version
   
   # 检查 FIO
   which fio
   fio --version
   
   # 检查 UFS 设备
   lsblk
   ```

3. **执行实际测试**
   ```bash
   cd /opt/SysTest
   python3 bin/SysTest run -s performance -d /dev/ufs0
   ```

## 5. 定制配置

编辑 `config/default.json`：

```json
{
  "targets": {
    "seq_read_burst": 2100,
    "seq_read_sustained": 1800,
    "seq_write_burst": 1650,
    "seq_write_sustained": 250
  }
}
```

## 6. 输出示例

执行测试后，结果保存在 `results/` 目录：

```
results/
└── 20260315_120000/
    ├── results.json       # 完整测试结果
    ├── report.html        # HTML 可视化报告
    ├── summary.txt        # 文本摘要
    └── raw/               # FIO 原始数据
```

## 7. 常见问题

### Q: FIO 命令找不到？
```bash
# 安装 FIO
apt update && apt install fio
```

### Q: 设备路径不是 /dev/ufs0？
```bash
# 查看可用块设备
lsblk

# 使用实际设备路径
python3 bin/SysTest run -s performance -d /dev/sda
```

### Q: 如何修改测试时间？
编辑 `config/default.json`：
```json
{
  "execution": {
    "default_runtime": 60,      // Burst 测试 60 秒
    "sustained_runtime": 300    // Sustained 测试 300 秒
  }
}
```

## 8. 联系与支持

- 项目文档：`README.md`
- 配置说明：`config/default.json`
- 测试套件：`suites/*/README.md`

---

**状态**: ✅ 框架代码已完成，可开始测试验证
