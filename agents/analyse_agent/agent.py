"""
Analyse Agent - 推文分析代理
负责使用 LLM 分析推文内容，提取热点和要点
"""

import os
from typing import Dict, Any, List, Optional

from agents.base import BaseAgent
from agents.llm_factory import LLMFactory, SimpleLLM


class AnalyseAgent(BaseAgent):
    """
    分析代理
    职责：使用 LLM 分析推文，提取热点和要点
    """

    def __init__(
        self,
        provider: str = None,
        strategy_path: str = None,
        temperature: float = 0.3,
    ):
        """
        初始化 Analyse Agent

        Args:
            provider: LLM 提供方（如果为 None，从环境变量读取）
            strategy_path: 分析策略文件路径（可选）
            temperature: LLM 温度参数
        """
        super().__init__(name="AnalyseAgent")

        self.temperature = temperature
        self.strategy_path = strategy_path
        self.strategy = self._load_strategy() if strategy_path else None

        # 初始化 LLM
        self.llm = SimpleLLM(provider)
        self._log(f"LLM: {self.llm}", "success")

        self.is_initialized = True

    def execute(self, tweets: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        分析推文列表

        Args:
            tweets: 推文列表，每个推文包含 id, content, author

        Returns:
            包含分析结果的字典
        """
        if not tweets:
            return self._error("没有推文需要分析")

        self._log(f"开始分析 {len(tweets)} 条推文")

        # 构建 prompt
        prompt = self._build_prompt(tweets)

        # 调用 LLM
        try:
            summary = self.llm.invoke(
                prompt=prompt,
                system=self._get_system_prompt(),
                max_tokens=2000,
                temperature=self.temperature,
            )
        except Exception as e:
            return self._error(f"LLM 调用失败: {e}")

        self._log("分析完成", "success")

        return self._success(
            data={
                "summary": summary,
                "tweet_count": len(tweets),
                "provider": self.llm.provider,
                "model": self.llm.model,
            },
            message=f"成功分析 {len(tweets)} 条推文",
        )

    def _get_system_prompt(self) -> str:
        """获取系统提示"""
        if self.strategy:
            return f"你是一个专业的社交媒体分析师。\n\n分析策略:\n{self.strategy}"
        return "你是一个专业的社交媒体分析师，擅长从推文中提取热点话题和有价值的信息。"

    def _build_prompt(self, tweets: List[Dict[str, Any]]) -> str:
        """构建分析提示"""
        max_tweets = int(os.getenv("MAX_TWEETS_TO_ANALYZE", "20"))
        # 格式化推文
        tweets_text = "\n\n---\n\n".join(
            [
                f"@{t.get('author', 'unknown')}:\n{t.get('content', '')}"
                for t in tweets[:max_tweets]  # 从环境变量读取
            ]
        )

        return f"""分析以下 Twitter/X 推文，提取热点和要点。

【推文内容】
{tweets_text}

【分析要求】
请用简洁的中文总结：

1. **🔥 热点话题**（2-4个最重要的）
   - 简述每个话题的核心内容

2. **💡 值得关注的观点**（如果有）
   - 有见地的讨论或独特视角

3. **📊 潜在机会信号**（如果有）
   - 技术趋势、投资信号等

4. **🎯 行动建议**（可选）
   - 建议深入了解的话题

请保持简洁，每个要点 1-2 句话即可。使用 Markdown 格式。"""

    def _load_strategy(self) -> Optional[str]:
        """加载分析策略文件"""
        if not self.strategy_path or not os.path.exists(self.strategy_path):
            return None
        try:
            with open(self.strategy_path, "r", encoding="utf-8") as f:
                return f.read()
        except Exception as e:
            self._log(f"加载策略文件失败: {e}", "warning")
            return None
