#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Test logging functionality"""

import sys
from pathlib import Path

# Add project root to Python path
sys.path.insert(0, str(Path(__file__).parent))

from systest.core.logger import get_logger, close_all_loggers

# Create logger
logger = get_logger(test_id='test_logging', log_dir='logs', console_level=10, file_level=10)

# Test all log levels
logger.debug("This is a DEBUG message")
logger.info("This is an INFO message")
logger.warning("This is a WARNING message")
logger.error("This is an ERROR message with exception", exc_info=True)
logger.critical("This is a CRITICAL message")

# Get log file path
log_file = logger.get_log_file()
print(f"\n✅ Log file created: {log_file}")

# Close logger
close_all_loggers()

# Check files created
import os
log_dir = Path('logs')
files = list(log_dir.glob('test_logging*'))
print(f"\n📁 Files created in logs/:")
for f in files:
    size = f.stat().st_size
    print(f"  - {f.name} ({size} bytes)")

# Verify no error log file
error_files = list(log_dir.glob('*_error.log'))
if error_files:
    print(f"\n❌ ERROR: Found error log files (should not exist):")
    for f in error_files:
        print(f"  - {f.name}")
else:
    print(f"\n✅ No error log files created (as expected)")

# Show log content
if log_file.exists():
    print(f"\n📄 Log file content (last 30 lines):")
    print("=" * 80)
    with open(log_file, 'r', encoding='utf-8') as f:
        lines = f.readlines()
        for line in lines[-30:]:
            print(line, end='')
    print("=" * 80)
