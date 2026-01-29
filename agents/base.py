"""
Base Agent - 所有 Agent 的基类
提供统一的接口和 LLM 工厂
"""

import os
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from datetime import datetime


class BaseAgent(ABC):
    """
    Agent 基类
    所有 Agent 都继承此类，实现统一接口
    """

    def __init__(self, name: str = "BaseAgent"):
        self.name = name
        self.is_initialized = False
        self.last_execution_time: Optional[datetime] = None
        self.execution_count = 0

    @abstractmethod
    def execute(self, *args, **kwargs) -> Dict[str, Any]:
        """
        执行 Agent 的主要任务

        Returns:
            包含执行结果的字典，必须包含 'status' 字段 ('success' | 'error')
        """
        pass

    def _success(self, data: Any = None, message: str = "") -> Dict[str, Any]:
        """返回成功结果"""
        self.execution_count += 1
        self.last_execution_time = datetime.now()
        return {
            "status": "success",
            "agent": self.name,
            "data": data,
            "message": message,
            "timestamp": self.last_execution_time.isoformat(),
        }

    def _error(self, error: str, data: Any = None) -> Dict[str, Any]:
        """返回错误结果"""
        return {
            "status": "error",
            "agent": self.name,
            "error": error,
            "data": data,
            "timestamp": datetime.now().isoformat(),
        }

    def _log(self, message: str, level: str = "info"):
        """统一日志格式"""
        symbols = {"info": "ℹ️", "success": "✓", "error": "✗", "warning": "⚠️"}
        symbol = symbols.get(level, "•")
        print(f"{symbol} [{self.name}] {message}")
