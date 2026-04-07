# UFS SysTest 实战指南

**目标**: 在开发板上运行完整测试流程，建立性能基线，验证 CI/CD 环境一致性

---

## 📋 完整测试流程

```
1. 环境检查 → 2. 执行测试 → 3. 收集基线 → 4. CI/CD 验证 → 5. 对比分析
```

---

## 步骤 1: 环境检查

### 在开发板上

```bash
# SSH 登录开发板
ssh user@dev-board

# 进入项目目录
cd ufsauto/systest

# 检查环境配置
python3 bin/SysTest check-env -v

# 生成环境报告
python3 bin/SysTest check-env --report -o env_dev_board.json
```

**预期输出**:
```
✅ Python 版本：当前：3.11.x, 要求：≥3.11, 基线：3.11
✅ FIO 版本：当前：3.33, 要求：≥3.33, 基线：3.33
✅ Linux 内核版本：当前：6.1.0-xx-arm64, 要求：≥6.1, 基线：6.1
✅ Debian 版本：当前：12, 基线：12
✅ CPU 架构：当前：aarch64, 基线：arm64
✅ 环境检查通过
```

### 在 CI/CD 环境

```bash
# 使用 Docker
docker run --rm ufsauto/systest:1.0 \
  "python3 /workspace/systest/bin/SysTest check-env -v"

# 或自托管 Runner
cd ufsauto/systest
python3 bin/SysTest check-env -v
```

---

## 步骤 2: 执行性能测试

### 开发板测试

```bash
cd ufsauto/systest

# 运行完整性能测试套件
python3 bin/SysTest run --suite=performance \
  --device=/dev/ufs0 \
  -v \
  -o results/dev_board_baseline

# 查看实时日志
tail -f logs/SysTest_*.log
```

**测试执行时间**: 约 5-10 分钟 (取决于测试配置)

### 测试配置说明

默认测试参数 (来自 `config/production.json`):

| 测试项 | 块大小 | 队列深度 | 运行时间 | 目标值 |
|--------|--------|----------|----------|--------|
| 顺序读 Burst | 1M | 1 | 60s | ≥2100 MB/s |
| 顺序写 Burst | 1M | 1 | 60s | ≥1650 MB/s |
| 随机读 Burst | 4K | 64 | 60s | ≥200 KIOPS |
| 随机写 Burst | 4K | 64 | 60s | ≥330 KIOPS |
| 混合读写 70/30 | 4K | 64 | 60s | ≥150 KIOPS |

---

## 步骤 3: 查看测试结果

### 检查测试状态

```bash
# 查看测试摘要
cat results/dev_board_baseline/results.json | jq '.summary'

# 查看通过率
cat results/dev_board_baseline/results.json | jq '.summary.pass_rate'
```

### 打开 HTML 报告

```bash
# 如果有图形界面
firefox results/dev_board_baseline/report.html

# 或复制到本地查看
scp user@dev-board:~/ufsauto/systest/results/dev_board_baseline/report.html .
open report.html
```

### 示例输出

```json
{
  "test_id": "20260322_133000",
  "suite": "performance",
  "device": "/dev/ufs0",
  "summary": {
    "total": 5,
    "passed": 5,
    "failed": 0,
    "pass_rate": 100.0
  },
  "test_cases": [
    {
      "name": "t_perf_SeqReadBurst_001",
      "status": "PASS",
      "metrics": {
        "bandwidth": {
          "value": 2150.5,
          "unit": "MB/s"
        }
      }
    }
    // ... 其他测试
  ]
}
```

---

## 步骤 4: 保存基线数据

```bash
# 创建基线目录
mkdir -p baselines

# 复制当前结果作为基线
cp -r results/dev_board_baseline baselines/dev_board_20260322

# 记录基线信息
cat > baselines/dev_board_20260322/info.txt << EOF
基线日期：2026-03-22
开发板：ARM64 Debian 12
内核：6.1.0-xx-arm64
FIO: 3.33
UFS: 3.1 128GB
测试套件：performance (5 项)
通过率：100%
EOF

# 提交基线到 git
git add baselines/dev_board_20260322
git commit -m "baseline: 开发板性能基线 (2026-03-22)"
```

---

## 步骤 5: CI/CD 环境验证

### 构建 Docker 镜像

```bash
cd ufsauto
docker build -t ufsauto/systest:1.0 -f Dockerfile.ci .
```

### 运行 CI/CD 测试

```bash
# 如果有 UFS 设备
docker run --rm -v /dev:/dev --privileged \
  ufsauto/systest:1.0 \
  "python3 /workspace/systest/bin/SysTest run --suite=performance --device=/dev/ufs0 -o /workspace/results/ci_test"

# 如果没有硬件，使用 dry-run
docker run --rm ufsauto/systest:1.0 \
  "python3 /workspace/systest/bin/SysTest run --suite=performance --dry-run"
```

### GitHub Actions 自动测试

```bash
# 推送代码触发 CI
git push origin master

# 查看测试结果
# https://github.com/hanxueyuan/ufsauto/actions
```

---

## 步骤 6: 性能对比分析

### 对比开发板和 CI/CD 结果

```bash
cd systest

# 对比性能基线
python3 bin/SysTest compare-baseline \
  --dev results/dev_board_baseline/ \
  --ci results/ci_test/ \
  --threshold 0.10 \
  --output baseline_comparison_report.txt
```

### 解读对比报告

**示例输出**:
```
================================================================================
UFS SysTest 性能基线对比报告
================================================================================
生成时间：2026-03-22T13:35:00

📊 对比摘要
----------------------------------------
总测试数：5
✅ 通过：5 (100.0%)
⚠️  警告：0
❌ 失败：0

📋 详细对比
----------------------------------------

测试：t_perf_SeqReadBurst_001
  开发板：PASS
  CI/CD:  PASS
  ✅ bandwidth:
      开发板：2150.50 MB/s
      CI/CD:  2100.30 MB/s
      差异：2.33% [PASS]

测试：t_perf_RandReadBurst_005
  开发板：PASS
  CI/CD:  PASS
  ✅ iops:
      开发板：205000.00 IOPS
      CI/CD:  198000.00 IOPS
      差异：3.41% [PASS]

================================================================================
✅ 环境一致性优秀！所有性能指标差异在允许范围内。
================================================================================
```

### 性能差异解读

| 差异范围 | 状态 | 说明 |
|----------|------|------|
| ≤ 10% | ✅ PASS | 环境一致性良好 |
| 10-15% | ⚠️ WARNING | 轻微差异，建议关注 |
| > 15% | ❌ FAIL | 环境配置可能不一致 |

---

## 故障排查

### 问题 1: 测试失败率高

**症状**: 通过率 < 80%

**排查步骤**:
```bash
# 1. 检查设备健康状态
cat /sys/class/ufs_device/ufs0/health_status

# 2. 检查可用空间
df -h /dev/ufs0

# 3. 检查系统负载
top -bn1 | head -20

# 4. 查看详细日志
cat logs/SysTest_*.log | grep -A 5 "FAIL"
```

### 问题 2: 性能波动大

**症状**: 多次测试结果差异 > 20%

**解决方案**:
```bash
# 1. 关闭节能模式
echo performance | sudo tee /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor

# 2. 设置 I/O 调度器
echo none | sudo tee /sys/block/sda/queue/scheduler

# 3. 清理后台进程
killall -9 background_apps

# 4. 刷新缓存
sync && echo 3 | sudo tee /proc/sys/vm/drop_caches

# 5. 重新测试
python3 bin/SysTest run --suite=performance --device=/dev/ufs0
```

### 问题 3: CI/CD 与开发板性能差异大

**症状**: 对比报告显示 > 15% 差异

**排查清单**:
- [ ] 确认 Docker 镜像版本正确 (`debian:12-slim`)
- [ ] 检查 FIO 版本 (`fio --version`)
- [ ] 确认内核版本 (`uname -r`)
- [ ] 检查 CPU 架构 (`uname -m`)
- [ ] 验证测试参数一致 (对比 config 文件)

---

## 自动化脚本

### 一键测试脚本

创建 `scripts/run_full_test.sh`:

```bash
#!/bin/bash
set -e

echo "=========================================="
echo "UFS SysTest 完整测试流程"
echo "=========================================="

# 1. 环境检查
echo "📋 步骤 1: 环境检查"
python3 bin/SysTest check-env -v || exit 1

# 2. 执行测试
echo "🚀 步骤 2: 执行性能测试"
TEST_ID=$(date +%Y%m%d_%H%M%S)
python3 bin/SysTest run --suite=performance \
  --device=/dev/ufs0 \
  -v \
  -o results/test_${TEST_ID}

# 3. 生成报告
echo "📊 步骤 3: 生成测试报告"
python3 bin/SysTest report --id test_${TEST_ID}

# 4. 保存基线
echo "💾 步骤 4: 保存基线数据"
mkdir -p baselines/baseline_${TEST_ID}
cp -r results/test_${TEST_ID}/* baselines/baseline_${TEST_ID}/

echo "=========================================="
echo "✅ 测试完成！"
echo "报告：results/test_${TEST_ID}/report.html"
echo "基线：baselines/baseline_${TEST_ID}/"
echo "=========================================="
```

使用方法:
```bash
chmod +x scripts/run_full_test.sh
./scripts/run_full_test.sh
```

---

## 定期验证计划

### 每周验证

```bash
# 每周一运行一次完整测试
0 9 * * 1 cd /home/user/ufsauto/systest && ./scripts/run_full_test.sh
```

### 每次代码更新后

```bash
# Git pre-commit hook
cat > .git/hooks/pre-commit << 'EOF'
#!/bin/bash
# 运行快速环境检查
python3 bin/SysTest check-env || exit 1
EOF
chmod +x .git/hooks/pre-commit
```

### 每月基线校准

```bash
# 每月第一天重新建立基线
0 9 1 * * cd /home/user/ufsauto/systest && \
  python3 bin/SysTest run --suite=performance --device=/dev/ufs0 && \
  git commit -am "baseline: 月度性能基线 ($(date +%Y-%m))"
```

---

## 最佳实践

### ✅ 推荐做法

1. **固定测试时间**: 每天同一时间运行，减少环境波动
2. **空闲状态测试**: 确保无其他进程干扰
3. **温度稳定**: 开发板预热 5 分钟后再测试
4. **多次平均**: 关键测试运行 3 次取平均值
5. **版本记录**: 记录每次测试的软件版本

### ❌ 避免做法

1. **不要在系统负载高时测试**
2. **不要在温度过高时测试**
3. **不要跳过环境检查**
4. **不要忽略警告信息**
5. **不要混用不同版本的 FIO**

---

## 参考文档

- [DEV_BOARD_ENV.md](./DEV_BOARD_ENV.md) - 开发板环境配置
- [ENVIRONMENT_SETUP.md](./ENVIRONMENT_SETUP.md) - 环境配置指南
- [CI_CD_QUICKSTART.md](./CI_CD_QUICKSTART.md) - CI/CD 快速指南
- [README.md](./README.md) - SysTest 使用手册

---

**最后更新**: 2026-03-22  
**版本**: v1.0.0
