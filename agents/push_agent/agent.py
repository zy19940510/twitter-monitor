"""
Push Agent - 推送代理
负责将分析结果推送到 Telegram
"""

import os
from typing import Dict, Any, Optional
from datetime import datetime

import requests

from agents.base import BaseAgent


class PushAgent(BaseAgent):
    """
    推送代理
    职责：将分析结果推送到 Telegram
    """

    def __init__(
        self,
        bot_token: str = None,
        chat_id: str = None,
    ):
        """
        初始化 Push Agent

        Args:
            bot_token: Telegram Bot Token
            chat_id: Telegram Chat ID
        """
        super().__init__(name="PushAgent")

        self.bot_token = bot_token or os.getenv("TELEGRAM_BOT_TOKEN")
        self.chat_id = chat_id or os.getenv("TELEGRAM_CHAT_ID")

        if not self.bot_token or not self.chat_id:
            self._log("Telegram 配置不完整", "warning")
        else:
            self._log("Telegram 配置已加载", "success")

        self.is_initialized = True

    def execute(
        self,
        summary: str,
        tweet_count: int = 0,
        provider: str = "unknown",
        model: str = "unknown",
        tweets: list = None,
    ) -> Dict[str, Any]:
        """
        推送分析结果到 Telegram

        Args:
            summary: 分析摘要
            tweet_count: 推文数量
            provider: LLM 提供方
            model: 使用的模型
            tweets: 原始推文列表

        Returns:
            推送结果
        """
        if not self.bot_token or not self.chat_id:
            return self._error("Telegram 配置不完整")

        if not summary:
            return self._error("没有内容需要推送")

        self._log("准备推送到 Telegram")

        # 格式化消息
        message = self._format_message(summary, tweet_count, provider, model, tweets or [])

        # 发送消息
        success = self._send_message(message)

        if success:
            self._log("推送成功", "success")
            return self._success(
                data={"message_length": len(message)}, message="成功推送到 Telegram"
            )
        else:
            return self._error("推送失败")

    def _format_message(
        self,
        summary: str,
        tweet_count: int,
        provider: str,
        model: str,
        tweets: list,
    ) -> str:
        """格式化 Telegram 消息 - 使用 HTML 格式"""
        now = datetime.now().strftime("%Y-%m-%d %H:%M")

        # 将 Markdown 摘要转换为 HTML
        summary_html = self._markdown_to_html(summary)

        # 构建推文列表（按时间从新到旧）
        tweets_section = self._format_tweets_list(tweets)

        return f"""📱 <b>Twitter/X 热点速递</b>

🕐 {now} | 📊 {tweet_count} 条新推文 | 🤖 {provider}/{model}

━━━━━━━━━━━━━━━━

📝 <b>推文详情</b> (按时间排序)

{tweets_section}

━━━━━━━━━━━━━━━━

🤖 <b>AI 分析摘要</b>

{summary_html}

━━━━━━━━━━━━━━━━
<i>由 Twitter Monitor 自动生成</i>"""

    def _format_tweets_list(self, tweets: list) -> str:
        """格式化推文列表 - HTML 格式"""
        if not tweets:
            return "<i>无新推文</i>"

        max_display = int(os.getenv("MAX_TWEETS_TO_DISPLAY", "10"))
        lines = []
        for i, tweet in enumerate(tweets[:max_display], 1):  # 从环境变量读取
            author = tweet.get("author", "unknown")
            time = tweet.get("time", "unknown")
            content = tweet.get("content", "")
            engagement = tweet.get("engagement", {})
            url = tweet.get("url", f"https://x.com/{author}")

            # 截取内容（避免太长）
            content_preview = content[:150] + "..." if len(content) > 150 else content
            # HTML 转义
            content_html = self._escape_html(content_preview)

            # 互动数据
            likes = engagement.get("likes", 0)
            views = engagement.get("views", 0)

            # HTML 超链接格式：<a href="url">text</a>
            tweet_line = f"""<b>{i}. <a href="{url}">@{author}</a></b> ({time})
{content_html}
👍 {likes} | 👁 {self._format_number(views)}

"""
            lines.append(tweet_line)

        return "".join(lines)

    def _escape_html(self, text: str) -> str:
        """转义 HTML 特殊字符"""
        # 替换图片标记
        text = text.replace("Image Image", "📷")
        text = text.replace("Image", "📷")

        # HTML 只需要转义这三个字符
        text = text.replace("&", "&amp;")
        text = text.replace("<", "&lt;")
        text = text.replace(">", "&gt;")

        return text

    def _markdown_to_html(self, markdown_text: str) -> str:
        """将 Markdown 转换为 HTML（简化版，适配 LLM 输出格式）"""
        import re

        html = markdown_text

        # 先转义 HTML 特殊字符
        html = self._escape_html(html)

        # 1. 标题：## 标题 → <b>标题</b>
        html = re.sub(r'^### (.+)$', r'<b>\1</b>', html, flags=re.MULTILINE)
        html = re.sub(r'^## (.+)$', r'<b>\1</b>', html, flags=re.MULTILINE)
        html = re.sub(r'^# (.+)$', r'<b>\1</b>', html, flags=re.MULTILINE)

        # 2. 粗体：**文本** 或 __文本__ → <b>文本</b>
        html = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', html)
        html = re.sub(r'__(.+?)__', r'<b>\1</b>', html)

        # 3. 斜体：*文本* 或 _文本_ → <i>文本</i>
        html = re.sub(r'\*(.+?)\*', r'<i>\1</i>', html)
        html = re.sub(r'_(.+?)_', r'<i>\1</i>', html)

        # 4. 代码：`代码` → <code>代码</code>
        html = re.sub(r'`(.+?)`', r'<code>\1</code>', html)

        # 5. 列表项：- 项目 → • 项目
        html = re.sub(r'^\s*[-*]\s+(.+)$', r'  • \1', html, flags=re.MULTILINE)

        # 6. 有序列表：1. 项目 → 1. 项目 (保持原样)
        # Telegram 会自动识别

        # 7. 链接：[文本](url) → <a href="url">文本</a>
        html = re.sub(r'\[(.+?)\]\((.+?)\)', r'<a href="\2">\1</a>', html)

        # 8. 清理多余的空行（保留最多1个空行）
        html = re.sub(r'\n{3,}', '\n\n', html)

        return html

    def _format_number(self, num: int) -> str:
        """格式化数字（K/M）"""
        if num >= 1000000:
            return f"{num/1000000:.1f}M"
        elif num >= 1000:
            return f"{num/1000:.1f}K"
        return str(num)

    def _send_message(
        self,
        message: str,
        parse_mode: str = "HTML",
    ) -> bool:
        """发送 Telegram 消息"""
        url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"

        # Telegram 消息长度限制 4096 字符
        if len(message) > 4000:
            message = message[:4000] + "\n\n<i>(内容已截断)</i>"

        try:
            response = requests.post(
                url,
                json={
                    "chat_id": self.chat_id,
                    "text": message,
                    "parse_mode": parse_mode,
                    "disable_web_page_preview": True,
                },
                timeout=30,
            )

            if response.status_code != 200:
                self._log(f"Telegram API 错误: {response.text}", "error")
                return False
            return True
        except Exception as e:
            self._log(f"发送消息失败: {e}", "error")
            return False
