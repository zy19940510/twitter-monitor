#!/bin/bash
set -e

# 从 .env 文件加载配置
if [ -f .env ]; then
    export $(grep -v '^#' .env | xargs)
fi

# 使用环境变量，如果未设置则使用默认值
STATE_DIR="${DATA_DIR:-$HOME/.twitter-monitor}"
STATE_DIR=$(eval echo "$STATE_DIR")  # 展开路径中的 ~ 符号
STATE_FILE="$STATE_DIR/twitter_auth.json"
CDP_PORT="${CDP_PORT:-9222}"
CHROME_PATH="${CHROME_PATH:-/Applications/Google Chrome.app/Contents/MacOS/Google Chrome}"
USER_DATA_DIR="${CHROME_USER_DATA_DIR:-$HOME/.chrome-debug-profile}"
USER_DATA_DIR=$(eval echo "$USER_DATA_DIR")  # 展开路径中的 ~ 符号

mkdir -p "$STATE_DIR"

echo "🚀 启动 Chrome Debug 模式..."
echo ""

# 检查 Chrome 是否已经在运行
if curl -s http://localhost:$CDP_PORT/json/version > /dev/null 2>&1; then
    echo "✅ Chrome Debug 已在运行 (端口 $CDP_PORT)"
    echo ""
    echo "⚠️  如果需要重新启动 Chrome:"
    echo "   1. 关闭当前的 Chrome 窗口"
    echo "   2. 重新运行此脚本"
else
    echo "📱 启动 Chrome with CDP..."

    # 启动 Chrome
    "$CHROME_PATH" \
        --remote-debugging-port=$CDP_PORT \
        --user-data-dir="$USER_DATA_DIR" \
        > /dev/null 2>&1 &

    # 等待 Chrome 启动
    sleep 3

    # 验证启动成功
    if curl -s http://localhost:$CDP_PORT/json/version > /dev/null 2>&1; then
        echo "✅ Chrome 启动成功"
    else
        echo "❌ Chrome 启动失败"
        exit 1
    fi
fi

echo ""
echo "⚠️  请在浏览器中："
echo "   1. 访问 https://x.com/home"
echo "   2. 如果未登录，请登录 Twitter"
echo "   3. 等待进入主页并看到推文流"
echo "   4. 确认页面完全加载完成"
echo ""
read -p "✋ 确认已登录并看到主页了吗？按 Enter 保存状态..."

echo ""
echo "💾 正在保存登录态..."

# 使用 CDP 模式保存状态
agent-browser --cdp $CDP_PORT state save "$STATE_FILE"

echo ""
echo "🔍 验证登录状态..."

# 验证关键 token
if grep -q "auth_token" "$STATE_FILE"; then
    echo "✅ 登录成功！找到 auth_token"

    # 显示统计
    cookie_count=$(grep -o '"name":' "$STATE_FILE" | wc -l | tr -d ' ')
    file_size=$(wc -c < "$STATE_FILE")

    echo "✅ 登录状态已保存到: $STATE_FILE"
    echo "   - Cookies 数量: $cookie_count"
    echo "   - 文件大小: $file_size bytes"
    echo ""

    # 关闭 Chrome
    echo "🔒 关闭浏览器..."
    pkill -f "remote-debugging-port=$CDP_PORT" || true
    sleep 1

    echo "✅ 登录态已保存，浏览器已关闭"
    echo ""
    echo "💡 运行 graph.py 时会自动重启 Chrome 并加载登录态"
    echo "现在可以运行 python3 graph.py 测试抓取功能"
else
    echo "❌ 登录失败！未找到 auth_token"
    echo "⚠️  可能原因："
    echo "   - 浏览器中没有登录 Twitter"
    echo "   - 没有访问 https://x.com/home"
    echo "   - 登录后页面没有完全加载"
    echo ""
    echo "💡 请在浏览器中登录后重新运行 ./login.sh"
    exit 1
fi
