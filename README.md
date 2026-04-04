# SysTest - UFS 系统测试框架

车规级 UFS 3.1 存储设备系统测试框架，支持性能测试、QoS 验证、可靠性测试。

**项目状态**: ✅ 生产就绪（95% 完成度）  
**代码量**: ~4500 行 Python  
**测试覆盖**: 5 个性能测试 + 4 个 QoS 测试 + 3 个可靠性测试

---

## 📦 项目结构

```
ufsauto/systest/
├── bin/                    # 入口脚本
│   ├── SysTest            # 主入口（run/check-env/compare-baseline）
│   ├── check_env.py       # 环境信息收集
│   └── compare_baseline.py # 性能基线对比
├── core/                   # 核心框架
│   ├── runner.py          # 测试执行引擎（支持 Fail-Stop/Fail-Continue）
│   ├── collector.py       # 结果收集器
│   ├── reporter.py        # 报告生成器（HTML/JSON）
│   ├── logger.py          # 日志管理器（轮转 + 结构化）
│   └── analyzer.py        # 失效分析引擎
├── tools/                  # 工具层
│   ├── fio_wrapper.py     # FIO 封装（标准化指标输出）
│   ├── ufs_utils.py       # UFS 设备管理（健康状态/描述符）
│   ├── latency_analyzer.py # QoS 延迟分析（根因定位）
│   └── reliability_calculator.py # 寿命计算工具
├── suites/                 # 测试套件
│   ├── performance/        # 性能测试（5 个用例）
│   │   ├── t_perf_SeqReadBurst_001.py    # 顺序读带宽
│   │   ├── t_perf_SeqWriteBurst_002.py   # 顺序写带宽
│   │   ├── t_perf_RandReadBurst_003.py   # 随机读 IOPS
│   │   ├── t_perf_RandWriteBurst_004.py  # 随机写 IOPS
│   │   └── t_perf_MixedRw_005.py         # 混合读写（70/30）
│   ├── qos/                # QoS 测试（4 个用例）
│   │   ├── t_qos_LatencyPercentile_001.py # 延迟百分位
│   │   ├── t_qos_LatencyJitter_002.py    # 延迟抖动
│   │   ├── t_qos_TailLatencyRatio_003.py # 尾部发散度
│   │   └── t_qos_LatencyStability_004.py # 延迟稳定性
│   └── reliability/        # 可靠性测试（3 个用例）
│       ├── t_reliability_BadBlockMonitor_001.py # 坏块监控
│       ├── t_reliability_ECCErrorRate_002.py    # ECC 错误率
│       └── t_reliability_EnduranceTest_003.py   # 耐久性测试
├── config/                 # 配置文件
│   └── runtime.json        # 运行时配置（设备路径/测试目录）
├── docs/                   # 文档
│   ├── AEC-Q100_Checklist.md      # AEC-Q100 测试清单
│   ├── FA_Process.md              # 失效分析流程
│   └── SysTest_Bug_Report_20260404.md # Bug 检查报告
└── tests/                  # 单元测试
```

---

## 🚀 快速开始

### 1. 环境检查

```bash
cd /home/gem/workspace/agent/workspace/ufsauto

# 检查环境信息（推荐首次运行时执行）
python3 systest/bin/SysTest check-env

# 保存检测结果为配置文件（自动检测设备路径和测试目录）
python3 systest/bin/SysTest check-env --save-config

# CI/CD 环境验证模式
python3 systest/bin/SysTest check-env --ci
```

**输出示例:**
```
============================================================
UFS SysTest 环境信息
============================================================
模式：开发模式

[系统信息]
  操作系统        Ubuntu 22.04.3 LTS
  内核版本        6.8.0-100-generic
  CPU 架构         aarch64
  CPU 核心数        8
  内存            16.0 GB

[工具链]
  Python          3.11.2
  FIO             3.33

[存储设备]
  设备类型        UFS ✓
  UFS 地址         39410000.ufs
  SCSI Host       host0
  UFS 配置         Gear [4, 4], Lane [2, 2]
  块设备          sda    128G disk 0
  UFS 设备路径     /dev/sda (via ufshcd)

[用户权限]
  当前用户        root
  用户组          root, disk
  设备访问        可读写 (root)

[测试目录]
  findmnt 版本     findmnt from util-linux 2.38
  findmnt 兼容性   新版 (支持所有列)
  建议测试目录     /mapdata/ufs_test (可用 36.0 GB)

✅ 配置已保存：config/runtime.json
   设备路径：/dev/sda
   测试目录：/mapdata/ufs_test
```

---

### 2. 运行测试

#### 运行完整测试套件

```bash
cd /home/gem/workspace/agent/workspace/ufsauto

# 性能测试套件（约 5-10 分钟）
python3 systest/bin/SysTest run --suite=performance

# QoS 测试套件（约 10-15 分钟）
python3 systest/bin/SysTest run --suite=qos

# 可靠性测试套件（约 30-60 分钟）
python3 systest/bin/SysTest run --suite=reliability

# 运行所有套件（约 1-2 小时）
python3 systest/bin/SysTest run --all
```

#### 运行单个测试用例

```bash
cd /home/gem/workspace/agent/workspace/ufsauto

# 顺序读性能测试
python3 systest/bin/SysTest run --test=seq_read_burst

# 随机写 IOPS 测试
python3 systest/bin/SysTest run --test=rand_write_burst

# QoS 延迟百分位测试
python3 systest/bin/SysTest run --test=qos_latency_percentile

# 坏块监控可靠性测试
python3 systest/bin/SysTest run --test=reliability_bad_block_monitor
```

#### 自定义测试参数

```bash
cd /home/gem/workspace/agent/workspace/ufsauto

# 指定设备路径
python3 systest/bin/SysTest run --suite=performance --device=/dev/sda

# 指定测试目录
python3 systest/bin/SysTest run --suite=performance --test-dir=/mapdata/ufs_test

# 详细输出模式
python3 systest/bin/SysTest run --suite=performance -v

# Dry-run 模式（验证框架，不执行真实测试）⭐推荐首次运行
python3 systest/bin/SysTest run --suite=performance --dry-run
```

---

### 3. 查看结果

测试完成后，结果保存在 `results/` 目录：

```bash
# 查看最新测试结果
cd results
ls -lt | head

# 查看测试汇总
cat SysTest_20260404_073000/summary.txt

# 查看 JSON 格式详细结果
cat SysTest_20260404_073000/results.json | python3 -m json.tool

# 在浏览器打开 HTML 报告
firefox SysTest_20260404_073000/report.html
```

**HTML 报告预览:**
```
📊 UFS 系统测试报告
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
测试 ID: SysTest_20260404_073000
时间：2026-04-04T07:30:00
套件：performance
设备：/dev/sda

📈 汇总统计
┌──────┬────────┬────────┬──────────┐
│ 总计 │  通过  │  失败  │  通过率  │
├──────┼────────┼────────┼──────────┤
│  5   │   5    │   0    │  100.0%  │
└──────┴────────┴────────┴──────────┘

📋 测试结果
✅ seq_read_burst: PASS (72.34s)
   带宽：2156.8 MB/s | IOPS: 16932 | 平均延迟：152.3 μs
✅ seq_write_burst: PASS (71.89s)
   带宽：1723.4 MB/s | IOPS: 13521 | 平均延迟：189.7 μs
✅ rand_read_burst: PASS (72.12s)
   IOPS: 215678 | 平均延迟：148.2 μs
✅ rand_write_burst: PASS (71.95s)
   IOPS: 342891 | 平均延迟：138.5 μs
✅ mixed_rw: PASS (72.45s)
   总 IOPS: 167234 | 平均延迟：191.3 μs
```

---

## 🔧 常用工具

### 性能基线对比

对比开发板和 CI/CD 环境的性能差异：

```bash
cd /home/gem/workspace/agent/workspace/ufsauto/systest

# 对比两个测试结果
python3 bin/compare_baseline.py \
  --baseline1 results/dev_board/ \
  --baseline2 results/ci/

# 允许 10% 性能差异
python3 bin/compare_baseline.py \
  --baseline1 results/test1/ \
  --baseline2 results/test2/ \
  --threshold 0.10

# 输出报告到文件
python3 bin/compare_baseline.py \
  --dev results/dev/ --ci results/ci/ \
  --output baseline_comparison.txt
```

### QoS 延迟分析

深度分析延迟分布和尾部延迟根因：

```bash
cd /home/gem/workspace/agent/workspace/ufsauto/systest

# 分析 FIO JSON 结果
python3 tools/latency_analyzer.py results/SysTest_xxx/qos_latency.json

# 输出分析报告
python3 tools/latency_analyzer.py \
  results/SysTest_xxx/qos_latency.json \
  qos_latency_analysis.txt
```

### 可靠性计算工具

计算 AEC-Q100 寿命和 LTPD 样本量：

```bash
cd /home/gem/workspace/agent/workspace/ufsauto/systest/tools
python3 reliability_calculator.py

# 示例输出:
温度加速因子 (125℃→55℃): 89.2x
电压加速因子 (1.8V→1.98V): 1.43x
125℃ 1000hr HTOL 等效 55℃使用寿命：12.7 年 ✅
LTPD 1.0/90% CL 需要样本量：230 颗
```

---

## 📋 测试用例清单

### 性能测试套件 (performance)

| 用例 ID | 测试名称 | 测试目的 | 关键指标 | 测试耗时 |
|--------|---------|---------|---------|---------|
| `seq_read_burst` | 顺序读带宽 | 验证 Burst 读性能 | 带宽 ≥2100 MB/s | ~70s |
| `seq_write_burst` | 顺序写带宽 | 验证 Burst 写性能 | 带宽 ≥1650 MB/s | ~70s |
| `rand_read_burst` | 随机读 IOPS | 验证 4K 随机读性能 | IOPS ≥200K | ~70s |
| `rand_write_burst` | 随机写 IOPS | 验证 4K 随机写性能 | IOPS ≥330K | ~70s |
| `mixed_rw` | 混合读写 | 验证 70% 读/30% 写混合负载 | 总 IOPS ≥150K | ~70s |

### QoS 测试套件 (qos)

| 用例 ID | 测试名称 | 测试目的 | 关键指标 | 测试耗时 |
|--------|---------|---------|---------|---------|
| `qos_latency_percentile` | 延迟百分位 | 验证 p99.99/p99.999 延迟 | p99.99 <10ms, p99.999 <20ms | ~130s |
| `qos_latency_jitter` | 延迟抖动 | 验证延迟稳定性 | 抖动 <20% | ~200s |
| `qos_tail_latency_ratio` | 尾部发散度 | 验证 p99.99/p50 比率 | 比率 <100x | ~150s |
| `qos_latency_stability` | 延迟稳定性 | 多次迭代验证延迟一致性 | CV <1.0 | ~600s |

### 可靠性测试套件 (reliability)

| 用例 ID | 测试名称 | 测试目的 | 验收标准 | 测试耗时 |
|--------|---------|---------|---------|---------|
| `reliability_bad_block_monitor` | 坏块监控 | 验证压力写入后坏块不增加 | 坏块增加=0 | ~1800s |
| `reliability_ecc_error_rate` | ECC 错误率 | 验证 UBER <10^-15 | UBER 达标 | ~3600s |
| `reliability_endurance_test` | 耐久性测试 | 验证 P/E 循环寿命 | P/E ≥3K cycles | ~7200s |

---

## 🛠️ 高级用法

### 自定义测试配置

编辑 `systest/config/runtime.json`:

```json
{
  "device": "/dev/sda",
  "test_dir": "/mapdata/ufs_test",
  "env_checked_at": "2026-04-04T07:30:00",
  "system": {
    "os": "Ubuntu 22.04.3 LTS",
    "kernel": "6.8.0-100-generic",
    "cpu": "aarch64"
  }
}
```

### 修改测试阈值

在测试用例中覆盖默认参数：

```bash
cd /home/gem/workspace/agent/workspace/ufsauto

# 放宽带宽阈值（90% 目标）
python3 systest/bin/SysTest run --test=seq_read_burst \
  --test-args='{"target_bw_mbps": 1890}'

# 收紧延迟阈值
python3 systest/bin/SysTest run --test=qos_latency_percentile \
  --test-args='{"target_p9999_us": 8000}'
```

### CI/CD 集成

GitHub Actions 示例:

```yaml
name: SysTest CI

on: [push, pull_request]

jobs:
  systest:
    runs-on: [self-hosted, arm64]
    steps:
      - uses: actions/checkout@v4
      
      - name: 环境检查
        run: |
          cd ufsauto/systest
          python3 bin/SysTest check-env --save-config
      
      - name: 运行性能测试 (dry-run 验证框架)
        run: |
          python3 bin/SysTest run --suite=performance --dry-run
      
      - name: 上传测试结果
        uses: actions/upload-artifact@v4
        with:
          name: systest-results
          path: ufsauto/systest/results/
```

---

## 📚 文档索引

| 文档 | 说明 | 路径 |
|------|------|------|
| **AEC-Q100 测试清单** | 23 项车规认证测试详细条件 | `docs/AEC-Q100_Checklist.md` |
| **失效分析流程** | FA 流程、失效模式库、8D 模板 | `docs/FA_Process.md` |
| **Bug 检查报告** | 2026-04-04 代码检查结果 | `docs/SysTest_Bug_Report_20260404.md` |
| **闪存原理速查手册** | 3D NAND 参数、FTL 算法、ECC 计算 | `../../docs/闪存原理速查手册.md` |
| **寿命计算工具** | 温度/电压加速因子、DPPM、LTPD | `tools/reliability_calculator.py` |

---

## ❓ 常见问题

### Q: 找不到设备 `/dev/ufs0`

**A:** 使用 `check-env` 自动检测设备路径：

```bash
cd /home/gem/workspace/agent/workspace/ufsauto
python3 systest/bin/SysTest check-env --save-config
# 或手动指定
python3 systest/bin/SysTest run --device=/dev/sda
```

### Q: 测试失败 "Permission denied"

**A:** 需要 root 权限或 disk 组权限：

```bash
cd /home/gem/workspace/agent/workspace/ufsauto

# 使用 sudo
sudo python3 systest/bin/SysTest run --suite=performance

# 或将用户加入 disk 组
sudo usermod -aG disk $USER
```

### Q: 可用空间不足

**A:** 指定有足够空间的测试目录：

```bash
cd /home/gem/workspace/agent/workspace/ufsauto
python3 systest/bin/SysTest run --test-dir=/mapdata/ufs_test
```

### Q: FIO 工具未安装

**A:** 安装 FIO：

```bash
# Ubuntu/Debian
sudo apt-get install fio

# 验证安装
fio --version

# 或使用 dry-run 模式先验证框架（不需要 FIO）
cd /home/gem/workspace/agent/workspace/ufsauto
python3 systest/bin/SysTest run --suite=performance --dry-run
```

### Q: 如何解读测试结果中的 "Fail-Continue" 和 "Fail-Stop"？

**A:** 
- **Fail-Continue**: 记录失败但继续执行，最终状态为 FAIL（用于性能不达标）
- **Fail-Stop**: 立即终止测试，状态为 FAIL（用于硬件损伤、数据损坏等严重问题）

---

## 📞 技术支持

- **项目仓库**: https://github.com/hanxueyuan/ufsauto
- **文档中心**: `ufsauto/docs/`
- **问题反馈**: GitHub Issues

---

*最后更新：2026-04-04*  
*维护者：团长 1 🦞*