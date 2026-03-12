#!/bin/bash
# UFS性能测试脚本，基于fio
# 支持顺序读写、随机读写、混合读写等测试场景

set -e

# 默认配置
DEVICE="/dev/ufs0"
OUTPUT_DIR="fio_results"
SIZE="1G"
BLOCK_SIZE="4k"
RUNTIME="300"
IO_DEPTH="32"
NUM_JOBS="4"
DRY_RUN=0

usage() {
    echo "UFS FIO性能测试脚本"
    echo "用法: $0 [选项]"
    echo "选项:"
    echo "  -d, --device DEVICE    测试设备路径 (默认: /dev/ufs0)"
    echo "  -s, --size SIZE        测试数据大小 (默认: 1G)"
    echo "  -b, --block-size SIZE  块大小 (默认: 4k)"
    echo "  -t, --time SEC         测试运行时间 (默认: 300秒)"
    echo "  -i, --iodepth NUM      IO深度 (默认: 32)"
    echo "  -j, --jobs NUM         并发任务数 (默认: 4)"
    echo "  -o, --output DIR       结果输出目录 (默认: fio_results)"
    echo "  -n, --dry-run          仅生成配置文件，不执行测试"
    echo "  -h, --help             显示帮助信息"
    exit 1
}

# 解析命令行参数
while [[ $# -gt 0 ]]; do
    case "$1" in
        -d|--device)
            DEVICE="$2"
            shift 2
            ;;
        -s|--size)
            SIZE="$2"
            shift 2
            ;;
        -b|--block-size)
            BLOCK_SIZE="$2"
            shift 2
            ;;
        -t|--time)
            RUNTIME="$2"
            shift 2
            ;;
        -i|--iodepth)
            IO_DEPTH="$2"
            shift 2
            ;;
        -j|--jobs)
            NUM_JOBS="$2"
            shift 2
            ;;
        -o|--output)
            OUTPUT_DIR="$2"
            shift 2
            ;;
        -n|--dry-run)
            DRY_RUN=1
            shift
            ;;
        -h|--help)
            usage
            ;;
        *)
            echo "未知选项: $1"
            usage
            ;;
    esac
done

# 检查设备
if [ ! -b "$DEVICE" ]; then
    echo "错误：设备 $DEVICE 不存在或不是块设备"
    exit 1
fi

# 创建输出目录
mkdir -p "$OUTPUT_DIR"

echo "====================================="
echo "UFS FIO性能测试配置"
echo "====================================="
echo "测试设备: $DEVICE"
echo "测试大小: $SIZE"
echo "块大小: $BLOCK_SIZE"
echo "测试时间: $RUNTIME 秒"
echo "IO深度: $IO_DEPTH"
echo "并发任务: $NUM_JOBS"
echo "结果目录: $OUTPUT_DIR"
echo "====================================="

if [ $DRY_RUN -eq 0 ]; then
    read -p "警告：测试会覆盖设备上的数据！确认继续？(y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# 生成fio配置文件
create_fio_config() {
    local test_name="$1"
    local rw="$2"
    local rwmixread="${3:-50}"
    
    cat > "$OUTPUT_DIR/$test_name.fio" << EOF
[global]
ioengine=libaio
direct=1
buffered=0
randrepeat=0
size=$SIZE
bs=$BLOCK_SIZE
iodepth=$IO_DEPTH
numjobs=$NUM_JOBS
runtime=$RUNTIME
time_based
group_reporting
filename=$DEVICE
exitall_on_error=1

[$test_name]
rw=$rw
EOF

    if [ "$rw" = "rw" ] || [ "$rw" = "randrw" ]; then
        echo "rwmixread=$rwmixread" >> "$OUTPUT_DIR/$test_name.fio"
    fi
}

# 测试场景
TESTS=(
    "seq_read:read"
    "seq_write:write"
    "rand_read:randread"
    "rand_write:randwrite"
    "rw_mix_70read:randrw:70"
    "rw_mix_50read:randrw:50"
    "rw_mix_30read:randrw:30"
)

echo "生成FIO配置文件..."
for test in "${TESTS[@]}"; do
    IFS=':' read -r name rw mix <<< "$test"
    create_fio_config "$name" "$rw" "$mix"
    echo "  ✅ 已生成: $name.fio"
done

if [ $DRY_RUN -eq 1 ]; then
    echo "干运行模式，配置文件已生成到 $OUTPUT_DIR/ 目录"
    exit 0
fi

# 运行测试
echo "====================================="
echo "开始执行测试，共 ${#TESTS[@]} 个测试项"
echo "预计总耗时: $(( ${#TESTS[@]} * RUNTIME / 60 )) 分钟"
echo "====================================="

RESULTS_FILE="$OUTPUT_DIR/test_summary_$(date +%Y%m%d_%H%M%S).txt"
echo "UFS FIO 性能测试报告" > "$RESULTS_FILE"
echo "测试时间: $(date)" >> "$RESULTS_FILE"
echo "设备: $DEVICE" >> "$RESULTS_FILE"
echo "块大小: $BLOCK_SIZE" >> "$RESULTS_FILE"
echo "IO深度: $IO_DEPTH" >> "$RESULTS_FILE"
echo "并发任务: $NUM_JOBS" >> "$RESULTS_FILE"
echo "=====================================" >> "$RESULTS_FILE"
echo "" >> "$RESULTS_FILE"

for test in "${TESTS[@]}"; do
    IFS=':' read -r name rw mix <<< "$test"
    echo ""
    echo "▶️  开始测试: $name"
    echo "-------------------------------------"
    
    # 运行fio测试
    fio "$OUTPUT_DIR/$name.fio" --output="$OUTPUT_DIR/$name.result"
    
    # 提取结果
    if [ "$rw" = "read" ] || [ "$rw" = "randread" ]; then
        bw=$(grep -i "read:" "$OUTPUT_DIR/$name.result" | awk '{print $2}' | sed 's/BW=//')
        iops=$(grep -i "read:" "$OUTPUT_DIR/$name.result" | awk -F'IOPS=' '{print $2}' | awk '{print $1}')
        lat=$(grep -i "lat" "$OUTPUT_DIR/$name.result" | grep avg | head -1 | awk '{print $3}')
        
        echo "读取带宽: $bw"
        echo "读取IOPS: $iops"
        echo "平均延迟: $lat"
        
        echo "$name:" >> "$RESULTS_FILE"
        echo "  类型: 读取" >> "$RESULTS_FILE"
        echo "  带宽: $bw" >> "$RESULTS_FILE"
        echo "  IOPS: $iops" >> "$RESULTS_FILE"
        echo "  平均延迟: $lat" >> "$RESULTS_FILE"
        
    elif [ "$rw" = "write" ] || [ "$rw" = "randwrite" ]; then
        bw=$(grep -i "write:" "$OUTPUT_DIR/$name.result" | awk '{print $2}' | sed 's/BW=//')
        iops=$(grep -i "write:" "$OUTPUT_DIR/$name.result" | awk -F'IOPS=' '{print $2}' | awk '{print $1}')
        lat=$(grep -i "lat" "$OUTPUT_DIR/$name.result" | grep avg | head -1 | awk '{print $3}')
        
        echo "写入带宽: $bw"
        echo "写入IOPS: $iops"
        echo "平均延迟: $lat"
        
        echo "$name:" >> "$RESULTS_FILE"
        echo "  类型: 写入" >> "$RESULTS_FILE"
        echo "  带宽: $bw" >> "$RESULTS_FILE"
        echo "  IOPS: $iops" >> "$RESULTS_FILE"
        echo "  平均延迟: $lat" >> "$RESULTS_FILE"
        
    else
        read_bw=$(grep -i "read:" "$OUTPUT_DIR/$name.result" | awk '{print $2}' | sed 's/BW=//')
        read_iops=$(grep -i "read:" "$OUTPUT_DIR/$name.result" | awk -F'IOPS=' '{print $2}' | awk '{print $1}')
        write_bw=$(grep -i "write:" "$OUTPUT_DIR/$name.result" | awk '{print $2}' | sed 's/BW=//')
        write_iops=$(grep -i "write:" "$OUTPUT_DIR/$name.result" | awk -F'IOPS=' '{print $2}' | awk '{print $1}')
        lat=$(grep -i "lat" "$OUTPUT_DIR/$name.result" | grep avg | head -1 | awk '{print $3}')
        
        echo "读取带宽: $read_bw"
        echo "读取IOPS: $read_iops"
        echo "写入带宽: $write_bw"
        echo "写入IOPS: $write_iops"
        echo "平均延迟: $lat"
        
        echo "$name (读写混合 $rwmixread%读):" >> "$RESULTS_FILE"
        echo "  读取带宽: $read_bw" >> "$RESULTS_FILE"
        echo "  读取IOPS: $read_iops" >> "$RESULTS_FILE"
        echo "  写入带宽: $write_bw" >> "$RESULTS_FILE"
        echo "  写入IOPS: $write_iops" >> "$RESULTS_FILE"
        echo "  平均延迟: $lat" >> "$RESULTS_FILE"
    fi
    
    echo "" >> "$RESULTS_FILE"
    echo "✅ 测试完成: $name"
    
    # 设备降温
    echo "等待设备冷却 10 秒..."
    sleep 10
done

echo "====================================="
echo "所有测试完成！"
echo "结果摘要已保存到: $RESULTS_FILE"
echo "详细结果保存在: $OUTPUT_DIR/ 目录"
echo "====================================="

# 显示摘要
echo ""
echo "测试结果摘要:"
echo "====================================="
cat "$RESULTS_FILE"
