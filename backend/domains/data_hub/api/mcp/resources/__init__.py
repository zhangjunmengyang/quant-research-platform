"""
MCP 资源模块

提供数据资源的只读访问。
"""

from .data_resources import DataResourceProvider, ResourceDefinition, ResourceContent

__all__ = [
    "DataResourceProvider",
    "ResourceDefinition",
    "ResourceContent",
]
