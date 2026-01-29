#!/bin/bash
# 检查 Twitter 登录状态

STATE_FILE="$HOME/.twitter-monitor/twitter_auth.json"

echo "🔍 检查 Twitter 登录状态..."
echo ""

if [ ! -f "$STATE_FILE" ]; then
    echo "❌ 登录态文件不存在: $STATE_FILE"
    echo "💡 请运行: ./login.sh"
    exit 1
fi

echo "📄 登录态文件: $STATE_FILE"
echo "📊 文件大小: $(wc -c < "$STATE_FILE") bytes"
echo ""

# 检查关键 token
has_auth=0

if grep -q "auth_token" "$STATE_FILE"; then
    echo "✅ auth_token: 找到"
    has_auth=1
else
    echo "❌ auth_token: 未找到"
fi

if grep -q "ct0" "$STATE_FILE"; then
    echo "✅ ct0 (CSRF): 找到"
else
    echo "⚠️  ct0 (CSRF): 未找到"
fi

if grep -q "twid" "$STATE_FILE"; then
    echo "✅ twid (用户ID): 找到"
else
    echo "⚠️  twid (用户ID): 未找到"
fi

echo ""

if [ $has_auth -eq 1 ]; then
    echo "🎉 登录状态有效！可以运行监控脚本"
    echo "   运行: source .venv/bin/activate && python3 graph.py"
else
    echo "❌ 登录状态无效或未登录"
    echo "💡 请重新运行: ./login.sh"
    echo ""
    echo "⚠️  登录时注意："
    echo "   1. 完整输入用户名和密码"
    echo "   2. 完成所有验证步骤（邮箱/手机号）"
    echo "   3. 等待进入主页并看到推文"
    echo "   4. 页面完全加载后再按 Enter"
    exit 1
fi
