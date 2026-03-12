#!/bin/bash
# UFS 3.1 代码质量扫描脚本

set -e

# 默认配置
SCAN_CPPCHECK=true
SCAN_CLANG_TIDY=true
SCAN_FORMAT=true
SCAN_VALGRIND=false
OUTPUT_DIR="quality-reports"
SOURCE_DIRS=("src" "include")

# 帮助信息
usage() {
    echo "Usage: $0 [OPTIONS]"
    echo "Options:"
    echo "  --no-cppcheck        Skip cppcheck static analysis"
    echo "  --no-clang-tidy      Skip clang-tidy analysis"
    echo "  --no-format          Skip clang-format check"
    echo "  --valgrind           Run valgrind memory leak check"
    echo "  -o, --output DIR     Output directory (default: $OUTPUT_DIR)"
    echo "  -h, --help           Show this help message"
    exit 1
}

# 解析参数
while [[ $# -gt 0 ]]; do
    case "$1" in
        --no-cppcheck)
            SCAN_CPPCHECK=false
            shift
            ;;
        --no-clang-tidy)
            SCAN_CLANG_TIDY=false
            shift
            ;;
        --no-format)
            SCAN_FORMAT=false
            shift
            ;;
        --valgrind)
            SCAN_VALGRIND=true
            shift
            ;;
        -o|--output)
            OUTPUT_DIR="$2"
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

echo "========================================"
echo "Starting UFS 3.1 code quality scan"
echo "cppcheck: $SCAN_CPPCHECK"
echo "clang-tidy: $SCAN_CLANG_TIDY"
echo "clang-format: $SCAN_FORMAT"
echo "valgrind: $SCAN_VALGRIND"
echo "Output directory: $OUTPUT_DIR"
echo "========================================"

# 创建输出目录
mkdir -p "$OUTPUT_DIR"

# 计数器
ERROR_COUNT=0
WARNING_COUNT=0

# 运行 cppcheck
run_cppcheck() {
    echo "Running cppcheck static analysis..."
    echo "----------------------------------------"
    
    cppcheck --enable=all --inconclusive --std=c++17 \
        --xml --xml-version=2 \
        --output-file="$OUTPUT_DIR/cppcheck-report.xml" \
        --suppressions-list=.cppcheck-suppress \
        ${SOURCE_DIRS[@]} 2> "$OUTPUT_DIR/cppcheck-stderr.txt"
    
    # 统计错误和警告
    ERRORS=$(grep -c "<error" "$OUTPUT_DIR/cppcheck-report.xml" || true)
    WARNINGS=$(grep -c "severity=\"warning\"" "$OUTPUT_DIR/cppcheck-report.xml" || true)
    
    ERROR_COUNT=$((ERROR_COUNT + ERRORS))
    WARNING_COUNT=$((WARNING_COUNT + WARNINGS))
    
    echo "cppcheck found $ERRORS errors, $WARNINGS warnings"
    
    # 显示严重错误
    if [ $ERRORS -gt 0 ]; then
        echo "Critical errors found:"
        grep -A5 -B5 "severity=\"error\"" "$OUTPUT_DIR/cppcheck-report.xml" | head -50
    fi
}

# 运行 clang-tidy
run_clang_tidy() {
    echo "Running clang-tidy analysis..."
    echo "----------------------------------------"
    
    # 收集所有源文件
    SOURCE_FILES=()
    for dir in "${SOURCE_DIRS[@]}"; do
        SOURCE_FILES+=($(find "$dir" -name "*.cpp" -o -name "*.c"))
    done
    
    if [ ${#SOURCE_FILES[@]} -eq 0 ]; then
        echo "No source files found for clang-tidy"
        return
    fi
    
    # 运行 clang-tidy
    clang-tidy -p build/ \
        --checks='-*,performance-*,portability-*,readability-*,bugprone-*,modernize-*' \
        --format-style=file \
        "${SOURCE_FILES[@]}" > "$OUTPUT_DIR/clang-tidy-report.txt" 2>&1
    
    # 统计问题
    ISSUES=$(grep -c ": warning:" "$OUTPUT_DIR/clang-tidy-report.txt" || true)
    WARNING_COUNT=$((WARNING_COUNT + ISSUES))
    
    echo "clang-tidy found $ISSUES issues"
    
    if [ $ISSUES -gt 0 ]; then
        echo "Top issues:"
        head -30 "$OUTPUT_DIR/clang-tidy-report.txt"
    fi
}

# 检查代码格式
run_clang_format() {
    echo "Checking code formatting with clang-format..."
    echo "----------------------------------------"
    
    # 收集所有源文件和头文件
    FILES=()
    for dir in "${SOURCE_DIRS[@]}"; do
        FILES+=($(find "$dir" -name "*.cpp" -o -name "*.h" -o -name "*.hpp"))
    done
    
    if [ ${#FILES[@]} -eq 0 ]; then
        echo "No files found for clang-format check"
        return
    fi
    
    # 检查格式
    clang-format --dry-run --Werror "${FILES[@]}" > "$OUTPUT_DIR/clang-format-report.txt" 2>&1 || true
    
    # 统计问题文件
    FILES_WITH_ISSUES=$(grep -c "warning:" "$OUTPUT_DIR/clang-format-report.txt" || true)
    
    if [ $FILES_WITH_ISSUES -gt 0 ]; then
        echo "clang-format found $FILES_WITH_ISSUES files with formatting issues"
        WARNING_COUNT=$((WARNING_COUNT + FILES_WITH_ISSUES))
        echo "Files with issues:"
        grep "warning:" "$OUTPUT_DIR/clang-format-report.txt" | awk '{print $1}' | sort | uniq
    else
        echo "All files are correctly formatted"
    fi
}

# 运行 valgrind 内存检测
run_valgrind() {
    echo "Running valgrind memory leak check..."
    echo "----------------------------------------"
    
    BUILD_DIR="build/Debug"
    TEST_BINS=$(find "$BUILD_DIR/bin/tests" -name "unit_*" -type f -executable 2>/dev/null | head -5)
    
    if [ -z "$TEST_BINS" ]; then
        echo "No test binaries found for valgrind check"
        return
    fi
    
    MEMORY_ERRORS=0
    
    for test_bin in $TEST_BINS; do
        test_name=$(basename "$test_bin")
        echo "Checking $test_name for memory leaks..."
        
        valgrind --leak-check=full \
            --show-leak-kinds=all \
            --errors-for-leak-kinds=all \
            --error-exitcode=1 \
            --log-file="$OUTPUT_DIR/valgrind-$test_name.log" \
            qemu-aarch64-static "$test_bin" > /dev/null 2>&1 || MEMORY_ERRORS=$((MEMORY_ERRORS + 1))
    done
    
    ERROR_COUNT=$((ERROR_COUNT + MEMORY_ERRORS))
    echo "valgrind found $MEMORY_ERRORS binaries with memory leaks"
}

# 执行扫描
[ "$SCAN_CPPCHECK" = true ] && run_cppcheck
[ "$SCAN_CLANG_TIDY" = true ] && run_clang_tidy
[ "$SCAN_FORMAT" = true ] && run_clang_format
[ "$SCAN_VALGRIND" = true ] && run_valgrind

# 生成汇总报告
echo "========================================"
echo "Quality Scan Summary"
echo "========================================"
echo "Total errors: $ERROR_COUNT"
echo "Total warnings: $WARNING_COUNT"
echo "========================================"

# 生成 HTML 报告（如果有 cppcheck 结果）
if [ -f "$OUTPUT_DIR/cppcheck-report.xml" ]; then
    echo "Generating HTML report..."
    cppcheck-htmlreport --file="$OUTPUT_DIR/cppcheck-report.xml" \
        --report-dir="$OUTPUT_DIR/html" \
        --source-dir=. > /dev/null 2>&1
    echo "HTML report generated at $OUTPUT_DIR/html/index.html"
fi

# 结果判断
if [ $ERROR_COUNT -gt 0 ]; then
    echo "❌ Quality scan failed with $ERROR_COUNT errors!"
    exit 1
elif [ $WARNING_COUNT -gt 0 ]; then
    echo "⚠️  Quality scan passed with $WARNING_COUNT warnings"
    exit 0
else
    echo "✅ Quality scan passed with no issues!"
    exit 0
fi
