"""
Web 模块

提供 FastAPI Web 服务，支持流式对话和记忆功能。
"""

from .main import create_app

__all__ = ["create_app"]
