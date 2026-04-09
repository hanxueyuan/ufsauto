# UFS Auto - UFS System Test Framework

[![Status: Production Ready](https://img.shields.io/badge/status-production--ready-green)](.)
[![Python](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![FIO](https://img.shields.io/badge/fio-3.20+-orange.svg)](https://github.com/axboe/fio)

Production-grade UFS storage device test framework with performance and QoS test suites.

## 🚀 Quick Start

```bash
# Install FIO
apt-get install fio

# Check environment and save config
python3 systest/bin/systest_cli.py check-env --save-config

# Run performance tests (Development mode - 5 seconds per test)
python3 verify_all_tests.py

# Run performance tests (Production mode)
python3 systest/bin/systest_cli.py run --suite performance

# Run QoS tests
python3 systest/bin/systest_cli.py run --suite qos

# Quick mode (50% test time)
python3 systest/bin/systest_cli.py run --suite performance --quick
```

## 📋 Features

- ✅ **6 Test Cases** - 5 Performance + 1 QoS
- ✅ **Development Mode** - 5 seconds per test, 31 seconds total
- ✅ **Production Mode** - Full 60-second tests with ramp time
- ✅ **HTML/JSON Reports** - Automatic report generation
- ✅ **Batch Testing** - Run multiple times with intervals
- ✅ **Environment Detection** - Auto-detect device and save config
- ✅ **Enhanced Logging** - System snapshots, error tracking, JSON format

## 🏗️ Architecture

```
ufsauto/
├── systest/
│   ├── bin/                  # CLI entry point
│   │   ├── systest_cli.py    # Main CLI tool
│   │   └── check_env.py      # Environment checker
│   ├── core/                 # Core framework
│   │   ├── runner.py         # TestRunner
│   │   ├── collector.py      # ResultCollector
│   │   ├── reporter.py       # ReportGenerator
│   │   └── logger.py         # TestLogger
│   ├── tools/                # Utilities
│   │   ├── fio_wrapper.py    # FIO wrapper
│   │   └── ufs_utils.py      # UFS device utils
│   ├── suites/               # Test suites
│   │   ├── performance/      # 5 tests (refactored)
│   │   └── qos/              # 1 test
│   ├── config/               # Configuration
│   │   └── runtime.json      # Runtime config
│   └── performance_base.py   # ⭐ Base class for performance tests
├── results/                  # Test results
├── logs/                     # Log files
├── verify_all_tests.py       # ⭐ Development mode verification
└── README.md
```

### Data Flow

```
User Command → CLI → TestRunner → Environment Check
                                    ↓
                            Load Test Suites
                                    ↓
                        Each Test Case:
                          setup() → Check prerequisites
                          execute() → FIO test
                          validate() → Compare metrics
                          teardown() → Cleanup
                                    ↓
                            ResultCollector
                                    ↓
                            ReportGenerator
                                    ↓
                            HTML/JSON Report
```

### Test Case Structure (After Refactoring)

**Before**: 300 lines per test file (1265 lines total)  
**After**: 55 lines per test file (270 lines total) - **79% reduction**

```python
# Example: t_perf_SeqReadBurst_001.py (55 lines)
from performance_base import PerformanceTestCase

class Test(PerformanceTestCase):
    """Sequential read performance test"""
    
    name = "seq_read_burst"
    description = "Sequential read performance test"
    
    # FIO configuration
    fio_rw = 'read'
    fio_bs = '128k'
    fio_size = '1G'
    fio_runtime = 60
    
    # Performance targets
    target_bandwidth_mbps = 2100
    max_avg_latency_us = 200
    max_tail_latency_us = 5000
```

**Base Class**: `performance_base.py` provides:
- ✅ Generic `setup()` - Prerequisites check
- ✅ Generic `execute_fio_test()` - FIO execution
- ✅ Generic `validate_performance()` - Metrics validation
- ✅ Generic `teardown()` - Cleanup
- ✅ Mixed read/write support (`fio_rwmixread`)

## 🧪 Test Suites

| Suite | Cases | Description | Test Time |
|-------|-------|-------------|-----------|
| **performance** | 5 | Seq read/write, random read/write, mixed RW | ~25s |
| **qos** | 1 | Latency percentiles (p50/p99/p99.99) | ~5s |

### Performance Tests

| Test | Block Size | QD | Target | Metric |
|------|------------|----|--------|--------|
| Seq Read | 128K | 1 | ≥2100 MB/s | Bandwidth |
| Seq Write | 128K | 1 | ≥1650 MB/s | Bandwidth |
| Rand Read | 4K | 32 | ≥120K IOPS | IOPS |
| Rand Write | 4K | 32 | ≥100K IOPS | IOPS |
| Mixed RW | 4K | 32 | ≥150K IOPS | Total IOPS (70% read) |

### QoS Tests

| Test | Block Size | QD | Target | Metrics |
|------|------------|----|--------|---------|
| Latency Percentile | 4K | 1 | p50<50μs, p99<200μs, p99.99<500μs | Latency distribution |

## 🔧 Configuration

### Runtime Configuration

Edit `systest/config/runtime.json`:

```json
{
  "device": "/dev/sda",
  "test_dir": "/mapdata/ufs_test",
  "device_capacity_gb": 238.2,
  "toolchain": {
    "python": "3.12.3",
    "fio": "3.36"
  }
}
```

### Development Mode Configuration

Edit `systest/config/runtime.json`:

```json
{
  "test_mode": {
    "mode": "development",
    "quick_test": true,
    "runtime_seconds": 5,
    "test_size": "64M",
    "skip_prefill": true
  }
}
```

## 💻 Common Commands

### Environment Setup

```bash
# Check environment and save config
python3 systest/bin/systest_cli.py check-env --save-config

# View configuration
python3 systest/bin/systest_cli.py config --show

# Set device path
python3 systest/bin/systest_cli.py config --device=/dev/sda
```

### Run Tests

```bash
# Development mode (31 seconds for all tests)
python3 verify_all_tests.py

# Production mode - Performance suite
python3 systest/bin/systest_cli.py run --suite performance

# Production mode - QoS suite
python3 systest/bin/systest_cli.py run --suite qos

# Quick mode (50% test time)
python3 systest/bin/systest_cli.py run --suite performance --quick

# Single test
python3 systest/bin/systest_cli.py run --test t_perf_SeqReadBurst_001

# Verbose mode
python3 systest/bin/systest_cli.py run --suite performance -v

# Batch testing (3 times, 60s interval)
python3 systest/bin/systest_cli.py run --suite performance --batch=3 --interval=60

# With custom device
python3 systest/bin/systest_cli.py run --suite performance --device=/dev/sda
```

### View Results

```bash
# List all tests
python3 systest/bin/systest_cli.py list

# View latest report
python3 systest/bin/systest_cli.py report --latest

# View specific report
python3 systest/bin/systest_cli.py report --id=SysTest_performance_20260409_090726

# Export CSV
python3 systest/bin/systest_cli.py report --latest --export-csv
```

### Enhanced Logging

```bash
# Development mode with enhanced logging
python3 verify_all_tests_enhanced.py

# Verbose mode (DEBUG level)
python3 verify_all_tests_enhanced.py --verbose

# Save FIO raw output
python3 verify_all_tests_enhanced.py --save-fio
```

## 📊 Test Results

### Development Mode Results

```
总计：6 个测试用例 | 通过：6 | 失败：0 | 总耗时：31.2 秒

📊 Performance 套件:
seq_read_burst    ✅ 49,865 MB/s   398K IOPS   2.3 μs
seq_write_burst   ✅ 196 MB/s      1.5K IOPS   636 μs
rand_read_burst   ✅ 4,887 MB/s    1,251K IOPS 0.5 μs
rand_write_burst  ✅ 15.5 MB/s     3.9K IOPS   250 μs
mixed_rw          ✅ 12.2 MB/s     3.1K IOPS   57 μs

📊 QoS 套件:
qos_latency       ✅ 4,917 MB/s    1,258K IOPS 0.5 μs
```

### Production Mode Expectations (UFS Gear4 Lane2)

| Test | Expected | Metric |
|------|----------|--------|
| Seq Read | ≥2100 MB/s | Bandwidth |
| Seq Write | ≥1650 MB/s | Bandwidth |
| Rand Read | ≥120K IOPS | IOPS |
| Rand Write | ≥100K IOPS | IOPS |
| Mixed RW | ≥150K IOPS | Total IOPS |
| p50 Latency | <50 μs | Latency |
| p99 Latency | <200 μs | Latency |
| p99.99 Latency | <500 μs | Latency |

## 📁 Project Structure

```
ufsauto/
├── systest/
│   ├── bin/
│   │   ├── systest_cli.py      # Main CLI (updated)
│   │   └── check_env.py        # Environment checker
│   ├── core/
│   │   ├── runner.py           # TestRunner (dry-run removed)
│   │   ├── collector.py        # ResultCollector
│   │   ├── reporter.py         # ReportGenerator
│   │   └── logger.py           # Enhanced logger
│   ├── tools/
│   │   ├── fio_wrapper.py      # FIO wrapper (dry-run removed)
│   │   └── ufs_utils.py        # UFS utilities
│   ├── suites/
│   │   ├── performance/        # 5 tests (refactored, -79% code)
│   │   │   ├── t_perf_SeqReadBurst_001.py
│   │   │   ├── t_perf_SeqWriteBurst_002.py
│   │   │   ├── t_perf_RandReadBurst_003.py
│   │   │   ├── t_perf_RandWriteBurst_004.py
│   │   │   └── t_perf_MixedRw_005.py
│   │   └── qos/
│   │       └── t_qos_LatencyPercentile_001.py
│   ├── config/
│   │   └── runtime.json        # Runtime configuration
│   └── performance_base.py     # ⭐ Base class for performance tests
├── results/                    # Test reports (HTML/JSON/CSV)
├── logs/                       # Enhanced logs (JSON format)
├── verify_all_tests.py         # ⭐ Development mode verification
├── verify_all_tests_enhanced.py # ⭐ Enhanced logging
└── README.md                   # This file
```

## 🎯 Recent Changes (2026-04-09)

### Code Refactoring ⭐

- **Reduced code by 79%** - 1265 lines → 270 lines
- **Introduced base class** - `performance_base.py`
- **Removed dry-run** - All dry-run code eliminated
- **Unified device path** - All tests use `/dev/sda`
- **Added timestamps** - All tests record start time
- **Enhanced documentation** - Complete docstrings

### Features Removed

- ❌ `--dry-run` mode (replaced by fast development mode)
- ❌ Mock metrics generation
- ❌ Dry-run validation logic

### Features Added

- ✅ Development mode (5 seconds per test)
- ✅ Enhanced logging with system snapshots
- ✅ FIO raw output saving
- ✅ Mixed read/write support in base class
- ✅ Verbose mode (--verbose)

## 🆘 Troubleshooting

### Device Not Found

```bash
# Check available devices
lsblk

# Set correct device path
python3 systest/bin/systest_cli.py config --device=/dev/sda
```

### Insufficient Space

```bash
# Check available space
df -h

# Clean test directory
rm -rf /mapdata/ufs_test/*
```

### FIO Not Installed

```bash
# Install FIO
apt-get update
apt-get install -y fio

# Verify installation
fio --version
```

## 📖 Additional Documentation

- `DEPLOY_TO_BOARD.md` - Deployment guide for development boards
- `DEV_MODE_QUICK_TEST.md` - Development mode guide
- `REFACTOR_VERIFICATION_REPORT.md` - Refactoring verification report
- `LOG_OPTIMIZATION_COMPARISON.md` - Logging enhancement comparison

## 📄 License

Production-ready UFS test framework.

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests: `python3 verify_all_tests.py`
5. Submit a pull request

---

**Last Updated**: 2026-04-09  
**Version**: 1.0 (Refactored)  
**Status**: Production Ready ✅
