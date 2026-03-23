# UFS 测试框架设计原则

## 1. 测试状态

| 状态 | 含义 | 触发条件 |
|------|------|---------|
| **PASS** | 测试完成，数据采集成功 | execute + validate 正常结束 |
| **FAIL** | 验证不通过 | validate 返回 False，或有 record_failure 记录 |
| **ERROR** | 执行过程异常 | execute 抛异常（FIO crash、IO error��� |
| **SKIP** | 前置条件不满足，未执行 | setup 返回 False |
| **ABORT** | 被中断或超时 | SIGINT / KeyboardInterrupt / 超时 |

## 2. Failure 两种模式

### Fail-Continue（软失败）
- 记录失败，**case 后续逻辑继续跑**，suite 也继续跑下一个 case
- 用 `self.record_failure(check, expected, actual)` 记录
- 适用场景：多项校验有部分不过，但不影响后续步骤

### Fail-Stop（硬失败）
- **立刻终止当前 case**，suite 也停下来，后续 case 全部 SKIP
- 用 `raise FailStop("原因")` 触发
- 适用场景：设备异常、IO error、数据严重损坏、继续跑有风险

## 3. 性能测试 vs 功能测试

### 性能测试
- **validate 永远返回 True**（不产生 FAIL）
- 指标是否达标通过 `result['annotations']` 标注，不是判决
- 指标不达标需要后续深入分析（环境噪声、SLC cache、温度……），不能让框架直接判死刑
- 测试完成 = PASS，跑不起来 = ERROR/SKIP/ABORT

### 功能测试
- validate 可以返回 False（FAIL）
- 可以使用 Fail-Continue（多项校验部分不过）和 Fail-Stop（严重异常）

## 4. Case 设计规范

### 参数化
- 性能目标（target）、FIO 参数（bs/ioengine/iodepth��等通过 `__init__` 参数可配
- 不同 UFS 规格（3.0/3.1/4.0）对应不同目标值，不能硬编码

### 预热与预填充
- 性能测试必须有 `ramp_time`（默认 10s），避免冷启动偏差
- 读测试必须预填充真实数据，不读 sparse file

### 指标采集与标注
- 所有采集到的指标都应该标注（annotation），不要白采集
- 标注格式：`{'metric': '带宽', 'actual': '1980.5 MB/s', 'target': '>= 2100 MB/s', 'met': False}`
- 交叉验证：IOPS × bs ≈ bandwidth

### 可复现性
- setup 中记录完整测试配置到日志
- 出问题时能根据日志重建 FIO 命令

### teardown
- 清理失败应返回 False（而不是吞掉异常返回 True）
- 即使 teardown 失败，不影响测试状态
