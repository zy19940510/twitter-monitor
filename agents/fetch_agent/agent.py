"""
Fetch Agent - 推文抓取代理
负责使用 agent-browser 抓取 Twitter For You 时间线
"""

import json
import os
import re
import subprocess
from pathlib import Path
from typing import Dict, Any, List

from agents.base import BaseAgent


class FetchAgent(BaseAgent):
    """抓取代理 - 使用 agent-browser 通过 CDP 抓取 Twitter 推文"""

    def __init__(
        self,
        session: str = None,
        data_dir: str = None,
        scroll_count: int = 3,
        cdp_port: int = None,
    ):
        super().__init__(name="FetchAgent")

        self.session = session or os.getenv("BROWSER_SESSION", "twitter")
        self.data_dir = Path(
            os.path.expanduser(data_dir or os.getenv("DATA_DIR", "~/.twitter-monitor"))
        )
        self.scroll_count = scroll_count
        self.cdp_port = cdp_port or int(os.getenv("CDP_PORT", "9222"))
        self.state_file = self.data_dir / "twitter_auth.json"

        self._log(f"CDP Port: {self.cdp_port}", "info")
        self.is_initialized = True

    def execute(self, url: str = "https://x.com/home") -> Dict[str, Any]:
        self._log(f"开始抓取: {url}")

        # 检查 CDP 是否在运行，如果没有则启动
        import urllib.request
        chrome_was_running = False

        try:
            urllib.request.urlopen(f"http://localhost:{self.cdp_port}/json/version", timeout=2)
            self._log("CDP 浏览器已在运行", "info")
            chrome_was_running = True
        except Exception:
            self._log("CDP 浏览器未运行，正在启动...", "info")
            # 启动 Chrome
            chrome_path = os.getenv(
                "CHROME_PATH",
                "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
            )
            user_data_dir = os.path.expanduser(
                os.getenv("CHROME_USER_DATA_DIR", "~/.chrome-debug-profile")
            )

            import subprocess
            subprocess.Popen(
                [chrome_path, f"--remote-debugging-port={self.cdp_port}", f"--user-data-dir={user_data_dir}"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )

            # 等待启动
            import time
            time.sleep(3)

            # 验证启动成功
            try:
                urllib.request.urlopen(f"http://localhost:{self.cdp_port}/json/version", timeout=2)
                self._log("Chrome 启动成功", "success")
            except Exception:
                return self._error(f"Chrome 启动失败，请手动运行: ./login.sh")

        # 检查是否已有活跃的页面访问 Twitter
        try:
            response = urllib.request.urlopen(f"http://localhost:{self.cdp_port}/json", timeout=2)
            import json
            pages = json.loads(response.read())

            # 查找是否已经打开了 Twitter 页面
            twitter_page_found = False
            for page in pages:
                if page.get("type") == "page" and "x.com" in page.get("url", ""):
                    twitter_page_found = True
                    self._log(f"发现已打开的 Twitter 页面: {page.get('url')}", "info")
                    break

            if not twitter_page_found:
                success, output = self._run_browser("open", url)
                if not success:
                    return self._error(f"打开页面失败: {output}")
                self._log("打开新 Twitter 页面", "info")
            else:
                # 刷新页面确保是最新的
                success, output = self._run_browser("reload")
                if not success:
                    self._log(f"刷新页面失败，尝试重新打开: {output}", "warning")
                    success, output = self._run_browser("open", url)
                    if not success:
                        return self._error(f"打开页面失败: {output}")
                else:
                    self._log("复用已有页面并刷新", "success")

        except Exception as e:
            self._log(f"检查页面失败，尝试打开新页面: {e}", "warning")
            success, output = self._run_browser("open", url)
            if not success:
                return self._error(f"打开页面失败: {output}")

        self._run_browser("wait", "--load", "networkidle")

        # 验证是否成功登录
        self._log("验证登录状态...", "info")
        is_logged_in, login_error = self._verify_login()
        if not is_logged_in:
            return self._error(login_error)

        # 多次滚动，每次滚动后收集推文（避免丢失）
        all_tweets = {}  # 使用 dict 去重，key 是 (author, content_hash)
        self._log(f"开始滚动加载推文 ({self.scroll_count} 次)...", "info")

        for scroll_num in range(self.scroll_count):
            # 获取当前快照
            success, output = self._run_browser("snapshot", "--json")
            if success:
                try:
                    snapshot = json.loads(output)
                    tweets = self._extract_tweets(snapshot)

                    # 合并到总列表（按 author + content 前50字符去重）
                    for tweet in tweets:
                        # 使用 author + content 的前50个字符作为唯一标识
                        # 避免同一个作者的不同推文被误判为重复
                        content_preview = tweet["content"][:50]
                        tweet_key = f"{tweet['author']}_{content_preview}"

                        if tweet_key not in all_tweets:
                            all_tweets[tweet_key] = tweet

                    self._log(
                        f"第 {scroll_num + 1}/{self.scroll_count} 次: "
                        f"当前批次 {len(tweets)} 条, 累计 {len(all_tweets)} 条",
                        "info"
                    )
                except json.JSONDecodeError as e:
                    self._log(f"解析快照失败: {e}", "warning")

            # 继续滚动（最后一次不需要滚动）
            if scroll_num < self.scroll_count - 1:
                # 使用 JavaScript 精确滚动到最后一个推文
                success = self._scroll_to_next_batch()

                if not success:
                    # 如果 JS 滚动失败，回退到像素滚动
                    self._run_browser("scroll", "down", "1200")

                self._run_browser("wait", "2000")
                if scroll_num % 2 == 0:
                    self._run_browser("wait", "1000")

        # 转换为列表并按时间排序
        final_tweets = list(all_tweets.values())
        final_tweets.sort(key=lambda t: t.get("timestamp", 0), reverse=True)

        self._log(f"✓ 总计提取到 {len(final_tweets)} 条推文", "success")

        return self._success(
            data={"tweets": final_tweets, "count": len(final_tweets)},
            message=f"成功抓取 {len(final_tweets)} 条推文",
        )

    def _verify_login(self) -> tuple[bool, str]:
        """
        验证是否已成功登录 Twitter

        Returns:
            (is_logged_in, error_message)
        """
        # 获取当前页面快照
        success, output = self._run_browser("snapshot", "--json")
        if not success:
            return False, f"无法获取页面快照: {output}"

        try:
            snapshot = json.loads(output)
        except json.JSONDecodeError as e:
            return False, f"快照解析失败: {e}"

        # 检查快照内容
        snapshot_text = snapshot.get("data", {}).get("snapshot", "")
        refs = snapshot.get("data", {}).get("refs", {})

        # 登录失败的特征
        login_indicators = [
            "Sign in to X",
            "Sign in to Twitter",
            "Log in",
            "Phone, email, or username",
            "Don't have an account?",
        ]

        # 检查是否有登录提示
        for indicator in login_indicators:
            if indicator in snapshot_text or any(
                indicator in ref.get("name", "") for ref in refs.values()
            ):
                self._log("检测到登录页面", "error")

                # 保存调试快照
                debug_file = self.data_dir / "debug_login_failed.json"
                try:
                    with open(debug_file, "w") as f:
                        json.dump(snapshot, f, indent=2, ensure_ascii=False)
                    self._log(f"调试快照已保存: {debug_file}", "info")
                except Exception as e:
                    self._log(f"保存调试快照失败: {e}", "warning")

                return False, (
                    "未登录或登录已失效！\n"
                    "解决方案:\n"
                    "1. 运行 ./login.sh 重新登录\n"
                    "2. 确保完成所有登录验证步骤\n"
                    "3. 等待进入主页看到推文流后再保存状态\n"
                    "4. 运行 ./check_login.sh 验证登录状态"
                )

        # 检查是否有推文流相关元素（登录成功的特征）
        logged_in_indicators = [
            "Home",
            "Timeline",
            "What's happening",
            "For you",
            "Following",
        ]

        has_logged_in_indicator = False
        for indicator in logged_in_indicators:
            if indicator in snapshot_text or any(
                indicator.lower() in ref.get("name", "").lower() for ref in refs.values()
            ):
                has_logged_in_indicator = True
                break

        if not has_logged_in_indicator:
            self._log("页面异常：未检测到登录页面，也未检测到主页元素", "error")

            # 保存调试快照
            debug_file = self.data_dir / "debug_page_abnormal.json"
            try:
                with open(debug_file, "w") as f:
                    json.dump(snapshot, f, indent=2, ensure_ascii=False)
                self._log(f"调试快照已保存: {debug_file}", "info")
            except Exception as e:
                self._log(f"保存调试快照失败: {e}", "warning")

            return False, (
                "页面状态异常！\n"
                "可能的原因:\n"
                "1. 页面加载不完整，请稍后重试\n"
                "2. Twitter 页面结构发生变化\n"
                "3. 网络连接问题导致页面内容未加载\n"
                "4. 浏览器被重定向到其他页面\n"
                f"调试信息已保存至: {debug_file}"
            )
        else:
            self._log("✓ 登录状态验证通过", "success")

        return True, ""

    def _run_browser(self, *args) -> tuple[bool, str]:
        """Run agent-browser command using CDP mode to connect to existing Chrome"""
        cmd = ["agent-browser", "--cdp", str(self.cdp_port), *args]
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            return result.returncode == 0, result.stdout + result.stderr
        except subprocess.TimeoutExpired:
            return False, "Command timed out"
        except Exception as e:
            return False, str(e)

    def _scroll_to_next_batch(self) -> bool:
        """使用 JavaScript 精确滚动 - 每次滚动1条推文的高度"""
        # 使用 IIFE 而非箭头函数，因为 agent-browser eval 不支持箭头函数
        js_code = """
        (function() {
            const articles = Array.from(document.querySelectorAll('article'));
            const viewportHeight = window.innerHeight;

            if (articles.length === 0) {
                return { success: false, count: 0 };
            }

            // 找到当前视口内可见的所有 article
            const visibleArticles = articles.filter(article => {
                const rect = article.getBoundingClientRect();
                // article 的顶部在视口内
                return rect.top >= 0 && rect.top < viewportHeight;
            });

            if (visibleArticles.length === 0) {
                // 视口内没有article顶部，滚动固定距离
                window.scrollBy({ top: 400, behavior: 'auto' });
                return { success: true, count: articles.length, scrollAmount: 400 };
            }

            // 找到视口内第一个可见的推文（顶部在视口内）
            const firstVisibleArticle = visibleArticles[0];
            const firstRect = firstVisibleArticle.getBoundingClientRect();

            // 策略：滚动距离 = 第一条可见推文的高度
            // 这样正好让第一条推文滚出视口，第二条变成新的第一条
            const scrollAmount = firstRect.height;

            window.scrollBy({
                top: scrollAmount,
                behavior: 'auto'
            });

            return {
                success: true,
                count: articles.length,
                visibleCount: visibleArticles.length,
                scrollAmount: Math.round(scrollAmount)
            };
        })()
        """

        success, output = self._run_browser("eval", "--json", js_code)

        if success:
            try:
                import json
                result = json.loads(output)
                return result.get("data", {}).get("result", {}).get("success", False)
            except Exception:
                return False
        return False

    def _extract_tweets(self, snapshot: dict) -> List[Dict[str, Any]]:
        tweets = []
        skipped_reasons = {
            "too_short": 0,
            "carousel": 0,
            "video": 0,
            "no_author": 0,
        }

        # agent-browser --json 返回 {"success": true, "data": {"refs": {...}}}
        refs = snapshot.get("data", {}).get("refs", {})
        snapshot_text = snapshot.get("data", {}).get("snapshot", "")

        for ref_id, ref_data in refs.items():
            if ref_data.get("role") == "article":
                name = ref_data.get("name", "")

                # 降低长度要求，只要有内容就尝试提取
                if not name or len(name) < 20:
                    skipped_reasons["too_short"] += 1
                    continue

                # 过滤 Carousel（轮播推荐/广告区）
                if "carousel" in name.lower():
                    skipped_reasons["carousel"] += 1
                    continue

                # 从 name 中提取作者 (@username)
                author_match = re.search(r"@(\w+)", name)
                if not author_match:
                    skipped_reasons["no_author"] += 1
                    continue

                author = author_match.group(1)

                # 提取时间信息
                time_str = self._extract_time(name)
                timestamp = self._parse_time_to_timestamp(time_str)

                # 提取互动数据 (replies, reposts, likes, views)
                engagement = self._extract_engagement(name)

                # 提取推文 URL
                tweet_url = self._extract_tweet_url(author, snapshot_text, ref_id)

                # 从 name 中提取 tweet ID (从 URL 模式)
                tweet_id = ref_id  # 使用 ref_id 作为 fallback

                # 提取实际内容（去除元数据）
                content = self._extract_content(name, author, time_str)

                tweets.append(
                    {
                        "id": tweet_id,
                        "content": content,
                        "author": author,
                        "time": time_str,
                        "timestamp": timestamp,
                        "engagement": engagement,
                        "url": tweet_url,
                    }
                )

        # 按时间戳排序（最新的在前面）
        tweets.sort(key=lambda t: t.get("timestamp", 0), reverse=True)

        # 输出统计信息
        self._log(
            f"提取统计: 共 {len(tweets)} 条推文, "
            f"跳过: 太短({skipped_reasons['too_short']}), "
            f"Carousel({skipped_reasons['carousel']}), "
            f"视频({skipped_reasons['video']}), "
            f"无作者({skipped_reasons['no_author']})",
            "info"
        )

        return tweets

    def _extract_tweet_url(self, author: str, snapshot_text: str, ref_id: str) -> str:
        """从 snapshot 中提取推文 URL"""
        # 在 snapshot 文本中查找该作者的 status URL
        # 格式类似: /url: /author/status/1234567890
        pattern = rf"/url: /{author}/status/(\d+)"
        match = re.search(pattern, snapshot_text)

        if match:
            status_id = match.group(1)
            return f"https://x.com/{author}/status/{status_id}"

        # 如果找不到，返回作者主页
        return f"https://x.com/{author}"

    def _extract_time(self, name: str) -> str:
        """从 name 中提取时间信息"""
        # 匹配 "4 hours ago", "Jan 28", "15h" 等格式
        time_patterns = [
            r"(\d+)\s+hours?\s+ago",
            r"(\d+)h\b",
            r"(\d+)\s+minutes?\s+ago",
            r"(\d+)m\b",
            r"(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d+",
        ]
        for pattern in time_patterns:
            match = re.search(pattern, name)
            if match:
                return match.group(0)
        return "unknown"

    def _parse_time_to_timestamp(self, time_str: str) -> int:
        """将时间字符串转换为时间戳（用于排序）"""
        import time as time_module
        from datetime import datetime, timedelta

        now = datetime.now()

        # 小时前
        match = re.match(r"(\d+)\s*h", time_str)
        if match:
            hours = int(match.group(1))
            return int((now - timedelta(hours=hours)).timestamp())

        # "X hours ago"
        match = re.match(r"(\d+)\s+hours?\s+ago", time_str)
        if match:
            hours = int(match.group(1))
            return int((now - timedelta(hours=hours)).timestamp())

        # 分钟前
        match = re.match(r"(\d+)\s*m", time_str)
        if match:
            minutes = int(match.group(1))
            return int((now - timedelta(minutes=minutes)).timestamp())

        # 日期格式 "Jan 28"
        if "Jan" in time_str or "Feb" in time_str or "Dec" in time_str:
            # 粗略估计：假设是昨天或前天
            return int((now - timedelta(days=1)).timestamp())

        # 默认返回0（最旧）
        return 0

    def _extract_engagement(self, name: str) -> dict:
        """提取互动数据"""
        engagement = {
            "replies": 0,
            "reposts": 0,
            "likes": 0,
            "views": 0,
        }

        # 匹配 "63 replies, 12 reposts, 1058 likes, 313816 views"
        replies_match = re.search(r"(\d+)\s+repl(?:y|ies)", name)
        reposts_match = re.search(r"(\d+)\s+repost", name)
        likes_match = re.search(r"(\d+)\s+like", name)
        views_match = re.search(r"(\d+)\s+views", name)

        if replies_match:
            engagement["replies"] = int(replies_match.group(1))
        if reposts_match:
            engagement["reposts"] = int(reposts_match.group(1))
        if likes_match:
            engagement["likes"] = int(likes_match.group(1))
        if views_match:
            engagement["views"] = int(views_match.group(1))

        return engagement

    def _extract_content(self, name: str, author: str, time_str: str) -> str:
        """提取推文实际内容，去除作者名和时间等元数据"""
        # 去除开头的 "作者名 Verified account @username 时间"
        content = name

        # 移除 Verified account
        content = re.sub(r"Verified account", "", content)

        # 移除作者名（假设在开头）
        content = re.sub(r"^[^@]+@\w+\s+", "", content)

        # 移除时间
        content = content.replace(time_str, "")

        # 移除 "Embedded video" 和播放控制文本
        content = re.sub(r"Embedded video\s*", "", content)
        content = re.sub(r"Play Video\s*", "", content)
        content = re.sub(r"Play\s+Embed\s*", "", content)

        # 移除尾部的互动数据
        content = re.sub(r"\d+\s+repl(?:y|ies).*$", "", content)

        # 清理多余空格
        content = " ".join(content.split())

        return content[:500]
