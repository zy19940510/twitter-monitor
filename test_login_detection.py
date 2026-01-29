#!/usr/bin/env python3
"""测试登录状态检测逻辑"""

import json
from agents.fetch_agent import FetchAgent


def test_login_detection():
    """测试登录检测"""
    print("🧪 测试登录状态检测\n")
    print("=" * 60)

    agent = FetchAgent()

    # 测试 1: 检查登录态文件
    print("\n[测试 1] 检查登录态文件")
    if agent.state_file.exists():
        size = agent.state_file.stat().st_size
        print(f"✅ 登录态文件存在: {agent.state_file}")
        print(f"   文件大小: {size:,} bytes")

        # 检查关键 token
        with open(agent.state_file) as f:
            content = f.read()
            has_auth = "auth_token" in content
            has_ct0 = "ct0" in content

        print(f"   auth_token: {'✅' if has_auth else '❌'}")
        print(f"   ct0: {'✅' if has_ct0 else '❌'}")

        if not has_auth:
            print("\n⚠️  警告: 登录态文件缺少 auth_token，需要重新登录")
            print("   运行: ./login.sh")
            return False
    else:
        print(f"❌ 登录态文件不存在: {agent.state_file}")
        print("   运行: ./login.sh")
        return False

    # 测试 2: 尝试访问 Twitter 并验证登录状态
    print("\n[测试 2] 访问 Twitter 并验证登录状态")
    print("正在打开页面...")

    try:
        result = agent.execute("https://x.com/home")

        if result["status"] == "success":
            tweet_count = len(result["data"]["tweets"])
            print(f"\n✅ 登录验证成功！")
            print(f"📊 抓取到 {tweet_count} 条推文")

            if tweet_count > 0:
                print(f"\n📝 前 3 条推文预览:")
                for i, tweet in enumerate(result["data"]["tweets"][:3], 1):
                    author = tweet.get("author", "unknown")
                    content = tweet.get("content", "")[:80]
                    print(f"   {i}. @{author}: {content}...")
            else:
                print("\n⚠️  未抓取到推文，可能原因:")
                print("   - 页面还在加载")
                print("   - For You 时间线为空")
                print("   - 需要增加 scroll_count")

            return True
        else:
            error = result.get("error", "未知错误")
            print(f"\n❌ 登录验证失败")
            print(f"\n错误信息:\n{error}")
            return False

    except Exception as e:
        print(f"\n❌ 测试异常: {e}")
        import traceback

        traceback.print_exc()
        return False


def main():
    success = test_login_detection()

    print("\n" + "=" * 60)
    if success:
        print("\n🎉 所有测试通过！系统已就绪")
        print("   可以运行: python3 graph.py")
    else:
        print("\n❌ 测试失败，请按照上述提示修复")
        print("\n常见问题:")
        print("   1. 未登录 → 运行 ./login.sh")
        print("   2. 登录过期 → 重新运行 ./login.sh")
        print("   3. 网络问题 → 检查网络连接")


if __name__ == "__main__":
    main()
