# 代码审查自动化检查清单

## 一、静态代码检查

### C 代码检查
```bash
# 1. MISRA 规范检查
cppcheck --enable=all --std=c11 --misra-version=2012 --suppressions-list=misra_suppressions.txt src/

# 2. 代码风格检查
clang-format --style=file --dry-run src/**/*.c src/**/*.h

# 3. 静态分析
scan-build make
```

### Python 代码检查
```bash
# 1. PEP 8 规范检查
flake8 --max-line-length=120 src/

# 2. 类型检查
mypy src/

# 3. 安全检查
bandit -r src/
```

## 二、单元测试与覆盖率检查
```bash
# 运行单元测试
make test

# 生成覆盖率报告
gcovr --root . --filter src/ --html-details coverage.html --threshold 80

# 检查覆盖率是否达标
gcovr --root . --filter src/ --fail-under-line 80
```

## 三、性能测试
```bash
# 顺序读写性能测试
./perf_test --seq-read --seq-write --block-size=4K --count=10000

# 随机读写性能测试
./perf_test --rand-read --rand-write --block-size=4K --count=10000

# 延迟测试
./latency_test --iterations=10000
```

## 四、内存检查
```bash
# 内存泄漏检查
valgrind --leak-check=full --show-leak-kinds=all ./test_runner

# 内存错误检查
valgrind --tool=memcheck --track-origins=yes ./test_runner
```

## 五、ARM 架构兼容性检查
```bash
# 交叉编译检查
make CROSS_COMPILE=arm-linux-gnueabihf-
make CROSS_COMPILE=aarch64-linux-gnu-

# 静态分析 ARM 特定代码
clang --target=arm-linux-gnueabihf --analyze src/**/*.c
```

## 六、CI 流水线自动检查项
- [ ] 代码编译成功
- [ ] 静态代码检查通过
- [ ] 单元测试全部通过
- [ ] 测试覆盖率 ≥ 80%
- [ ] 性能测试符合指标
- [ ] 内存检查无泄漏/错误
- [ ] ARM 交叉编译成功
- [ ] 代码风格符合规范

## 七、自动化脚本配置示例
```yaml
# .github/workflows/code-review.yml
name: Code Review Checks
on: [pull_request]

jobs:
  static-check:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: C static check
        run: |
          sudo apt install -y cppcheck clang-format
          cppcheck --enable=all --std=c11 src/
          clang-format --style=file --dry-run src/**/*.c src/**/*.h
      
      - name: Python static check
        run: |
          pip install flake8 mypy bandit
          flake8 --max-line-length=120 src/
          mypy src/
          bandit -r src/

  test-coverage:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Build and test
        run: |
          make test
          sudo apt install -y gcovr
          gcovr --root . --filter src/ --fail-under-line 80

  performance-test:
    runs-on: [self-hosted, arm64]
    steps:
      - uses: actions/checkout@v4
      - name: Performance test
        run: |
          make perf
          ./perf_test --seq-read --threshold=2000 --seq-write --threshold=1500
```
