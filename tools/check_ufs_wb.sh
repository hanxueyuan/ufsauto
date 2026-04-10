#!/bin/bash
# UFS Write Booster 状态检查脚本
# 使用方法：./check_ufs_wb.sh [device_path]
# 示例：./check_ufs_wb.sh /sys/class/scsi_device/0:0:0:2/device

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 默认设备路径
DEFAULT_DEVICE="/sys/class/scsi_device/0:0:0:2/device"
UFS_DEVICE="${1:-$DEFAULT_DEVICE}"

# 打印函数
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

# 检查设备路径
if [ ! -d "$UFS_DEVICE" ]; then
    print_error "设备路径不存在：$UFS_DEVICE"
    echo ""
    echo "可用的 SCSI 设备:"
    ls -d /sys/class/scsi_device/*/device 2>/dev/null || echo "  未找到 SCSI 设备"
    echo ""
    echo "使用方法：$0 [设备路径]"
    echo "示例：$0 /sys/class/scsi_device/0:0:0:2/device"
    exit 1
fi

print_header "UFS Write Booster 状态检查"
echo ""
print_info "设备路径：$UFS_DEVICE"
echo ""

# 1. 检查 WB 缓冲区分配
print_header "1. Write Booster 缓冲区"
if [ -f "$UFS_DEVICE/wb_buf_alloc_units" ]; then
    WB_ALLOC=$(cat "$UFS_DEVICE/wb_buf_alloc_units" 2>/dev/null || echo "0")
    if [ "$WB_ALLOC" -gt 0 ] 2>/dev/null; then
        # 计算实际大小 (假设 1 单位 = 4KB)
        WB_SIZE_KB=$((WB_ALLOC * 4))
        WB_SIZE_MB=$((WB_SIZE_KB / 1024))
        print_ok "Write Booster 缓冲区：已分配"
        print_info "分配单位：$WB_ALLOC"
        print_info "缓冲区大小：约 ${WB_SIZE_MB}MB (${WB_SIZE_KB}KB)"
    else
        print_warn "Write Booster 缓冲区：未分配或为 0"
    fi
else
    print_warn "wb_buf_alloc_units: 文件不存在"
fi
echo ""

# 2. 检查 LU 启用状态
print_header "2. 逻辑单元 (LU) 状态"
if [ -f "$UFS_DEVICE/lu_enable" ]; then
    LU_EN=$(cat "$UFS_DEVICE/lu_enable" 2>/dev/null || echo "-1")
    if [ "$LU_EN" -eq 1 ] 2>/dev/null; then
        print_ok "LU 状态：已启用"
    elif [ "$LU_EN" -eq 0 ] 2>/dev/null; then
        print_warn "LU 状态：已禁用"
    else
        print_info "LU 状态：$LU_EN"
    fi
else
    print_warn "lu_enable: 文件不存在"
fi

if [ -f "$UFS_DEVICE/lu_memory_type" ]; then
    LU_MEM=$(cat "$UFS_DEVICE/lu_memory_type" 2>/dev/null || echo "-1")
    print_info "LU 内存类型："
    case $LU_MEM in
        0) print_info "  - Unknown" ;;
        1) print_info "  - General Purpose (TLC/QLC)" ;;
        2) print_ok "  - SLC / Write Booster" ;;
        3) print_info "  - Reserved" ;;
        *) print_info "  - Unknown ($LU_MEM)" ;;
    esac
else
    print_warn "lu_memory_type: 文件不存在"
fi

if [ -f "$UFS_DEVICE/lu_queue_depth" ]; then
    LU_QD=$(cat "$UFS_DEVICE/lu_queue_depth" 2>/dev/null || echo "N/A")
    print_info "LU 队列深度：$LU_QD"
fi
echo ""

# 3. 检查数据可靠性
print_header "3. 数据可靠性"
if [ -f "$UFS_DEVICE/data_reliability" ]; then
    RELIABILITY=$(cat "$UFS_DEVICE/data_reliability" 2>/dev/null || echo "-1")
    if [ "$RELIABILITY" -eq 1 ] 2>/dev/null; then
        print_ok "数据可靠性：已启用"
    else
        print_info "数据可靠性：未启用 ($RELIABILITY)"
    fi
else
    print_warn "data_reliability: 文件不存在"
fi

if [ -f "$UFS_DEVICE/provisioning_type" ]; then
    PROV_TYPE=$(cat "$UFS_DEVICE/provisioning_type" 2>/dev/null || echo "N/A")
    print_info "Provisioning 类型："
    case $PROV_TYPE in
        0) print_info "  - Default" ;;
        1) print_info "  - Thin Provisioning" ;;
        2) print_info "  - Full Provisioning" ;;
        *) print_info "  - Unknown ($PROV_TYPE)" ;;
    esac
else
    print_warn "provisioning_type: 文件不存在"
fi
echo ""

# 4. 检查 HPB 状态 (与 WB 配合使用)
print_header "4. Host Performance Booster (HPB)"
if [ -f "$UFS_DEVICE/hpb_lu_max_active_regions" ]; then
    HPB_MAX=$(cat "$UFS_DEVICE/hpb_lu_max_active_regions" 2>/dev/null || echo "0")
    print_info "HPB 最大活动区域：$HPB_MAX"
fi

if [ -f "$UFS_DEVICE/hpb_number_pinned_regions" ]; then
    HPB_PINNED=$(cat "$UFS_DEVICE/hpb_number_pinned_regions" 2>/dev/null || echo "0")
    print_info "HPB 固定区域数：$HPB_PINNED"
fi

if [ -f "$UFS_DEVICE/hpb_pinned_region_start_offset" ]; then
    HPB_OFFSET=$(cat "$UFS_DEVICE/hpb_pinned_region_start_offset" 2>/dev/null || echo "0")
    print_info "HPB 固定区域起始偏移：$HPB_OFFSET"
fi

if [ ! -f "$UFS_DEVICE/hpb_lu_max_active_regions" ] && \
   [ ! -f "$UFS_DEVICE/hpb_number_pinned_regions" ]; then
    print_warn "HPB 文件不存在 (设备可能不支持 HPB)"
fi
echo ""

# 5. 其他设备信息
print_header "5. 其他设备信息"
if [ -f "$UFS_DEVICE/logical_block_size" ]; then
    BLOCK_SIZE=$(cat "$UFS_DEVICE/logical_block_size" 2>/dev/null || echo "N/A")
    print_info "逻辑块大小：$BLOCK_SIZE 字节"
fi

if [ -f "$UFS_DEVICE/logical_block_count" ]; then
    BLOCK_COUNT=$(cat "$UFS_DEVICE/logical_block_count" 2>/dev/null || echo "N/A")
    print_info "逻辑块数量：$BLOCK_COUNT"
    if [ "$BLOCK_COUNT" != "N/A" ] && [ "$BLOCK_SIZE" != "N/A" ]; then
        CAPACITY=$((BLOCK_COUNT * BLOCK_SIZE))
        CAPACITY_GB=$((CAPACITY / 1024 / 1024 / 1024))
        print_info "设备容量：约 ${CAPACITY_GB}GB"
    fi
fi

if [ -f "$UFS_DEVICE/vendor" ]; then
    VENDOR=$(cat "$UFS_DEVICE/vendor" 2>/dev/null || echo "Unknown")
    print_info "厂商标识：$VENDOR"
fi

if [ -f "$UFS_DEVICE/type" ]; then
    DEV_TYPE=$(cat "$UFS_DEVICE/type" 2>/dev/null || echo "Unknown")
    print_info "设备类型：$DEV_TYPE"
fi
echo ""

# 6. 块设备信息
print_header "6. 关联块设备"
if [ -d "$UFS_DEVICE/block" ]; then
    BLOCK_DEV=$(ls "$UFS_DEVICE/block/" 2>/dev/null | head -1)
    if [ -n "$BLOCK_DEV" ]; then
        print_info "块设备：/dev/$BLOCK_DEV"
        
        BLOCK_PATH="$UFS_DEVICE/block/$BLOCK_DEV"
        
        if [ -f "$BLOCK_PATH/queue/write_cache" ]; then
            WC=$(cat "$BLOCK_PATH/queue/write_cache" 2>/dev/null || echo "Unknown")
            if [ "$WC" = "write through" ]; then
                print_info "写缓存：write through (较安全)"
            elif [ "$WC" = "write back" ]; then
                print_ok "写缓存：write back (性能优先)"
            else
                print_info "写缓存：$WC"
            fi
        fi
        
        if [ -f "$BLOCK_PATH/queue/rotational" ]; then
            ROT=$(cat "$BLOCK_PATH/queue/rotational" 2>/dev/null || echo "1")
            if [ "$ROT" = "0" ]; then
                print_ok "存储类型：非旋转 (SSD/UFS)"
            else
                print_info "存储类型：旋转 (HDD)"
            fi
        fi
        
        if [ -f "$BLOCK_PATH/size" ]; then
            SIZE_SECTORS=$(cat "$BLOCK_PATH/size" 2>/dev/null || echo "0")
            SIZE_GB=$((SIZE_SECTORS * 512 / 1024 / 1024 / 1024))
            print_info "块设备大小：约 ${SIZE_GB}GB"
        fi
    else
        print_warn "未找到关联的块设备"
    fi
else
    print_warn "block 目录不存在"
fi
echo ""

# 7. 综合评估
print_header "7. 综合评估"

WB_SCORE=0
WB_MAX=5

# WB 缓冲区评分
if [ -f "$UFS_DEVICE/wb_buf_alloc_units" ]; then
    WB_ALLOC=$(cat "$UFS_DEVICE/wb_buf_alloc_units" 2>/dev/null || echo "0")
    if [ "$WB_ALLOC" -gt 256 ] 2>/dev/null; then
        WB_SCORE=$((WB_SCORE + 2))
        print_ok "WB 缓冲区充足 (>256 单位)"
    elif [ "$WB_ALLOC" -gt 0 ] 2>/dev/null; then
        WB_SCORE=$((WB_SCORE + 1))
        print_info "WB 缓冲区已分配 (建议增加)"
    else
        print_warn "WB 缓冲区未分配"
    fi
fi

# LU 启用评分
if [ -f "$UFS_DEVICE/lu_enable" ]; then
    LU_EN=$(cat "$UFS_DEVICE/lu_enable" 2>/dev/null || echo "0")
    if [ "$LU_EN" -eq 1 ] 2>/dev/null; then
        WB_SCORE=$((WB_SCORE + 1))
    fi
fi

# 内存类型评分
if [ -f "$UFS_DEVICE/lu_memory_type" ]; then
    LU_MEM=$(cat "$UFS_DEVICE/lu_memory_type" 2>/dev/null || echo "0")
    if [ "$LU_MEM" -eq 2 ] 2>/dev/null; then
        WB_SCORE=$((WB_SCORE + 2))
        print_ok "使用 SLC/WB 内存类型"
    fi
fi

echo ""
echo "Write Booster 评分：$WB_SCORE / $WB_MAX"

if [ $WB_SCORE -ge 4 ]; then
    print_ok "Write Booster 配置良好!"
elif [ $WB_SCORE -ge 2 ]; then
    print_info "Write Booster 已启用，但可以优化"
else
    print_warn "Write Booster 未完全启用，建议检查配置"
fi

echo ""
print_header "检查完成"
echo ""
echo "详细文档：/workspace/projects/ufsauto/research/ufs_write_booster_guide.md"
echo ""
