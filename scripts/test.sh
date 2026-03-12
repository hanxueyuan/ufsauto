#!/bin/bash
# UFS 3.1 测试脚本

set -e

# 默认配置
BUILD_TYPE="Release"
RUN_UNIT_TESTS=false
RUN_INTEGRATION_TESTS=false
RUN_PERF_TESTS=false
USE_QEMU=false
JUNIT_XML=""
TEST_FILTER="*"

# 帮助信息
usage() {
    echo "Usage: $0 [OPTIONS]"
    echo "Options:"
    echo "  -t, --build-type TYPE    Build type (Debug/Release, default: Release)"
    echo "  --unit                   Run unit tests"
    echo "  --integration            Run integration tests"
    echo "  --perf                   Run performance tests"
    echo "  --qemu                   Run tests in QEMU ARM emulator"
    echo "  --junitxml FILE          Output JUnit XML report to FILE"
    echo "  --filter PATTERN         Filter tests to run (default: all)"
    echo "  -h, --help               Show this help message"
    exit 1
}

# 解析参数
while [[ $# -gt 0 ]]; do
    case "$1" in
        -t|--build-type)
            BUILD_TYPE="$2"
            shift 2
            ;;
        --unit)
            RUN_UNIT_TESTS=true
            shift
            ;;
        --integration)
            RUN_INTEGRATION_TESTS=true
            shift
            ;;
        --perf)
            RUN_PERF_TESTS=true
            shift
            ;;
        --qemu)
            USE_QEMU=true
            shift
            ;;
        --junitxml)
            JUNIT_XML="$2"
            shift 2
            ;;
        --filter)
            TEST_FILTER="$2"
            shift 2
            ;;
        -h|--help)
            usage
            ;;
        *)
            echo "Unknown option: $1"
            usage
            ;;
    esac
done

# 至少选择一种测试类型
if [ "$RUN_UNIT_TESTS" = false ] && [ "$RUN_INTEGRATION_TESTS" = false ] && [ "$RUN_PERF_TESTS" = false ]; then
    echo "Error: No test type selected. Use --unit, --integration, or --perf."
    exit 1
fi

# 测试执行命令前缀
TEST_PREFIX=""
if [ "$USE_QEMU" = true ]; then
    TEST_PREFIX="qemu-aarch64-static -L /usr/aarch64-linux-gnu/"
    echo "Running tests in QEMU ARM64 emulator"
fi

# 构建目录
BUILD_DIR="build/$BUILD_TYPE"
TEST_DIR="$BUILD_DIR/bin/tests"

echo "========================================"
echo "Starting UFS 3.1 test suite"
echo "Build type: $BUILD_TYPE"
echo "Unit tests: $RUN_UNIT_TESTS"
echo "Integration tests: $RUN_INTEGRATION_TESTS"
echo "Performance tests: $RUN_PERF_TESTS"
echo "QEMU emulation: $USE_QEMU"
echo "Test filter: $TEST_FILTER"
echo "========================================"

# 检查测试目录是否存在
if [ ! -d "$TEST_DIR" ]; then
    echo "Error: Test directory $TEST_DIR not found. Build the project first."
    exit 1
fi

# 测试结果统计
TOTAL_TESTS=0
PASSED_TESTS=0
FAILED_TESTS=0
TEST_RESULTS=()

# 运行单元测试
run_unit_tests() {
    echo "Running unit tests..."
    echo "----------------------------------------"
    
    for test_bin in "$TEST_DIR"/unit_*; do
        if [ -x "$test_bin" ] && [[ "$test_bin" == *"$TEST_FILTER"* ]]; then
            TOTAL_TESTS=$((TOTAL_TESTS + 1))
            test_name=$(basename "$test_bin")
            
            echo "Running test: $test_name"
            
            start_time=$(date +%s.%N)
            
            # 运行测试
            set +e
            if [ -n "$JUNIT_XML" ]; then
                $TEST_PREFIX "$test_bin" --gtest_output=xml:"$JUNIT_XML.$test_name.xml" > "$test_name.log" 2>&1
            else
                $TEST_PREFIX "$test_bin" > "$test_name.log" 2>&1
            fi
            exit_code=$?
            set -e
            
            end_time=$(date +%s.%N)
            duration=$(echo "$end_time - $start_time" | bc)
            
            if [ $exit_code -eq 0 ]; then
                echo "✅ $test_name PASSED (${duration}s)"
                PASSED_TESTS=$((PASSED_TESTS + 1))
                TEST_RESULTS+=("✅ $test_name: PASSED (${duration}s)")
            else
                echo "❌ $test_name FAILED (${duration}s)"
                echo "Error log:"
                cat "$test_name.log"
                FAILED_TESTS=$((FAILED_TESTS + 1))
                TEST_RESULTS+=("❌ $test_name: FAILED (${duration}s)")
            fi
            
            rm -f "$test_name.log"
        fi
    done
}

# 运行集成测试
run_integration_tests() {
    echo "Running integration tests..."
    echo "----------------------------------------"
    
    for test_bin in "$TEST_DIR"/integration_*; do
        if [ -x "$test_bin" ] && [[ "$test_bin" == *"$TEST_FILTER"* ]]; then
            TOTAL_TESTS=$((TOTAL_TESTS + 1))
            test_name=$(basename "$test_bin")
            
            echo "Running test: $test_name"
            
            start_time=$(date +%s.%N)
            
            # 运行测试
            set +e
            if [ -n "$JUNIT_XML" ]; then
                $TEST_PREFIX "$test_bin" --gtest_output=xml:"$JUNIT_XML.$test_name.xml" > "$test_name.log" 2>&1
            else
                $TEST_PREFIX "$test_bin" > "$test_name.log" 2>&1
            fi
            exit_code=$?
            set -e
            
            end_time=$(date +%s.%N)
            duration=$(echo "$end_time - $start_time" | bc)
            
            if [ $exit_code -eq 0 ]; then
                echo "✅ $test_name PASSED (${duration}s)"
                PASSED_TESTS=$((PASSED_TESTS + 1))
                TEST_RESULTS+=("✅ $test_name: PASSED (${duration}s)")
            else
                echo "❌ $test_name FAILED (${duration}s)"
                echo "Error log:"
                cat "$test_name.log"
                FAILED_TESTS=$((FAILED_TESTS + 1))
                TEST_RESULTS+=("❌ $test_name: FAILED (${duration}s)")
            fi
            
            rm -f "$test_name.log"
        fi
    done
}

# 运行性能测试
run_perf_tests() {
    echo "Running performance tests..."
    echo "----------------------------------------"
    
    for test_bin in "$TEST_DIR"/perf_*; do
        if [ -x "$test_bin" ] && [[ "$test_bin" == *"$TEST_FILTER"* ]]; then
            TOTAL_TESTS=$((TOTAL_TESTS + 1))
            test_name=$(basename "$test_bin")
            
            echo "Running test: $test_name"
            
            start_time=$(date +%s.%N)
            
            # 运行性能测试
            set +e
            $TEST_PREFIX "$test_bin" > "$test_name.log" 2>&1
            exit_code=$?
            set -e
            
            end_time=$(date +%s.%N)
            duration=$(echo "$end_time - $start_time" | bc)
            
            if [ $exit_code -eq 0 ]; then
                echo "✅ $test_name PASSED (${duration}s)"
                PASSED_TESTS=$((PASSED_TESTS + 1))
                TEST_RESULTS+=("✅ $test_name: PASSED (${duration}s)")
                
                # 显示性能指标
                echo "Performance metrics:"
                grep -E "(Throughput|Latency|IOPS)" "$test_name.log" || true
            else
                echo "❌ $test_name FAILED (${duration}s)"
                echo "Error log:"
                cat "$test_name.log"
                FAILED_TESTS=$((FAILED_TESTS + 1))
                TEST_RESULTS+=("❌ $test_name: FAILED (${duration}s)")
            fi
            
            rm -f "$test_name.log"
        fi
    done
}

# 执行测试
[ "$RUN_UNIT_TESTS" = true ] && run_unit_tests
[ "$RUN_INTEGRATION_TESTS" = true ] && run_integration_tests
[ "$RUN_PERF_TESTS" = true ] && run_perf_tests

# 合并 JUnit XML 报告
if [ -n "$JUNIT_XML" ]; then
    echo "Merging JUnit reports..."
    # 合并所有 XML 报告到一个文件
    cat "$JUNIT_XML".*.xml > "$JUNIT_XML" 2>/dev/null || true
    rm -f "$JUNIT_XML".*.xml
fi

# 显示测试结果汇总
echo "========================================"
echo "Test Results Summary"
echo "========================================"
echo "Total tests: $TOTAL_TESTS"
echo "Passed: $PASSED_TESTS"
echo "Failed: $FAILED_TESTS"
echo "Pass rate: $(( TOTAL_TESTS > 0 ? PASSED_TESTS * 100 / TOTAL_TESTS : 0 ))%"
echo "========================================"

# 显示详细结果
if [ ${#TEST_RESULTS[@]} -gt 0 ]; then
    echo "Detailed results:"
    for result in "${TEST_RESULTS[@]}"; do
        echo "$result"
    done
    echo "========================================"
fi

# 如果有测试失败，退出并返回错误码
if [ $FAILED_TESTS -gt 0 ]; then
    echo "❌ $FAILED_TESTS tests failed!"
    exit 1
else
    echo "✅ All tests passed!"
    exit 0
fi
