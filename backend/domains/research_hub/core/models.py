"""
研报知识库数据模型

定义研报、切块、对话等核心数据结构。
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
import uuid


class ProcessingStatus(Enum):
    """研报处理状态"""
    UPLOADED = "uploaded"  # 已上传
    PARSING = "parsing"  # 解析中
    PARSED = "parsed"  # 已解析
    CHUNKING = "chunking"  # 切块中
    CHUNKED = "chunked"  # 已切块
    EMBEDDING = "embedding"  # 向量化中
    INDEXED = "indexed"  # 已索引
    ENRICHING = "enriching"  # 增强中
    READY = "ready"  # 就绪
    FAILED = "failed"  # 失败


@dataclass
class ResearchReport:
    """
    研报数据模型

    存储研报的基本信息、解析内容和处理状态。
    """
    # 基础信息
    id: Optional[int] = None
    uuid: str = field(default_factory=lambda: str(uuid.uuid4()))
    title: str = ""
    filename: str = ""
    file_path: str = ""
    file_size: int = 0
    page_count: int = 0

    # 来源信息
    author: Optional[str] = None
    source_url: Optional[str] = None
    publish_date: Optional[datetime] = None

    # 解析后的内容
    content_markdown: str = ""  # 完整 Markdown

    # 增强信息（LLM 生成）
    summary: str = ""  # 摘要
    tags: str = ""  # 逗号分隔的标签
    category: str = ""  # 分类

    # 处理状态
    status: str = ProcessingStatus.UPLOADED.value
    progress: int = 0  # 0-100
    error_message: str = ""

    # 时间戳
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    parsed_at: Optional[datetime] = None
    indexed_at: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'id': self.id,
            'uuid': self.uuid,
            'title': self.title,
            'filename': self.filename,
            'file_path': self.file_path,
            'file_size': self.file_size,
            'page_count': self.page_count,
            'author': self.author,
            'source_url': self.source_url,
            'publish_date': self.publish_date,
            'content_markdown': self.content_markdown,
            'summary': self.summary,
            'tags': self.tags,
            'category': self.category,
            'status': self.status,
            'progress': self.progress,
            'error_message': self.error_message,
            'created_at': self.created_at,
            'updated_at': self.updated_at,
            'parsed_at': self.parsed_at,
            'indexed_at': self.indexed_at,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ResearchReport':
        """从字典创建实例"""
        valid_fields = {k: v for k, v in data.items() if k in cls.__dataclass_fields__}
        return cls(**valid_fields)

    @property
    def tags_list(self) -> List[str]:
        """获取标签列表"""
        if not self.tags:
            return []
        return [t.strip() for t in self.tags.split(',') if t.strip()]

    @property
    def is_ready(self) -> bool:
        """是否处理完成"""
        return self.status == ProcessingStatus.READY.value

    @property
    def is_failed(self) -> bool:
        """是否处理失败"""
        return self.status == ProcessingStatus.FAILED.value


@dataclass
class ResearchChunk:
    """
    研报切块数据模型

    存储切块内容、向量和元数据。
    """
    # 基础信息
    id: Optional[int] = None
    chunk_id: str = field(default_factory=lambda: str(uuid.uuid4())[:12])
    report_id: Optional[int] = None
    report_uuid: str = ""

    # 位置信息
    chunk_index: int = 0
    page_start: Optional[int] = None
    page_end: Optional[int] = None

    # 内容
    chunk_type: str = "text"  # text / table / formula / figure
    content: str = ""
    token_count: int = 0

    # 层次信息
    heading_path: str = "[]"  # JSON 格式的标题路径
    section_title: str = ""

    # 向量（存储为 JSON 字符串，PostgreSQL 需要 pgvector 扩展）
    # 实际向量存储由 vector_store 处理
    embedding_model: str = ""

    # 元数据
    metadata: str = "{}"  # JSON 格式的额外信息（JSONB 列需要有效 JSON）

    # 时间戳
    created_at: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'id': self.id,
            'chunk_id': self.chunk_id,
            'report_id': self.report_id,
            'report_uuid': self.report_uuid,
            'chunk_index': self.chunk_index,
            'page_start': self.page_start,
            'page_end': self.page_end,
            'chunk_type': self.chunk_type,
            'content': self.content,
            'token_count': self.token_count,
            'heading_path': self.heading_path,
            'section_title': self.section_title,
            'embedding_model': self.embedding_model,
            'metadata': self.metadata,
            'created_at': self.created_at,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ResearchChunk':
        """从字典创建实例"""
        valid_fields = {k: v for k, v in data.items() if k in cls.__dataclass_fields__}
        return cls(**valid_fields)


@dataclass
class Conversation:
    """
    对话数据模型

    存储 ChatBot 对话信息。
    """
    id: Optional[int] = None
    uuid: str = field(default_factory=lambda: str(uuid.uuid4()))
    title: str = ""

    # 关联的研报（可选，None 表示全部研报）
    report_id: Optional[int] = None

    # 时间戳
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'id': self.id,
            'uuid': self.uuid,
            'title': self.title,
            'report_id': self.report_id,
            'created_at': self.created_at,
            'updated_at': self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Conversation':
        """从字典创建实例"""
        valid_fields = {k: v for k, v in data.items() if k in cls.__dataclass_fields__}
        return cls(**valid_fields)


@dataclass
class Message:
    """
    消息数据模型

    存储对话中的单条消息。
    """
    id: Optional[int] = None
    conversation_id: Optional[int] = None
    role: str = "user"  # user / assistant
    content: str = ""

    # 来源引用（JSON 格式）
    sources: str = "[]"  # [{report_id, chunk_id, page, relevance}]

    # 时间戳
    created_at: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'id': self.id,
            'conversation_id': self.conversation_id,
            'role': self.role,
            'content': self.content,
            'sources': self.sources,
            'created_at': self.created_at,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Message':
        """从字典创建实例"""
        import json
        valid_fields = {k: v for k, v in data.items() if k in cls.__dataclass_fields__}
        # JSONB 字段会被 psycopg 自动解析为 Python 对象，需要转回字符串
        if 'sources' in valid_fields and isinstance(valid_fields['sources'], (list, dict)):
            valid_fields['sources'] = json.dumps(valid_fields['sources'])
        return cls(**valid_fields)

    @property
    def sources_list(self) -> List[Dict[str, Any]]:
        """解析来源列表"""
        if not self.sources:
            return []
        import json
        try:
            return json.loads(self.sources)
        except json.JSONDecodeError:
            return []
