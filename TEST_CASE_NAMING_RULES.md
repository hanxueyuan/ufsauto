# 测试用例命名规则

**版本**: v2.0  
**最后更新**: 2026-03-16  
**适用范围**: 所有 UFS 项目测试用例

---

## 🎯 命名格式

**统一使用「小写模块名 + 驼峰用例名 + 数字编号」，格式如下：**

```
t_<module>_<CamelCaseDescription>_<number>
```

### 格式说明

| 部分 | 命名方式 | 说明 | 示例 |
|------|---------|------|------|
| **前缀** | 固定小写 | 表示这是一个测试用例 | `t_` |
| **模块名** | 小写 + 下划线 | 测试所属的模块 | `performance_` / `qos_` / `reliability_` |
| **用例描述** | 驼峰命名 (CamelCase) | 描述测试的内容和目的 | `SequentialReadBurst` / `LatencyPercentile` |
| **编号** | 三位数字 | 同一模块内连续编号 | `_001` / `_002` / `_003` |

---

## 📋 模块命名定义

**使用完整模块名称，小写 + 下划线：**

| 测试模块 | 模块名 | 说明 |
|----------|------|------|
| 系统环境测试 | `system_` | System check，环境检查类测试 |
| 功能测试 | `function_` | Functional test，功能验证类测试 |
| 性能测试 | `performance_` | Performance test，性能指标类测试 |
| QoS 测试 | `qos_` | Quality of Service，服务质量测试 |
| 可靠性测试 | `reliability_` | Reliability test，可靠性稳定性类测试 |
| 场景测试 | `scenario_` | Scenario test，真实应用场景类测试 |

---

## 📝 驼峰命名规则

**用例描述使用驼峰命名法 (CamelCase)**：

- ✅ 每个单词首字母大写
- ✅ 单词之间无分隔符
- ✅ 见名知意，简洁明了

**示例**：
- ✅ `SequentialReadBurst` (顺序读 Burst)
- ✅ `RandomWriteSustained` (随机写 Sustained)
- ✅ `LatencyPercentile` (延迟百分位)
- ✅ `StabilityTest` (稳定性测试)
- ❌ `sequential_read_burst` (全小写，不推荐)
- ❌ `Sequential_Read_Burst` (下划线分隔，不推荐)

---

## ✅ 正确示例（驼峰命名法）

### 性能测试 (performance)

```
t_performance_SequentialReadBurst_001       # 顺序读带宽 (Burst)
t_performance_SequentialReadSustained_002   # 顺序读带宽 (Sustained)
t_performance_SequentialWriteBurst_003      # 顺序写带宽 (Burst)
t_performance_SequentialWriteSustained_004  # 顺序写带宽 (Sustained)
t_performance_RandomReadBurst_005           # 随机读 IOPS (Burst)
t_performance_RandomReadSustained_006       # 随机读 IOPS (Sustained)
t_performance_RandomWriteBurst_007          # 随机写 IOPS (Burst)
t_performance_RandomWriteSustained_008      # 随机写 IOPS (Sustained)
t_performance_MixedRw_009                   # 混合读写性能
```

### QoS 测试 (qos)

```
t_qos_LatencyPercentile_001                 # 延迟百分位测试
t_qos_LatencyJitter_002                     # 延迟抖动测试
```

### 可靠性测试 (reliability)

```
t_reliability_StabilityTest_001             # 长期稳定性测试
```

### 场景测试 (scenario)

```
t_scenario_SensorWrite_001                  # 传感器数据写入
t_scenario_ModelLoad_002                    # 算法模型加载
```

### 系统环境测试 (system)

```
t_system_UfsDeviceRecognition_001           # UFS 设备识别
t_system_KernelVersionCheck_002             # 内核版本检查
t_system_AvailableSpaceCheck_003            # 可用空间检查
```

### 功能测试 (function)

```
t_function_SmallFileRw_001                  # 小文件读写
t_function_LargeFileRw_002                  # 大文件读写
t_function_FileCopyMove_003                 # 文件拷贝移动
t_function_ConcurrentRw_004                 # 并发读写
t_function_TrimCommand_005                  # Trim 命令测试
```

---

## ❌ 错误示例

### 1. 没有固定前缀

```
❌ SequentialReadBurst_001          # 缺少 t_前缀
✅ t_performance_SequentialReadBurst_001
```

### 2. 模块名未使用小写

```
❌ t_Performance_SequentialRead_001  # 模块名应该小写
✅ t_performance_SequentialRead_001
```

### 3. 用例名未使用驼峰命名

```
❌ t_performance_sequential_read_001  # 用例名应该用驼峰
✅ t_performance_SequentialRead_001
```

### 4. 编号不规范

```
❌ t_performance_SequentialRead_1     # 编号应该是三位数字
✅ t_performance_SequentialRead_001
```

### 5. 模块与用例之间缺少下划线分隔

```
❌ t_performanceSequentialRead_001    # 模块与用例之间需要下划线
✅ t_performance_SequentialRead_001
```

---

## 📌 命名规则说明

1. **见名知意**：从测试用例名称就能看出测试的模块、内容和目的
2. **一致性**：所有测试用例统一使用相同的命名规则
3. **唯一性**：每个测试用例名称唯一，编号不重复
4. **简洁性**：描述尽量简洁，避免过长
5. **英文**：全部使用英文，禁止使用中文拼音或中文

---

## 🔧 自动化检查

CI/CD 流水线会自动检查测试用例命名是否符合规则，不符合规则的用例会阻止代码提交。

---

## 📚 相关文件

- `systest/suites/performance/tests.json` - 性能测试用例定义
- `systest/suites/qos/tests.json` - QoS 测试用例定义
- `systest/suites/reliability/tests.json` - 可靠性测试用例定义
- `systest/suites/scenario/tests.json` - 场景测试用例定义

---

**版本历史**:
- v2.0 (2026-03-16): 更新为驼峰命名法 (CamelCase)
- v1.0 (2026-03-15): 初始版本，使用全小写命名
