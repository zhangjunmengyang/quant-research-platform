"""
嵌入器基类

负责将文本转换为向量表示。
"""

from abc import abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Union
from enum import Enum

from .component import AsyncComponent, ComponentConfig, ComponentType


class EmbeddingType(Enum):
    """嵌入类型"""
    DENSE = "dense"  # 稠密向量
    SPARSE = "sparse"  # 稀疏向量 (用于 BM25 风格检索)
    COLBERT = "colbert"  # ColBERT 风格多向量


@dataclass
class EmbeddingResult:
    """嵌入结果"""
    # 稠密向量
    dense: Optional[List[float]] = None

    # 稀疏向量 (token -> weight)
    sparse: Optional[Dict[str, float]] = None

    # ColBERT 多向量
    colbert: Optional[List[List[float]]] = None

    # 元数据
    model: Optional[str] = None
    dimensions: Optional[int] = None
    token_count: Optional[int] = None

    @property
    def vector(self) -> Optional[List[float]]:
        """兼容性属性，返回稠密向量"""
        return self.dense


@dataclass
class EmbedderConfig(ComponentConfig):
    """嵌入器配置"""
    # 模型配置
    model_name: str = "BAAI/bge-m3"
    dimensions: int = 1024

    # 输出类型
    return_dense: bool = True
    return_sparse: bool = False
    return_colbert: bool = False

    # 批处理
    batch_size: int = 32

    # 归一化
    normalize: bool = True

    # 设备
    device: str = "auto"  # auto / cpu / cuda / mps


class BaseEmbedder(AsyncComponent[EmbedderConfig, List[EmbeddingResult]]):
    """
    嵌入器基类

    负责将文本转换为向量表示，支持:
    - 稠密向量 (Dense): 标准语义嵌入
    - 稀疏向量 (Sparse): BM25 风格的词权重
    - ColBERT 向量: 多向量表示

    示例:
        @component_registries.embedder.register("bge-m3")
        class BGEM3Embedder(BaseEmbedder):
            async def embed(self, texts: List[str]) -> List[EmbeddingResult]:
                # 使用 BGE-M3 生成嵌入
                ...
    """

    component_type = ComponentType.EMBEDDER

    def __init__(
        self,
        model_name: str = "BAAI/bge-m3",
        dimensions: int = 1024,
        batch_size: int = 32,
        normalize: bool = True,
        return_dense: bool = True,
        return_sparse: bool = False,
        **kwargs,
    ):
        config = EmbedderConfig(
            model_name=model_name,
            dimensions=dimensions,
            batch_size=batch_size,
            normalize=normalize,
            return_dense=return_dense,
            return_sparse=return_sparse,
            extra=kwargs,
        )
        super().__init__(config)

    @abstractmethod
    async def embed(self, texts: List[str]) -> List[EmbeddingResult]:
        """
        生成文本嵌入

        Args:
            texts: 文本列表

        Returns:
            嵌入结果列表
        """
        raise NotImplementedError

    async def embed_single(self, text: str) -> EmbeddingResult:
        """嵌入单个文本"""
        results = await self.embed([text])
        return results[0]

    async def embed_query(self, query: str) -> EmbeddingResult:
        """
        嵌入查询

        部分模型对查询有特殊处理（如添加前缀）
        """
        return await self.embed_single(query)

    async def execute(
        self, texts: Union[str, List[str]]
    ) -> Union[EmbeddingResult, List[EmbeddingResult]]:
        """执行嵌入"""
        if isinstance(texts, str):
            return await self.embed_single(texts)
        return await self.embed(texts)

    @property
    def dimensions(self) -> int:
        """向量维度"""
        return self.config.dimensions if self.config else 1024
