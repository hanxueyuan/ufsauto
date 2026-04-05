# 失效分析流程 (Failure Analysis Process)

本文档定义 UFS 系统测试的失效分析标准流程，用于快速定位问题根因并采取纠正措施。

---

## 一、失效分类

### 1.1 按严重程度

| 等级 | 定义 | 响应时间 | 示例 |
|------|------|----------|------|
| **Critical** | 系统完全失效，数据丢失风险 | 立即 | 设备无响应、IO Error、数据损坏 |
| **Major** | 性能严重下降，影响使用 | 24 小时 | 带宽低于规格 50%、延迟超标 3x |
| **Minor** | 轻微异常，可继续使用 | 72 小时 | 性能低于规格 10-20%、偶发超时 |

### 1.2 按失效模式

| 类别 | 失效模式 | 可能原因 |
|------|----------|----------|
| **性能类** | 低带宽、低 IOPS、高延迟 | 调度器配置、固件问题、总线瓶颈 |
| **稳定性类** | 测试超时、系统崩溃、设备丢失 | 硬件故障、驱动 bug、电源问题 |
| **资源类** | 空间不足、内存耗尽、CPU 限流 | 配置错误、资源泄漏、并发冲突 |
| **健康类** | 设备降级、坏块增加、温度过高 | NAND 磨损、散热不良、寿命到期 |

---

## 二、分析流程

### 2.1 第一阶段：快速诊断 (15 分钟)

```
1. 查看测试报告
   - 确认失效测试项
   - 记录失败指标数值
   - 检查是否有错误信息

2. 检查系统状态
   $ dmesg | tail -100
   $ lsblk
   $ cat /sys/block/sda/device/state

3. 复现测试
   $ python3 systest/bin/SysTest run --test=<失效测试项> -v
```

### 2.2 第二阶段：深入分析 (1-2 小时)

```
1. 收集详细日志
   - SysTest 日志：logs/SysTest_*_*.log
   - 错误日志：logs/SysTest_*_error.log
   - 系统日志：dmesg, journalctl

2. 运行诊断工具
   $ python3 systest/tools/latency_analyzer.py results/xxx/results.json
   $ python3 systest/tools/ufs_utils.py health

3. 对比历史数据
   $ python3 systest/bin/compare_baseline.py --baseline1 results/baseline/ --baseline2 results/current/
```

### 2.3 第三阶段：根因定位 (4-8 小时)

根据失效模式选择分析方向：

#### 性能问题
- 检查 I/O 调度器：`cat /sys/block/sda/queue/scheduler`
- 检查 CPU 频率：`cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_governor`
- 检查设备温度：读取 thermal zone 数据
- 检查并发干扰：`top`, `iotop`

#### 稳定性问题
- 检查电源稳定性：示波器测量 Vcc
- 检查信号完整性：眼图测试
- 检查固件版本：联系供应商确认
- 检查驱动版本：`modinfo ufshcd`

#### 可靠性问题
- 检查 SMART 数据：读取健康描述符
- 检查坏块增长：对比前后测试数据
- 检查 ECC 错误率：读取设备计数器

---

## 三、失效分析引擎

SysTest 内置失效分析引擎 (`core/analyzer.py`)，可自动识别常见失效模式。

### 3.1 使用方法

```python
from core.analyzer import FailureAnalyzer

analyzer = FailureAnalyzer()
analysis = analyzer.analyze(test_result)

print(f"失效模式：{analysis.failure_mode}")
print(f"根因：{analysis.root_cause}")
print(f"建议：{analysis.suggestions}")
```

### 3.2 支持的失效模式

| 失效模式 | 检测条件 | 置信度 |
|----------|----------|--------|
| LOW_BANDWIDTH | 带宽 < 阈值 90% | 80% |
| LOW_IOPS | IOPS < 阈值 90% | 80% |
| HIGH_LATENCY | 延迟 > 阈值 150% | 80% |
| TEST_TIMEOUT | 超时错误 | 90% |
| DEVICE_NOT_FOUND | 设备不存在错误 | 95% |
| THERMAL_THROTTLING | 温度 > 80℃ + 性能下降 | 75% |
| DEVICE_DEGRADED | 健康状态恶化 | 85% |

---

## 四、8D 报告模板

### D1: 问题描述

```
问题标题：[简短描述]
发生日期：YYYY-MM-DD
发生地点：[实验室/产线/客户现场]
影响范围：[设备批次/软件版本]
```

### D2: 问题现象

```
测试 ID: SysTest_XXXXX
失效测试项：[测试名称]
失效指标：[具体数值 vs 规格]
错误信息：[完整错误日志]
```

### D3: 临时措施

```
[立即采取的遏制措施，如：]
- 暂停测试/生产
- 隔离受影响设备
- 回退到稳定版本
```

### D4: 根因分析

```
直接原因：[技术层面的直接原因]
根本原因：[系统层面的根本原因]
分析方法：[5 Why / 鱼骨图 / FTA]
```

### D5: 永久纠正措施

```
[长期解决方案，如：]
- 硬件设计变更
- 固件版本升级
- 软件配置优化
```

### D6: 效果验证

```
验证方法：[重新测试/对比测试]
验证结果：[数据对比]
验证日期：YYYY-MM-DD
```

### D7: 预防措施

```
[防止再发的措施，如：]
- 更新测试规范
- 增加监控告警
- 完善文档流程
```

### D8: 总结与认可

```
经验教训：[关键收获]
团队认可：[参与人员]
关闭日期：YYYY-MM-DD
```

---

## 五、常用诊断命令

### 设备信息
```bash
# 查看块设备
lsblk -o NAME,SIZE,TYPE,MOUNTPOINT

# 查看设备驱动
cat /sys/block/sda/device/driver

# 查看 UFS 健康状态
cat /sys/class/ufs_device/ufs*/health_descriptor/*
```

### 性能诊断
```bash
# 实时 IO 监控
iostat -x 1

# 进程 IO 监控
iotop -o

# 延迟跟踪
blktrace -d /dev/sda -o - | blkparse -i -
```

### 系统日志
```bash
# 内核日志
dmesg | grep -i ufs
dmesg | grep -i error

# 系统日志
journalctl -u ufs-service
```

---

## 六、升级路径

当无法自行解决时，按以下路径升级：

1. **内部升级**: 通知项目负责人，组织会诊
2. **供应商支持**: 联系 UFS 设备供应商 FAE
3. **第三方实验室**: 送样进行失效分析
4. **客户沟通**: 如影响客户，及时通报进展

---

## 七、联系方式

| 角色 | 联系人 | 邮箱 |
|------|--------|------|
| 项目负责人 | 团长 1 | - |
| 硬件支持 | [待填写] | - |
| 固件支持 | [待填写] | - |
| 供应商 FAE | [待填写] | - |

---

*最后更新：2026-04-04*  
*维护者：团长 1 🦞*
