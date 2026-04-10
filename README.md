# UFS Auto - UFS System Test Framework

[![Status: Production Ready](https://img.shields.io/badge/status-production--ready-green)](.)
[![Python](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![FIO](https://img.shields.io/badge/fio-3.20+-orange.svg)](https://github.com/axboe/fio)

Production-grade UFS storage device test framework.

---

## 🚀 Quick Start

```bash
# 1. Install FIO
apt-get install fio

# 2. Check environment
python3 systest/bin/systest.py check-env --save-config

# 3. Run tests (Development mode - 31 seconds)
python3 systest/bin/systest.py run --suite performance

# 4. Run all tests (Production mode - 6 minutes)
python3 systest/bin/systest.py run --all
```

---

## 📋 Usage Examples

### Environment Setup

```bash
# Check environment and save config
python3 systest/bin/systest.py check-env --save-config

# View configuration
python3 systest/bin/systest.py config --show

# Set device path
python3 systest/bin/systest.py config --device=/dev/sda

# Reset configuration
python3 systest/bin/systest.py config --reset
```

### Run Tests

```bash
# Run performance test suite
python3 systest/bin/systest.py run --suite performance

# Run QoS test suite
python3 systest/bin/systest.py run --suite qos

# Run all test suites
python3 systest/bin/systest.py run --all

# Run single test
python3 systest/bin/systest.py run --test t_perf_SeqReadBurst_001

# Verbose mode (detailed output)
python3 systest/bin/systest.py run --suite performance -v

# Batch testing (3 times, 60s interval)
python3 systest/bin/systest.py run --suite performance --batch=3 --interval=60

# With custom device
python3 systest/bin/systest.py run --suite performance --device=/dev/sda

# With custom test directory
python3 systest/bin/systest.py run --suite performance --test-dir=/mapdata/ufs_test

# Load preset configuration
python3 systest/bin/systest.py run --suite performance --config=configs/ufs31_128GB.json
```

### View Results

```bash
# List all tests
python3 systest/bin/systest.py list

# View latest report
python3 systest/bin/systest.py report --latest

# View specific report
python3 systest/bin/systest.py report --id=SysTest_performance_20260409_090726

# Export CSV
python3 systest/bin/systest.py report --latest --export-csv
```

### Compare Baselines

```bash
# Compare two test results
python3 systest/bin/systest.py compare-baseline --baseline1 results/gold/ --baseline2 results/current/
```

---

## 🧪 Test Suites

| Suite | Cases | Description | Time |
|-------|-------|-------------|------|
| **performance** | 5 | Seq read/write, random read/write, mixed RW | ~25s |
| **qos** | 1 | Latency percentiles (p50/p99/p99.99) | ~5s |

### Performance Tests

| Test | Block Size | QD | Target |
|------|------------|----|--------|
| Seq Read | 128K | 1 | ≥2100 MB/s |
| Seq Write | 128K | 1 | ≥1650 MB/s |
| Rand Read | 4K | 32 | ≥120K IOPS |
| Rand Write | 4K | 32 | ≥100K IOPS |
| Mixed RW | 4K | 32 | ≥150K IOPS (70% read) |

### QoS Tests

| Test | Block Size | QD | Targets |
|------|------------|----|---------|
| Latency Percentile | 4K | 1 | p50<50μs, p99<200μs, p99.99<500μs |

---

## 🔧 Configuration

Edit `systest/config/runtime.json`:

```json
{
  "device": "/dev/sda",
  "test_dir": "/mapdata/ufs_test",
  "test_mode": {
    "mode": "development",
    "runtime_seconds": 5,
    "test_size": "64M",
    "skip_prefill": true
  }
}
```

### Switch to Production Mode

```json
{
  "test_mode": {
    "mode": "production",
    "runtime_seconds": 60,
    "test_size": "1G",
    "skip_prefill": false
  }
}
```

---

## 📁 Project Structure

```
ufsauto/
├── systest/
│   ├── bin/              # CLI entry point (systest.py)
│   ├── core/             # Framework
│   ├── tools/            # Utilities
│   ├── suites/           # Test suites
│   └── config/           # Configuration
├── scripts/              # Helper scripts
├── results/              # Test reports
├── logs/                 # Log files
└── README.md             # This file
```

---

## 🆘 Troubleshooting

### Device Not Found

```bash
# Check available devices
lsblk

# Set correct device
python3 systest/bin/systest.py config --device=/dev/sda
```

### Insufficient Space

```bash
# Check space
df -h

# Clean test directory
rm -rf /mapdata/ufs_test/*
```

### FIO Not Installed

```bash
# Install FIO
apt-get update
apt-get install -y fio

# Verify
fio --version
```

---

## 📖 CLI Help

```bash
# View main help
python3 systest/bin/systest.py --help

# View run command help
python3 systest/bin/systest.py run --help

# View list command help
python3 systest/bin/systest.py list --help

# View report command help
python3 systest/bin/systest.py report --help

# View config command help
python3 systest/bin/systest.py config --help

# View check-env command help
python3 systest/bin/systest.py check-env --help
```

---

**Last Updated**: 2026-04-09  
**Version**: 1.0  
**Status**: Production Ready ✅
