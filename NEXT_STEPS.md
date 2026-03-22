# 🚀 下一步行动计划

**创建时间**: 2026-03-22  
**优先级**: 高 → 低

---

## 🔥 立即执行 (今天)

### 1. 开发板实战测试 ⭐⭐⭐

**目标**: 在真实开发板上验证所有工具和环境配置

**步骤**:
```bash
# SSH 登录开发板
ssh user@dev-board

# 拉取最新代码
cd ~/ufsauto
git pull origin master

# 环境检查
cd systest
python3 bin/SysTest check-env -v

# 预期输出
# ✅ Python 版本：3.11.x
# ✅ FIO 版本：3.33
# ✅ Debian 版本：12
# ✅ CPU 架构：aarch64
# ✅ 环境检查通过

# 执行性能测试
python3 bin/SysTest run --suite=performance --device=/dev/ufs0 -v

# 查看结果
python3 bin/SysTest report --latest
```

**预期结果**:
- 环境检查 100% 通过
- 5 个性能测试用例全部执行
- 生成 HTML 和 JSON 报告
- 收集真实性能基线数据

**输出物**:
- `results/dev_board_YYYYMMDD/` - 测试结果
- `baselines/dev_board_YYYYMMDD/` - 性能基线

---

## 📅 本周完成 (2026-03-23 ~ 2026-03-29)

### 2. QoS 测试套件开发 ⭐⭐⭐

**目标**: 实现延迟和抖动测试

**任务分解**:

#### 2.1 延迟百分位测试 (t_qos_LatencyPercentile_001)
```python
# systest/suites/qos/t_qos_LatencyPercentile_001.py
def test():
    # 使用 FIO 延迟测试
    fio_config = FIOConfig(
        rw='read',
        bs='4k',
        iodepth=1,      # 队列深度 1，测量纯延迟
        runtime=60,
        lat_percentiles=True  # 启用延迟百分位
    )
    result = fio.run(config)
    
    # 验证 P99 延迟
    assert result['latency_p99'] < 100  # us
```

**验收标准**:
- P50, P90, P95, P99 延迟数据
- 延迟直方图
- 通过率判定

#### 2.2 延迟抖动测试 (t_qos_LatencyJitter_002)
```python
# systest/suites/qos/t_qos_LatencyJitter_002.py
def test():
    # 长时间运行，统计延迟标准差
    fio_config = FIOConfig(
        rw='read',
        bs='4k',
        iodepth=1,
        runtime=300  # 5 分钟
    )
    result = fio.run(config)
    
    # 计算抖动 (标准差/平均值)
    jitter = result['latency_stddev'] / result['latency_avg']
    assert jitter < 0.2  # 20% 抖动
```

**验收标准**:
- 平均延迟
- 延迟标准差
- 抖动系数

**时间安排**:
- 周一：实现 t_qos_LatencyPercentile_001
- 周二：实现 t_qos_LatencyJitter_002
- 周三：测试和优化

---

### 3. CI/CD Runner 配置 ⭐⭐

**目标**: 在开发板或 ARM64 服务器上配置自托管 Runner

**步骤**:

#### 3.1 准备 Runner 机器
```bash
# 选项 A: 使用开发板
# 选项 B: 使用 ARM64 服务器 (如 AWS Graviton)

# 安装依赖
sudo apt-get update
sudo apt-get install -y docker.io docker-compose
```

#### 3.2 配置 GitHub Runner
```bash
# 下载 Runner
mkdir actions-runner && cd actions-runner
curl -O -L https://github.com/actions/runner/releases/download/v2.311.0/actions-runner-linux-arm64-2.311.0.tar.gz
tar xzf ./actions-runner-linux-arm64-2.311.0.tar.gz

# 注册 Runner (需要 GitHub token)
./config.sh --url https://github.com/hanxueyuan/ufsauto --token YOUR_TOKEN

# 启动 Runner
./run.sh
```

#### 3.3 测试 Runner
```bash
# 推送测试提交
git commit --allow-empty -m "test: trigger CI"
git push

# 查看 GitHub Actions
# https://github.com/hanxueyuan/ufsauto/actions
```

**验收标准**:
- Runner 在线状态正常
- 自动触发测试
- 测试结果回传

---

### 4. 性能基线收集 ⭐⭐

**目标**: 建立开发板性能基线，用于后续回归测试

**步骤**:
```bash
# 在开发板上运行
cd systest

# 运行 3 次取平均值
for i in 1 2 3; do
  python3 bin/SysTest run --suite=performance --device=/dev/ufs0 -o results/run_$i
done

# 对比结果
python3 bin/SysTest compare-baseline \
  --baseline1 results/run_1 \
  --baseline2 results/run_2 \
  --baseline3 results/run_3

# 保存基线
mkdir -p baselines/final_baseline
cp results/run_3/* baselines/final_baseline/
git add baselines/final_baseline
git commit -m "baseline: 开发板性能基线 (2026-03-22)"
```

**输出物**:
- 基线数据 (JSON)
- 性能报告 (HTML)
- Git 提交记录

---

## 📆 下周计划 (2026-03-30 ~ 2026-04-05)

### 5. Reliability 测试套件 ⭐

**测试项**:
- [ ] t_rel_StabilityTest_001 - 24 小时稳定性测试
- [ ] t_rel_PowerCycle_002 - 电源循环测试
- [ ] t_rel_TemperatureCycle_003 - 温度循环测试

**实现要点**:
- 长时间运行 (24h+)
- 自动恢复机制
- 异常检测和记录

---

### 6. 性能趋势分析 ⭐

**目标**: 可视化性能数据，观察趋势变化

**功能**:
- 性能数据时间序列图表
- 基线对比图表
- 自动告警 (性能下降 > 10%)

**技术栈**:
- Python: matplotlib / plotly
- 输出：HTML 交互式图表

---

### 7. 文档完善 ⭐

**待补充**:
- [ ] QoS 测试指南
- [ ] Reliability 测试指南
- [ ] 故障排查手册
- [ ] 最佳实践总结

---

## 🗓️ 下月计划 (2026-04)

### 8. Scenario 测试套件

**场景化测试**:
- [ ] t_scen_SensorWrite_001 - 传感器数据写入
- [ ] t_scen_ModelLoad_002 - AI 模型加载
- [ ] t_scen_LogWrite_003 - 日志持续写入

**特点**:
- 真实业务场景模拟
- 混合负载
- 长时间运行

---

### 9. 集成与自动化

**集成目标**:
- [ ] JIRA/禅道集成 (自动创建 issue)
- [ ] 邮件通知 (测试失败自动通知)
- [ ] Slack/飞书通知

**自动化**:
- [ ] 每日定时测试 (cron)
- [ ] 性能回归检测
- [ ] 自动优化建议

---

### 10. 性能优化建议引擎

**功能**:
- 基于测试结果自动分析瓶颈
- 提供优化建议 (I/O 调度器、内核参数等)
- 优化前后对比

**示例**:
```
检测到顺序写性能偏低 (1200 MB/s < 1650 MB/s)

可能原因:
1. I/O 调度器不是 'none' 或 'mq-deadline'
2. 写缓存未启用
3. 设备固件版本过旧

建议操作:
1. echo none > /sys/block/sda/queue/scheduler
2. hdparm -W1 /dev/sda
3. 联系厂商升级固件
```

---

## 📊 优先级矩阵

| 任务 | 重要性 | 紧急性 | 优先级 |
|------|--------|--------|--------|
| 开发板实战测试 | ⭐⭐⭐ | ⭐⭐⭐ | 🔥 立即 |
| QoS 测试套件 | ⭐⭐⭐ | ⭐⭐ | 高 |
| CI/CD Runner | ⭐⭐ | ⭐⭐ | 高 |
| 性能基线收集 | ⭐⭐⭐ | ⭐ | 高 |
| Reliability 测试 | ⭐⭐ | ⭐ | 中 |
| 性能趋势分析 | ⭐ | ⭐ | 中 |
| Scenario 测试 | ⭐ | ⭐ | 低 |
| 集成自动化 | ⭐ | ⭐ | 低 |

---

## ✅ 检查清单

### 开发板测试前
- [ ] 代码已推送到 GitHub
- [ ] SSH 可以登录开发板
- [ ] 开发板已安装 FIO 3.33
- [ ] 开发板有足够可用空间 (>2GB)
- [ ] 备份重要数据

### QoS 开发前
- [ ] 熟悉 FIO 延迟测试参数
- [ ] 了解 UFS QoS 指标要求
- [ ] 准备测试数据记录模板

### CI/CD 配置前
- [ ] 有可用的 ARM64 机器
- [ ] GitHub 仓库有 Actions 权限
- [ ] 网络可以访问 GitHub

---

## 📞 联系方式

**项目负责人**: UFS Team  
**GitHub**: https://github.com/hanxueyuan/ufsauto  
**文档**: systest/docs/

---

**最后更新**: 2026-03-22  
**下次更新**: 2026-03-23
