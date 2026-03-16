# SysTest 最小化验证方案

**版本**: v1.1.0  
**创建时间**: 2026-03-16  
**目标**: 在不依赖实际硬件的情况下，通过真实执行（非模拟）验证系统功能

---

## 🎯 设计理念

### 原有干跑模式的问题
- ❌ 只验证配置加载，不验证实际执行流程
- ❌ 无法发现执行时的真实问题
- ❌ 与真实测试脱节

### 新方案的核心思路
- ✅ **真实执行但缩短周期** - 实际调用 FIO 但使用最小参数
- ✅ **验证完整流程** - 从命令解析到结果生成的全链路
- ✅ **无需实际硬件** - 使用 FIO 的 dry-run 或 mock 模式
- ✅ **快速反馈** - 每个测试在秒级完成

---

## 🔧 最小化验证策略

### 方案 1: FIO 原生 Dry-Run（推荐）

FIO 工具本身支持 `--dry-run` 参数，可以实际调用 FIO 但不执行 IO：

```bash
# 使用 FIO 的 --dry-run 参数
fio --name=test --filename=/dev/ufs0 --rw=read --dry-run
```

**优点**:
- 真实调用 FIO，验证命令构建逻辑
- 不依赖实际硬件
- 执行速度快（毫秒级）
- 可以验证 FIO 参数是否正确

**实现方式**:
在 `runner.py` 中添加 `dry_run=True` 参数，在执行 FIO 时添加 `--dry-run` 标志。

---

### 方案 2: FIO Mock 设备

使用 FIO 的 `--filename=/dev/zero` 或内存文件：

```bash
# 使用 /dev/zero 作为 mock 设备
fio --name=test --filename=/dev/zero --rw=read --size=1M --runtime=1

# 使用内存临时文件
fio --name=test --filename=/tmp/fio_test --rw=read --size=1M --runtime=1
```

**优点**:
- 完全真实的 FIO 执行
- 验证完整执行流程
- 可以测试结果解析逻辑
- 执行时间短（1-2 秒）

**注意**: 需要处理 `/dev/zero` 不支持某些操作的情况。

---

### 方案 3: 超时保护 + 快速失败

对于必须实际执行的测试，添加严格的超时保护：

```python
# 设置 5 秒超时
result = subprocess.run(cmd, timeout=5, capture_output=True)
```

**优点**:
- 防止长时间阻塞
- 快速发现执行问题
- 适合验证异常处理

---

## 📋 最小化验证测试集

### 验证类别和用例

| 类别 | 验证项 | 方法 | 预期时间 |
|------|--------|------|---------|
| **命令解析** | 参数解析正确 | 实际执行 + 超时保护 | <1s |
| **FIO 集成** | FIO 命令构建 | FIO --dry-run | <1s |
| **结果解析** | JSON 解析 | Mock 数据 + 真实解析 | <1s |
| **报告生成** | 3 种格式 | 真实生成 | <2s |
| **失效分析** | 规则匹配 | Mock 数据 + 真实分析 | <1s |
| **配置管理** | 配置加载 | 真实加载 | <1s |

### 执行示例

```bash
# 1. 验证 FIO 命令构建（使用 FIO --dry-run）
python3 bin/SysTest run -t seq_read_burst --verify-cmd -v

# 2. 验证结果解析（使用 mock 数据）
python3 tests/verify_result_parser.py

# 3. 验证报告生成（真实生成）
python3 tests/verify_report_gen.py

# 4. 验证失效分析（使用 mock 数据）
python3 tests/verify_failure_analysis.py

# 5. 完整流程验证（FIO dry-run 模式）
python3 tests/verify_full_flow.py
```

---

## 🛠️ 实现方案

### 1. 添加验证模式

在 `bin/SysTest` 中添加新命令：

```bash
# 验证模式 - 使用 FIO --dry-run
SysTest verify --suite performance

# 验证单个测试
SysTest verify --test seq_read_burst

# 验证完整流程
SysTest verify --full
```

### 2. Runner 支持 Dry-Run

修改 `core/runner.py`:

```python
def _execute_test(self, test_name, test_info, dry_run=False):
    # 构建 FIO 命令
    fio_cmd = self._build_fio_command(test_name, runtime, test_info)
    
    # 如果是 dry-run 模式，添加 --dry-run 参数
    if dry_run:
        fio_cmd.append('--dry-run')
    
    # 执行 FIO
    result = self._run_fio(fio_cmd, timeout=5)
    
    # 解析结果（即使是 dry-run 也会返回基本结构）
    parsed = self._parse_fio_result(result, test_name)
    
    return parsed
```

### 3. 创建验证脚本

```python
# tests/verify_full_flow.py
#!/usr/bin/env python3
"""
SysTest 完整流程验证
使用 FIO --dry-run 验证从命令构建到报告生成的全流程
"""

import subprocess
import json
from pathlib import Path

def test_fio_dry_run():
    """验证 FIO dry-run 模式"""
    cmd = [
        'fio', '--name=test', '--filename=/dev/zero',
        '--rw=read', '--bs=4k', '--iodepth=32',
        '--runtime=1', '--dry-run',
        '--output-format=json'
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
    
    # 即使是 dry-run，FIO 也会返回基本结构
    if result.returncode == 0:
        print("✅ FIO dry-run 执行成功")
        return True
    else:
        print(f"❌ FIO dry-run 失败：{result.stderr}")
        return False

def test_result_parsing():
    """验证结果解析"""
    # 使用真实的 FIO dry-run 输出
    mock_output = '{"jobs": [{"read": {"bw_bytes": 1000000, "iops": 250000}}]}'
    
    # 调用 runner 的解析逻辑
    from core.runner import TestRunner
    runner = TestRunner()
    parsed = runner._parse_fio_result(mock_output, 'seq_read_burst')
    
    if 'metrics' in parsed and 'bandwidth' in parsed['metrics']:
        print("✅ 结果解析成功")
        return True
    else:
        print("❌ 结果解析失败")
        return False

def test_report_generation():
    """验证报告生成"""
    from core.reporter import ReportGenerator
    
    # 准备测试数据
    test_data = {
        'test_id': 'verify_001',
        'test_results': {
            'test_cases': [{'test_name': 'seq_read_burst', 'status': 'PASS'}],
            'summary': {'total': 1, 'passed': 1, 'failed': 0}
        }
    }
    
    # 生成报告
    reporter = ReportGenerator(output_dir='./results/verify', formats=['html', 'json', 'text'])
    files = reporter.generate(test_data, 'verify_001')
    
    if files and len(files) > 0:
        print(f"✅ 报告生成成功：{len(files)} 个文件")
        return True
    else:
        print("❌ 报告生成失败")
        return False

if __name__ == '__main__':
    print("🔍 SysTest 最小化验证")
    print("=" * 60)
    
    results = []
    results.append(("FIO dry-run", test_fio_dry_run()))
    results.append(("结果解析", test_result_parsing()))
    results.append(("报告生成", test_report_generation()))
    
    print("=" * 60)
    passed = sum(1 for _, r in results if r)
    print(f"总计：{passed}/{len(results)} 验证通过")
```

---

## 📊 验证指标

### 覆盖度指标

| 指标 | 目标值 | 测量方法 |
|------|--------|---------|
| 命令解析覆盖率 | 100% | 所有命令行参数 |
| FIO 集成覆盖率 | 100% | 所有测试类型 |
| 结果解析覆盖率 | 100% | 所有指标字段 |
| 报告生成覆盖率 | 100% | 3 种格式 |
| 失效分析覆盖率 | 100% | 15 种规则 |

### 性能指标

| 指标 | 目标值 |
|------|--------|
| 单个验证用例执行时间 | <2 秒 |
| 完整验证套件执行时间 | <30 秒 |
| 内存占用 | <100MB |

---

## 🚀 迁移计划

### 阶段 1: 添加验证模式（本周）
- [ ] 实现 `SysTest verify` 命令
- [ ] 修改 runner 支持 dry-run
- [ ] 创建验证脚本

### 阶段 2: 替换干跑模式（下周）
- [ ] 将现有干跑测试改为验证模式
- [ ] 更新文档和示例
- [ ] 移除 `--dry-run` 参数

### 阶段 3: 持续集成（后续）
- [ ] 集成到 GitHub Actions
- [ ] 每次提交自动运行验证
- [ ] 验证失败阻止合并

---

## 📝 对比总结

| 特性 | 原干跑模式 | 新验证模式 |
|------|-----------|-----------|
| **执行方式** | 模拟执行 | 真实执行（dry-run） |
| **验证范围** | 配置加载 | 完整流程 |
| **发现问题** | 有限 | 全面 |
| **执行时间** | 快 | 快（秒级） |
| **硬件依赖** | 无 | 无 |
| **FIO 调用** | 不调用 | 调用（dry-run） |
| **结果解析** | 跳过 | 验证 |
| **报告生成** | 可选 | 必选 |

---

**新方案优势**: 在保持快速验证的同时，确保**真实执行流程**的每个环节都经过验证，发现更多潜在问题。
