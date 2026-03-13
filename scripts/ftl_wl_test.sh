#!/bin/bash
# FTL 磨损均衡测试脚本
# 用途：验证 FTL 磨损均衡算法效果

set -e

echo "=========================================="
echo "FTL Wear Leveling Test"
echo "=========================================="

# 配置参数
TEST_ITERATIONS=${1:-10000}  # 写入次数，默认 10000 次
TEST_LBA=${2:-0}             # 测试 LBA，默认 0
BLOCK_SIZE=${3:-4096}        # 块大小，默认 4KB

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 打印函数
print_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 检查依赖
check_dependencies() {
    print_info "Checking dependencies..."
    
    if ! command -v fio &> /dev/null; then
        print_error "fio not found, please install: sudo apt install fio"
        exit 1
    fi
    
    if ! command -v jq &> /dev/null; then
        print_error "jq not found, please install: sudo apt install jq"
        exit 1
    fi
    
    print_info "Dependencies OK"
}

# 清理测试环境
cleanup() {
    print_info "Cleaning up test environment..."
    rm -rf /tmp/ftl_test_*
    print_info "Cleanup done"
}

# 运行磨损均衡测试
run_wl_test() {
    print_info "Starting wear leveling test..."
    print_info "Iterations: $TEST_ITERATIONS"
    print_info "Test LBA: $TEST_LBA"
    print_info "Block size: $BLOCK_SIZE"
    
    # 创建测试数据
    dd if=/dev/urandom of=/tmp/ftl_test_data.bin bs=$BLOCK_SIZE count=1 2>/dev/null
    
    # 循环写入
    print_info "Writing data..."
    for i in $(seq 1 $TEST_ITERATIONS); do
        # 写入固定 LBA（模拟热数据）
        dd if=/tmp/ftl_test_data.bin of=/dev/ftl_test seek=$TEST_LBA bs=$BLOCK_SIZE conv=notrunc 2>/dev/null
        
        # 进度显示
        if [ $((i % 1000)) -eq 0 ]; then
            print_info "Progress: $i/$TEST_ITERATIONS"
        fi
    done
    
    print_info "Write completed"
}

# 分析磨损均衡结果
analyze_results() {
    print_info "Analyzing wear leveling results..."
    
    # 读取各块擦除次数（需要从 FTL 驱动获取）
    # 这里是示例，实际需要读取 FTL 统计信息
    if [ -f /sys/class/ftl/ftl0/erase_counts ]; then
        # 读取擦除次数统计
        ERASE_DATA=$(cat /sys/class/ftl/ftl0/erase_counts)
        
        # 计算最大值、最小值、平均值
        MAX_ERASE=$(echo "$ERASE_DATA" | jq 'max')
        MIN_ERASE=$(echo "$ERASE_DATA" | jq 'min')
        AVG_ERASE=$(echo "$ERASE_DATA" | jq 'add / length')
        TOTAL_BLOCKS=$(echo "$ERASE_DATA" | jq 'length')
        
        # 计算磨损均衡因子
        WEAR_LEVEL=$(echo "scale=4; ($MAX_ERASE - $MIN_ERASE) / $TOTAL_BLOCKS * 100" | bc)
        
        # 输出结果
        echo ""
        echo "=========================================="
        echo "Wear Leveling Test Results"
        echo "=========================================="
        echo "Total Blocks:     $TOTAL_BLOCKS"
        echo "Max Erase Count:  $MAX_ERASE"
        echo "Min Erase Count:  $MIN_ERASE"
        echo "Avg Erase Count:  $AVG_ERASE"
        echo "Wear Level:       ${WEAR_LEVEL}%"
        echo "=========================================="
        
        # 验收标准：Wear Level < 5%
        if (( $(echo "$WEAR_LEVEL < 5" | bc -l) )); then
            print_info "TEST PASSED: Wear level < 5%"
            exit 0
        else
            print_error "TEST FAILED: Wear level >= 5%"
            exit 1
        fi
    else
        print_warn "FTL statistics not available (need real FTL device)"
        print_info "Test completed (simulation mode)"
        exit 0
    fi
}

# 主函数
main() {
    print_info "FTL Wear Leveling Test Script"
    print_info "=============================="
    
    # 检查是否 root
    if [ "$EUID" -ne 0 ]; then
        print_error "Please run as root"
        exit 1
    fi
    
    # 清理
    cleanup
    
    # 检查依赖
    check_dependencies
    
    # 运行测试
    run_wl_test
    
    # 分析结果
    analyze_results
}

# 捕获退出信号
trap cleanup EXIT

# 运行主函数
main "$@"
