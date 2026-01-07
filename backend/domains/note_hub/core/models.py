"""
经验概览数据模型定义
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Dict, Any, List


@dataclass
class Note:
    """
    经验概览数据类

    Attributes:
        id: 笔记 ID（主键，自增）
        title: 笔记标题
        content: 笔记内容（Markdown 格式）
        tags: 标签（逗号分隔的字符串）
        source: 来源（如 factor, strategy, backtest, manual）
        source_ref: 来源引用（如因子名、策略ID等）
        created_at: 创建时间
        updated_at: 更新时间
    """
    id: Optional[int] = None
    title: str = ""
    content: str = ""
    tags: str = ""
    source: str = ""
    source_ref: str = ""
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'id': self.id,
            'title': self.title,
            'content': self.content,
            'tags': self.tags,
            'source': self.source,
            'source_ref': self.source_ref,
            'created_at': self.created_at,
            'updated_at': self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Note':
        """从字典创建笔记实例"""
        valid_fields = {k: v for k, v in data.items() if k in cls.__dataclass_fields__}
        return cls(**valid_fields)

    @property
    def tags_list(self) -> List[str]:
        """获取标签列表（逗号分隔的字符串转为列表）"""
        if not self.tags:
            return []
        return [t.strip() for t in self.tags.split(',') if t.strip()]

    def set_tags(self, tags: List[str]):
        """设置标签列表"""
        self.tags = ','.join(tags)

    def add_tag(self, tag: str):
        """添加标签"""
        tags = self.tags_list
        if tag not in tags:
            tags.append(tag)
            self.set_tags(tags)

    def remove_tag(self, tag: str):
        """移除标签"""
        tags = self.tags_list
        if tag in tags:
            tags.remove(tag)
            self.set_tags(tags)

    @property
    def summary(self) -> str:
        """获取内容摘要（前 200 字符）"""
        if not self.content:
            return ""
        content = self.content.strip()
        if len(content) <= 200:
            return content
        return content[:200] + "..."
