# SysTest 测试框架设计原则与流程规范

**版本**: 2.2  
**最后更新**: 2026-04-10  
**状态**: Production Ready ✅  
**更新说明**: 移除循环测试逻辑、统一日志系统、增强安全验证、完善常量配置

---

## 🚀 5 分钟快速上手

### 环境准备

```bash
# 检查环境并保存配置
python3 systest/bin/systest.py check-env --save-config
```

> **说明**: 假设 FIO 已预装。如未安装，请先运行 `apt-get install fio`。

### 运行测试

```bash
# 开发模式（快速验证，~2 分钟）
python3 systest/bin/systest.py run --suite performance

# 生产模式（充分验证，~25 分钟）
python3 systest/bin/systest.py run --suite performance --mode=production

# 查看最新报告
python3 systest/bin/systest.py report --latest
```

### 查看当前模式

```bash
python3 systest/bin/systest.py mode
```

---

## 一、架构设计原则

### 1.1 四层架构，职责分离

```plaintext
入口层 (bin/) → 核心层 (core/) → 工具层 (tools/) → 套件层 (suites/)
```

| 层级 | 模块 | 职责 |
|------|------|------|
| **入口层** | `systest.py` | CLI 命令行入口、参数解析、模式管理 |
| **核心层** | `runner.py` | 测试执行引擎 (TestRunner/TestCase) |
| **核心层** | `collector.py` | 结果收集 (ResultCollector) |
| **核心层** | `reporter.py` | 报告生成 (HTML/JSON/CSV) |
| **核心层** | `logger.py` | 日志管理 (TestLogger) |
| **核心层** | `constants.py` | 常量配置 (Config) |
| **工具层** | `fio_wrapper.py` | FIO 封装 (FIO/FIOConfig/FIOMetrics) |
| **工具层** | `ufs_utils.py` | UFS 设备操作 (UFSDevice/UFSUtils) |
| **工具层** | `health_monitor.py` | 健康状态监控 |
| **套件层** | `performance/` | 5 个性能测试用例 |
| **套件层** | `qos/` | QoS 测试用例 |

**设计思想**:
- **入口层**: 只负责参数解析和组件组装，包含模式管理逻辑
- **核心层**: 通用测试引擎，不依赖具体测试类型
- **工具层**: 提供可复用能力，封装外部依赖 (FIO/设备操作)
- **套件层**: 只关注测试业务逻辑，复用基类能力

### 1.2 测试发现机制

测试框架通过以下机制自动发现和加载测试用例：

1. **套件目录**: `suites/performance/`、`suites/qos/` 等
2. **模块导出**: 每个套件目录下的 `__init__.py` 导出测试类
3. **动态导入**: runner 根据 `--suite` 参数动态加载对应目录下的测试用例
4. **命名约定**: 测试文件以 `t_` 开头，类名为 `Test`

---

## 二、测试用例生命周期

### 2.1 四阶段标准化流程

每个测试用例必须实现四个阶段：

**1. setup() - 前置条件检查**
- 检查设备存在 (支持自动检测)
- 检查可用空间 (≥2GB)
- 检查 FIO 工具
- 检查权限
- **记录健康基线 (Precondition)**
- 创建测试文件路径
- 返回 False → SKIP 状态

**2. execute() - 执行测试、采集数据**
- 调用 FIO 执行测试
- 解析性能指标 (带宽/IOPS/延迟)
- 返回 metrics 字典
- 抛出异常 → ERROR 状态

**3. validate() - 结果判定**
- 对比目标阈值 (量化达标比例)
- record_failure() 记录不达标项
- **检查 Postcondition (健康状态)**
- 返回 True (框架根据 failures 判定最终状态)

**4. teardown() - 清理现场**
- 父类自动清理测试文件
- 根据模式决定是否保留 (开发模式保留便于调试)
- 大文件 (>100MB) 会提示手动删除

### 2.2 状态判定五元组

| 状态 | 触发条件 | 后续动作 |
|------|----------|----------|
| **PASS** | 执行完成，无失败记录 | 继续下一个用例 |
| **FAIL** | record_failure() 或 FailStop | 继续/停止 (取决于模式) |
| **ERROR** | 异常未捕获 (FIO 崩溃、IO 错误) | 停止当前用例 |
| **SKIP** | setup() 返回 False | 跳过，不执行 |
| **ABORT** | 用户中断、超时 | 立即终止 |

---

## 三、失败处理模式

### 3.1 Fail-Continue (软失败)

**适用场景**: 性能测试、非关键功能验证

**机制**:
- 使用 record_failure() 记录失败
- 测试继续执行
- 失败项记录在 result['failures'] 中
- 最终状态由框架根据是否有 failures 判定
- 始终返回 True

### 3.2 Fail-Stop (硬失败)

**适用场景**: 功能测试、数据完整性验证、硬件故障

**机制**:
- 抛出 FailStop("原因")
- 立即终止当前测试用例
- 套件也停止执行 (不再运行后续用例)
- 状态标记为 FAIL

**典型场景**:
- 设备返回 IO 错误
- 严重数据损坏
- 硬件损伤风险

---

## 四、核心实现模式

### 4.1 工具封装模式

FIO 工具封装提供两种使用方式：

**便捷 API**: 针对常见测试场景 (顺序读/写、随机读/写、混合读写) 提供专用方法

**配置对象**: 使用 FIOConfig 对象传递完整配置，支持自定义参数

### 4.2 健康检查模式

**Precondition (setup 中)**:
- 记录测试前健康状态基线
- 包括设备状态、坏块数量、健康百分比等

**Postcondition (validate 中)**:
- 对比测试前后健康状态，包含 3 项检查：
  - **设备健康状态 (status)**: OK → 非 OK = 记录失败
  - **Critical Warning 标志**: 新增警告 = 记录失败
  - **Pre-EOL 信息**: 从 0x00 → 非 0x00 = 记录失败 (设备接近寿命终点)
- **坏块增加 = FailStop (最高优先级)**
- 健康状态异常 = 记录警告但不中断
- 缺少健康数据 = 跳过检查 (非致命)

### 4.3 结果判定模式 (量化达标比例)

性能验证采用量化达标比例方式：

**带宽/IOPS**: 计算实际值/目标值的百分比
- ≥100%: 达标 ✅
- 90%-100%: 可接受 ⚠️
- <90%: 显著不达标，记录失败

**延迟**: 计算实际值/限制值的百分比
- ≤100%: 达标 ✅
- >100%: 超出限制，记录失败

---

## 五、测试用例命名规范

### 5.1 命名格式

```plaintext
t_<模块>_<CamelCaseDescription>_<序号>.py
```

### 5.2 示例

| 文件名 | 说明 | 继承类 |
|--------|------|--------|
| t_perf_SeqReadBurst_001.py | 性能测试：顺序读突发 | PerformanceTestCase |
| t_perf_SeqWriteBurst_002.py | 性能测试：顺序写突发 | PerformanceTestCase |
| t_perf_RandReadBurst_003.py | 性能测试：随机读突发 | PerformanceTestCase |
| t_perf_RandWriteBurst_004.py | 性能测试：随机写突发 | PerformanceTestCase |
| t_perf_MixedRw_005.py | 性能测试：混合读写 | PerformanceTestCase |
| t_qos_LatencyPercentile_001.py | QoS 测试：延迟百分位 | TestCase (独立实现) |
| t_rel_PowerLossRecovery_001.py | 可靠性测试：掉电恢复 (待开发) | - |

> **注意**: QoS 测试用例直接继承 TestCase，不继承 PerformanceTestCase。QoS 测试有自己的延迟分布记录、JSON 导出功能。

---

## 六、测试流程框架

### 6.1 模式参数传递链路

```plaintext
CLI 参数 (--mode=production)
   ↓
systest.py 解析 → 传递 mode 参数
   ↓
runner.py 加载测试用例 → TestCase.__init__(mode=...)
   ↓
根据 mode 调整测试参数 (如 fio_runtime: 60s → 300s)
```

### 6.2 单次测试流程

```plaintext
用户命令
   ↓
CLI 入口 (systest.py)
   ↓
解析参数 (suite/test/all/batch/mode...)
   ↓
加载配置 (runtime.json / --config)
   ↓
确定测试模式 (CLI > 环境变量 > 配置文件 > 默认 development)
   ↓
初始化组件 (Runner/Collector/Reporter/Logger)
   ↓
环境检测 (设备/空间/FIO/权限)
   ↓
动态加载测试套件 (按 --suite 参数)
   ↓
┌─────────────────────────────────────────────┐
│  对每个测试用例执行：                        │
│                                             │
│  1. setup()                                 │
│     ├─ 检查设备存在 (支持自动检测)           │
│     ├─ 检查可用空间 (≥2GB)                   │
│     ├─ 检查 FIO 工具                          │
│     ├─ 检查权限                              │
│     ├─ 记录健康基线 (Precondition)           │
│     └─ 创建测试文件路径                      │
│                                             │
│  2. execute()                               │
│     ├─ 调用 FIO 执行测试                      │
│     ├─ 解析性能指标 (带宽/IOPS/延迟)         │
│     └─ 返回 metrics 字典                      │
│                                             │
│  3. validate()                              │
│     ├─ 对比目标阈值 (量化达标比例)           │
│     ├─ record_failure() 记录不达标项         │
│     ├─ 检查 Postcondition (健康状态)         │
│     └─ 返回 True (框架判定最终状态)          │
│                                             │
│  4. teardown()                              │
│     └─ 清理测试文件 (根据模式决定)           │
└─────────────────────────────────────────────┘
   ↓
ResultCollector 汇总结果
   ↓
ReportGenerator 生成 HTML/JSON 报告
   ↓
输出到 results/ 和 logs/
```

### 6.3 批量测试流程

**批量测试**: 使用 `--batch` 参数重复执行测试套件

```bash
# 批量测试 3 次，间隔 60 秒
python3 systest/bin/systest.py run --suite performance --batch=3 --interval=60
```

---

## 七、测试模式管理

### 7.1 模式配置优先级

```plaintext
CLI 参数 (--mode) > 环境变量 (SYSTEST_MODE) > 配置文件 (runtime.json) > 默认值 (development)
```

### 7.2 模式差异对比

| 特性 | 开发模式 (Development) | 生产模式 (Production) |
|------|------------------------|----------------------|
| **单次时长** | 60 秒 | 300 秒 |
| **总测试时间** | ~2 分钟 | ~25 分钟 |
| **日志级别** | DEBUG (详细) | INFO (简洁) |
| **报告详细度** | 简略摘要 | 完整详细报告 |
| **测试文件保留** | 保留 (便于调试) | 自动清理 (大文件提示手动删除) |
| **适用场景** | 开发阶段快速迭代 | 部署前最终验证 |

> **说明**: 每个测试用例执行 1 次，不再循环。如需多次测试，使用 `--batch` 参数。

### 7.3 模式切换方法

**方法 1: 命令行切换**
```bash
# 切换到生产模式
python3 systest/bin/systest.py mode --set=production

# 切换回开发模式
python3 systest/bin/systest.py mode --set=development
```

**方法 2: 环境变量 (会话级)**
```bash
export SYSTEST_MODE=production
python3 systest/bin/systest.py run --suite performance
unset SYSTEST_MODE
```

**方法 3: CLI 参数 (一次性覆盖)**
```bash
python3 systest/bin/systest.py run --suite performance --mode=production
```

**方法 4: 配置文件 (持久化)**
编辑 `systest/config/runtime.json` 中的 mode 字段

### 7.4 查看当前模式

```bash
python3 systest/bin/systest.py mode
```

输出示例：
```plaintext
=== Current Test Mode ===
Mode: Development
Config file: /path/to/systest/config/runtime.json
```

---

## 八、配置管理

### 8.1 配置文件

**systest/config/runtime.json**:
```json
{
  "mode": "development",
  "device": "/dev/sda",
  "test_dir": "/mapdata/ufs_test",
  "modes": {
    "development": {
      "test_duration": 60,
      "log_level": "DEBUG",
      "keep_files": true
    },
    "production": {
      "test_duration": 300,
      "log_level": "INFO",
      "keep_files": false
    }
  }
}
```

### 8.2 常量配置

**systest/core/constants.py** 定义所有魔法数字：

```python
@dataclass
class Config:
    # 路径安全
    ALLOWED_TEST_DIR_PREFIXES = ['/tmp', '/mapdata']
    
    # 日志阈值
    LARGE_LOG_THRESHOLD_MB = 100
    HUGE_LOG_THRESHOLD_MB = 500
    
    # 空间要求
    MIN_AVAILABLE_SPACE_GB = 2.0
    
    # 测试模式
    DEFAULT_MODE = 'development'
    PRODUCTION_RUNTIME = 300
    DEVELOPMENT_RUNTIME = 60
```

### 8.3 命令行覆盖

```bash
# 指定设备
python3 systest/bin/systest.py run --suite performance --device=/dev/ufs0

# 指定测试目录
python3 systest/bin/systest.py run --suite performance --test-dir=/data/test

# 批量测试 (3 次，间隔 60 秒)
python3 systest/bin/systest.py run --suite performance --batch=3 --interval=60

# 详细日志
python3 systest/bin/systest.py run --suite performance -v

# 指定模式
python3 systest/bin/systest.py run --suite performance --mode=production
```

---

## 九、报告输出结构

### 9.1 目录结构

```plaintext
results/SysTest_performance_20260410_094600/
├── summary.json       # 汇总结果
├── report.html        # HTML 报告 (含图表)
├── report.md          # Markdown 报告
└── qos_latency_distribution.json  # QoS 延迟分布数据
```

### 9.2 汇总结果格式

```json
{
  "test_id": "SysTest_performance_20260410_094600",
  "mode": "development",
  "start_time": "2026-04-10T09:46:00+08:00",
  "end_time": "2026-04-10T09:48:31+08:00",
  "duration_seconds": 151.2,
  "total_cases": 5,
  "passed": 5,
  "failed": 0,
  "skipped": 0,
  "pass_rate": 100.0
}
```

### 9.3 QoS 延迟分布数据

QoS 测试会生成独立的延迟分布 JSON 文件，包含完整百分位数据：

```json
{
  "test_name": "qos_latency_percentile",
  "timestamp": "2026-04-10T09:46:00+08:00",
  "device": "/dev/sda",
  "distribution": {
    "p50": 25.3,
    "p90": 45.1,
    "p95": 67.8,
    "p99": 120.5,
    "p99.9": 250.3,
    "p99.99": 400.1,
    "p99.999": 4800.2,
    "min": 5.2,
    "max": 15000.0,
    "mean": 35.7,
    "stddev": 15.3
  }
}
```

---

## 十、基类复用模式

### 10.1 PerformanceTestCase 基类

所有性能测试用例继承自 PerformanceTestCase，只需定义测试特定参数：

**必须定义的属性**:
- name: 测试名称
- description: 测试描述
- target_bandwidth_mbps / target_iops: 性能目标
- max_avg_latency_us / max_tail_latency_us: 延迟限制
- fio_rw / fio_bs / fio_size 等：FIO 配置

**基类提供**:
- ✅ 通用 setup() (前置条件检查)
- ✅ 通用 execute_fio_test() (FIO 执行)
- ✅ 通用 validate_performance() (性能验证)
- ✅ 自动设备检测
- ✅ 量化达标比例输出
- ✅ 根据测试模式自动调整 runtime

### 10.2 QoS 测试用例 (独立实现)

QoS 测试用例 (`t_qos_LatencyPercentile_001.py`) 直接继承 TestCase，不继承 PerformanceTestCase。

**特点**:
- 有自己的延迟分布记录和 JSON 导出功能
- 包含完整的百分位数据 (p50/p90/p95/p99/p99.9/p99.99/p99.999)
- 生产模式下 runtime 自动调整为 ≥300s

---

## 十一、CLI 命令参考

### 11.1 环境管理

```bash
# 检查环境并保存配置
python3 systest/bin/systest.py check-env --save-config

# 查看当前配置
python3 systest/bin/systest.py config --show

# 设置设备路径
python3 systest/bin/systest.py config --device=/dev/sda

# 重置配置
python3 systest/bin/systest.py config --reset
```

### 11.2 模式管理

```bash
# 查看当前模式
python3 systest/bin/systest.py mode

# 切换到生产模式
python3 systest/bin/systest.py mode --set=production

# 切换回开发模式
python3 systest/bin/systest.py mode --set=development
```

### 11.3 测试执行

```bash
# 运行性能测试套件
python3 systest/bin/systest.py run --suite performance

# 运行 QoS 测试套件
python3 systest/bin/systest.py run --suite qos

# 运行所有套件
python3 systest/bin/systest.py run --all

# 运行单个测试
python3 systest/bin/systest.py run --test t_perf_SeqReadBurst_001

# 批量测试 (3 次，间隔 60 秒)
python3 systest/bin/systest.py run --suite performance --batch=3 --interval=60

# 详细日志模式
python3 systest/bin/systest.py run --suite performance -v

# 指定模式
python3 systest/bin/systest.py run --suite performance --mode=production
```

### 11.4 结果查看

```bash
# 列出所有测试
python3 systest/bin/systest.py list

# 列出指定 suite 的测试
python3 systest/bin/systest.py list --suite performance

# 查看最新报告
python3 systest/bin/systest.py report --latest

# 列出所有可用报告
python3 systest/bin/systest.py report --list

# 查看指定报告
python3 systest/bin/systest.py report --id=SysTest_performance_20260410_094600

# 导出 CSV
python3 systest/bin/systest.py report --latest --export-csv
```

### 11.5 基线对比

```bash
# 对比两个测试结果
python3 systest/bin/systest.py compare-baseline \
  --baseline1 results/gold/ \
  --baseline2 results/current/
```

---

## 十二、测试套件概览

### 12.1 Performance 套件 (5 个用例)

| 测试用例 | 块大小 | 队列深度 | 目标 | 时长 |
|----------|--------|----------|------|------|
| Seq Read | 128K | 1 | ≥2100 MB/s | ~5s |
| Seq Write | 128K | 1 | ≥1650 MB/s | ~5s |
| Rand Read | 4K | 32 | ≥120K IOPS | ~5s |
| Rand Write | 4K | 32 | ≥100K IOPS | ~5s |
| Mixed RW | 4K | 32 | ≥150K IOPS (70% 读) | ~5s |

> **注意**: 目标值可在各测试用例类属性中调整。

### 12.2 QoS 套件 (1 个用例)

| 测试用例 | 块大小 | 队列深度 | 目标 | 时长 |
|----------|--------|----------|------|------|
| Latency Percentile | 4K | 1 | p50<50μs, p99<200μs, p99.99<500μs | ~5s |

### 12.3 Reliability 套件 (待开发)

- [ ] Power Loss Recovery (掉电恢复)
- [ ] Endurance Test (耐久性测试)
- [ ] Data Retention (数据保持)

---

## 十三、核心经验沉淀

### 13.1 设计原则

1. **Precondition 是测试方法说明，不写死具体值**
   - 写检查逻辑 (如"空间≥2GB")，不写死路径/设备名
   - 配置通过 runtime.json 或命令行注入

2. **Postcondition 必须检查硬件损伤**
   - 坏块增加 = FailStop (最高优先级)
   - 健康状态异常 = 记录警告但不中断
   - 缺少健康数据 = 跳过检查 (非致命)
   - **包含 3 项检查**: status、Critical Warning、Pre-EOL

3. **PASS/FAIL 四维度判定**

4. **测试文件统一管理**
   - 统一放在 test_dir 下
   - 防止路径遍历攻击
   - 父类自动清理 (开发模式可保留)
   - 大文件 (>100MB) 会提示手动删除

5. **FIO 执行必须带 ramp_time**
   - 避免冷启动数据污染
   - 推荐预热时间 = 10 秒

6. **安全验证**
   - 测试目录必须在允许前缀内（/tmp, /mapdata）
   - 路径验证逻辑：先创建目录，再验证路径
   - 防止路径遍历攻击

### 13.2 性能测试特殊规则

- **不直接返回 FAIL**: 性能测试始终返回 True
- **阈值合规性记录**: 通过 record_failure() 记录
- **量化达标比例**: 输出 (达标率 XX%) 便于分析
- **90% 容忍度**: <90% 目标值才记录失败

### 13.3 日志系统规范

- **统一日志文件**: 只创建 .log 文件（不再创建 _error.log）
- **完整信息**: 日志包含时间戳（毫秒级）、级别、完整路径、行号
- **错误记录**: ERROR 级别自动输出堆栈跟踪
- **终端输出**: 简洁彩色输出，方便调试
- **文件输出**: 详细完整路径，方便追溯

---

## 十四、故障排查

### 14.1 常见问题

| 问题 | 解决方案 |
|------|----------|
| 设备不存在 | lsblk 查看可用设备 → systest.py config --device=/dev/sda |
| 可用空间不足 | df -h 检查 → rm -rf /mapdata/ufs_test/* |
| FIO 未安装 | apt-get install fio |
| 权限不足 | chmod 666 /dev/sda 或 sudo 运行 |
| 导入错误 | 确认 systest/__init__.py 存在 |
| 模式配置不生效 | 检查优先级：CLI > 环境变量 > 配置文件 > 默认值 (development) |
| mode 参数无法传递 | 确认测试用例 __init__ 接收 mode 参数 |

### 14.2 日志定位

```bash
# 查看最新日志
tail -f logs/SysTest_*.log

# 搜索错误
grep -i "error" logs/SysTest_*.log

# 查看失败详情
grep -A5 "record_failure" logs/SysTest_*.log

# 查看模式信息
grep "测试模式" logs/SysTest_*.log
```

---

## 十五、扩展指南

### 15.1 添加新测试套件

1. 在 suites/ 下创建新目录
2. 创建 `__init__.py` 导出测试类
3. runner 根据 `--suite` 参数动态加载

### 15.2 添加新测试用例

1. 继承基类 (PerformanceTestCase 或 TestCase)
2. 定义 name 和 description
3. 定义性能目标 (如适用)
4. 定义 FIO 配置 (如适用)
5. 可选：覆盖特定方法 (setup/execute/validate)

### 15.3 添加新的 FIO 模式

在 fio_wrapper.py 中添加新方法，遵循现有模式：
- 接收 FIOConfig 配置对象
- 执行 FIO 命令
- 解析返回结果
- 返回 FIOMetrics 对象

---

## 十六、版本历史

### v2.2 (2026-04-10)
- ✅ 移除循环测试逻辑（loop_count 统一为 1）
- ✅ 统一日志系统（移除空 error.log 文件）
- ✅ 增强安全验证（路径遍历防护）
- ✅ 完善常量配置（constants.py）
- ✅ 统一终端输出（移除 print，使用 logger）
- ✅ 修复导入路径（统一使用 systest.core.*）
- ✅ 移除 FIO 安装步骤（假设已预装）
- ✅ 移除 GitHub 地址引用

### v2.1 (2026-04-10)
- ✅ 补充测试发现机制说明
- ✅ 补充模式参数传递链路
- ✅ 补充 QoS 测试独立实现说明
- ✅ 补充 Postcondition 3 项检查维度
- ✅ 补充测试文件清理逻辑细节
- ✅ 补充 QoS 延迟分布数据格式
- ✅ 统一入口文件名称为 systest.py
- ✅ 增加"5 分钟快速上手"章节

### v2.0 (2026-04-10)
- ✅ 新增开发/生产模式切换功能
- ✅ 支持 CLI 参数、环境变量、配置文件三种配置方式
- ✅ 增强健康检查 (Precondition/Postcondition)
- ✅ 新增 mode 子命令
- ✅ 优化报告结构

### v1.0 (2026-04-09)
- ✅ 初始版本
- ✅ 四层架构设计
- ✅ 测试用例生命周期标准化
- ✅ Fail-Continue/Fail-Stop 失败处理
- ✅ 性能测试基类复用

---

**文档维护**: 随框架迭代同步更新  
**负责人**: 雪原  
**反馈渠道**: 飞书群聊
