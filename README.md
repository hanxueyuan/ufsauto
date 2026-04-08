# UFS Auto - UFS System Test Framework

[![Status: Production Ready](https://img.shields.io/badge/status-production--ready-green)](.)
[![Python](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![FIO](https://img.shields.io/badge/fio-3.20+-orange.svg)](https://github.com/axboe/fio)

Production-grade UFS storage device test framework with performance and QoS test suites.

## Quick Start

```bash
# Install FIO
apt-get install fio

# Check environment and save config
python3 systest/bin/systest_cli.py check-env --save-config

# Run performance tests
python3 systest/bin/systest_cli.py run --suite performance

# Run QoS tests
python3 systest/bin/systest_cli.py run --suite qos

# Dry-run mode (validate without real tests)
python3 systest/bin/systest_cli.py run --suite performance --dry-run
```

## Architecture

```
ufsauto/
├── systest/
│   ├── bin/              # CLI entry point
│   │   └── systest_cli.py
│   ├── core/             # Core framework
│   │   ├── runner.py     # TestRunner / TestCase
│   │   ├── collector.py  # ResultCollector
│   │   ├── reporter.py   # HTML/JSON Report
│   │   └── logger.py     # TestLogger
│   ├── tools/            # Utilities
│   │   ├── fio_wrapper.py    # FIO wrapper
│   │   └── ufs_utils.py      # UFS device utils
│   ├── suites/           # Test suites
│   │   ├── performance/  # 5 performance tests
│   │   └── qos/          # 1 QoS test
│   └── config/           # runtime.json
├── results/              # Test results
└── logs/                 # Log files
```

### Data Flow

```
User Command → CLI → TestRunner → Environment Check
                                    ↓
                            Load Test Suites
                                    ↓
                        Each Test Case:
                          setup()
                          execute() → FIO
                          validate()
                          teardown()
                                    ↓
                            ResultCollector
                                    ↓
                            ReportGenerator
                                    ↓
                            HTML/JSON Report
```

### Test Case Lifecycle

- **setup()** - Check prerequisites (device, space, FIO, permissions)
- **execute()** - Run FIO test, collect metrics
- **validate()** - Compare metrics against targets, record failures
- **teardown()** - Cleanup test files

## Test Suites

| Suite | Cases | Description |
|-------|-------|-------------|
| performance | 5 | Seq read/write, random read/write, mixed RW |
| qos | 1 | Latency percentiles (p50/p99/p99.99) |

## Configuration

Edit `systest/config/runtime.json`:

```json
{
  "device": "/dev/sda",
  "test_dir": "/mapdata/ufs_test"
}
```

## Common Commands

```bash
# List all tests
python3 systest/bin/systest_cli.py list

# Run specific test
python3 systest/bin/systest_cli.py run --test t_perf_SeqReadBurst_001

# View latest report
python3 systest/bin/systest_cli.py report --latest

# CI/CD mode
python3 systest/bin/systest_cli.py run --suite performance --ci
```
