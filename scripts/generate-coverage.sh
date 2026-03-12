#!/bin/bash
# UFS 3.1 覆盖率报告生成脚本

set -e

# 默认配置
BUILD_TYPE="Debug"
OUTPUT_DIR="coverage-report"
SOURCE_DIRS=("src" "include")
EXCLUDE_PATTERNS=("*/tests/*" "*/examples/*" "*/3rdparty/*")

# 帮助信息
usage() {
    echo "Usage: $0 [OPTIONS]"
    echo "Options:"
    echo "  -t, --build-type TYPE    Build type (default: Debug)"
    echo "  -o, --output DIR         Output directory (default: $OUTPUT_DIR)"
    echo "  --exclude PATTERN        Exclude files matching pattern (can be used multiple times)"
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
        -o|--output)
            OUTPUT_DIR="$2"
            shift 2
            ;;
        --exclude)
            EXCLUDE_PATTERNS+=("$2")
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
echo "Generating coverage report"
echo "Build type: $BUILD_TYPE"
echo "Output directory: $OUTPUT_DIR"
echo "Exclude patterns: ${EXCLUDE_PATTERNS[*]}"
echo "========================================"

# 构建目录
BUILD_DIR="build/$BUILD_TYPE"

# 检查是否存在 gcno 文件
GCNO_FILES=$(find "$BUILD_DIR" -name "*.gcno" | wc -l)
if [ "$GCNO_FILES" -eq 0 ]; then
    echo "Error: No .gcno files found in $BUILD_DIR. Make sure the project was built with coverage flags."
    exit 1
fi

echo "Found $GCNO_FILES coverage files"

# 创建输出目录
mkdir -p "$OUTPUT_DIR"

# 构建 lcov 排除参数
EXCLUDE_ARGS=()
for pattern in "${EXCLUDE_PATTERNS[@]}"; do
    EXCLUDE_ARGS+=("$pattern")
done

# 生成初始覆盖率数据
echo "Capturing coverage data..."
lcov --capture \
    --directory "$BUILD_DIR" \
    --output-file "$OUTPUT_DIR/coverage.info" \
    --rc lcov_branch_coverage=1 \
    --quiet

# 排除不需要的文件
echo "Filtering coverage data..."
lcov --remove "$OUTPUT_DIR/coverage.info" \
    "${EXCLUDE_ARGS[@]}" \
    --output-file "$OUTPUT_DIR/coverage-filtered.info" \
    --rc lcov_branch_coverage=1 \
    --quiet

# 生成 HTML 报告
echo "Generating HTML report..."
genhtml "$OUTPUT_DIR/coverage-filtered.info" \
    --output-directory "$OUTPUT_DIR/html" \
    --title "UFS 3.1 Code Coverage" \
    --show-details \
    --legend \
    --branch-coverage \
    --quiet

# 生成文本摘要
echo "Generating summary report..."
lcov --summary "$OUTPUT_DIR/coverage-filtered.info" \
    --rc lcov_branch_coverage=1 > "$OUTPUT_DIR/summary.txt"

# 显示摘要
echo "========================================"
echo "Coverage Summary"
echo "========================================"
cat "$OUTPUT_DIR/summary.txt"
echo "========================================"

# 提取覆盖率指标
LINE_COVERAGE=$(grep "lines......:" "$OUTPUT_DIR/summary.txt" | awk '{print $2}')
FUNCTION_COVERAGE=$(grep "functions..:" "$OUTPUT_DIR/summary.txt" | awk '{print $2}')
BRANCH_COVERAGE=$(grep "branches...:" "$OUTPUT_DIR/summary.txt" | awk '{print $2}')

echo "Line coverage: $LINE_COVERAGE"
echo "Function coverage: $FUNCTION_COVERAGE"
echo "Branch coverage: $BRANCH_COVERAGE"
echo "HTML report: $OUTPUT_DIR/html/index.html"

# 检查覆盖率阈值（可选）
MIN_LINE_COVERAGE=70
LINE_COVERAGE_NUM=$(echo "$LINE_COVERAGE" | tr -d '%')

if (( $(echo "$LINE_COVERAGE_NUM < $MIN_LINE_COVERAGE" | bc -l) )); then
    echo "⚠️  Warning: Line coverage ($LINE_COVERAGE) is below minimum threshold ($MIN_LINE_COVERAGE%)"
    exit 0  # 警告但不失败，可根据需要改为 exit 1
else
    echo "✅ Line coverage meets minimum requirement of $MIN_LINE_COVERAGE%"
fi

echo "Coverage report generated successfully!"
