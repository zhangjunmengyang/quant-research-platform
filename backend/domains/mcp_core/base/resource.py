"""
MCP Resource 基类和资源提供者

提供可扩展的资源定义框架，支持:
- 静态资源注册
- 动态资源 (URI 模板)
- 资源缓存
"""

import json
import logging
import re
import time
from abc import ABC
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class ResourceDefinition:
    """MCP 资源定义"""
    uri: str
    name: str
    description: str
    mime_type: str = "application/json"

    def to_mcp_format(self) -> dict[str, Any]:
        """转换为 MCP 协议格式"""
        return {
            "uri": self.uri,
            "name": self.name,
            "description": self.description,
            "mimeType": self.mime_type,
        }


@dataclass
class ResourceContent:
    """资源内容"""
    uri: str
    mime_type: str
    text: str | None = None
    blob: bytes | None = None

    def to_mcp_format(self) -> dict[str, Any]:
        """转换为 MCP 协议格式"""
        result = {
            "uri": self.uri,
            "mimeType": self.mime_type,
        }
        if self.text is not None:
            result["text"] = self.text
        if self.blob is not None:
            import base64
            result["blob"] = base64.b64encode(self.blob).decode()
        return result

    @classmethod
    def json(cls, uri: str, data: Any) -> 'ResourceContent':
        """创建 JSON 资源内容"""
        return cls(
            uri=uri,
            mime_type="application/json",
            text=json.dumps(data, ensure_ascii=False, indent=2),
        )

    @classmethod
    def text(cls, uri: str, content: str, mime_type: str = "text/plain") -> 'ResourceContent':
        """创建文本资源内容"""
        return cls(
            uri=uri,
            mime_type=mime_type,
            text=content,
        )


@dataclass
class CacheEntry:
    """缓存条目"""
    content: ResourceContent
    timestamp: float
    ttl: int


class BaseResourceProvider(ABC):
    """
    资源提供者基类

    管理 MCP 资源的注册、发现和读取。

    使用方式:
        class MyResourceProvider(BaseResourceProvider):
            def __init__(self):
                super().__init__()
                self._register_resources()

            def _register_resources(self):
                self.register_static(
                    uri="myapp://stats",
                    name="统计信息",
                    description="应用统计信息",
                    handler=self._read_stats,
                )

                self.register_dynamic(
                    pattern="myapp://item/{id}",
                    name="项目详情",
                    description="获取项目详情",
                    handler=self._read_item,
                )

            async def _read_stats(self) -> ResourceContent:
                return ResourceContent.json("myapp://stats", {"count": 100})

            async def _read_item(self, id: str) -> Optional[ResourceContent]:
                item = get_item(id)
                if item:
                    return ResourceContent.json(f"myapp://item/{id}", item)
                return None
    """

    def __init__(self, default_cache_ttl: int = 0):
        """
        初始化资源提供者

        Args:
            default_cache_ttl: 默认缓存 TTL（秒），0 表示不缓存
        """
        self._static_resources: dict[str, ResourceDefinition] = {}
        self._static_handlers: dict[str, Callable[[], Awaitable[ResourceContent]]] = {}
        self._dynamic_patterns: list[dict[str, Any]] = []
        self._cache: dict[str, CacheEntry] = {}
        self._default_cache_ttl = default_cache_ttl

    def register_static(
        self,
        uri: str,
        name: str,
        description: str,
        handler: Callable[[], Awaitable[ResourceContent]],
        mime_type: str = "application/json",
        cache_ttl: int | None = None,
    ) -> None:
        """
        注册静态资源

        Args:
            uri: 资源 URI
            name: 资源名称
            description: 资源描述
            handler: 资源读取处理函数
            mime_type: MIME 类型
            cache_ttl: 缓存 TTL（秒），None 使用默认值
        """
        self._static_resources[uri] = ResourceDefinition(
            uri=uri,
            name=name,
            description=description,
            mime_type=mime_type,
        )
        self._static_handlers[uri] = handler
        logger.debug(f"注册静态资源: {uri}")

    def register_dynamic(
        self,
        pattern: str,
        name: str,
        description: str,
        handler: Callable[..., Awaitable[ResourceContent | None]],
        mime_type: str = "application/json",
    ) -> None:
        """
        注册动态资源

        Args:
            pattern: URI 模式，如 "myapp://item/{id}"
            name: 资源名称
            description: 资源描述
            handler: 资源读取处理函数，接收 URI 中的参数
            mime_type: MIME 类型
        """
        # 将 {param} 模式转换为正则表达式
        regex_pattern = pattern
        param_names = re.findall(r'\{(\w+)\}', pattern)
        for param in param_names:
            regex_pattern = regex_pattern.replace(f'{{{param}}}', f'(?P<{param}>[^/]+)')

        self._dynamic_patterns.append({
            "pattern": pattern,
            "regex": re.compile(f"^{regex_pattern}$"),
            "param_names": param_names,
            "handler": handler,
            "definition": ResourceDefinition(
                uri=pattern,
                name=name,
                description=description,
                mime_type=mime_type,
            ),
        })
        logger.debug(f"注册动态资源: {pattern}")

    def list_resources(self) -> list[ResourceDefinition]:
        """列出所有可用资源"""
        resources = list(self._static_resources.values())

        # 添加动态资源模板
        for dynamic in self._dynamic_patterns:
            resources.append(dynamic["definition"])

        return resources

    async def read_resource(self, uri: str) -> ResourceContent | None:
        """
        读取资源内容

        Args:
            uri: 资源 URI

        Returns:
            资源内容，不存在则返回 None
        """
        # 检查缓存
        cached = self._get_from_cache(uri)
        if cached is not None:
            return cached

        # 尝试静态资源
        if uri in self._static_handlers:
            try:
                content = await self._static_handlers[uri]()
                self._set_cache(uri, content)
                return content
            except Exception as e:
                logger.error(f"读取静态资源失败 {uri}: {e}")
                return None

        # 尝试动态资源
        for dynamic in self._dynamic_patterns:
            match = dynamic["regex"].match(uri)
            if match:
                params = match.groupdict()
                try:
                    content = await dynamic["handler"](**params)
                    if content is not None:
                        self._set_cache(uri, content)
                    return content
                except Exception as e:
                    logger.error(f"读取动态资源失败 {uri}: {e}")
                    return None

        logger.warning(f"未知资源 URI: {uri}")
        return None

    def _get_from_cache(self, uri: str) -> ResourceContent | None:
        """从缓存获取"""
        if uri in self._cache:
            entry = self._cache[uri]
            if time.time() - entry.timestamp < entry.ttl:
                return entry.content
            else:
                del self._cache[uri]
        return None

    def _set_cache(self, uri: str, content: ResourceContent, ttl: int | None = None) -> None:
        """设置缓存"""
        ttl = ttl if ttl is not None else self._default_cache_ttl
        if ttl > 0:
            self._cache[uri] = CacheEntry(
                content=content,
                timestamp=time.time(),
                ttl=ttl,
            )

    def clear_cache(self, uri: str | None = None) -> None:
        """清除缓存"""
        if uri:
            self._cache.pop(uri, None)
        else:
            self._cache.clear()


class SimpleResourceProvider(BaseResourceProvider):
    """
    简单资源提供者

    适用于简单场景，直接在初始化时提供资源。
    """

    def __init__(
        self,
        resources: dict[str, dict[str, Any]] | None = None,
        default_cache_ttl: int = 0,
    ):
        """
        初始化

        Args:
            resources: 静态资源字典，格式为 {uri: {"name": ..., "description": ..., "data": ...}}
            default_cache_ttl: 默认缓存 TTL
        """
        super().__init__(default_cache_ttl)
        self._static_data: dict[str, Any] = {}

        if resources:
            for uri, config in resources.items():
                self._static_data[uri] = config.get("data", {})
                self.register_static(
                    uri=uri,
                    name=config.get("name", uri),
                    description=config.get("description", ""),
                    handler=self._create_handler(uri),
                    mime_type=config.get("mime_type", "application/json"),
                )

    def _create_handler(self, uri: str) -> Callable[[], Awaitable[ResourceContent]]:
        """创建资源处理函数"""
        async def handler() -> ResourceContent:
            data = self._static_data.get(uri, {})
            if callable(data):
                data = data()
            return ResourceContent.json(uri, data)
        return handler

    def set_data(self, uri: str, data: Any) -> None:
        """更新资源数据"""
        self._static_data[uri] = data
        self.clear_cache(uri)
