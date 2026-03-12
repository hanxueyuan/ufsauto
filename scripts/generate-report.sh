#!/bin/bash
# UFS 3.1 CI 报告生成脚本

set -e

# 默认配置
WORKFLOW_NAME="UFS 3.1 CI Pipeline"
RUN_ID=""
STATUS="unknown"
OUTPUT_FILE="ci-report.md"
REPO_URL="https://github.com/${GITHUB_REPOSITORY:-}"

# 帮助信息
usage() {
    echo "Usage: $0 [OPTIONS]"
    echo "Options:"
    echo "  --workflow NAME      Workflow name (default: $WORKFLOW_NAME)"
    echo "  --run-id ID          GitHub Actions run ID"
    echo "  --status STATUS      Pipeline status (success/failure/cancelled)"
    echo "  --output FILE        Output markdown file (default: $OUTPUT_FILE)"
    echo "  --repo-url URL       Repository URL (default: $REPO_URL)"
    echo "  -h, --help           Show this help message"
    exit 1
}

# 解析参数
while [[ $# -gt 0 ]]; do
    case "$1" in
        --workflow)
            WORKFLOW_NAME="$2"
            shift 2
            ;;
        --run-id)
            RUN_ID="$2"
            shift 2
            ;;
        --status)
            STATUS="$2"
            shift 2
            ;;
        --output)
            OUTPUT_FILE="$2"
            shift 2
            ;;
        --repo-url)
            REPO_URL="$2"
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

# 状态图标
STATUS_ICON="❓"
STATUS_TEXT="Unknown"
case "$STATUS" in
    success)
        STATUS_ICON="✅"
        STATUS_TEXT="成功"
        ;;
    failure)
        STATUS_ICON="❌"
        STATUS_TEXT="失败"
        ;;
    cancelled)
        STATUS_ICON="🚫"
        STATUS_TEXT="取消"
        ;;
esac

# 构建详情链接
RUN_URL=""
if [ -n "$RUN_ID" ] && [ -n "$REPO_URL" ]; then
    RUN_URL="$REPO_URL/actions/runs/$RUN_ID"
fi

echo "Generating CI report..."

# 生成报告头
cat > "$OUTPUT_FILE" << EOF
# $STATUS_ICON $WORKFLOW_NAME $STATUS_TEXT

## 📊 基本信息
| 项 | 值 |
|----|----|
| 流水线名称 | $WORKFLOW_NAME |
| 运行 ID | $RUN_ID |
| 状态 | $STATUS_TEXT |
| 触发分支 | ${GITHUB_REF_NAME:-} |
| 提交 SHA | ${GITHUB_SHA:-} |
| 提交信息 | ${GITHUB_EVENT_HEAD_COMMIT_MESSAGE:-} |
| 提交人 | ${GITHUB_EVENT_HEAD_COMMIT_AUTHOR_NAME:-} |
| 触发时间 | $(date "+%Y-%m-%d %H:%M:%S") |
EOF

# 添加运行链接
if [ -n "$RUN_URL" ]; then
    cat >> "$OUTPUT_FILE" << EOF
| 详情链接 | [点击查看]($RUN_URL) |
EOF
fi

# 分隔线
echo -e "\n---\n" >> "$OUTPUT_FILE"

# 收集构建结果
BUILD_RESULTS=""
if [ -d "artifacts/build-Release" ]; then
    BUILD_FILES=$(find artifacts/build-Release/bin -type f | wc -l)
    BUILD_SIZE=$(du -sh artifacts/build-Release | cut -f1)
    BUILD_RESULTS="✅ Release 构建成功，生成 $BUILD_FILES 个文件，总大小 $BUILD_SIZE"
else
    BUILD_RESULTS="❌ Release 构建失败"
fi

if [ -d "artifacts/build-Debug" ]; then
    DEBUG_FILES=$(find artifacts/build-Debug/bin -type f | wc -l)
    DEBUG_SIZE=$(du -sh artifacts/build-Debug | cut -f1)
    BUILD_RESULTS="$BUILD_RESULTS\n✅ Debug 构建成功，生成 $DEBUG_FILES 个文件，总大小 $DEBUG_SIZE"
else
    BUILD_RESULTS="$BUILD_RESULTS\n❌ Debug 构建失败"
fi

cat >> "$OUTPUT_FILE" << EOF
## 🏗️ 构建结果
$BUILD_RESULTS

---
EOF

# 收集测试结果
TEST_RESULTS=""
TOTAL_TESTS=0
PASSED_TESTS=0
FAILED_TESTS=0

if [ -d "artifacts/test-results-Release" ]; then
    # 统计 Release 测试结果
    if ls artifacts/test-results-Release/test-results-*.xml 1> /dev/null 2>&1; then
        RELEASE_TOTAL=$(grep -r "tests=\"" artifacts/test-results-Release/*.xml | awk -F'tests="' '{sum += $2} END {print sum+0}')
        RELEASE_PASSED=$(grep -r "passed=\"" artifacts/test-results-Release/*.xml | awk -F'passed="' '{sum += $2} END {print sum+0}')
        RELEASE_FAILED=$(grep -r "failed=\"" artifacts/test-results-Release/*.xml | awk -F'failed="' '{sum += $2} END {print sum+0}')
        
        TOTAL_TESTS=$((TOTAL_TESTS + RELEASE_TOTAL))
        PASSED_TESTS=$((PASSED_TESTS + RELEASE_PASSED))
        FAILED_TESTS=$((FAILED_TESTS + RELEASE_FAILED))
        
        TEST_RESULTS="✅ Release 测试：$RELEASE_PASSED / $RELEASE_TOTAL 测试通过"
        if [ $RELEASE_FAILED -gt 0 ]; then
            TEST_RESULTS="$TEST_RESULTS (失败 $RELEASE_FAILED 个)"
        fi
    fi
else
    TEST_RESULTS="❌ Release 测试未执行"
fi

if [ -d "artifacts/test-results-Debug" ]; then
    # 统计 Debug 测试结果
    if ls artifacts/test-results-Debug/test-results-*.xml 1> /dev/null 2>&1; then
        DEBUG_TOTAL=$(grep -r "tests=\"" artifacts/test-results-Debug/*.xml | awk -F'tests="' '{sum += $2} END {print sum+0}')
        DEBUG_PASSED=$(grep -r "passed=\"" artifacts/test-results-Debug/*.xml | awk -F'passed="' '{sum += $2} END {print sum+0}')
        DEBUG_FAILED=$(grep -r "failed=\"" artifacts/test-results-Debug/*.xml | awk -F'failed="' '{sum += $2} END {print sum+0}')
        
        TOTAL_TESTS=$((TOTAL_TESTS + DEBUG_TOTAL))
        PASSED_TESTS=$((PASSED_TESTS + DEBUG_PASSED))
        FAILED_TESTS=$((FAILED_TESTS + DEBUG_FAILED))
        
        TEST_RESULTS="$TEST_RESULTS\n✅ Debug 测试：$DEBUG_PASSED / $DEBUG_TOTAL 测试通过"
        if [ $DEBUG_FAILED -gt 0 ]; then
            TEST_RESULTS="$TEST_RESULTS (失败 $DEBUG_FAILED 个)"
        fi
    fi
else
    TEST_RESULTS="$TEST_RESULTS\n❌ Debug 测试未执行"
fi

# 计算通过率
PASS_RATE=0
if [ $TOTAL_TESTS -gt 0 ]; then
    PASS_RATE=$((PASSED_TESTS * 100 / TOTAL_TESTS))
fi

cat >> "$OUTPUT_FILE" << EOF

## 🧪 测试结果
### 测试汇总
| 总测试数 | 成功 | 失败 | 通过率 |
|----------|------|------|--------|
| $TOTAL_TESTS | $PASSED_TESTS | $FAILED_TESTS | $PASS_RATE% |

### 详细结果
$TEST_RESULTS
---
EOF

# 收集覆盖率报告
COVERAGE_REPORT=""
if [ -d "artifacts/test-results-Debug/coverage-report" ]; then
    COVERAGE_FILE="artifacts/test-results-Debug/coverage-report/index.html"
    if [ -f "$COVERAGE_FILE" ]; then
        LINE_COVERAGE=$(grep -A5 "Lines" "$COVERAGE_FILE" | grep -o "[0-9.]*%" | head -1)
        FUNCTION_COVERAGE=$(grep -A5 "Functions" "$COVERAGE_FILE" | grep -o "[0-9.]*%" | head -1)
        
        COVERAGE_REPORT="✅ 覆盖率报告已生成\n- 行覆盖率：$LINE_COVERAGE\n- 函数覆盖率：$FUNCTION_COVERAGE"
    fi
else
    COVERAGE_REPORT="ℹ️  覆盖率报告未生成"
fi

cat >> "$OUTPUT_FILE" << EOF

## 📈 覆盖率报告
$COVERAGE_REPORT

---
EOF

# 收集代码质量扫描结果
QUALITY_RESULTS=""
CPPCHECK_ERRORS=0
CLANG_TIDY_ISSUES=0
FORMAT_ISSUES=0

if [ -d "artifacts/quality-reports" ]; then
    if [ -f "artifacts/quality-reports/cppcheck-report.xml" ]; then
        CPPCHECK_ERRORS=$(grep -c "<error" artifacts/quality-reports/cppcheck-report.xml || true)
    fi
    
    if [ -f "artifacts/quality-reports/clang-tidy-report.txt" ]; then
        CLANG_TIDY_ISSUES=$(grep -c ": warning:" artifacts/quality-reports/clang-tidy-report.txt || true)
    fi
    
    if [ -f "artifacts/quality-reports/clang-format-report.txt" ]; then
        FORMAT_ISSUES=$(grep -c "warning:" artifacts/quality-reports/clang-format-report.txt || true)
    fi
    
    QUALITY_RESULTS="### 代码质量扫描结果\n| 检查项 | 问题数 |\n|--------|--------|\n| cppcheck 错误 | $CPPCHECK_ERRORS |\n| clang-tidy 问题 | $CLANG_TIDY_ISSUES |\n| 格式问题 | $FORMAT_ISSUES |"
    
    TOTAL_QUALITY_ISSUES=$((CPPCHECK_ERRORS + CLANG_TIDY_ISSUES + FORMAT_ISSUES))
    if [ $TOTAL_QUALITY_ISSUES -eq 0 ]; then
        QUALITY_RESULTS="$QUALITY_RESULTS\n\n✅ 代码质量检查全部通过！"
    else
        QUALITY_RESULTS="$QUALITY_RESULTS\n\n⚠️  共发现 $TOTAL_QUALITY_ISSUES 个代码质量问题，请查看详细报告。"
    fi
else
    QUALITY_RESULTS="❌ 代码质量扫描未执行"
fi

cat >> "$OUTPUT_FILE" << EOF

## 🔍 代码质量检查
$QUALITY_RESULTS

---
EOF

# 页脚
cat >> "$OUTPUT_FILE" << EOF

## 📎 附件
所有构建产物、测试报告和质量扫描结果已作为工作流附件保存，保留 14 天。

---
*报告由 UFS 3.1 CI 系统自动生成*
EOF

echo "Report generated successfully: $OUTPUT_FILE"
echo "Report preview:"
echo "========================================"
cat "$OUTPUT_FILE" | head -50
echo "========================================"
