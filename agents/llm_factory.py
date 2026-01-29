"""
LLM Factory - 统一的 LLM 创建工厂
支持多 Provider 一键切换，兼容 LangChain
"""

import os
from typing import Optional, Dict, Any, Union
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage


# Provider 配置映射
PROVIDER_CONFIGS = {
    # 本地代理 (默认，你的 opencode 配置)
    "local": {
        "base_url_env": "LOCAL_BASE_URL",
        "api_key_env": "LOCAL_API_KEY",
        "model_env": "LOCAL_MODEL",
        "defaults": {
            "base_url": "http://127.0.0.1:8045/v1",
            "api_key": "sk-xxx",
            "model": "claude-sonnet-4-5",
        },
    },
    # 火山方舟
    "ark": {
        "base_url_env": "ARK_BASE_URL",
        "api_key_env": "ARK_API_KEY",
        "model_env": "ARK_MODEL",
        "defaults": {
            "base_url": "https://ark.cn-beijing.volces.com/api/v3",
            "api_key": "",
            "model": "deepseek-v3-2-251201",
        },
    },
    # LB One API
    "one": {
        "base_url_env": "ONE_BASE_URL",
        "api_key_env": "ONE_API_KEY",
        "model_env": "ONE_MODEL",
        "defaults": {
            "base_url": "https://lboneapi.longbridge-inc.com/v1",
            "api_key": "",
            "model": "gpt-5.1",
        },
    },
    # Anthropic
    "anthropic": {
        "base_url_env": "ANTHROPIC_BASE_URL",
        "api_key_env": "ANTHROPIC_API_KEY",
        "model_env": "ANTHROPIC_MODEL",
        "defaults": {
            "base_url": "https://api.anthropic.com/v1",
            "api_key": "",
            "model": "claude-sonnet-4-20250514",
        },
    },
    # OpenAI
    "openai": {
        "base_url_env": "OPENAI_BASE_URL",
        "api_key_env": "OPENAI_API_KEY",
        "model_env": "OPENAI_MODEL",
        "defaults": {
            "base_url": "https://api.openai.com/v1",
            "api_key": "",
            "model": "gpt-4o",
        },
    },
    # Ollama
    "ollama": {
        "base_url_env": "OLLAMA_BASE_URL",
        "api_key_env": "OLLAMA_API_KEY",
        "model_env": "OLLAMA_MODEL",
        "defaults": {
            "base_url": "http://localhost:11434",
            "api_key": "ollama",
            "model": "llama3.2",
        },
    },
    # Gemini (通过代理)
    "gemini": {
        "base_url_env": "GEMINI_BASE_URL",
        "api_key_env": "GEMINI_API_KEY",
        "model_env": "GEMINI_MODEL",
        "defaults": {
            "base_url": "http://127.0.0.1:8045/v1",
            "api_key": "sk-xxx",
            "model": "gemini-3-pro-high",
        },
    },
}


class LLMFactory:
    """
    LLM 工厂类
    根据 provider 创建对应的 LangChain ChatModel
    """

    @staticmethod
    def get_provider() -> str:
        """获取当前配置的 provider"""
        return os.getenv("LLM_PROVIDER", "local").strip().lower()

    @staticmethod
    def get_config(provider: Optional[str] = None) -> Dict[str, str]:
        """获取指定 provider 的配置"""
        provider = provider or LLMFactory.get_provider()

        if provider not in PROVIDER_CONFIGS:
            print(f"Warning: Unknown provider '{provider}', falling back to 'local'")
            provider = "local"

        config = PROVIDER_CONFIGS[provider]
        defaults = config["defaults"]

        return {
            "provider": provider,
            "base_url": os.getenv(config["base_url_env"], defaults["base_url"]),
            "api_key": os.getenv(config["api_key_env"], defaults["api_key"]),
            "model": os.getenv(config["model_env"], defaults["model"]),
        }

    @staticmethod
    def create(
        provider: Optional[str] = None, temperature: float = 0.3, **kwargs
    ) -> BaseChatModel:
        """
        创建 LangChain ChatModel

        Args:
            provider: LLM 提供方，如果为 None 则从环境变量读取
            temperature: 温度参数
            **kwargs: 其他参数传递给 ChatModel

        Returns:
            LangChain BaseChatModel 实例
        """
        config = LLMFactory.get_config(provider)
        provider = config["provider"]

        # Ollama 使用专门的 ChatOllama
        if provider == "ollama":
            from langchain_ollama import ChatOllama

            return ChatOllama(
                model=config["model"],
                base_url=config["base_url"],
                temperature=temperature,
                **kwargs,
            )

        # 其他 provider 使用 ChatOpenAI (OpenAI 兼容)
        from langchain_openai import ChatOpenAI

        return ChatOpenAI(
            model=config["model"],
            base_url=config["base_url"],
            api_key=config["api_key"],
            temperature=temperature,
            **kwargs,
        )

    @staticmethod
    def create_simple(provider: Optional[str] = None) -> "SimpleLLM":
        """
        创建简单的 LLM 包装器（不依赖完整 LangChain）
        用于简单场景，直接调用 OpenAI SDK
        """
        return SimpleLLM(provider)


class SimpleLLM:
    """
    简单的 LLM 包装器
    直接使用 OpenAI SDK，不依赖 LangChain 的复杂功能
    适用于简单的单轮对话场景
    """

    def __init__(self, provider: Optional[str] = None):
        from openai import OpenAI

        self.config = LLMFactory.get_config(provider)
        self.provider = self.config["provider"]
        self.model = self.config["model"]

        # Ollama 需要特殊处理 base_url
        base_url = self.config["base_url"]
        if self.provider == "ollama" and not base_url.endswith("/v1"):
            base_url = f"{base_url}/v1"

        self.client = OpenAI(
            base_url=base_url,
            api_key=self.config["api_key"],
        )

    def invoke(
        self,
        prompt: str,
        system: Optional[str] = None,
        max_tokens: int = 2000,
        temperature: float = 0.3,
    ) -> str:
        """
        调用 LLM

        Args:
            prompt: 用户输入
            system: 系统提示（可选）
            max_tokens: 最大 token 数
            temperature: 温度

        Returns:
            LLM 响应文本
        """
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature,
        )

        return response.choices[0].message.content

    def __repr__(self) -> str:
        return f"SimpleLLM(provider={self.provider}, model={self.model})"
