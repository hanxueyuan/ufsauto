# UFS Auto 测试框架使用指南

## 🎯 极简使用方式
**工程师不需要懂任何技术细节，只需要执行3步即可完成测试：**

### 1. 上传测试包到开发板
```bash
scp ufs_test_package.tar.gz root@192.168.195.3:/mapdata/
```

### 2. 解压并进入目录
```bash
cd /mapdata
tar zxf ufs_test_package.tar.gz
cd ufs_test_package
```

### 3. 一键执行所有测试
```bash
python3 run_all.py
```

✅ **就这么简单！** 框架会自动完成所有检查、测试、报告生成。

---
## 📋 常用命令
### 基础命令
| 命令 | 功能 |
|------|------|
| `python3 run_all.py` | 执行所有测试 |
| `python3 run_all.py -t system` | 仅执行系统环境检查测试 |
| `python3 run_all.py -t function` | 仅执行功能测试 |
| `python3 run_all.py -t performance` | 仅执行性能测试 |
| `python3 run_all.py -t reliability` | 仅执行可靠性测试 |
| `python3 run_all.py -t scenario` | 仅执行场景测试 |

### 高级命令
| 命令 | 功能 |
|------|------|
| `python3 run_all.py -l` | 列出所有可用测试用例 |
| `python3 run_all.py -v` | 输出详细日志 |
| `python3 run_all.py --no-fail-fast` | 测试失败时不停止，继续执行后续用例 |
| `python3 run_all.py --pre-check-only` | 仅检查环境，不运行测试 |
| `python3 run_all.py -o /path/to/output` | 指定测试结果输出目录 |

---
## 📊 测试完成后自动生成的内容
测试结束后，在 `results/` 目录下会自动生成：
1. **测试报告**：`report.md`（Markdown格式）和`report.html`（HTML格式，可选）
2. **执行日志**：详细的执行日志，包含每一步操作和结果
3. **性能数据**：所有性能测试的原始数据和图表
4. **失败分析**：失败用例的详细错误信息和初步失效分析
5. **环境快照**：测试前后的环境对比信息

---
## ❌ 测试失败自动处理
**任何一步失败都会立即停止（默认），并输出：**
- 失败的测试用例名称
- 详细的失败原因和错误日志
- 初步的失效分析和可能的原因
- 相关的系统日志和UFS状态信息
- 后续排查建议

**示例失败输出：**
```
❌ 失败用例详情：
  测试用例: 大文件读写测试
  失败原因: 写入速度低于预期（实际800MB/s，预期≥1600MB/s）
  初步分析: 可能是UFS工作在低速模式，或Write Booster功能未开启
  日志文件: results/logs/test_large_file_io.log
```

---
## 📈 测试报告示例
```
# UFS 自动化测试报告
## 基本信息
- 测试时间: 2026-03-12 19:00:00
- 测试类型: 所有测试
- UFS设备: /dev/sda 128GB
- 内核版本: Linux 6.1.112-rt43

## 测试总结
| 总用例数 | 通过 | 失败 | 跳过 | 总耗时 |
|----------|------|------|------|--------|
| 74       | 72   | 2    | 0    | 1h23m  |

## 失败用例详情
1. **大文件读写测试** ❌
   - 错误: 写入速度800MB/s < 预期1600MB/s
   - 分析: Write Booster未开启
   - 建议: 检查UFS配置，开启Write Booster功能

2. **随机写入IOPS测试** ❌
   - 错误: 随机写IOPS 250K < 预期300K
   - 分析: 可能是温度过高导致降速
   - 建议: 检查散热，或降低测试环境温度

## 性能指标
| 测试项 | 结果 | 基准 | 状态 |
|--------|------|------|------|
| 顺序读 | 2150MB/s | ≥2100MB/s | ✅ 通过 |
| 顺序写 | 800MB/s | ≥1600MB/s | ❌ 失败 |
| 随机读 | 420K IOPS | ≥400K | ✅ 通过 |
| 随机写 | 250K IOPS | ≥300K | ❌ 失败 |
```

---
## 💡 常见问题
### Q: 执行报错提示缺少依赖？
A: 所有核心功能仅使用Python标准库，无需额外安装依赖。如果缺少Python3，请运行`apt install python3`。

### Q: 测试需要多长时间？
A: 全量测试约1-2小时，单独性能测试约30分钟，功能测试约15分钟。

### Q: 测试会影响系统正常运行吗？
A: 所有测试都在`/mapdata/ufs_test/`目录下进行，不会修改系统文件，不会影响系统稳定。

### Q: 如何自动定时执行测试？
A: 使用crontab定时任务：
```bash
# 每天凌晨2点执行全量测试
0 2 * * * cd /mapdata/ufs_test_package && python3 run_all.py -o /mapdata/test_results/$(date +\%Y\%m\%d)
```

---
## 📞 技术支持
如果遇到问题，请提供：
1. `results/`目录下的所有文件
2. 测试时的系统环境信息
3. 具体的错误现象和复现步骤
