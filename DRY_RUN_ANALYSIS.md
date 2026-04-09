# Dry-Run 模式去留分析报告

## 📊 Dry-Run 当前用途

### 1. CLI 参数 `--dry-run`

**位置**: `systest/bin/systest_cli.py:557`

**用途**:
```bash
python3 systest/bin/systest_cli.py run --suite=performance --dry-run
```

**功能**:
- 验证测试框架能正常工作
- 不实际执行 FIO 测试
- 验证测试用例可以正确加载和解析

**使用场景**:
- CI/CD 环境验证
- 开发调试
- 部署前验证

---

### 2. TestRunner 初始化

**位置**: `systest/core/runner.py:424`

**用途**:
```python
runner = TestRunner(dry_run=True)
```

**功能**:
- 使用临时参数（`/dev/sda`, `/tmp/systest_dryrun`）
- 跳过环境检测
- 跳过配置文件加载
- 仅验证框架结构

**使用场景**:
- 查找测试用例所属 suite
- 列出可用测试套件
- CI 环境验证

---

### 3. FIO Wrapper

**位置**: `systest/tools/fio_wrapper.py:279`

**用途**:
```python
def run(self, config: FIOConfig, dry_run: bool = False, ...)
```

**功能**:
- 打印 FIO 命令但不执行
- 返回模拟数据（mock metrics）

**使用场景**:
- 验证 FIO 命令生成
- 测试框架流程

---

### 4. TestRunner.run_suite

**位置**: `systest/core/runner.py:724`

**用途**:
```python
if self.dry_run:
    # 验证测试用例可以正确导入和解析
```

**功能**:
- 验证测试文件存在
- 验证 Python 语法正确
- 验证 Test 类存在
- 验证参数可以解析
- 不实际执行测试

**使用场景**:
- CI/CD 验证
- 开发调试

---

## 🎯 实际使用情况

### 当前环境（开发板）

**现状**:
- ✅ FIO 已安装（v3.36）
- ✅ 可以实际运行 FIO 测试
- ✅ 开发模式测试仅需 5 秒
- ✅ 完整测试仅需 31 秒

**Dry-Run 价值**: ❌ **几乎为零**

理由：
1. 实际测试已经很快（5-31 秒）
2. 开发板环境稳定
3. 不需要模拟数据

---

### CI/CD 环境

**现状**:
- 检查点中提到 "CI 使用 dry-run 模式"
- 但实际 CI 配置（`.gitlab-ci.yml`）中未使用 `--dry-run`

**Dry-Run 价值**: ⚠️ **有限**

理由：
1. CI 环境如果有 FIO，可以直接运行真实测试
2. 如果没有 FIO，dry-run 只能验证框架结构
3. 实际价值不大

---

## ❌ Dry-Run 的问题

### 1. 代码复杂度

**问题**: Dry-run 逻辑分散在多处
- `runner.py`: 424 行、438 行、724 行
- `fio_wrapper.py`: 279 行、307 行、433 行
- `systest_cli.py`: 135 行、152 行、223 行

**影响**: 增加维护成本

---

### 2. 模拟数据不准确

**位置**: `fio_wrapper.py:433`

```python
def _create_mock_metrics(self, rw_type: str) -> FIOMetrics:
    """Create mock metrics (for dry-run)"""
```

**问题**:
- 模拟数据无法反映真实性能
- 可能掩盖性能问题
- 调试价值有限

---

### 3. 用途被替代

**现状**:
- 开发模式测试仅需 5 秒
- 增强版日志支持完整调试
- 可以直接运行真实测试

**结论**: Dry-run 的验证功能已被快速测试替代

---

## ✅ 建议清除的内容

### 高优先级（可以清除）

1. **CLI 的 `--dry-run` 参数**
   - 文件：`systest_cli.py:557`
   - 相关代码：135 行、152 行
   - 理由：实际测试已经很快，不需要模拟

2. **TestRunner 的 dry_run 参数**
   - 文件：`runner.py:424`
   - 相关代码：429 行、438 行、724 行
   - 理由：功能被快速测试替代

3. **FIO Wrapper 的 dry_run 参数**
   - 文件：`fio_wrapper.py:279`
   - 相关代码：307 行、433 行
   - 理由：可以直接运行真实 FIO

4. **模拟数据函数**
   - 文件：`fio_wrapper.py:433`
   - 函数：`_create_mock_metrics()`
   - 理由：不再需要

---

### 保留的内容

1. **TestRunner.list_suites()**
   - 用途：列出可用测试套件
   - 不需要 dry-run 参数
   - 可以直接实例化 TestRunner

2. **查找测试用例所属 suite**
   - 用途：根据测试名查找 suite
   - 可以改用其他方式实现

---

## 🚀 清除后的替代方案

### 1. 验证框架

**原方案**: `--dry-run`  
**新方案**: 开发模式快速测试
```bash
python3 verify_all_tests.py  # 31 秒验证所有用例
```

### 2. 列出测试套件

**原方案**: `TestRunner(dry_run=True).list_suites()`  
**新方案**: 直接实例化
```python
runner = TestRunner()
suites = runner.list_suites()
```

### 3. CI/CD 验证

**原方案**: dry-run 模式  
**新方案**: 实际运行快速测试
```bash
python3 verify_all_tests.py --ci
```

---

## 📋 清除清单

### 需要删除的代码

| 文件 | 行号 | 内容 | 优先级 |
|------|------|------|--------|
| systest_cli.py | 557 | `--dry-run` 参数定义 | 高 |
| systest_cli.py | 135, 152 | dry_run 参数传递 | 高 |
| runner.py | 424, 429, 438 | dry_run 参数和处理 | 高 |
| runner.py | 724+ | dry_run 执行逻辑 | 高 |
| fio_wrapper.py | 279, 307 | dry_run 参数 | 高 |
| fio_wrapper.py | 433 | `_create_mock_metrics()` | 高 |
| check_env.py | 481-506 | CI dry-run 提示 | 中 |

### 需要更新的文档

| 文件 | 内容 | 优先级 |
|------|------|--------|
| systest_cli.py | help 文档中的 --dry-run 说明 | 中 |
| README.md | 使用示例中的 --dry-run | 低 |
| 其他文档 | 提及 dry-run 的地方 | 低 |

---

## ✅ 结论

**建议**: **清除所有 dry-run 相关代码**

**理由**:
1. ✅ 实际测试已经很快（5-31 秒）
2. ✅ Dry-run 功能被快速测试完全替代
3. ✅ 减少代码复杂度
4. ✅ 提高可维护性
5. ✅ 模拟数据价值有限

**风险**: 低
- CI/CD 可以改用快速测试
- 开发调试可以直接运行真实测试
- 功能完全可替代

---

**分析完成时间**: 2026-04-09 08:38  
**建议**: 立即清除 dry-run 相关代码
