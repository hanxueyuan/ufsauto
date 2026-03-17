#!/bin/bash
#
# 硬件验证部署脚本
# 用于将 SysTest 部署到智驾板并运行测试
#

set -e

# 配置
ZHJIA_BOARD="${ZHJIA_BOARD:-root@zhijia-board}"
DEPLOY_PATH="${DEPLOY_PATH:-/opt/systest}"
LOCAL_PATH="$(cd "$(dirname "$0")/.." && pwd)"

echo "======================================"
echo "SysTest 硬件验证部署"
echo "======================================"
echo "目标设备：$ZHJIA_BOARD"
echo "部署路径：$DEPLOY_PATH"
echo "本地路径：$LOCAL_PATH"
echo ""

# 1. 检查连接
echo "📡 检查设备连接..."
if ! ping -c 1 -W 2 "$ZHJIA_BOARD" > /dev/null 2>&1; then
    echo "❌ 无法连接到智驾板，请检查网络连接"
    exit 1
fi
echo "✅ 设备连接正常"

# 2. 创建部署目录
echo "📁 创建部署目录..."
ssh "$ZHJIA_BOARD" "mkdir -p $DEPLOY_PATH"
echo "✅ 目录创建完成"

# 3. 同步文件
echo "📤 同步文件到设备..."
rsync -avz --progress \
    --exclude '.git/' \
    --exclude '__pycache__/' \
    --exclude '*.pyc' \
    --exclude '.pytest_cache/' \
    --exclude 'results/' \
    --exclude 'logs/' \
    "$LOCAL_PATH/systest/" \
    "$ZHJIA_BOARD:$DEPLOY_PATH/"

echo "✅ 文件同步完成"

# 4. 安装依赖
echo "📦 安装依赖..."
ssh "$ZHJIA_BOARD" "cd $DEPLOY_PATH && pip3 install -r requirements.txt"
echo "✅ 依赖安装完成"

# 5. 运行测试
echo "🧪 运行测试..."
read -p "要运行哪个测试用例？（留空运行全部）: " TEST_NAME

if [ -z "$TEST_NAME" ]; then
    ssh "$ZHJIA_BOARD" "cd $DEPLOY_PATH && python3 -m pytest tests/ -v"
else
    ssh "$ZHJIA_BOARD" "cd $DEPLOY_PATH && python3 tests/$TEST_NAME -v"
fi

echo "✅ 测试运行完成"

# 6. 收集结果
echo "📥 收集测试结果..."
RESULTS_DIR="./hardware_results/$(date +%Y%m%d_%H%M%S)"
mkdir -p "$RESULTS_DIR"

scp -r "$ZHJIA_BOARD:$DEPLOY_PATH/results/" "$RESULTS_DIR/"
scp -r "$ZHJIA_BOARD:$DEPLOY_PATH/logs/" "$RESULTS_DIR/"

echo "✅ 结果已保存到：$RESULTS_DIR"

# 7. 生成报告
echo "📊 生成验证报告..."
cat > "$RESULTS_DIR/report.txt" << EOF
SysTest 硬件验证报告
====================
时间：$(date)
设备：$ZHJIA_BOARD
部署路径：$DEPLOY_PATH
测试结果：$RESULTS_DIR/results/
日志：$RESULTS_DIR/logs/
EOF

echo "✅ 报告已生成：$RESULTS_DIR/report.txt"

echo ""
echo "======================================"
echo "硬件验证完成！"
echo "======================================"
echo "查看结果：cd $RESULTS_DIR && cat results/*.json"
echo "查看日志：cd $RESULTS_DIR && cat logs/*.log"
