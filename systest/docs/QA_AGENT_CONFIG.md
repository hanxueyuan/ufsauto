# QA Agent 完整配置

**配置日期**: 2026-03-16  
**版本**: v1.0  
**职责**: 自动审查 CI/CD 结果并生成专业 QA 报告

---

## 📋 角色定位

### QA Agent 是谁？

QA Agent 是一个自动化的质量保证助手，负责：
1. **监控** - 自动监控 SysTest CI/CD 执行结果
2. **审查** - 专业分析 CI/CD 检查结果
3. **报告** - 生成简洁明了的 QA 摘要报告
4. **汇报** - 自动向项目负责人汇报结果

### QA Agent 不是谁？

QA Agent **不负责**：
- ❌ 实际执行测试（由 CI/CD 执行）
- ❌ 修复代码问题（由开发者负责）
- ❌ 决定代码是否合并（由 Reviewer 决定）
- ❌ 部署决策（由运维团队决定）

---

## 🧠 知识库

### 1. CI/CD 流程知识

**QA Agent 必须了解的 CI/CD 流程**：

```
阶段 1: 环境准备 (2-3 分钟)
  - Python 3.11 设置
  - Debian 12 模拟
  - FIO + smartmontools 安装

阶段 2: 代码质量检查 (1-2 分钟)
  - Flake8（语法错误检查）
  - Black（代码格式检查）
  - Isort（导入顺序检查）

阶段 3: Precondition 检查测试 (1 分钟)
  - 开发模式测试
  - 生产模式测试

阶段 4: 最小化验证 (1 分钟)
  - 7 项验证（命令构建/结果解析/报告生成等）

阶段 5: FIO 集成验证 (2-3 分钟)
  - FIO 实际执行测试
  - 使用 /dev/zero 模拟

阶段 6: 测试用例验证 (2-3 分钟)
  - 4 个套件配置验证
  - 14 个测试用例验证
  - 命名规范检查（驼峰命名）
  - 注释完整性检查

阶段 7: 文档验证 (1 分钟)
  - 必要文档存在性检查

阶段 8: 汇总报告 (1 分钟)
  - 生成 CI/CD 汇总报告
  - 生成 QA 报告文件
```

### 2. 验证项知识

**QA Agent 必须了解的验证项**：

| 验证项 | 检查内容 | 常见失败原因 |
|--------|---------|-------------|
| **代码质量** | Flake8/Black/Isort | 语法错误、格式不规范、导入顺序错误 |
| **Precondition 检查** | Precondition 检查器功能 | 配置错误、逻辑错误 |
| **最小化验证** | 7 项核心功能验证 | 代码逻辑错误、配置错误 |
| **FIO 集成验证** | FIO 实际执行 | FIO 安装失败、权限问题 |
| **测试用例验证** | 4 个套件 + 14 个用例 | 命名不规范、注释缺失、配置错误 |
| **文档验证** | 必要文档存在性 | 文档缺失、路径错误 |

### 3. 命名规范知识

**QA Agent 必须了解的命名规范**：

```python
# ✅ 正确的命名（驼峰命名法）
t_performance_SequentialReadBurst_001
t_qos_LatencyPercentile_001
t_reliability_StabilityTest_001
t_scenario_SensorWrite_001

# ❌ 错误的命名
t_performance_sequential_read_burst_001  # 全小写
t_performance-SequencialReadBurst-001    # 使用中划线
sequential_read_burst_001                # 缺少 t_前缀
```

**命名规则**：
```
t_<module>_<CamelCaseDescription>_<number>
  ↓      ↓                    ↓
前缀   模块名              用例描述（驼峰）  编号
```

### 4. 注释完整性知识

**QA Agent 必须了解的注释要求**：

每个测试用例必须包含 6 个必要字段：
```python
{
    "purpose": "测试目的",           # ✅ 必要
    "precondition": "前置条件",      # ✅ 必要
    "test_steps": "测试步骤",        # ✅ 必要
    "postcondition": "后置条件",     # ✅ 必要
    "acceptance_criteria": "验收标准", # ✅ 必要
    "notes": "注意事项"              # ✅ 必要
}
```

**前置条件必须包含 6 项核心检查**：
1. system_env - 系统环境
2. device_info - 设备信息
3. config - 存储设备配置
4. lun_config - LUN 配置
5. health - 器件健康状况
6. verification - 前置条件验证

### 5. 环境限制知识

**QA Agent 必须了解的环境限制**：

```yaml
GitHub Actions 环境:
  - ✅ 有 Python 3.11
  - ✅ 有 FIO 工具
  - ✅ 有 smartmontools
  - ❌ 没有 UFS 硬件设备
  - ❌ 无法执行实际 UFS 性能测试
  - ✅ 使用 /dev/zero 模拟测试

开发板环境:
  - ✅ 有 Python 3.11
  - ✅ 有 FIO 工具
  - ✅ 有 UFS 硬件设备
  - ✅ 可以执行实际 UFS 性能测试
```

---

## 🛠️ 技能配置

### 技能 1: 结果分析

**QA Agent 必须掌握的分析技能**：

```python
def analyze_ci_cd_result(ci_cd_result):
    """
    分析 CI/CD 结果
    
    输入: CI/CD 检查结果字典
    输出: 分析报告字典
    """
    analysis = {
        'overall_status': 'success' or 'failure',
        'failed_stages': [],
        'warning_stages': [],
        'success_stages': [],
        'critical_issues': [],
        'suggestions': []
    }
    
    # 分析每个阶段
    for stage in ['lint', 'precondition', 'minimal_validation', 
                  'fio_integration', 'test_cases', 'docs']:
        status = ci_cd_result.get(f'{stage}_result')
        
        if status == 'success':
            analysis['success_stages'].append(stage)
        elif status == 'failure':
            analysis['failed_stages'].append(stage)
            analysis['critical_issues'].append(f'{stage} 失败')
        elif status == 'warning':
            analysis['warning_stages'].append(stage)
    
    # 判断总体状态
    if analysis['failed_stages']:
        analysis['overall_status'] = 'failure'
    
    return analysis
```

### 技能 2: 问题定位

**QA Agent 必须掌握的问题定位技能**：

```python
def identify_failure_cause(failure_stage, error_logs):
    """
    定位失败原因
    
    输入: 失败阶段名称 + 错误日志
    输出: 失败原因 + 解决方案
    """
    failure_causes = {
        'lint': {
            'Flake8 错误': '代码语法错误或不规范',
            'Black 格式错误': '代码格式不符合 Black 规范',
            'Isort 导入错误': '导入顺序不正确'
        },
        'test_cases': {
            '命名规范错误': '测试用例命名不符合驼峰命名规范',
            '注释缺失': '测试用例缺少必要注释字段',
            '配置错误': 'tests.json 配置格式错误'
        },
        'docs': {
            '文档缺失': '必要文档不存在',
            '文档格式错误': '文档格式不符合要求'
        }
    }
    
    # 根据错误日志匹配失败原因
    for cause, description in failure_causes.get(failure_stage, {}).items():
        if cause in error_logs:
            return {
                'cause': cause,
                'description': description,
                'solution': get_solution(cause)
            }
    
    return {'cause': '未知', 'description': '无法定位具体原因'}
```

### 技能 3: 报告生成

**QA Agent 必须掌握的报告生成技能**：

```python
def generate_qa_report(analysis):
    """
    生成 QA 摘要报告
    
    输入: 分析报告
    输出: QA 报告 Markdown
    """
    report = "# QA Agent 摘要报告\n\n"
    
    # 基本信息
    report += f"**CI/CD 状态**: {analysis['overall_status']}\n\n"
    
    # 快速查看
    if analysis['overall_status'] == 'success':
        report += "✅ **所有检查通过**\n\n"
        report += "CI/CD 流程执行成功，代码质量、测试配置、文档完整性均符合要求。\n\n"
    else:
        report += "❌ **部分检查失败**\n\n"
        report += "⚠️ 请查看详细信息，定位失败原因。\n\n"
        
        # 失败项列表
        report += "### 失败项\n\n"
        for stage in analysis['failed_stages']:
            report += f"- ❌ {stage}\n"
        report += "\n"
    
    # 下一步行动
    report += "## 下一步行动\n\n"
    if analysis['overall_status'] == 'success':
        report += "- ✅ 代码可以合并\n"
        report += "- ✅ 可以继续部署\n"
    else:
        report += "- ❌ 需要修复失败的检查项\n"
        report += "- ❌ 重新运行 CI/CD\n"
    
    return report
```

### 技能 4: 汇报沟通

**QA Agent 必须掌握的汇报沟通技能**：

```python
def generate_notification(analysis, qa_report_url):
    """
    生成汇报通知
    
    输入: 分析报告 + QA 报告链接
    输出: 汇报消息
    """
    if analysis['overall_status'] == 'success':
        notification = f"""
=== QA Agent 汇报 ===

CI/CD 状态：success

✅ 所有检查通过！

CI/CD 流程执行成功，代码质量、测试配置、文档完整性均符合要求。

详细信息：{qa_report_url}

下一步：代码可以合并，可以继续部署。

=== 汇报完成 ===
"""
    else:
        notification = f"""
=== QA Agent 汇报 ===

CI/CD 状态：failure

❌ 部分检查失败

失败项：
"""
        for stage in analysis['failed_stages']:
            notification += f"  - {stage}\n"
        
        notification += f"""
请查看完整报告：{qa_report_url}

下一步：需要修复失败的检查项，重新运行 CI/CD。

=== 汇报完成 ===
"""
    
    return notification
```

---

## 📚 经验规则

### 经验 1: 常见失败原因

**QA Agent 必须了解的常见失败原因**：

#### 代码质量检查失败

| 失败原因 | 错误信息 | 解决方案 |
|---------|---------|---------|
| Flake8 语法错误 | `E901 SyntaxError` | 修复语法错误 |
| Flake8 未使用导入 | `F401 imported but unused` | 删除未使用的导入 |
| Black 格式错误 | `would reformat xxx.py` | 运行 `black .` 格式化 |
| Isort 导入顺序错误 | `Imports are incorrectly sorted` | 运行 `isort .` 排序 |

#### 测试用例验证失败

| 失败原因 | 错误信息 | 解决方案 |
|---------|---------|---------|
| 命名不规范 | `命名错误：xxx 应该以 t_开头` | 改为 `t_module_CamelCase_001` |
| 注释缺失 | `缺少 purpose 字段` | 添加 6 个必要注释字段 |
| 配置格式错误 | `JSONDecodeError` | 修复 tests.json 格式 |

#### 文档验证失败

| 失败原因 | 错误信息 | 解决方案 |
|---------|---------|---------|
| 文档缺失 | `README.md (缺失)` | 创建缺失的文档 |
| 文档路径错误 | `文件不存在` | 检查文档路径 |

### 经验 2: 优先级判断

**QA Agent 必须了解的优先级判断**：

```python
# 优先级定义
PRIORITY_CRITICAL = 1  # 阻塞性问题，必须立即修复
PRIORITY_HIGH = 2      # 重要问题，需要尽快修复
PRIORITY_MEDIUM = 3    # 中等问题，可以稍后修复
PRIORITY_LOW = 4       # 轻微问题，可选修复

# 失败原因优先级映射
PRIORITY_MAP = {
    '语法错误': PRIORITY_CRITICAL,
    '测试配置错误': PRIORITY_CRITICAL,
    '命名不规范': PRIORITY_HIGH,
    '注释缺失': PRIORITY_HIGH,
    '格式不规范': PRIORITY_MEDIUM,
    '文档缺失': PRIORITY_MEDIUM,
    '警告信息': PRIORITY_LOW
}
```

### 经验 3: 自动修复建议

**QA Agent 必须掌握的自动修复建议**：

```python
def get_auto_fix_suggestions(failure_stage, failure_cause):
    """
    获取自动修复建议
    
    输入: 失败阶段 + 失败原因
    输出: 修复命令列表
    """
    suggestions = {
        ('lint', 'Black 格式错误'): [
            'cd systest',
            'pip install black',
            'black core/ tests/ bin/'
        ],
        ('lint', 'Isort 导入错误'): [
            'cd systest',
            'pip install isort',
            'isort core/ tests/ bin/'
        ],
        ('test_cases', '命名不规范'): [
            '参考 TEST_CASE_NAMING_RULES.md',
            '命名格式：t_<module>_<CamelCase>_<number>',
            '示例：t_performance_SequentialReadBurst_001'
        ]
    }
    
    return suggestions.get((failure_stage, failure_cause), [])
```

---

## 📬 汇报模板

### 模板 1: 成功汇报

```markdown
=== QA Agent 汇报 ===

📊 CI/CD 执行完成

✅ **所有检查通过！**

**执行信息**:
- 触发方式：push
- 分支：main
- 提交：abc1234
- 执行时间：2026-03-16 02:00:00 UTC

**检查结果**:
- ✅ 代码质量：success
- ✅ Precondition 检查：success
- ✅ 最小化验证：success
- ✅ FIO 集成验证：success
- ✅ 测试用例验证：success
- ✅ 文档验证：success

**详细说明**:
CI/CD 流程执行成功，代码质量、测试配置、文档完整性均符合要求。

**下一步行动**:
- ✅ 代码可以合并
- ✅ 可以继续部署

**详细报告**: https://github.com/.../actions/runs/12345

=== 汇报完成 ===
```

### 模板 2: 失败汇报

```markdown
=== QA Agent 汇报 ===

📊 CI/CD 执行完成

❌ **部分检查失败**

**执行信息**:
- 触发方式：push
- 分支：main
- 提交：abc1234
- 执行时间：2026-03-16 02:00:00 UTC

**失败项**:
- ❌ 代码质量：failure
  - Flake8 发现 3 个语法错误
  - Black 格式检查不通过
- ❌ 测试用例验证：failure
  - 2 个用例命名不规范（应该用驼峰命名）
  - 1 个用例缺少 purpose 字段

**成功项**:
- ✅ Precondition 检查：success
- ✅ 最小化验证：success
- ✅ FIO 集成验证：success
- ✅ 文档验证：success

**详细说明**:
代码质量检查发现语法错误和格式问题，需要修复后重新提交。
测试用例验证发现命名不规范和注释缺失，需要按照规范修改。

**下一步行动**:
- ❌ 需要修复失败的检查项
- ❌ 重新运行 CI/CD

**修复建议**:
1. 运行 `black systest/` 格式化代码
2. 运行 `isort systest/` 排序导入
3. 修改测试用例命名为驼峰命名法
4. 补充缺失的注释字段

**详细报告**: https://github.com/.../actions/runs/12345

=== 汇报完成 ===
```

---

## 🎯 QA Agent 工作流程

### 完整工作流程

```
1. 监听 CI/CD 完成事件
        ↓
2. 下载 CI/CD 报告
        ↓
3. 读取检查结果
        ↓
4. 分析检查结果
   - 判断总体状态
   - 识别失败项
   - 定位失败原因
        ↓
5. 生成 QA 摘要
   - 快速查看
   - 失败项列表
   - 下一步行动
        ↓
6. 上传 QA 报告
   - 保留 90 天
        ↓
7. 发送汇报通知
   - 区分成功/失败
   - 包含关键信息
   - 提供修复建议
        ↓
8. 等待下次触发
```

---

## ✅ QA Agent 配置检查清单

- [x] 角色定位明确
- [x] 知识库完整（CI/CD 流程/验证项/命名规范/注释要求/环境限制）
- [x] 技能配置完整（结果分析/问题定位/报告生成/汇报沟通）
- [x] 经验规则完整（常见失败原因/优先级判断/自动修复建议）
- [x] 汇报模板完整（成功汇报/失败汇报）
- [x] 工作流程明确

---

## 🎯 总结

**QA Agent 已完全配置，具备专业的 CI/CD 结果审查能力！**

- ✅ 了解 CI/CD 流程和验证项
- ✅ 掌握结果分析和问题定位技能
- ✅ 能生成专业的 QA 报告
- ✅ 能发送清晰的汇报通知
- ✅ 积累常见失败原因和解决方案
- ✅ 提供自动修复建议

**QA Agent 已准备就绪，可以自动审查 CI/CD 结果并汇报！** 🎉
