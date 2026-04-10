#!/bin/bash
# UFS Write Booster 配置脚本
# 使用方法：sudo ./configure_ufs_wb.sh [enable|disable|status] [device_path]
# 示例：sudo ./configure_ufs_wb.sh enable /sys/class/scsi_device/0:0:0:2/device

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# 默认参数
ACTION="${1:-status}"
DEFAULT_DEVICE="/sys/class/scsi_device/0:0:0:2/device"
UFS_DEVICE="${2:-$DEFAULT_DEVICE}"

print_header() {
    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}========================================${NC}"
}

print_ok() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warn() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_info() {
    echo -e "   $1"
}

# 检查 root 权限
if [ "$EUID" -ne 0 ] && [ "$ACTION" != "status" ]; then
    print_error "此操作需要 root 权限"
    echo "请使用：sudo $0 $ACTION $UFS_DEVICE"
    exit 1
fi

# 检查设备路径
if [ ! -d "$UFS_DEVICE" ]; then
    print_error "设备路径不存在：$UFS_DEVICE"
    exit 1
fi

# 状态检查函数
check_status() {
    echo ""
    print_header "当前 Write Booster 状态"
    
    if [ -f "$UFS_DEVICE/wb_buf_alloc_units" ]; then
        WB_ALLOC=$(cat "$UFS_DEVICE/wb_buf_alloc_units" 2>/dev/null || echo "0")
        echo "WB 缓冲区分配：$WB_ALLOC 单位"
    fi
    
    if [ -f "$UFS_DEVICE/lu_enable" ]; then
        LU_EN=$(cat "$UFS_DEVICE/lu_enable" 2>/dev/null || echo "0")
        echo "LU 启用状态：$LU_EN"
    fi
    
    if [ -f "$UFS_DEVICE/lu_memory_type" ]; then
        LU_MEM=$(cat "$UFS_DEVICE/lu_memory_type" 2>/dev/null || echo "0")
        echo "LU 内存类型：$LU_MEM"
    fi
    
    echo ""
}

# 启用 Write Booster
enable_wb() {
    print_header "启用 Write Booster"
    echo ""
    
    # 1. 启用 LU
    if [ -f "$UFS_DEVICE/lu_enable" ]; then
        print_info "启用逻辑单元 (LU)..."
        if echo "1" > "$UFS_DEVICE/lu_enable" 2>/dev/null; then
            print_ok "LU 已启用"
        else
            print_warn "LU 启用失败 (可能只读或需要重启)"
        fi
    else
        print_warn "lu_enable 文件不存在"
    fi
    
    # 2. 配置 WB 缓冲区
    if [ -f "$UFS_DEVICE/wb_buf_alloc_units" ]; then
        print_info "配置 WB 缓冲区..."
        # 设置 256 单位 (约 1MB)
        if echo "256" > "$UFS_DEVICE/wb_buf_alloc_units" 2>/dev/null; then
            print_ok "WB 缓冲区已配置 (256 单位)"
        else
            print_warn "WB 缓冲区配置失败 (可能只读)"
        fi
    else
        print_warn "wb_buf_alloc_units 文件不存在"
    fi
    
    # 3. 启用数据可靠性 (可选)
    if [ -f "$UFS_DEVICE/data_reliability" ]; then
        print_info "启用数据可靠性..."
        if echo "1" > "$UFS_DEVICE/data_reliability" 2>/dev/null; then
            print_ok "数据可靠性已启用"
        else
            print_warn "数据可靠性配置失败"
        fi
    fi
    
    # 4. 刷新缓存
    print_info "刷新系统缓存..."
    sync
    echo 3 > /proc/sys/vm/drop_caches 2>/dev/null || true
    
    echo ""
    print_ok "配置完成!"
    echo ""
    print_info "请运行以下命令验证配置:"
    echo "   $0 status $UFS_DEVICE"
    echo ""
    print_warn "注意：某些配置可能需要重启才能生效"
}

# 禁用 Write Booster
disable_wb() {
    print_header "禁用 Write Booster"
    echo ""
    
    # 1. 禁用 LU
    if [ -f "$UFS_DEVICE/lu_enable" ]; then
        print_info "禁用逻辑单元 (LU)..."
        if echo "0" > "$UFS_DEVICE/lu_enable" 2>/dev/null; then
            print_ok "LU 已禁用"
        else
            print_warn "LU 禁用失败"
        fi
    fi
    
    # 2. 清除 WB 缓冲区
    if [ -f "$UFS_DEVICE/wb_buf_alloc_units" ]; then
        print_info "清除 WB 缓冲区..."
        if echo "0" > "$UFS_DEVICE/wb_buf_alloc_units" 2>/dev/null; then
            print_ok "WB 缓冲区已清除"
        else
            print_warn "WB 缓冲区清除失败"
        fi
    fi
    
    # 3. 刷新缓存
    sync
    
    echo ""
    print_ok "Write Booster 已禁用"
}

# 性能测试
test_performance() {
    print_header "Write Booster 性能测试"
    echo ""
    
    # 查找关联的块设备
    BLOCK_DEV=""
    if [ -d "$UFS_DEVICE/block" ]; then
        BLOCK_DEV=$(ls "$UFS_DEVICE/block/" 2>/dev/null | head -1)
    fi
    
    if [ -z "$BLOCK_DEV" ]; then
        print_error "未找到关联的块设备"
        exit 1
    fi
    
    DEVICE="/dev/$BLOCK_DEV"
    print_info "测试设备：$DEVICE"
    echo ""
    
    # 检查 fio 是否安装
    if ! command -v fio &> /dev/null; then
        print_error "fio 未安装，请先安装：apt-get install fio"
        exit 1
    fi
    
    # 顺序写入测试
    print_info "执行顺序写入测试 (1 分钟)..."
    fio --name=seq_write \
        --filename=$DEVICE \
        --rw=write \
        --bs=1M \
        --size=1G \
        --numjobs=1 \
        --iodepth=32 \
        --runtime=60 \
        --time_based \
        --group_reporting \
        --direct=1 \
        --output-format=json 2>/dev/null | \
        python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    bw = data['jobs'][0]['write']['bw_bytes'] / (1024*1024)
    iops = data['jobs'][0]['write']['iops']
    print(f'顺序写入带宽：{bw:.1f} MB/s')
    print(f'顺序写入 IOPS: {iops:.0f}')
except:
    print('测试结果解析失败')
" || echo "测试执行失败"
    
    echo ""
    
    # 随机写入测试
    print_info "执行随机写入测试 (1 分钟)..."
    fio --name=rand_write \
        --filename=$DEVICE \
        --rw=randwrite \
        --bs=4K \
        --size=1G \
        --numjobs=4 \
        --iodepth=32 \
        --runtime=60 \
        --time_based \
        --group_reporting \
        --direct=1 \
        --output-format=json 2>/dev/null | \
        python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    bw = data['jobs'][0]['write']['bw_bytes'] / (1024*1024)
    iops = data['jobs'][0]['write']['iops']
    print(f'随机写入带宽：{bw:.1f} MB/s')
    print(f'随机写入 IOPS: {iops:.0f}')
except:
    print('测试结果解析失败')
" || echo "测试执行失败"
    
    echo ""
    print_header "测试完成"
}

# 主程序
case "$ACTION" in
    status)
        check_status
        ;;
    enable)
        check_status
        enable_wb
        check_status
        ;;
    disable)
        disable_wb
        check_status
        ;;
    test)
        test_performance
        ;;
    *)
        echo "使用方法：$0 [enable|disable|status|test] [device_path]"
        echo ""
        echo "操作:"
        echo "   status   - 查看当前状态"
        echo "   enable   - 启用 Write Booster"
        echo "   disable  - 禁用 Write Booster"
        echo "   test     - 性能测试"
        echo ""
        echo "示例:"
        echo "   $0 status"
        echo "   sudo $0 enable /sys/class/scsi_device/0:0:0:2/device"
        echo "   sudo $0 disable"
        echo "   $0 test"
        ;;
esac
