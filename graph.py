"""
Twitter Monitor - LangGraph 工作流
使用 StateGraph 串联 Fetch → Filter → Analyse → Push
"""

import os
import sys
import sqlite3
from pathlib import Path
from typing import List, Dict, Any, Optional, Annotated
from datetime import datetime
from typing_extensions import TypedDict
from dotenv import load_dotenv

from langgraph.graph import StateGraph, START, END

from agents.fetch_agent import FetchAgent
from agents.analyse_agent import AnalyseAgent
from agents.push_agent import PushAgent


load_dotenv(Path(__file__).parent / ".env")


class MonitorState(TypedDict):
    """工作流状态"""

    tweets: List[Dict[str, Any]]
    new_tweets: List[Dict[str, Any]]
    summary: str
    provider: str
    model: str
    tweet_count: int
    error: Optional[str]
    status: str


class TwitterMonitorGraph:
    """基于 LangGraph 的 Twitter 监控工作流"""

    def __init__(self):
        self.config = self._load_config()
        self.db_conn: Optional[sqlite3.Connection] = None

        self.fetch_agent = FetchAgent(
            session=self.config["browser_session"],
            data_dir=str(self.config["data_dir"]),
            scroll_count=self.config["scroll_count"],
        )
        self.analyse_agent = AnalyseAgent(provider=self.config["llm_provider"])
        self.push_agent = PushAgent()

        self._init_db()
        self.graph = self._build_graph()

        self._print_banner()

    def _load_config(self) -> Dict[str, Any]:
        return {
            "data_dir": Path(
                os.path.expanduser(os.getenv("DATA_DIR", "~/.twitter-monitor"))
            ),
            "browser_session": os.getenv("BROWSER_SESSION", "twitter"),
            "scroll_count": int(os.getenv("SCROLL_COUNT", "3")),
            "llm_provider": os.getenv("LLM_PROVIDER", "local"),
        }

    def _print_banner(self):
        print("\n" + "=" * 60)
        print("📱 Twitter/X 智能监控系统")
        print("=" * 60)
        print("架构模式: LangGraph StateGraph")
        print(f"LLM Provider: {self.config['llm_provider']}")
        print("=" * 60 + "\n")

    def _init_db(self):
        db_path = self.config["data_dir"] / "twitter_monitor.db"
        db_path.parent.mkdir(parents=True, exist_ok=True)

        self.db_conn = sqlite3.connect(db_path)
        self.db_conn.execute("""
            CREATE TABLE IF NOT EXISTS seen_tweets (
                tweet_id TEXT PRIMARY KEY,
                content TEXT,
                author TEXT,
                seen_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        self.db_conn.execute("""
            CREATE TABLE IF NOT EXISTS push_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                pushed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                tweet_count INTEGER,
                summary TEXT
            )
        """)
        self.db_conn.commit()
        retention_days = int(os.getenv("DB_RETENTION_DAYS", "7"))
        self.db_conn.execute(
            f"DELETE FROM seen_tweets WHERE seen_at < datetime('now', '-{retention_days} days')"
        )
        self.db_conn.commit()

    def _build_graph(self) -> StateGraph:
        """构建 LangGraph 工作流"""
        builder = StateGraph(MonitorState)

        builder.add_node("fetch", self._fetch_node)
        builder.add_node("filter", self._filter_node)
        builder.add_node("analyse", self._analyse_node)
        builder.add_node("push", self._push_node)

        builder.add_edge(START, "fetch")
        builder.add_edge("fetch", "filter")
        builder.add_conditional_edges(
            "filter", self._should_continue, {"continue": "analyse", "end": END}
        )
        builder.add_edge("analyse", "push")
        builder.add_edge("push", END)

        return builder.compile()

    def _fetch_node(self, state: MonitorState) -> dict:
        """抓取推文节点"""
        print("[Node: fetch] 抓取推文...")
        result = self.fetch_agent.execute()

        if result["status"] != "success":
            return {
                "error": f"抓取失败: {result.get('error')}",
                "status": "error",
                "tweets": [],
            }

        tweets = result["data"]["tweets"]
        print(f"  → 获取到 {len(tweets)} 条推文")
        return {"tweets": tweets, "status": "success"}

    def _filter_node(self, state: MonitorState) -> dict:
        """过滤新推文节点"""
        print("[Node: filter] 过滤新推文...")
        tweets = state.get("tweets", [])
        new_tweets = []
        ad_count = 0

        for tweet in tweets:
            tweet_id = str(tweet["id"])

            # 检查是否是广告
            if self._is_ad(tweet):
                ad_count += 1
                continue  # 跳过广告

            cursor = self.db_conn.execute(
                "SELECT 1 FROM seen_tweets WHERE tweet_id = ?", (tweet_id,)
            )
            if cursor.fetchone() is None:
                new_tweets.append(tweet)
                self.db_conn.execute(
                    "INSERT OR IGNORE INTO seen_tweets (tweet_id, content, author) VALUES (?, ?, ?)",
                    (tweet_id, tweet.get("content", ""), tweet.get("author", "")),
                )
        self.db_conn.commit()

        print(f"  → 过滤掉 {ad_count} 条广告")
        print(f"  → {len(new_tweets)} 条新推文")
        return {"new_tweets": new_tweets, "tweet_count": len(new_tweets)}

    def _is_ad(self, tweet: dict) -> bool:
        """检测推文是否为广告或低质量内容"""
        content = tweet.get("content", "").lower()
        author = tweet.get("author", "").lower()
        engagement = tweet.get("engagement", {})

        # 广告关键词列表
        ad_keywords = [
            "promoted",
            "ad",
            "sponsored",
            "推广",
            "广告",
            "赞助",
            "点击链接",
            "立即购买",
            "限时优惠",
            "免费领取",
            "扫码",
            "加微信",
            "加vx",
            "咨询微信",
            "详情咨询",
            "私信了解",
            "点击下方",
            "戳链接",
            "#sponsored",
        ]

        # 检查内容是否包含广告关键词
        for keyword in ad_keywords:
            if keyword in content:
                return True

        # 检查是否是已知的广告账号
        ad_accounts = [
            "promoted",
            "ad",
            "sponsor",
        ]
        for account in ad_accounts:
            if account in author:
                return True

        # 过滤低质量推文（互动数过低可能是垃圾内容）
        # 但要注意不要过滤刚发布的新推文
        views = engagement.get("views", 0)
        likes = engagement.get("likes", 0)
        replies = engagement.get("replies", 0)

        # 如果浏览量 > 1000 但点赞数 < 5，可能是低质量内容
        if views > 1000 and likes < 5 and replies < 2:
            return True

        return False

    def _should_continue(self, state: MonitorState) -> str:
        """条件判断：是否继续分析"""
        if state.get("error"):
            return "end"
        if not state.get("new_tweets"):
            print("  → 没有新推文，结束流程")
            return "end"
        return "continue"

    def _analyse_node(self, state: MonitorState) -> dict:
        """AI 分析节点"""
        print("[Node: analyse] AI 分析中...")
        new_tweets = state.get("new_tweets", [])

        result = self.analyse_agent.execute(new_tweets)

        if result["status"] != "success":
            return {"error": f"分析失败: {result.get('error')}", "status": "error"}

        data = result["data"]
        print(f"  → 分析完成 (使用 {data['provider']}/{data['model']})")
        return {
            "summary": data["summary"],
            "provider": data["provider"],
            "model": data["model"],
        }

    def _push_node(self, state: MonitorState) -> dict:
        """推送节点"""
        print("[Node: push] 推送到 Telegram...")

        result = self.push_agent.execute(
            summary=state.get("summary", ""),
            tweet_count=state.get("tweet_count", 0),
            provider=state.get("provider", "unknown"),
            model=state.get("model", "unknown"),
            tweets=state.get("new_tweets", []),  # 传递原始推文列表
        )

        if result["status"] == "success":
            print("  → 推送成功")
            self.db_conn.execute(
                "INSERT INTO push_history (tweet_count, summary) VALUES (?, ?)",
                (state.get("tweet_count", 0), state.get("summary", "")),
            )
            self.db_conn.commit()
            return {"status": "success"}
        else:
            print(f"  ⚠️ 推送失败: {result.get('error')}")
            return {"status": "push_failed"}

    def run(self) -> Dict[str, Any]:
        """执行工作流"""
        start_time = datetime.now()
        print(f"[{start_time.strftime('%H:%M:%S')}] 开始执行 LangGraph 工作流\n")

        initial_state: MonitorState = {
            "tweets": [],
            "new_tweets": [],
            "summary": "",
            "provider": "",
            "model": "",
            "tweet_count": 0,
            "error": None,
            "status": "pending",
        }

        result = self.graph.invoke(initial_state)

        duration = (datetime.now() - start_time).total_seconds()
        print(f"\n[完成] 耗时 {duration:.1f}s")

        return {
            "status": result.get("status", "unknown"),
            "tweet_count": result.get("tweet_count", 0),
            "provider": result.get("provider", ""),
            "model": result.get("model", ""),
            "error": result.get("error"),
            "duration_seconds": duration,
        }

    def cleanup(self):
        if self.db_conn:
            self.db_conn.close()

        # 关闭 Chrome（如果是自动启动的）
        import subprocess
        cdp_port = int(os.getenv("CDP_PORT", "9222"))
        print("\n🔒 关闭浏览器...")
        subprocess.run(
            ["pkill", "-f", f"remote-debugging-port={cdp_port}"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.cleanup()


def main():
    print(f"[{datetime.now()}] Starting Twitter Monitor (LangGraph)...\n")

    with TwitterMonitorGraph() as monitor:
        result = monitor.run()

        if result["status"] == "success":
            if result.get("tweet_count", 0) > 0:
                print(f"\n✅ 成功分析 {result['tweet_count']} 条推文")
            else:
                print("\nℹ️ 没有新推文")
        else:
            print(f"\n❌ 执行失败: {result.get('error')}")
            sys.exit(1)


if __name__ == "__main__":
    main()
