#!/bin/bash
# UFS 3.1 编译脚本

set -e

# 默认配置
BUILD_TYPE="Release"
CLEAN_BUILD=false
JOBS=$(nproc)
OUTPUT_DIR="output"

# 帮助信息
usage() {
    echo "Usage: $0 [OPTIONS]"
    echo "Options:"
    echo "  -t, --type TYPE        Build type (Debug/Release, default: Release)"
    echo "  -c, --clean            Clean build directory before building"
    echo "  -j, --jobs NUM         Number of parallel jobs (default: $JOBS)"
    echo "  -o, --output DIR       Output directory (default: $OUTPUT_DIR)"
    echo "  -h, --help             Show this help message"
    exit 1
}

# 解析参数
while [[ $# -gt 0 ]]; do
    case "$1" in
        -t|--type)
            BUILD_TYPE="$2"
            shift 2
            ;;
        -c|--clean)
            CLEAN_BUILD=true
            shift
            ;;
        -j|--jobs)
            JOBS="$2"
            shift 2
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

# 验证构建类型
if [[ "$BUILD_TYPE" != "Debug" && "$BUILD_TYPE" != "Release" ]]; then
    echo "Error: Invalid build type $BUILD_TYPE. Must be Debug or Release."
    exit 1
fi

echo "========================================"
echo "Starting UFS 3.1 build"
echo "Build type: $BUILD_TYPE"
echo "Parallel jobs: $JOBS"
echo "Clean build: $CLEAN_BUILD"
echo "========================================"

# 构建目录
BUILD_DIR="build/$BUILD_TYPE"

# 清理构建目录
if [ "$CLEAN_BUILD" = true ]; then
    echo "Cleaning build directory..."
    rm -rf "$BUILD_DIR"
fi

# 创建构建目录
mkdir -p "$BUILD_DIR"
cd "$BUILD_DIR"

# 配置 CMake
echo "Configuring CMake..."
cmake ../.. \
    -DCMAKE_BUILD_TYPE="$BUILD_TYPE" \
    -DCMAKE_C_COMPILER=aarch64-linux-gnu-gcc \
    -DCMAKE_CXX_COMPILER=aarch64-linux-gnu-g++ \
    -DBUILD_TESTS=ON \
    -DBUILD_EXAMPLES=ON \
    -DCMAKE_INSTALL_PREFIX="$OUTPUT_DIR"

# 编译
echo "Building project..."
make -j"$JOBS"

# 安装
echo "Installing to output directory..."
make install

# 显示构建结果
echo "========================================"
echo "Build completed successfully!"
echo "Output directory: $OUTPUT_DIR"
echo "Binaries: $OUTPUT_DIR/bin/"
echo "Libraries: $OUTPUT_DIR/lib/"
echo "========================================"

# 显示 ccache 统计
echo "ccache statistics:"
ccache -s

# 验证二进制架构
echo "Binary architecture verification:"
file "$OUTPUT_DIR/bin/ufs31-*" | head -5
