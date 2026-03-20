"""
HTTP Adapter 配置加载器

从 config/adapters.yaml 加载 HTTP 适配器配置。
"""

import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

from .client import HTTPAdapter, HTTPEndpoint


logger = logging.getLogger(__name__)


class HTTPConfigLoader:
    """
    HTTP 配置加载器

    从 YAML 文件加载 HTTP 适配器配置。
    """

    def __init__(self, config_path: str = "config/adapters.yaml"):
        self.config_path = Path(config_path)

    def load_all(self) -> Dict[str, Dict[str, Any]]:
        """加载所有适配器配置"""
        if not self.config_path.exists():
            logger.warning(f"配置文件不存在: {self.config_path}")
            return {}

        with open(self.config_path, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f) or {}

        return config.get("http_adapters", {})

    async def create_adapter(
        self,
        name: str,
        config: Optional[Dict[str, Any]] = None,
    ) -> Optional[HTTPAdapter]:
        """从配置创建适配器"""
        all_configs = self.load_all()

        adapter_config = config or all_configs.get(name)
        if not adapter_config:
            logger.warning(f"未找到适配器配置: {name}")
            return None

        # 解析环境变量
        base_url = self._parse_env(adapter_config.get("base_url", ""))
        auth_config = adapter_config.get("auth", {})

        # 处理认证配置中的环境变量
        if "token" in auth_config:
            auth_config["token"] = os.getenv(
                auth_config.get("token_env", ""), auth_config["token"]
            )

        # 创建适配器
        adapter = HTTPAdapter(
            config={
                "name": name,
                "base_url": base_url,
                "auth": auth_config,
            },
            base_url=base_url,
            auth_config=auth_config,
        )

        # 注册端点
        for ep_config in adapter_config.get("endpoints", []):
            endpoint = HTTPEndpoint(
                name=ep_config["name"],
                method=ep_config.get("method", "GET"),
                path=ep_config["path"],
                description=ep_config.get("description"),
                auth_type=ep_config.get("auth_type"),
                headers=ep_config.get("headers"),
                timeout=ep_config.get("timeout", 30.0),
            )
            adapter.register_endpoint(endpoint)

        await adapter.initialize()
        return adapter

    def _parse_env(self, value: str) -> str:
        """解析环境变量（如 ${VAR_NAME}）"""
        import re

        def replace_env(match):
            var_name = match.group(1)
            return os.getenv(var_name, "")

        return re.sub(r"\$\{(\w+)\}", replace_env, value)


async def load_http_adapter(
    name: str,
    config_path: str = "config/adapters.yaml",
) -> Optional[HTTPAdapter]:
    """
    便捷函数：加载 HTTP 适配器

    Args:
        name: 适配器名称
        config_path: 配置文件路径

    Returns:
        初始化后的 HTTP 适配器
    """
    loader = HTTPConfigLoader(config_path)
    return await loader.create_adapter(name)
