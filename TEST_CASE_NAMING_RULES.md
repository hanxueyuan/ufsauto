# 测试用例命名规则

## 🎯 命名格式
**统一使用小写字母 + 下划线命名，格式如下：**
```
t_<模块全称>_<测试内容描述>_<编号>
```

### 格式说明
| 部分 | 说明 | 示例 |
|------|------|------|
| **前缀** | 固定为 `t_`，表示这是一个测试用例 | `t_` |
| **模块全称** | 测试所属的模块，使用完整英文名称，可读性优先 | `system` / `function` / `performance` / `reliability` / `scenario` |
| **测试内容描述** | 简短描述测试的内容和目的，见名知意 | `ufs_device_recognition` / `small_file_rw` / `sequential_read` |
| **编号** | 三位数字编号，同一模块内连续编号 | `001` / `002` / `003` |

---
## 📋 模块命名定义
**使用完整模块名称，不使用缩写，可读性优先：**
| 测试模块 | 模块名 | 说明 |
|----------|------|------|
| 系统环境测试 | `system` | System check，环境检查类测试 |
| 功能测试 | `function` | Functional test，功能验证类测试 |
| 性能测试 | `performance` | Performance test，性能指标类测试 |
| 可靠性测试 | `reliability` | Reliability test，可靠性稳定性类测试 |
| 场景测试 | `scenario` | Scenario test，真实应用场景类测试 |

---
## ✅ 正确示例
### 系统环境测试
```
t_system_ufs_device_recognition_001    # 系统模块-UFS设备识别-第1个测试
t_system_kernel_version_check_002      # 系统模块-内核版本检查-第2个测试
t_system_available_space_check_003     # 系统模块-可用空间检查-第3个测试
```

### 功能测试
```
t_function_small_file_rw_001             # 功能模块-小文件读写-第1个测试
t_function_large_file_rw_002             # 功能模块-大文件读写-第2个测试
t_function_file_copy_move_003            # 功能模块-文件拷贝移动-第3个测试
t_function_concurrent_rw_004             # 功能模块-并发读写-第4个测试
t_function_trim_command_005              # 功能模块-Trim命令测试-第5个测试
```

### 性能测试
```
t_performance_sequential_read_001           # 性能模块-顺序读-第1个测试
t_performance_sequential_write_002          # 性能模块-顺序写-第2个测试
t_performance_random_read_003               # 性能模块-随机读-第3个测试
t_performance_random_write_004              # 性能模块-随机写-第4个测试
t_performance_mixed_rw_7_3_005               # 性能模块-7:3混合读写-第5个测试
t_performance_latency_006                    # 性能模块-延迟测试-第6个测试
```

### 可靠性测试
```
t_reliability_long_time_stress_001            # 可靠性模块-长时间压力测试-第1个测试
t_reliability_power_cycle_002                 # 可靠性模块-掉电测试-第2个测试
t_reliability_data_integrity_003              # 可靠性模块-数据完整性测试-第3个测试
t_reliability_low_space_operation_004         # 可靠性模块-低空间操作测试-第4个测试
t_reliability_temperature_cycle_005           # 可靠性模块-温度循环测试-第5个测试
```

### 场景测试
```
t_scenario_database_operation_001        # 场景模块-数据库操作-第1个测试
t_scenario_video_playback_002             # 场景模块-视频播放测试-第2个测试
t_scenario_code_compilation_003           # 场景模块-代码编译测试-第3个测试
t_scenario_virtual_machine_004            # 场景模块-虚拟机运行测试-第4个测试
t_scenario_system_update_005              # 场景模块-系统更新测试-第5个测试
```

---
## ❌ 错误示例
### 1. 没有固定前缀
```
❌ system_check_001          # 缺少t_前缀
✅ t_sys_system_check_001
```

### 2. 模块缩写不明确
```
❌ t_function_test_001       # 模块名称太长，应该用缩写func
✅ t_func_test_001
```

### 3. 描述不清晰
```
❌ t_func_test1_001          # 无法看出测试内容
✅ t_func_small_file_rw_001
```

### 4. 编号不规范
```
❌ t_func_rw_1               # 编号应该是三位数字
✅ t_func_rw_001
```

### 5. 使用大写字母或特殊字符
```
❌ t_FUNC_LargeFileRW_001    # 不能使用大写字母和驼峰命名
✅ t_func_large_file_rw_001
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
CI/CD流水线会自动检查测试用例命名是否符合规则，不符合规则的用例会阻止代码提交。
