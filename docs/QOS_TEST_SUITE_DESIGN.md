# QoS 测试套件设计文档

**版本**: 1.0  
**整理时间**: 2026-03-26 06:30  
**学习阶段**: 第二阶段 - 测试框架完善  
**优先级**: 🔴 高（SysTest 框架待完成部分）

---

## 📊 QoS 测试套件总览

### 1. 测试目标

QoS (Quality of Service) 测试关注**性能一致性**而非峰值性能：

| 维度 | 性能测试 | QoS 测试 |
|------|----------|----------|
| **关注点** | 峰值带宽/IOPS | 延迟分布、稳定性 |
| **指标** | 平均带宽、IOPS | P99/P99.99 延迟、抖动 |
| **场景** | 稳态负载 | 瞬态、混合、并发 |
| **时长** | 短 (60 秒) | 长 (300 秒+) |

### 2. 测试套件结构

```
systest/suites/qos/
├── __init__.py
├── test_latency.py        # 延迟分布测试
├── test_jitter.py         # 延迟抖动测试
├── test_queue_depth.py    # 队列深度扫描
└── test_concurrent.py     # 并发测试
```

---

## 📈 测试用例 1：延迟分布测试

### 测试目的
测量 IO 延迟的完整分布，识别尾延迟 (Tail Latency)

### 测试原理
```
1. 发送大量单块 IO 请求 (4K)
2. 记录每个 IO 的延迟
3. 统计延迟分布：P50, P90, P99, P99.9, P99.99, Max
4. 生成直方图
```

### 测试配置

```python
# test_latency.py 配置
LATENCY_CONFIG = {
    "block_size": 4096,          # 4K block
    "io_count": 100000,          # 10 万个 IO
    "queue_depth": 1,            # QD=1 (避免排队延迟)
    "pattern": "randread",       # 随机读
    "runtime": 300,              # 5 分钟
    "io_engine": "libaio",       # 异步 IO
    "direct": 1,                 # 绕过缓存
}
```

### 预期指标 (UFS 3.1 128GB)

| 百分位 | 目标延迟 | 警告阈值 | 失败阈值 |
|--------|----------|----------|----------|
| **P50** | < 100 μs | 100-150 μs | > 150 μs |
| **P90** | < 200 μs | 200-300 μs | > 300 μs |
| **P99** | < 500 μs | 500-800 μs | > 800 μs |
| **P99.9** | < 1 ms | 1-2 ms | > 2 ms |
| **P99.99** | < 5 ms | 5-10 ms | > 10 ms |
| **Max** | < 10 ms | 10-50 ms | > 50 ms |

### FIO 配置示例

```ini
[latency_test]
ioengine=libaio
direct=1
rw=randread
bs=4k
size=4k
numjobs=1
iodepth=1
runtime=300
time_based
io_submit_mode=off
lat_percentiles=1
lat_window_size=100
log_avg_msec=1000
write_lat_log=latency_log
```

### 输出示例

```json
{
  "test_name": "latency_distribution",
  "timestamp": "2026-03-26T06:35:00",
  "device": "/dev/sda",
  "config": {
    "block_size": 4096,
    "io_count": 100000,
    "queue_depth": 1
  },
  "results": {
    "latency_us": {
      "min": 45,
      "max": 8234,
      "mean": 87.3,
      "stddev": 156.2,
      "percentiles": {
        "p50": 78,
        "p90": 145,
        "p95": 234,
        "p99": 456,
        "p99.9": 1234,
        "p99.99": 4567,
        "p99.999": 7890
      }
    },
    "iops": 11456,
    "bandwidth_mbps": 44.75
  },
  "histogram": {
    "buckets": [
      {"range": "0-50us", "count": 12345, "percent": 12.3},
      {"range": "50-100us", "count": 45678, "percent": 45.7},
      {"range": "100-200us", "count": 28901, "percent": 28.9},
      {"range": "200-500us", "count": 9876, "percent": 9.9},
      {"range": "500us-1ms", "count": 2345, "percent": 2.3},
      {"range": "1ms-5ms", "count": 789, "percent": 0.8},
      {"range": "5ms+", "count": 66, "percent": 0.1}
    ]
  }
}
```

---

## 📉 测试用例 2：延迟抖动测试

### 测试目的
测量延迟随时间的变化 (抖动)，识别性能不稳定问题

### 测试原理
```
1. 持续发送固定负载的 IO 请求
2. 按时间窗口统计延迟 (如每秒)
3. 计算延迟的标准差、变异系数
4. 识别异常波动 (毛刺)
```

### 测试配置

```python
# test_jitter.py 配置
JITTER_CONFIG = {
    "block_size": 4096,
    "queue_depth": 32,           # 典型工作负载 QD
    "runtime": 600,              # 10 分钟 (更长周期观察)
    "window_size": 1,            # 1 秒窗口
    "pattern": "randread",
    "target_iops": 50000,        # 目标 IOPS (QoS 测试需要稳态)
}
```

### 关键指标

| 指标 | 计算公式 | 目标值 |
|------|----------|--------|
| **延迟标准差** | σ = √(Σ(xi-μ)²/n) | < 50 μs |
| **变异系数** | CV = σ/μ | < 0.5 |
| **最大抖动** | Max - Min | < 500 μs |
| **毛刺次数** | 延迟 > 3σ 的次数 | < 10 次/分钟 |

### FIO 配置示例

```ini
[jitter_test]
ioengine=libaio
direct=1
rw=randread
bs=4k
size=1g
numjobs=1
iodepth=32
runtime=600
time_based
rate_iops=50000
log_avg_msec=1000
write_lat_log=jitter_log
write_bw_log=jitter_bw
```

### 输出示例

```json
{
  "test_name": "latency_jitter",
  "timestamp": "2026-03-26T06:40:00",
  "results": {
    "latency_us": {
      "mean": 125.4,
      "stddev": 23.7,
      "cv": 0.189,
      "min": 67,
      "max": 892
    },
    "jitter_analysis": {
      "window_count": 600,
      "spike_count": 3,
      "spike_threshold_us": 200,
      "worst_window": {
        "timestamp": 234,
        "mean_latency_us": 456,
        "iops": 32000
      }
    },
    "stability_score": 95.2
  },
  "time_series": {
    "latency_per_second": [120, 125, 118, 130, ..., 127],
    "iops_per_second": [49800, 50200, 49900, 50100, ..., 50050]
  }
}
```

---

## 📊 测试用例 3：队列深度扫描

### 测试目的
测量不同队列深度下的性能曲线，识别最佳 QD 和饱和点

### 测试原理
```
1. 从 QD=1 开始测试
2. 逐步增加 QD (1, 2, 4, 8, 16, 32, 64, 128, 256)
3. 记录每个 QD 下的 IOPS、带宽、延迟
4. 绘制性能曲线
```

### 测试配置

```python
# test_queue_depth.py 配置
QD_SCAN_CONFIG = {
    "block_size": 4096,
    "queue_depths": [1, 2, 4, 8, 16, 32, 64, 128, 256],
    "runtime_per_qd": 60,      # 每个 QD 测试 60 秒
    "pattern": "randread",
    "warmup_time": 5,          # 预热时间
}
```

### 预期结果 (UFS 3.1)

| QD | IOPS (目标) | 延迟 (P99) | 备注 |
|----|-------------|------------|------|
| 1 | ~10,000 | < 150 μs | 低延迟场景 |
| 2 | ~18,000 | < 150 μs | |
| 4 | ~35,000 | < 200 μs | |
| 8 | ~65,000 | < 250 μs | |
| 16 | ~110,000 | < 300 μs | |
| 32 | ~180,000 | < 400 μs | **典型工作点** |
| 64 | ~220,000 | < 600 μs | 接近饱和 |
| 128 | ~240,000 | < 1 ms | 饱和区 |
| 256 | ~245,000 | < 2 ms | 性能饱和，延迟增加 |

### FIO 配置模板

```ini
[qd_scan]
ioengine=libaio
direct=1
rw=randread
bs=4k
size=1g
numjobs=1
iodepth=${QD}
runtime=60
time_based
group_reporting
write_lat_log=qd_${QD}_lat
write_bw_log=qd_${QD}_bw
```

### 输出示例

```json
{
  "test_name": "queue_depth_scan",
  "timestamp": "2026-03-26T06:45:00",
  "results": [
    {
      "queue_depth": 1,
      "iops": 9876,
      "bandwidth_mbps": 38.6,
      "latency_us": {
        "mean": 98,
        "p99": 145
      }
    },
    {
      "queue_depth": 2,
      "iops": 18234,
      "bandwidth_mbps": 71.2,
      "latency_us": {
        "mean": 105,
        "p99": 156
      }
    },
    {
      "queue_depth": 4,
      "iops": 34567,
      "bandwidth_mbps": 135.0,
      "latency_us": {
        "mean": 112,
        "p99": 189
      }
    },
    ...
    {
      "queue_depth": 256,
      "iops": 245678,
      "bandwidth_mbps": 959.7,
      "latency_us": {
        "mean": 987,
        "p99": 1890
      }
    }
  ],
  "analysis": {
    "optimal_qd": 32,
    "saturation_qd": 128,
    "max_iops": 245678,
    "iops_at_optimal_qd": 180000
  }
}
```

---

## 🔀 测试用例 4：并发测试

### 测试目的
测量多 LU 并发访问时的性能隔离和相互影响

### 测试原理
```
1. 在多个 LU 上同时运行 IO 负载
2. 测量每个 LU 的独立性能
3. 对比单 LU 性能，计算干扰系数
4. 验证 QoS 隔离效果
```

### 测试配置

```python
# test_concurrent.py 配置
CONCURRENT_CONFIG = {
    "num_lu": 4,                 # 4 个 LU 并发
    "block_size": 4096,
    "queue_depth_per_lu": 16,    # 每个 LU QD=16
    "runtime": 300,              # 5 分钟
    "pattern": "randread",
    "load_balance": "uniform",   # 均匀负载
}
```

### 测试场景

| 场景 | LU0 | LU1 | LU2 | LU3 | 目的 |
|------|-----|-----|-----|-----|------|
| **单 LU 基线** | 100% | - | - | - | 建立基线 |
| **双 LU 并发** | 50% | 50% | - | - | 2 路并发 |
| **四 LU 并发** | 25% | 25% | 25% | 25% | 4 路并发 |
| **混合负载** | 读 80% | 写 20% | 混合 50/50 | - | 真实场景 |
| **优先级测试** | 高 | 中 | 低 | - | QoS 隔离 |

### 关键指标

| 指标 | 计算公式 | 目标值 |
|------|----------|--------|
| **总吞吐量** | Σ(各 LU 带宽) | > 单 LU 的 80% |
| **干扰系数** | (单 LU 性能 - 并发性能) / 单 LU 性能 | < 20% |
| **隔离度** | 高优先级 LU 性能保持率 | > 90% |
| **公平性指数** | 1 - (Max-Min)/Avg | > 0.9 |

### FIO 配置示例 (多 Job)

```ini
[global]
ioengine=libaio
direct=1
bs=4k
size=1g
numjobs=1
iodepth=16
runtime=300
time_based
group_reporting

[lu0]
filename=/dev/sda
rw=randread
rate_iops=50000

[lu1]
filename=/dev/sdb
rw=randread
rate_iops=50000

[lu2]
filename=/dev/sdc
rw=randread
rate_iops=50000

[lu3]
filename=/dev/sdd
rw=randread
rate_iops=50000
```

### 输出示例

```json
{
  "test_name": "concurrent_access",
  "timestamp": "2026-03-26T06:50:00",
  "config": {
    "num_lu": 4,
    "queue_depth_per_lu": 16
  },
  "baseline": {
    "single_lu_iops": 180000,
    "single_lu_latency_us": 125
  },
  "results": {
    "lu0": {
      "iops": 42000,
      "bandwidth_mbps": 164.1,
      "latency_us": {"mean": 145, "p99": 320}
    },
    "lu1": {
      "iops": 43500,
      "bandwidth_mbps": 169.9,
      "latency_us": {"mean": 142, "p99": 310}
    },
    "lu2": {
      "iops": 41800,
      "bandwidth_mbps": 163.3,
      "latency_us": {"mean": 148, "p99": 330}
    },
    "lu3": {
      "iops": 42700,
      "bandwidth_mbps": 166.8,
      "latency_us": {"mean": 144, "p99": 315}
    }
  },
  "analysis": {
    "total_iops": 170000,
    "aggregate_efficiency": 0.944,
    "interference_coefficient": 0.056,
    "fairness_index": 0.987,
    "isolation_score": 95.2
  }
}
```

---

## 🛠️ 实现方案

### 1. 代码结构

```python
# systest/suites/qos/__init__.py
from .test_latency import LatencyTest
from .test_jitter import JitterTest
from .test_queue_depth import QueueDepthScanTest
from .test_concurrent import ConcurrentAccessTest

__all__ = [
    'LatencyTest',
    'JitterTest',
    'QueueDepthScanTest',
    'ConcurrentAccessTest',
]
```

### 2. 基类设计

```python
# systest/suites/qos/base.py
from systest.core.test_case import TestCase
from systest.core.collector import FioCollector
from systest.core.reporter import HTMLReporter

class QoSTestCase(TestCase):
    """QoS 测试基类"""
    
    def __init__(self, config):
        super().__init__(config)
        self.collector = FioCollector()
        self.reporter = HTMLReporter()
    
    def analyze_latency_distribution(self, latencies):
        """分析延迟分布"""
        import numpy as np
        
        latencies = np.array(latencies)
        return {
            'min': float(np.min(latencies)),
            'max': float(np.max(latencies)),
            'mean': float(np.mean(latencies)),
            'stddev': float(np.std(latencies)),
            'p50': float(np.percentile(latencies, 50)),
            'p90': float(np.percentile(latencies, 90)),
            'p95': float(np.percentile(latencies, 95)),
            'p99': float(np.percentile(latencies, 99)),
            'p99.9': float(np.percentile(latencies, 99.9)),
            'p99.99': float(np.percentile(latencies, 99.99)),
        }
    
    def calculate_jitter(self, time_series):
        """计算抖动"""
        import numpy as np
        
        series = np.array(time_series)
        mean = np.mean(series)
        stddev = np.std(series)
        cv = stddev / mean if mean > 0 else 0
        
        # 检测毛刺 (> 3σ)
        threshold = mean + 3 * stddev
        spikes = np.sum(series > threshold)
        
        return {
            'mean': float(mean),
            'stddev': float(stddev),
            'cv': float(cv),
            'spike_count': int(spikes),
            'spike_threshold': float(threshold),
        }
```

### 3. 延迟测试实现

```python
# systest/suites/qos/test_latency.py
from .base import QoSTestCase

class LatencyTest(QoSTestCase):
    """延迟分布测试"""
    
    NAME = "qos_latency_distribution"
    DESCRIPTION = "测量 IO 延迟的完整分布，识别尾延迟"
    
    DEFAULT_CONFIG = {
        'block_size': 4096,
        'io_count': 100000,
        'queue_depth': 1,
        'pattern': 'randread',
        'runtime': 300,
    }
    
    def run(self):
        """执行测试"""
        self.logger.info(f"开始延迟分布测试: QD={self.config['queue_depth']}")
        
        # 生成 FIO 配置
        fio_config = self._generate_fio_config()
        
        # 执行测试
        result = self.collector.run_fio(fio_config)
        
        # 解析延迟日志
        latencies = self._parse_latency_log(result.lat_log)
        
        # 分析分布
        distribution = self.analyze_latency_distribution(latencies)
        
        # 生成直方图
        histogram = self._generate_histogram(latencies)
        
        # 判定 (基于 P99)
        p99 = distribution['p99']
        if p99 < 500:
            status = 'PASS'
        elif p99 < 800:
            status = 'WARNING'
        else:
            status = 'FAIL'
        
        return {
            'name': self.NAME,
            'status': status,
            'config': self.config,
            'results': {
                'latency_us': distribution,
                'iops': result.iops,
                'bandwidth_mbps': result.bandwidth,
            },
            'histogram': histogram,
        }
```

### 4. 集成到测试框架

```python
# systest/program.py
from systest.suites.qos import (
    LatencyTest,
    JitterTest,
    QueueDepthScanTest,
    ConcurrentAccessTest,
)

QOS_SUITE = [
    LatencyTest,
    JitterTest,
    QueueDepthScanTest,
    ConcurrentAccessTest,
]

def run_qos_suite(device='/dev/sda', output_dir='./results'):
    """运行完整 QoS 测试套件"""
    results = []
    
    for test_class in QOS_SUITE:
        test = test_class(config={'device': device})
        result = test.run()
        results.append(result)
    
    # 生成综合报告
    reporter = HTMLReporter(output_dir)
    reporter.generate_qos_report(results)
    
    return results
```

---

## 📊 报告生成

### HTML 报告模板

```html
<!DOCTYPE html>
<html>
<head>
    <title>QoS 测试报告</title>
    <style>
        .pass { color: green; }
        .warning { color: orange; }
        .fail { color: red; }
        .histogram { display: flex; }
        .bar { height: 20px; background: #4CAF50; }
    </style>
</head>
<body>
    <h1>QoS 测试报告</h1>
    <p>设备：{{ device }}</p>
    <p>时间：{{ timestamp }}</p>
    
    <h2>1. 延迟分布</h2>
    <table>
        <tr><th>百分位</th><th>延迟 (μs)</th><th>状态</th></tr>
        <tr><td>P50</td><td>{{ p50 }}</td><td class="pass">OK</td></tr>
        <tr><td>P99</td><td>{{ p99 }}</td><td class="{{ p99_status }}">{{ p99_status }}</td></tr>
        <tr><td>P99.99</td><td>{{ p99_99 }}</td><td class="{{ p99_99_status }}">{{ p99_99_status }}</td></tr>
    </table>
    
    <h2>2. 延迟直方图</h2>
    <div class="histogram">
        {% for bucket in histogram %}
        <div class="bar" style="width: {{ bucket.percent }}%;">
            {{ bucket.range }}: {{ bucket.count }}
        </div>
        {% endfor %}
    </div>
    
    <h2>3. QD 扫描曲线</h2>
    <canvas id="qd_chart"></canvas>
    <script>
        // Chart.js 绘制 QD-IOPS 曲线
    </script>
</body>
</html>
```

---

## 📖 参考资料

1. **JEDEC JESD220D** - UFS 3.1 标准 (QoS 要求)
2. **FIO Documentation** - https://fio.readthedocs.io/
3. **SNIA IOTA** - IO 性能测试最佳实践
4. **Linux blk-mq** - 多队列块层架构

---

**学习时间**: 2026-03-26 06:30-07:00  
**下一阶段**: 客户端调试材料准备 (07:00-07:30)
